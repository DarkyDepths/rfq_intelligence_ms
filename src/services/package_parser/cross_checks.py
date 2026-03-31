"""Cross-checks for deterministic package parser outputs."""

from __future__ import annotations

import re

from src.services.package_parser.contracts import (
    BomProfile,
    ComplianceProfile,
    DeviationProfile,
    PackageIdentity,
    PackageInventory,
    RvlProfile,
    SectionRegistry,
)
from src.services.workbook_parser.issues import CrossCheck


_MR_RE = re.compile(r"MR-(\d+)", re.IGNORECASE)


def run_cross_checks(
    identity: PackageIdentity,
    bom_profile: BomProfile | None,
    rvl_profile: RvlProfile | None,
    compliance_profile: ComplianceProfile | None,
    deviation_profile: DeviationProfile | None,
    registry: SectionRegistry,
    inventory: PackageInventory,
) -> list[CrossCheck]:
    checks = [
        _exact_check(
            code="PACKAGE_MR_vs_RVL_MR",
            left_field_path="package_identity.mr_number_short",
            right_field_path="rvl_profile.mr_number_in_rvl",
            left_value=identity.mr_number_short,
            right_value=(rvl_profile.mr_number_in_rvl if rvl_profile is not None else None),
        ),
        _exact_check(
            code="PACKAGE_MR_vs_BOM_MR",
            left_field_path="package_identity.mr_number_short",
            right_field_path="bom_profile.source_file",
            left_value=identity.mr_number_short,
            right_value=(_extract_mr_number(bom_profile.source_file) if bom_profile is not None else None),
            note=("MR extracted from BOM source filename" if bom_profile is not None else None),
        ),
        _exact_check(
            code="PACKAGE_MR_vs_COMPLIANCE_MR",
            left_field_path="package_identity.mr_number_short",
            right_field_path="compliance_profile.mr_number",
            left_value=identity.mr_number_short,
            right_value=(compliance_profile.mr_number if compliance_profile is not None else None),
        ),
        _exact_check(
            code="PACKAGE_MR_vs_DEVIATION_MR",
            left_field_path="package_identity.mr_number_short",
            right_field_path="deviation_profile.mr_number",
            left_value=identity.mr_number_short,
            right_value=(deviation_profile.mr_number if deviation_profile is not None else None),
        ),
        _set_overlap_check(
            code="BOM_9COM_vs_RVL_9COM",
            left_field_path="bom_profile.nine_com_codes_found",
            right_field_path="rvl_profile.nine_com_codes",
            left_values=(bom_profile.nine_com_codes_found if bom_profile is not None else []),
            right_values=(rvl_profile.nine_com_codes if rvl_profile is not None else []),
        ),
        _exact_set_to_scalar_check(
            code="BOM_9COM_vs_COMPLIANCE_9COM",
            left_field_path="bom_profile.nine_com_codes_found",
            right_field_path="compliance_profile.nine_com",
            left_values=(bom_profile.nine_com_codes_found if bom_profile is not None else []),
            right_value=(compliance_profile.nine_com if compliance_profile is not None else None),
        ),
        *_section_prefix_consistency_checks(registry, inventory),
        _mr_index_completeness_check(registry),
    ]
    return checks


def _exact_check(
    code: str,
    left_field_path: str,
    right_field_path: str,
    left_value: str | None,
    right_value: str | None,
    note: str | None = None,
) -> CrossCheck:
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
            note=note or "Required value missing for exact comparison.",
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
        note=note,
    )


def _set_overlap_check(
    code: str,
    left_field_path: str,
    right_field_path: str,
    left_values: list[str],
    right_values: list[str],
) -> CrossCheck:
    left_unique = _ordered_unique(left_values)
    right_unique = _ordered_unique(right_values)
    left_rendered = _render_values(left_unique)
    right_rendered = _render_values(right_unique)

    if not left_unique or not right_unique:
        return CrossCheck(
            code=code,
            status="skipped",
            left_field_path=left_field_path,
            right_field_path=right_field_path,
            left_value=left_rendered,
            right_value=right_rendered,
            tolerance_abs=None,
            tolerance_rel=None,
            delta_abs=None,
            delta_rel=None,
            note="One or both value sets are missing.",
        )

    overlap = sorted(set(left_unique) & set(right_unique))
    status = "pass" if overlap else "warn"
    note = None if overlap else "No overlap found between 9COM sets."
    if overlap:
        note = f"Overlap: {', '.join(overlap)}"

    return CrossCheck(
        code=code,
        status=status,
        left_field_path=left_field_path,
        right_field_path=right_field_path,
        left_value=left_rendered,
        right_value=right_rendered,
        tolerance_abs=None,
        tolerance_rel=None,
        delta_abs=None,
        delta_rel=None,
        note=note,
    )


def _exact_set_to_scalar_check(
    code: str,
    left_field_path: str,
    right_field_path: str,
    left_values: list[str],
    right_value: str | None,
) -> CrossCheck:
    left_unique = _ordered_unique(left_values)
    left_rendered = _render_values(left_unique)

    if not left_unique or right_value is None:
        return CrossCheck(
            code=code,
            status="skipped",
            left_field_path=left_field_path,
            right_field_path=right_field_path,
            left_value=left_rendered,
            right_value=right_value,
            tolerance_abs=None,
            tolerance_rel=None,
            delta_abs=None,
            delta_rel=None,
            note="Required value missing for exact comparison.",
        )

    status = "pass" if set(left_unique) == {right_value} else "warn"
    return CrossCheck(
        code=code,
        status=status,
        left_field_path=left_field_path,
        right_field_path=right_field_path,
        left_value=left_rendered,
        right_value=right_value,
        tolerance_abs=None,
        tolerance_rel=None,
        delta_abs=None,
        delta_rel=None,
        note=None,
    )


def _section_prefix_consistency_checks(registry: SectionRegistry, inventory: PackageInventory) -> list[CrossCheck]:
    section_number_by_path = {
        section.folder_relative_path: str(section.number_prefix).zfill(2)
        for section in registry.matched_sections
        if section.number_prefix is not None
    }

    checks: list[CrossCheck] = []
    for file_entry in inventory.files:
        if file_entry.is_system_file or file_entry.section_prefix is None:
            continue

        top_level_folder = file_entry.relative_path.split("/", 1)[0]
        expected_prefix = section_number_by_path.get(top_level_folder)
        if expected_prefix is None:
            continue

        status = "pass" if file_entry.section_prefix == expected_prefix else "warn"
        checks.append(
            CrossCheck(
                code="SECTION_PREFIX_CONSISTENCY",
                status=status,
                left_field_path=f"package_inventory.files[{file_entry.relative_path}].section_prefix",
                right_field_path=f"section_registry.sections[{top_level_folder}].number_prefix",
                left_value=file_entry.section_prefix,
                right_value=expected_prefix,
                tolerance_abs=None,
                tolerance_rel=None,
                delta_abs=None,
                delta_rel=None,
                note=file_entry.relative_path,
            )
        )

    if checks:
        return checks

    return [
        CrossCheck(
            code="SECTION_PREFIX_CONSISTENCY",
            status="skipped",
            left_field_path="package_inventory.files[].section_prefix",
            right_field_path="section_registry.matched_sections[].number_prefix",
            left_value=None,
            right_value=None,
            tolerance_abs=None,
            tolerance_rel=None,
            delta_abs=None,
            delta_rel=None,
            note="No files with section prefixes were available for comparison.",
        )
    ]


def _mr_index_completeness_check(registry: SectionRegistry) -> CrossCheck:
    left_value = registry.total_mr_index_count
    right_value = registry.numbered_section_count

    if right_value == 0:
        return CrossCheck(
            code="MR_INDEX_COMPLETENESS",
            status="skipped",
            left_field_path="section_registry.total_mr_index_count",
            right_field_path="section_registry.numbered_section_count",
            left_value=left_value,
            right_value=right_value,
            tolerance_abs=0.0,
            tolerance_rel=None,
            delta_abs=None,
            delta_rel=None,
            note="No numbered sections were available for MR Index coverage.",
        )

    delta_abs = float(abs(right_value - left_value))
    status = "pass" if left_value == right_value else "warn"
    return CrossCheck(
        code="MR_INDEX_COMPLETENESS",
        status=status,
        left_field_path="section_registry.total_mr_index_count",
        right_field_path="section_registry.numbered_section_count",
        left_value=left_value,
        right_value=right_value,
        tolerance_abs=0.0,
        tolerance_rel=None,
        delta_abs=delta_abs,
        delta_rel=None,
        note=f"{left_value}/{right_value} numbered sections contain MR Index files.",
    )


def _extract_mr_number(value: str | None) -> str | None:
    if value is None:
        return None
    match = _MR_RE.search(value)
    if match is None:
        return None
    return f"MR-{match.group(1)}"


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _render_values(values: list[str]) -> str | None:
    if not values:
        return None
    return ", ".join(values)
