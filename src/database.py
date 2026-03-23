"""
database.py — SQLAlchemy Engine, Session Factory, and Declarative Base

BACAB Layer: Infrastructure (cross-cutting)

Responsibility:
    Provides the database connection machinery:
    - engine         — SQLAlchemy sync engine
    - SessionLocal   — scoped session factory
    - Base           — declarative base class for all models
    - get_db()       — FastAPI dependency that yields a session per request

    All model files in src/models/ inherit from Base defined here.

Current status: COMPLETE for skeleton.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from src.config.settings import settings

# ── 1. Engine ─────────────────────────────────────────
# One connection pool to PostgreSQL. Created once at startup.
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.APP_DEBUG,
)

# ── 2. Session Factory ────────────────────────────────
# Creates sessions. Controllers decide when to commit.
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

# ── 3. Base ───────────────────────────────────────────
# Every model inherits from this. Alembic uses Base.metadata
# to discover tables for migration generation.
Base = declarative_base()


# ── 4. get_db() — FastAPI dependency ──────────────────
# Yields a session per request. Does NOT commit —
# controllers/datasources own commit decisions.
def get_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
