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

Current status: operational for manual-trigger and direct-handler flows; not yet
wired to an autonomous event bus consumer.

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
from src.services.event_processing_service import EventProcessingService
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
        event_processing_service: EventProcessingService,
    ):
        self.intake_service = intake_service
        self.briefing_service = briefing_service
        self.workbook_service = workbook_service
        self.review_service = review_service
        self.snapshot_service = snapshot_service
        self.analytical_record_service = analytical_record_service
        self.event_processing_service = event_processing_service

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

        processing_action, processing_record = self.event_processing_service.begin_processing(
            event_id=event_meta["event_id"],
            event_type=event_meta["event_type"],
            rfq_id=rfq_id,
        )

        if processing_action == "duplicate_completed":
            return {
                "status": "duplicate",
                "reason": "already_completed",
                "event_id": event_meta["event_id"],
                "event_type": event_type,
                "rfq_id": rfq_id,
            }

        if processing_action == "in_progress":
            return {
                "status": "ignored",
                "reason": "already_processing",
                "event_id": event_meta["event_id"],
                "event_type": event_type,
                "rfq_id": rfq_id,
            }

        try:
            rfq_context = await self.intake_service.get_rfq_context(rfq_id)
            intake_artifact = self.intake_service.build_intake_profile_from_rfq_created(
                rfq_context=rfq_context,
                event_meta=event_meta,
                commit=False,
            )
            briefing_artifact = self.briefing_service.build_briefing_from_intake(
                intake_artifact=intake_artifact,
                event_meta=event_meta,
                commit=False,
            )
            analytical_artifact = self.analytical_record_service.build_initial_analytical_record(
                rfq_context=rfq_context,
                intake_artifact=intake_artifact,
                event_meta=event_meta,
                commit=False,
            )
            snapshot_artifact = self.snapshot_service.rebuild_snapshot_for_rfq(
                rfq_id=rfq_id,
                source_event_meta=event_meta,
                commit=False,
            )

            self.event_processing_service.mark_completed(event_id=event_meta["event_id"])
        except Exception as exc:
            self.event_processing_service.rollback_active_transaction()
            self.event_processing_service.mark_failed(
                event_id=event_meta["event_id"],
                error_message=str(exc),
            )
            raise

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

    async def handle_workbook_uploaded(self, event: dict) -> dict:
        """
        Triggered by: workbook.uploaded event from rfq_manager_ms

        Chain (sequential):
            1. Fetch workbook ref → build workbook_profile
            2. Build workbook_review_report
            3. Enrich rfq_analytical_record
            4. Update rfq_intelligence_snapshot

        Sequentially builds workbook profile/review, enriches analytical record,
        then refreshes snapshot under idempotent transactional orchestration.
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
        if event_type != "workbook.uploaded":
            return {
                "status": "ignored",
                "reason": "unsupported_event_type",
                "event_type": event_type,
            }

        payload = event.get("payload") or {}
        required_payload = ["rfq_id", "workbook_ref", "workbook_filename", "uploaded_at"]
        missing_payload = [field for field in required_payload if not payload.get(field)]
        if missing_payload:
            raise BadRequestError(f"Missing required payload fields: {', '.join(missing_payload)}")

        rfq_id = payload["rfq_id"]

        event_meta = {
            "event_id": event["event_id"],
            "event_type": event_type,
            "event_version": event["event_version"],
            "emitted_at": event["emitted_at"],
            "producer": event["producer"],
        }

        processing_action, _ = self.event_processing_service.begin_processing(
            event_id=event_meta["event_id"],
            event_type=event_meta["event_type"],
            rfq_id=rfq_id,
        )

        parser_artifacts_created = False

        if processing_action == "duplicate_completed":
            return {
                "status": "duplicate",
                "reason": "already_completed",
                "event_id": event_meta["event_id"],
                "event_type": event_type,
                "rfq_id": rfq_id,
            }

        if processing_action == "in_progress":
            return {
                "status": "ignored",
                "reason": "already_processing",
                "event_id": event_meta["event_id"],
                "event_type": event_type,
                "rfq_id": rfq_id,
            }

        try:
            workbook_context = await self.workbook_service.get_workbook_context(
                rfq_id=rfq_id,
                workbook_ref=payload["workbook_ref"],
                workbook_filename=payload["workbook_filename"],
                uploaded_at=payload["uploaded_at"],
            )
            parser_artifacts = self.workbook_service.build_workbook_parser_artifacts_from_uploaded_event(
                workbook_context=workbook_context,
                event_meta=event_meta,
                commit=False,
            )
            parser_artifacts_created = True

            workbook_profile_artifact = parser_artifacts["workbook_profile"]
            cost_breakdown_artifact = parser_artifacts["cost_breakdown_profile"]
            parser_report_artifact = parser_artifacts["parser_report"]
            parser_failed = parser_report_artifact.status == "failed"

            workbook_review_artifact = None
            analytical_artifact = None
            if not parser_failed:
                intake_artifact, briefing_artifact = self.review_service.get_current_supporting_artifacts(rfq_id)
                workbook_review_artifact = self.review_service.build_workbook_review_report(
                    rfq_id=rfq_id,
                    workbook_profile_artifact=workbook_profile_artifact,
                    event_meta=event_meta,
                    intake_artifact=intake_artifact,
                    briefing_artifact=briefing_artifact,
                    commit=False,
                )

                analytical_artifact = self.analytical_record_service.enrich_analytical_record_from_workbook(
                    rfq_id=rfq_id,
                    workbook_profile_artifact=workbook_profile_artifact,
                    workbook_review_artifact=workbook_review_artifact,
                    event_meta=event_meta,
                    commit=False,
                )

            snapshot_artifact = self.snapshot_service.rebuild_snapshot_for_rfq(
                rfq_id=rfq_id,
                source_event_meta=event_meta,
                commit=False,
            )

            self.event_processing_service.mark_completed(event_id=event_meta["event_id"])
        except Exception as exc:
            self.event_processing_service.rollback_active_transaction()

            if not parser_artifacts_created:
                self.workbook_service.persist_parser_failure_artifact(
                    rfq_id=rfq_id,
                    event_meta=event_meta,
                    workbook_ref=payload.get("workbook_ref"),
                    workbook_filename=payload.get("workbook_filename"),
                    uploaded_at=payload.get("uploaded_at"),
                    error_code="WORKBOOK_PARSE_PIPELINE_FAILED",
                    error_message=str(exc),
                    commit=True,
                )

            self.event_processing_service.mark_failed(
                event_id=event_meta["event_id"],
                error_message=str(exc),
            )
            raise

        return {
            "status": "processed_with_failures" if parser_failed else "processed",
            "event_id": event_meta["event_id"],
            "event_type": event_type,
            "rfq_id": rfq_id,
            "artifacts": {
                "workbook_profile": {
                    "id": str(workbook_profile_artifact.id),
                    "version": workbook_profile_artifact.version,
                    "status": workbook_profile_artifact.status,
                },
                "cost_breakdown_profile": {
                    "id": str(cost_breakdown_artifact.id),
                    "version": cost_breakdown_artifact.version,
                    "status": cost_breakdown_artifact.status,
                },
                "parser_report": {
                    "id": str(parser_report_artifact.id),
                    "version": parser_report_artifact.version,
                    "status": parser_report_artifact.status,
                },
                "workbook_review_report": {
                    "id": str(workbook_review_artifact.id) if workbook_review_artifact else None,
                    "version": workbook_review_artifact.version if workbook_review_artifact else None,
                    "status": workbook_review_artifact.status if workbook_review_artifact else "skipped",
                },
                "rfq_analytical_record": {
                    "id": str(analytical_artifact.id) if analytical_artifact else None,
                    "version": analytical_artifact.version if analytical_artifact else None,
                    "status": analytical_artifact.status if analytical_artifact else "skipped",
                },
                "rfq_intelligence_snapshot": {
                    "id": str(snapshot_artifact.id),
                    "version": snapshot_artifact.version,
                    "status": snapshot_artifact.status,
                },
            },
        }

    async def handle_outcome_recorded(self, event: dict) -> dict:
        """
        Triggered by: outcome.recorded event from rfq_manager_ms

        Chain (sequential):
            1. Read outcome
            2. Enrich rfq_analytical_record
            3. Refresh snapshot if needed

        Reads outcome payload, enriches analytical record, and refreshes snapshot
        under idempotent transactional orchestration.
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
        if event_type != "outcome.recorded":
            return {
                "status": "ignored",
                "reason": "unsupported_event_type",
                "event_type": event_type,
            }

        payload = event.get("payload") or {}
        required_payload = ["rfq_id", "outcome", "recorded_at"]
        missing_payload = [field for field in required_payload if not payload.get(field)]
        if missing_payload:
            raise BadRequestError(f"Missing required payload fields: {', '.join(missing_payload)}")

        if payload["outcome"] not in {"awarded", "lost", "cancelled"}:
            raise BadRequestError("Invalid outcome value; supported values are awarded, lost, cancelled")

        rfq_id = payload["rfq_id"]

        event_meta = {
            "event_id": event["event_id"],
            "event_type": event_type,
            "event_version": event["event_version"],
            "emitted_at": event["emitted_at"],
            "producer": event["producer"],
        }

        processing_action, _ = self.event_processing_service.begin_processing(
            event_id=event_meta["event_id"],
            event_type=event_meta["event_type"],
            rfq_id=rfq_id,
        )

        if processing_action == "duplicate_completed":
            return {
                "status": "duplicate",
                "reason": "already_completed",
                "event_id": event_meta["event_id"],
                "event_type": event_type,
                "rfq_id": rfq_id,
            }

        if processing_action == "in_progress":
            return {
                "status": "ignored",
                "reason": "already_processing",
                "event_id": event_meta["event_id"],
                "event_type": event_type,
                "rfq_id": rfq_id,
            }

        try:
            analytical_artifact = self.analytical_record_service.enrich_analytical_record_from_outcome(
                rfq_id=rfq_id,
                outcome_payload=payload,
                event_meta=event_meta,
                commit=False,
            )

            snapshot_artifact = self.snapshot_service.rebuild_snapshot_for_rfq(
                rfq_id=rfq_id,
                source_event_meta=event_meta,
                commit=False,
            )

            self.event_processing_service.mark_completed(event_id=event_meta["event_id"])
        except Exception as exc:
            self.event_processing_service.rollback_active_transaction()
            self.event_processing_service.mark_failed(
                event_id=event_meta["event_id"],
                error_message=str(exc),
            )
            raise

        return {
            "status": "processed",
            "event_id": event_meta["event_id"],
            "event_type": event_type,
            "rfq_id": rfq_id,
            "artifacts": {
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
