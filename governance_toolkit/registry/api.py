from __future__ import annotations

import datetime
import hashlib
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .db import get_db, init_db
from .models import AgentRecord
from .schemas import (
    AgentCreate,
    AgentResponse,
    AgentUpdate,
    BatchResult,
    GovernanceReport,
)
from ..scorer.owasp import calculate_score, generate_report

app = FastAPI(
    title="AI Governance Registry",
    description="Register and track AI agents for governance compliance (OWASP LLM maturity)",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


def _make_agent_id(body: AgentCreate) -> str:
    if body.agent_id:
        return body.agent_id
    raw = f"{body.name}:{body.framework}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _get_or_404(db: Session, agent_id: str) -> AgentRecord:
    record = db.query(AgentRecord).filter_by(agent_id=agent_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return record


@app.post("/api/v1/agents", response_model=AgentResponse, status_code=201)
def create_agent(body: AgentCreate, db: Session = Depends(get_db)):
    agent_id = _make_agent_id(body)
    existing = db.query(AgentRecord).filter_by(agent_id=agent_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Agent already registered")

    score = calculate_score(body)
    now = datetime.datetime.utcnow()
    data = body.dict(exclude_none=True)
    data.pop("agent_id", None)

    record = AgentRecord(
        agent_id=agent_id,
        governance_score=score,
        first_seen=now,
        last_seen=now,
        **data,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.get("/api/v1/agents", response_model=List[AgentResponse])
def list_agents(
    framework: Optional[str] = None,
    min_score: Optional[float] = None,
    owner: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(AgentRecord)
    if framework:
        q = q.filter(AgentRecord.framework == framework)
    if min_score is not None:
        q = q.filter(AgentRecord.governance_score >= min_score)
    if owner:
        q = q.filter(AgentRecord.owner == owner)
    return q.order_by(AgentRecord.last_seen.desc()).offset(offset).limit(limit).all()


@app.get("/api/v1/agents/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    return _get_or_404(db, agent_id)


@app.patch("/api/v1/agents/{agent_id}", response_model=AgentResponse)
def update_agent(agent_id: str, body: AgentUpdate, db: Session = Depends(get_db)):
    record = _get_or_404(db, agent_id)
    for field_name, value in body.dict(exclude_unset=True).items():
        setattr(record, field_name, value)
    record.last_seen = datetime.datetime.utcnow()
    agent_create = AgentCreate.from_orm(record)
    record.governance_score = calculate_score(agent_create)
    db.commit()
    db.refresh(record)
    return record


@app.delete("/api/v1/agents/{agent_id}", status_code=204)
def delete_agent(agent_id: str, db: Session = Depends(get_db)):
    record = _get_or_404(db, agent_id)
    db.delete(record)
    db.commit()


@app.get("/api/v1/agents/{agent_id}/score", response_model=GovernanceReport)
def score_agent(agent_id: str, db: Session = Depends(get_db)):
    record = _get_or_404(db, agent_id)
    agent = AgentResponse.from_orm(record)
    return generate_report(agent)


@app.post("/api/v1/agents/batch", response_model=List[BatchResult], status_code=207)
def batch_register(bodies: List[AgentCreate], db: Session = Depends(get_db)):
    results = []
    for body in bodies:
        try:
            agent_id = _make_agent_id(body)
            existing = db.query(AgentRecord).filter_by(agent_id=agent_id).first()
            if existing:
                raise HTTPException(status_code=409, detail="Agent already registered")
            score = calculate_score(body)
            now = datetime.datetime.utcnow()
            data = body.dict(exclude_none=True)
            data.pop("agent_id", None)
            record = AgentRecord(agent_id=agent_id, governance_score=score, first_seen=now, last_seen=now, **data)
            db.add(record)
            db.commit()
            db.refresh(record)
            results.append(BatchResult(agent_id=agent_id, success=True, agent=AgentResponse.from_orm(record)))
        except HTTPException as e:
            results.append(BatchResult(agent_id="unknown", success=False, error=e.detail))
    return results


@app.get("/api/v1/health")
def health_check(db: Session = Depends(get_db)):
    count = db.query(AgentRecord).count()
    return {"status": "ok", "agent_count": count}


@app.get("/api/v1/summary")
def governance_summary(db: Session = Depends(get_db)):
    agents = db.query(AgentRecord).all()
    by_framework: dict = {}
    for a in agents:
        by_framework[a.framework] = by_framework.get(a.framework, 0) + 1
    avg_score = sum(a.governance_score for a in agents) / len(agents) if agents else 0.0
    below_50 = sum(1 for a in agents if a.governance_score < 50)
    return {
        "total": len(agents),
        "avg_score": round(avg_score, 1),
        "by_framework": by_framework,
        "below_50": below_50,
    }


class ScanRequest(BaseModel):
    path: str
    auto_register: bool = False


class ScanResult(BaseModel):
    scanned: int
    registered: int
    updated: int
    agents: list


@app.post("/api/v1/scan", response_model=ScanResult)
def scan_path(body: ScanRequest, db: Session = Depends(get_db)):
    scan_path = Path(body.path).expanduser().resolve()
    if not scan_path.exists():
        raise HTTPException(status_code=400, detail=f"Path does not exist: {body.path}")
    if not scan_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {body.path}")

    from ..scanner.detector import scan_directory
    fingerprints = scan_directory(scan_path)

    registered = 0
    updated = 0

    if body.auto_register:
        for fp in fingerprints:
            data = fp.to_agent_create()
            existing = db.query(AgentRecord).filter_by(agent_id=fp.agent_id).first()
            if existing:
                existing.last_seen = datetime.datetime.utcnow()
                db.commit()
                updated += 1
            else:
                ac = AgentCreate(**data)
                score = calculate_score(ac)
                now = datetime.datetime.utcnow()
                record = AgentRecord(governance_score=score, first_seen=now, last_seen=now, **data)
                db.add(record)
                db.commit()
                registered += 1

    return ScanResult(
        scanned=len(fingerprints),
        registered=registered,
        updated=updated,
        agents=[fp.to_dict() for fp in fingerprints],
    )


@app.get("/", response_class=HTMLResponse)
def dashboard():
    ui_path = Path(__file__).parent / "ui.html"
    return HTMLResponse(content=ui_path.read_text(encoding="utf-8"))
