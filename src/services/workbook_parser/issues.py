"""Parser issue/report support types for workbook parser v2.1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ParserStatus = Literal["parsed_ok", "parsed_with_warnings", "failed"]
SheetParseStatus = Literal["parsed_ok", "parsed_with_warnings", "failed", "skipped"]
Severity = Literal["info", "warning", "error"]
CheckStatus = Literal["pass", "warn", "fail", "skipped"]
SheetName = Literal["General", "Bid S", "Top Sheet", "Cash Flow", "Mat Break-up", "B-O-Q"]


@dataclass(frozen=True)
class ParserIssue:
    code: str
    severity: Severity
    sheet_name: str | None
    cell_ref: str | None
    row_number: int | None
    field_path: str | None
    message: str
    expected_value: str | float | int | bool | None
    actual_value: str | float | int | bool | None
    raw_value: str | float | int | bool | None


@dataclass(frozen=True)
class AnchorCheck:
    sheet_name: SheetName
    cell_ref: str
    expected_normalized_value: str | float | int
    actual_normalized_value: str | float | int | None
    passed: bool


@dataclass(frozen=True)
class CrossCheck:
    code: str
    status: CheckStatus
    left_field_path: str
    right_field_path: str
    left_value: str | float | int | None
    right_value: str | float | int | None
    tolerance_abs: float | None
    tolerance_rel: float | None
    delta_abs: float | None
    delta_rel: float | None
    note: str | None


@dataclass(frozen=True)
class SheetReport:
    sheet_name: SheetName
    status: SheetParseStatus
    merged_regions_count: int | None
    expected_body_range: str | None
    rows_scanned: int | None
    rows_kept: int | None
    rows_skipped: int | None
    warning_count: int
    error_count: int


@dataclass(frozen=True)
class SheetReports:
    general: SheetReport
    bid_s: SheetReport
    top_sheet: SheetReport
    cash_flow: SheetReport | None = None
    mat_breakup: SheetReport | None = None
    boq: SheetReport | None = None
