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
from src.services.analytical_record_service import AnalyticalRecordService
from src.utils.exceptions import BadRequestError


class LifecycleHandlers:
    """Handles rfq_manager_ms lifecycle events and triggers intelligence build chains."""

    def __init__(
        self,
        intake_service: IntakeService,
        briefing_service: BriefingService,
        workbook_service: WorkbookService,
        review_service: ReviewService,
        snapshot_service: SnapshotService,
        analytical_record_service: AnalyticalRecordService,
    ):
        self.intake_service = intake_service
        self.briefing_service = briefing_service
        self.workbook_service = workbook_service
        self.review_service = review_service
        self.snapshot_service = snapshot_service
        self.analytical_record_service = analytical_record_service

    async def handle_rfq_created(self, event: dict) -> dict:
        """
        Triggered by: rfq.created event from rfq_manager_ms

        Chain (sequential):
            1. Fetch metadata → build rfq_intake_profile
            2. Build intelligence_briefing
            3. Create rfq_analytical_record stub
            4. Update rfq_intelligence_snapshot

        Sequentially builds intake, briefing, analytical stub, then snapshot.
        """
        required_envelope_fields = [
            "event_id",
            "event_type",
            "event_version",
            "emitted_at",
            "producer",
            "payload",
        ]
        missing = [field for field in required_envelope_fields if field not in event]
        if missing:
            raise BadRequestError(f"Missing required event fields: {', '.join(missing)}")

        event_type = event["event_type"]
        if event_type != "rfq.created":
            return {
                "status": "ignored",
                "reason": "unsupported_event_type",
                "event_type": event_type,
            }

        payload = event.get("payload") or {}
        rfq_id = payload.get("rfq_id")
        if not rfq_id:
            raise BadRequestError("Missing required payload field: rfq_id")

        event_meta = {
            "event_id": event["event_id"],
            "event_type": event_type,
            "event_version": event["event_version"],
            "emitted_at": event["emitted_at"],
            "producer": event["producer"],
        }

        rfq_context = await self.intake_service.get_rfq_context(rfq_id)
        intake_artifact = self.intake_service.build_intake_profile_from_rfq_created(
            rfq_context=rfq_context,
            event_meta=event_meta,
        )
        briefing_artifact = self.briefing_service.build_briefing_from_intake(
            intake_artifact=intake_artifact,
            event_meta=event_meta,
        )
        analytical_artifact = self.analytical_record_service.build_initial_analytical_record(
            rfq_context=rfq_context,
            intake_artifact=intake_artifact,
            event_meta=event_meta,
        )
        snapshot_artifact = self.snapshot_service.rebuild_snapshot_for_rfq(
            rfq_id=rfq_id,
            source_event_meta=event_meta,
        )

        return {
            "status": "processed",
            "event_id": event_meta["event_id"],
            "event_type": event_type,
            "rfq_id": rfq_id,
            "artifacts": {
                "rfq_intake_profile": {
                    "id": str(intake_artifact.id),
                    "version": intake_artifact.version,
                    "status": intake_artifact.status,
                },
                "intelligence_briefing": {
                    "id": str(briefing_artifact.id),
                    "version": briefing_artifact.version,
                    "status": briefing_artifact.status,
                },
                "rfq_analytical_record": {
                    "id": str(analytical_artifact.id),
                    "version": analytical_artifact.version,
                    "status": analytical_artifact.status,
                },
                "rfq_intelligence_snapshot": {
                    "id": str(snapshot_artifact.id),
                    "version": snapshot_artifact.version,
                    "status": snapshot_artifact.status,
                },
            },
        }

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
