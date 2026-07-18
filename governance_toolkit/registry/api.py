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
from .models import AgentRecord, RegisteredAgent
from .schemas import (
    AgentCreate,
    AgentResponse,
    AgentUpdate,
    BatchResult,
    GovernanceReport,
    RegisteredAgentCreate,
    RegisteredAgentResponse,
    RegisteredAgentUpdate,
    RegisterSummary,
)
from ..scorer.owasp import calculate_score, generate_report
from ..scorer.traceability import traceability_status, traceability_gaps, trace_checks

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


# --------------------------------------------------------------------------- #
# Agent Register — post-deployment accountability & traceability.              #
# Metadata only: no credentials, secrets or tokens are ever stored.            #
# --------------------------------------------------------------------------- #


def _make_registered_agent_id(body: RegisteredAgentCreate) -> str:
    if body.agent_id:
        return body.agent_id
    raw = f"{body.name}:{body.vendor or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _registered_response(record: RegisteredAgent) -> RegisteredAgentResponse:
    resp = RegisteredAgentResponse.from_orm(record)
    resp.traceability_status = traceability_status(record)
    resp.traceability_gaps = traceability_gaps(record)
    return resp


def _get_registered_or_404(db: Session, agent_id: str) -> RegisteredAgent:
    record = db.query(RegisteredAgent).filter_by(agent_id=agent_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Registered agent '{agent_id}' not found")
    return record


@app.post("/api/v1/register/agents", response_model=RegisteredAgentResponse, status_code=201)
def create_registered_agent(body: RegisteredAgentCreate, db: Session = Depends(get_db)):
    agent_id = _make_registered_agent_id(body)
    if db.query(RegisteredAgent).filter_by(agent_id=agent_id).first():
        raise HTTPException(status_code=409, detail="Agent already in register")

    data = body.dict(exclude_none=True)
    data.pop("agent_id", None)
    record = RegisteredAgent(agent_id=agent_id, **data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return _registered_response(record)


@app.get("/api/v1/register/agents", response_model=List[RegisteredAgentResponse])
def list_registered_agents(
    environment: Optional[str] = None,
    risk_tier: Optional[str] = None,
    status: Optional[str] = None,
    owner: Optional[str] = None,
    traceability: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(RegisteredAgent)
    if environment:
        q = q.filter(RegisteredAgent.environment == environment)
    if risk_tier:
        q = q.filter(RegisteredAgent.risk_tier == risk_tier)
    if status:
        q = q.filter(RegisteredAgent.status == status)
    if owner:
        q = q.filter(RegisteredAgent.owner_name == owner)
    records = q.order_by(RegisteredAgent.name.asc()).all()
    responses = [_registered_response(r) for r in records]
    if traceability:
        responses = [r for r in responses if r.traceability_status == traceability]
    return responses


@app.get("/api/v1/register/summary", response_model=RegisterSummary)
def register_summary(db: Session = Depends(get_db)):
    records = db.query(RegisteredAgent).all()
    total = len(records)
    if total == 0:
        return RegisterSummary(
            total=0, pct_with_owner=0.0, pct_with_identity=0.0,
            pct_with_logging=0.0, red_count=0, amber_count=0, green_count=0,
        )
    checks = [trace_checks(r) for r in records]
    statuses = [traceability_status(r) for r in records]
    pct = lambda key: round(100.0 * sum(1 for c in checks if c[key]) / total, 0)
    return RegisterSummary(
        total=total,
        pct_with_owner=pct("owner"),
        pct_with_identity=pct("identity"),
        pct_with_logging=pct("logging"),
        red_count=statuses.count("red"),
        amber_count=statuses.count("amber"),
        green_count=statuses.count("green"),
    )


@app.get("/api/v1/register/agents/{agent_id}", response_model=RegisteredAgentResponse)
def get_registered_agent(agent_id: str, db: Session = Depends(get_db)):
    return _registered_response(_get_registered_or_404(db, agent_id))


@app.patch("/api/v1/register/agents/{agent_id}", response_model=RegisteredAgentResponse)
def update_registered_agent(agent_id: str, body: RegisteredAgentUpdate, db: Session = Depends(get_db)):
    record = _get_registered_or_404(db, agent_id)
    for field_name, value in body.dict(exclude_unset=True).items():
        setattr(record, field_name, value)
    db.commit()
    db.refresh(record)
    return _registered_response(record)


@app.delete("/api/v1/register/agents/{agent_id}", status_code=204)
def delete_registered_agent(agent_id: str, db: Session = Depends(get_db)):
    record = _get_registered_or_404(db, agent_id)
    db.delete(record)
    db.commit()


_CSV_COLUMNS = [
    "agent_id", "name", "description", "vendor", "environment", "deployment_date",
    "status", "traceability_status", "traceability_gaps", "owner_name", "owner_role",
    "owner_contact", "has_unique_identity", "identity_provider", "credential_scope",
    "last_credential_rotation", "autonomy_level", "risk_tier", "permitted_actions",
    "action_logging", "log_location", "last_audit_review",
]


@app.get("/api/v1/register/export.csv")
def export_register_csv(db: Session = Depends(get_db)):
    records = db.query(RegisteredAgent).order_by(RegisteredAgent.name.asc()).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(_CSV_COLUMNS)
    for r in records:
        resp = _registered_response(r)
        writer.writerow([
            resp.agent_id, resp.name, resp.description or "", resp.vendor or "",
            resp.environment or "", resp.deployment_date or "", resp.status,
            resp.traceability_status, "; ".join(resp.traceability_gaps),
            resp.owner_name or "", resp.owner_role or "", resp.owner_contact or "",
            resp.has_unique_identity, resp.identity_provider or "",
            resp.credential_scope or "", resp.last_credential_rotation or "",
            resp.autonomy_level or "", resp.risk_tier or "",
            "; ".join(resp.permitted_actions or []), resp.action_logging,
            resp.log_location or "", resp.last_audit_review or "",
        ])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=agent_register.csv"},
    )


@app.get("/", response_class=HTMLResponse)
def dashboard():
    ui_path = Path(__file__).parent / "ui.html"
    return HTMLResponse(content=ui_path.read_text(encoding="utf-8"))


@app.get("/design-gate", include_in_schema=False)
def design_gate():
    # The gate now lives on the dashboard's Pre-Build tab; keep old links working.
    return RedirectResponse(url="/#pre-build")
