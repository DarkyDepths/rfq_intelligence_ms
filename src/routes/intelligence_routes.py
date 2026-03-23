"""
intelligence_routes.py — V1 Intelligence API Endpoints

BACAB Layer: Route (API layer — HTTP endpoint definitions)

Responsibility:
    Defines the 7 V1 endpoints for rfq_intelligence_ms.
    Routes are thin — they receive HTTP requests, extract parameters,
    and delegate to controllers. No business logic here.

    Endpoints:
        GET  /rfqs/{rfq_id}/snapshot          → rfq_intelligence_snapshot
        GET  /rfqs/{rfq_id}/briefing          → intelligence_briefing
        GET  /rfqs/{rfq_id}/workbook-profile  → workbook_profile
        GET  /rfqs/{rfq_id}/workbook-review   → workbook_review_report
        POST /rfqs/{rfq_id}/reprocess/intake  → manual intake reprocess
        POST /rfqs/{rfq_id}/reprocess/workbook → manual workbook reprocess
        GET  /rfqs/{rfq_id}/artifacts         → artifact index

Current status: COMPLETE for skeleton — wired to controllers with stub behavior.
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from src.app_context import get_intelligence_controller, get_reprocess_controller
from src.controllers.intelligence_controller import IntelligenceController
from src.controllers.reprocess_controller import ReprocessController

router = APIRouter(prefix="/rfqs/{rfq_id}", tags=["Intelligence"])


# ── Single-Artifact GET Endpoints ─────────────────────
# Return 404 with detail message if no current artifact exists.

@router.get("/snapshot")
def get_snapshot(
    rfq_id: UUID,
    controller: IntelligenceController = Depends(get_intelligence_controller),
):
    """Returns the current rfq_intelligence_snapshot for the given RFQ."""
    return controller.get_artifact(rfq_id, "rfq_intelligence_snapshot")


@router.get("/briefing")
def get_briefing(
    rfq_id: UUID,
    controller: IntelligenceController = Depends(get_intelligence_controller),
):
    """Returns the current intelligence_briefing for the given RFQ."""
    return controller.get_artifact(rfq_id, "intelligence_briefing")


@router.get("/workbook-profile")
def get_workbook_profile(
    rfq_id: UUID,
    controller: IntelligenceController = Depends(get_intelligence_controller),
):
    """Returns the current workbook_profile for the given RFQ."""
    return controller.get_artifact(rfq_id, "workbook_profile")


@router.get("/workbook-review")
def get_workbook_review(
    rfq_id: UUID,
    controller: IntelligenceController = Depends(get_intelligence_controller),
):
    """Returns the current workbook_review_report for the given RFQ."""
    return controller.get_artifact(rfq_id, "workbook_review_report")


# ── Collection Endpoint ──────────────────────────────
# Returns 200 with empty list if no artifacts exist (not 404).

@router.get("/artifacts")
def list_artifacts(
    rfq_id: UUID,
    controller: IntelligenceController = Depends(get_intelligence_controller),
):
    """Returns all artifacts (all types, all versions) for the given RFQ."""
    return controller.list_artifacts(rfq_id)


# ── Reprocess Action Endpoints ────────────────────────
# Return 202 Accepted — processing happens asynchronously.

@router.post("/reprocess/intake", status_code=202)
def reprocess_intake(
    rfq_id: UUID,
    controller: ReprocessController = Depends(get_reprocess_controller),
):
    """Manual re-run of intake parsing for the given RFQ."""
    return controller.reprocess_intake(str(rfq_id))


@router.post("/reprocess/workbook", status_code=202)
def reprocess_workbook(
    rfq_id: UUID,
    controller: ReprocessController = Depends(get_reprocess_controller),
):
    """Manual re-run of workbook parsing for the given RFQ."""
    return controller.reprocess_workbook(str(rfq_id))
