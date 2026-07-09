from __future__ import annotations

import datetime
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from governance_toolkit.registry.db import get_db, reset_engine
from governance_toolkit.registry.models import Base
from governance_toolkit.registry.api import app
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def use_in_memory_db(monkeypatch):
    """Force all DB operations to use an in-memory SQLite database."""
    monkeypatch.setenv("GOVERNANCE_DB_URL", "sqlite:///:memory:")
    reset_engine()
    yield
    reset_engine()


@pytest.fixture
def test_client(use_in_memory_db):
    """TestClient that shares the same in-memory engine as get_db."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_agent_data():
    return {
        "name": "customer-support-agent",
        "framework": "anthropic_claude",
        "model": "claude-opus-4-5",
        "tools": ["search_kb", "create_ticket", "send_email"],
        "owner": "alice@example.com",
        "file_path": "/src/agents/support.py",
        "data_classification": "confidential",
        "risk_tier": "high",
        "ethics_review_status": "passed",
        "ethics_review_date": (datetime.datetime.utcnow() - datetime.timedelta(days=10)).isoformat(),
        "audit_log_configured": True,
    }


@pytest.fixture
def minimal_agent_data():
    return {
        "name": "unnamed-agent",
        "framework": "langchain",
    }

