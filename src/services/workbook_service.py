"""
workbook_service.py — Workbook Parsing Service

BACAB Layer: Service (domain logic, called by controllers and event handlers)

Responsibility:
    Parses the GHI estimation workbook (deterministic fixed template) and produces
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

from datetime import datetime, timezone
from uuid import UUID

from src.datasources.artifact_datasource import ArtifactDatasource
from src.connectors.manager_connector import ManagerConnector
from src.services.workbook_parser import parse_workbook_deterministic


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

    async def get_workbook_context(
        self,
        rfq_id: str,
        workbook_ref: str,
        workbook_filename: str,
        uploaded_at: str,
    ) -> dict:
        return await self.connector.get_workbook_context(
            rfq_id=rfq_id,
            workbook_ref=workbook_ref,
            workbook_filename=workbook_filename,
            uploaded_at=uploaded_at,
        )

    def build_workbook_profile_from_uploaded_event(
        self,
        workbook_context: dict,
        event_meta: dict,
        commit: bool = True,
    ):
        """Build and persist workbook_profile for workbook.uploaded first slice."""
        rfq_id = UUID(str(workbook_context["rfq_id"]))
        workbook_parse = parse_workbook_deterministic(
            workbook_path=workbook_context["local_workbook_path"],
            expected_sheet_names=workbook_context.get("expected_sheet_names"),
        )

        structure = workbook_parse["workbook_structure"]
        extracts = workbook_parse["high_value_extracts"]
        recognition = workbook_parse["template_recognition"]

        quality_gaps = []
        if structure["missing_sheets"]:
            quality_gaps.append(f"Missing expected sheets: {', '.join(structure['missing_sheets'][:10])}")
        if structure["sheet_count_found"] != structure["expected_sheet_count"]:
            quality_gaps.append(
                "Sheet count differs from expected GHI workbook template."
            )
        if not extracts["text_hits"]:
            quality_gaps.append("No high-signal workbook labels were detected in scanned cells.")

        profile_status = "complete" if recognition["recognition_status"] == "matched" else "partial"

        canonical_estimate_profile = {
            "rfq_id": str(rfq_id),
            "detected_labels": extracts["text_hits"][:25],
            "detected_identifiers": {
                "rfq_code": workbook_context.get("rfq_display", {}).get("rfq_code"),
                "project_title": workbook_context.get("rfq_display", {}).get("project_title"),
            },
        }

        content = {
            "artifact_meta": {
                "artifact_type": "workbook_profile",
                "slice": "workbook.uploaded_vertical_slice_v1",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source_event_id": event_meta["event_id"],
                "source_event_type": event_meta["event_type"],
            },
            "workbook_source": {
                "workbook_ref": workbook_context["workbook_ref"],
                "workbook_filename": workbook_context["workbook_filename"],
                "uploaded_at": workbook_context.get("uploaded_at"),
                "file_extension": workbook_context["workbook_filename"].split(".")[-1].lower(),
            },
            "template_recognition": recognition,
            "workbook_structure": {
                "sheet_names": structure["sheet_names"],
                "expected_sheet_count": structure["expected_sheet_count"],
                "sheet_count_found": structure["sheet_count_found"],
                "missing_sheets": structure["missing_sheets"],
                "extra_sheets": structure["extra_sheets"],
            },
            "canonical_estimate_profile": canonical_estimate_profile,
            "cost_breakdown": {
                "numeric_sample": extracts["numeric_sample"][:60],
                "totals_detected": [
                    hit for hit in extracts["text_hits"] if "total" in hit["text"].lower()
                ][:20],
                "status": "partial",
            },
            "financial_profile": {
                "status": "partial" if extracts["numeric_sample"] else "unavailable",
                "notes": "Financial values require deeper semantic mapping in future slices.",
            },
            "schedule_profile": {
                "status": "partial" if any("delivery" in h["text"].lower() or "lead" in h["text"].lower() for h in extracts["text_hits"]) else "unavailable",
                "notes": "Schedule extraction is keyword-level only in this first workbook slice.",
            },
            "structural_quality_and_gaps": {
                "status": profile_status,
                "parse_coverage": {
                    "scanned_sheet_count": structure["sheet_count_found"],
                    "keyword_hits": len(extracts["text_hits"]),
                    "numeric_hits": len(extracts["numeric_sample"]),
                },
                "gaps": quality_gaps,
                "unsupported_variations": [
                    "Arbitrary workbook templates are not supported in this slice.",
                ],
            },
            "pairing_validation": {
                "pairing_status": "not_assessed",
                "notes": "Standalone workbook fixture processed without assuming linkage to the local RFQ source package fixture.",
                "external_linkage_required": True,
            },
            "downstream_readiness": {
                "review_report_ready": True,
                "benchmark_ready": False,
                "similarity_ready": False,
                "requires_human_review": True,
            },
        }

        artifact = self.datasource.create_new_artifact_version(
            rfq_id=rfq_id,
            artifact_type="workbook_profile",
            content=content,
            status=profile_status,
            source_event_type=event_meta["event_type"],
            source_event_id=event_meta["event_id"],
        )
        if commit:
            self.datasource.db.commit()
            self.datasource.db.refresh(artifact)
        return artifact

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
