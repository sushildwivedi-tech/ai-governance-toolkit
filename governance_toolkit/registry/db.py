from __future__ import annotations

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

_engine = None
_SessionLocal = None


def _get_database_url() -> str:
    return os.environ.get("GOVERNANCE_DB_URL", "sqlite:///./governance.db")


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        url = _get_database_url()
        if url == "sqlite:///:memory:":
            # StaticPool shares a single connection so in-memory tables persist
            _engine = create_engine(
                url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        elif url.startswith("sqlite"):
            _engine = create_engine(url, connect_args={"check_same_thread": False})
        else:
            _engine = create_engine(url)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine


def get_session_factory():
    get_engine()
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    factory = get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from .models import Base
    Base.metadata.create_all(bind=get_engine())


def reset_engine():
    global _engine, _SessionLocal
    _engine = None
    _SessionLocal = None
