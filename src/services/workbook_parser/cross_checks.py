"""Cross-check functions for workbook parser."""

from __future__ import annotations

from src.services.workbook_parser.issues import CrossCheck


def _value(obj: object, key: str) -> object:
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _line_by_canonical(lines: object, canonical_key: str) -> object:
    if not isinstance(lines, list):
        return None
    for line in lines:
        if _value(line, "canonical_key") == canonical_key:
            return line
    return None


def _relative_delta(left_value: float, right_value: float, delta_abs: float) -> float | None:
    denominator = abs(right_value)
    if denominator == 0:
        return None
    return delta_abs / denominator


def _exact_check(code: str, left_field_path: str, right_field_path: str, left_value: object, right_value: object) -> CrossCheck:
    if left_value is None or right_value is None:
        return CrossCheck(
            code=code,
            status="skipped",
            left_field_path=left_field_path,
            right_field_path=right_field_path,
            left_value=left_value,
            right_value=right_value,
            tolerance_abs=None,
            tolerance_rel=None,
            delta_abs=None,
            delta_rel=None,
            note="Skipped because one side is missing",
        )

    status = "pass" if left_value == right_value else "warn"
    return CrossCheck(
        code=code,
        status=status,
        left_field_path=left_field_path,
        right_field_path=right_field_path,
        left_value=left_value,
        right_value=right_value,
        tolerance_abs=None,
        tolerance_rel=None,
        delta_abs=None,
        delta_rel=None,
        note=None,
    )


def _numeric_check(
    code: str,
    left_field_path: str,
    right_field_path: str,
    left_value: object,
    right_value: object,
    tolerance_abs: float | None = None,
    tolerance_rel: float | None = None,
    informational_only: bool = False,
) -> CrossCheck:
    if left_value is None or right_value is None:
        return CrossCheck(
            code=code,
            status="skipped",
            left_field_path=left_field_path,
            right_field_path=right_field_path,
            left_value=left_value,
            right_value=right_value,
            tolerance_abs=tolerance_abs,
            tolerance_rel=tolerance_rel,
            delta_abs=None,
            delta_rel=None,
            note="Skipped because one side is missing",
        )

    left_number = float(left_value)
    right_number = float(right_value)
    delta_abs = abs(left_number - right_number)
    delta_rel = _relative_delta(left_number, right_number, delta_abs)

    within_abs = tolerance_abs is not None and delta_abs <= tolerance_abs
    within_rel = tolerance_rel is not None and delta_rel is not None and delta_rel <= tolerance_rel
    if tolerance_abs is None and tolerance_rel is None:
        is_within = delta_abs == 0
    else:
        is_within = within_abs or within_rel

    status = "pass" if is_within else "warn"
    note = None
    if informational_only and not is_within:
        note = "Informational delta; structural scope difference expected"

    return CrossCheck(
        code=code,
        status=status,
        left_field_path=left_field_path,
        right_field_path=right_field_path,
        left_value=left_number,
        right_value=right_number,
        tolerance_abs=tolerance_abs,
        tolerance_rel=tolerance_rel,
        delta_abs=delta_abs,
        delta_rel=delta_rel,
        note=note,
    )


def run_identity_cross_checks(
    general_identity: object,
    bid_s_identity: object,
    top_sheet_identity: object,
) -> list[CrossCheck]:
    fields = [
        "inquiry_no",
        "client_name",
        "client_inquiry_no",
        "subject",
        "project_name",
    ]

    checks: list[CrossCheck] = []
    for field in fields:
        checks.append(
            _exact_check(
                code=f"GENERAL_vs_BID_S_{field.upper()}",
                left_field_path=f"workbook_profile.rfq_identity.{field}",
                right_field_path=f"workbook_profile.identity_mirrors.bid_s.{field}",
                left_value=_value(general_identity, field),
                right_value=_value(bid_s_identity, field),
            )
        )
        checks.append(
            _exact_check(
                code=f"GENERAL_vs_TOP_SHEET_{field.upper()}",
                left_field_path=f"workbook_profile.rfq_identity.{field}",
                right_field_path=f"workbook_profile.identity_mirrors.top_sheet.{field}",
                left_value=_value(general_identity, field),
                right_value=_value(top_sheet_identity, field),
            )
        )

    return checks


def run_numeric_cross_checks(
    workbook_profile: dict,
    cost_breakdown_profile: dict,
) -> list[CrossCheck]:
    general_summary = _value(workbook_profile.get("general", {}), "general_summary")
    bid_summary = _value(cost_breakdown_profile.get("bid_s", {}), "bid_summary")
    top_sheet_summary = _value(cost_breakdown_profile.get("top_sheet", {}), "top_sheet_summary")
    bid_meta = _value(workbook_profile.get("bid_s", {}), "bid_meta")

    bid_summary_lines = _value(cost_breakdown_profile.get("bid_s", {}), "bid_summary_lines")
    top_sheet_lines = _value(cost_breakdown_profile.get("top_sheet", {}), "top_sheet_lines")

    bid_financial_charges = _line_by_canonical(bid_summary_lines, "financial_charges")
    top_financial_charges = _line_by_canonical(top_sheet_lines, "financial_charges")
    top_escalation = _line_by_canonical(top_sheet_lines, "escalation_on_material")
    top_negotiation = _line_by_canonical(top_sheet_lines, "negotiation")

    return [
        _numeric_check(
            code="GENERAL_TOTAL_WEIGHT_vs_BID_S_TOTAL_WEIGHT",
            left_field_path="workbook_profile.general_summary.total_weight_ton",
            right_field_path="workbook_profile.bid_meta.total_weight_ton",
            left_value=_value(general_summary, "total_weight_ton"),
            right_value=_value(bid_meta, "total_weight_ton"),
            tolerance_rel=0.0001,
        ),
        _numeric_check(
            code="TOP_SHEET_TOTAL_REVENUE_vs_BID_S_GRAND_TOTAL",
            left_field_path="cost_breakdown_profile.top_sheet_summary.total_revenue.rev00_value",
            right_field_path="cost_breakdown_profile.bid_summary.grand_total.amount_sar",
            left_value=_value(_value(top_sheet_summary, "total_revenue"), "rev00_value"),
            right_value=_value(_value(bid_summary, "grand_total"), "amount_sar"),
            tolerance_rel=0.0001,
        ),
        _numeric_check(
            code="TOP_SHEET_FINANCIAL_CHARGES_vs_BID_S_FINANCIAL_CHARGES",
            left_field_path="cost_breakdown_profile.top_sheet_lines[financial_charges].rev00_value",
            right_field_path="cost_breakdown_profile.bid_summary_lines[financial_charges].amount_sar",
            left_value=_value(top_financial_charges, "rev00_value"),
            right_value=_value(bid_financial_charges, "amount_sar"),
            tolerance_abs=0.01,
        ),
        _numeric_check(
            code="TOP_SHEET_ESCALATION_vs_BID_S_ESCALATION",
            left_field_path="cost_breakdown_profile.top_sheet_lines[escalation_on_material].rev00_value",
            right_field_path="cost_breakdown_profile.bid_summary.escalation_on_material.amount_sar",
            left_value=_value(top_escalation, "rev00_value"),
            right_value=_value(_value(bid_summary, "escalation_on_material"), "amount_sar"),
            tolerance_abs=0.01,
        ),
        _numeric_check(
            code="TOP_SHEET_NEGOTIATION_vs_BID_S_NEGOTIATION",
            left_field_path="cost_breakdown_profile.top_sheet_lines[negotiation].rev00_value",
            right_field_path="cost_breakdown_profile.bid_summary.negotiation.amount_sar",
            left_value=_value(top_negotiation, "rev00_value"),
            right_value=_value(_value(bid_summary, "negotiation"), "amount_sar"),
            tolerance_abs=0.01,
        ),
        _numeric_check(
            code="TOP_SHEET_DIRECT_COST_vs_BID_S_TOTAL_DIRECT_COST",
            left_field_path="cost_breakdown_profile.top_sheet_summary.total_project_direct_cost.rev00_value",
            right_field_path="cost_breakdown_profile.bid_summary.total_direct_cost.amount_sar",
            left_value=_value(_value(top_sheet_summary, "total_project_direct_cost"), "rev00_value"),
            right_value=_value(_value(bid_summary, "total_direct_cost"), "amount_sar"),
            tolerance_abs=0.01,
            informational_only=True,
        ),
    ]


def run_cross_checks(
    general_data: dict,
    bid_s_data: dict,
    top_sheet_data: dict,
) -> list[CrossCheck]:
    checks = []
    checks.extend(
        run_identity_cross_checks(
            general_identity=general_data.get("rfq_identity", {}),
            bid_s_identity=bid_s_data.get("identity_mirror", {}),
            top_sheet_identity=top_sheet_data.get("identity_mirror", {}),
        )
    )
    checks.extend(
        run_numeric_cross_checks(
            workbook_profile={
                "general": general_data,
                "bid_s": bid_s_data,
                "top_sheet": top_sheet_data,
            },
            cost_breakdown_profile={"bid_s": bid_s_data, "top_sheet": top_sheet_data},
        )
    )
    return checks
