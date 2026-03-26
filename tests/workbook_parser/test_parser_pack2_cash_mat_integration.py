from pathlib import Path

import pytest

from src.services.workbook_parser.extractors.mat_breakup_extractor import MatBreakupExtractor
from src.services.workbook_parser.parser_orchestrator import WorkbookParserOrchestrator
from src.services.workbook_parser.readers.xls_workbook_reader import XlsWorkbookReader


FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "local_fixtures"
    / "workbook_uploaded"
    / "workbook_sample_001"
    / "ghi_workbook_32_sheets.xls"
)


def test_parser_wires_cash_flow_and_mat_breakup_into_cost_breakdown_profile():
    envelope = WorkbookParserOrchestrator().parse(
        workbook_path=FIXTURE_PATH.as_posix(),
        rfq_id="RFQ-PACK2-INTEGRATION-HAPPY",
    )

    cost_breakdown = envelope["cost_breakdown_profile"]
    assert cost_breakdown["financial_profile"] is not None
    assert cost_breakdown["material_decomposition"] is not None

    financial_profile = cost_breakdown["financial_profile"]
    assert financial_profile["cash_flow_summary"]["total_inflow_sr"] == pytest.approx(971150.0)

    material_decomposition = cost_breakdown["material_decomposition"]
    assert material_decomposition["summary"]["grand_total"]["cost_total_sr"] == pytest.approx(202293.2381470275)

    sheet_reports = envelope["parser_report"]["sheet_reports"]
    assert sheet_reports["cash_flow"] is not None
    assert sheet_reports["mat_breakup"] is not None
    assert sheet_reports["cash_flow"]["status"] in {"parsed_ok", "parsed_with_warnings"}
    assert sheet_reports["mat_breakup"]["status"] in {"parsed_ok", "parsed_with_warnings"}

    assert envelope["workbook_profile"]["rfq_identity"] is not None
    assert envelope["cost_breakdown_profile"]["bid_summary"] is not None
    assert envelope["cost_breakdown_profile"]["top_sheet_summary"] is not None

    check_codes = {check["code"] for check in envelope["parser_report"]["cross_checks"]}
    assert "CASH_FLOW_INFLOW_vs_BID_S_GRAND_TOTAL" in check_codes
    assert "MAT_BREAKUP_TOTAL_vs_BID_S_MATERIAL" in check_codes
    assert "MAT_BREAKUP_FINISH_WT_vs_BID_S_WEIGHT" in check_codes
    assert "MAT_BREAKUP_ITEM_SUM_vs_SUMMARY" in check_codes


def test_parser_soft_fail_mat_breakup_crash_keeps_parser_usable_and_reports_explicitly(monkeypatch):
    def _raise_extract(self):
        raise RuntimeError("boom-mat-breakup")

    monkeypatch.setattr(MatBreakupExtractor, "extract", _raise_extract)

    envelope = WorkbookParserOrchestrator().parse(
        workbook_path=FIXTURE_PATH.as_posix(),
        rfq_id="RFQ-PACK2-INTEGRATION-MAT-FAIL",
    )

    assert envelope["parser_report"]["status"] == "parsed_with_warnings"
    assert envelope["cost_breakdown_profile"]["financial_profile"] is not None
    assert envelope["cost_breakdown_profile"]["material_decomposition"] is None

    sheet_reports = envelope["parser_report"]["sheet_reports"]
    assert sheet_reports["mat_breakup"]["status"] == "failed"
    assert sheet_reports["mat_breakup"]["error_count"] == 1

    error_codes = {issue["code"] for issue in envelope["parser_report"]["errors"]}
    assert "MAT_BREAK_UP_EXTRACTION_FAILED" in error_codes

    check_codes = {check["code"] for check in envelope["parser_report"]["cross_checks"]}
    assert "CASH_FLOW_INFLOW_vs_BID_S_GRAND_TOTAL" in check_codes
    assert "MAT_BREAKUP_TOTAL_vs_BID_S_MATERIAL" not in check_codes

    assert envelope["workbook_profile"]["rfq_identity"] is not None
    assert envelope["cost_breakdown_profile"]["bid_summary"] is not None


def test_parser_soft_fail_missing_cash_flow_sheet_reports_skipped_and_continues(monkeypatch):
    original_has_sheet = XlsWorkbookReader.has_sheet

    def _has_sheet_without_cash_flow(self, sheet_name: str) -> bool:
        if sheet_name == "Cash Flow":
            return False
        return original_has_sheet(self, sheet_name)

    monkeypatch.setattr(XlsWorkbookReader, "has_sheet", _has_sheet_without_cash_flow)

    envelope = WorkbookParserOrchestrator().parse(
        workbook_path=FIXTURE_PATH.as_posix(),
        rfq_id="RFQ-PACK2-INTEGRATION-CASH-MISSING",
    )

    assert envelope["parser_report"]["status"] in {"parsed_ok", "parsed_with_warnings"}
    assert envelope["cost_breakdown_profile"]["financial_profile"] is None
    assert envelope["cost_breakdown_profile"]["material_decomposition"] is not None

    sheet_reports = envelope["parser_report"]["sheet_reports"]
    assert sheet_reports["cash_flow"]["status"] == "skipped"
    assert sheet_reports["cash_flow"]["error_count"] == 0
    assert sheet_reports["mat_breakup"]["status"] in {"parsed_ok", "parsed_with_warnings"}