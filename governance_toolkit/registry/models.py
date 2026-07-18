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

from ..scorer.traceability import traceability_status, traceability_gaps

Base = declarative_base()


class AgentRecord(Base):
    """A single AI agent in the unified registry.

    Carries both its OWASP governance score (from data/tools/ethics/audit
    fields) and its post-deployment accountability metadata (owner, identity,
    audit posture) from which a green/amber/red traceability status is derived.

    Metadata only — this is a register, not an IAM system. It never stores
    credentials, secrets or tokens, only descriptive fields about them.
    """

    __tablename__ = "agents"

    agent_id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    framework = Column(String(50), nullable=False, default="unknown")
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

    # --- Accountability register (post-deployment) ---
    description = Column(Text, nullable=True)
    vendor = Column(String(100), nullable=True)
    environment = Column(String(20), nullable=True)
    deployment_date = Column(DateTime, nullable=True)
    status = Column(String(20), default="active", nullable=False)

    # Accountable owner: `owner` (above) is the named human; role/contact below.
    owner_role = Column(String(255), nullable=True)
    owner_contact = Column(String(255), nullable=True)

    # Identity (descriptive metadata only — never credential values).
    has_unique_identity = Column(Boolean, default=False, nullable=False)
    identity_provider = Column(String(255), nullable=True)
    credential_scope = Column(Text, nullable=True)
    last_credential_rotation = Column(DateTime, nullable=True)

    # Autonomy.
    autonomy_level = Column(String(30), nullable=True)
    permitted_actions = Column(JSON, default=list)

    # Audit.
    action_logging = Column(String(10), default="no", nullable=False)
    log_location = Column(String(255), nullable=True)
    last_audit_review = Column(DateTime, nullable=True)
    audit_notes = Column(JSON, default=list)

    first_seen = Column(DateTime, server_default=func.now(), nullable=False)
    last_seen = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    @property
    def traceability_status(self) -> str:
        """Derived green/amber/red — never set manually."""
        return traceability_status(self)

    @property
    def traceability_gaps(self) -> list:
        return traceability_gaps(self)
