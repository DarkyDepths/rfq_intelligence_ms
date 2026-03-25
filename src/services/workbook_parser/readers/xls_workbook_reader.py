"""xlrd-based .xls workbook reader implementation."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import xlrd

from src.services.workbook_parser.normalizers import normalize_empty_to_none
from src.services.workbook_parser.readers.workbook_reader import WorkbookReader


class XlsWorkbookReader(WorkbookReader):
    def __init__(self) -> None:
        self._workbook: xlrd.book.Book | None = None
        self._sheets: dict[str, xlrd.sheet.Sheet] = {}

    def open(self, workbook_path: str) -> None:
        path = Path(workbook_path)
        if not path.exists():
            raise FileNotFoundError(f"Workbook file not found: {workbook_path}")
        self._workbook = xlrd.open_workbook(path.as_posix(), formatting_info=True)
        self._sheets = {
            sheet_name: self._workbook.sheet_by_name(sheet_name)
            for sheet_name in self._workbook.sheet_names()
        }

    def get_sheet_names(self) -> list[str]:
        self._ensure_open()
        return list(self._sheets.keys())

    def has_sheet(self, sheet_name: str) -> bool:
        self._ensure_open()
        return sheet_name in self._sheets

    def get_cell_value(self, sheet_name: str, row: int, col: int) -> object:
        sheet = self._sheet(sheet_name)
        return sheet.cell_value(row - 1, col - 1)

    def get_label_value(self, sheet_name: str, row: int, col: int) -> str | None:
        sheet = self._sheet(sheet_name)
        r0 = row - 1
        c0 = col - 1
        value = sheet.cell_value(r0, c0)
        if value not in ("", None):
            return normalize_empty_to_none(value)

        for row_low, row_high, col_low, col_high in sheet.merged_cells:
            if row_low <= r0 < row_high and col_low <= c0 < col_high:
                top_left = sheet.cell_value(row_low, col_low)
                return normalize_empty_to_none(top_left)

        return normalize_empty_to_none(value)

    def get_numeric_value(self, sheet_name: str, row: int, col: int) -> float | None:
        sheet = self._sheet(sheet_name)
        r0 = row - 1
        c0 = col - 1
        cell_type = sheet.cell_type(r0, c0)
        if cell_type == xlrd.XL_CELL_NUMBER:
            return float(sheet.cell_value(r0, c0))
        if cell_type == xlrd.XL_CELL_BOOLEAN:
            return float(int(sheet.cell_value(r0, c0)))
        return None

    def get_date_value(self, sheet_name: str, row: int, col: int) -> date | None:
        sheet = self._sheet(sheet_name)
        r0 = row - 1
        c0 = col - 1
        cell_type = sheet.cell_type(r0, c0)
        if cell_type != xlrd.XL_CELL_DATE:
            return None
        workbook = self._ensure_open()
        y, m, d, _, _, _ = xlrd.xldate_as_tuple(sheet.cell_value(r0, c0), workbook.datemode)
        return date(y, m, d)

    def get_merged_regions_count(self, sheet_name: str) -> int:
        sheet = self._sheet(sheet_name)
        return len(sheet.merged_cells)

    def _ensure_open(self) -> xlrd.book.Book:
        if self._workbook is None:
            raise RuntimeError("Workbook is not loaded. Call open() first.")
        return self._workbook

    def _sheet(self, sheet_name: str) -> xlrd.sheet.Sheet:
        self._ensure_open()
        if sheet_name not in self._sheets:
            raise KeyError(f"Sheet not found: {sheet_name}")
        return self._sheets[sheet_name]
