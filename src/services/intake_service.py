"""
intake_service.py — RFQ Intake Parsing Service

BACAB Layer: Service (domain logic, called by controllers and event handlers)

Responsibility:
    Parses the ZIP/MR package from an RFQ and produces the rfq_intake_profile artifact.
    Combines deterministic extraction (folder tree, BOM, standards filenames) with
    LLM extraction for unstructured documents when needed.

Current status: STUB — not yet implemented.

TODO:
    - Intake parsing pipeline
    - Document understanding extraction
    - Canonical field normalization
    - Evidence and quality/gap tracking
    - Wire to artifact_datasource for persistence
"""

from src.datasources.artifact_datasource import ArtifactDatasource
from src.connectors.manager_connector import ManagerConnector


class IntakeService:
    """Parses ZIP/MR packages and produces rfq_intake_profile artifacts."""

    def __init__(self, datasource: ArtifactDatasource, connector: ManagerConnector):
        self.datasource = datasource
        self.connector = connector

    def reprocess(self, rfq_id: str) -> dict:
        """Accept manual intake reprocess request (stub)."""
        return {
            "status": "accepted",
            "message": "Reprocess request received (stub only — not yet implemented)",
        }

    async def process_intake(self, rfq_id: str, event_payload: dict) -> None:
        """
        Run the full intake parsing pipeline for an RFQ.

        Steps (sequential):
            1. Fetch RFQ metadata + file references from manager
            2. Parse package structure (deterministic)
            3. Extract document understanding (heuristic + LLM)
            4. Normalize into canonical_project_profile
            5. Build field_evidence and quality_and_gaps
            6. Persist rfq_intake_profile artifact

        TODO: Implement pipeline.
        """
        raise NotImplementedError("Intake parsing not yet implemented")
