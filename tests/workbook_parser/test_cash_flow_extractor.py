from pathlib import Path

import pytest

from src.services.workbook_parser.extractors.cash_flow_extractor import CashFlowExtractor
from src.services.workbook_parser.readers.workbook_reader import WorkbookReader
from src.services.workbook_parser.readers.xls_workbook_reader import XlsWorkbookReader


FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "local_fixtures"
    / "workbook_uploaded"
    / "workbook_sample_001"
    / "ghi_workbook_32_sheets.xls"
)


class OverrideReader(WorkbookReader):
    def __init__(self, base: WorkbookReader, label_overrides: dict[tuple[str, int, int], object] | None = None):
        self._base = base
        self._label_overrides = label_overrides or {}

    def open(self, workbook_path: str) -> None:
        self._base.open(workbook_path)

    def get_sheet_names(self) -> list[str]:
        return self._base.get_sheet_names()

    def has_sheet(self, sheet_name: str) -> bool:
        return self._base.has_sheet(sheet_name)

    def get_cell_value(self, sheet_name: str, row: int, col: int) -> object:
        return self._base.get_cell_value(sheet_name, row, col)

    def get_label_value(self, sheet_name: str, row: int, col: int) -> str | None:
        key = (sheet_name, row, col)
        if key in self._label_overrides:
            value = self._label_overrides[key]
            if value is None:
                return None
            return str(value)
        return self._base.get_label_value(sheet_name, row, col)

    def get_numeric_value(self, sheet_name: str, row: int, col: int) -> float | None:
        return self._base.get_numeric_value(sheet_name, row, col)

    def get_date_value(self, sheet_name: str, row: int, col: int) -> str | None:
        return self._base.get_date_value(sheet_name, row, col)

    def get_merged_regions_count(self, sheet_name: str) -> int:
        return self._base.get_merged_regions_count(sheet_name)


class MissingCashFlowSheetReader(WorkbookReader):
    def open(self, workbook_path: str) -> None:
        return None

    def get_sheet_names(self) -> list[str]:
        return ["General", "Bid S", "Top Sheet"]

    def has_sheet(self, sheet_name: str) -> bool:
        return sheet_name != "Cash Flow"

    def get_cell_value(self, sheet_name: str, row: int, col: int) -> object:
        return None

    def get_label_value(self, sheet_name: str, row: int, col: int) -> str | None:
        return None

    def get_numeric_value(self, sheet_name: str, row: int, col: int) -> float | None:
        return None

    def get_date_value(self, sheet_name: str, row: int, col: int) -> str | None:
        return None

    def get_merged_regions_count(self, sheet_name: str) -> int:
        return 0


def _build_reader() -> XlsWorkbookReader:
    reader = XlsWorkbookReader()
    reader.open(FIXTURE_PATH.as_posix())
    return reader


def test_cash_flow_extractor_extracts_identity_lines_and_summary_from_fixture():
    result = CashFlowExtractor(_build_reader()).extract()

    assert result.identity_mirror.inquiry_no == "IF-25144"
    assert result.identity_mirror.client_name == "Al Bawani Group"
    assert result.identity_mirror.project_name == "Abqaiq Yanbu Pipeline SECTION 6 (AY-1L) BI-10-01575"
    assert result.identity_mirror.dated == "2025-08-26"

    assert len(result.cash_flow_lines) == 7
    by_key = {line.canonical_key: line for line in result.cash_flow_lines}
    assert by_key["net_in_out_flow"].sheet_row == 15
    assert by_key["net_in_out_flow"].line_kind == "summary"
    assert by_key["cash_inflow"].line_kind == "detail"
    assert by_key["cash_outflow"].total_sr == pytest.approx(776920.1)

    assert result.cash_flow_summary.total_inflow_sr == pytest.approx(971150.0)
    assert result.cash_flow_summary.total_outflow_sr == pytest.approx(776920.1)
    assert result.cash_flow_summary.total_inflow_pct == pytest.approx(1.0)
    assert result.cash_flow_summary.total_outflow_pct == pytest.approx(0.9)
    assert result.cash_flow_summary.negative_months_count == 9
    assert result.cash_flow_summary.peak_negative_exposure == pytest.approx(-291345.05)
    assert result.cash_flow_summary.net_cash_position_final == pytest.approx(-67980.54999999993)
    assert result.cash_flow_summary.months_with_data == 12

    assert len(result.anchor_checks) == 8
    assert all(check.passed for check in result.anchor_checks)
    assert result.issues == []
    assert result.sheet_report.status == "parsed_ok"
    assert result.sheet_report.rows_scanned == 7
    assert result.sheet_report.rows_kept == 7
    assert result.sheet_report.rows_skipped == 0


def test_cash_flow_extractor_reports_anchor_mismatch_and_blank_line_label_as_warnings():
    base_reader = _build_reader()
    reader = OverrideReader(
        base=base_reader,
        label_overrides={
            ("Cash Flow", 14, 16): "Wrong Total Header",
            ("Cash Flow", 20, 2): None,
        },
    )

    result = CashFlowExtractor(reader).extract()

    issue_codes = {issue.code for issue in result.issues}
    assert "CASH_FLOW_MISSING_REQUIRED_ANCHOR" in issue_codes
    assert "CASH_FLOW_MISSING_REQUIRED_LINE_LABEL" in issue_codes

    assert len(result.cash_flow_lines) == 6
    assert result.sheet_report.status == "parsed_with_warnings"
    assert result.sheet_report.warning_count >= 2
    assert result.sheet_report.error_count == 0

    assert any(check.cell_ref == "P14" and not check.passed for check in result.anchor_checks)
    assert result.sheet_report.rows_scanned == 7
    assert result.sheet_report.rows_kept == 6
    assert result.sheet_report.rows_skipped == 1


def test_cash_flow_extractor_missing_sheet_returns_failed_result():
    reader = MissingCashFlowSheetReader()
    result = CashFlowExtractor(reader).extract()

    issue_codes = {issue.code for issue in result.issues}
    assert "CASH_FLOW_MISSING_REQUIRED_SHEET" in issue_codes
    assert result.sheet_report.status == "failed"
    assert result.sheet_report.error_count == 1
    assert result.cash_flow_lines == []
    assert result.identity_mirror.inquiry_no is None
    assert result.identity_mirror.project_name is None
    assert result.identity_mirror.client_name is None
    assert result.identity_mirror.dated is None