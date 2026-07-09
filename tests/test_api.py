from __future__ import annotations

import datetime
import pytest


def test_health_endpoint(test_client):
    resp = test_client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["agent_count"] == 0


def test_create_agent(test_client, sample_agent_data):
    resp = test_client.post("/api/v1/agents", json=sample_agent_data)
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == sample_agent_data["name"]
    assert body["governance_score"] == 100.0
    assert "agent_id" in body


def test_create_agent_duplicate(test_client, sample_agent_data):
    test_client.post("/api/v1/agents", json=sample_agent_data)
    resp = test_client.post("/api/v1/agents", json=sample_agent_data)
    assert resp.status_code == 409


def test_list_agents_empty(test_client):
    resp = test_client.get("/api/v1/agents")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_agents(test_client, sample_agent_data, minimal_agent_data):
    test_client.post("/api/v1/agents", json=sample_agent_data)
    test_client.post("/api/v1/agents", json=minimal_agent_data)
    resp = test_client.get("/api/v1/agents")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_agent(test_client, sample_agent_data):
    create_resp = test_client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = create_resp.json()["agent_id"]
    resp = test_client.get(f"/api/v1/agents/{agent_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == sample_agent_data["name"]


def test_get_agent_not_found(test_client):
    resp = test_client.get("/api/v1/agents/nonexistent-id-12345")
    assert resp.status_code == 404


def test_update_agent_recalculates_score(test_client, minimal_agent_data):
    create_resp = test_client.post("/api/v1/agents", json=minimal_agent_data)
    assert create_resp.status_code == 201
    agent_id = create_resp.json()["agent_id"]
    assert create_resp.json()["governance_score"] == 0.0

    patch_resp = test_client.patch(
        f"/api/v1/agents/{agent_id}",
        json={"owner": "bob@example.com"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["governance_score"] == 20.0


def test_delete_agent(test_client, sample_agent_data):
    create_resp = test_client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = create_resp.json()["agent_id"]

    del_resp = test_client.delete(f"/api/v1/agents/{agent_id}")
    assert del_resp.status_code == 204

    get_resp = test_client.get(f"/api/v1/agents/{agent_id}")
    assert get_resp.status_code == 404


def test_score_endpoint_full_report(test_client, sample_agent_data):
    create_resp = test_client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = create_resp.json()["agent_id"]

    score_resp = test_client.get(f"/api/v1/agents/{agent_id}/score")
    assert score_resp.status_code == 200
    report = score_resp.json()
    assert report["total_score"] == 100.0
    assert len(report["criteria"]) == 5
    assert report["recommendations"] == []


def test_score_endpoint_gap_report(test_client, minimal_agent_data):
    create_resp = test_client.post("/api/v1/agents", json=minimal_agent_data)
    agent_id = create_resp.json()["agent_id"]

    score_resp = test_client.get(f"/api/v1/agents/{agent_id}/score")
    assert score_resp.status_code == 200
    report = score_resp.json()
    assert report["total_score"] == 0.0
    assert len(report["recommendations"]) == 5


def test_list_filter_by_framework(test_client, sample_agent_data, minimal_agent_data):
    test_client.post("/api/v1/agents", json=sample_agent_data)
    test_client.post("/api/v1/agents", json=minimal_agent_data)

    resp = test_client.get("/api/v1/agents?framework=anthropic_claude")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["framework"] == "anthropic_claude"


def test_list_filter_by_min_score(test_client, sample_agent_data, minimal_agent_data):
    test_client.post("/api/v1/agents", json=sample_agent_data)
    test_client.post("/api/v1/agents", json=minimal_agent_data)

    resp = test_client.get("/api/v1/agents?min_score=50")
    assert resp.status_code == 200
    results = resp.json()
    assert all(a["governance_score"] >= 50 for a in results)


def test_summary_endpoint(test_client, sample_agent_data, minimal_agent_data):
    test_client.post("/api/v1/agents", json=sample_agent_data)
    test_client.post("/api/v1/agents", json=minimal_agent_data)

    resp = test_client.get("/api/v1/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert "by_framework" in body
    assert "avg_score" in body
    assert body["below_50"] == 1


def test_batch_register(test_client, sample_agent_data, minimal_agent_data):
    resp = test_client.post("/api/v1/agents/batch", json=[sample_agent_data, minimal_agent_data])
    assert resp.status_code == 207
    results = resp.json()
    assert len(results) == 2
    assert all(r["success"] for r in results)


def test_batch_register_partial_failure(test_client, sample_agent_data):
    test_client.post("/api/v1/agents", json=sample_agent_data)
    resp = test_client.post("/api/v1/agents/batch", json=[sample_agent_data])
    assert resp.status_code == 207
    results = resp.json()
    assert results[0]["success"] is False
    assert "already registered" in results[0]["error"]
