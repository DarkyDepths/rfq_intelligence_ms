from pathlib import Path

import pytest

from src.services.workbook_parser.extractors.top_sheet_extractor import TopSheetExtractor
from src.services.workbook_parser.readers.xls_workbook_reader import XlsWorkbookReader


FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "local_fixtures"
    / "workbook_uploaded"
    / "workbook_sample_001"
    / "ghi_workbook_32_sheets.xls"
)


def _extract_top_sheet():
    reader = XlsWorkbookReader()
    reader.open(FIXTURE_PATH.as_posix())
    return TopSheetExtractor(reader).extract()


def test_top_sheet_extractor_extracts_identity_mirror():
    result = _extract_top_sheet()

    assert result.identity_mirror.inquiry_no == "IF-25144"
    assert result.identity_mirror.client_name == "Al Bawani Group"
    assert result.identity_mirror.client_inquiry_no == "SA-AYPP-6-MR-022"
    assert result.identity_mirror.subject == "Mech. Design, supply & fabrication of Vessels"
    assert result.identity_mirror.project_name == "Abqaiq Yanbu Pipeline SECTION 6 (AY-1L) BI-10-01575"
    assert result.identity_mirror.dated == "2025-08-26"


def test_top_sheet_extractor_normalizes_dash_labels_and_maps_canonical_keys():
    result = _extract_top_sheet()
    by_row = {line.sheet_row: line for line in result.top_sheet_lines}

    assert by_row[20].particular_raw == "-Direct Material"
    assert by_row[20].particular_normalized == "Direct Material"
    assert by_row[20].canonical_key == "direct_material"


def test_top_sheet_extractor_extracts_rows_and_preserves_zero_value_categories():
    result = _extract_top_sheet()

    assert result.sheet_report.rows_scanned == 66
    assert result.sheet_report.rows_kept == 62
    assert result.sheet_report.rows_skipped == 4

    keys = {line.canonical_key for line in result.top_sheet_lines}
    assert "total_revenue" in keys
    assert "direct_material" in keys
    assert "total_project_direct_cost" in keys
    assert "total_project_indirect_cost" in keys
    assert "total_project_cost" in keys
    assert "gross_profit" in keys
    assert "patam" in keys

    pwht_line = next(line for line in result.top_sheet_lines if line.canonical_key == "pwht_stress_relieving")
    assert pwht_line.rev00_value == pytest.approx(0.0)


def test_top_sheet_extractor_section_and_line_kind_and_rev_names():
    result = _extract_top_sheet()
    by_row = {line.sheet_row: line for line in result.top_sheet_lines}

    assert by_row[18].section == "revenue"
    assert by_row[20].section == "project_direct_cost"
    assert by_row[63].section == "project_indirect_cost"
    assert by_row[71].section == "profitability"

    assert by_row[18].line_kind == "summary"
    assert by_row[60].line_kind == "summary"
    assert by_row[73].line_kind == "detail"
    assert by_row[76].line_kind == "summary"

    assert hasattr(by_row[20], "rev00_value")
    assert hasattr(by_row[20], "rev01_value")


def test_top_sheet_extractor_promotes_summary_metrics_from_expected_rows():
    result = _extract_top_sheet()
    assert result.top_sheet_summary is not None

    summary = result.top_sheet_summary
    assert summary.total_revenue.sheet_row == 18
    assert summary.total_project_direct_cost.sheet_row == 60
    assert summary.contribution_margin.sheet_row == 61
    assert summary.total_project_indirect_cost.sheet_row == 70
    assert summary.total_project_cost.sheet_row == 71
    assert summary.gross_profit.sheet_row == 72
    assert summary.bu_overheads.sheet_row == 73
    assert summary.profit_before_zakat_tax.sheet_row == 74
    assert summary.zakat_tax.sheet_row == 75
    assert summary.patam.sheet_row == 76

    assert summary.total_revenue.canonical_key == "total_revenue"
    assert summary.patam.canonical_key == "patam"
