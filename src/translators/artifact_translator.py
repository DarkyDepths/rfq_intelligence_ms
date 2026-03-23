"""
artifact_translator.py — Artifact Data Translator

BACAB Layer: Translator (data mapping between layers)

Responsibility:
    Converts between artifact DB rows (SQLAlchemy model instances)
    and API response shapes (dicts / Pydantic models). Keeps the
    datasource layer independent of API contract details.

Current status: COMPLETE for skeleton.

TODO:
    - Add content-type-specific formatting when artifact schemas mature
    - Add pagination metadata translation
"""

from src.models.artifact import Artifact


class ArtifactTranslator:
    """Translates artifact DB rows → API responses."""

    @staticmethod
    def to_response(artifact: Artifact) -> dict:
        """Convert a single artifact row to a full API response dict."""
        return {
            "id": str(artifact.id),
            "rfq_id": str(artifact.rfq_id),
            "artifact_type": artifact.artifact_type,
            "version": artifact.version,
            "status": artifact.status,
            "is_current": artifact.is_current,
            "content": artifact.content,
            "source_event_type": artifact.source_event_type,
            "source_event_id": artifact.source_event_id,
            "schema_version": artifact.schema_version,
            "created_at": artifact.created_at.isoformat() if artifact.created_at else None,
            "updated_at": artifact.updated_at.isoformat() if artifact.updated_at else None,
        }

    @staticmethod
    def to_summary(artifact: Artifact) -> dict:
        """Convert an artifact row to a compact summary for the index endpoint."""
        return {
            "id": str(artifact.id),
            "rfq_id": str(artifact.rfq_id),
            "artifact_type": artifact.artifact_type,
            "version": artifact.version,
            "status": artifact.status,
            "is_current": artifact.is_current,
            "schema_version": artifact.schema_version,
            "created_at": artifact.created_at.isoformat() if artifact.created_at else None,
            "updated_at": artifact.updated_at.isoformat() if artifact.updated_at else None,
        }
