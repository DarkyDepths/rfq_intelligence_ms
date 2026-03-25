"""Top Sheet extractor stub for Step 9."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.services.workbook_parser.contracts import RfqIdentityMirrorTopSheet, TopSheetLine, TopSheetSummary
from src.services.workbook_parser.issues import AnchorCheck, ParserIssue, SheetReport
from src.services.workbook_parser.readers.workbook_reader import WorkbookReader


@dataclass(frozen=True)
class TopSheetExtractionResult:
    identity_mirror: RfqIdentityMirrorTopSheet = field(default_factory=RfqIdentityMirrorTopSheet)
    top_sheet_lines: list[TopSheetLine] = field(default_factory=list)
    top_sheet_summary: TopSheetSummary | None = None
    anchor_checks: list[AnchorCheck] = field(default_factory=list)
    issues: list[ParserIssue] = field(default_factory=list)
    sheet_report: SheetReport = field(
        default_factory=lambda: SheetReport(
            sheet_name="Top Sheet",
            status="parsed_ok",
            merged_regions_count=None,
            expected_body_range="11:76",
            rows_scanned=0,
            rows_kept=0,
            rows_skipped=0,
            warning_count=0,
            error_count=0,
        )
    )


class TopSheetExtractor:
    def __init__(self, reader: WorkbookReader):
        self._reader = reader

    def extract(self) -> TopSheetExtractionResult:
        if not self._reader.has_sheet("Top Sheet"):
            issue = ParserIssue(
                code="TOP_SHEET_MISSING_REQUIRED_SHEET",
                severity="error",
                sheet_name="Top Sheet",
                cell_ref=None,
                row_number=None,
                field_path=None,
                message="Required sheet is missing: Top Sheet",
                expected_value="Top Sheet",
                actual_value=None,
                raw_value=None,
            )
            return TopSheetExtractionResult(
                issues=[issue],
                sheet_report=SheetReport(
                    sheet_name="Top Sheet",
                    status="failed",
                    merged_regions_count=None,
                    expected_body_range="11:76",
                    rows_scanned=0,
                    rows_kept=0,
                    rows_skipped=0,
                    warning_count=0,
                    error_count=1,
                ),
            )

        return TopSheetExtractionResult(
            sheet_report=SheetReport(
                sheet_name="Top Sheet",
                status="parsed_ok",
                merged_regions_count=self._reader.get_merged_regions_count("Top Sheet"),
                expected_body_range="11:76",
                rows_scanned=0,
                rows_kept=0,
                rows_skipped=0,
                warning_count=0,
                error_count=0,
            )
        )
