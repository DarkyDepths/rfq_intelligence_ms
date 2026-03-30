"""batch_seed_run.py — Operational run-level records for historical batch seeding."""

from __future__ import annotations

import uuid as _uuid

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, func

from src.models.artifact import JSONContent
from src.database import Base


class BatchSeedRun(Base):
    """Single summary record per historical workbook batch-seeding run."""

    __tablename__ = "batch_seed_runs"

    # Keep id as string to match migration 004 and avoid UUID/String casting issues.
    id = Column(String(36), primary_key=True, default=lambda: str(_uuid.uuid4()))
    run_id = Column(String(64), nullable=False, unique=True, index=True)
    run_type = Column(String(64), nullable=False)
    parser_version = Column(String(64), nullable=True)
    freeze_version = Column(String(64), nullable=True)

    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=False)
    duration_seconds = Column(Float, nullable=False, default=0.0)

    persist_artifacts = Column(Boolean, nullable=False, default=False)
    input_scope_root = Column(String(512), nullable=True)

    total_files = Column(Integer, nullable=False, default=0)
    parsed_ok = Column(Integer, nullable=False, default=0)
    parsed_with_warnings = Column(Integer, nullable=False, default=0)
    failed = Column(Integer, nullable=False, default=0)
    skipped_invalid = Column(Integer, nullable=False, default=0)
    persisted_ok = Column(Integer, nullable=False, default=0)
    persisted_failed = Column(Integer, nullable=False, default=0)
    rollback_count = Column(Integer, nullable=False, default=0)
    overall_status = Column(String(32), nullable=False)

    failure_samples = Column(JSONContent(), nullable=False, default=list)
    warning_samples = Column(JSONContent(), nullable=False, default=list)

    created_at = Column(DateTime, nullable=False, server_default=func.now())
