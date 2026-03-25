"""Deterministic workbook parser orchestrator (Step 9 skeleton)."""

from __future__ import annotations

from pathlib import Path

from src.services.workbook_parser.assembler import build_envelope
from src.services.workbook_parser.cross_checks import run_cross_checks
from src.services.workbook_parser.extractors.bid_s_extractor import BidSExtractor
from src.services.workbook_parser.extractors.general_extractor import GeneralExtractor
from src.services.workbook_parser.extractors.top_sheet_extractor import TopSheetExtractor
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
            matcher_anchor_checks=match_result.anchor_checks,
            matcher_issues=match_result.issues,
            cross_checks=checks,
        )
