"""Deterministic workbook parser orchestrator (Step 9 skeleton)."""

from __future__ import annotations

import logging
from pathlib import Path

from src.services.workbook_parser.assembler import build_envelope
from src.services.workbook_parser.cross_checks import run_cross_checks
from src.services.workbook_parser.extractors.bid_s_extractor import BidSExtractor
from src.services.workbook_parser.extractors.boq_extractor import BoqExtractionResult, BoqExtractor
from src.services.workbook_parser.extractors.cash_flow_extractor import CashFlowExtractionResult, CashFlowExtractor
from src.services.workbook_parser.extractors.general_extractor import GeneralExtractor
from src.services.workbook_parser.extractors.mat_breakup_extractor import MatBreakupExtractionResult, MatBreakupExtractor
from src.services.workbook_parser.extractors.top_sheet_extractor import TopSheetExtractor
from src.services.workbook_parser.issues import ParserIssue, SheetReport
from src.services.workbook_parser.readers.xls_workbook_reader import XlsWorkbookReader
from src.services.workbook_parser.template_matcher import TemplateMatcher


class WorkbookParserOrchestrator:
    def __init__(self) -> None:
        self._reader = XlsWorkbookReader()

    def parse(
        self,
        workbook_path: str,
        rfq_id: str,
        workbook_file_name: str | None = None,
        workbook_blob_path: str | None = None,
    ) -> dict:
        workbook = Path(workbook_path)
        self._reader.open(workbook.as_posix())

        match_result = TemplateMatcher(self._reader).validate()
        general_result = GeneralExtractor(self._reader).extract()
        bid_s_result = BidSExtractor(self._reader).extract()
        top_sheet_result = TopSheetExtractor(self._reader).extract()
        cash_flow_result = self._try_extract("Cash Flow", CashFlowExtractor, CashFlowExtractionResult)
        mat_breakup_result = self._try_extract("Mat Break-up", MatBreakupExtractor, MatBreakupExtractionResult)
        boq_result = self._try_extract("B-O-Q", BoqExtractor, BoqExtractionResult)

        def _pack2_data(result):
            if result is None or result.sheet_report.status == "failed":
                return None
            return {k: v for k, v in result.__dict__.items() if k not in {"anchor_checks", "issues", "sheet_report"}}

        checks = run_cross_checks(
            general_data={
                "rfq_identity": general_result.rfq_identity,
                "general_summary": general_result.general_summary,
            },
            bid_s_data={
                "identity_mirror": bid_s_result.identity_mirror,
                "bid_meta": bid_s_result.bid_meta,
                "bid_summary_lines": bid_s_result.bid_summary_lines,
                "bid_summary": bid_s_result.bid_summary,
            },
            top_sheet_data={
                "identity_mirror": top_sheet_result.identity_mirror,
                "top_sheet_lines": top_sheet_result.top_sheet_lines,
                "top_sheet_summary": top_sheet_result.top_sheet_summary,
            },
            cash_flow_data=_pack2_data(cash_flow_result),
            mat_breakup_data=_pack2_data(mat_breakup_result),
            boq_data=_pack2_data(boq_result),
            general_item_rows=general_result.general_item_rows,
        )

        return build_envelope(
            rfq_id=rfq_id,
            workbook_file_name=workbook_file_name or workbook.name,
            workbook_blob_path=workbook_blob_path,
            workbook_format=workbook.suffix.lstrip(".").lower() or "xls",
            template_match=match_result.template_match,
            general_result=general_result,
            bid_s_result=bid_s_result,
            top_sheet_result=top_sheet_result,
            cash_flow_result=cash_flow_result,
            mat_breakup_result=mat_breakup_result,
            boq_result=boq_result,
            matcher_anchor_checks=match_result.anchor_checks,
            matcher_issues=match_result.issues,
            cross_checks=checks,
        )

    def _try_extract(self, sheet_name: str, extractor_class, result_class):
        if not self._reader.has_sheet(sheet_name):
            return None

        try:
            return extractor_class(self._reader).extract()
        except Exception as exc:
            logging.getLogger(__name__).error("Pack 2 extraction failed for '%s': %s", sheet_name, exc)

            error_issue = ParserIssue(
                code=f"{sheet_name.upper().replace(' ', '_').replace('-', '_')}_EXTRACTION_FAILED",
                severity="error",
                sheet_name=sheet_name,
                cell_ref=None,
                row_number=None,
                field_path=None,
                message=f"Extractor crashed: {exc}",
                expected_value=None,
                actual_value=None,
                raw_value=None,
            )
            failed_report = SheetReport(
                sheet_name=sheet_name,
                status="failed",
                merged_regions_count=None,
                expected_body_range=None,
                rows_scanned=0,
                rows_kept=0,
                rows_skipped=0,
                warning_count=0,
                error_count=1,
            )
            return result_class(anchor_checks=[], issues=[error_issue], sheet_report=failed_report)
