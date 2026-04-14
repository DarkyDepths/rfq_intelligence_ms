"""
snapshot_service.py — Intelligence Snapshot Assembly Service

BACAB Layer: Service (domain logic, called by controllers and event handlers)

Responsibility:
    Assembles the rfq_intelligence_snapshot — the consumer-facing read model.
    A single assembled projection per RFQ containing latest states of all
    intelligence artifacts, section availability, confidence markers, and
    consumer hints. Simplifies UI and chatbot integration.

    For V1 skeleton: snapshot follows the same shared artifact-table pattern
    as all other artifacts including version and is_current.

Current status: implemented for current V1 artifact availability and consumer-facing
snapshot assembly.

TODO:
    - Artifact reference assembly (latest version + status of each artifact)
    - Availability matrix computation
    - Executive panel, briefing panel, workbook panel, review panel assembly
    - Consumer hints generation (ui_recommended_tabs, chatbot_suggested_questions)
    - Wire to artifact_datasource for persistence
"""

from datetime import datetime, timezone
from uuid import UUID

from src.datasources.artifact_datasource import ArtifactDatasource


class SnapshotService:
    """Assembles rfq_intelligence_snapshot read models from underlying artifacts."""

    def __init__(self, datasource: ArtifactDatasource):
        self.datasource = datasource

    def rebuild_snapshot_for_rfq(
        self,
        rfq_id: str,
        source_event_meta: dict,
        commit: bool = True,
    ):
        """Build and persist current rfq_intelligence_snapshot for available slices."""
        rfq_uuid = UUID(str(rfq_id))
        current_artifacts = self.datasource.list_current_artifacts_for_rfq(rfq_uuid)

        intake_artifact = current_artifacts.get("rfq_intake_profile")
        briefing_artifact = current_artifacts.get("intelligence_briefing")
        workbook_profile_artifact = current_artifacts.get("workbook_profile")
        cost_breakdown_artifact = current_artifacts.get("cost_breakdown_profile")
        parser_report_artifact = current_artifacts.get("parser_report")
        workbook_review_artifact = current_artifacts.get("workbook_review_report")
        analytical_artifact = current_artifacts.get("rfq_analytical_record")

        intake_content = intake_artifact.content if intake_artifact else {}
        briefing_content = briefing_artifact.content if briefing_artifact else {}
        workbook_profile_content = workbook_profile_artifact.content if workbook_profile_artifact else {}
        parser_report_content = parser_report_artifact.content if parser_report_artifact else {}
        workbook_review_content = workbook_review_artifact.content if workbook_review_artifact else {}
        analytical_content = analytical_artifact.content if analytical_artifact else {}
        outcome_enrichment = analytical_content.get("outcome_enrichment") or {}
        parser_report_payload = parser_report_content.get("parser_report") or {}
        parser_status = parser_report_payload.get("status")

        intake_available = intake_artifact is not None
        briefing_available = briefing_artifact is not None
        analytical_available = analytical_artifact is not None
        requires_human_review = True

        availability_matrix = {
            "rfq_intake_profile": "available" if intake_available else "not_ready",
            "intelligence_briefing": "available" if briefing_available else "not_ready",
            "workbook_profile": "available" if workbook_profile_artifact else "not_ready",
            "cost_breakdown_profile": "available" if cost_breakdown_artifact else "not_ready",
            "parser_report": "available" if parser_report_artifact else "not_ready",
            "workbook_review_report": "available" if workbook_review_artifact else "not_ready",
            "rfq_analytical_record": "available" if analytical_available else "not_ready",
            "benchmarking": "insufficient_historical_base",
            "similarity": "insufficient_historical_base",
        }

        content = {
            "artifact_meta": {
                "artifact_type": "rfq_intelligence_snapshot",
                "slice": "v1_incremental_intelligence",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source_event_id": source_event_meta["event_id"],
                "source_event_type": source_event_meta["event_type"],
            },
            "rfq_summary": {
                "rfq_id": str(rfq_uuid),
                "rfq_code": intake_content.get("canonical_project_profile", {}).get("rfq_code"),
                "project_title": intake_content.get("canonical_project_profile", {}).get("project_title"),
                "client_name": intake_content.get("canonical_project_profile", {}).get("client_name"),
            },
            "availability_matrix": availability_matrix,
            "intake_panel_summary": {
                "status": intake_artifact.status if intake_artifact else "not_ready",
                "source_reference": intake_content.get("source_package", {}).get("primary_reference"),
                "quality_status": intake_content.get("quality_and_gaps", {}).get("status"),
                "key_gaps": intake_content.get("quality_and_gaps", {}).get("gaps", []),
            },
            "briefing_panel_summary": {
                "status": briefing_artifact.status if briefing_artifact else "not_ready",
                "executive_summary": briefing_content.get("executive_summary"),
                "missing_info": briefing_content.get("what_is_missing", []),
            },
            "workbook_panel": {
                "status": workbook_profile_artifact.status if workbook_profile_artifact else "not_ready",
                "reason": (
                    None
                    if workbook_profile_artifact
                    else "No workbook.uploaded event processed yet."
                ),
                "template_recognition": workbook_profile_content.get("template_recognition"),
                "pairing_validation": workbook_profile_content.get("pairing_validation"),
                "parser_status": parser_status,
                "parser_failure": parser_report_payload.get("failure"),
            },
            "review_panel": {
                "status": workbook_review_artifact.status if workbook_review_artifact else "not_ready",
                "reason": (
                    None
                    if workbook_review_artifact
                    else "Workbook parser failed; review report was not generated."
                    if parser_status == "failed"
                    else "No workbook review is available before workbook.uploaded."
                ),
                "active_findings_count": (
                    (workbook_review_content.get("summary") or {}).get("active_findings_count")
                    if workbook_review_artifact
                    else 0
                ),
            },
            "analytical_status_summary": {
                "status": analytical_artifact.status if analytical_artifact else "not_ready",
                "historical_readiness": False,
                "notes": [
                    "Initial analytical seed exists only for cold-start memory.",
                    "Historical similarity/benchmark capabilities are not ready.",
                ],
            },
            "outcome_summary": {
                "status": "recorded" if outcome_enrichment else "not_recorded",
                "outcome": outcome_enrichment.get("outcome_status"),
                "reason": outcome_enrichment.get("outcome_reason"),
                "recorded_at": outcome_enrichment.get("recorded_at"),
                "learning_loop_status": outcome_enrichment.get("learning_loop_status"),
            },
            "consumer_hints": {
                "ui_recommended_tabs": ["snapshot", "briefing"],
                "chatbot_suggested_questions": [
                    "What is currently known about this RFQ?",
                    "Which sections are still unavailable and why?",
                ],
            },
            "requires_human_review": requires_human_review,
            "overall_status": "partial",
        }

        artifact = self.datasource.create_new_artifact_version(
            rfq_id=rfq_uuid,
            artifact_type="rfq_intelligence_snapshot",
            content=content,
            status="partial",
            source_event_type=source_event_meta["event_type"],
            source_event_id=source_event_meta["event_id"],
        )
        if commit:
            self.datasource.db.commit()
            self.datasource.db.refresh(artifact)
        return artifact

    async def refresh_snapshot(self, rfq_id: str) -> None:
        """
        Rebuild the intelligence snapshot for the given RFQ.

        Reads the current state of all underlying artifacts and assembles
        a new snapshot version. Called after every artifact update.

        TODO: Implement snapshot assembly pipeline.
        """
        raise NotImplementedError("Snapshot assembly not yet implemented")
