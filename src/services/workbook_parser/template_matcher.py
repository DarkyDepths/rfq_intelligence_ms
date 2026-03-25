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
        ("B6", "CLIENT INQ.#", False),
        ("B7", "SUBJECT :", True),
        ("B8", "PROJECT:", False),
        ("B11", "ITEM TAGS", True),
        ("D11", "ITEM DESCRIPTION", False),
        ("K11", "MATERIAL", False),
    ],
    "Bid S": [
        ("B2", "INQ #", True),
        ("B3", "CLIENT:", False),
        ("B4", "CLIENT INQ.#", False),
        ("B5", "SUBJECT :", False),
        ("B6", "PROJECT:", False),
        ("F2", "Direct MH :", True),
        ("F3", "In-Direct MH :", False),
        ("F4", "Exch.Rate", False),
        ("F5", "Total Weight (Tons)", False),
        ("F6", "Tentative PO Date", False),
        ("B9", "BID SUMMARY", True),
        ("B12", "Particulars", True),
        ("E12", "Amounts", True),
        ("G12", "%Age", False),
        ("H12", "Cost / Price Per Ton", False),
        ("B49", "GRAND TOTAL", True),
    ],
    "Top Sheet": [
        ("B2", "INQ #", True),
        ("B3", "CLIENT:", False),
        ("B4", "CLIENT INQ.#", False),
        ("B5", "SUBJECT :", False),
        ("B6", "PROJECT:", False),
        ("B7", "Dated:", False),
        ("B9", "Description", True),
        ("C9", "Budget", False),
        ("D9", "%", False),
        ("E10", "Rev-01", False),
        ("B11", "REVENUE", True),
        ("B19", "PROJECT DIRECT COST:", True),
        ("B62", "PROJECT INDIRECT COST:", True),
        ("B71", "TOTAL PROJECT COST", False),
        ("B72", "GROSS PROFIT", False),
        ("B76", "PATAM", False),
    ],
}

_NUMERIC_ANCHORS: dict[str, list[tuple[str, float, bool]]] = {
    "Top Sheet": [
        ("G10", 1.0, False),
        ("H10", 2.0, False),
        ("I10", 3.0, False),
        ("J10", 4.0, False),
        ("K10", 5.0, False),
        ("L10", 6.0, False),
        ("M10", 7.0, False),
        ("N10", 8.0, False),
        ("O10", 9.0, False),
        ("P10", 10.0, False),
        ("Q10", 11.0, False),
        ("R10", 12.0, False),
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

        if self._reader.has_sheet("General"):
            inquiry_no = self._reader.get_label_value("General", 4, 4)
            if inquiry_no is None:
                has_hard_fail = True
                issues.append(
                    ParserIssue(
                        code="GENERAL_MISSING_REQUIRED_FIELD",
                        severity="error",
                        sheet_name="General",
                        cell_ref="D4",
                        row_number=4,
                        field_path="workbook_profile.rfq_identity.inquiry_no",
                        message="Required inquiry number cell is blank",
                        expected_value="non-empty",
                        actual_value=None,
                        raw_value=None,
                    )
                )

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
