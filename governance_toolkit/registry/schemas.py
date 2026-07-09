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
