"""B-O-Q sheet extractor for Pack 2 Step 22."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.services.workbook_parser.contracts import BoqComponentRow, BoqGrandTotal, BoqItemDetail, MaterialPriceEntry
from src.services.workbook_parser.issues import AnchorCheck, ParserIssue, SheetReport
from src.services.workbook_parser.normalizers import normalize_empty_to_none, normalize_label
from src.services.workbook_parser.readers.workbook_reader import WorkbookReader
from src.services.workbook_parser.template_matcher import excel_ref_to_row_col


_BOQ_SHEET = "B-O-Q"
_MAX_ROWS_SCAN = 2600

_TEXT_ANCHORS: list[tuple[str, str, bool]] = [
    ("A1", "Sr.", True),
    ("B2", "Code", True),
    ("H2", "Material.", True),
    ("Q2", "(SR)", True),
    ("B2188", "Material", False),
    ("G2188", "SAR /", False),
    ("K2189", "USD", False),
]

_INVALID_TAGS = {"e", "0", "0.0", "xxxx"}


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


def _is_valid_tag(tag_number: str | None) -> bool:
    normalized = normalize_label(tag_number)
    if normalized is None:
        return False
    return normalized not in _INVALID_TAGS


def _component_is_non_zero(component: BoqComponentRow) -> bool:
    numeric_values = (
        component.qty,
        component.finish_weight_kg,
        component.procured_weight_kg,
        component.total_amount_sr,
    )
    return any(value is not None and value > 0 for value in numeric_values)


def _build_anchor_results(reader: WorkbookReader) -> tuple[list[AnchorCheck], list[ParserIssue]]:
    checks: list[AnchorCheck] = []
    issues: list[ParserIssue] = []

    for cell_ref, expected, hard_fail in _TEXT_ANCHORS:
        row, col = excel_ref_to_row_col(cell_ref)
        actual = reader.get_label_value(_BOQ_SHEET, row, col)
        passed = normalize_label(actual) == normalize_label(expected)

        checks.append(
            AnchorCheck(
                sheet_name=_BOQ_SHEET,
                cell_ref=cell_ref,
                expected_normalized_value=normalize_label(expected) or "",
                actual_normalized_value=normalize_label(actual),
                passed=passed,
            )
        )

        if not passed:
            issues.append(
                ParserIssue(
                    code="BOQ_MISSING_REQUIRED_ANCHOR",
                    severity="error" if hard_fail else "warning",
                    sheet_name=_BOQ_SHEET,
                    cell_ref=cell_ref,
                    row_number=row,
                    field_path=None,
                    message="B-O-Q anchor value mismatch",
                    expected_value=expected,
                    actual_value=actual,
                    raw_value=actual,
                )
            )

    return checks, issues


@dataclass(frozen=True)
class _ItemBlockCandidate:
    item_block_index: int
    qty_row: int


def _score_candidate(tag_number: str | None, qty: float | None) -> tuple[int, int]:
    return (1 if _is_valid_tag(tag_number) else 0, 1 if (qty is not None and qty > 0) else 0)


def _discover_item_block_candidates(reader: WorkbookReader) -> list[_ItemBlockCandidate]:
    by_item_index: dict[int, _ItemBlockCandidate] = {}
    scores: dict[int, tuple[int, int]] = {}

    for row in range(1, _MAX_ROWS_SCAN + 1):
        try:
            if reader.get_label_value(_BOQ_SHEET, row, 14) != "Qty. =":
                continue
        except IndexError:
            break

        item_index = _to_int(reader.get_numeric_value(_BOQ_SHEET, row - 1, 1))
        if item_index is None or item_index <= 0:
            continue

        tag_number = normalize_empty_to_none(reader.get_label_value(_BOQ_SHEET, row - 1, 10))
        qty = _to_float(reader.get_numeric_value(_BOQ_SHEET, row, 15))
        candidate = _ItemBlockCandidate(item_block_index=item_index, qty_row=row)
        score = _score_candidate(tag_number=tag_number, qty=qty)

        existing_score = scores.get(item_index)
        if existing_score is None or score > existing_score:
            by_item_index[item_index] = candidate
            scores[item_index] = score

    return [by_item_index[index] for index in sorted(by_item_index.keys())]


def _find_next_grand_total_row(reader: WorkbookReader, start_row: int) -> int | None:
    for row in range(start_row + 1, _MAX_ROWS_SCAN + 1):
        try:
            if reader.get_label_value(_BOQ_SHEET, row, 9) == "GRAND TOTAL =":
                return row
        except IndexError:
            return None
    return None


def _grand_total_match(grand_total: BoqGrandTotal, computed_total: BoqGrandTotal) -> bool | None:
    def _weight_matches(left: float, right: float) -> bool:
        # Some workbooks report GRAND TOTAL weights in tons while component
        # rows are aggregated in kg. Accept either representation.
        if abs(left - right) <= 1e-6:
            return True
        if abs((left * 1000.0) - right) <= 1e-3:
            return True
        if abs(left - (right * 1000.0)) <= 1e-3:
            return True
        return False

    pairs = (
        (grand_total.finish_weight_kg, computed_total.finish_weight_kg, "weight"),
        (grand_total.procured_weight_kg, computed_total.procured_weight_kg, "weight"),
        (grand_total.total_amount_sr, computed_total.total_amount_sr, "amount"),
    )

    compared = False
    for left, right, kind in pairs:
        if left is None or right is None:
            continue
        compared = True
        if kind == "weight":
            if not _weight_matches(left, right):
                return False
        else:
            if abs(left - right) > 1e-6:
                return False

    if not compared:
        return None
    return True


def _extract_material_price_table(reader: WorkbookReader) -> list[MaterialPriceEntry]:
    header_row: int | None = None
    for row in range(1, _MAX_ROWS_SCAN + 1):
        try:
            if normalize_label(reader.get_label_value(_BOQ_SHEET, row, 2)) == "material" and "sar" in (
                normalize_label(reader.get_label_value(_BOQ_SHEET, row, 7)) or ""
            ):
                header_row = row
                break
        except IndexError:
            break

    if header_row is None:
        return []

    entries: list[MaterialPriceEntry] = []
    blank_streak = 0
    for row in range(header_row + 3, _MAX_ROWS_SCAN + 1):
        try:
            material_spec = normalize_empty_to_none(reader.get_label_value(_BOQ_SHEET, row, 2))
        except IndexError:
            break

        material_class = normalize_empty_to_none(reader.get_label_value(_BOQ_SHEET, row, 4))
        sar_per_kg = _to_float(reader.get_numeric_value(_BOQ_SHEET, row, 7))
        usd_per_ton_offer = _to_float(reader.get_numeric_value(_BOQ_SHEET, row, 9))

        if material_spec is None and material_class is None and sar_per_kg is None and usd_per_ton_offer is None:
            blank_streak += 1
            if blank_streak >= 3:
                break
            continue

        blank_streak = 0
        entries.append(
            MaterialPriceEntry(
                sheet_row=row,
                material_spec=material_spec,
                material_class=material_class,
                sar_per_kg=sar_per_kg,
                usd_per_ton_offer=usd_per_ton_offer,
            )
        )

    return entries


@dataclass(frozen=True)
class BoqExtractionResult:
    boq_item_details: list[BoqItemDetail] = field(default_factory=list)
    material_price_table: list[MaterialPriceEntry] = field(default_factory=list)
    anchor_checks: list[AnchorCheck] = field(default_factory=list)
    issues: list[ParserIssue] = field(default_factory=list)
    sheet_report: SheetReport = field(
        default_factory=lambda: SheetReport(
            sheet_name="B-O-Q",
            status="parsed_ok",
            merged_regions_count=None,
            expected_body_range="1:2210",
            rows_scanned=0,
            rows_kept=0,
            rows_skipped=0,
            warning_count=0,
            error_count=0,
        )
    )


class BoqExtractor:
    def __init__(self, reader: WorkbookReader):
        self._reader = reader

    def extract(self) -> BoqExtractionResult:
        if not self._reader.has_sheet(_BOQ_SHEET):
            issue = ParserIssue(
                code="BOQ_MISSING_REQUIRED_SHEET",
                severity="error",
                sheet_name=_BOQ_SHEET,
                cell_ref=None,
                row_number=None,
                field_path=None,
                message="Required sheet is missing: B-O-Q",
                expected_value=_BOQ_SHEET,
                actual_value=None,
                raw_value=None,
            )
            return BoqExtractionResult(
                issues=[issue],
                sheet_report=SheetReport(
                    sheet_name=_BOQ_SHEET,
                    status="failed",
                    merged_regions_count=None,
                    expected_body_range="1:2210",
                    rows_scanned=0,
                    rows_kept=0,
                    rows_skipped=0,
                    warning_count=0,
                    error_count=1,
                ),
            )

        anchor_checks, anchor_issues = _build_anchor_results(self._reader)
        issues = list(anchor_issues)

        item_candidates = _discover_item_block_candidates(self._reader)
        boq_items: list[BoqItemDetail] = []

        for candidate in item_candidates:
            qty_row = candidate.qty_row
            item_index = candidate.item_block_index
            tag_number = normalize_empty_to_none(self._reader.get_label_value(_BOQ_SHEET, qty_row - 1, 10))
            description = normalize_empty_to_none(self._reader.get_label_value(_BOQ_SHEET, qty_row, 10))
            item_qty = _to_float(self._reader.get_numeric_value(_BOQ_SHEET, qty_row, 15))

            grand_total_row = _find_next_grand_total_row(self._reader, qty_row)
            component_end_row = grand_total_row - 1 if grand_total_row is not None else qty_row

            sections_found: list[str] = []
            components: list[BoqComponentRow] = []

            for row in range(qty_row + 1, component_end_row + 1):
                material_code = normalize_empty_to_none(self._reader.get_label_value(_BOQ_SHEET, row, 2))
                if material_code is not None:
                    material_code = material_code.upper()

                component_description = normalize_empty_to_none(self._reader.get_label_value(_BOQ_SHEET, row, 3))
                material_spec = normalize_empty_to_none(self._reader.get_label_value(_BOQ_SHEET, row, 8))
                qty = _to_float(self._reader.get_numeric_value(_BOQ_SHEET, row, 9))
                finish_weight_kg = _to_float(self._reader.get_numeric_value(_BOQ_SHEET, row, 13))
                procured_weight_kg = _to_float(self._reader.get_numeric_value(_BOQ_SHEET, row, 15))
                unit_price_sr_per_kg = _to_float(self._reader.get_numeric_value(_BOQ_SHEET, row, 16))
                total_amount_sr = _to_float(self._reader.get_numeric_value(_BOQ_SHEET, row, 17))

                section_label = None
                if material_code is None and component_description is not None:
                    section_label = component_description
                    if section_label not in sections_found:
                        sections_found.append(section_label)

                has_component_data = any(
                    value is not None
                    for value in (
                        material_code,
                        material_spec,
                        qty,
                        finish_weight_kg,
                        procured_weight_kg,
                        unit_price_sr_per_kg,
                        total_amount_sr,
                    )
                )

                if not has_component_data:
                    continue

                components.append(
                    BoqComponentRow(
                        sheet_row=row,
                        material_code=material_code,
                        section_label=section_label,
                        component_description=component_description,
                        material_spec=material_spec,
                        qty=qty,
                        finish_weight_kg=finish_weight_kg,
                        procured_weight_kg=procured_weight_kg,
                        unit_price_sr_per_kg=unit_price_sr_per_kg,
                        total_amount_sr=total_amount_sr,
                    )
                )

            grand_total = BoqGrandTotal(
                finish_weight_kg=_to_float(self._reader.get_numeric_value(_BOQ_SHEET, grand_total_row, 13))
                if grand_total_row is not None
                else None,
                procured_weight_kg=_to_float(self._reader.get_numeric_value(_BOQ_SHEET, grand_total_row, 15))
                if grand_total_row is not None
                else None,
                total_amount_sr=_to_float(self._reader.get_numeric_value(_BOQ_SHEET, grand_total_row, 17))
                if grand_total_row is not None
                else None,
            )

            computed_total = BoqGrandTotal(
                finish_weight_kg=sum((component.finish_weight_kg or 0.0) for component in components),
                procured_weight_kg=sum((component.procured_weight_kg or 0.0) for component in components),
                total_amount_sr=sum((component.total_amount_sr or 0.0) for component in components),
            )

            item_detail = BoqItemDetail(
                item_block_index=item_index,
                tag_number=tag_number,
                description=description,
                qty=item_qty,
                components=components,
                sections_found=sections_found,
                grand_total=grand_total,
                computed_total=computed_total,
                grand_total_vs_computed_match=_grand_total_match(grand_total=grand_total, computed_total=computed_total),
            )

            is_populated = _is_valid_tag(item_detail.tag_number) and any(
                _component_is_non_zero(component) for component in item_detail.components
            )
            if is_populated:
                boq_items.append(item_detail)

        material_price_table = _extract_material_price_table(self._reader)

        warning_count = sum(1 for issue in issues if issue.severity == "warning")
        error_count = sum(1 for issue in issues if issue.severity == "error")

        status = "parsed_ok"
        if error_count > 0:
            status = "failed"
        elif warning_count > 0:
            status = "parsed_with_warnings"

        return BoqExtractionResult(
            boq_item_details=boq_items,
            material_price_table=material_price_table,
            anchor_checks=anchor_checks,
            issues=issues,
            sheet_report=SheetReport(
                sheet_name=_BOQ_SHEET,
                status=status,
                merged_regions_count=self._reader.get_merged_regions_count(_BOQ_SHEET),
                expected_body_range="1:2210",
                rows_scanned=len(item_candidates),
                rows_kept=len(boq_items),
                rows_skipped=len(item_candidates) - len(boq_items),
                warning_count=warning_count,
                error_count=error_count,
            ),
        )