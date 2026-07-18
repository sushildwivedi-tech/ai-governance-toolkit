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


class RegisteredAgent(Base):
    """Post-deployment accountability register for a running AI agent.

    Metadata only — this is a register, not an IAM system. It never stores
    credentials, secrets or tokens, only descriptive fields about them.
    """

    __tablename__ = "registered_agents"

    agent_id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    vendor = Column(String(100), nullable=True)
    environment = Column(String(20), nullable=True)
    deployment_date = Column(DateTime, nullable=True)
    status = Column(String(20), default="active", nullable=False)

    # Accountability — the point of the register.
    owner_name = Column(String(255), nullable=True)
    owner_role = Column(String(255), nullable=True)
    owner_contact = Column(String(255), nullable=True)

    # Identity (descriptive metadata only — never credential values).
    has_unique_identity = Column(Boolean, default=False, nullable=False)
    identity_provider = Column(String(255), nullable=True)
    credential_scope = Column(Text, nullable=True)
    last_credential_rotation = Column(DateTime, nullable=True)

    # Autonomy / risk.
    autonomy_level = Column(String(30), nullable=True)
    risk_tier = Column(String(20), nullable=True)
    permitted_actions = Column(JSON, default=list)

    # Audit.
    action_logging = Column(String(10), default="no", nullable=False)
    log_location = Column(String(255), nullable=True)
    last_audit_review = Column(DateTime, nullable=True)
    audit_notes = Column(JSON, default=list)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
