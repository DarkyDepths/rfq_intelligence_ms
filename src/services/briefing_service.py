"""
briefing_service.py — Intelligence Briefing Generation Service

BACAB Layer: Service (domain logic, called by controllers and event handlers)

Responsibility:
    Generates the intelligence_briefing artifact — the flagship proactive dossier.
    Consumes the rfq_intake_profile and produces a structured briefing with
    active sections (document understanding, compliance/risk) and unavailable
    sections (similarity, cost envelope) clearly marked.

Current status: STUB — not yet implemented.

TODO:
    - Executive summary generation
    - Document understanding section (from intake profile)
    - Compliance/risk flag extraction
    - Section availability matrix (cold-start awareness)
    - Dual format output (summary_text + structured fields)
    - Wire to artifact_datasource for persistence
"""

from datetime import datetime, timezone
from uuid import UUID

from src.datasources.artifact_datasource import ArtifactDatasource


class BriefingService:
    """Generates intelligence_briefing artifacts from intake profiles."""

    def __init__(self, datasource: ArtifactDatasource):
        self.datasource = datasource

    def build_briefing_from_intake(self, intake_artifact, event_meta: dict):
        """Build and persist a truthful intelligence_briefing from intake metadata."""
        intake_content = intake_artifact.content or {}
        canonical = intake_content.get("canonical_project_profile", {})
        gaps = intake_content.get("quality_and_gaps", {}).get("gaps", [])

        rfq_id = UUID(str(intake_artifact.rfq_id))
        executive_summary = (
            "Initial intelligence briefing generated from manager-provided context only. "
            "This deserves review and further enrichment once deeper parsing becomes available."
        )

        content = {
            "artifact_meta": {
                "artifact_type": "intelligence_briefing",
                "slice": "rfq.created_vertical_slice_v1",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source_event_id": event_meta["event_id"],
                "source_event_type": event_meta["event_type"],
            },
            "executive_summary": executive_summary,
            "what_is_known": {
                "rfq_id": str(rfq_id),
                "rfq_code": canonical.get("rfq_code"),
                "project_title": canonical.get("project_title"),
                "client_name": canonical.get("client_name"),
                "source_package_reference": intake_content.get("source_package", {}).get("primary_reference"),
            },
            "what_is_missing": gaps,
            "compliance_flags_or_placeholders": {
                "status": "unavailable",
                "reason": "No deep parsing or standards extraction yet in this slice.",
            },
            "risk_notes_or_placeholders": {
                "status": "limited",
                "notes": [
                    "Risk posture is reference-based only.",
                    "No benchmark or similarity context is available in cold start.",
                ],
            },
            "section_availability": {
                "document_understanding": "limited",
                "compliance_risk": "limited",
                "workbook_comparison": "not_ready",
                "benchmarking": "insufficient_historical_base",
                "similarity": "insufficient_historical_base",
                "cost_envelope": "not_ready",
            },
            "cold_start_limitations": [
                "No workbook uploaded yet.",
                "No historical analytical base available for benchmarking or similarity.",
                "No deep package parsing beyond stable references.",
            ],
            "recommended_next_actions": [
                "Review available RFQ metadata and source package references.",
                "Upload workbook to unlock workbook_profile and review_report slices.",
                "Treat this briefing as preliminary guidance requiring human review.",
            ],
            "review_posture": "supportive_review",
        }

        artifact = self.datasource.create_new_artifact_version(
            rfq_id=rfq_id,
            artifact_type="intelligence_briefing",
            content=content,
            status="partial",
            source_event_type=event_meta["event_type"],
            source_event_id=event_meta["event_id"],
        )
        self.datasource.db.commit()
        self.datasource.db.refresh(artifact)
        return artifact

    async def generate_briefing(self, rfq_id: str) -> None:
        """
        Generate an intelligence briefing for the given RFQ.

        Reads the current rfq_intake_profile, builds briefing sections,
        and persists the intelligence_briefing artifact.

        TODO: Implement briefing generation pipeline.
        """
        raise NotImplementedError("Briefing generation not yet implemented")
