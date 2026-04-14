"""
review_service.py — Workbook Review Report Service

BACAB Layer: Service (domain logic, called by controllers and event handlers)

Responsibility:
    Generates the workbook_review_report — the bridge artifact that compares
    intake intelligence vs workbook intelligence. Contains three anomaly families:
    1. Structural/completeness (fully active in V1)
    2. Benchmark/outlier (schema-ready but dormant in cold start)
    3. Briefing-vs-actual (selectively active — shared field deviations)

    Every finding phrased as "this deserves review," never "this is wrong."

Current status: partially implemented for structural workbook review and honest
cold-start suppression of dormant analysis families.

TODO:
    - Family 1: structural completeness checks (missing sheets, cost lines, totals)
    - Family 2: benchmark/outlier stub (unavailable, insufficient_historical_base)
    - Family 3: briefing-vs-actual deviation detection on shared fields
    - Universal finding object assembly
    - Executive summary and review_recommendations
    - Wire to artifact_datasource for persistence
"""

from datetime import datetime, timezone
from uuid import UUID

from src.datasources.artifact_datasource import ArtifactDatasource


class ReviewService:
    """Generates workbook_review_report artifacts comparing intake vs workbook."""

    def __init__(self, datasource: ArtifactDatasource):
        self.datasource = datasource

    @staticmethod
    def _is_placeholder_or_missing_project_title(value) -> bool:
        if value is None:
            return True

        normalized = str(value).strip()
        if not normalized:
            return True

        lowered = normalized.lower()
        return "pending manager enrichment" in lowered

    def get_current_supporting_artifacts(self, rfq_id: str):
        """Fetch current intake and briefing artifacts for optional overlap checks."""
        rfq_uuid = UUID(str(rfq_id))
        intake = self.datasource.get_current_artifact(rfq_uuid, "rfq_intake_profile")
        briefing = self.datasource.get_current_artifact(rfq_uuid, "intelligence_briefing")
        return intake, briefing

    def build_workbook_review_report(
        self,
        rfq_id: str,
        workbook_profile_artifact,
        event_meta: dict,
        intake_artifact=None,
        briefing_artifact=None,
        commit: bool = True,
    ):
        """Build and persist a truthful workbook_review_report for the first workbook slice."""
        rfq_uuid = UUID(str(rfq_id))
        workbook_content = workbook_profile_artifact.content or {}
        structure = workbook_content.get("workbook_structure", {})

        structural_findings = []
        if structure.get("missing_sheets"):
            structural_findings.append(
                {
                    "finding_id": "struct_missing_sheets",
                    "family": "structural_completeness",
                    "severity": "high",
                    "title": "Expected workbook sheets are missing",
                    "description": "Workbook template recognition indicates missing expected sheets.",
                    "review_posture": "this_deserves_review",
                    "evidence": {
                        "missing_sheets": structure.get("missing_sheets", []),
                    },
                    "confidence": "high",
                    "status": "active",
                    "suppression_reason": None,
                }
            )

        if structure.get("extra_sheets"):
            structural_findings.append(
                {
                    "finding_id": "struct_extra_sheets",
                    "family": "structural_completeness",
                    "severity": "medium",
                    "title": "Unexpected workbook sheets detected",
                    "description": "Workbook contains extra sheets beyond expected structure.",
                    "review_posture": "this_deserves_review",
                    "evidence": {
                        "extra_sheets": structure.get("extra_sheets", []),
                    },
                    "confidence": "medium",
                    "status": "active",
                    "suppression_reason": None,
                }
            )

        if not structural_findings:
            structural_findings.append(
                {
                    "finding_id": "struct_no_major_issues",
                    "family": "structural_completeness",
                    "severity": "low",
                    "title": "No major structural gaps detected",
                    "description": "Workbook structure appears aligned with template expectations for this slice.",
                    "review_posture": "this_deserves_review",
                    "evidence": {
                        "sheet_count_found": structure.get("sheet_count_found"),
                        "expected_sheet_count": structure.get("expected_sheet_count"),
                    },
                    "confidence": "medium",
                    "status": "active",
                    "suppression_reason": None,
                }
            )

        intake_vs_workbook_findings = []
        if intake_artifact is not None:
            intake_title = (
                (intake_artifact.content or {})
                .get("canonical_project_profile", {})
                .get("project_title")
            )
            workbook_title = (
                workbook_content
                .get("canonical_estimate_profile", {})
                .get("detected_identifiers", {})
                .get("project_title")
            )
            if (
                not self._is_placeholder_or_missing_project_title(intake_title)
                and not self._is_placeholder_or_missing_project_title(workbook_title)
                and intake_title != workbook_title
            ):
                intake_vs_workbook_findings.append(
                    {
                        "finding_id": "intake_workbook_project_label_diff",
                        "family": "intake_vs_workbook",
                        "severity": "medium",
                        "title": "Project label differs between intake and workbook context",
                        "description": "Intake and workbook labels differ; this deserves review before assuming linkage.",
                        "review_posture": "this_deserves_review",
                        "evidence": {
                            "intake_project_title": intake_title,
                            "workbook_project_title": workbook_title,
                        },
                        "confidence": "low",
                        "status": "active",
                        "suppression_reason": None,
                    }
                )

        benchmark_outlier_findings = [
            {
                "finding_id": "benchmark_unavailable_cold_start",
                "family": "benchmark_outlier",
                "severity": "low",
                "title": "Benchmark outlier analysis unavailable",
                "description": "Insufficient historical base for benchmark analysis in cold-start mode.",
                "review_posture": "this_deserves_review",
                "evidence": {},
                "confidence": "high",
                "status": "unavailable",
                "suppression_reason": "insufficient_historical_base",
            }
        ]

        content = {
            "artifact_meta": {
                "artifact_type": "workbook_review_report",
                "slice": "workbook.uploaded_vertical_slice_v1",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source_event_id": event_meta["event_id"],
                "source_event_type": event_meta["event_type"],
            },
            "summary": {
                "review_posture": "this_deserves_review",
                "active_findings_count": len(structural_findings) + len(intake_vs_workbook_findings),
                "unavailable_families": ["benchmark_outlier"],
            },
            "structural_completeness_findings": structural_findings,
            "workbook_internal_consistency_findings": [
                {
                    "finding_id": "workbook_pairing_not_assessed",
                    "family": "workbook_internal_consistency",
                    "severity": "low",
                    "title": "Workbook fixture processed as standalone input",
                    "description": "No local fixture-to-fixture linkage is assumed for this workbook sample.",
                    "review_posture": "this_deserves_review",
                    "evidence": workbook_content.get("pairing_validation", {}),
                    "confidence": "high",
                    "status": "active",
                    "suppression_reason": None,
                }
            ],
            "intake_vs_workbook_findings": intake_vs_workbook_findings,
            "benchmark_outlier_findings": benchmark_outlier_findings,
        }

        artifact = self.datasource.create_new_artifact_version(
            rfq_id=rfq_uuid,
            artifact_type="workbook_review_report",
            content=content,
            status="partial",
            source_event_type=event_meta["event_type"],
            source_event_id=event_meta["event_id"],
        )
        if commit:
            self.datasource.db.commit()
            self.datasource.db.refresh(artifact)
        return artifact

    async def generate_review(self, rfq_id: str) -> None:
        """
        Generate a workbook review report for the given RFQ.

        Reads the current rfq_intake_profile and workbook_profile,
        runs comparison checks, and persists the workbook_review_report artifact.

        TODO: Implement review generation pipeline.
        """
        raise NotImplementedError("Review report generation not yet implemented")
