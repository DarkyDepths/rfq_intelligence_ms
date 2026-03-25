"""General sheet extractor stub for Step 9."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.services.workbook_parser.contracts import GeneralItemRow, GeneralSummary, RfqIdentityPrimary
from src.services.workbook_parser.issues import AnchorCheck, ParserIssue, SheetReport
from src.services.workbook_parser.readers.workbook_reader import WorkbookReader


@dataclass(frozen=True)
class GeneralExtractionResult:
    rfq_identity: RfqIdentityPrimary = field(default_factory=RfqIdentityPrimary)
    general_item_rows: list[GeneralItemRow] = field(default_factory=list)
    general_summary: GeneralSummary = field(default_factory=GeneralSummary)
    anchor_checks: list[AnchorCheck] = field(default_factory=list)
    issues: list[ParserIssue] = field(default_factory=list)
    sheet_report: SheetReport = field(
        default_factory=lambda: SheetReport(
            sheet_name="General",
            status="parsed_ok",
            merged_regions_count=None,
            expected_body_range="14:62",
            rows_scanned=0,
            rows_kept=0,
            rows_skipped=0,
            warning_count=0,
            error_count=0,
        )
    )


class GeneralExtractor:
    def __init__(self, reader: WorkbookReader):
        self._reader = reader

    def extract(self) -> GeneralExtractionResult:
        if not self._reader.has_sheet("General"):
            issue = ParserIssue(
                code="GENERAL_MISSING_REQUIRED_SHEET",
                severity="error",
                sheet_name="General",
                cell_ref=None,
                row_number=None,
                field_path=None,
                message="Required sheet is missing: General",
                expected_value="General",
                actual_value=None,
                raw_value=None,
            )
            return GeneralExtractionResult(
                issues=[issue],
                sheet_report=SheetReport(
                    sheet_name="General",
                    status="failed",
                    merged_regions_count=None,
                    expected_body_range="14:62",
                    rows_scanned=0,
                    rows_kept=0,
                    rows_skipped=0,
                    warning_count=0,
                    error_count=1,
                ),
            )

        return GeneralExtractionResult(
            sheet_report=SheetReport(
                sheet_name="General",
                status="parsed_ok",
                merged_regions_count=self._reader.get_merged_regions_count("General"),
                expected_body_range="14:62",
                rows_scanned=0,
                rows_kept=0,
                rows_skipped=0,
                warning_count=0,
                error_count=0,
            )
        )
