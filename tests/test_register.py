from __future__ import annotations

import datetime
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
    """Accountable owner + unique identity + full logging → green."""
    return {
        "name": "Support Copilot",
        "description": "Drafts support replies.",
        "vendor": "Copilot",
        "environment": "prod",
        "status": "active",
        "owner_name": "Priya Nair",
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
    """No owner + shared identity → two gaps → red."""
    return {
        "name": "Shadow Bot",
        "vendor": "internal",
        "environment": "dev",
        "has_unique_identity": False,
        "action_logging": "no",
    }


# --------------------------------------------------------------------------- #
# Traceability derivation (unit)                                              #
# --------------------------------------------------------------------------- #


def _agent(**kw):
    base = dict(owner_name=None, has_unique_identity=False, action_logging="no")
    base.update(kw)
    return SimpleNamespace(**base)


def test_traceability_green():
    a = _agent(owner_name="Alice", has_unique_identity=True, action_logging="yes")
    assert traceability_status(a) == "green"
    assert traceability_gaps(a) == []


def test_traceability_amber_one_gap():
    a = _agent(owner_name="Alice", has_unique_identity=False, action_logging="yes")
    assert traceability_status(a) == "amber"
    assert traceability_gaps(a) == ["Unique identity"]


def test_traceability_red_two_gaps():
    a = _agent(owner_name=None, has_unique_identity=False, action_logging="yes")
    assert traceability_status(a) == "red"
    assert len(traceability_gaps(a)) == 2


def test_traceability_partial_logging_counts_as_gap():
    a = _agent(owner_name="Alice", has_unique_identity=True, action_logging="partial")
    assert trace_checks(a)["logging"] is False
    assert traceability_status(a) == "amber"


def test_traceability_blank_owner_is_gap():
    a = _agent(owner_name="   ", has_unique_identity=True, action_logging="yes")
    assert traceability_status(a) == "amber"


# --------------------------------------------------------------------------- #
# CRUD API                                                                     #
# --------------------------------------------------------------------------- #


def test_create_registered_agent_derives_status(test_client, green_agent_data):
    resp = test_client.post("/api/v1/register/agents", json=green_agent_data)
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Support Copilot"
    assert body["traceability_status"] == "green"
    assert body["traceability_gaps"] == []
    assert "agent_id" in body


def test_create_red_agent(test_client, red_agent_data):
    resp = test_client.post("/api/v1/register/agents", json=red_agent_data)
    assert resp.status_code == 201
    assert resp.json()["traceability_status"] == "red"


def test_create_duplicate_conflicts(test_client, green_agent_data):
    test_client.post("/api/v1/register/agents", json=green_agent_data)
    resp = test_client.post("/api/v1/register/agents", json=green_agent_data)
    assert resp.status_code == 409


def test_list_registered_agents_empty(test_client):
    resp = test_client.get("/api/v1/register/agents")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_registered_agent(test_client, green_agent_data):
    aid = test_client.post("/api/v1/register/agents", json=green_agent_data).json()["agent_id"]
    resp = test_client.get(f"/api/v1/register/agents/{aid}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Support Copilot"


def test_get_registered_agent_not_found(test_client):
    assert test_client.get("/api/v1/register/agents/nope").status_code == 404


def test_patch_recomputes_traceability(test_client, red_agent_data):
    aid = test_client.post("/api/v1/register/agents", json=red_agent_data).json()["agent_id"]
    resp = test_client.patch(
        f"/api/v1/register/agents/{aid}",
        json={"owner_name": "Sam", "has_unique_identity": True, "action_logging": "yes"},
    )
    assert resp.status_code == 200
    assert resp.json()["traceability_status"] == "green"


def test_delete_registered_agent(test_client, green_agent_data):
    aid = test_client.post("/api/v1/register/agents", json=green_agent_data).json()["agent_id"]
    assert test_client.delete(f"/api/v1/register/agents/{aid}").status_code == 204
    assert test_client.get(f"/api/v1/register/agents/{aid}").status_code == 404


# --------------------------------------------------------------------------- #
# Filters                                                                      #
# --------------------------------------------------------------------------- #


def test_filters(test_client, green_agent_data, red_agent_data):
    test_client.post("/api/v1/register/agents", json=green_agent_data)
    test_client.post("/api/v1/register/agents", json=red_agent_data)

    assert len(test_client.get("/api/v1/register/agents?environment=prod").json()) == 1
    assert len(test_client.get("/api/v1/register/agents?traceability=red").json()) == 1
    assert len(test_client.get("/api/v1/register/agents?risk_tier=medium").json()) == 1
    assert len(test_client.get("/api/v1/register/agents?owner=Priya Nair").json()) == 1


# --------------------------------------------------------------------------- #
# Summary + CSV                                                                #
# --------------------------------------------------------------------------- #


def test_summary_empty(test_client):
    body = test_client.get("/api/v1/register/summary").json()
    assert body["total"] == 0
    assert body["red_count"] == 0


def test_summary_percentages(test_client, green_agent_data, red_agent_data):
    test_client.post("/api/v1/register/agents", json=green_agent_data)
    test_client.post("/api/v1/register/agents", json=red_agent_data)
    body = test_client.get("/api/v1/register/summary").json()
    assert body["total"] == 2
    assert body["pct_with_owner"] == 50.0
    assert body["pct_with_identity"] == 50.0
    assert body["pct_with_logging"] == 50.0
    assert body["red_count"] == 1
    assert body["green_count"] == 1


def test_csv_export(test_client, green_agent_data):
    test_client.post("/api/v1/register/agents", json=green_agent_data)
    resp = test_client.get("/api/v1/register/export.csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    lines = resp.text.strip().splitlines()
    assert lines[0].startswith("agent_id,name")
    assert "Support Copilot" in lines[1]
    assert "traceability_status" in lines[0]


def test_csv_never_exposes_credential_columns(test_client, green_agent_data):
    test_client.post("/api/v1/register/agents", json=green_agent_data)
    header = test_client.get("/api/v1/register/export.csv").text.splitlines()[0].lower()
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

    agents = test_client.get("/api/v1/register/agents").json()
    statuses = [a["traceability_status"] for a in agents]
    assert statuses.count("red") >= 2
    assert statuses.count("amber") >= 3


def test_seed_is_idempotent(test_client):
    from governance_toolkit.registry.db import get_db
    from governance_toolkit.registry.seed import seed_register

    db = next(get_db())
    first = seed_register(db)
    second = seed_register(db)
    assert first >= 8
    assert second == 0


def test_seed_stores_no_credential_values():
    """Descriptive metadata only — no field should carry a secret-like value."""
    from governance_toolkit.registry.seed import DEMO_AGENTS

    banned_keys = {"secret", "token", "password", "api_key", "apikey", "credential"}
    for spec in DEMO_AGENTS:
        # No key literally named like a credential store.
        assert not (set(spec.keys()) & banned_keys)
