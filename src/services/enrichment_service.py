"""
enrichment_service.py — Analytical Record Enrichment Service

BACAB Layer: Service (domain logic, called by controllers and event handlers)

Responsibility:
    Manages the rfq_analytical_record lifecycle — the seed for future
    analytical store. Not user-facing.

    Lifecycle:
        1. Created as stub on rfq.created with intake-extracted normalized
           features and readiness flags
        2. Enriched on workbook.uploaded with workbook normalized features
           and cost metrics
        3. Enriched again on outcome.recorded with result/outcome fields
           and provenance

    Every new RFQ enriches this store from its first moment in the system,
    so future matching and benchmarking improve over time.

Current status: STUB — not yet implemented.

TODO:
    - Stub creation from intake profile features
    - Workbook enrichment with cost metrics and normalized features
    - Outcome enrichment with result/outcome fields
    - Wire to artifact_datasource for persistence
"""

from src.datasources.artifact_datasource import ArtifactDatasource


class EnrichmentService:
    """Manages rfq_analytical_record lifecycle and enrichment."""

    def __init__(self, datasource: ArtifactDatasource):
        self.datasource = datasource

    async def create_analytical_stub(self, rfq_id: str) -> None:
        """
        Create an initial analytical record stub from intake features.

        Called during the rfq.created event chain, after intake_profile
        and briefing have been generated.

        TODO: Implement analytical record stub creation.
        """
        raise NotImplementedError("Analytical record creation not yet implemented")

    async def enrich_from_workbook(self, rfq_id: str) -> None:
        """
        Enrich the analytical record with workbook features.

        Called during the workbook.uploaded event chain, after workbook_profile
        and review_report have been generated.

        TODO: Implement workbook enrichment.
        """
        raise NotImplementedError("Workbook enrichment not yet implemented")

    async def enrich_from_outcome(self, rfq_id: str) -> None:
        """
        Enrich the analytical record with outcome data.

        Called during the outcome.recorded event chain.

        TODO: Implement outcome enrichment.
        """
        raise NotImplementedError("Outcome enrichment not yet implemented")
