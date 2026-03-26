from pathlib import Path

from src.services.workbook_parser.parser_orchestrator import WorkbookParserOrchestrator


FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "local_fixtures"
    / "workbook_uploaded"
    / "workbook_sample_001"
    / "ghi_workbook_32_sheets.xls"
)


def test_orchestrator_emits_step14_cross_checks_with_expected_profile():
    envelope = WorkbookParserOrchestrator().parse(
        workbook_path=FIXTURE_PATH.as_posix(),
        rfq_id="RFQ-STEP14-E2E",
    )

    assert envelope["parser_report"]["status"] in {"parsed_ok", "parsed_with_warnings"}

    checks = envelope["parser_report"]["cross_checks"]
    assert len(checks) == 24

    by_code = {check["code"]: check for check in checks}

    assert by_code["GENERAL_vs_BID_S_INQUIRY_NO"]["status"] == "pass"
    assert by_code["GENERAL_vs_TOP_SHEET_CLIENT_NAME"]["status"] == "pass"
    assert by_code["GENERAL_TOTAL_WEIGHT_vs_BID_S_TOTAL_WEIGHT"]["status"] == "pass"

    revenue_check = by_code["TOP_SHEET_TOTAL_REVENUE_vs_BID_S_GRAND_TOTAL"]
    assert revenue_check["status"] == "pass"
    assert revenue_check["delta_abs"] is not None and revenue_check["delta_abs"] > 0

    assert by_code["CASH_FLOW_vs_GENERAL_INQUIRY_NO"]["status"] == "pass"
    assert by_code["CASH_FLOW_vs_GENERAL_CLIENT_NAME"]["status"] == "pass"
    assert by_code["CASH_FLOW_vs_GENERAL_PROJECT_NAME"]["status"] == "pass"
    assert by_code["CASH_FLOW_INFLOW_vs_BID_S_GRAND_TOTAL"]["status"] == "pass"
    assert by_code["CASH_FLOW_INFLOW_vs_TOP_SHEET_REVENUE"]["status"] in {"pass", "warn"}

    assert by_code["MAT_BREAKUP_TOTAL_vs_BID_S_MATERIAL"]["status"] == "pass"
    assert by_code["MAT_BREAKUP_FINISH_WT_vs_BID_S_WEIGHT"]["status"] == "pass"

    direct_cost_check = by_code["TOP_SHEET_DIRECT_COST_vs_BID_S_TOTAL_DIRECT_COST"]
    assert direct_cost_check["status"] == "warn"
    assert direct_cost_check["note"] == "Informational delta; structural scope difference expected"
