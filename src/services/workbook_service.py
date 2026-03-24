"""
workbook_service.py — Workbook Parsing Service

BACAB Layer: Service (domain logic, called by controllers and event handlers)

Responsibility:
    Parses the GHI estimation workbook (36-sheet fixed template) and produces
    the workbook_profile artifact. The cleanest V1 artifact because the
    workbook template is fixed and deterministic to parse.

Current status: STUB — not yet implemented.

TODO:
    - Workbook structure validation (expected sheets vs found)
    - Canonical estimate profile extraction (shared mirror fields)
    - Cost breakdown profile parsing
    - Financial profile extraction
    - Schedule profile extraction
    - Quality and gaps assessment
    - Wire to artifact_datasource for persistence
"""

from src.datasources.artifact_datasource import ArtifactDatasource
from src.connectors.manager_connector import ManagerConnector


class WorkbookService:
    """Parses GHI estimation workbooks and produces workbook_profile artifacts."""

    def __init__(self, datasource: ArtifactDatasource, connector: ManagerConnector):
        self.datasource = datasource
        self.connector = connector

    def reprocess(self, rfq_id: str) -> dict:
        """Accept manual workbook reprocess request (stub)."""
        return {
            "status": "accepted",
            "message": "Reprocess request received (stub only — not yet implemented)",
        }

    async def process_workbook(self, rfq_id: str, event_payload: dict) -> None:
        """
        Run the full workbook parsing pipeline for an RFQ.

        Steps (sequential):
            1. Fetch workbook reference from manager
            2. Validate workbook structure against template
            3. Extract canonical_estimate_profile (shared mirror)
            4. Parse cost_breakdown_profile
            5. Extract financial_profile and schedule_profile
            6. Assess quality_and_gaps
            7. Persist workbook_profile artifact

        TODO: Implement pipeline.
        """
        raise NotImplementedError("Workbook parsing not yet implemented")
