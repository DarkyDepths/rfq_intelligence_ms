"""Bid S sheet extractor stub for Step 9."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.services.workbook_parser.contracts import BidMeta, RfqIdentityMirrorBidS
from src.services.workbook_parser.issues import AnchorCheck, ParserIssue, SheetReport
from src.services.workbook_parser.readers.workbook_reader import WorkbookReader


@dataclass(frozen=True)
class BidSExtractionResult:
    identity_mirror: RfqIdentityMirrorBidS = field(default_factory=RfqIdentityMirrorBidS)
    bid_meta: BidMeta = field(default_factory=BidMeta)
    bid_summary_lines: list[dict] = field(default_factory=list)
    bid_summary: dict = field(default_factory=dict)
    anchor_checks: list[AnchorCheck] = field(default_factory=list)
    issues: list[ParserIssue] = field(default_factory=list)
    sheet_report: SheetReport = field(
        default_factory=lambda: SheetReport(
            sheet_name="Bid S",
            status="parsed_ok",
            merged_regions_count=None,
            expected_body_range="14:49",
            rows_scanned=0,
            rows_kept=0,
            rows_skipped=0,
            warning_count=0,
            error_count=0,
        )
    )


class BidSExtractor:
    def __init__(self, reader: WorkbookReader):
        self._reader = reader

    def extract(self) -> BidSExtractionResult:
        return BidSExtractionResult(
            sheet_report=SheetReport(
                sheet_name="Bid S",
                status="parsed_ok",
                merged_regions_count=self._reader.get_merged_regions_count("Bid S")
                if self._reader.has_sheet("Bid S")
                else None,
                expected_body_range="14:49",
                rows_scanned=0,
                rows_kept=0,
                rows_skipped=0,
                warning_count=0,
                error_count=0,
            )
        )
