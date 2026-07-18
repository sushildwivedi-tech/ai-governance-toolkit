from __future__ import annotations

import csv
import datetime
import hashlib
import io
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, Response
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
    RegisterSummary,
)
from ..scorer.owasp import calculate_score, generate_report
from ..scorer.traceability import traceability_status, trace_checks

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
    # Seed the accountability register with demo agents on a fresh file-backed
    # DB so the dashboard demonstrates on first load. In-memory DBs (tests) are
    # left untouched so the suite stays deterministic.
    from .db import _get_database_url
    if ":memory:" not in _get_database_url():
        from .seed import seed_register
        db = next(get_db())
        try:
            seed_register(db)
        finally:
            db.close()


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
    environment: Optional[str] = None,
    risk_tier: Optional[str] = None,
    status: Optional[str] = None,
    traceability: Optional[str] = None,
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
    if environment:
        q = q.filter(AgentRecord.environment == environment)
    if risk_tier:
        q = q.filter(AgentRecord.risk_tier == risk_tier)
    if status:
        q = q.filter(AgentRecord.status == status)
    records = q.order_by(AgentRecord.last_seen.desc()).offset(offset).limit(limit).all()
    if traceability:
        # traceability_status is a derived property, so filter in Python.
        records = [r for r in records if r.traceability_status == traceability]
    return records


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
    total = len(agents)
    avg_score = sum(a.governance_score for a in agents) / total if agents else 0.0
    below_50 = sum(1 for a in agents if a.governance_score < 50)

    # Accountability / traceability rollup.
    checks = [trace_checks(a) for a in agents]
    statuses = [a.traceability_status for a in agents]
    pct = lambda key: round(100.0 * sum(1 for c in checks if c[key]) / total, 0) if total else 0.0
    traceability = RegisterSummary(
        total=total,
        pct_with_owner=pct("owner"),
        pct_with_identity=pct("identity"),
        pct_with_logging=pct("logging"),
        red_count=statuses.count("red"),
        amber_count=statuses.count("amber"),
        green_count=statuses.count("green"),
    )
    return {
        "total": total,
        "avg_score": round(avg_score, 1),
        "by_framework": by_framework,
        "below_50": below_50,
        "traceability": traceability.dict(),
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


_CSV_COLUMNS = [
    "agent_id", "name", "framework", "vendor", "environment", "status",
    "governance_score", "traceability_status", "traceability_gaps",
    "owner", "owner_role", "owner_contact", "has_unique_identity",
    "identity_provider", "credential_scope", "last_credential_rotation",
    "autonomy_level", "risk_tier", "permitted_actions", "action_logging",
    "log_location", "last_audit_review", "deployment_date", "description",
]


@app.get("/api/v1/export.csv")
def export_agents_csv(db: Session = Depends(get_db)):
    records = db.query(AgentRecord).order_by(AgentRecord.name.asc()).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(_CSV_COLUMNS)
    for r in records:
        writer.writerow([
            r.agent_id, r.name, r.framework or "", r.vendor or "",
            r.environment or "", r.status, r.governance_score,
            r.traceability_status, "; ".join(r.traceability_gaps),
            r.owner or "", r.owner_role or "", r.owner_contact or "",
            r.has_unique_identity, r.identity_provider or "",
            r.credential_scope or "", r.last_credential_rotation or "",
            r.autonomy_level or "", r.risk_tier or "",
            "; ".join(r.permitted_actions or []), r.action_logging,
            r.log_location or "", r.last_audit_review or "",
            r.deployment_date or "", r.description or "",
        ])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=agent_registry.csv"},
    )


@app.get("/", response_class=HTMLResponse)
def dashboard():
    ui_path = Path(__file__).parent / "ui.html"
    return HTMLResponse(content=ui_path.read_text(encoding="utf-8"))


@app.get("/design-gate", include_in_schema=False)
def design_gate():
    # The gate now lives on the dashboard's Pre-Build tab; keep old links working.
    return RedirectResponse(url="/#pre-build")
