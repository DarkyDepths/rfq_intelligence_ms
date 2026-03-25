"""Workbook reader interface for deterministic parser."""

from __future__ import annotations

from abc import ABC, abstractmethod


class WorkbookReader(ABC):
    @abstractmethod
    def open(self, workbook_path: str) -> None:
        """Load workbook into memory."""

    @abstractmethod
    def get_sheet_names(self) -> list[str]:
        """Return workbook sheet names in source order."""

    @abstractmethod
    def has_sheet(self, sheet_name: str) -> bool:
        """Return true if sheet exists."""

    @abstractmethod
    def get_cell_value(self, sheet_name: str, row: int, col: int) -> object:
        """Return raw cell value at 1-based row/column coordinates."""

    @abstractmethod
    def get_label_value(self, sheet_name: str, row: int, col: int) -> str | None:
        """Return merged-aware label text for anchor/label parsing."""

    @abstractmethod
    def get_numeric_value(self, sheet_name: str, row: int, col: int) -> float | None:
        """Return raw numeric value from exact cell without merge backfill."""

    @abstractmethod
    def get_date_value(self, sheet_name: str, row: int, col: int) -> str | None:
        """Return ISO date string (YYYY-MM-DD) using workbook datemode when cell is date-like."""

    @abstractmethod
    def get_merged_regions_count(self, sheet_name: str) -> int:
        """Return merged region count for a sheet."""
