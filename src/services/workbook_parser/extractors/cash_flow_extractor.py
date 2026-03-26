"""Cash Flow sheet extractor for Pack 2 Step 17."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.services.workbook_parser.contracts import (
    CashFlowLine,
    CashFlowMonthlyValues,
    CashFlowSummary,
    RfqIdentityMirrorCashFlow,
)
from src.services.workbook_parser.issues import AnchorCheck, ParserIssue, SheetReport
from src.services.workbook_parser.normalizers import normalize_empty_to_none, normalize_label
from src.services.workbook_parser.readers.workbook_reader import WorkbookReader
from src.services.workbook_parser.template_matcher import excel_ref_to_row_col


_CASH_FLOW_SHEET = "Cash Flow"
_BODY_START_ROW = 15
_BODY_END_ROW = 21

_TEXT_ANCHORS: list[tuple[str, str, bool]] = [
    ("A7", "Enquiry No:", True),
    ("A8", "Project:", True),
    ("A9", "Client:", True),
    ("O12", "Dated:", False),
    ("A14", "Description", True),
    ("D14", "Month-1", True),
    ("O14", "Month-12", True),
    ("P14", "Total %", False),
]

_ROW_TO_CANONICAL_KEY: dict[int, str] = {
    15: "net_in_out_flow",
    16: "cumulative_inflow",
    17: "cash_inflow",
    18: "cash_inflow_pct",
    19: "cumulative_outflow",
    20: "cash_outflow",
    21: "cash_outflow_pct",
}

_SUMMARY_KEYS = {"net_in_out_flow", "cumulative_inflow", "cumulative_outflow"}


def _to_float(value: float | int | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _monthly_values_for(reader: WorkbookReader, row: int) -> CashFlowMonthlyValues:
    values = [_to_float(reader.get_numeric_value(_CASH_FLOW_SHEET, row, col)) for col in range(4, 16)]
    return CashFlowMonthlyValues(
        month_1=values[0],
        month_2=values[1],
        month_3=values[2],
        month_4=values[3],
        month_5=values[4],
        month_6=values[5],
        month_7=values[6],
        month_8=values[7],
        month_9=values[8],
        month_10=values[9],
        month_11=values[10],
        month_12=values[11],
    )


def _months_non_null(values: CashFlowMonthlyValues) -> int:
    return sum(1 for month in values.__dict__.values() if month is not None)


def _build_anchor_results(reader: WorkbookReader) -> tuple[list[AnchorCheck], list[ParserIssue]]:
    checks: list[AnchorCheck] = []
    issues: list[ParserIssue] = []

    for cell_ref, expected, hard_fail in _TEXT_ANCHORS:
        row, col = excel_ref_to_row_col(cell_ref)
        actual = reader.get_label_value(_CASH_FLOW_SHEET, row, col)
        passed = normalize_label(actual) == normalize_label(expected)
        checks.append(
            AnchorCheck(
                sheet_name=_CASH_FLOW_SHEET,
                cell_ref=cell_ref,
                expected_normalized_value=normalize_label(expected) or "",
                actual_normalized_value=normalize_label(actual),
                passed=passed,
            )
        )
        if not passed:
            issues.append(
                ParserIssue(
                    code="CASH_FLOW_MISSING_REQUIRED_ANCHOR",
                    severity="error" if hard_fail else "warning",
                    sheet_name=_CASH_FLOW_SHEET,
                    cell_ref=cell_ref,
                    row_number=row,
                    field_path=None,
                    message="Cash Flow anchor value mismatch",
                    expected_value=expected,
                    actual_value=actual,
                    raw_value=actual,
                )
            )

    return checks, issues


@dataclass(frozen=True)
class CashFlowExtractionResult:
    identity_mirror: RfqIdentityMirrorCashFlow = field(default_factory=RfqIdentityMirrorCashFlow)
    cash_flow_lines: list[CashFlowLine] = field(default_factory=list)
    cash_flow_summary: CashFlowSummary = field(default_factory=CashFlowSummary)
    anchor_checks: list[AnchorCheck] = field(default_factory=list)
    issues: list[ParserIssue] = field(default_factory=list)
    sheet_report: SheetReport = field(
        default_factory=lambda: SheetReport(
            sheet_name="Cash Flow",
            status="parsed_ok",
            merged_regions_count=None,
            expected_body_range="15:21",
            rows_scanned=0,
            rows_kept=0,
            rows_skipped=0,
            warning_count=0,
            error_count=0,
        )
    )


class CashFlowExtractor:
    def __init__(self, reader: WorkbookReader):
        self._reader = reader

    def extract(self) -> CashFlowExtractionResult:
        if not self._reader.has_sheet(_CASH_FLOW_SHEET):
            issue = ParserIssue(
                code="CASH_FLOW_MISSING_REQUIRED_SHEET",
                severity="error",
                sheet_name=_CASH_FLOW_SHEET,
                cell_ref=None,
                row_number=None,
                field_path=None,
                message="Required sheet is missing: Cash Flow",
                expected_value=_CASH_FLOW_SHEET,
                actual_value=None,
                raw_value=None,
            )
            return CashFlowExtractionResult(
                issues=[issue],
                sheet_report=SheetReport(
                    sheet_name=_CASH_FLOW_SHEET,
                    status="failed",
                    merged_regions_count=None,
                    expected_body_range="15:21",
                    rows_scanned=0,
                    rows_kept=0,
                    rows_skipped=0,
                    warning_count=0,
                    error_count=1,
                ),
            )

        anchor_checks, anchor_issues = _build_anchor_results(self._reader)
        issues = list(anchor_issues)

        identity_mirror = RfqIdentityMirrorCashFlow(
            inquiry_no=normalize_empty_to_none(self._reader.get_label_value(_CASH_FLOW_SHEET, 7, 3)),
            project_name=normalize_empty_to_none(self._reader.get_label_value(_CASH_FLOW_SHEET, 8, 3)),
            client_name=normalize_empty_to_none(self._reader.get_label_value(_CASH_FLOW_SHEET, 9, 3)),
            dated=self._reader.get_date_value(_CASH_FLOW_SHEET, 12, 16),
        )

        cash_flow_lines: list[CashFlowLine] = []
        rows_scanned = (_BODY_END_ROW - _BODY_START_ROW) + 1
        rows_skipped = 0

        for row in range(_BODY_START_ROW, _BODY_END_ROW + 1):
            canonical_key = _ROW_TO_CANONICAL_KEY.get(row)
            if canonical_key is None:
                rows_skipped += 1
                continue

            label_raw = normalize_empty_to_none(self._reader.get_label_value(_CASH_FLOW_SHEET, row, 2))
            if label_raw is None:
                rows_skipped += 1
                issues.append(
                    ParserIssue(
                        code="CASH_FLOW_MISSING_REQUIRED_LINE_LABEL",
                        severity="warning",
                        sheet_name=_CASH_FLOW_SHEET,
                        cell_ref=f"B{row}",
                        row_number=row,
                        field_path="cost_breakdown_profile.financial_profile.cash_flow_lines[].label_raw",
                        message="Expected Cash Flow line label is blank",
                        expected_value="non-empty",
                        actual_value=None,
                        raw_value=None,
                    )
                )
                continue

            monthly_values = _monthly_values_for(self._reader, row)
            total_cell_value = _to_float(self._reader.get_numeric_value(_CASH_FLOW_SHEET, row, 16))

            total_pct: float | None = None
            total_sr: float | None = None
            if canonical_key.endswith("_pct"):
                total_pct = total_cell_value
            else:
                total_sr = total_cell_value

            cash_flow_lines.append(
                CashFlowLine(
                    sheet_row=row,
                    canonical_key=canonical_key,
                    line_kind="summary" if canonical_key in _SUMMARY_KEYS else "detail",
                    label_raw=label_raw,
                    monthly_values=monthly_values,
                    total_pct=total_pct,
                    total_sr=total_sr,
                )
            )

        lines_by_key = {line.canonical_key: line for line in cash_flow_lines}

        net_in_out_line = lines_by_key.get("net_in_out_flow")
        cash_inflow_line = lines_by_key.get("cash_inflow")
        cash_inflow_pct_line = lines_by_key.get("cash_inflow_pct")
        cash_outflow_line = lines_by_key.get("cash_outflow")
        cash_outflow_pct_line = lines_by_key.get("cash_outflow_pct")

        net_month_12 = None
        negative_months_count = 0
        peak_negative_exposure = None
        months_with_data = 0

        if net_in_out_line is not None:
            net_values = [
                net_in_out_line.monthly_values.month_1,
                net_in_out_line.monthly_values.month_2,
                net_in_out_line.monthly_values.month_3,
                net_in_out_line.monthly_values.month_4,
                net_in_out_line.monthly_values.month_5,
                net_in_out_line.monthly_values.month_6,
                net_in_out_line.monthly_values.month_7,
                net_in_out_line.monthly_values.month_8,
                net_in_out_line.monthly_values.month_9,
                net_in_out_line.monthly_values.month_10,
                net_in_out_line.monthly_values.month_11,
                net_in_out_line.monthly_values.month_12,
            ]
            net_month_12 = net_in_out_line.monthly_values.month_12
            negative_values = [value for value in net_values if value is not None and value < 0]
            negative_months_count = len(negative_values)
            peak_negative_exposure = min(negative_values) if negative_values else None

        if cash_inflow_line is not None:
            months_with_data = _months_non_null(cash_inflow_line.monthly_values)

        cash_flow_summary = CashFlowSummary(
            total_inflow_sr=cash_inflow_line.total_sr if cash_inflow_line is not None else None,
            total_outflow_sr=cash_outflow_line.total_sr if cash_outflow_line is not None else None,
            total_inflow_pct=cash_inflow_pct_line.total_pct if cash_inflow_pct_line is not None else None,
            total_outflow_pct=cash_outflow_pct_line.total_pct if cash_outflow_pct_line is not None else None,
            net_cash_position_final=net_month_12,
            months_with_data=months_with_data,
            negative_months_count=negative_months_count,
            peak_negative_exposure=peak_negative_exposure,
        )

        warning_count = sum(1 for issue in issues if issue.severity == "warning")
        error_count = sum(1 for issue in issues if issue.severity == "error")

        status = "parsed_ok"
        if error_count > 0:
            status = "failed"
        elif warning_count > 0:
            status = "parsed_with_warnings"

        return CashFlowExtractionResult(
            identity_mirror=identity_mirror,
            cash_flow_lines=cash_flow_lines,
            cash_flow_summary=cash_flow_summary,
            anchor_checks=anchor_checks,
            issues=issues,
            sheet_report=SheetReport(
                sheet_name=_CASH_FLOW_SHEET,
                status=status,
                merged_regions_count=self._reader.get_merged_regions_count(_CASH_FLOW_SHEET),
                expected_body_range="15:21",
                rows_scanned=rows_scanned,
                rows_kept=len(cash_flow_lines),
                rows_skipped=rows_skipped,
                warning_count=warning_count,
                error_count=error_count,
            ),
        )