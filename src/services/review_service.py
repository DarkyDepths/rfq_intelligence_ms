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

Current status: STUB — not yet implemented.

TODO:
    - Family 1: structural completeness checks (missing sheets, cost lines, totals)
    - Family 2: benchmark/outlier stub (unavailable, insufficient_historical_base)
    - Family 3: briefing-vs-actual deviation detection on shared fields
    - Universal finding object assembly
    - Executive summary and review_recommendations
    - Wire to artifact_datasource for persistence
"""

from src.datasources.artifact_datasource import ArtifactDatasource


class ReviewService:
    """Generates workbook_review_report artifacts comparing intake vs workbook."""

    def __init__(self, datasource: ArtifactDatasource):
        self.datasource = datasource

    async def generate_review(self, rfq_id: str) -> None:
        """
        Generate a workbook review report for the given RFQ.

        Reads the current rfq_intake_profile and workbook_profile,
        runs comparison checks, and persists the workbook_review_report artifact.

        TODO: Implement review generation pipeline.
        """
        raise NotImplementedError("Review report generation not yet implemented")
