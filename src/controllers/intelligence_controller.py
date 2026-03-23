"""
intelligence_controller.py — Intelligence Read Controller

BACAB Layer: Controller (application orchestration — HTTP)

Responsibility:
    Orchestrates HTTP read requests for intelligence artifacts.
    Receives requests from routes, calls the datasource to fetch data,
    uses the translator to format responses. Does NOT contain domain logic.

    Flow: route → controller → datasource → translator → response

Current status: STUB — wired to datasource but returns 404 for missing artifacts.

TODO:
    - Add content-type-specific response formatting
    - Add cache headers for read-heavy optimization
"""

from uuid import UUID

from src.datasources.artifact_datasource import ArtifactDatasource
from src.translators.artifact_translator import ArtifactTranslator
from src.utils.exceptions import NotFoundError


class IntelligenceController:
    """Orchestrates HTTP read requests for artifacts."""

    def __init__(self, datasource: ArtifactDatasource, translator: ArtifactTranslator):
        self.datasource = datasource
        self.translator = translator

    def get_artifact(self, rfq_id: UUID, artifact_type: str) -> dict:
        """
        Fetch the current artifact of the given type for an RFQ.

        Returns the full artifact response or raises NotFoundError.
        """
        artifact = self.datasource.get_current_artifact(rfq_id, artifact_type)
        if not artifact:
            raise NotFoundError(f"No {artifact_type} artifact found for this RFQ")
        return self.translator.to_response(artifact)

    def list_artifacts(self, rfq_id: UUID) -> dict:
        """
        List all artifacts for an RFQ.

        Returns a collection response — empty list if no artifacts exist (not 404).
        """
        artifacts = self.datasource.list_artifacts(rfq_id)
        return {
            "artifacts": [self.translator.to_summary(a) for a in artifacts]
        }
