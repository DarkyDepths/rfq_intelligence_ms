"""Top Sheet extractor stub for Step 9."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.services.workbook_parser.contracts import (
    RfqIdentityMirrorTopSheet,
    TopSheetLine,
    TopSheetMetric,
    TopSheetSection,
    TopSheetSummary,
)
from src.services.workbook_parser.normalizers import normalize_empty_to_none, normalize_numeric, normalize_text, strip_top_sheet_leading_dash
from src.services.workbook_parser.issues import AnchorCheck, ParserIssue, SheetReport
from src.services.workbook_parser.readers.workbook_reader import WorkbookReader


_TOP_SHEET = "Top Sheet"
_BODY_START_ROW = 11
_BODY_END_ROW = 76
_SKIP_ROWS = {11, 19, 59, 62}

_TOP_SHEET_CANONICAL_KEYS: dict[str, str] = {
    "revenue normal work": "revenue_normal_work",
    "revenue accrued": "revenue_accrued",
    "revenue extra work": "revenue_extra_work",
    "revenue escalation": "revenue_escalation",
    "revenue internal": "revenue_internal",
    "revenue others": "revenue_others",
    "total revenue": "total_revenue",
    "direct material": "direct_material",
    "direct labour (owned labour)": "direct_labour_owned",
    "direct manpower (hired labour)": "direct_manpower_hired",
    "in-direct labour (owned labour)": "indirect_labour_owned",
    "design cost": "design_cost",
    "boarding & lodging of d. owned labour": "boarding_lodging_direct_owned",
    "boarding & lodging of d. hired labour": "boarding_lodging_direct_hired",
    "mob. & demob. of direct labour": "mob_demob_direct_labour",
    "direct consumables": "direct_consumables",
    "garnet": "garnet",
    "paint": "paint",
    "passivation paste": "passivation_paste",
    "ndt": "ndt",
    "pwht / stress relieving": "pwht_stress_relieving",
    "water (hydro test)": "water_hydro_test",
    "fea analysis": "fea_analysis",
    "u-stamp (asme ispection)": "u_stamp_asme_inspection",
    "nb (national board registration)": "nb_national_board_registration",
    "bolts tensioning": "bolts_tensioning",
    "air freight charges": "air_freight_charges",
    "internal protection": "internal_protection",
    "hydro test material/ test assy.": "hydro_test_material_test_assy",
    "special leak testing ( helium l. test)": "special_leak_testing_helium",
    "transportation": "transportation",
    "contingencies": "contingencies",
    "kick of meeting": "kickoff_meeting",
    "agent / consultancy fee": "agent_consultancy_fee",
    "insurance": "insurance",
    "financial charges": "financial_charges",
    "escalation on material": "escalation_on_material",
    "negotiation": "negotiation",
    "sub-contracting": "sub_contracting",
    "inter ba sub-contracting": "inter_ba_sub_contracting",
    "equipment o&m": "equipment_om",
    "equipment / vehicle pol": "equipment_vehicle_pol",
    "rental of equipment": "rental_of_equipment",
    "tools": "tools",
    "depreciation & amortization": "depreciation_amortization",
    "other overheads - direct": "other_overheads_direct",
    "total project direct cost": "total_project_direct_cost",
    "contribution margin": "contribution_margin",
    "const. exp. general": "const_exp_general",
    "repair & maintenance": "repair_maintenance",
    "site facilities": "site_facilities",
    "salaries & benefits": "salaries_benefits",
    "boarding & lodging of indirect": "boarding_lodging_indirect",
    "mob. & demob. of indirect": "mob_demob_indirect",
    "other overheads - indirect": "other_overheads_indirect",
    "total project indirect cost": "total_project_indirect_cost",
    "total project cost": "total_project_cost",
    "gross profit": "gross_profit",
    "bu overheads": "bu_overheads",
    "profit before zakat & tax": "profit_before_zakat_tax",
    "zakat & tax": "zakat_tax",
    "patam": "patam",
}

_SUMMARY_KEYS = {
    "total_revenue",
    "total_project_direct_cost",
    "contribution_margin",
    "total_project_indirect_cost",
    "total_project_cost",
    "gross_profit",
    "patam",
}

_PROMOTED_SUMMARY_ROWS: list[tuple[int, str, str]] = [
    (18, "total_revenue", "total_revenue"),
    (60, "total_project_direct_cost", "total_project_direct_cost"),
    (61, "contribution_margin", "contribution_margin"),
    (70, "total_project_indirect_cost", "total_project_indirect_cost"),
    (71, "total_project_cost", "total_project_cost"),
    (72, "gross_profit", "gross_profit"),
    (73, "bu_overheads", "bu_overheads"),
    (74, "profit_before_zakat_tax", "profit_before_zakat_tax"),
    (75, "zakat_tax", "zakat_tax"),
    (76, "patam", "patam"),
]


def _to_float(value: object) -> float | None:
    normalized = normalize_numeric(value)
    if normalized is None:
        return None
    return float(normalized)


def _section_for_row(row: int) -> TopSheetSection:
    if 12 <= row <= 18:
        return "revenue"
    if 20 <= row <= 61:
        return "project_direct_cost"
    if 63 <= row <= 70:
        return "project_indirect_cost"
    return "profitability"


def _normalize_particular(label: str | None) -> str | None:
    if label is None:
        return None
    normalized = normalize_text(label)
    if normalized is None:
        return None
    return normalize_text(strip_top_sheet_leading_dash(normalized))


def _canonicalize(label: str | None) -> str | None:
    if label is None:
        return None
    return _TOP_SHEET_CANONICAL_KEYS.get(label.lower())


def _line_kind(canonical_key: str | None) -> str:
    if canonical_key in _SUMMARY_KEYS:
        return "summary"
    return "detail"


def _metric_from_line(line: TopSheetLine | None, fallback_row: int, canonical_key: str) -> TopSheetMetric:
    if line is None:
        return TopSheetMetric(sheet_row=fallback_row, canonical_key=canonical_key)

    return TopSheetMetric(
        sheet_row=line.sheet_row,
        canonical_key=canonical_key,
        particular_raw=line.particular_raw,
        particular_normalized=line.particular_normalized,
        rev00_value=line.rev00_value,
        rev00_ratio=line.rev00_ratio,
        rev01_value=line.rev01_value,
        rev01_ratio=line.rev01_ratio,
        period_1_value=line.period_1_value,
        period_2_value=line.period_2_value,
        period_3_value=line.period_3_value,
        period_4_value=line.period_4_value,
        period_5_value=line.period_5_value,
        period_6_value=line.period_6_value,
        period_7_value=line.period_7_value,
        period_8_value=line.period_8_value,
        period_9_value=line.period_9_value,
        period_10_value=line.period_10_value,
        period_11_value=line.period_11_value,
        period_12_value=line.period_12_value,
    )


@dataclass(frozen=True)
class TopSheetExtractionResult:
    identity_mirror: RfqIdentityMirrorTopSheet = field(default_factory=RfqIdentityMirrorTopSheet)
    top_sheet_lines: list[TopSheetLine] = field(default_factory=list)
    top_sheet_summary: TopSheetSummary | None = None
    anchor_checks: list[AnchorCheck] = field(default_factory=list)
    issues: list[ParserIssue] = field(default_factory=list)
    sheet_report: SheetReport = field(
        default_factory=lambda: SheetReport(
            sheet_name="Top Sheet",
            status="parsed_ok",
            merged_regions_count=None,
            expected_body_range="11:76",
            rows_scanned=0,
            rows_kept=0,
            rows_skipped=0,
            warning_count=0,
            error_count=0,
        )
    )


class TopSheetExtractor:
    def __init__(self, reader: WorkbookReader):
        self._reader = reader

    def extract(self) -> TopSheetExtractionResult:
        if not self._reader.has_sheet(_TOP_SHEET):
            issue = ParserIssue(
                code="TOP_SHEET_MISSING_REQUIRED_SHEET",
                severity="error",
                sheet_name=_TOP_SHEET,
                cell_ref=None,
                row_number=None,
                field_path=None,
                message="Required sheet is missing: Top Sheet",
                expected_value=_TOP_SHEET,
                actual_value=None,
                raw_value=None,
            )
            return TopSheetExtractionResult(
                issues=[issue],
                sheet_report=SheetReport(
                    sheet_name=_TOP_SHEET,
                    status="failed",
                    merged_regions_count=None,
                    expected_body_range="11:76",
                    rows_scanned=0,
                    rows_kept=0,
                    rows_skipped=0,
                    warning_count=0,
                    error_count=1,
                ),
            )

        issues: list[ParserIssue] = []

        identity_mirror = RfqIdentityMirrorTopSheet(
            inquiry_no=normalize_empty_to_none(self._reader.get_label_value(_TOP_SHEET, 2, 3)),
            client_name=normalize_empty_to_none(self._reader.get_label_value(_TOP_SHEET, 3, 3)),
            client_inquiry_no=normalize_empty_to_none(self._reader.get_label_value(_TOP_SHEET, 4, 3)),
            subject=normalize_empty_to_none(self._reader.get_label_value(_TOP_SHEET, 5, 3)),
            project_name=normalize_empty_to_none(self._reader.get_label_value(_TOP_SHEET, 6, 3)),
            dated=self._reader.get_date_value(_TOP_SHEET, 7, 3),
        )

        top_sheet_lines: list[TopSheetLine] = []
        rows_scanned = (_BODY_END_ROW - _BODY_START_ROW) + 1
        rows_skipped = 0

        for row in range(_BODY_START_ROW, _BODY_END_ROW + 1):
            if row in _SKIP_ROWS:
                rows_skipped += 1
                continue

            particular_raw = normalize_empty_to_none(self._reader.get_label_value(_TOP_SHEET, row, 2))
            if particular_raw is None:
                rows_skipped += 1
                continue

            particular_normalized = _normalize_particular(particular_raw)
            canonical_key = _canonicalize(particular_normalized)
            if canonical_key is None:
                issues.append(
                    ParserIssue(
                        code="TOP_SHEET_UNKNOWN_LABEL",
                        severity="warning",
                        sheet_name=_TOP_SHEET,
                        cell_ref=f"B{row}",
                        row_number=row,
                        field_path="cost_breakdown_profile.top_sheet_lines[].canonical_key",
                        message="Top Sheet row label could not be mapped to canonical key",
                        expected_value="known canonical label",
                        actual_value=particular_normalized,
                        raw_value=particular_raw,
                    )
                )

            line = TopSheetLine(
                sheet_row=row,
                section=_section_for_row(row),
                line_kind=_line_kind(canonical_key),
                particular_raw=particular_raw,
                particular_normalized=particular_normalized,
                canonical_key=canonical_key,
                rev00_value=_to_float(self._reader.get_numeric_value(_TOP_SHEET, row, 3)),
                rev00_ratio=_to_float(self._reader.get_numeric_value(_TOP_SHEET, row, 4)),
                rev01_value=_to_float(self._reader.get_numeric_value(_TOP_SHEET, row, 5)),
                rev01_ratio=_to_float(self._reader.get_numeric_value(_TOP_SHEET, row, 6)),
                period_1_value=_to_float(self._reader.get_numeric_value(_TOP_SHEET, row, 7)),
                period_2_value=_to_float(self._reader.get_numeric_value(_TOP_SHEET, row, 8)),
                period_3_value=_to_float(self._reader.get_numeric_value(_TOP_SHEET, row, 9)),
                period_4_value=_to_float(self._reader.get_numeric_value(_TOP_SHEET, row, 10)),
                period_5_value=_to_float(self._reader.get_numeric_value(_TOP_SHEET, row, 11)),
                period_6_value=_to_float(self._reader.get_numeric_value(_TOP_SHEET, row, 12)),
                period_7_value=_to_float(self._reader.get_numeric_value(_TOP_SHEET, row, 13)),
                period_8_value=_to_float(self._reader.get_numeric_value(_TOP_SHEET, row, 14)),
                period_9_value=_to_float(self._reader.get_numeric_value(_TOP_SHEET, row, 15)),
                period_10_value=_to_float(self._reader.get_numeric_value(_TOP_SHEET, row, 16)),
                period_11_value=_to_float(self._reader.get_numeric_value(_TOP_SHEET, row, 17)),
                period_12_value=_to_float(self._reader.get_numeric_value(_TOP_SHEET, row, 18)),
            )
            top_sheet_lines.append(line)

        lines_by_row = {line.sheet_row: line for line in top_sheet_lines}
        promoted_metrics: dict[str, TopSheetMetric] = {}
        for row, canonical_key, field_name in _PROMOTED_SUMMARY_ROWS:
            line = lines_by_row.get(row)
            if line is None:
                issues.append(
                    ParserIssue(
                        code="TOP_SHEET_MISSING_SUMMARY_ROW",
                        severity="warning",
                        sheet_name=_TOP_SHEET,
                        cell_ref=f"B{row}",
                        row_number=row,
                        field_path=f"cost_breakdown_profile.top_sheet_summary.{field_name}",
                        message="Expected Top Sheet summary row was not extracted",
                        expected_value=canonical_key,
                        actual_value=None,
                        raw_value=None,
                    )
                )
            promoted_metrics[field_name] = _metric_from_line(line, fallback_row=row, canonical_key=canonical_key)

        top_sheet_summary = TopSheetSummary(
            total_revenue=promoted_metrics["total_revenue"],
            total_project_direct_cost=promoted_metrics["total_project_direct_cost"],
            contribution_margin=promoted_metrics["contribution_margin"],
            total_project_indirect_cost=promoted_metrics["total_project_indirect_cost"],
            total_project_cost=promoted_metrics["total_project_cost"],
            gross_profit=promoted_metrics["gross_profit"],
            bu_overheads=promoted_metrics["bu_overheads"],
            profit_before_zakat_tax=promoted_metrics["profit_before_zakat_tax"],
            zakat_tax=promoted_metrics["zakat_tax"],
            patam=promoted_metrics["patam"],
        )

        warning_count = sum(1 for issue in issues if issue.severity == "warning")
        error_count = sum(1 for issue in issues if issue.severity == "error")
        status = "parsed_ok"
        if error_count > 0:
            status = "failed"
        elif warning_count > 0:
            status = "parsed_with_warnings"

        return TopSheetExtractionResult(
            identity_mirror=identity_mirror,
            top_sheet_lines=top_sheet_lines,
            top_sheet_summary=top_sheet_summary,
            issues=issues,
            sheet_report=SheetReport(
                sheet_name=_TOP_SHEET,
                status=status,
                merged_regions_count=self._reader.get_merged_regions_count(_TOP_SHEET),
                expected_body_range="11:76",
                rows_scanned=rows_scanned,
                rows_kept=len(top_sheet_lines),
                rows_skipped=rows_skipped,
                warning_count=warning_count,
                error_count=error_count,
            ),
        )
