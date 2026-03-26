"""Mat Break-up sheet extractor for Pack 2 Step 19."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.services.workbook_parser.contracts import (
    MaterialCategoryRow,
    MaterialCategoryTotals,
    MaterialDecomposition,
    MaterialDecompositionItem,
    MaterialDecompositionSummary,
)
from src.services.workbook_parser.issues import AnchorCheck, ParserIssue, SheetReport
from src.services.workbook_parser.normalizers import normalize_empty_to_none, normalize_label
from src.services.workbook_parser.readers.workbook_reader import WorkbookReader
from src.services.workbook_parser.template_matcher import excel_ref_to_row_col


_MAT_BREAKUP_SHEET = "Mat Break-up"
_BLOCK_SIZE = 21

_TEXT_ANCHORS: list[tuple[str, str, bool]] = [
    ("B2", "Item #", True),
    ("B4", "Sr. No", True),
    ("D4", "Description", True),
    ("E4", "Weight (Tons)", True),
    ("H4", "Cost", True),
    ("K4", "%", True),
    ("E5", "Finish", True),
    ("F5", "Wastage", True),
    ("G5", "Procured", True),
    ("H5", "Total (SR)", True),
    ("I5", "Per Ton (SR)", False),
    ("J5", "Per Ton $", False),
    ("B20", "Grand Total", True),
]

_CATEGORY_KEY_MAP: dict[str, str] = {
    "PL": "plate",
    "H": "dished_head",
    "FL": "flanges",
    "FO": "forgings",
    "BO": "boss",
    "PI": "pipe",
    "FI": "fittings",
    "DE": "demister",
    "RO": "rods",
    "STR": "structure",
    "STD": "fasteners",
    "G": "gasket",
    "MIS": "misc",
}


def _to_float(value: float | int | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _to_int(value: float | int | None) -> int | None:
    if value is None:
        return None
    numeric = float(value)
    if numeric.is_integer():
        return int(numeric)
    return None


def _is_block_populated(item_qty: float | None, categories: list[MaterialCategoryRow], grand_total: MaterialCategoryTotals) -> bool:
    if item_qty is not None and item_qty > 0:
        return True
    if grand_total.weight_finish_ton is not None and grand_total.weight_finish_ton > 0:
        return True
    if grand_total.cost_total_sr is not None and grand_total.cost_total_sr > 0:
        return True
    for category in categories:
        if (category.weight_finish_ton is not None and category.weight_finish_ton > 0) or (
            category.cost_total_sr is not None and category.cost_total_sr > 0
        ):
            return True
    return False


def _build_anchor_results(reader: WorkbookReader) -> tuple[list[AnchorCheck], list[ParserIssue]]:
    checks: list[AnchorCheck] = []
    issues: list[ParserIssue] = []

    for cell_ref, expected, hard_fail in _TEXT_ANCHORS:
        row, col = excel_ref_to_row_col(cell_ref)
        actual = reader.get_label_value(_MAT_BREAKUP_SHEET, row, col)
        passed = normalize_label(actual) == normalize_label(expected)
        checks.append(
            AnchorCheck(
                sheet_name=_MAT_BREAKUP_SHEET,
                cell_ref=cell_ref,
                expected_normalized_value=normalize_label(expected) or "",
                actual_normalized_value=normalize_label(actual),
                passed=passed,
            )
        )
        if not passed:
            issues.append(
                ParserIssue(
                    code="MAT_BREAKUP_MISSING_REQUIRED_ANCHOR",
                    severity="error" if hard_fail else "warning",
                    sheet_name=_MAT_BREAKUP_SHEET,
                    cell_ref=cell_ref,
                    row_number=row,
                    field_path=None,
                    message="Mat Break-up anchor value mismatch",
                    expected_value=expected,
                    actual_value=actual,
                    raw_value=actual,
                )
            )

    return checks, issues


@dataclass(frozen=True)
class MatBreakupExtractionResult:
    material_decomposition: MaterialDecomposition = field(default_factory=MaterialDecomposition)
    material_cost_loading_present: bool = False
    anchor_checks: list[AnchorCheck] = field(default_factory=list)
    issues: list[ParserIssue] = field(default_factory=list)
    sheet_report: SheetReport = field(
        default_factory=lambda: SheetReport(
            sheet_name="Mat Break-up",
            status="parsed_ok",
            merged_regions_count=None,
            expected_body_range="2:1051",
            rows_scanned=0,
            rows_kept=0,
            rows_skipped=0,
            warning_count=0,
            error_count=0,
        )
    )


class MatBreakupExtractor:
    def __init__(self, reader: WorkbookReader):
        self._reader = reader

    def extract(self) -> MatBreakupExtractionResult:
        if not self._reader.has_sheet(_MAT_BREAKUP_SHEET):
            issue = ParserIssue(
                code="MAT_BREAKUP_MISSING_REQUIRED_SHEET",
                severity="error",
                sheet_name=_MAT_BREAKUP_SHEET,
                cell_ref=None,
                row_number=None,
                field_path=None,
                message="Required sheet is missing: Mat Break-up",
                expected_value=_MAT_BREAKUP_SHEET,
                actual_value=None,
                raw_value=None,
            )
            return MatBreakupExtractionResult(
                issues=[issue],
                sheet_report=SheetReport(
                    sheet_name=_MAT_BREAKUP_SHEET,
                    status="failed",
                    merged_regions_count=None,
                    expected_body_range="2:1051",
                    rows_scanned=0,
                    rows_kept=0,
                    rows_skipped=0,
                    warning_count=0,
                    error_count=1,
                ),
            )

        anchor_checks, anchor_issues = _build_anchor_results(self._reader)
        issues = list(anchor_issues)

        block_starts: list[int] = []
        for row in range(1, 1200):
            try:
                if self._reader.get_label_value(_MAT_BREAKUP_SHEET, row, 2) == "Item #":
                    block_starts.append(row)
            except IndexError:
                break

        items: list[MaterialDecompositionItem] = []
        categories_seen: dict[str, None] = {}
        material_cost_loading_present = False

        for start_row in block_starts:
            item_number = _to_int(self._reader.get_numeric_value(_MAT_BREAKUP_SHEET, start_row, 4))
            item_qty = _to_float(self._reader.get_numeric_value(_MAT_BREAKUP_SHEET, start_row, 11))

            category_rows: list[MaterialCategoryRow] = []
            for row in range(start_row + 4, start_row + 17):
                sr_no = _to_int(self._reader.get_numeric_value(_MAT_BREAKUP_SHEET, row, 2))
                code_raw = normalize_empty_to_none(self._reader.get_label_value(_MAT_BREAKUP_SHEET, row, 3))
                code = code_raw.upper() if code_raw is not None else None
                canonical_key = _CATEGORY_KEY_MAP.get(code, code.lower() if code is not None else None)
                description = normalize_empty_to_none(self._reader.get_label_value(_MAT_BREAKUP_SHEET, row, 4))

                if canonical_key is not None:
                    categories_seen[canonical_key] = None

                per_ton_sr = _to_float(self._reader.get_numeric_value(_MAT_BREAKUP_SHEET, row, 9))
                per_ton_usd = _to_float(self._reader.get_numeric_value(_MAT_BREAKUP_SHEET, row, 10))
                if (per_ton_sr is not None and per_ton_sr > 0) or (per_ton_usd is not None and per_ton_usd > 0):
                    material_cost_loading_present = True

                category_rows.append(
                    MaterialCategoryRow(
                        sheet_row=row,
                        sr_no=sr_no,
                        code=code,
                        canonical_key=canonical_key,
                        description=description,
                        material_spec=None,
                        weight_finish_ton=_to_float(self._reader.get_numeric_value(_MAT_BREAKUP_SHEET, row, 5)),
                        cost_total_sr=_to_float(self._reader.get_numeric_value(_MAT_BREAKUP_SHEET, row, 8)),
                        cost_pct=_to_float(self._reader.get_numeric_value(_MAT_BREAKUP_SHEET, row, 11)),
                    )
                )

            grand_total = MaterialCategoryTotals(
                weight_finish_ton=_to_float(self._reader.get_numeric_value(_MAT_BREAKUP_SHEET, start_row + 18, 5)),
                cost_total_sr=_to_float(self._reader.get_numeric_value(_MAT_BREAKUP_SHEET, start_row + 18, 8)),
                cost_pct=_to_float(self._reader.get_numeric_value(_MAT_BREAKUP_SHEET, start_row + 18, 11)),
            )

            if not _is_block_populated(item_qty=item_qty, categories=category_rows, grand_total=grand_total):
                continue

            if item_number is None:
                issues.append(
                    ParserIssue(
                        code="MAT_BREAKUP_MISSING_ITEM_NUMBER",
                        severity="warning",
                        sheet_name=_MAT_BREAKUP_SHEET,
                        cell_ref=f"D{start_row}",
                        row_number=start_row,
                        field_path="cost_breakdown_profile.material_decomposition.items[].item_number",
                        message="Populated item block is missing numeric item number",
                        expected_value="non-empty number",
                        actual_value=None,
                        raw_value=None,
                    )
                )
                item_number = len(items) + 1

            items.append(
                MaterialDecompositionItem(
                    item_number=item_number,
                    item_qty=item_qty,
                    categories=category_rows,
                    grand_total=grand_total,
                )
            )

        summary_total = MaterialCategoryTotals(
            weight_finish_ton=sum((item.grand_total.weight_finish_ton or 0.0) for item in items) if items else 0.0,
            cost_total_sr=sum((item.grand_total.cost_total_sr or 0.0) for item in items) if items else 0.0,
            cost_pct=sum((item.grand_total.cost_pct or 0.0) for item in items) if items else 0.0,
        )

        material_decomposition = MaterialDecomposition(
            items=items,
            summary=MaterialDecompositionSummary(
                categories=list(categories_seen.keys()),
                grand_total=summary_total,
            ),
        )

        warning_count = sum(1 for issue in issues if issue.severity == "warning")
        error_count = sum(1 for issue in issues if issue.severity == "error")

        status = "parsed_ok"
        if error_count > 0:
            status = "failed"
        elif warning_count > 0:
            status = "parsed_with_warnings"

        kept_blocks = len(items)
        scanned_blocks = len(block_starts)

        return MatBreakupExtractionResult(
            material_decomposition=material_decomposition,
            material_cost_loading_present=material_cost_loading_present,
            anchor_checks=anchor_checks,
            issues=issues,
            sheet_report=SheetReport(
                sheet_name=_MAT_BREAKUP_SHEET,
                status=status,
                merged_regions_count=self._reader.get_merged_regions_count(_MAT_BREAKUP_SHEET),
                expected_body_range="2:1051",
                rows_scanned=scanned_blocks,
                rows_kept=kept_blocks,
                rows_skipped=scanned_blocks - kept_blocks,
                warning_count=warning_count,
                error_count=error_count,
            ),
        )