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

from datetime import datetime, timezone
from uuid import UUID

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

    async def get_rfq_context(self, rfq_id: str) -> dict:
        """Read minimal RFQ context through the manager connector boundary."""
        return await self.connector.get_rfq_context(rfq_id)

    def build_intake_profile_from_rfq_created(self, rfq_context: dict, event_meta: dict):
        """Build and persist a minimal, honest rfq_intake_profile for the first slice."""
        rfq_id = UUID(str(rfq_context["rfq_id"]))
        source_package_refs = rfq_context.get("source_package_refs", [])
        known_fields = {
            "rfq_code": rfq_context.get("rfq_code"),
            "client_name": rfq_context.get("client_name"),
            "project_title": rfq_context.get("project_title"),
            "created_at": rfq_context.get("created_at"),
        }

        content = {
            "artifact_meta": {
                "artifact_type": "rfq_intake_profile",
                "slice": "rfq.created_vertical_slice_v1",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source_event_id": event_meta["event_id"],
                "source_event_type": event_meta["event_type"],
            },
            "source_package": {
                "references": source_package_refs,
                "primary_reference": source_package_refs[0]["reference"] if source_package_refs else None,
                "visibility_level": "reference_only",
            },
            "package_structure": {
                "status": "limited",
                "summary": "Source package structure is not parsed yet in this slice.",
                "reference_count": len(source_package_refs),
            },
            "document_understanding": {
                "status": "not_ready",
                "summary": "Deep document parsing is not implemented in this first vertical slice.",
            },
            "canonical_project_profile": {
                "rfq_id": str(rfq_id),
                "rfq_code": known_fields["rfq_code"],
                "client_name": known_fields["client_name"],
                "project_title": known_fields["project_title"],
                "created_at": known_fields["created_at"],
            },
            "field_evidence": [
                {
                    "field": "rfq_id",
                    "value": str(rfq_id),
                    "source": "rfq_manager_context",
                    "confidence": "high",
                },
                {
                    "field": "source_package_refs",
                    "value": source_package_refs,
                    "source": "rfq_manager_context",
                    "confidence": "medium",
                },
            ],
            "quality_and_gaps": {
                "status": "partial",
                "known_data_points": [
                    "rfq identifiers",
                    "source package references",
                    "minimal display metadata",
                ],
                "gaps": [
                    "deep file inventory",
                    "document extraction",
                    "structured compliance extraction",
                ],
            },
            "downstream_readiness": {
                "briefing_ready": True,
                "workbook_comparison_ready": False,
                "historical_matching_ready": False,
                "requires_human_review": True,
            },
        }

        artifact = self.datasource.create_new_artifact_version(
            rfq_id=rfq_id,
            artifact_type="rfq_intake_profile",
            content=content,
            status="partial",
            source_event_type=event_meta["event_type"],
            source_event_id=event_meta["event_id"],
        )
        self.datasource.db.commit()
        self.datasource.db.refresh(artifact)
        return artifact

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
