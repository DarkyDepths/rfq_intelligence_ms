"""General sheet extractor stub for Step 9."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.services.workbook_parser.contracts import GeneralItemRow, GeneralSummary, RfqIdentityPrimary
from src.services.workbook_parser.normalizers import normalize_empty_to_none, normalize_numeric
from src.services.workbook_parser.issues import AnchorCheck, ParserIssue, SheetReport
from src.services.workbook_parser.readers.workbook_reader import WorkbookReader


_GENERAL_SHEET = "General"
_BODY_START_ROW = 14
_BODY_END_ROW = 62


def _normalize_revision(value: object) -> str | None:
    numeric = normalize_numeric(value)
    if numeric is None:
        text = normalize_empty_to_none(value)
        return text
    if isinstance(numeric, int):
        return str(numeric)
    if float(numeric).is_integer():
        return str(int(numeric))
    return str(numeric)


def _normalize_yes_no_field(value: object) -> tuple[bool | None, bool]:
    text = normalize_empty_to_none(value)
    if text is None:
        return None, False

    lowered = text.lower()
    if lowered == "yes":
        return True, False
    if lowered == "no":
        return False, False
    return None, True


def _safe_float(value: float | int | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _safe_int(value: float | int | None) -> int | None:
    if value is None:
        return None
    numeric = float(value)
    if numeric.is_integer():
        return int(numeric)
    return None


def _is_meaningful_tag(value: str | None) -> bool:
    return value is not None and value.upper() != "E"


def _is_meaningful_description(value: str | None) -> bool:
    return value is not None and value.upper() != "XXXX"


@dataclass(frozen=True)
class GeneralExtractionResult:
    rfq_identity: RfqIdentityPrimary = field(default_factory=RfqIdentityPrimary)
    general_item_rows: list[GeneralItemRow] = field(default_factory=list)
    general_summary: GeneralSummary = field(default_factory=GeneralSummary)
    anchor_checks: list[AnchorCheck] = field(default_factory=list)
    issues: list[ParserIssue] = field(default_factory=list)
    sheet_report: SheetReport = field(
        default_factory=lambda: SheetReport(
            sheet_name="General",
            status="parsed_ok",
            merged_regions_count=None,
            expected_body_range="14:62",
            rows_scanned=0,
            rows_kept=0,
            rows_skipped=0,
            warning_count=0,
            error_count=0,
        )
    )


class GeneralExtractor:
    def __init__(self, reader: WorkbookReader):
        self._reader = reader

    def extract(self) -> GeneralExtractionResult:
        if not self._reader.has_sheet(_GENERAL_SHEET):
            issue = ParserIssue(
                code="GENERAL_MISSING_REQUIRED_SHEET",
                severity="error",
                sheet_name=_GENERAL_SHEET,
                cell_ref=None,
                row_number=None,
                field_path=None,
                message="Required sheet is missing: General",
                expected_value=_GENERAL_SHEET,
                actual_value=None,
                raw_value=None,
            )
            return GeneralExtractionResult(
                issues=[issue],
                sheet_report=SheetReport(
                    sheet_name=_GENERAL_SHEET,
                    status="failed",
                    merged_regions_count=None,
                    expected_body_range="14:62",
                    rows_scanned=0,
                    rows_kept=0,
                    rows_skipped=0,
                    warning_count=0,
                    error_count=1,
                ),
            )

        issues: list[ParserIssue] = []

        inquiry_no = normalize_empty_to_none(self._reader.get_label_value(_GENERAL_SHEET, 4, 4))
        revision_no = _normalize_revision(self._reader.get_cell_value(_GENERAL_SHEET, 4, 8))
        client_name = normalize_empty_to_none(self._reader.get_label_value(_GENERAL_SHEET, 5, 4))
        status_value = normalize_empty_to_none(self._reader.get_label_value(_GENERAL_SHEET, 5, 8))
        client_inquiry_no = normalize_empty_to_none(self._reader.get_label_value(_GENERAL_SHEET, 6, 4))
        subject = normalize_empty_to_none(self._reader.get_label_value(_GENERAL_SHEET, 7, 4))
        project_name = normalize_empty_to_none(self._reader.get_label_value(_GENERAL_SHEET, 8, 4))
        inquiry_date = self._reader.get_date_value(_GENERAL_SHEET, 9, 4)

        required_identity_fields = [
            ("inquiry_no", inquiry_no, "D4"),
            ("client_name", client_name, "D5"),
            ("subject", subject, "D7"),
            ("project_name", project_name, "D8"),
        ]
        for field_name, field_value, cell_ref in required_identity_fields:
            if field_value is None:
                issues.append(
                    ParserIssue(
                        code="GENERAL_MISSING_REQUIRED_FIELD",
                        severity="warning",
                        sheet_name=_GENERAL_SHEET,
                        cell_ref=cell_ref,
                        row_number=int(cell_ref[1:]),
                        field_path=f"workbook_profile.rfq_identity.{field_name}",
                        message=f"Required identity field is missing: {field_name}",
                        expected_value="non-empty",
                        actual_value=None,
                        raw_value=None,
                    )
                )

        rfq_identity = RfqIdentityPrimary(
            inquiry_no=inquiry_no,
            revision_no=revision_no,
            client_name=client_name,
            status=status_value,
            client_inquiry_no=client_inquiry_no,
            subject=subject,
            project_name=project_name,
            inquiry_date=inquiry_date,
        )

        kept_rows: list[GeneralItemRow] = []
        rows_scanned = (_BODY_END_ROW - _BODY_START_ROW) + 1
        rows_skipped = 0

        for row in range(_BODY_START_ROW, _BODY_END_ROW + 1):
            sr_no = _safe_int(self._reader.get_numeric_value(_GENERAL_SHEET, row, 1))
            item_tag = normalize_empty_to_none(self._reader.get_label_value(_GENERAL_SHEET, row, 2))
            item_revision = _normalize_revision(self._reader.get_cell_value(_GENERAL_SHEET, row, 3))
            item_description = normalize_empty_to_none(self._reader.get_label_value(_GENERAL_SHEET, row, 4))

            qty = _safe_float(self._reader.get_numeric_value(_GENERAL_SHEET, row, 5))
            diameter = _safe_float(self._reader.get_numeric_value(_GENERAL_SHEET, row, 6))
            length = _safe_float(self._reader.get_numeric_value(_GENERAL_SHEET, row, 7))
            thickness = _safe_float(self._reader.get_numeric_value(_GENERAL_SHEET, row, 8))
            unit_weight_ton = _safe_float(self._reader.get_numeric_value(_GENERAL_SHEET, row, 9))
            total_weight_ton = _safe_float(self._reader.get_numeric_value(_GENERAL_SHEET, row, 10))

            material = normalize_empty_to_none(self._reader.get_label_value(_GENERAL_SHEET, row, 11))
            item_type = normalize_empty_to_none(self._reader.get_label_value(_GENERAL_SHEET, row, 12))
            rt_level = normalize_empty_to_none(self._reader.get_label_value(_GENERAL_SHEET, row, 13))
            rt_source = normalize_empty_to_none(self._reader.get_label_value(_GENERAL_SHEET, row, 14))

            flag_columns = [
                ("pwht", 15),
                ("asme_stamp", 16),
                ("nb_regn_cost_flag", 17),
                ("fea_cost_flag", 18),
                ("bolts_tensioner_cost_flag", 19),
                ("material_freight_cost_flag", 20),
                ("helium_leak_test_cost_flag", 21),
                ("kom_flag", 22),
            ]

            flag_values: dict[str, bool | None] = {}
            for field_name, col in flag_columns:
                raw_flag = self._reader.get_cell_value(_GENERAL_SHEET, row, col)
                value, invalid = _normalize_yes_no_field(raw_flag)
                flag_values[field_name] = value
                if invalid:
                    issues.append(
                        ParserIssue(
                            code="GENERAL_INVALID_BOOLEAN_FLAG",
                            severity="warning",
                            sheet_name=_GENERAL_SHEET,
                            cell_ref=f"{chr(ord('A') + col - 1)}{row}",
                            row_number=row,
                            field_path=f"workbook_profile.general_item_rows[].{field_name}",
                            message="Unexpected boolean-like flag value; normalized to null",
                            expected_value="Yes/No/blank",
                            actual_value=str(raw_flag),
                            raw_value=str(raw_flag),
                        )
                    )

            placeholder_drop = (
                (item_tag is not None and item_tag.upper() == "E")
                and (item_description is not None and item_description.upper() == "XXXX")
                and (qty is None or qty == 0)
                and (unit_weight_ton is None or unit_weight_ton == 0)
                and (total_weight_ton is None or total_weight_ton == 0)
            )

            keep_row = (
                _is_meaningful_tag(item_tag)
                or _is_meaningful_description(item_description)
                or (qty is not None and qty > 0)
                or (total_weight_ton is not None and total_weight_ton > 0)
            )

            if placeholder_drop or not keep_row:
                rows_skipped += 1
                continue

            kept_rows.append(
                GeneralItemRow(
                    sheet_row=row,
                    sr_no=sr_no,
                    item_tag=item_tag,
                    item_revision=item_revision,
                    item_description=item_description,
                    qty=qty,
                    diameter=diameter,
                    length=length,
                    thickness=thickness,
                    unit_weight_ton=unit_weight_ton,
                    total_weight_ton=total_weight_ton,
                    material=material,
                    item_type=item_type,
                    rt_level=rt_level,
                    rt_source=rt_source,
                    pwht=flag_values["pwht"],
                    asme_stamp=flag_values["asme_stamp"],
                    nb_regn_cost_flag=flag_values["nb_regn_cost_flag"],
                    fea_cost_flag=flag_values["fea_cost_flag"],
                    bolts_tensioner_cost_flag=flag_values["bolts_tensioner_cost_flag"],
                    material_freight_cost_flag=flag_values["material_freight_cost_flag"],
                    helium_leak_test_cost_flag=flag_values["helium_leak_test_cost_flag"],
                    kom_flag=flag_values["kom_flag"],
                )
            )

        total_qty = sum((row.qty or 0.0) for row in kept_rows)
        total_weight = sum((row.total_weight_ton or 0.0) for row in kept_rows)
        general_summary = GeneralSummary(
            item_count=len(kept_rows),
            total_qty=float(total_qty),
            total_weight_ton=float(total_weight),
        )

        warning_count = sum(1 for issue in issues if issue.severity == "warning")
        error_count = sum(1 for issue in issues if issue.severity == "error")
        status = "parsed_ok"
        if error_count > 0:
            status = "failed"
        elif warning_count > 0:
            status = "parsed_with_warnings"

        return GeneralExtractionResult(
            rfq_identity=rfq_identity,
            general_item_rows=kept_rows,
            general_summary=general_summary,
            issues=issues,
            sheet_report=SheetReport(
                sheet_name=_GENERAL_SHEET,
                status=status,
                merged_regions_count=self._reader.get_merged_regions_count(_GENERAL_SHEET),
                expected_body_range="14:62",
                rows_scanned=rows_scanned,
                rows_kept=len(kept_rows),
                rows_skipped=rows_skipped,
                warning_count=warning_count,
                error_count=error_count,
            ),
        )
