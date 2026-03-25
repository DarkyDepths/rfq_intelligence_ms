"""Envelope assembler for deterministic workbook parser."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

from src.services.workbook_parser.contracts import (
    CostBreakdownProfile,
    IdentityMirrors,
    ParserReport,
    SheetReports,
    WorkbookParseEnvelope,
    WorkbookProfile,
)
from src.services.workbook_parser.extractors.bid_s_extractor import BidSExtractionResult
from src.services.workbook_parser.extractors.general_extractor import GeneralExtractionResult
from src.services.workbook_parser.extractors.top_sheet_extractor import TopSheetExtractionResult
from src.services.workbook_parser.issues import AnchorCheck, CrossCheck, ParserIssue

TEMPLATE_NAME = "ghi_estimation_workbook_v1"
PARSER_VERSION = "workbook-parser-v1.1"


def build_envelope(
    rfq_id: str,
    workbook_file_name: str | None,
    workbook_blob_path: str | None,
    workbook_format: str,
    template_match: bool,
    general_result: GeneralExtractionResult,
    bid_s_result: BidSExtractionResult,
    top_sheet_result: TopSheetExtractionResult,
    matcher_anchor_checks: list[AnchorCheck],
    matcher_issues: list[ParserIssue],
    cross_checks: list[CrossCheck],
) -> dict:
    all_issues = [*matcher_issues, *general_result.issues, *bid_s_result.issues, *top_sheet_result.issues]
    warnings = [issue for issue in all_issues if issue.severity == "warning"]
    errors = [issue for issue in all_issues if issue.severity == "error"]

    status = "parsed_ok"
    if errors or not template_match:
        status = "failed"
    elif warnings:
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
        bid_summary=bid_s_result.bid_summary or None,
        top_sheet_lines=top_sheet_result.top_sheet_lines,
        top_sheet_summary=top_sheet_result.top_sheet_summary or None,
    )

    parser_report = ParserReport(
        status=status,
        parsed_sheets=["General", "Bid S", "Top Sheet"],
        skipped_sheets=[],
        warnings=warnings,
        errors=errors,
        anchor_checks=matcher_anchor_checks,
        cross_checks=cross_checks,
        sheet_reports=SheetReports(
            general=general_result.sheet_report,
            bid_s=bid_s_result.sheet_report,
            top_sheet=top_sheet_result.sheet_report,
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
    )
    return asdict(envelope)
