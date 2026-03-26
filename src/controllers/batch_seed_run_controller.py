"""Controller for operational read/query of historical batch-seed runs."""

from __future__ import annotations

from src.services.batch_seed_run_read_service import BatchSeedRunReadService


class BatchSeedRunController:
    def __init__(self, read_service: BatchSeedRunReadService):
        self.read_service = read_service

    def get_run(self, run_id: str) -> dict:
        return self.read_service.get_run(run_id)

    def list_recent_runs(self, limit: int = 20, overall_status: str | None = None) -> dict:
        return self.read_service.list_recent_runs(limit=limit, overall_status=overall_status)
