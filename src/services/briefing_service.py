"""
briefing_service.py — Intelligence Briefing Generation Service

BACAB Layer: Service (domain logic, called by controllers and event handlers)

Responsibility:
    Generates the intelligence_briefing artifact — the flagship proactive dossier.
    Consumes the rfq_intake_profile and produces a structured briefing with
    active sections (document understanding, compliance/risk) and unavailable
    sections (similarity, cost envelope) clearly marked.

Current status: partially implemented for the current intake-driven V1 briefing slice.

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

    def build_briefing_from_intake(
        self,
        intake_artifact,
        event_meta: dict,
        commit: bool = True,
    ):
        """Build and persist a truthful intelligence_briefing from intake metadata."""
        intake_content = intake_artifact.content or {}
        rfq_id = UUID(str(intake_artifact.rfq_id))
        if intake_content.get("package_structure", {}).get("status") == "parsed":
            content = self._build_deterministic_enriched_content(
                rfq_id=rfq_id,
                intake_content=intake_content,
                event_meta=event_meta,
            )
        else:
            content = self._build_stub_content(
                rfq_id=rfq_id,
                intake_content=intake_content,
                event_meta=event_meta,
            )

        artifact = self.datasource.create_new_artifact_version(
            rfq_id=rfq_id,
            artifact_type="intelligence_briefing",
            content=content,
            status="partial",
            source_event_type=event_meta["event_type"],
            source_event_id=event_meta["event_id"],
        )
        if commit:
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

    def _build_stub_content(self, rfq_id: UUID, intake_content: dict, event_meta: dict) -> dict:
        canonical = intake_content.get("canonical_project_profile", {})
        gaps = intake_content.get("quality_and_gaps", {}).get("gaps", [])

        executive_summary = (
            "Initial intelligence briefing generated from manager-provided context only. "
            "This deserves review and further enrichment once deeper parsing becomes available."
        )

        return {
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

    def _build_deterministic_enriched_content(self, rfq_id: UUID, intake_content: dict, event_meta: dict) -> dict:
        canonical = intake_content.get("canonical_project_profile", {})
        package_identity = intake_content.get("package_identity", {})
        document_understanding = intake_content.get("document_understanding", {})
        quality_and_gaps = intake_content.get("quality_and_gaps", {})
        downstream = intake_content.get("downstream_readiness", {})
        standards_profile = document_understanding.get("standards_profile") or {}
        bom_profile = document_understanding.get("bom_profile") or {}
        rvl_profile = document_understanding.get("rvl_profile") or {}
        sa175_profile = document_understanding.get("sa175_profile")
        compliance_profile = document_understanding.get("compliance_profile")
        deviation_profile = document_understanding.get("deviation_profile")
        review_flags = quality_and_gaps.get("review_flags", [])
        parser_report_status = intake_content.get("parser_report_status")

        executive_summary = (
            "Deterministic-enriched v1 briefing generated from package structure, filenames, spreadsheets, "
            "and cross-check results. Semantic PDF understanding remains deferred."
        )

        tag_numbers = canonical.get("tag_numbers", [])
        design_codes = canonical.get("design_codes", [])
        standards_counts = canonical.get("standards_count", {})
        known_points = [
            f"MR {package_identity.get('mr_number_short')}" if package_identity.get("mr_number_short") else None,
            f"{len(tag_numbers)} BOM tag(s)" if tag_numbers else None,
            f"{rvl_profile.get('total_vendors', 0)} RVL vendor(s)" if rvl_profile else None,
            (
                f"Standards families: SAMSS {standards_counts.get('samss', 0)}, "
                f"SAES {standards_counts.get('saes', 0)}, "
                f"SAEP {standards_counts.get('saep', 0)}, "
                f"STD DWG {standards_counts.get('std_dwg', 0)}"
                if standards_counts
                else None
            ),
        ]

        recommended_actions = [
            "Review deterministic package findings and cross-check warnings before issuing decisions.",
            "Use workbook upload to add commercial comparison and review coverage.",
            "Treat QAQC/specs/general-requirement semantics as still deferred pending later phases.",
        ]
        if review_flags:
            recommended_actions.insert(0, "Resolve the highlighted package review flags before downstream use.")

        return {
            "artifact_meta": {
                "artifact_type": "intelligence_briefing",
                "slice": "rfq.created_deterministic_enriched_v1",
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
                "mr_number": package_identity.get("mr_number"),
                "material_description": package_identity.get("material_description"),
                "tag_numbers": tag_numbers,
                "design_codes": design_codes,
                "vendor_count": rvl_profile.get("total_vendors"),
                "standards_count": standards_counts,
                "known_points": [value for value in known_points if value is not None],
            },
            "what_is_missing": quality_and_gaps.get("gaps", []),
            "compliance_flags_or_placeholders": {
                "status": "deterministic_enriched",
                "standards_families": {
                    "samss": standards_profile.get("samss_count", 0),
                    "saes": standards_profile.get("saes_count", 0),
                    "saep": standards_profile.get("saep_count", 0),
                    "std_dwg": standards_profile.get("std_dwg_count", 0),
                },
                "sa175_form_count": sa175_profile.get("total_count", 0) if sa175_profile else 0,
                "compliance_items_present": compliance_profile is not None,
                "deviation_list_present": deviation_profile is not None,
                "review_flags": review_flags,
                "scope_boundary": "Deterministic package extraction only; semantic document understanding deferred.",
            },
            "risk_notes_or_placeholders": {
                "status": "partial_deterministic",
                "notes": [
                    "Risk posture is derived from deterministic package facts and cross-checks only.",
                    *(
                        [f"Review flag: {flag}" for flag in review_flags]
                        if review_flags
                        else ["No review flags were raised by the deterministic intake artifact."]
                    ),
                    "No semantic interpretation of QAQC/specifications/general requirements is included in this version.",
                ],
            },
            "section_availability": {
                "document_understanding": "partial_deterministic",
                "compliance_risk": "partial_deterministic",
                "workbook_comparison": "ready_from_package_intake" if downstream.get("workbook_comparison_ready") else "not_ready",
                "benchmarking": "insufficient_historical_base",
                "similarity": "insufficient_historical_base",
                "cost_envelope": "not_ready",
            },
            "cold_start_limitations": [
                "No historical analytical base available for benchmarking or similarity.",
                "No semantic PDF understanding is included in deterministic-enriched v1.",
                "QAQC/specifications/general requirements remain placeholder-only until later phases.",
            ],
            "recommended_next_actions": recommended_actions,
            "review_posture": "supportive_review",
            "package_readiness": {
                "parser_report_status": parser_report_status,
                "briefing_ready": downstream.get("briefing_ready"),
                "requires_human_review": downstream.get("requires_human_review"),
            },
        }
