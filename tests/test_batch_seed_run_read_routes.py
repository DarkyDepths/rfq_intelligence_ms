from datetime import datetime, timedelta, timezone

from src.datasources.batch_seed_run_datasource import BatchSeedRunDatasource


def _create_run(datasource: BatchSeedRunDatasource, run_id: str, completed_offset_minutes: int, status: str):
    now = datetime.now(timezone.utc)
    started = now + timedelta(minutes=completed_offset_minutes - 5)
    completed = now + timedelta(minutes=completed_offset_minutes)
    return datasource.create_run_summary(
        {
            "run_id": run_id,
            "run_type": "historical_workbook_batch_seed",
            "parser_version": "workbook-parser-v2.1",
            "freeze_version": "workbook-parser-v2.1",
            "started_at": started,
            "completed_at": completed,
            "duration_seconds": 300.0,
            "persist_artifacts": False,
            "input_scope_root": "D:/seed-input",
            "total_files": 3,
            "parsed_ok": 2,
            "parsed_with_warnings": 1,
            "failed": 0,
            "skipped_invalid": 0,
            "persisted_ok": 0,
            "persisted_failed": 0,
            "rollback_count": 0,
            "overall_status": status,
            "failure_samples": [],
            "warning_samples": [{"workbook_file_name": "warn.xls", "message": "parsed_with_warnings"}],
        }
    )


def test_get_batch_seed_run_by_id_existing(client, db_session):
    datasource = BatchSeedRunDatasource(db_session)
    _create_run(datasource, run_id="run-001", completed_offset_minutes=0, status="completed")

    response = client.get("/intelligence/v1/batch-seed-runs/run-001")

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == "run-001"
    assert payload["overall_status"] == "completed"


def test_get_batch_seed_run_by_id_missing_returns_404(client):
    response = client.get("/intelligence/v1/batch-seed-runs/missing-run")
    assert response.status_code == 404
    assert "No batch seed run found" in response.json()["detail"]


def test_list_recent_runs_descending_completed_at(client, db_session):
    datasource = BatchSeedRunDatasource(db_session)
    _create_run(datasource, run_id="run-old", completed_offset_minutes=-20, status="completed")
    _create_run(datasource, run_id="run-mid", completed_offset_minutes=-10, status="completed")
    _create_run(datasource, run_id="run-new", completed_offset_minutes=0, status="completed")

    response = client.get("/intelligence/v1/batch-seed-runs?limit=3")

    assert response.status_code == 200
    runs = response.json()["runs"]
    assert [item["run_id"] for item in runs] == ["run-new", "run-mid", "run-old"]


def test_list_recent_runs_filter_by_status(client, db_session):
    datasource = BatchSeedRunDatasource(db_session)
    _create_run(datasource, run_id="run-completed", completed_offset_minutes=-5, status="completed")
    _create_run(datasource, run_id="run-partial", completed_offset_minutes=0, status="completed_with_failures")

    response = client.get("/intelligence/v1/batch-seed-runs?overall_status=completed_with_failures")

    assert response.status_code == 200
    runs = response.json()["runs"]
    assert len(runs) == 1
    assert runs[0]["run_id"] == "run-partial"
    assert runs[0]["overall_status"] == "completed_with_failures"
