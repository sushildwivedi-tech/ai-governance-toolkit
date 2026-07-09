from __future__ import annotations

import datetime
from typing import List, Optional

from governance_toolkit.registry.schemas import (
    AgentCreate,
    AgentResponse,
    EthicsReviewStatus,
    GovernanceCriterion,
    GovernanceReport,
)

ETHICS_REVIEW_EXPIRY_DAYS = 90

CRITERIA_SPEC = [
    {
        "key": "owner",
        "label": "Agent Owner Assigned",
        "points": 20,
        "description": "A named human owner is responsible for this agent.",
        "remediation": "Set the 'owner' field to a responsible engineer's email or username.",
    },
    {
        "key": "data_classification",
        "label": "Data Classification Set",
        "points": 20,
        "description": "Data sensitivity level is declared (public/internal/confidential/restricted).",
        "remediation": "Set 'data_classification' based on the most sensitive data the agent processes.",
    },
    {
        "key": "tools_scoped",
        "label": "Tool Permissions Scoped",
        "points": 20,
        "description": "The agent's tool list is explicitly enumerated (not wildcard/unlimited).",
        "remediation": "Declare specific tools in the 'tools' field. An empty tools list fails this check.",
    },
    {
        "key": "ethics_review",
        "label": "Ethics Review Current",
        "points": 20,
        "description": f"Agent has a 'passed' ethics review within the last {ETHICS_REVIEW_EXPIRY_DAYS} days.",
        "remediation": (
            "Complete an ethics/risk review, set ethics_review_status='passed', "
            "and provide the review date. Reviews expire every 90 days."
        ),
    },
    {
        "key": "audit_log",
        "label": "Audit Logging Configured",
        "points": 20,
        "description": "Audit logging is confirmed configured for this agent.",
        "remediation": "Configure audit logging and set 'audit_log_configured' to true.",
    },
]

RISK_SUMMARY = {
    (80, 100): "Governance-mature. Agent meets OWASP LLM maturity criteria for production.",
    (60, 79): "Governance-partial. Gaps present; remediate before expanding agent scope.",
    (40, 59): "Governance-immature. High-risk deployment; escalation to security team recommended.",
    (0, 39): "Governance-absent. Agent must not be in production until all criteria are met.",
}


def _check_owner(agent) -> bool:
    return bool(agent.owner and str(agent.owner).strip())


def _check_data_classification(agent) -> bool:
    return agent.data_classification is not None


def _check_tools_scoped(agent) -> bool:
    return bool(agent.tools and len(agent.tools) > 0)


def _check_ethics_review(agent) -> bool:
    if agent.ethics_review_status != EthicsReviewStatus.passed:
        return False
    if agent.ethics_review_date is None:
        return False
    age = (datetime.datetime.utcnow() - agent.ethics_review_date).days
    return age <= ETHICS_REVIEW_EXPIRY_DAYS


def _check_audit_log(agent) -> bool:
    return bool(agent.audit_log_configured)


_CHECK_MAP = {
    "owner": _check_owner,
    "data_classification": _check_data_classification,
    "tools_scoped": _check_tools_scoped,
    "ethics_review": _check_ethics_review,
    "audit_log": _check_audit_log,
}


def calculate_score(agent) -> float:
    total = 0
    for spec in CRITERIA_SPEC:
        fn = _CHECK_MAP[spec["key"]]
        if fn(agent):
            total += spec["points"]
    return float(total)


def _risk_summary_text(score: float) -> str:
    for (low, high), text in RISK_SUMMARY.items():
        if low <= int(score) <= high:
            return text
    return RISK_SUMMARY[(0, 39)]


def generate_report(agent: AgentResponse) -> GovernanceReport:
    criteria_results: List[GovernanceCriterion] = []
    for spec in CRITERIA_SPEC:
        fn = _CHECK_MAP[spec["key"]]
        passed = fn(agent)
        earned = spec["points"] if passed else 0
        criteria_results.append(
            GovernanceCriterion(
                criterion=spec["key"],
                label=spec["label"],
                points_possible=spec["points"],
                points_earned=earned,
                passed=passed,
                description=spec["description"],
                remediation=None if passed else spec["remediation"],
            )
        )

    total = sum(c.points_earned for c in criteria_results)
    recommendations = [
        spec["remediation"]
        for spec in CRITERIA_SPEC
        if not _CHECK_MAP[spec["key"]](agent)
    ]

    return GovernanceReport(
        agent_id=agent.agent_id,
        agent_name=agent.name,
        total_score=float(total),
        max_score=100,
        risk_summary=_risk_summary_text(float(total)),
        criteria=criteria_results,
        recommendations=recommendations,
    )
