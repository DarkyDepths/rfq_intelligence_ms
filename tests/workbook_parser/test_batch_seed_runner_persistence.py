from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.services.workbook_parser.batch_seed_runner import (
    build_historical_workbook_context,
    run_historical_workbook_batch_seed_with_persistence,
)


class _FakeDB:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


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
        if name == "explode.xls":
            raise RuntimeError("forced failure")

        parser_status = "parsed_with_warnings" if name == "warn.xls" else "parsed_ok"
        parser_version = "workbook-parser-v1.1" if name == "mismatch.xls" else "workbook-parser-v2.1"

        parser_content = {
            "parser_version": parser_version,
            "template_match": True,
            "parser_report": {"status": parser_status},
        }

        return {
            "workbook_profile": _FakeArtifact(id=f"wp-{name}", version=1, status="complete", content={}),
            "cost_breakdown_profile": _FakeArtifact(id=f"cb-{name}", version=1, status="complete", content={}),
            "parser_report": _FakeArtifact(
                id=f"pr-{name}",
                version=1,
                status="partial" if parser_status == "parsed_with_warnings" else "complete",
                content=parser_content,
            ),
        }


def test_build_historical_workbook_context_is_deterministic(tmp_path):
    workbook = tmp_path / "same.xls"
    workbook.write_text("x", encoding="utf-8")

    context1 = build_historical_workbook_context(str(workbook))
    context2 = build_historical_workbook_context(str(workbook))

    assert context1["rfq_id"] == context2["rfq_id"]
    assert context1["workbook_filename"] == "same.xls"


def test_persistence_runner_commits_successes_and_rolls_back_failures(tmp_path):
    workbook_ok = tmp_path / "ok.xls"
    workbook_warn = tmp_path / "warn.xls"
    workbook_fail = tmp_path / "explode.xls"
    for path in (workbook_ok, workbook_warn, workbook_fail):
        path.write_text("x", encoding="utf-8")

    service = _FakeWorkbookService()
    result = run_historical_workbook_batch_seed_with_persistence(
        workbook_paths=[str(workbook_ok), str(workbook_warn), str(workbook_fail)],
        workbook_service=service,
        expected_parser_version="workbook-parser-v2.1",
    )

    assert result["summary"]["parsed_ok"] == 1
    assert result["summary"]["parsed_with_warnings"] == 1
    assert result["summary"]["failed"] == 1
    assert service.datasource.db.commits == 2
    assert service.datasource.db.rollbacks == 1

    persisted_rows = [row for row in result["results"] if row["persisted"]]
    assert len(persisted_rows) == 2
    assert all(row["artifacts"] is not None for row in persisted_rows)


def test_persistence_runner_rolls_back_on_parser_version_mismatch(tmp_path):
    workbook = tmp_path / "mismatch.xls"
    workbook.write_text("x", encoding="utf-8")

    service = _FakeWorkbookService()
    result = run_historical_workbook_batch_seed_with_persistence(
        workbook_paths=[str(workbook)],
        workbook_service=service,
        expected_parser_version="workbook-parser-v2.1",
    )

    assert result["summary"]["failed"] == 1
    assert result["results"][0]["persisted"] is False
    assert result["results"][0]["error"]["code"] == "PARSER_VERSION_MISMATCH"
    assert service.datasource.db.commits == 0
    assert service.datasource.db.rollbacks == 1
