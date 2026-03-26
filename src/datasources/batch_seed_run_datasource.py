"""Datasource for batch seeding run-level summary records."""

from __future__ import annotations

from src.models.batch_seed_run import BatchSeedRun


class BatchSeedRunDatasource:
    def __init__(self, db):
        self.db = db

    def create_run_summary(self, summary: dict, commit: bool = True) -> BatchSeedRun:
        record = BatchSeedRun(
            run_id=summary["run_id"],
            run_type=summary["run_type"],
            parser_version=summary.get("parser_version"),
            freeze_version=summary.get("freeze_version"),
            started_at=summary["started_at"],
            completed_at=summary["completed_at"],
            duration_seconds=summary["duration_seconds"],
            persist_artifacts=summary["persist_artifacts"],
            input_scope_root=summary.get("input_scope_root"),
            total_files=summary["total_files"],
            parsed_ok=summary["parsed_ok"],
            parsed_with_warnings=summary["parsed_with_warnings"],
            failed=summary["failed"],
            skipped_invalid=summary["skipped_invalid"],
            persisted_ok=summary["persisted_ok"],
            persisted_failed=summary["persisted_failed"],
            rollback_count=summary["rollback_count"],
            overall_status=summary["overall_status"],
            failure_samples=summary.get("failure_samples") or [],
            warning_samples=summary.get("warning_samples") or [],
        )
        self.db.add(record)
        self.db.flush()
        if commit:
            self.db.commit()
            self.db.refresh(record)
        return record

    def get_by_run_id(self, run_id: str) -> BatchSeedRun | None:
        return self.db.query(BatchSeedRun).filter(BatchSeedRun.run_id == run_id).first()

    def list_recent_runs(self, limit: int = 20, overall_status: str | None = None) -> list[BatchSeedRun]:
        query = self.db.query(BatchSeedRun)
        if overall_status:
            query = query.filter(BatchSeedRun.overall_status == overall_status)
        return query.order_by(BatchSeedRun.completed_at.desc()).limit(limit).all()
