"""
artifact_datasource.py — Artifact Persistence Layer

BACAB Layer: Datasource (infrastructure — DB queries)

Responsibility:
    Handles all database CRUD operations for the artifacts table.
    Encapsulates SQLAlchemy queries and relies on DB constraints/indexes for
    invariant enforcement. Transactional flip old → insert new logic remains
    the application-side companion to DB-level safeguards.

Current status: STUB — query methods implemented for skeleton reads,
    create_artifact stubbed for future use.

TODO:
    - Wire create_artifact with full is_current flip logic
    - Add batch queries for snapshot assembly
    - Add version history queries
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.artifact import Artifact


class ArtifactDatasource:
    """Generic artifact persistence — JSONB payloads with version management."""

    def __init__(self, db: Session):
        self.db = db

    def get_current_artifact(self, rfq_id: UUID, artifact_type: str) -> Optional[Artifact]:
        """
        Fetch the current (is_current=True) artifact for a given RFQ and type.

        Uses the composite index (rfq_id, artifact_type, is_current) for fast lookup.
        Returns None if no current artifact exists.
        """
        return (
            self.db.query(Artifact)
            .filter(
                Artifact.rfq_id == rfq_id,
                Artifact.artifact_type == artifact_type,
                Artifact.is_current == True,  # noqa: E712
            )
            .first()
        )

    def list_artifacts(self, rfq_id: UUID) -> list[Artifact]:
        """
        List all artifacts (all types, all versions) for a given RFQ.

        Returns an empty list if the RFQ has no artifacts yet.
        Ordered by artifact_type then version descending.
        """
        return (
            self.db.query(Artifact)
            .filter(Artifact.rfq_id == rfq_id)
            .order_by(Artifact.artifact_type, Artifact.version.desc())
            .all()
        )

    def list_current_artifacts_for_rfq(self, rfq_id: UUID) -> dict[str, Artifact]:
        """Return all current artifacts for an RFQ keyed by artifact_type."""
        artifacts = (
            self.db.query(Artifact)
            .filter(
                Artifact.rfq_id == rfq_id,
                Artifact.is_current == True,  # noqa: E712
            )
            .all()
        )
        return {artifact.artifact_type: artifact for artifact in artifacts}

    def create_artifact(
        self,
        rfq_id: UUID,
        artifact_type: str,
        content: Optional[dict] = None,
        status: str = "pending",
        source_event_type: Optional[str] = None,
        source_event_id: Optional[str] = None,
    ) -> Artifact:
        """
        Create a new artifact version, flipping the old version's is_current to False.

        This must happen in the same transaction to maintain the invariant:
        at most one is_current=True per (rfq_id, artifact_type), with DB-level
        partial unique index protection in PostgreSQL.

        TODO: Implement full version management when services are wired.
        """
        # Step 1: Find current version number
        current = self.get_current_artifact(rfq_id, artifact_type)
        new_version = (current.version + 1) if current else 1

        # Step 2: Flip old version's is_current (same transaction)
        if current:
            current.is_current = False

        # Step 3: Insert new version
        artifact = Artifact(
            rfq_id=rfq_id,
            artifact_type=artifact_type,
            version=new_version,
            status=status,
            is_current=True,
            content=content,
            source_event_type=source_event_type,
            source_event_id=source_event_id,
        )
        self.db.add(artifact)
        self.db.flush()

        return artifact

    def create_new_artifact_version(
        self,
        rfq_id: UUID,
        artifact_type: str,
        content: Optional[dict] = None,
        status: str = "pending",
        source_event_type: Optional[str] = None,
        source_event_id: Optional[str] = None,
    ) -> Artifact:
        """Compatibility helper for explicit versioned artifact creation intent."""
        return self.create_artifact(
            rfq_id=rfq_id,
            artifact_type=artifact_type,
            content=content,
            status=status,
            source_event_type=source_event_type,
            source_event_id=source_event_id,
        )
