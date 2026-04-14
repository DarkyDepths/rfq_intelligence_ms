"""
workbook_service.py — Workbook Parsing Service

BACAB Layer: Service (domain logic, called by controllers and event handlers)

Responsibility:
    Parses the GHI estimation workbook (deterministic fixed template) and produces
    the workbook_profile artifact. The cleanest V1 artifact because the
    workbook template is fixed and deterministic to parse.

Current status: implemented for the deterministic workbook parser slice, parser
report persistence, and truthful failure handling.

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
        """Backward-compatible helper returning the workbook_profile artifact only."""
        artifacts = self.build_workbook_parser_artifacts_from_uploaded_event(
            workbook_context=workbook_context,
            event_meta=event_meta,
            commit=commit,
        )
        return artifacts["workbook_profile"]

    @staticmethod
    def _status_from_parser_status(parser_status: str) -> str:
        if parser_status == "parsed_ok":
            return "complete"
        if parser_status == "parsed_with_warnings":
            return "partial"
        return "failed"

    @staticmethod
    def _workbook_source(workbook_context: dict) -> dict:
        filename = workbook_context["workbook_filename"]
        return {
            "workbook_ref": workbook_context["workbook_ref"],
            "workbook_filename": filename,
            "uploaded_at": workbook_context.get("uploaded_at"),
            "file_extension": filename.split(".")[-1].lower(),
            "local_workbook_path": workbook_context.get("local_workbook_path"),
        }

    def build_workbook_parser_artifacts_from_uploaded_event(
        self,
        workbook_context: dict,
        event_meta: dict,
        commit: bool = True,
    ) -> dict:
        """Build and persist deterministic parser artifacts for workbook.uploaded."""
        rfq_id = UUID(str(workbook_context["rfq_id"]))
        workbook_parse = parse_workbook_deterministic(
            workbook_path=workbook_context["local_workbook_path"],
            expected_sheet_names=workbook_context.get("expected_sheet_names"),
        )

        envelope = workbook_parse["workbook_parse_envelope"]
        structure = workbook_parse["workbook_structure"]
        recognition = workbook_parse["template_recognition"]
        parser_report = envelope["parser_report"]
        parser_status = parser_report["status"]
        artifact_status = self._status_from_parser_status(parser_status)

        rfq_identity = (envelope.get("workbook_profile") or {}).get("rfq_identity") or {}

        workbook_profile_content = {
            "artifact_meta": {
                "artifact_type": "workbook_profile",
                "slice": "workbook.uploaded_vertical_slice_v1",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source_event_id": event_meta["event_id"],
                "source_event_type": event_meta["event_type"],
            },
            "workbook_source": self._workbook_source(workbook_context),
            "template_name": envelope.get("template_name"),
            "parser_version": envelope.get("parser_version"),
            "template_match": envelope.get("template_match"),
            "template_recognition": recognition,
            "workbook_structure": {
                "sheet_names": structure["sheet_names"],
                "expected_sheet_count": structure["expected_sheet_count"],
                "sheet_count_found": structure["sheet_count_found"],
                "missing_sheets": structure["missing_sheets"],
                "extra_sheets": structure["extra_sheets"],
            },
            "canonical_estimate_profile": {
                "rfq_id": str(rfq_id),
                "detected_identifiers": {
                    "rfq_code": workbook_context.get("rfq_display", {}).get("rfq_code"),
                    "project_title": rfq_identity.get("project_name")
                    or workbook_context.get("rfq_display", {}).get("project_title"),
                    "client_name": rfq_identity.get("client_name"),
                    "inquiry_no": rfq_identity.get("inquiry_no"),
                },
            },
            "workbook_profile": envelope.get("workbook_profile"),
            "pairing_validation": {
                "pairing_status": "not_assessed",
                "notes": "Standalone workbook fixture processed without assuming linkage to the local RFQ source package fixture.",
                "external_linkage_required": True,
            },
            "downstream_readiness": {
                "review_report_ready": parser_status != "failed",
                "benchmark_ready": False,
                "similarity_ready": False,
                "requires_human_review": True,
            },
            "parser_report_status": parser_status,
        }

        cost_breakdown_content = {
            "artifact_meta": {
                "artifact_type": "cost_breakdown_profile",
                "slice": "workbook.uploaded_vertical_slice_v1",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source_event_id": event_meta["event_id"],
                "source_event_type": event_meta["event_type"],
            },
            "workbook_source": self._workbook_source(workbook_context),
            "template_name": envelope.get("template_name"),
            "parser_version": envelope.get("parser_version"),
            "template_match": envelope.get("template_match"),
            "cost_breakdown_profile": envelope.get("cost_breakdown_profile"),
            "parser_report_status": parser_status,
        }

        parser_report_content = {
            "artifact_meta": {
                "artifact_type": "parser_report",
                "slice": "workbook.uploaded_vertical_slice_v1",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source_event_id": event_meta["event_id"],
                "source_event_type": event_meta["event_type"],
            },
            "workbook_source": self._workbook_source(workbook_context),
            "template_name": envelope.get("template_name"),
            "parser_version": envelope.get("parser_version"),
            "template_match": envelope.get("template_match"),
            "parsed_at": envelope.get("parsed_at"),
            "parser_report": parser_report,
        }

        workbook_profile_artifact = self.datasource.create_new_artifact_version(
            rfq_id=rfq_id,
            artifact_type="workbook_profile",
            content=workbook_profile_content,
            status=artifact_status,
            source_event_type=event_meta["event_type"],
            source_event_id=event_meta["event_id"],
        )
        cost_breakdown_artifact = self.datasource.create_new_artifact_version(
            rfq_id=rfq_id,
            artifact_type="cost_breakdown_profile",
            content=cost_breakdown_content,
            status=artifact_status,
            source_event_type=event_meta["event_type"],
            source_event_id=event_meta["event_id"],
        )
        parser_report_artifact = self.datasource.create_new_artifact_version(
            rfq_id=rfq_id,
            artifact_type="parser_report",
            content=parser_report_content,
            status=artifact_status,
            source_event_type=event_meta["event_type"],
            source_event_id=event_meta["event_id"],
        )

        if commit:
            self.datasource.db.commit()
            self.datasource.db.refresh(workbook_profile_artifact)
            self.datasource.db.refresh(cost_breakdown_artifact)
            self.datasource.db.refresh(parser_report_artifact)

        return {
            "workbook_profile": workbook_profile_artifact,
            "cost_breakdown_profile": cost_breakdown_artifact,
            "parser_report": parser_report_artifact,
        }

    def persist_parser_failure_artifact(
        self,
        rfq_id: str,
        event_meta: dict,
        workbook_ref: str | None,
        workbook_filename: str | None,
        uploaded_at: str | None,
        error_code: str,
        error_message: str,
        commit: bool = True,
    ):
        """Persist a truthful parser_report failure state when parsing cannot start/complete."""
        rfq_uuid = UUID(str(rfq_id))
        content = {
            "artifact_meta": {
                "artifact_type": "parser_report",
                "slice": "workbook.uploaded_vertical_slice_v1",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source_event_id": event_meta["event_id"],
                "source_event_type": event_meta["event_type"],
            },
            "workbook_source": {
                "workbook_ref": workbook_ref,
                "workbook_filename": workbook_filename,
                "uploaded_at": uploaded_at,
            },
            "parser_report": {
                "status": "failed",
                "failure": {
                    "code": error_code,
                    "message": error_message,
                },
            },
        }
        artifact = self.datasource.create_new_artifact_version(
            rfq_id=rfq_uuid,
            artifact_type="parser_report",
            content=content,
            status="failed",
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
