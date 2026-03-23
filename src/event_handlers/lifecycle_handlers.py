"""
lifecycle_handlers.py — RFQ Lifecycle Event Handlers

BACAB Layer: Event Handler (inbound adapter — async, NOT HTTP)

Responsibility:
    Handles the 3 V1 event triggers from rfq_manager_ms.
    Each handler orchestrates a sequential build chain through the
    service layer. Event handlers are a SEPARATE inbound adapter
    from HTTP routes — they converge at the services layer.

    Architecture:
        HTTP path:   routes → controllers → services → datasources
        Event path:  event_handlers → services → datasources/connectors

    Important: These cascades run as sequential steps within the same handler,
    NOT as separate events triggering each other (avoids infinite loops and
    race conditions).

Current status: STUB — not yet wired to an event bus.

TODO:
    - Wire to event bus consumer (polling, webhook, or message queue)
    - Implement error handling and partial-completion tracking
    - Add idempotency checks for duplicate events
"""

from src.services.intake_service import IntakeService
from src.services.briefing_service import BriefingService
from src.services.workbook_service import WorkbookService
from src.services.review_service import ReviewService
from src.services.snapshot_service import SnapshotService
from src.services.enrichment_service import EnrichmentService


class LifecycleHandlers:
    """Handles rfq_manager_ms lifecycle events and triggers intelligence build chains."""

    def __init__(
        self,
        intake_service: IntakeService,
        briefing_service: BriefingService,
        workbook_service: WorkbookService,
        review_service: ReviewService,
        snapshot_service: SnapshotService,
        enrichment_service: EnrichmentService,
    ):
        self.intake_service = intake_service
        self.briefing_service = briefing_service
        self.workbook_service = workbook_service
        self.review_service = review_service
        self.snapshot_service = snapshot_service
        self.enrichment_service = enrichment_service

    async def handle_rfq_created(self, rfq_id: str, event_payload: dict) -> None:
        """
        Triggered by: rfq.created event from rfq_manager_ms

        Chain (sequential):
            1. Fetch metadata → build rfq_intake_profile
            2. Build intelligence_briefing
            3. Create rfq_analytical_record stub
            4. Update rfq_intelligence_snapshot

        TODO: Implement sequential build chain.
        """
        pass

    async def handle_workbook_uploaded(self, rfq_id: str, event_payload: dict) -> None:
        """
        Triggered by: workbook.uploaded event from rfq_manager_ms

        Chain (sequential):
            1. Fetch workbook ref → build workbook_profile
            2. Build workbook_review_report
            3. Enrich rfq_analytical_record
            4. Update rfq_intelligence_snapshot

        TODO: Implement sequential build chain.
        """
        pass

    async def handle_outcome_recorded(self, rfq_id: str, event_payload: dict) -> None:
        """
        Triggered by: outcome.recorded event from rfq_manager_ms

        Chain (sequential):
            1. Read outcome
            2. Enrich rfq_analytical_record
            3. Refresh snapshot if needed

        TODO: Implement sequential build chain.
        """
        pass
