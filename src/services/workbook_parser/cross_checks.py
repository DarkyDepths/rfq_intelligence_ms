"""Cross-check skeleton functions for workbook parser."""

from __future__ import annotations

from src.services.workbook_parser.issues import CrossCheck


def run_identity_cross_checks(
    general_identity: dict,
    bid_s_identity: dict,
    top_sheet_identity: dict,
) -> list[CrossCheck]:
    """Step 9 skeleton: identity checks are defined but not fully implemented yet."""
    _ = (general_identity, bid_s_identity, top_sheet_identity)
    return []


def run_numeric_cross_checks(
    workbook_profile: dict,
    cost_breakdown_profile: dict,
) -> list[CrossCheck]:
    """Step 9 skeleton: numeric tolerance checks are TODO for Step 10."""
    _ = (workbook_profile, cost_breakdown_profile)
    return []


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
            workbook_profile={"general": general_data, "bid_s": bid_s_data, "top_sheet": top_sheet_data},
            cost_breakdown_profile={"bid_s": bid_s_data, "top_sheet": top_sheet_data},
        )
    )
    return checks
