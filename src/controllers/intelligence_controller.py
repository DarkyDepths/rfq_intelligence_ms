"""
intelligence_controller.py — Intelligence Read Controller

BACAB Layer: Controller (application orchestration — HTTP)

Responsibility:
    Orchestrates HTTP read requests for intelligence artifacts.
    Receives requests from routes and delegates to the read service.
    Does NOT contain persistence logic.

    Flow: route → controller → service → datasource/connectors

Current status: STUB — wired to datasource but returns 404 for missing artifacts.

TODO:
    - Add content-type-specific response formatting
    - Add cache headers for read-heavy optimization
"""

from uuid import UUID

from src.services.artifact_read_service import ArtifactReadService


class IntelligenceController:
    """Orchestrates HTTP read requests for artifacts."""

    def __init__(self, artifact_read_service: ArtifactReadService):
        self.artifact_read_service = artifact_read_service

    def get_artifact(self, rfq_id: UUID, artifact_type: str) -> dict:
        """
        Fetch the current artifact of the given type for an RFQ.

        Returns the full artifact response or raises NotFoundError.
        """
        return self.artifact_read_service.get_artifact(rfq_id, artifact_type)

    def list_artifacts(self, rfq_id: UUID) -> dict:
        """
        List all artifacts for an RFQ.

        Returns a collection response — empty list if no artifacts exist (not 404).
        """
        return self.artifact_read_service.list_artifacts(rfq_id)
