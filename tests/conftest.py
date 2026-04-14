"""Shared pytest fixtures for rfq_intelligence_ms tests.

Provides:
- ``db_engine`` / ``db_session``: isolated in-memory SQLite DB per test
- ``app`` / ``client``: FastAPI app and TestClient wired to the test DB

Note: SQLite is used for skeleton smoke tests. The JSONB column works as
a plain JSON column in SQLite via SQLAlchemy's TypeDecorator fallback.
For production tests against PostgreSQL, use a real test database.
"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from src.app import create_app
from src.database import Base, get_db

# Ensure model metadata is registered for Base.metadata.create_all()
import src.models.artifact  # noqa: F401
import src.models.batch_seed_run  # noqa: F401
import src.models.processed_event  # noqa: F401


@pytest.fixture
def db_engine():
    # check_same_thread=False required because FastAPI TestClient may access
    # the DB from a different thread than the test.
    # poolclass=StaticPool ensures all threads/connections share the SAME memory DB.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(db_engine):
    TestingSessionLocal = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def app(db_engine):
    """Create app with get_db overridden to use the test engine.

    Each call to get_db creates a fresh session from the test engine,
    avoiding thread-safety issues with shared sessions.
    """
    TestingSessionLocal = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    application = create_app()

    def _override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    application.dependency_overrides[get_db] = _override_get_db
    try:
        yield application
    finally:
        application.dependency_overrides.clear()


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client
