from __future__ import annotations

from src.services.workbook_parser.readers.workbook_reader import WorkbookReader
from src.services.workbook_parser.template_matcher import TemplateMatcher


class FakeReader(WorkbookReader):
    def __init__(self, *, missing_bid_s: bool = False, mismatch_general_b2: bool = False):
        self._missing_bid_s = missing_bid_s
        self._mismatch_general_b2 = mismatch_general_b2

    def open(self, workbook_path: str) -> None:
        return None

    def get_sheet_names(self) -> list[str]:
        names = ["General", "Top Sheet"] if self._missing_bid_s else ["General", "Bid S", "Top Sheet"]
        return names

    def has_sheet(self, sheet_name: str) -> bool:
        return sheet_name in self.get_sheet_names()

    def get_cell_value(self, sheet_name: str, row: int, col: int) -> object:
        return self.get_label_value(sheet_name, row, col)

    def get_label_value(self, sheet_name: str, row: int, col: int) -> str | None:
        if sheet_name == "General":
            if (row, col) == (2, 2):
                return "WRONG" if self._mismatch_general_b2 else "GENERAL INFORMATION"
            if (row, col) == (4, 2):
                return "INQ #"
            if (row, col) == (5, 2):
                return "CLIENT:"
            if (row, col) == (6, 2):
                return "CLIENT INQ.#"
            if (row, col) == (7, 2):
                return "SUBJECT :"
            if (row, col) == (8, 2):
                return "PROJECT:"
            if (row, col) == (11, 2):
                return "ITEM TAGS"
            if (row, col) == (11, 4):
                return "ITEM DESCRIPTION"
            if (row, col) == (11, 11):
                return "MATERIAL"
            if (row, col) == (4, 4):
                return "IF-25144"
        if sheet_name == "Bid S":
            mapping = {
                (2, 2): "INQ #",
                (3, 2): "CLIENT:",
                (4, 2): "CLIENT INQ.#",
                (5, 2): "SUBJECT :",
                (6, 2): "PROJECT:",
                (2, 6): "Direct MH :",
                (3, 6): "In-Direct MH :",
                (4, 6): "Exch.Rate",
                (5, 6): "Total Weight (Tons)",
                (6, 6): "Tentative PO Date",
                (9, 2): "BID SUMMARY",
                (12, 2): "Particulars",
                (12, 5): "Amounts",
                (12, 7): "%Age",
                (12, 8): "Cost / Price Per Ton",
                (49, 2): "GRAND TOTAL",
            }
            return mapping.get((row, col))
        if sheet_name == "Top Sheet":
            mapping = {
                (2, 2): "INQ #",
                (3, 2): "CLIENT:",
                (4, 2): "CLIENT INQ.#",
                (5, 2): "SUBJECT :",
                (6, 2): "PROJECT:",
                (7, 2): "Dated:",
                (9, 2): "Description",
                (9, 3): "Budget",
                (9, 4): "%",
                (10, 5): "Rev-01",
                (11, 2): "REVENUE",
                (19, 2): "PROJECT DIRECT COST:",
                (62, 2): "PROJECT INDIRECT COST:",
                (71, 2): "TOTAL PROJECT COST",
                (72, 2): "GROSS PROFIT",
                (76, 2): "PATAM",
            }
            return mapping.get((row, col))
        return None

    def get_numeric_value(self, sheet_name: str, row: int, col: int) -> float | None:
        if sheet_name == "Top Sheet" and row == 10 and 7 <= col <= 18:
            return float(col - 6)
        return None

    def get_date_value(self, sheet_name: str, row: int, col: int) -> str | None:
        return None

    def get_merged_regions_count(self, sheet_name: str) -> int:
        return 0


def test_template_matcher_fails_when_required_sheet_missing():
    matcher = TemplateMatcher(FakeReader(missing_bid_s=True))
    result = matcher.validate()

    assert result.template_match is False
    assert any(issue.code == "BID_S_MISSING_REQUIRED_SHEET" for issue in result.issues)


def test_template_matcher_fails_when_required_anchor_mismatch():
    matcher = TemplateMatcher(FakeReader(mismatch_general_b2=True))
    result = matcher.validate()

    assert result.template_match is False
    assert any(issue.code == "GENERAL_MISSING_REQUIRED_ANCHOR" and issue.cell_ref == "B2" for issue in result.issues)
