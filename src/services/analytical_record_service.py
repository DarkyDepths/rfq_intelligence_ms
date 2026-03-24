"""
analytical_record_service.py — Analytical Record Service

BACAB Layer: Service (domain logic, called by event handlers)

Responsibility:
    Builds the minimal initial rfq_analytical_record artifact for the
    rfq.created vertical slice.
"""

from datetime import datetime, timezone
from uuid import UUID

from src.datasources.artifact_datasource import ArtifactDatasource


class AnalyticalRecordService:
    """Builds minimal rfq_analytical_record artifacts."""

    def __init__(self, datasource: ArtifactDatasource):
        self.datasource = datasource

    def build_initial_analytical_record(
        self,
        rfq_context: dict,
        intake_artifact,
        event_meta: dict,
        commit: bool = True,
    ):
        """Seed a truthful, minimal analytical record from known intake context."""
        rfq_id = UUID(str(rfq_context["rfq_id"]))
        source_package_refs = rfq_context.get("source_package_refs", [])

        content = {
            "artifact_meta": {
                "artifact_type": "rfq_analytical_record",
                "slice": "rfq.created_vertical_slice_v1",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source_event_id": event_meta["event_id"],
                "source_event_type": event_meta["event_type"],
            },
            "rfq_identifiers": {
                "rfq_id": str(rfq_id),
                "rfq_code": rfq_context.get("rfq_code"),
                "project_title": rfq_context.get("project_title"),
                "client_name": rfq_context.get("client_name"),
            },
            "source_package": {
                "references": source_package_refs,
                "reference_count": len(source_package_refs),
            },
            "lineage": {
                "source_event_id": event_meta["event_id"],
                "source_event_type": event_meta["event_type"],
                "intake_artifact_id": str(intake_artifact.id),
                "intake_artifact_version": intake_artifact.version,
            },
            "completeness_flags": {
                "intake_profile_available": True,
                "briefing_available": True,
                "workbook_profile_available": False,
                "review_report_available": False,
                "outcome_available": False,
            },
            "historical_readiness": False,
            "notes": [
                "Initial analytical seed only.",
                "Historical matching and benchmarking remain unavailable in cold start.",
                "Further enrichment expected on workbook.uploaded and outcome.recorded flows.",
            ],
        }

        artifact = self.datasource.create_new_artifact_version(
            rfq_id=rfq_id,
            artifact_type="rfq_analytical_record",
            content=content,
            status="partial",
            source_event_type=event_meta["event_type"],
            source_event_id=event_meta["event_id"],
        )
        if commit:
            self.datasource.db.commit()
            self.datasource.db.refresh(artifact)
        return artifact
