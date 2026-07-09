from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class AgentRecord(Base):
    __tablename__ = "agents"

    agent_id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    framework = Column(String(50), nullable=False)
    model = Column(String(100), nullable=True)
    tools = Column(JSON, default=list)
    owner = Column(String(255), nullable=True)
    file_path = Column(Text, nullable=True)
    data_classification = Column(String(50), nullable=True)
    risk_tier = Column(String(20), nullable=True)
    ethics_review_status = Column(String(20), nullable=True)
    ethics_review_date = Column(DateTime, nullable=True)
    audit_log_configured = Column(Boolean, default=False, nullable=False)
    governance_score = Column(Float, default=0.0, nullable=False)
    first_seen = Column(DateTime, server_default=func.now(), nullable=False)
    last_seen = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
