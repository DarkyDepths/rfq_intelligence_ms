from pathlib import Path

import pytest

from src.services.workbook_parser.extractors.bid_s_extractor import BidSExtractor
from src.services.workbook_parser.readers.xls_workbook_reader import XlsWorkbookReader


FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "local_fixtures"
    / "workbook_uploaded"
    / "workbook_sample_001"
    / "ghi_workbook_32_sheets.xls"
)


def _extract_bid_s():
    reader = XlsWorkbookReader()
    reader.open(FIXTURE_PATH.as_posix())
    return BidSExtractor(reader).extract()


def test_bid_s_extractor_extracts_identity_mirror_and_meta():
    result = _extract_bid_s()

    assert result.identity_mirror.inquiry_no == "IF-25144"
    assert result.identity_mirror.client_name == "Al Bawani Group"
    assert result.identity_mirror.client_inquiry_no == "SA-AYPP-6-MR-022"
    assert result.identity_mirror.subject == "Mech. Design, supply & fabrication of Vessels"
    assert result.identity_mirror.project_name == "Abqaiq Yanbu Pipeline SECTION 6 (AY-1L) BI-10-01575"

    assert result.bid_meta.direct_mh == pytest.approx(8199.579806859632)
    assert result.bid_meta.indirect_mh == pytest.approx(1229.9369710289448)
    assert result.bid_meta.exchange_rate == pytest.approx(3.75)
    assert result.bid_meta.total_weight_ton == pytest.approx(10.24947475857454)
    assert result.bid_meta.tentative_po_date == "2025-08-26"
    assert result.bid_meta.delivery_text == "36 Weeks"
    assert result.bid_meta.dated == "2025-08-26"
    assert result.bid_meta.status == "Live"


def test_bid_s_extractor_handles_merged_cells_and_numeric_isolation():
    result = _extract_bid_s()
    by_row = {line.sheet_row: line for line in result.bid_summary_lines}

    assert by_row[15].row_no_label == "2-"
    assert by_row[16].row_no_label == "2-"

    assert by_row[35].particular_raw == "Total Direct Cost (A)"
    assert by_row[35].basis_factor is None

    assert by_row[39].particular_raw == "Agent Fee"
    assert by_row[39].basis_factor == pytest.approx(0.0)


def test_bid_s_extractor_rows_sections_keys_and_zero_categories():
    result = _extract_bid_s()

    assert result.sheet_report.rows_scanned == 36
    assert result.sheet_report.rows_kept == 35
    assert result.sheet_report.rows_skipped == 1

    canonical_keys = {line.canonical_key for line in result.bid_summary_lines}
    assert "material" in canonical_keys
    assert "total_direct_cost" in canonical_keys
    assert "total_other_overheads" in canonical_keys
    assert "gross_price" in canonical_keys
    assert "grand_total" in canonical_keys

    pwht_line = next(line for line in result.bid_summary_lines if line.canonical_key == "pwht")
    assert pwht_line.amount_sar == pytest.approx(0.0)

    by_row = {line.sheet_row: line for line in result.bid_summary_lines}
    assert by_row[35].section == "direct_cost"
    assert by_row[37].section == "other_overheads"
    assert by_row[45].section == "pricing_final"

    assert by_row[35].line_kind == "summary"
    assert by_row[45].line_kind == "detail"
    assert by_row[46].line_kind == "summary"


def test_bid_s_extractor_promotes_summary_metrics_from_expected_rows():
    result = _extract_bid_s()
    assert result.bid_summary is not None

    summary = result.bid_summary
    assert summary.total_direct_cost.sheet_row == 35
    assert summary.total_other_overheads.sheet_row == 43
    assert summary.total_gross_cost.sheet_row == 44
    assert summary.gross_margin.sheet_row == 45
    assert summary.gross_price.sheet_row == 46
    assert summary.escalation_on_material.sheet_row == 47
    assert summary.negotiation.sheet_row == 48
    assert summary.grand_total.sheet_row == 49

    assert summary.total_direct_cost.canonical_key == "total_direct_cost"
    assert summary.grand_total.canonical_key == "grand_total"
