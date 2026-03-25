"""Bid S sheet extractor stub for Step 9."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.services.workbook_parser.contracts import (
    BidMeta,
    BidSection,
    BidSummary,
    BidSummaryLine,
    BidSummaryMetric,
    RfqIdentityMirrorBidS,
)
from src.services.workbook_parser.normalizers import normalize_empty_to_none, normalize_numeric, normalize_text
from src.services.workbook_parser.issues import AnchorCheck, ParserIssue, SheetReport
from src.services.workbook_parser.readers.workbook_reader import WorkbookReader


_BID_S_SHEET = "Bid S"
_BODY_START_ROW = 14
_BODY_END_ROW = 49
_SKIP_ROWS = {36, 50}

_BID_S_CANONICAL_KEYS: dict[str, str] = {
    "material": "material",
    "direct manhours cost (ghi)": "direct_manhours_ghi",
    "direct manhours cost (hire)": "direct_manhours_hire",
    "indirect manhours cost": "indirect_manhours",
    "design": "design",
    "consumable": "consumable",
    "garnet": "garnet",
    "paint (ext.)": "paint_external",
    "paint (int.)": "paint_internal",
    "ndt": "ndt",
    "pwht": "pwht",
    "water": "water",
    "fea analysis": "fea_analysis",
    "u-stamp": "u_stamp",
    "nb": "nb",
    "bolts tensioning": "bolts_tensioning",
    "freight charges": "freight_charges",
    "vci-309": "vci_309",
    "hyd. test material/test assy": "hyd_test_material_test_assy",
    "cp": "cp",
    "transport": "transport",
    "total direct cost (a)": "total_direct_cost",
    'contingency of direct cost "a"': "contingency_direct_cost",
    "kick of meeting": "kickoff_meeting",
    "agent fee": "agent_fee",
    "insurance": "insurance",
    "financial charges": "financial_charges",
    "bu overheads": "bu_overheads",
    "total other overheads": "total_other_overheads",
    "total gross cost (b)": "total_gross_cost",
    "gross margin": "gross_margin",
    "gross price": "gross_price",
    "escalation on material": "escalation_on_material",
    "negotiation": "negotiation",
    "grand total": "grand_total",
}

_SUMMARY_CANONICAL_KEYS = {
    "total_direct_cost",
    "total_other_overheads",
    "total_gross_cost",
    "gross_price",
    "grand_total",
}

_PROMOTED_SUMMARY_ROWS: list[tuple[int, str, str]] = [
    (35, "total_direct_cost", "total_direct_cost"),
    (43, "total_other_overheads", "total_other_overheads"),
    (44, "total_gross_cost", "total_gross_cost"),
    (45, "gross_margin", "gross_margin"),
    (46, "gross_price", "gross_price"),
    (47, "escalation_on_material", "escalation_on_material"),
    (48, "negotiation", "negotiation"),
    (49, "grand_total", "grand_total"),
]


def _to_float(value: object) -> float | None:
    normalized = normalize_numeric(value)
    if normalized is None:
        return None
    return float(normalized)


def _section_for_row(row: int) -> BidSection:
    if 14 <= row <= 35:
        return "direct_cost"
    if 37 <= row <= 43:
        return "other_overheads"
    return "pricing_final"


def _canonicalize_particular(label: str | None) -> tuple[str | None, str | None]:
    if label is None:
        return None, None
    normalized = normalize_text(label)
    if normalized is None:
        return None, None
    canonical_key = _BID_S_CANONICAL_KEYS.get(normalized.lower())
    return normalized, canonical_key


def _line_kind_for(canonical_key: str | None) -> str:
    if canonical_key in _SUMMARY_CANONICAL_KEYS:
        return "summary"
    return "detail"


def _metric_from_line(line: BidSummaryLine | None, fallback_row: int, canonical_key: str) -> BidSummaryMetric:
    if line is None:
        return BidSummaryMetric(sheet_row=fallback_row, canonical_key=canonical_key)

    return BidSummaryMetric(
        sheet_row=line.sheet_row,
        canonical_key=canonical_key,
        particular_raw=line.particular_raw,
        particular_normalized=line.particular_normalized,
        basis_factor=line.basis_factor,
        amount_sar=line.amount_sar,
        amount_usd=line.amount_usd,
        share_ratio=line.share_ratio,
        per_ton_sar=line.per_ton_sar,
        per_ton_usd=line.per_ton_usd,
    )


@dataclass(frozen=True)
class BidSExtractionResult:
    identity_mirror: RfqIdentityMirrorBidS = field(default_factory=RfqIdentityMirrorBidS)
    bid_meta: BidMeta = field(default_factory=BidMeta)
    bid_summary_lines: list[BidSummaryLine] = field(default_factory=list)
    bid_summary: BidSummary | None = None
    anchor_checks: list[AnchorCheck] = field(default_factory=list)
    issues: list[ParserIssue] = field(default_factory=list)
    sheet_report: SheetReport = field(
        default_factory=lambda: SheetReport(
            sheet_name="Bid S",
            status="parsed_ok",
            merged_regions_count=None,
            expected_body_range="14:49",
            rows_scanned=0,
            rows_kept=0,
            rows_skipped=0,
            warning_count=0,
            error_count=0,
        )
    )


class BidSExtractor:
    def __init__(self, reader: WorkbookReader):
        self._reader = reader

    def extract(self) -> BidSExtractionResult:
        if not self._reader.has_sheet(_BID_S_SHEET):
            issue = ParserIssue(
                code="BID_S_MISSING_REQUIRED_SHEET",
                severity="error",
                sheet_name=_BID_S_SHEET,
                cell_ref=None,
                row_number=None,
                field_path=None,
                message="Required sheet is missing: Bid S",
                expected_value=_BID_S_SHEET,
                actual_value=None,
                raw_value=None,
            )
            return BidSExtractionResult(
                issues=[issue],
                sheet_report=SheetReport(
                    sheet_name=_BID_S_SHEET,
                    status="failed",
                    merged_regions_count=None,
                    expected_body_range="14:49",
                    rows_scanned=0,
                    rows_kept=0,
                    rows_skipped=0,
                    warning_count=0,
                    error_count=1,
                ),
            )

        issues: list[ParserIssue] = []

        identity_mirror = RfqIdentityMirrorBidS(
            inquiry_no=normalize_empty_to_none(self._reader.get_label_value(_BID_S_SHEET, 2, 3)),
            client_name=normalize_empty_to_none(self._reader.get_label_value(_BID_S_SHEET, 3, 3)),
            client_inquiry_no=normalize_empty_to_none(self._reader.get_label_value(_BID_S_SHEET, 4, 3)),
            subject=normalize_empty_to_none(self._reader.get_label_value(_BID_S_SHEET, 5, 3)),
            project_name=normalize_empty_to_none(self._reader.get_label_value(_BID_S_SHEET, 6, 3)),
        )

        bid_meta = BidMeta(
            direct_mh=_to_float(self._reader.get_numeric_value(_BID_S_SHEET, 2, 7)),
            indirect_mh=_to_float(self._reader.get_numeric_value(_BID_S_SHEET, 3, 7)),
            exchange_rate=_to_float(self._reader.get_numeric_value(_BID_S_SHEET, 4, 7)),
            total_weight_ton=_to_float(self._reader.get_numeric_value(_BID_S_SHEET, 5, 7)),
            tentative_po_date=self._reader.get_date_value(_BID_S_SHEET, 6, 7),
            delivery_text=normalize_empty_to_none(self._reader.get_label_value(_BID_S_SHEET, 7, 7)),
            dated=self._reader.get_date_value(_BID_S_SHEET, 8, 9),
            status=normalize_empty_to_none(self._reader.get_label_value(_BID_S_SHEET, 10, 2)),
        )

        required_meta_fields = [
            ("direct_mh", bid_meta.direct_mh, "G2"),
            ("indirect_mh", bid_meta.indirect_mh, "G3"),
            ("exchange_rate", bid_meta.exchange_rate, "G4"),
            ("total_weight_ton", bid_meta.total_weight_ton, "G5"),
            ("tentative_po_date", bid_meta.tentative_po_date, "G6"),
            ("delivery_text", bid_meta.delivery_text, "G7"),
            ("dated", bid_meta.dated, "I8"),
            ("status", bid_meta.status, "B10"),
        ]
        for field_name, field_value, cell_ref in required_meta_fields:
            if field_value is None:
                issues.append(
                    ParserIssue(
                        code="BID_S_MISSING_REQUIRED_FIELD",
                        severity="warning",
                        sheet_name=_BID_S_SHEET,
                        cell_ref=cell_ref,
                        row_number=int(cell_ref[1:]),
                        field_path=f"workbook_profile.bid_meta.{field_name}",
                        message=f"Missing expected Bid S metadata field: {field_name}",
                        expected_value="non-empty",
                        actual_value=None,
                        raw_value=None,
                    )
                )

        bid_summary_lines: list[BidSummaryLine] = []
        rows_scanned = (_BODY_END_ROW - _BODY_START_ROW) + 1
        rows_skipped = 0

        for row in range(_BODY_START_ROW, _BODY_END_ROW + 1):
            if row in _SKIP_ROWS:
                rows_skipped += 1
                continue

            row_no_label = normalize_empty_to_none(self._reader.get_label_value(_BID_S_SHEET, row, 1))
            particular_raw = normalize_empty_to_none(self._reader.get_label_value(_BID_S_SHEET, row, 2))

            if particular_raw is None:
                rows_skipped += 1
                continue

            particular_normalized, canonical_key = _canonicalize_particular(particular_raw)
            if canonical_key is None:
                issues.append(
                    ParserIssue(
                        code="BID_S_UNKNOWN_PARTICULAR_LABEL",
                        severity="warning",
                        sheet_name=_BID_S_SHEET,
                        cell_ref=f"B{row}",
                        row_number=row,
                        field_path="cost_breakdown_profile.bid_summary_lines[].canonical_key",
                        message="Bid S row label could not be mapped to canonical key",
                        expected_value="known canonical label",
                        actual_value=particular_normalized,
                        raw_value=particular_raw,
                    )
                )

            line = BidSummaryLine(
                sheet_row=row,
                section=_section_for_row(row),
                line_kind=_line_kind_for(canonical_key),
                row_no_label=row_no_label,
                particular_raw=particular_raw,
                particular_normalized=particular_normalized,
                canonical_key=canonical_key,
                basis_factor=_to_float(self._reader.get_numeric_value(_BID_S_SHEET, row, 4)),
                amount_sar=_to_float(self._reader.get_numeric_value(_BID_S_SHEET, row, 5)),
                amount_usd=_to_float(self._reader.get_numeric_value(_BID_S_SHEET, row, 6)),
                share_ratio=_to_float(self._reader.get_numeric_value(_BID_S_SHEET, row, 7)),
                per_ton_sar=_to_float(self._reader.get_numeric_value(_BID_S_SHEET, row, 8)),
                per_ton_usd=_to_float(self._reader.get_numeric_value(_BID_S_SHEET, row, 9)),
            )
            bid_summary_lines.append(line)

        lines_by_row = {line.sheet_row: line for line in bid_summary_lines}
        promoted_metrics: dict[str, BidSummaryMetric] = {}
        for row, canonical_key, field_name in _PROMOTED_SUMMARY_ROWS:
            line = lines_by_row.get(row)
            if line is None:
                issues.append(
                    ParserIssue(
                        code="BID_S_MISSING_SUMMARY_ROW",
                        severity="warning",
                        sheet_name=_BID_S_SHEET,
                        cell_ref=f"B{row}",
                        row_number=row,
                        field_path=f"cost_breakdown_profile.bid_summary.{field_name}",
                        message="Expected Bid S summary row was not extracted",
                        expected_value=canonical_key,
                        actual_value=None,
                        raw_value=None,
                    )
                )

            promoted_metrics[field_name] = _metric_from_line(line, fallback_row=row, canonical_key=canonical_key)

        bid_summary = BidSummary(
            total_direct_cost=promoted_metrics["total_direct_cost"],
            total_other_overheads=promoted_metrics["total_other_overheads"],
            total_gross_cost=promoted_metrics["total_gross_cost"],
            gross_margin=promoted_metrics["gross_margin"],
            gross_price=promoted_metrics["gross_price"],
            escalation_on_material=promoted_metrics["escalation_on_material"],
            negotiation=promoted_metrics["negotiation"],
            grand_total=promoted_metrics["grand_total"],
        )

        warning_count = sum(1 for issue in issues if issue.severity == "warning")
        error_count = sum(1 for issue in issues if issue.severity == "error")
        status = "parsed_ok"
        if error_count > 0:
            status = "failed"
        elif warning_count > 0:
            status = "parsed_with_warnings"

        return BidSExtractionResult(
            identity_mirror=identity_mirror,
            bid_meta=bid_meta,
            bid_summary_lines=bid_summary_lines,
            bid_summary=bid_summary,
            issues=issues,
            sheet_report=SheetReport(
                sheet_name=_BID_S_SHEET,
                status=status,
                merged_regions_count=self._reader.get_merged_regions_count(_BID_S_SHEET),
                expected_body_range="14:49",
                rows_scanned=rows_scanned,
                rows_kept=len(bid_summary_lines),
                rows_skipped=rows_skipped,
                warning_count=warning_count,
                error_count=error_count,
            ),
        )
