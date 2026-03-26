"""Operational read/query routes for historical batch-seed run summaries."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from src.app_context import get_batch_seed_run_controller
from src.controllers.batch_seed_run_controller import BatchSeedRunController

router = APIRouter(prefix="/batch-seed-runs", tags=["Batch Seed Runs"])


@router.get("/{run_id}")
def get_batch_seed_run(
    run_id: str,
    controller: BatchSeedRunController = Depends(get_batch_seed_run_controller),
):
    return controller.get_run(run_id)


@router.get("")
def list_batch_seed_runs(
    limit: int = Query(default=20, ge=1, le=100),
    overall_status: str | None = Query(default=None),
    controller: BatchSeedRunController = Depends(get_batch_seed_run_controller),
):
    return controller.list_recent_runs(limit=limit, overall_status=overall_status)
