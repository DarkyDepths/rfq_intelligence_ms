from __future__ import annotations

from dataclasses import dataclass

from src.datasources.batch_seed_run_datasource import BatchSeedRunDatasource
from src.services.workbook_parser.batch_seed_runner import execute_historical_batch_seed_run


def test_run_summary_record_happy_path_completed(db_session, monkeypatch, tmp_path):
    workbook1 = tmp_path / "ok1.xls"
    workbook2 = tmp_path / "ok2.xls"
    workbook1.write_text("x", encoding="utf-8")
    workbook2.write_text("x", encoding="utf-8")

    def _fake_parse(workbook_path: str, expected_sheet_names=None):
        return {
            "workbook_parse_envelope": {
                "parser_version": "workbook-parser-v2.1",
                "template_match": True,
                "parser_report": {"status": "parsed_ok"},
            }
        }

    monkeypatch.setattr(
        "src.services.workbook_parser.batch_seed_runner.parse_workbook_deterministic",
        _fake_parse,
    )

    datasource = BatchSeedRunDatasource(db_session)
    result = execute_historical_batch_seed_run(
        workbook_paths=[str(workbook1), str(workbook2)],
        expected_parser_version="workbook-parser-v2.1",
        persist_artifacts=False,
        input_scope_root=str(tmp_path),
        batch_seed_run_datasource=datasource,
    )

    run_id = result["batch_meta"]["run_id"]
    record = datasource.get_by_run_id(run_id)
    assert record is not None
    assert record.total_files == 2
    assert record.parsed_ok == 2
    assert record.failed == 0
    assert record.overall_status == "completed"
    assert record.persist_artifacts is False


def test_run_summary_record_partial_failure_has_samples(db_session, monkeypatch, tmp_path):
    workbook_ok = tmp_path / "ok.xls"
    workbook_warn = tmp_path / "warn.xls"
    workbook_fail = tmp_path / "fail.xls"
    for path in (workbook_ok, workbook_warn, workbook_fail):
        path.write_text("x", encoding="utf-8")

    def _fake_parse(workbook_path: str, expected_sheet_names=None):
        if workbook_path.endswith("fail.xls"):
            raise RuntimeError("boom")
        status = "parsed_with_warnings" if workbook_path.endswith("warn.xls") else "parsed_ok"
        return {
            "workbook_parse_envelope": {
                "parser_version": "workbook-parser-v2.1",
                "template_match": True,
                "parser_report": {"status": status},
            }
        }

    monkeypatch.setattr(
        "src.services.workbook_parser.batch_seed_runner.parse_workbook_deterministic",
        _fake_parse,
    )

    datasource = BatchSeedRunDatasource(db_session)
    result = execute_historical_batch_seed_run(
        workbook_paths=[str(workbook_ok), str(workbook_warn), str(workbook_fail)],
        expected_parser_version="workbook-parser-v2.1",
        persist_artifacts=False,
        input_scope_root=str(tmp_path),
        batch_seed_run_datasource=datasource,
    )

    record = datasource.get_by_run_id(result["batch_meta"]["run_id"])
    assert record is not None
    assert record.parsed_ok == 1
    assert record.parsed_with_warnings == 1
    assert record.failed == 1
    assert record.overall_status == "completed_with_failures"
    assert len(record.failure_samples) == 1
    assert len(record.warning_samples) == 1


class _FakeDB:
    def commit(self):
        return None

    def rollback(self):
        return None


class _FakeDatasource:
    def __init__(self):
        self.db = _FakeDB()


@dataclass
class _FakeArtifact:
    id: str
    version: int
    status: str
    content: dict


class _FakeWorkbookService:
    def __init__(self):
        self.datasource = _FakeDatasource()

    def build_workbook_parser_artifacts_from_uploaded_event(self, workbook_context, event_meta, commit=False):
        name = workbook_context["workbook_filename"]
        return {
            "workbook_profile": _FakeArtifact(id=f"wp-{name}", version=1, status="complete", content={}),
            "cost_breakdown_profile": _FakeArtifact(id=f"cb-{name}", version=1, status="complete", content={}),
            "parser_report": _FakeArtifact(
                id=f"pr-{name}",
                version=1,
                status="complete",
                content={
                    "parser_version": "workbook-parser-v2.1",
                    "template_match": True,
                    "parser_report": {"status": "parsed_ok"},
                },
            ),
        }


def test_run_summary_record_persistence_mode_on_off(db_session, monkeypatch, tmp_path):
    workbook = tmp_path / "ok.xls"
    workbook.write_text("x", encoding="utf-8")

    def _fake_parse(workbook_path: str, expected_sheet_names=None):
        return {
            "workbook_parse_envelope": {
                "parser_version": "workbook-parser-v2.1",
                "template_match": True,
                "parser_report": {"status": "parsed_ok"},
            }
        }

    monkeypatch.setattr(
        "src.services.workbook_parser.batch_seed_runner.parse_workbook_deterministic",
        _fake_parse,
    )

    datasource = BatchSeedRunDatasource(db_session)

    off_result = execute_historical_batch_seed_run(
        workbook_paths=[str(workbook)],
        expected_parser_version="workbook-parser-v2.1",
        persist_artifacts=False,
        input_scope_root=str(tmp_path),
        batch_seed_run_datasource=datasource,
    )
    off_record = datasource.get_by_run_id(off_result["batch_meta"]["run_id"])
    assert off_record is not None
    assert off_record.persist_artifacts is False
    assert off_record.persisted_ok == 0

    on_result = execute_historical_batch_seed_run(
        workbook_paths=[str(workbook)],
        expected_parser_version="workbook-parser-v2.1",
        persist_artifacts=True,
        input_scope_root=str(tmp_path),
        workbook_service=_FakeWorkbookService(),
        batch_seed_run_datasource=datasource,
    )
    on_record = datasource.get_by_run_id(on_result["batch_meta"]["run_id"])
    assert on_record is not None
    assert on_record.persist_artifacts is True
    assert on_record.persisted_ok == 1
