from pathlib import Path

import pytest

from src.services.workbook_parser.extractors.general_extractor import GeneralExtractor
from src.services.workbook_parser.readers.xls_workbook_reader import XlsWorkbookReader


FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "local_fixtures"
    / "workbook_uploaded"
    / "workbook_sample_001"
    / "ghi_workbook_32_sheets.xls"
)


def _extract_general():
    reader = XlsWorkbookReader()
    reader.open(FIXTURE_PATH.as_posix())
    return GeneralExtractor(reader).extract()


def test_general_extractor_extracts_primary_identity():
    result = _extract_general()

    assert result.rfq_identity.inquiry_no == "IF-25144"
    assert result.rfq_identity.revision_no == "0"
    assert result.rfq_identity.client_name == "Al Bawani Group"
    assert result.rfq_identity.status == "Live"
    assert result.rfq_identity.subject == "Mech. Design, supply & fabrication of Vessels"
    assert result.rfq_identity.project_name == "Abqaiq Yanbu Pipeline SECTION 6 (AY-1L) BI-10-01575"
    assert result.rfq_identity.inquiry_date == "2025-08-26"


def test_general_extractor_filters_placeholder_rows_and_keeps_real_rows_only():
    result = _extract_general()

    assert len(result.general_item_rows) == 1
    assert all(14 <= row.sheet_row <= 62 for row in result.general_item_rows)

    row = result.general_item_rows[0]
    assert row.sheet_row == 14
    assert row.item_tag == "K18-D-0003"
    assert row.item_description == "DRAIN COLLECTION VESSEL"
    assert row.qty == 1.0
    assert row.total_weight_ton == pytest.approx(10.249, abs=0.001)
    assert row.material == "SA 516 Gr. 70N"


def test_general_extractor_computes_summary_from_kept_rows_only():
    result = _extract_general()

    assert result.general_summary.item_count == 1
    assert result.general_summary.total_qty == pytest.approx(1.0)
    assert result.general_summary.total_weight_ton == pytest.approx(10.249, abs=0.001)

    assert result.sheet_report.expected_body_range == "14:62"
    assert result.sheet_report.rows_scanned == 49
    assert result.sheet_report.rows_kept == 1
    assert result.sheet_report.rows_skipped == 48
    assert result.sheet_report.status in {"parsed_ok", "parsed_with_warnings"}
