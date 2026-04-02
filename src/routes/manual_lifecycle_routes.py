"""Manual lifecycle trigger routes for UI/dev orchestration flows."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.app_context import get_manual_lifecycle_controller
from src.controllers.manual_lifecycle_controller import ManualLifecycleController

router = APIRouter(prefix="/rfqs/{rfq_id}/trigger", tags=["Intelligence Lifecycle"])


class TriggerWorkbookRequest(BaseModel):
    workbook_ref: str | None = None
    workbook_filename: str | None = None
    uploaded_at: str | None = None


class TriggerOutcomeRequest(BaseModel):
    outcome: Literal["awarded", "lost", "cancelled"]
    recorded_at: str | None = None
    outcome_reason: str | None = None


@router.post("/intake")
async def trigger_intake(
    rfq_id: UUID,
    controller: ManualLifecycleController = Depends(get_manual_lifecycle_controller),
):
    return await controller.trigger_rfq_created(str(rfq_id))


@router.post("/workbook")
async def trigger_workbook(
    rfq_id: UUID,
    body: TriggerWorkbookRequest | None = None,
    controller: ManualLifecycleController = Depends(get_manual_lifecycle_controller),
):
    payload = body or TriggerWorkbookRequest()
    return await controller.trigger_workbook_uploaded(
        rfq_id=str(rfq_id),
        workbook_ref=payload.workbook_ref,
        workbook_filename=payload.workbook_filename,
        uploaded_at=payload.uploaded_at,
    )


@router.post("/outcome")
async def trigger_outcome(
    rfq_id: UUID,
    body: TriggerOutcomeRequest,
    controller: ManualLifecycleController = Depends(get_manual_lifecycle_controller),
):
    return await controller.trigger_outcome_recorded(
        rfq_id=str(rfq_id),
        outcome=body.outcome,
        recorded_at=body.recorded_at,
        outcome_reason=body.outcome_reason,
    )
