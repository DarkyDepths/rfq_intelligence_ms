from src.services.workbook_parser.contracts import (
    BidMeta,
    BidSummary,
    BidSummaryLine,
    BidSummaryMetric,
    GeneralSummary,
    RfqIdentityMirrorBidS,
    RfqIdentityMirrorTopSheet,
    RfqIdentityPrimary,
    TopSheetLine,
    TopSheetMetric,
    TopSheetSummary,
)
from src.services.workbook_parser.cross_checks import run_cross_checks


def _base_general_identity() -> RfqIdentityPrimary:
    return RfqIdentityPrimary(
        inquiry_no="IF-25144",
        client_name="Al Bawani Group",
        client_inquiry_no="SA-AYPP-6-MR-022",
        subject="Mech. Design, supply & fabrication of Vessels",
        project_name="Abqaiq Yanbu Pipeline SECTION 6 (AY-1L) BI-10-01575",
    )


def _base_bid_identity() -> RfqIdentityMirrorBidS:
    return RfqIdentityMirrorBidS(
        inquiry_no="IF-25144",
        client_name="Al Bawani Group",
        client_inquiry_no="SA-AYPP-6-MR-022",
        subject="Mech. Design, supply & fabrication of Vessels",
        project_name="Abqaiq Yanbu Pipeline SECTION 6 (AY-1L) BI-10-01575",
    )


def _base_top_identity() -> RfqIdentityMirrorTopSheet:
    return RfqIdentityMirrorTopSheet(
        inquiry_no="IF-25144",
        client_name="Al Bawani Group",
        client_inquiry_no="SA-AYPP-6-MR-022",
        subject="Mech. Design, supply & fabrication of Vessels",
        project_name="Abqaiq Yanbu Pipeline SECTION 6 (AY-1L) BI-10-01575",
    )


def _base_bid_summary() -> BidSummary:
    return BidSummary(
        total_direct_cost=BidSummaryMetric(sheet_row=35, canonical_key="total_direct_cost", amount_sar=688524.32),
        total_other_overheads=BidSummaryMetric(sheet_row=43, canonical_key="total_other_overheads", amount_sar=14396.18),
        total_gross_cost=BidSummaryMetric(sheet_row=44, canonical_key="total_gross_cost", amount_sar=702920.50),
        gross_margin=BidSummaryMetric(sheet_row=45, canonical_key="gross_margin", amount_sar=268232.94),
        gross_price=BidSummaryMetric(sheet_row=46, canonical_key="gross_price", amount_sar=971153.44),
        escalation_on_material=BidSummaryMetric(sheet_row=47, canonical_key="escalation_on_material", amount_sar=0.0),
        negotiation=BidSummaryMetric(sheet_row=48, canonical_key="negotiation", amount_sar=0.0),
        grand_total=BidSummaryMetric(sheet_row=49, canonical_key="grand_total", amount_sar=971161.0),
    )


def _base_top_summary() -> TopSheetSummary:
    return TopSheetSummary(
        total_revenue=TopSheetMetric(sheet_row=18, canonical_key="total_revenue", rev00_value=971168.0),
        total_project_direct_cost=TopSheetMetric(
            sheet_row=60,
            canonical_key="total_project_direct_cost",
            rev00_value=747778.0,
        ),
        contribution_margin=TopSheetMetric(sheet_row=61, canonical_key="contribution_margin", rev00_value=223390.0),
        total_project_indirect_cost=TopSheetMetric(
            sheet_row=70,
            canonical_key="total_project_indirect_cost",
            rev00_value=44957.0,
        ),
        total_project_cost=TopSheetMetric(sheet_row=71, canonical_key="total_project_cost", rev00_value=792735.0),
        gross_profit=TopSheetMetric(sheet_row=72, canonical_key="gross_profit", rev00_value=178433.0),
        bu_overheads=TopSheetMetric(sheet_row=73, canonical_key="bu_overheads", rev00_value=0.0),
        profit_before_zakat_tax=TopSheetMetric(
            sheet_row=74,
            canonical_key="profit_before_zakat_tax",
            rev00_value=178433.0,
        ),
        zakat_tax=TopSheetMetric(sheet_row=75, canonical_key="zakat_tax", rev00_value=0.0),
        patam=TopSheetMetric(sheet_row=76, canonical_key="patam", rev00_value=178433.0),
    )


def test_cross_checks_include_expected_codes_and_informational_direct_cost_note():
    checks = run_cross_checks(
        general_data={
            "rfq_identity": _base_general_identity(),
            "general_summary": GeneralSummary(total_weight_ton=10.24947475857454),
        },
        bid_s_data={
            "identity_mirror": _base_bid_identity(),
            "bid_meta": BidMeta(total_weight_ton=10.24947475857454),
            "bid_summary": _base_bid_summary(),
            "bid_summary_lines": [
                BidSummaryLine(
                    sheet_row=14,
                    section="direct_cost",
                    line_kind="detail",
                    canonical_key="material",
                    amount_sar=202293.24,
                ),
                BidSummaryLine(
                    sheet_row=41,
                    section="other_overheads",
                    line_kind="detail",
                    canonical_key="financial_charges",
                    amount_sar=0.0,
                )
            ],
        },
        top_sheet_data={
            "identity_mirror": _base_top_identity(),
            "top_sheet_summary": _base_top_summary(),
            "top_sheet_lines": [
                TopSheetLine(
                    sheet_row=48,
                    section="project_direct_cost",
                    line_kind="detail",
                    canonical_key="financial_charges",
                    rev00_value=0.0,
                ),
                TopSheetLine(
                    sheet_row=49,
                    section="project_direct_cost",
                    line_kind="detail",
                    canonical_key="escalation_on_material",
                    rev00_value=0.0,
                ),
                TopSheetLine(
                    sheet_row=50,
                    section="project_direct_cost",
                    line_kind="detail",
                    canonical_key="negotiation",
                    rev00_value=0.0,
                ),
            ],
        },
        cash_flow_data={
            "identity_mirror": {
                "inquiry_no": "IF-25144",
                "client_name": "Al Bawani Group",
                "project_name": "Abqaiq Yanbu Pipeline SECTION 6 (AY-1L) BI-10-01575",
            },
            "cash_flow_summary": {
                "total_inflow_sr": 971161.0,
            },
        },
        mat_breakup_data={
            "material_decomposition": {
                "summary": {
                    "grand_total": {
                        "cost_total_sr": 202293.24,
                        "weight_finish_ton": 10.24947475857454,
                    }
                },
                "items": [
                    {"grand_total": {"cost_total_sr": 100000.0}},
                    {"grand_total": {"cost_total_sr": 102293.24}},
                ],
            }
        },
        boq_data={
            "boq_item_details": [
                {
                    "item_block_index": 1,
                    "computed_total": {
                        "procured_weight_kg": 14666.82082534326,
                    },
                }
            ]
        },
        general_item_rows=[
            {
                "total_weight_ton": 14.66682082534326,
            }
        ],
    )

    assert len(checks) == 25

    by_code = {check.code: check for check in checks}
    assert by_code["GENERAL_vs_BID_S_INQUIRY_NO"].status == "pass"
    assert by_code["GENERAL_vs_TOP_SHEET_PROJECT_NAME"].status == "pass"

    assert by_code["TOP_SHEET_TOTAL_REVENUE_vs_BID_S_GRAND_TOTAL"].status == "pass"

    direct_cost_check = by_code["TOP_SHEET_DIRECT_COST_vs_BID_S_TOTAL_DIRECT_COST"]
    assert direct_cost_check.status == "warn"
    assert direct_cost_check.note == "Informational delta; structural scope difference expected"
    assert direct_cost_check.delta_abs is not None and direct_cost_check.delta_abs > 0

    assert by_code["CASH_FLOW_vs_GENERAL_INQUIRY_NO"].status == "pass"
    assert by_code["CASH_FLOW_INFLOW_vs_BID_S_GRAND_TOTAL"].status == "pass"
    assert by_code["MAT_BREAKUP_TOTAL_vs_BID_S_MATERIAL"].status == "pass"
    assert by_code["MAT_BREAKUP_FINISH_WT_vs_BID_S_WEIGHT"].status == "pass"
    assert by_code["MAT_BREAKUP_ITEM_SUM_vs_SUMMARY"].status == "pass"
    assert by_code["BOQ_ITEM_1_WEIGHT_vs_GENERAL"].status == "pass"


def test_cross_checks_mark_missing_values_as_skipped():
    checks = run_cross_checks(
        general_data={
            "rfq_identity": _base_general_identity(),
            "general_summary": GeneralSummary(total_weight_ton=None),
        },
        bid_s_data={
            "identity_mirror": _base_bid_identity(),
            "bid_meta": BidMeta(total_weight_ton=None),
            "bid_summary": _base_bid_summary(),
            "bid_summary_lines": [],
        },
        top_sheet_data={
            "identity_mirror": _base_top_identity(),
            "top_sheet_summary": _base_top_summary(),
            "top_sheet_lines": [],
        },
    )

    by_code = {check.code: check for check in checks}
    assert by_code["GENERAL_TOTAL_WEIGHT_vs_BID_S_TOTAL_WEIGHT"].status == "skipped"
    assert by_code["TOP_SHEET_FINANCIAL_CHARGES_vs_BID_S_FINANCIAL_CHARGES"].status == "skipped"
    assert by_code["TOP_SHEET_ESCALATION_vs_BID_S_ESCALATION"].status == "skipped"
    assert by_code["TOP_SHEET_NEGOTIATION_vs_BID_S_NEGOTIATION"].status == "skipped"
