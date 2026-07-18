from __future__ import annotations

"""Demo seed data for the unified agent registry.

Ten realistic deployed agents spread across statuses, environments, vendors and
frameworks — including at least two red- and three amber-traceability agents,
and a range of OWASP governance scores — so the dashboard demonstrates well on
first load. Metadata only: nothing here is or resembles a real credential,
secret or token.
"""

import datetime
import hashlib

from .models import AgentRecord
from .schemas import AgentCreate
from ..scorer.owasp import calculate_score


def _dt(y, m, d) -> datetime.datetime:
    return datetime.datetime(y, m, d)


def _note(y, m, d, text) -> dict:
    return {"timestamp": _dt(y, m, d).isoformat(), "note": text}


# Each entry is metadata about a deployed agent. credential_scope is a plain
# description of what the agent's identity may do — never a value. tools /
# data_classification / ethics fields feed the OWASP score; owner / identity /
# action_logging feed the derived traceability status.
DEMO_AGENTS = [
    {
        "name": "Customer Support Copilot",
        "framework": "anthropic_claude",
        "description": "Drafts and (with approval) sends replies in the support inbox.",
        "vendor": "Copilot",
        "environment": "prod",
        "deployment_date": _dt(2025, 11, 3),
        "status": "active",
        "owner": "Priya Nair",
        "owner_role": "Head of Customer Experience",
        "owner_contact": "priya.nair@example.com",
        "has_unique_identity": True,
        "identity_provider": "Microsoft Entra ID (workload identity)",
        "credential_scope": "Read/write to support mailbox and ticketing API only.",
        "last_credential_rotation": _dt(2026, 6, 1),
        "autonomy_level": "act_with_approval",
        "risk_tier": "medium",
        "permitted_actions": ["read_tickets", "draft_reply", "send_reply(approved)"],
        "tools": ["read_tickets", "draft_reply", "send_reply"],
        "data_classification": "confidential",
        "ethics_review_status": "passed",
        "ethics_review_date": _dt(2026, 6, 15),
        "action_logging": "yes",
        "log_location": "Splunk — index=agents_support",
        "last_audit_review": _dt(2026, 6, 15),
        "audit_notes": [_note(2026, 6, 15, "Quarterly review — logging and approval gate verified.")],
    },
    {
        "name": "Invoice Reconciliation Agent",
        "framework": "langchain",
        "description": "Matches invoices to purchase orders and flags exceptions.",
        "vendor": "internal",
        "environment": "prod",
        "deployment_date": _dt(2025, 9, 20),
        "status": "active",
        "owner": "Marcus Bell",
        "owner_role": "Finance Systems Lead",
        "owner_contact": "marcus.bell@example.com",
        "has_unique_identity": True,
        "identity_provider": "Okta service principal",
        "credential_scope": "Read-only to ERP invoices/POs; write to exceptions queue.",
        "last_credential_rotation": _dt(2026, 5, 12),
        "autonomy_level": "act_autonomously",
        "risk_tier": "high",
        "permitted_actions": ["read_invoices", "read_purchase_orders", "write_exception"],
        "tools": ["read_invoices", "read_purchase_orders", "write_exception"],
        "data_classification": "confidential",
        "ethics_review_status": "passed",
        "ethics_review_date": _dt(2026, 5, 30),
        "action_logging": "yes",
        "log_location": "ERP audit log + Datadog",
        "last_audit_review": _dt(2026, 5, 30),
        "audit_notes": [_note(2026, 5, 30, "Autonomy justified by full logging and read-mostly scope.")],
    },
    {
        "name": "Sales Email Drafter",
        "framework": "langgraph",
        "description": "Suggests personalised outreach drafts for reps to review.",
        "vendor": "custom LangGraph",
        "environment": "prod",
        "deployment_date": _dt(2026, 1, 14),
        "status": "active",
        "owner": "Elena Torres",
        "owner_role": "Revenue Operations Manager",
        "owner_contact": "elena.torres@example.com",
        "has_unique_identity": True,
        "identity_provider": "Custom OAuth client (per-agent)",
        "credential_scope": "Read CRM contacts; no send capability.",
        "last_credential_rotation": _dt(2026, 6, 20),
        "autonomy_level": "suggest_only",
        "risk_tier": "low",
        "permitted_actions": ["read_crm_contacts", "draft_email"],
        "tools": ["read_crm_contacts", "draft_email"],
        "data_classification": "internal",
        "ethics_review_status": "passed",
        "ethics_review_date": _dt(2026, 6, 25),
        "action_logging": "yes",
        "log_location": "CloudWatch — /agents/sales-drafter",
        "last_audit_review": _dt(2026, 6, 25),
        "audit_notes": [_note(2026, 6, 25, "Suggest-only; low risk confirmed.")],
    },
    {
        "name": "Beta Chat Widget Agent",
        "framework": "anthropic_claude",
        "description": "Retired pilot chatbot for the marketing site.",
        "vendor": "internal",
        "environment": "dev",
        "deployment_date": _dt(2025, 6, 2),
        "status": "retired",
        "owner": "Sam Okafor",
        "owner_role": "Web Platform Engineer",
        "owner_contact": "sam.okafor@example.com",
        "has_unique_identity": True,
        "identity_provider": "Microsoft Entra ID (workload identity)",
        "credential_scope": "Read-only public FAQ content.",
        "last_credential_rotation": _dt(2025, 6, 2),
        "autonomy_level": "suggest_only",
        "risk_tier": "low",
        "permitted_actions": ["read_faq"],
        "tools": ["read_faq"],
        "data_classification": "public",
        "ethics_review_status": "not_required",
        "ethics_review_date": None,
        "action_logging": "yes",
        "log_location": "CloudWatch — /agents/beta-widget",
        "last_audit_review": _dt(2025, 12, 1),
        "audit_notes": [_note(2025, 12, 1, "Pilot closed; agent decommissioned and identity revoked.")],
    },
    {
        "name": "Knowledge Base Summariser",
        "framework": "langchain",
        "description": "Summarises long internal docs for the intranet.",
        "vendor": "internal",
        "environment": "staging",
        "deployment_date": _dt(2026, 2, 10),
        "status": "active",
        "owner": "Hana Lindqvist",
        "owner_role": "Knowledge Manager",
        "owner_contact": "hana.lindqvist@example.com",
        "has_unique_identity": False,  # shares a team service account — traceability gap
        "identity_provider": "Shared team service account",
        "credential_scope": "Read-only to Confluence spaces (shared account).",
        "last_credential_rotation": None,
        "autonomy_level": "suggest_only",
        "risk_tier": "low",
        "permitted_actions": ["read_confluence", "summarise"],
        "tools": ["read_confluence", "summarise"],
        "data_classification": "internal",
        "ethics_review_status": "pending",
        "ethics_review_date": None,
        "action_logging": "yes",
        "log_location": "Confluence access log",
        "last_audit_review": _dt(2026, 4, 2),
        "audit_notes": [_note(2026, 4, 2, "Flagged: runs under a shared account — needs its own identity.")],
    },
    {
        "name": "Recruitment Screening Assistant",
        "framework": "anthropic_claude",
        "description": "Pre-screens applications against role criteria.",
        "vendor": "Copilot",
        "environment": "prod",
        "deployment_date": _dt(2026, 3, 5),
        "status": "active",
        "owner": "David Cho",
        "owner_role": "Talent Acquisition Lead",
        "owner_contact": "david.cho@example.com",
        "has_unique_identity": True,
        "identity_provider": "Microsoft Entra ID (workload identity)",
        "credential_scope": "Read-only to ATS candidate records.",
        "last_credential_rotation": _dt(2026, 3, 5),
        "autonomy_level": "act_with_approval",
        "risk_tier": "high",
        "permitted_actions": ["read_applications", "score_candidate"],
        "tools": ["read_applications", "score_candidate"],
        "data_classification": "restricted",
        "ethics_review_status": "passed",
        "ethics_review_date": _dt(2026, 4, 18),
        "action_logging": "partial",  # only errors logged — traceability gap
        "log_location": "App logs (errors only)",
        "last_audit_review": _dt(2026, 4, 18),
        "audit_notes": [_note(2026, 4, 18, "Logging is partial (errors only); full action logging required given HR data.")],
    },
    {
        "name": "DevOps Incident Triage Bot",
        "framework": "langgraph",
        "description": "Triages alerts and proposes runbook steps in the on-call channel.",
        "vendor": "custom LangGraph",
        "environment": "prod",
        "deployment_date": _dt(2025, 12, 8),
        "status": "active",
        "owner": "Ravi Menon",
        "owner_role": "SRE Team Lead",
        "owner_contact": "ravi.menon@example.com",
        "has_unique_identity": True,
        "identity_provider": "Custom OAuth client (per-agent)",
        "credential_scope": "Read alerts; post to on-call Slack; no infra write.",
        "last_credential_rotation": _dt(2026, 2, 1),
        "autonomy_level": "act_with_approval",
        "risk_tier": "medium",
        "permitted_actions": ["read_alerts", "post_slack", "suggest_runbook"],
        "tools": ["read_alerts", "post_slack", "suggest_runbook"],
        "data_classification": "internal",
        "ethics_review_status": "in_review",
        "ethics_review_date": None,
        "action_logging": "no",  # not yet wired up — traceability gap
        "log_location": "",
        "last_audit_review": _dt(2026, 3, 22),
        "audit_notes": [_note(2026, 3, 22, "Action logging not yet configured — tracked as remediation item.")],
    },
    {
        "name": "Marketing Content Generator",
        "framework": "unknown",
        "description": "Generates campaign copy and social posts.",
        "vendor": "internal",
        "environment": "dev",
        "deployment_date": _dt(2026, 4, 28),
        "status": "active",
        "owner": None,  # no accountable owner — traceability gap
        "owner_role": None,
        "owner_contact": None,
        "has_unique_identity": False,  # runs under a developer's personal token
        "identity_provider": "Developer personal account",
        "credential_scope": "Whatever the developer's account can reach (unscoped).",
        "last_credential_rotation": None,
        "autonomy_level": "act_autonomously",
        "risk_tier": "medium",
        "permitted_actions": ["generate_copy", "post_social(draft)"],
        "tools": [],
        "data_classification": None,
        "ethics_review_status": None,
        "ethics_review_date": None,
        "action_logging": "no",  # no logging — traceability gap
        "log_location": "",
        "last_audit_review": None,
        "audit_notes": [_note(2026, 5, 5, "Discovered in shadow-IT sweep — no owner, no unique identity, no logging.")],
    },
    {
        "name": "Legacy Data Migration Agent",
        "framework": "autogpt",
        "description": "One-off bulk migration between two data warehouses.",
        "vendor": "internal",
        "environment": "prod",
        "deployment_date": _dt(2025, 10, 1),
        "status": "paused",
        "owner": None,  # owner left the company — traceability gap
        "owner_role": None,
        "owner_contact": None,
        "has_unique_identity": False,  # shared migration service account
        "identity_provider": "Shared migration service account",
        "credential_scope": "Read/write to both warehouses (broad).",
        "last_credential_rotation": None,
        "autonomy_level": "act_autonomously",
        "risk_tier": "critical",
        "permitted_actions": ["read_warehouse_a", "write_warehouse_b", "bulk_transform"],
        "tools": ["read_warehouse_a", "write_warehouse_b", "bulk_transform"],
        "data_classification": "restricted",
        "ethics_review_status": "failed",
        "ethics_review_date": _dt(2025, 10, 1),
        "action_logging": "partial",
        "log_location": "Warehouse job history",
        "last_audit_review": _dt(2026, 1, 10),
        "audit_notes": [_note(2026, 1, 10, "Owner departed; paused pending reassignment and a dedicated identity.")],
    },
    {
        "name": "Procurement Negotiation Agent",
        "framework": "langgraph",
        "description": "Drafts supplier negotiation messages and counter-offers.",
        "vendor": "custom LangGraph",
        "environment": "staging",
        "deployment_date": _dt(2026, 5, 19),
        "status": "active",
        "owner": "Ngozi Adeyemi",
        "owner_role": "Procurement Manager",
        "owner_contact": "ngozi.adeyemi@example.com",
        "has_unique_identity": False,  # shared account — traceability gap
        "identity_provider": "Shared procurement service account",
        "credential_scope": "Read supplier records; draft messages (shared account).",
        "last_credential_rotation": None,
        "autonomy_level": "act_with_approval",
        "risk_tier": "high",
        "permitted_actions": ["read_suppliers", "draft_message", "propose_counter_offer"],
        "tools": ["read_suppliers", "draft_message", "propose_counter_offer"],
        "data_classification": "confidential",
        "ethics_review_status": "pending",
        "ethics_review_date": None,
        "action_logging": "no",  # traceability gap
        "log_location": "",
        "last_audit_review": None,
        "audit_notes": [_note(2026, 6, 3, "Needs its own identity and action logging before any prod promotion.")],
    },
]


def _agent_id(name: str, framework: str) -> str:
    return hashlib.sha256(f"{name}:{framework}".encode()).hexdigest()[:32]


def seed_register(db, force: bool = False) -> int:
    """Insert demo agents if the registry is empty (or force=True). Returns count inserted."""
    if not force and db.query(AgentRecord).count() > 0:
        return 0
    now = datetime.datetime.utcnow()
    inserted = 0
    for spec in DEMO_AGENTS:
        agent_id = _agent_id(spec["name"], spec["framework"])
        if db.query(AgentRecord).filter_by(agent_id=agent_id).first():
            continue
        data = dict(spec)
        # Keep the OWASP audit criterion consistent with the richer action_logging field.
        data["audit_log_configured"] = data.get("action_logging") == "yes"
        score = calculate_score(AgentCreate(**data))
        db.add(AgentRecord(
            agent_id=agent_id,
            governance_score=score,
            first_seen=now,
            last_seen=now,
            **data,
        ))
        inserted += 1
    db.commit()
    return inserted
