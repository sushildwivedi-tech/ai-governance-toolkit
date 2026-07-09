from __future__ import annotations

import datetime
import pytest

from governance_toolkit.scorer.owasp import calculate_score, generate_report
from governance_toolkit.registry.schemas import AgentCreate, AgentResponse, EthicsReviewStatus


def _make_response(**kwargs) -> AgentResponse:
    defaults = {
        "agent_id": "test-id-001",
        "name": "test-agent",
        "framework": "anthropic_claude",
        "governance_score": 0.0,
        "first_seen": datetime.datetime.utcnow(),
        "last_seen": datetime.datetime.utcnow(),
    }
    defaults.update(kwargs)
    return AgentResponse(**defaults)


def test_perfect_score(sample_agent_data):
    agent = AgentCreate(**sample_agent_data)
    assert calculate_score(agent) == 100.0


def test_zero_score():
    agent = AgentCreate(name="bare", framework="unknown")
    assert calculate_score(agent) == 0.0


def test_owner_criterion():
    agent_no_owner = AgentCreate(name="t", framework="unknown")
    agent_with_owner = AgentCreate(name="t", framework="unknown", owner="bob@example.com")
    assert calculate_score(agent_no_owner) == 0.0
    assert calculate_score(agent_with_owner) == 20.0


def test_data_classification_criterion():
    agent = AgentCreate(name="t", framework="unknown", data_classification="confidential")
    assert calculate_score(agent) == 20.0


def test_tools_scoped_criterion():
    agent_no_tools = AgentCreate(name="t", framework="unknown")
    agent_empty_tools = AgentCreate(name="t", framework="unknown", tools=[])
    agent_with_tools = AgentCreate(name="t", framework="unknown", tools=["search"])
    assert calculate_score(agent_no_tools) == 0.0
    assert calculate_score(agent_empty_tools) == 0.0
    assert calculate_score(agent_with_tools) == 20.0


def test_ethics_review_passed_and_fresh():
    recent = datetime.datetime.utcnow() - datetime.timedelta(days=10)
    agent = AgentCreate(
        name="t", framework="unknown",
        ethics_review_status="passed",
        ethics_review_date=recent,
    )
    assert calculate_score(agent) == 20.0


def test_ethics_review_expired():
    old = datetime.datetime.utcnow() - datetime.timedelta(days=91)
    agent = AgentCreate(
        name="t", framework="unknown",
        ethics_review_status="passed",
        ethics_review_date=old,
    )
    assert calculate_score(agent) == 0.0


def test_ethics_review_exactly_at_boundary():
    boundary = datetime.datetime.utcnow() - datetime.timedelta(days=90)
    agent = AgentCreate(
        name="t", framework="unknown",
        ethics_review_status="passed",
        ethics_review_date=boundary,
    )
    assert calculate_score(agent) == 20.0


def test_ethics_review_not_passed_status():
    recent = datetime.datetime.utcnow() - datetime.timedelta(days=5)
    agent = AgentCreate(
        name="t", framework="unknown",
        ethics_review_status="pending",
        ethics_review_date=recent,
    )
    assert calculate_score(agent) == 0.0


def test_audit_log_criterion():
    agent = AgentCreate(name="t", framework="unknown", audit_log_configured=True)
    assert calculate_score(agent) == 20.0


def test_gap_report_has_five_criteria():
    agent = _make_response()
    report = generate_report(agent)
    assert len(report.criteria) == 5
    assert all(c.points_possible == 20 for c in report.criteria)


def test_gap_report_zero_score_has_all_recommendations():
    agent = _make_response()
    report = generate_report(agent)
    assert report.total_score == 0.0
    assert len(report.recommendations) == 5


def test_recommendations_empty_when_perfect(sample_agent_data):
    agent = AgentResponse(
        agent_id="test-id",
        governance_score=100.0,
        first_seen=datetime.datetime.utcnow(),
        last_seen=datetime.datetime.utcnow(),
        **sample_agent_data,
    )
    report = generate_report(agent)
    assert report.recommendations == []
    assert report.total_score == 100.0


def test_risk_summary_bands():
    for score, expected_fragment in [
        (100.0, "Governance-mature"),
        (60.0, "Governance-partial"),
        (40.0, "Governance-immature"),
        (0.0, "Governance-absent"),
    ]:
        agent = _make_response(governance_score=score)
        # Manually set fields to match the expected score
        if score == 100.0:
            pass  # we use generate_report which recalculates live
        report = generate_report(agent)
        # The risk summary is based on the *calculated* score, not governance_score field
        # For a bare agent with no fields, score = 0
        # Test the scoring band text directly
        from governance_toolkit.scorer.owasp import _risk_summary_text
        assert expected_fragment in _risk_summary_text(score)


def test_criteria_remediation_present_on_failure():
    agent = _make_response()
    report = generate_report(agent)
    for criterion in report.criteria:
        assert not criterion.passed
        assert criterion.remediation is not None
        assert len(criterion.remediation) > 0


def test_criteria_remediation_absent_on_pass(sample_agent_data):
    agent = AgentResponse(
        agent_id="test-id",
        governance_score=100.0,
        first_seen=datetime.datetime.utcnow(),
        last_seen=datetime.datetime.utcnow(),
        **sample_agent_data,
    )
    report = generate_report(agent)
    for criterion in report.criteria:
        assert criterion.passed
        assert criterion.remediation is None
