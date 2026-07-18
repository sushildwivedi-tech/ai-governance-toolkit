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


class AgentCreate(BaseModel):
    agent_id: Optional[str] = None
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


# --------------------------------------------------------------------------- #
# Agent Register (post-deployment accountability). Metadata only — never       #
# stores credentials, secrets or tokens.                                       #
# --------------------------------------------------------------------------- #


class Environment(str, Enum):
    prod = "prod"
    staging = "staging"
    dev = "dev"


class AgentStatus(str, Enum):
    active = "active"
    paused = "paused"
    retired = "retired"


class AutonomyLevel(str, Enum):
    suggest_only = "suggest_only"
    act_with_approval = "act_with_approval"
    act_autonomously = "act_autonomously"


class ActionLogging(str, Enum):
    yes = "yes"
    no = "no"
    partial = "partial"


class AuditNote(BaseModel):
    timestamp: datetime.datetime
    note: str


class RegisteredAgentCreate(BaseModel):
    agent_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    vendor: Optional[str] = None
    environment: Optional[Environment] = None
    deployment_date: Optional[datetime.datetime] = None
    status: AgentStatus = AgentStatus.active

    owner_name: Optional[str] = None
    owner_role: Optional[str] = None
    owner_contact: Optional[str] = None

    has_unique_identity: bool = False
    identity_provider: Optional[str] = None
    credential_scope: Optional[str] = None
    last_credential_rotation: Optional[datetime.datetime] = None

    autonomy_level: Optional[AutonomyLevel] = None
    risk_tier: Optional[RiskTier] = None
    permitted_actions: Optional[List[str]] = None

    action_logging: ActionLogging = ActionLogging.no
    log_location: Optional[str] = None
    last_audit_review: Optional[datetime.datetime] = None
    audit_notes: Optional[List[AuditNote]] = None

    class Config:
        orm_mode = True


class RegisteredAgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    vendor: Optional[str] = None
    environment: Optional[Environment] = None
    deployment_date: Optional[datetime.datetime] = None
    status: Optional[AgentStatus] = None

    owner_name: Optional[str] = None
    owner_role: Optional[str] = None
    owner_contact: Optional[str] = None

    has_unique_identity: Optional[bool] = None
    identity_provider: Optional[str] = None
    credential_scope: Optional[str] = None
    last_credential_rotation: Optional[datetime.datetime] = None

    autonomy_level: Optional[AutonomyLevel] = None
    risk_tier: Optional[RiskTier] = None
    permitted_actions: Optional[List[str]] = None

    action_logging: Optional[ActionLogging] = None
    log_location: Optional[str] = None
    last_audit_review: Optional[datetime.datetime] = None
    audit_notes: Optional[List[AuditNote]] = None

    class Config:
        orm_mode = True


class RegisteredAgentResponse(BaseModel):
    agent_id: str
    name: str
    description: Optional[str] = None
    vendor: Optional[str] = None
    environment: Optional[str] = None
    deployment_date: Optional[datetime.datetime] = None
    status: str = "active"

    owner_name: Optional[str] = None
    owner_role: Optional[str] = None
    owner_contact: Optional[str] = None

    has_unique_identity: bool = False
    identity_provider: Optional[str] = None
    credential_scope: Optional[str] = None
    last_credential_rotation: Optional[datetime.datetime] = None

    autonomy_level: Optional[str] = None
    risk_tier: Optional[str] = None
    permitted_actions: Optional[List[str]] = None

    action_logging: str = "no"
    log_location: Optional[str] = None
    last_audit_review: Optional[datetime.datetime] = None
    audit_notes: Optional[List[AuditNote]] = None

    created_at: datetime.datetime
    updated_at: datetime.datetime

    # Derived server-side, never set manually.
    traceability_status: str = "red"
    traceability_gaps: List[str] = []

    class Config:
        orm_mode = True


class RegisterSummary(BaseModel):
    total: int
    pct_with_owner: float
    pct_with_identity: float
    pct_with_logging: float
    red_count: int
    amber_count: int
    green_count: int
