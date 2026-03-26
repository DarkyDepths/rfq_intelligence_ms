from pathlib import Path

from src.services.workbook_parser.batch_seed_runner import (
    discover_workbook_files,
    run_historical_workbook_batch_seed,
)


def test_discover_workbook_files_finds_and_sorts_xls_variants(tmp_path):
    (tmp_path / "b.xls").write_text("x", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "a.xlsx").write_text("x", encoding="utf-8")
    (nested / "notes.txt").write_text("ignored", encoding="utf-8")

    files = discover_workbook_files(str(tmp_path))

    assert files == sorted(files)
    assert len(files) == 2
    assert {Path(path).name for path in files} == {"a.xlsx", "b.xls"}


def test_batch_seed_runner_continues_after_single_file_failure(monkeypatch, tmp_path):
    file_ok = tmp_path / "ok.xls"
    file_bad = tmp_path / "bad.xls"
    file_ok.write_text("x", encoding="utf-8")
    file_bad.write_text("x", encoding="utf-8")

    def _fake_parse(workbook_path: str, expected_sheet_names=None):
        if workbook_path.endswith("bad.xls"):
            raise RuntimeError("boom")
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

    result = run_historical_workbook_batch_seed([str(file_ok), str(file_bad)], expected_parser_version="workbook-parser-v2.1")

    assert result["summary"]["parsed_ok"] == 1
    assert result["summary"]["failed"] == 1
    assert len(result["results"]) == 2
    failed_row = next(item for item in result["results"] if item["status"] == "failed")
    assert failed_row["error"]["code"] == "WORKBOOK_PARSE_EXCEPTION"


def test_batch_seed_runner_marks_parser_version_mismatch_as_failed(monkeypatch, tmp_path):
    workbook = tmp_path / "ver.xls"
    workbook.write_text("x", encoding="utf-8")

    def _fake_parse(workbook_path: str, expected_sheet_names=None):
        return {
            "workbook_parse_envelope": {
                "parser_version": "workbook-parser-v1.1",
                "template_match": True,
                "parser_report": {"status": "parsed_ok"},
            }
        }

    monkeypatch.setattr(
        "src.services.workbook_parser.batch_seed_runner.parse_workbook_deterministic",
        _fake_parse,
    )

    result = run_historical_workbook_batch_seed([str(workbook)], expected_parser_version="workbook-parser-v2.1")

    assert result["summary"]["parsed_ok"] == 0
    assert result["summary"]["failed"] == 1
    assert result["results"][0]["status"] == "failed"
    assert result["results"][0]["error"]["code"] == "PARSER_VERSION_MISMATCH"
