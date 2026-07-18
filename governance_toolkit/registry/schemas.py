from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, validator


class Framework(str, Enum):
    anthropic_claude = "anthropic_claude"
    langchain = "langchain"
    langgraph = "langgraph"
    crewai = "crewai"
    autogpt = "autogpt"
    unknown = "unknown"


class RiskTier(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class EthicsReviewStatus(str, Enum):
    pending = "pending"
    in_review = "in_review"
    passed = "passed"
    failed = "failed"
    not_required = "not_required"


class DataClassification(str, Enum):
    public = "public"
    internal = "internal"
    confidential = "confidential"
    restricted = "restricted"


class AuditNote(BaseModel):
    # ISO-8601 string, not a datetime: audit_notes is a JSON column, so the
    # value must stay JSON-serializable when written.
    timestamp: str
    note: str


class AgentCreate(BaseModel):
    agent_id: Optional[str] = None
    name: str
    framework: Optional[str] = "unknown"
    model: Optional[str] = None
    tools: Optional[List[str]] = None
    owner: Optional[str] = None
    file_path: Optional[str] = None
    data_classification: Optional[str] = None
    risk_tier: Optional[str] = None
    ethics_review_status: Optional[str] = None
    ethics_review_date: Optional[datetime.datetime] = None
    audit_log_configured: Optional[bool] = False

    # Accountability register (metadata only — never credential values).
    description: Optional[str] = None
    vendor: Optional[str] = None
    environment: Optional[str] = None
    deployment_date: Optional[datetime.datetime] = None
    status: Optional[str] = "active"
    owner_role: Optional[str] = None
    owner_contact: Optional[str] = None
    has_unique_identity: Optional[bool] = False
    identity_provider: Optional[str] = None
    credential_scope: Optional[str] = None
    last_credential_rotation: Optional[datetime.datetime] = None
    autonomy_level: Optional[str] = None
    permitted_actions: Optional[List[str]] = None
    action_logging: Optional[str] = "no"
    log_location: Optional[str] = None
    last_audit_review: Optional[datetime.datetime] = None
    audit_notes: Optional[List[AuditNote]] = None

    class Config:
        orm_mode = True


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    framework: Optional[str] = None
    model: Optional[str] = None
    tools: Optional[List[str]] = None
    owner: Optional[str] = None
    file_path: Optional[str] = None
    data_classification: Optional[str] = None
    risk_tier: Optional[str] = None
    ethics_review_status: Optional[str] = None
    ethics_review_date: Optional[datetime.datetime] = None
    audit_log_configured: Optional[bool] = None

    description: Optional[str] = None
    vendor: Optional[str] = None
    environment: Optional[str] = None
    deployment_date: Optional[datetime.datetime] = None
    status: Optional[str] = None
    owner_role: Optional[str] = None
    owner_contact: Optional[str] = None
    has_unique_identity: Optional[bool] = None
    identity_provider: Optional[str] = None
    credential_scope: Optional[str] = None
    last_credential_rotation: Optional[datetime.datetime] = None
    autonomy_level: Optional[str] = None
    permitted_actions: Optional[List[str]] = None
    action_logging: Optional[str] = None
    log_location: Optional[str] = None
    last_audit_review: Optional[datetime.datetime] = None
    audit_notes: Optional[List[AuditNote]] = None

    class Config:
        orm_mode = True


class AgentResponse(BaseModel):
    agent_id: str
    name: str
    framework: str
    model: Optional[str] = None
    tools: Optional[List[str]] = None
    owner: Optional[str] = None
    file_path: Optional[str] = None
    data_classification: Optional[str] = None
    risk_tier: Optional[str] = None
    ethics_review_status: Optional[str] = None
    ethics_review_date: Optional[datetime.datetime] = None
    audit_log_configured: Optional[bool] = False
    governance_score: float = 0.0

    description: Optional[str] = None
    vendor: Optional[str] = None
    environment: Optional[str] = None
    deployment_date: Optional[datetime.datetime] = None
    status: Optional[str] = "active"
    owner_role: Optional[str] = None
    owner_contact: Optional[str] = None
    has_unique_identity: Optional[bool] = False
    identity_provider: Optional[str] = None
    credential_scope: Optional[str] = None
    last_credential_rotation: Optional[datetime.datetime] = None
    autonomy_level: Optional[str] = None
    permitted_actions: Optional[List[str]] = None
    action_logging: Optional[str] = "no"
    log_location: Optional[str] = None
    last_audit_review: Optional[datetime.datetime] = None
    audit_notes: Optional[List[AuditNote]] = None

    # Derived, never set manually.
    traceability_status: str = "red"
    traceability_gaps: List[str] = []

    first_seen: datetime.datetime
    last_seen: datetime.datetime

    class Config:
        orm_mode = True


class GovernanceCriterion(BaseModel):
    criterion: str
    label: str
    points_possible: int
    points_earned: int
    passed: bool
    description: str
    remediation: Optional[str] = None


class GovernanceReport(BaseModel):
    agent_id: str
    agent_name: str
    total_score: float
    max_score: int = 100
    risk_summary: str
    criteria: List[GovernanceCriterion]
    recommendations: List[str]


class BatchResult(BaseModel):
    agent_id: str
    success: bool
    agent: Optional[AgentResponse] = None
    error: Optional[str] = None


class RegisterSummary(BaseModel):
    """Accountability/traceability rollup, returned alongside the OWASP summary."""

    total: int
    pct_with_owner: float
    pct_with_identity: float
    pct_with_logging: float
    red_count: int
    amber_count: int
    green_count: int
