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

    def enrich_analytical_record_from_workbook(
        self,
        rfq_id: str,
        workbook_profile_artifact,
        workbook_review_artifact,
        event_meta: dict,
        commit: bool = True,
    ):
        """Create enriched analytical record version from workbook slice artifacts."""
        rfq_uuid = UUID(str(rfq_id))
        current = self.datasource.get_current_artifact(rfq_uuid, "rfq_analytical_record")

        if current and current.content:
            content = dict(current.content)
        else:
            content = {
                "artifact_meta": {
                    "artifact_type": "rfq_analytical_record",
                    "slice": "workbook.uploaded_vertical_slice_v1",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "source_event_id": event_meta["event_id"],
                    "source_event_type": event_meta["event_type"],
                },
                "rfq_identifiers": {
                    "rfq_id": str(rfq_uuid),
                },
                "completeness_flags": {},
                "historical_readiness": False,
                "notes": [],
            }

        completeness = content.get("completeness_flags", {})
        completeness.update(
            {
                "workbook_profile_available": True,
                "review_report_available": True,
            }
        )
        content["completeness_flags"] = completeness

        content["workbook_enrichment"] = {
            "source_event_id": event_meta["event_id"],
            "source_event_type": event_meta["event_type"],
            "workbook_profile_artifact_id": str(workbook_profile_artifact.id),
            "workbook_profile_version": workbook_profile_artifact.version,
            "workbook_review_artifact_id": str(workbook_review_artifact.id),
            "workbook_review_version": workbook_review_artifact.version,
            "pairing_status": (
                (workbook_profile_artifact.content or {})
                .get("pairing_validation", {})
                .get("pairing_status", "not_assessed")
            ),
            "historical_readiness": False,
        }

        notes = content.get("notes", [])
        notes.append(
            "Workbook slice enrichment added deterministic workbook structure and review signals; benchmark/similarity remain unavailable."
        )
        content["notes"] = notes[-10:]

        artifact = self.datasource.create_new_artifact_version(
            rfq_id=rfq_uuid,
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

    def enrich_analytical_record_from_outcome(
        self,
        rfq_id: str,
        outcome_payload: dict,
        event_meta: dict,
        commit: bool = True,
    ):
        """Create enriched analytical record version from outcome.recorded payload."""
        rfq_uuid = UUID(str(rfq_id))
        current = self.datasource.get_current_artifact(rfq_uuid, "rfq_analytical_record")

        if current and current.content:
            content = dict(current.content)
        else:
            content = {
                "artifact_meta": {
                    "artifact_type": "rfq_analytical_record",
                    "slice": "outcome.recorded_vertical_slice_v1",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "source_event_id": event_meta["event_id"],
                    "source_event_type": event_meta["event_type"],
                },
                "rfq_identifiers": {
                    "rfq_id": str(rfq_uuid),
                },
                "completeness_flags": {
                    "intake_profile_available": False,
                    "briefing_available": False,
                    "workbook_profile_available": False,
                    "review_report_available": False,
                },
                "historical_readiness": False,
                "notes": [
                    "Outcome enrichment created without prior intake/workbook analytical baseline.",
                ],
            }

        completeness = content.get("completeness_flags", {})
        completeness["outcome_available"] = True
        content["completeness_flags"] = completeness

        content["outcome_enrichment"] = {
            "outcome_status": outcome_payload["outcome"],
            "outcome_reason": outcome_payload.get("outcome_reason"),
            "recorded_at": outcome_payload["recorded_at"],
            "outcome_source_event_id": event_meta["event_id"],
            "outcome_source_event_type": event_meta["event_type"],
            "outcome_enriched_at": datetime.now(timezone.utc).isoformat(),
            "learning_loop_status": "closed_for_rfq",
            "benchmark_ready": False,
            "similarity_ready": False,
            "predictive_ready": False,
        }

        notes = content.get("notes", [])
        notes.append(
            "Outcome recorded and linked into analytical memory; predictive, benchmark, and similarity capabilities remain unavailable in V1."
        )
        content["notes"] = notes[-12:]

        artifact = self.datasource.create_new_artifact_version(
            rfq_id=rfq_uuid,
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
