"""xlrd-based .xls workbook reader implementation."""

from __future__ import annotations

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
        if path.suffix.lower() != ".xls":
            raise ValueError(f"Unsupported workbook format for Step 10 reader: {path.suffix}")
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
        sheet, r0, c0 = self._cell(sheet_name, row, col)
        return sheet.cell_value(r0, c0)

    def get_label_value(self, sheet_name: str, row: int, col: int) -> str | None:
        sheet, r0, c0 = self._cell(sheet_name, row, col)
        value = sheet.cell_value(r0, c0)
        if value not in ("", None):
            return normalize_empty_to_none(value)

        for row_low, row_high, col_low, col_high in sheet.merged_cells:
            if row_low <= r0 < row_high and col_low <= c0 < col_high:
                top_left = sheet.cell_value(row_low, col_low)
                return normalize_empty_to_none(top_left)

        return normalize_empty_to_none(value)

    def get_numeric_value(self, sheet_name: str, row: int, col: int) -> float | None:
        sheet, r0, c0 = self._cell(sheet_name, row, col)
        cell_type = sheet.cell_type(r0, c0)
        if cell_type == xlrd.XL_CELL_NUMBER:
            return float(sheet.cell_value(r0, c0))
        if cell_type == xlrd.XL_CELL_BOOLEAN:
            return float(int(sheet.cell_value(r0, c0)))
        return None

    def get_date_value(self, sheet_name: str, row: int, col: int) -> str | None:
        sheet, r0, c0 = self._cell(sheet_name, row, col)
        cell_type = sheet.cell_type(r0, c0)
        if cell_type != xlrd.XL_CELL_DATE:
            return None
        workbook = self._ensure_open()
        try:
            y, m, d, _, _, _ = xlrd.xldate_as_tuple(sheet.cell_value(r0, c0), workbook.datemode)
            return f"{y:04d}-{m:02d}-{d:02d}"
        except (TypeError, ValueError, OverflowError):
            return None

    def get_merged_regions_count(self, sheet_name: str) -> int:
        sheet = self._sheet(sheet_name)
        return len(sheet.merged_cells)

    def _ensure_open(self) -> xlrd.book.Book:
        if self._workbook is None:
            raise RuntimeError("Workbook is not loaded. Call open() first.")
        return self._workbook

    def _cell(self, sheet_name: str, row: int, col: int) -> tuple[xlrd.sheet.Sheet, int, int]:
        if row < 1 or col < 1:
            raise ValueError("Workbook coordinates are 1-based and must be >= 1.")

        sheet = self._sheet(sheet_name)
        r0 = row - 1
        c0 = col - 1
        if r0 >= sheet.nrows or c0 >= sheet.ncols:
            raise IndexError(
                f"Cell out of bounds: sheet={sheet_name}, row={row}, col={col}, max_rows={sheet.nrows}, max_cols={sheet.ncols}"
            )
        return sheet, r0, c0

    def _sheet(self, sheet_name: str) -> xlrd.sheet.Sheet:
        self._ensure_open()
        if sheet_name not in self._sheets:
            raise KeyError(f"Sheet not found: {sheet_name}")
        return self._sheets[sheet_name]
