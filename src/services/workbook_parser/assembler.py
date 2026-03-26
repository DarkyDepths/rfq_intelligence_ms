"""Envelope assembler for deterministic workbook parser."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

from src.services.workbook_parser.contracts import (
    BoqProfile,
    CostBreakdownProfile,
    FinancialProfile,
    IdentityMirrors,
    ParserReport,
    SheetReports,
    WorkbookParseEnvelope,
    WorkbookProfile,
)
from src.services.workbook_parser.extractors.bid_s_extractor import BidSExtractionResult
from src.services.workbook_parser.extractors.boq_extractor import BoqExtractionResult
from src.services.workbook_parser.extractors.cash_flow_extractor import CashFlowExtractionResult
from src.services.workbook_parser.extractors.general_extractor import GeneralExtractionResult
from src.services.workbook_parser.extractors.mat_breakup_extractor import MatBreakupExtractionResult
from src.services.workbook_parser.extractors.top_sheet_extractor import TopSheetExtractionResult
from src.services.workbook_parser.issues import AnchorCheck, CrossCheck, ParserIssue, SheetReport

TEMPLATE_NAME = "ghi_estimation_workbook_v1"
PARSER_VERSION = "workbook-parser-v2.1"


def _pack2_ok(result) -> bool:
    return result is not None and result.sheet_report.status != "failed"


def _skipped_sheet_report(sheet_name: str):
    return SheetReport(
        sheet_name=sheet_name,
        status="skipped",
        merged_regions_count=None,
        expected_body_range=None,
        rows_scanned=0,
        rows_kept=0,
        rows_skipped=0,
        warning_count=0,
        error_count=0,
    )


def build_envelope(
    rfq_id: str,
    workbook_file_name: str | None,
    workbook_blob_path: str | None,
    workbook_format: str,
    template_match: bool,
    general_result: GeneralExtractionResult,
    bid_s_result: BidSExtractionResult,
    top_sheet_result: TopSheetExtractionResult,
    cash_flow_result: CashFlowExtractionResult | None,
    mat_breakup_result: MatBreakupExtractionResult | None,
    boq_result: BoqExtractionResult | None,
    matcher_anchor_checks: list[AnchorCheck],
    matcher_issues: list[ParserIssue],
    cross_checks: list[CrossCheck],
) -> dict:
    raw_sheet_reports = {
        "General": general_result.sheet_report,
        "Bid S": bid_s_result.sheet_report,
        "Top Sheet": top_sheet_result.sheet_report,
        "Cash Flow": cash_flow_result.sheet_report if cash_flow_result is not None else _skipped_sheet_report("Cash Flow"),
        "Mat Break-up": (
            mat_breakup_result.sheet_report if mat_breakup_result is not None else _skipped_sheet_report("Mat Break-up")
        ),
        "B-O-Q": boq_result.sheet_report if boq_result is not None else _skipped_sheet_report("B-O-Q"),
    }

    matcher_warning_counts = {name: 0 for name in raw_sheet_reports}
    matcher_error_counts = {name: 0 for name in raw_sheet_reports}
    for issue in matcher_issues:
        if issue.sheet_name in matcher_warning_counts:
            if issue.severity == "warning":
                matcher_warning_counts[issue.sheet_name] += 1
            elif issue.severity == "error":
                matcher_error_counts[issue.sheet_name] += 1

    sheet_reports = {}
    for name, report in raw_sheet_reports.items():
        warning_count = report.warning_count + matcher_warning_counts[name]
        error_count = report.error_count + matcher_error_counts[name]

        status = report.status
        if report.status in {"parsed_ok", "parsed_with_warnings"}:
            if error_count > 0:
                status = "failed"
            elif warning_count > 0:
                status = "parsed_with_warnings"
            else:
                status = "parsed_ok"

        sheet_reports[name] = type(report)(
            sheet_name=report.sheet_name,
            status=status,
            merged_regions_count=report.merged_regions_count,
            expected_body_range=report.expected_body_range,
            rows_scanned=report.rows_scanned,
            rows_kept=report.rows_kept,
            rows_skipped=report.rows_skipped,
            warning_count=warning_count,
            error_count=error_count,
        )

    all_issues = [
        *matcher_issues,
        *general_result.issues,
        *bid_s_result.issues,
        *top_sheet_result.issues,
        *(cash_flow_result.issues if cash_flow_result is not None else []),
        *(mat_breakup_result.issues if mat_breakup_result is not None else []),
        *(boq_result.issues if boq_result is not None else []),
    ]
    warnings = [issue for issue in all_issues if issue.severity == "warning"]
    errors = [issue for issue in all_issues if issue.severity == "error"]

    parsed_sheets = [name for name, report in sheet_reports.items() if report.status in {"parsed_ok", "parsed_with_warnings"}]
    skipped_sheets = [name for name, report in sheet_reports.items() if report.status == "skipped"]
    failed_sheets = [name for name, report in sheet_reports.items() if report.status == "failed"]

    core_failed = (
        not template_match
        or sheet_reports["General"].status == "failed"
        or sheet_reports["Bid S"].status == "failed"
        or sheet_reports["Top Sheet"].status == "failed"
    )

    status = "parsed_ok"
    if core_failed:
        status = "failed"
    elif warnings or errors or failed_sheets:
        status = "parsed_with_warnings"

    workbook_profile = WorkbookProfile(
        rfq_identity=general_result.rfq_identity,
        identity_mirrors=IdentityMirrors(
            bid_s=bid_s_result.identity_mirror,
            top_sheet=top_sheet_result.identity_mirror,
        ),
        general_item_rows=general_result.general_item_rows,
        general_summary=general_result.general_summary,
        bid_meta=bid_s_result.bid_meta,
    )

    cost_breakdown_profile = CostBreakdownProfile(
        bid_summary_lines=bid_s_result.bid_summary_lines,
        bid_summary=bid_s_result.bid_summary,
        top_sheet_lines=top_sheet_result.top_sheet_lines,
        top_sheet_summary=top_sheet_result.top_sheet_summary,
        material_decomposition=(
            mat_breakup_result.material_decomposition if _pack2_ok(mat_breakup_result) else None
        ),
        financial_profile=(
            FinancialProfile(
                identity_mirror=cash_flow_result.identity_mirror,
                cash_flow_lines=cash_flow_result.cash_flow_lines,
                cash_flow_summary=cash_flow_result.cash_flow_summary,
            )
            if _pack2_ok(cash_flow_result)
            else None
        ),
    )

    boq_profile = None
    if _pack2_ok(boq_result):
        boq_profile = BoqProfile(
            boq_item_details=boq_result.boq_item_details,
            material_price_table=boq_result.material_price_table,
        )

    parser_report = ParserReport(
        status=status,
        parsed_sheets=parsed_sheets,
        skipped_sheets=skipped_sheets,
        warnings=warnings,
        errors=errors,
        anchor_checks=[
            *matcher_anchor_checks,
            *general_result.anchor_checks,
            *bid_s_result.anchor_checks,
            *top_sheet_result.anchor_checks,
            *(cash_flow_result.anchor_checks if cash_flow_result is not None else []),
            *(mat_breakup_result.anchor_checks if mat_breakup_result is not None else []),
            *(boq_result.anchor_checks if boq_result is not None else []),
        ],
        cross_checks=cross_checks,
        sheet_reports=SheetReports(
            general=sheet_reports["General"],
            bid_s=sheet_reports["Bid S"],
            top_sheet=sheet_reports["Top Sheet"],
            cash_flow=sheet_reports["Cash Flow"],
            mat_breakup=sheet_reports["Mat Break-up"],
            boq=sheet_reports["B-O-Q"],
        ),
    )

    envelope = WorkbookParseEnvelope(
        rfq_id=rfq_id,
        template_name=TEMPLATE_NAME,
        workbook_format=workbook_format,
        workbook_file_name=workbook_file_name,
        workbook_blob_path=workbook_blob_path,
        template_match=template_match,
        parsed_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        parser_version=PARSER_VERSION,
        workbook_profile=workbook_profile,
        cost_breakdown_profile=cost_breakdown_profile,
        parser_report=parser_report,
        boq_profile=boq_profile,
    )
    return asdict(envelope)
