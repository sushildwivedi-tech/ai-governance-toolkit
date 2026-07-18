from __future__ import annotations

from types import SimpleNamespace

import pytest

from governance_toolkit.scorer.traceability import (
    traceability_status,
    traceability_gaps,
    trace_checks,
)


# --------------------------------------------------------------------------- #
# Fixtures                                                                     #
# --------------------------------------------------------------------------- #


@pytest.fixture
def green_agent_data():
    """Accountable owner + unique identity + full logging → green traceability."""
    return {
        "name": "Support Copilot",
        "framework": "anthropic_claude",
        "description": "Drafts support replies.",
        "vendor": "Copilot",
        "environment": "prod",
        "status": "active",
        "owner": "Priya Nair",
        "owner_role": "Head of CX",
        "owner_contact": "priya@example.com",
        "has_unique_identity": True,
        "identity_provider": "Entra ID",
        "credential_scope": "Read/write support mailbox only.",
        "autonomy_level": "act_with_approval",
        "risk_tier": "medium",
        "permitted_actions": ["read_tickets", "draft_reply"],
        "action_logging": "yes",
        "log_location": "Splunk",
    }


@pytest.fixture
def red_agent_data():
    """No owner + shared identity + no logging → red traceability."""
    return {
        "name": "Shadow Bot",
        "framework": "unknown",
        "vendor": "internal",
        "environment": "dev",
        "status": "paused",
        "has_unique_identity": False,
        "action_logging": "no",
    }


# --------------------------------------------------------------------------- #
# Traceability derivation (unit)                                              #
# --------------------------------------------------------------------------- #


def _agent(**kw):
    base = dict(owner=None, has_unique_identity=False, action_logging="no")
    base.update(kw)
    return SimpleNamespace(**base)


def test_traceability_green():
    a = _agent(owner="Alice", has_unique_identity=True, action_logging="yes")
    assert traceability_status(a) == "green"
    assert traceability_gaps(a) == []


def test_traceability_amber_one_gap():
    a = _agent(owner="Alice", has_unique_identity=False, action_logging="yes")
    assert traceability_status(a) == "amber"
    assert traceability_gaps(a) == ["Unique identity"]


def test_traceability_red_two_gaps():
    a = _agent(owner=None, has_unique_identity=False, action_logging="yes")
    assert traceability_status(a) == "red"
    assert len(traceability_gaps(a)) == 2


def test_traceability_partial_logging_counts_as_gap():
    a = _agent(owner="Alice", has_unique_identity=True, action_logging="partial")
    assert trace_checks(a)["logging"] is False
    assert traceability_status(a) == "amber"


def test_traceability_blank_owner_is_gap():
    a = _agent(owner="   ", has_unique_identity=True, action_logging="yes")
    assert traceability_status(a) == "amber"


# --------------------------------------------------------------------------- #
# Unified agent API — traceability alongside OWASP                            #
# --------------------------------------------------------------------------- #


def test_create_agent_derives_traceability(test_client, green_agent_data):
    resp = test_client.post("/api/v1/agents", json=green_agent_data)
    assert resp.status_code == 201
    body = resp.json()
    assert body["traceability_status"] == "green"
    assert body["traceability_gaps"] == []
    # Still carries an OWASP score.
    assert "governance_score" in body


def test_create_red_agent(test_client, red_agent_data):
    resp = test_client.post("/api/v1/agents", json=red_agent_data)
    assert resp.status_code == 201
    assert resp.json()["traceability_status"] == "red"


def test_create_agent_without_framework_defaults_unknown(test_client):
    resp = test_client.post("/api/v1/agents", json={"name": "Ownerless", "owner": "Jo"})
    assert resp.status_code == 201
    assert resp.json()["framework"] == "unknown"


def test_get_agent_includes_traceability(test_client, green_agent_data):
    aid = test_client.post("/api/v1/agents", json=green_agent_data).json()["agent_id"]
    body = test_client.get(f"/api/v1/agents/{aid}").json()
    assert body["traceability_status"] == "green"
    assert body["owner_role"] == "Head of CX"


def test_audit_notes_round_trip(test_client, green_agent_data):
    """audit_notes is a JSON column — timestamps must survive create + patch."""
    data = dict(green_agent_data)
    data["audit_notes"] = [{"timestamp": "2026-07-18T00:00:00", "note": "created"}]
    r = test_client.post("/api/v1/agents", json=data)
    assert r.status_code == 201
    aid = r.json()["agent_id"]
    assert len(r.json()["audit_notes"]) == 1

    r2 = test_client.patch(f"/api/v1/agents/{aid}", json={
        "action_logging": "no",
        "deployment_date": "2025-11-03T00:00:00",
        "audit_notes": [
            {"timestamp": "2026-07-18T00:00:00", "note": "created"},
            {"timestamp": "2026-07-19T00:00:00", "note": "logging paused"},
        ],
    })
    assert r2.status_code == 200
    assert r2.json()["action_logging"] == "no"
    assert len(r2.json()["audit_notes"]) == 2
    # persisted across a fresh read
    assert test_client.get(f"/api/v1/agents/{aid}").json()["action_logging"] == "no"


def test_patch_recomputes_traceability(test_client, red_agent_data):
    aid = test_client.post("/api/v1/agents", json=red_agent_data).json()["agent_id"]
    resp = test_client.patch(
        f"/api/v1/agents/{aid}",
        json={"owner": "Sam", "has_unique_identity": True, "action_logging": "yes"},
    )
    assert resp.status_code == 200
    assert resp.json()["traceability_status"] == "green"


# --------------------------------------------------------------------------- #
# Filters                                                                      #
# --------------------------------------------------------------------------- #


def test_new_filters(test_client, green_agent_data, red_agent_data):
    test_client.post("/api/v1/agents", json=green_agent_data)
    test_client.post("/api/v1/agents", json=red_agent_data)

    assert len(test_client.get("/api/v1/agents?environment=prod").json()) == 1
    assert len(test_client.get("/api/v1/agents?traceability=red").json()) == 1
    assert len(test_client.get("/api/v1/agents?risk_tier=medium").json()) == 1
    assert len(test_client.get("/api/v1/agents?status=active").json()) == 1


# --------------------------------------------------------------------------- #
# Summary + CSV                                                                #
# --------------------------------------------------------------------------- #


def test_summary_includes_traceability(test_client, green_agent_data, red_agent_data):
    test_client.post("/api/v1/agents", json=green_agent_data)
    test_client.post("/api/v1/agents", json=red_agent_data)
    body = test_client.get("/api/v1/summary").json()
    assert body["total"] == 2
    t = body["traceability"]
    assert t["pct_with_owner"] == 50.0
    assert t["pct_with_identity"] == 50.0
    assert t["pct_with_logging"] == 50.0
    assert t["red_count"] == 1
    assert t["green_count"] == 1


def test_csv_export(test_client, green_agent_data):
    test_client.post("/api/v1/agents", json=green_agent_data)
    resp = test_client.get("/api/v1/export.csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    lines = resp.text.strip().splitlines()
    assert lines[0].startswith("agent_id,name")
    assert "governance_score" in lines[0]
    assert "traceability_status" in lines[0]
    assert "Support Copilot" in lines[1]


def test_csv_never_exposes_credential_columns(test_client, green_agent_data):
    test_client.post("/api/v1/agents", json=green_agent_data)
    header = test_client.get("/api/v1/export.csv").text.splitlines()[0].lower()
    for banned in ("secret", "token", "password", "api_key", "apikey"):
        assert banned not in header


# --------------------------------------------------------------------------- #
# Seed data                                                                    #
# --------------------------------------------------------------------------- #


def test_seed_inserts_demo_agents(test_client):
    from governance_toolkit.registry.db import get_db
    from governance_toolkit.registry.seed import seed_register

    inserted = seed_register(next(get_db()))
    assert inserted >= 8

    agents = test_client.get("/api/v1/agents?limit=500").json()
    statuses = [a["traceability_status"] for a in agents]
    assert statuses.count("red") >= 2
    assert statuses.count("amber") >= 3
    # Unified: seed agents also carry OWASP scores.
    assert any(a["governance_score"] >= 80 for a in agents)
    assert any(a["governance_score"] == 0 for a in agents)


def test_seed_is_idempotent(test_client):
    from governance_toolkit.registry.db import get_db
    from governance_toolkit.registry.seed import seed_register

    db = next(get_db())
    first = seed_register(db)
    second = seed_register(db)
    assert first >= 8
    assert second == 0


def test_seed_stores_no_credential_values():
    """Descriptive metadata only — no field named like a credential store."""
    from governance_toolkit.registry.seed import DEMO_AGENTS

    banned_keys = {"secret", "token", "password", "api_key", "apikey", "credential"}
    for spec in DEMO_AGENTS:
        assert not (set(spec.keys()) & banned_keys)
