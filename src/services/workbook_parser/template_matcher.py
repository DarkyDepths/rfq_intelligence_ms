"""Template matcher for GHI estimation workbook v1.1 (3-sheet first pack)."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.services.workbook_parser.issues import AnchorCheck, ParserIssue
from src.services.workbook_parser.normalizers import normalize_label
from src.services.workbook_parser.readers.workbook_reader import WorkbookReader


_REQUIRED_SHEETS = ["General", "Bid S", "Top Sheet"]

_TEXT_ANCHORS: dict[str, list[tuple[str, str, bool]]] = {
    "General": [
        ("B2", "GENERAL INFORMATION", True),
        ("B4", "INQ #", True),
        ("B5", "CLIENT:", True),
        ("B7", "SUBJECT :", True),
        ("B11", "ITEM TAGS", True),
    ],
    "Bid S": [
        ("B2", "INQ #", True),
        ("F2", "Direct MH :", True),
        ("B9", "BID SUMMARY", True),
        ("B12", "Particulars", True),
        ("E12", "Amounts", True),
        ("B49", "GRAND TOTAL", True),
    ],
    "Top Sheet": [
        ("B2", "INQ #", True),
        ("B9", "Description", True),
        ("B11", "REVENUE", True),
        ("B19", "PROJECT DIRECT COST:", True),
        ("B62", "PROJECT INDIRECT COST:", True),
    ],
}

_NUMERIC_ANCHORS: dict[str, list[tuple[str, float, bool]]] = {
    "Top Sheet": [
        ("G10", 1.0, False),
        ("H10", 2.0, False),
        ("I10", 3.0, False),
    ]
}


@dataclass(frozen=True)
class TemplateMatchResult:
    template_name: str
    template_match: bool
    anchor_checks: list[AnchorCheck] = field(default_factory=list)
    issues: list[ParserIssue] = field(default_factory=list)


class TemplateMatcher:
    def __init__(self, reader: WorkbookReader):
        self._reader = reader

    def validate(self) -> TemplateMatchResult:
        checks: list[AnchorCheck] = []
        issues: list[ParserIssue] = []
        has_hard_fail = False

        for sheet_name in _REQUIRED_SHEETS:
            if not self._reader.has_sheet(sheet_name):
                has_hard_fail = True
                issues.append(
                    ParserIssue(
                        code=f"{sheet_name.upper().replace(' ', '_')}_MISSING_REQUIRED_SHEET",
                        severity="error",
                        sheet_name=sheet_name,
                        cell_ref=None,
                        row_number=None,
                        field_path=None,
                        message=f"Required sheet is missing: {sheet_name}",
                        expected_value=sheet_name,
                        actual_value=None,
                        raw_value=None,
                    )
                )

        for sheet_name, anchors in _TEXT_ANCHORS.items():
            if not self._reader.has_sheet(sheet_name):
                continue
            for cell_ref, expected, hard_fail in anchors:
                row, col = excel_ref_to_row_col(cell_ref)
                actual = self._reader.get_label_value(sheet_name, row, col)
                passed = normalize_label(actual) == normalize_label(expected)
                checks.append(
                    AnchorCheck(
                        sheet_name=sheet_name,  # type: ignore[arg-type]
                        cell_ref=cell_ref,
                        expected_normalized_value=normalize_label(expected) or "",
                        actual_normalized_value=normalize_label(actual),
                        passed=passed,
                    )
                )
                if not passed:
                    issues.append(
                        ParserIssue(
                            code=f"{sheet_name.upper().replace(' ', '_')}_MISSING_REQUIRED_ANCHOR",
                            severity="error" if hard_fail else "warning",
                            sheet_name=sheet_name,
                            cell_ref=cell_ref,
                            row_number=row,
                            field_path=None,
                            message="Anchor value mismatch",
                            expected_value=expected,
                            actual_value=actual,
                            raw_value=actual,
                        )
                    )
                if hard_fail and not passed:
                    has_hard_fail = True

        for sheet_name, anchors in _NUMERIC_ANCHORS.items():
            if not self._reader.has_sheet(sheet_name):
                continue
            for cell_ref, expected, hard_fail in anchors:
                row, col = excel_ref_to_row_col(cell_ref)
                actual = self._reader.get_numeric_value(sheet_name, row, col)
                passed = actual is not None and float(actual) == float(expected)
                checks.append(
                    AnchorCheck(
                        sheet_name=sheet_name,  # type: ignore[arg-type]
                        cell_ref=cell_ref,
                        expected_normalized_value=expected,
                        actual_normalized_value=actual,
                        passed=passed,
                    )
                )
                if not passed:
                    issues.append(
                        ParserIssue(
                            code=f"{sheet_name.upper().replace(' ', '_')}_UNEXPECTED_HEADER_CHANGE",
                            severity="error" if hard_fail else "warning",
                            sheet_name=sheet_name,
                            cell_ref=cell_ref,
                            row_number=row,
                            field_path=None,
                            message="Numeric anchor mismatch",
                            expected_value=expected,
                            actual_value=actual,
                            raw_value=actual,
                        )
                    )
                if hard_fail and not passed:
                    has_hard_fail = True

        return TemplateMatchResult(
            template_name="ghi_estimation_workbook_v1",
            template_match=not has_hard_fail,
            anchor_checks=checks,
            issues=issues,
        )


def excel_ref_to_row_col(cell_ref: str) -> tuple[int, int]:
    letters = ""
    digits = ""
    for char in cell_ref:
        if char.isalpha():
            letters += char.upper()
        elif char.isdigit():
            digits += char
    col = 0
    for char in letters:
        col = col * 26 + (ord(char) - ord("A") + 1)
    return int(digits), col
