"""Frozen typed contracts for deterministic workbook parser v2.1 (Pack 2 foundation)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from src.services.workbook_parser.issues import (
    AnchorCheck,
    CrossCheck,
    ParserIssue,
    ParserStatus,
    SheetName,
    SheetReport,
    SheetReports,
)

BidSection = Literal["direct_cost", "other_overheads", "pricing_final"]
BidLineKind = Literal["detail", "summary"]
TopSheetSection = Literal[
    "revenue",
    "project_direct_cost",
    "project_indirect_cost",
    "profitability",
]
TopSheetLineKind = Literal["detail", "summary"]


@dataclass(frozen=True)
class RfqIdentityPrimary:
    inquiry_no: str | None = None
    revision_no: str | None = None
    client_name: str | None = None
    status: str | None = None
    client_inquiry_no: str | None = None
    subject: str | None = None
    project_name: str | None = None
    inquiry_date: str | None = None


@dataclass(frozen=True)
class RfqIdentityMirrorBidS:
    inquiry_no: str | None = None
    client_name: str | None = None
    client_inquiry_no: str | None = None
    subject: str | None = None
    project_name: str | None = None


@dataclass(frozen=True)
class RfqIdentityMirrorTopSheet:
    inquiry_no: str | None = None
    client_name: str | None = None
    client_inquiry_no: str | None = None
    subject: str | None = None
    project_name: str | None = None
    dated: str | None = None


@dataclass(frozen=True)
class RfqIdentityMirrorCashFlow:
    inquiry_no: str | None = None
    project_name: str | None = None
    client_name: str | None = None
    dated: str | None = None


@dataclass(frozen=True)
class IdentityMirrors:
    bid_s: RfqIdentityMirrorBidS = field(default_factory=RfqIdentityMirrorBidS)
    top_sheet: RfqIdentityMirrorTopSheet = field(default_factory=RfqIdentityMirrorTopSheet)


@dataclass(frozen=True)
class GeneralItemRow:
    sheet_row: int
    sr_no: int | None = None
    item_tag: str | None = None
    item_revision: str | None = None
    item_description: str | None = None
    qty: float | None = None
    diameter: float | None = None
    length: float | None = None
    thickness: float | None = None
    unit_weight_ton: float | None = None
    total_weight_ton: float | None = None
    material: str | None = None
    item_type: str | None = None
    rt_level: str | None = None
    rt_source: str | None = None
    pwht: bool | None = None
    asme_stamp: bool | None = None
    nb_regn_cost_flag: bool | None = None
    fea_cost_flag: bool | None = None
    bolts_tensioner_cost_flag: bool | None = None
    material_freight_cost_flag: bool | None = None
    helium_leak_test_cost_flag: bool | None = None
    kom_flag: bool | None = None


@dataclass(frozen=True)
class GeneralSummary:
    item_count: int | None = None
    total_qty: float | None = None
    total_weight_ton: float | None = None


@dataclass(frozen=True)
class BidMeta:
    direct_mh: float | None = None
    indirect_mh: float | None = None
    exchange_rate: float | None = None
    total_weight_ton: float | None = None
    tentative_po_date: str | None = None
    delivery_text: str | None = None
    dated: str | None = None
    status: str | None = None


@dataclass(frozen=True)
class WorkbookProfile:
    rfq_identity: RfqIdentityPrimary = field(default_factory=RfqIdentityPrimary)
    identity_mirrors: IdentityMirrors = field(default_factory=IdentityMirrors)
    general_item_rows: list[GeneralItemRow] = field(default_factory=list)
    general_summary: GeneralSummary = field(default_factory=GeneralSummary)
    bid_meta: BidMeta = field(default_factory=BidMeta)


@dataclass(frozen=True)
class BidSummaryLine:
    sheet_row: int
    section: BidSection
    line_kind: BidLineKind
    row_no_label: str | None = None
    particular_raw: str | None = None
    particular_normalized: str | None = None
    canonical_key: str | None = None
    basis_factor: float | None = None
    amount_sar: float | None = None
    amount_usd: float | None = None
    share_ratio: float | None = None
    per_ton_sar: float | None = None
    per_ton_usd: float | None = None


@dataclass(frozen=True)
class BidSummaryMetric:
    sheet_row: int | None
    canonical_key: str
    particular_raw: str | None = None
    particular_normalized: str | None = None
    basis_factor: float | None = None
    amount_sar: float | None = None
    amount_usd: float | None = None
    share_ratio: float | None = None
    per_ton_sar: float | None = None
    per_ton_usd: float | None = None


@dataclass(frozen=True)
class BidSummary:
    total_direct_cost: BidSummaryMetric
    total_other_overheads: BidSummaryMetric
    total_gross_cost: BidSummaryMetric
    gross_margin: BidSummaryMetric
    gross_price: BidSummaryMetric
    escalation_on_material: BidSummaryMetric
    negotiation: BidSummaryMetric
    grand_total: BidSummaryMetric


@dataclass(frozen=True)
class TopSheetLine:
    sheet_row: int
    section: TopSheetSection
    line_kind: TopSheetLineKind
    particular_raw: str | None = None
    particular_normalized: str | None = None
    canonical_key: str | None = None
    rev00_value: float | None = None
    rev00_ratio: float | None = None
    rev01_value: float | None = None
    rev01_ratio: float | None = None
    period_1_value: float | None = None
    period_2_value: float | None = None
    period_3_value: float | None = None
    period_4_value: float | None = None
    period_5_value: float | None = None
    period_6_value: float | None = None
    period_7_value: float | None = None
    period_8_value: float | None = None
    period_9_value: float | None = None
    period_10_value: float | None = None
    period_11_value: float | None = None
    period_12_value: float | None = None


@dataclass(frozen=True)
class TopSheetMetric:
    sheet_row: int | None
    canonical_key: str
    particular_raw: str | None = None
    particular_normalized: str | None = None
    rev00_value: float | None = None
    rev00_ratio: float | None = None
    rev01_value: float | None = None
    rev01_ratio: float | None = None
    period_1_value: float | None = None
    period_2_value: float | None = None
    period_3_value: float | None = None
    period_4_value: float | None = None
    period_5_value: float | None = None
    period_6_value: float | None = None
    period_7_value: float | None = None
    period_8_value: float | None = None
    period_9_value: float | None = None
    period_10_value: float | None = None
    period_11_value: float | None = None
    period_12_value: float | None = None


@dataclass(frozen=True)
class TopSheetSummary:
    total_revenue: TopSheetMetric
    total_project_direct_cost: TopSheetMetric
    contribution_margin: TopSheetMetric
    total_project_indirect_cost: TopSheetMetric
    total_project_cost: TopSheetMetric
    gross_profit: TopSheetMetric
    bu_overheads: TopSheetMetric
    profit_before_zakat_tax: TopSheetMetric
    zakat_tax: TopSheetMetric
    patam: TopSheetMetric


@dataclass(frozen=True)
class CashFlowMonthlyValues:
    month_1: float | None = None
    month_2: float | None = None
    month_3: float | None = None
    month_4: float | None = None
    month_5: float | None = None
    month_6: float | None = None
    month_7: float | None = None
    month_8: float | None = None
    month_9: float | None = None
    month_10: float | None = None
    month_11: float | None = None
    month_12: float | None = None


@dataclass(frozen=True)
class CashFlowLine:
    sheet_row: int
    canonical_key: str
    line_kind: Literal["summary", "detail"]
    label_raw: str | None = None
    monthly_values: CashFlowMonthlyValues = field(default_factory=CashFlowMonthlyValues)
    total_pct: float | None = None
    total_sr: float | None = None


@dataclass(frozen=True)
class CashFlowSummary:
    total_inflow_sr: float | None = None
    total_outflow_sr: float | None = None
    total_inflow_pct: float | None = None
    total_outflow_pct: float | None = None
    net_cash_position_final: float | None = None
    months_with_data: int = 0
    negative_months_count: int = 0
    peak_negative_exposure: float | None = None


@dataclass(frozen=True)
class FinancialProfile:
    identity_mirror: RfqIdentityMirrorCashFlow = field(default_factory=RfqIdentityMirrorCashFlow)
    cash_flow_lines: list[CashFlowLine] = field(default_factory=list)
    cash_flow_summary: CashFlowSummary = field(default_factory=CashFlowSummary)


@dataclass(frozen=True)
class MaterialCategoryRow:
    sheet_row: int
    sr_no: int | None = None
    code: str | None = None
    canonical_key: str | None = None
    description: str | None = None
    material_spec: str | None = None
    weight_finish_ton: float | None = None
    cost_total_sr: float | None = None
    cost_pct: float | None = None


@dataclass(frozen=True)
class MaterialCategoryTotals:
    weight_finish_ton: float | None = None
    cost_total_sr: float | None = None
    cost_pct: float | None = None


@dataclass(frozen=True)
class MaterialDecompositionItem:
    item_number: int
    item_qty: float | None = None
    categories: list[MaterialCategoryRow] = field(default_factory=list)
    grand_total: MaterialCategoryTotals = field(default_factory=MaterialCategoryTotals)


@dataclass(frozen=True)
class MaterialDecompositionSummary:
    categories: list[str] = field(default_factory=list)
    grand_total: MaterialCategoryTotals = field(default_factory=MaterialCategoryTotals)


@dataclass(frozen=True)
class MaterialDecomposition:
    items: list[MaterialDecompositionItem] = field(default_factory=list)
    summary: MaterialDecompositionSummary = field(default_factory=MaterialDecompositionSummary)


@dataclass(frozen=True)
class BoqComponentRow:
    sheet_row: int
    material_code: str | None = None
    section_label: str | None = None
    component_description: str | None = None
    material_spec: str | None = None
    qty: float | None = None
    finish_weight_kg: float | None = None
    procured_weight_kg: float | None = None
    unit_price_sr_per_kg: float | None = None
    total_amount_sr: float | None = None


@dataclass(frozen=True)
class BoqGrandTotal:
    finish_weight_kg: float | None = None
    procured_weight_kg: float | None = None
    total_amount_sr: float | None = None


@dataclass(frozen=True)
class BoqItemDetail:
    item_block_index: int
    tag_number: str | None = None
    description: str | None = None
    qty: float | None = None
    components: list[BoqComponentRow] = field(default_factory=list)
    sections_found: list[str] = field(default_factory=list)
    grand_total: BoqGrandTotal = field(default_factory=BoqGrandTotal)
    computed_total: BoqGrandTotal = field(default_factory=BoqGrandTotal)
    grand_total_vs_computed_match: bool | None = None


@dataclass(frozen=True)
class MaterialPriceEntry:
    sheet_row: int
    material_spec: str | None = None
    material_class: str | None = None
    sar_per_kg: float | None = None
    usd_per_ton_offer: float | None = None


@dataclass(frozen=True)
class BoqProfile:
    boq_item_details: list[BoqItemDetail] = field(default_factory=list)
    material_price_table: list[MaterialPriceEntry] = field(default_factory=list)


@dataclass(frozen=True)
class CostBreakdownProfile:
    bid_summary_lines: list[BidSummaryLine] = field(default_factory=list)
    bid_summary: BidSummary | None = None
    top_sheet_lines: list[TopSheetLine] = field(default_factory=list)
    top_sheet_summary: TopSheetSummary | None = None
    material_decomposition: MaterialDecomposition | None = None
    financial_profile: FinancialProfile | None = None


@dataclass(frozen=True)
class ParserReport:
    status: ParserStatus
    parsed_sheets: list[SheetName]
    skipped_sheets: list[str]
    warnings: list[ParserIssue]
    errors: list[ParserIssue]
    anchor_checks: list[AnchorCheck]
    cross_checks: list[CrossCheck]
    sheet_reports: SheetReports


@dataclass(frozen=True)
class WorkbookParseEnvelope:
    rfq_id: str
    template_name: str
    workbook_format: str
    workbook_file_name: str | None
    workbook_blob_path: str | None
    template_match: bool
    parsed_at: str
    parser_version: str
    workbook_profile: WorkbookProfile
    cost_breakdown_profile: CostBreakdownProfile
    parser_report: ParserReport
    boq_profile: BoqProfile | None = None
