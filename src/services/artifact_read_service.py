"""
artifact_read_service.py — Artifact Read Service

BACAB Layer: Service (application read orchestration)

Responsibility:
    Provides the read path between controllers and persistence for artifact
    retrieval/list operations. Keeps controller free of datasource concerns.

    Flow: controller → service → datasource → translator
"""

from uuid import UUID

from src.datasources.artifact_datasource import ArtifactDatasource
from src.translators.artifact_translator import ArtifactTranslator
from src.utils.exceptions import NotFoundError


class ArtifactReadService:
    """Thin service boundary for intelligence artifact read operations."""

    def __init__(self, datasource: ArtifactDatasource, translator: ArtifactTranslator):
        self.datasource = datasource
        self.translator = translator

    def get_artifact(self, rfq_id: UUID, artifact_type: str) -> dict:
        artifact = self.datasource.get_current_artifact(rfq_id, artifact_type)
        if not artifact:
            raise NotFoundError(f"No {artifact_type} artifact found for this RFQ")
        return self.translator.to_response(artifact)

    def list_artifacts(self, rfq_id: UUID) -> dict:
        artifacts = self.datasource.list_artifacts(rfq_id)
        return {
            "artifacts": [self.translator.to_summary(a) for a in artifacts]
        }
