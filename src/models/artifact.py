"""
artifact.py — Core Artifact Table Model

BACAB Layer: Model (data definition)

Responsibility:
    Defines the single shared artifact table that persists all 6 intelligence
    artifact types using JSONB content. Each artifact is versioned, with
    is_current tracking the latest version per (rfq_id, artifact_type).

    The JSONB design keeps the DB simple — artifact schemas are JSON document
    structures, not relational schemas. Normalizing them would create dozens
    of tables and a schema nightmare.

Current status: COMPLETE for skeleton.

Constraints:
    - UniqueConstraint on (rfq_id, artifact_type, version) prevents duplicates
    - Composite index on (rfq_id, artifact_type, is_current) enables fast lookup
    - Partial unique index on (rfq_id, artifact_type) where is_current is true,
      enforcing at most one current row per artifact type and RFQ
"""

import uuid as _uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    JSON,
    String,
    TypeDecorator,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID

from src.database import Base


# ── Cross-dialect type helpers ────────────────────────
# These allow the model to work with both PostgreSQL (production)
# and SQLite (in-memory tests) without separate model definitions.

class GUID(TypeDecorator):
    """Platform-independent UUID type. Uses PG UUID on PostgreSQL, CHAR(36) elsewhere."""
    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is not None:
            if isinstance(value, _uuid.UUID):
                return str(value) if dialect.name != "postgresql" else value
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and not isinstance(value, _uuid.UUID):
            return _uuid.UUID(str(value))
        return value


class JSONContent(TypeDecorator):
    """Uses JSONB on PostgreSQL, plain JSON elsewhere (e.g. SQLite)."""
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class Artifact(Base):
    """Shared artifact table — stores all 6 intelligence artifact types as JSONB."""

    __tablename__ = "artifacts"

    id = Column(GUID(), primary_key=True, default=_uuid.uuid4)
    rfq_id = Column(GUID(), nullable=False, index=True)
    artifact_type = Column(String, nullable=False, index=True)
    # One of: rfq_intake_profile, intelligence_briefing, workbook_profile,
    #         cost_breakdown_profile, parser_report, workbook_review_report,
    #         rfq_intelligence_snapshot, rfq_analytical_record
    version = Column(Integer, nullable=False, default=1)
    status = Column(String, nullable=False, default="pending")
    # One of: pending, partial, complete, failed
    is_current = Column(Boolean, nullable=False, default=True, index=True)
    content = Column(JSONContent(), nullable=True)
    # The full artifact payload as JSON — schema varies by artifact_type
    source_event_type = Column(String, nullable=True)
    source_event_id = Column(String, nullable=True)
    schema_version = Column(String, nullable=False, default="v1")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("rfq_id", "artifact_type", "version", name="uq_artifact_version"),
        Index("ix_artifact_current_lookup", "rfq_id", "artifact_type", "is_current"),
        Index(
            "uq_artifact_current_per_type",
            "rfq_id",
            "artifact_type",
            unique=True,
            postgresql_where=text("is_current = true"),
            sqlite_where=text("is_current = 1"),
        ),
    )

    def __repr__(self):
        return (
            f"<Artifact(id={self.id}, rfq_id={self.rfq_id}, "
            f"type={self.artifact_type}, v={self.version}, "
            f"status={self.status}, current={self.is_current})>"
        )
