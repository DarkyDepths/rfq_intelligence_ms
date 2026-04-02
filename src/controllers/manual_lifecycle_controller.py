"""Controller for manual lifecycle trigger routes exposed to the UI/dev flows."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from src.connectors.manager_connector import ManagerConnector
from src.event_handlers.lifecycle_handlers import LifecycleHandlers


class ManualLifecycleController:
    def __init__(
        self,
        lifecycle_handlers: LifecycleHandlers,
        manager_connector: ManagerConnector,
    ):
        self.lifecycle_handlers = lifecycle_handlers
        self.manager_connector = manager_connector

    @staticmethod
    def _event_envelope(event_type: str, payload: dict) -> dict:
        return {
            "event_id": f"manual-ui:{event_type}:{uuid4()}",
            "event_type": event_type,
            "event_version": "v1",
            "emitted_at": datetime.now(timezone.utc).isoformat(),
            "producer": "rfq_ui_ms.manual_trigger",
            "payload": payload,
        }

    async def trigger_rfq_created(self, rfq_id: str) -> dict:
        event = self._event_envelope(
            "rfq.created",
            {
                "rfq_id": rfq_id,
            },
        )
        return await self.lifecycle_handlers.handle_rfq_created(event)

    async def trigger_workbook_uploaded(
        self,
        rfq_id: str,
        workbook_ref: str | None = None,
        workbook_filename: str | None = None,
        uploaded_at: str | None = None,
    ) -> dict:
        workbook_context = await self.manager_connector.get_workbook_context(
            rfq_id=rfq_id,
            workbook_ref=workbook_ref,
            workbook_filename=workbook_filename,
            uploaded_at=uploaded_at,
        )
        event = self._event_envelope(
            "workbook.uploaded",
            {
                "rfq_id": rfq_id,
                "workbook_ref": workbook_context["workbook_ref"],
                "workbook_filename": workbook_context["workbook_filename"],
                "uploaded_at": workbook_context.get("uploaded_at"),
            },
        )
        return await self.lifecycle_handlers.handle_workbook_uploaded(event)

    async def trigger_outcome_recorded(
        self,
        rfq_id: str,
        outcome: str,
        recorded_at: str | None = None,
        outcome_reason: str | None = None,
    ) -> dict:
        event = self._event_envelope(
            "outcome.recorded",
            {
                "rfq_id": rfq_id,
                "outcome": outcome,
                "recorded_at": recorded_at or datetime.now(timezone.utc).isoformat(),
                "outcome_reason": outcome_reason,
            },
        )
        return await self.lifecycle_handlers.handle_outcome_recorded(event)
