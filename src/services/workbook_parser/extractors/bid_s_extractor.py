"""Bid S sheet extractor stub for Step 9."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.services.workbook_parser.contracts import BidMeta, BidSummary, BidSummaryLine, RfqIdentityMirrorBidS
from src.services.workbook_parser.issues import AnchorCheck, ParserIssue, SheetReport
from src.services.workbook_parser.readers.workbook_reader import WorkbookReader


@dataclass(frozen=True)
class BidSExtractionResult:
    identity_mirror: RfqIdentityMirrorBidS = field(default_factory=RfqIdentityMirrorBidS)
    bid_meta: BidMeta = field(default_factory=BidMeta)
    bid_summary_lines: list[BidSummaryLine] = field(default_factory=list)
    bid_summary: BidSummary | None = None
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
        if not self._reader.has_sheet("Bid S"):
            issue = ParserIssue(
                code="BID_S_MISSING_REQUIRED_SHEET",
                severity="error",
                sheet_name="Bid S",
                cell_ref=None,
                row_number=None,
                field_path=None,
                message="Required sheet is missing: Bid S",
                expected_value="Bid S",
                actual_value=None,
                raw_value=None,
            )
            return BidSExtractionResult(
                issues=[issue],
                sheet_report=SheetReport(
                    sheet_name="Bid S",
                    status="failed",
                    merged_regions_count=None,
                    expected_body_range="14:49",
                    rows_scanned=0,
                    rows_kept=0,
                    rows_skipped=0,
                    warning_count=0,
                    error_count=1,
                ),
            )

        return BidSExtractionResult(
            sheet_report=SheetReport(
                sheet_name="Bid S",
                status="parsed_ok",
                merged_regions_count=self._reader.get_merged_regions_count("Bid S"),
                expected_body_range="14:49",
                rows_scanned=0,
                rows_kept=0,
                rows_skipped=0,
                warning_count=0,
                error_count=0,
            )
        )
