from __future__ import annotations

"""Traceability status for registered (deployed) AI agents.

Identity is the first control for agentic AI: every other control
(human-in-the-loop, audit trails, evaluations) assumes you already know
which agent acted and under whose authority. This module derives a
traceability status from three signals — accountable owner, unique
identity, and action logging — and never lets it be set manually.
"""

TRACE_CHECKS = [
    {
        "key": "owner",
        "label": "Accountable owner",
        "description": "A named human is accountable for this agent.",
    },
    {
        "key": "identity",
        "label": "Unique identity",
        "description": "The agent has its own identity, not a shared or human account.",
    },
    {
        "key": "logging",
        "label": "Action logging",
        "description": "Agent actions are logged so they can be traced.",
    },
]


def _has_owner(agent) -> bool:
    return bool(getattr(agent, "owner_name", None) and str(agent.owner_name).strip())


def _has_identity(agent) -> bool:
    return bool(getattr(agent, "has_unique_identity", False))


def _has_logging(agent) -> bool:
    # Only full logging counts toward traceability; "partial"/"no" do not.
    return getattr(agent, "action_logging", None) == "yes"


_TRACE_CHECK_MAP = {
    "owner": _has_owner,
    "identity": _has_identity,
    "logging": _has_logging,
}


def trace_checks(agent) -> dict:
    """Return {check_key: bool} for the three traceability signals."""
    return {key: fn(agent) for key, fn in _TRACE_CHECK_MAP.items()}


def traceability_status(agent) -> str:
    """Derive green / amber / red from the three signals.

    green = all three present; amber = one missing; red = two or more missing.
    """
    missing = sum(1 for present in trace_checks(agent).values() if not present)
    if missing == 0:
        return "green"
    if missing == 1:
        return "amber"
    return "red"


def traceability_gaps(agent) -> list:
    """Human-readable labels of the missing traceability signals."""
    checks = trace_checks(agent)
    return [spec["label"] for spec in TRACE_CHECKS if not checks[spec["key"]]]
