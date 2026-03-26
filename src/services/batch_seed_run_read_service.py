"""Operational read service for historical batch-seed run summaries."""

from __future__ import annotations

from src.datasources.batch_seed_run_datasource import BatchSeedRunDatasource
from src.utils.exceptions import NotFoundError


class BatchSeedRunReadService:
    def __init__(self, datasource: BatchSeedRunDatasource):
        self.datasource = datasource

    @staticmethod
    def _to_lightweight_dict(run) -> dict:
        return {
            "run_id": run.run_id,
            "run_type": run.run_type,
            "parser_version": run.parser_version,
            "freeze_version": run.freeze_version,
            "started_at": run.started_at.isoformat(),
            "completed_at": run.completed_at.isoformat(),
            "duration_seconds": run.duration_seconds,
            "persist_artifacts": run.persist_artifacts,
            "input_scope_root": run.input_scope_root,
            "total_files": run.total_files,
            "parsed_ok": run.parsed_ok,
            "parsed_with_warnings": run.parsed_with_warnings,
            "failed": run.failed,
            "skipped_invalid": run.skipped_invalid,
            "persisted_ok": run.persisted_ok,
            "persisted_failed": run.persisted_failed,
            "rollback_count": run.rollback_count,
            "overall_status": run.overall_status,
            "failure_samples": run.failure_samples,
            "warning_samples": run.warning_samples,
            "created_at": run.created_at.isoformat(),
        }

    @staticmethod
    def _to_list_item(run) -> dict:
        return {
            "run_id": run.run_id,
            "run_type": run.run_type,
            "started_at": run.started_at.isoformat(),
            "completed_at": run.completed_at.isoformat(),
            "duration_seconds": run.duration_seconds,
            "persist_artifacts": run.persist_artifacts,
            "input_scope_root": run.input_scope_root,
            "total_files": run.total_files,
            "parsed_ok": run.parsed_ok,
            "parsed_with_warnings": run.parsed_with_warnings,
            "failed": run.failed,
            "skipped_invalid": run.skipped_invalid,
            "persisted_ok": run.persisted_ok,
            "persisted_failed": run.persisted_failed,
            "rollback_count": run.rollback_count,
            "overall_status": run.overall_status,
        }

    def get_run(self, run_id: str) -> dict:
        run = self.datasource.get_by_run_id(run_id)
        if not run:
            raise NotFoundError(f"No batch seed run found for run_id '{run_id}'")
        return self._to_lightweight_dict(run)

    def list_recent_runs(self, limit: int = 20, overall_status: str | None = None) -> dict:
        runs = self.datasource.list_recent_runs(limit=limit, overall_status=overall_status)
        return {"runs": [self._to_list_item(run) for run in runs]}
