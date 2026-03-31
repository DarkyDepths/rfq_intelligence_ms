"""Envelope assembler for deterministic package parser."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

from src.services.package_parser.contracts import (
    BomProfile,
    ComplianceProfile,
    DeviationProfile,
    PackageIdentity,
    PackageInventory,
    PackageParseEnvelope,
    RvlProfile,
    Sa175Profile,
    SectionRegistry,
    StandardsProfile,
)
from src.services.package_parser.issues import PackageParserReport, ParserIssue, StageReport
from src.services.workbook_parser.issues import CrossCheck

PARSER_VERSION = "package-parser-v1.0"


def build_envelope(
    rfq_id: str,
    inventory: PackageInventory,
    identity: PackageIdentity,
    registry: SectionRegistry,
    standards_profile: StandardsProfile | None,
    bom_profile: BomProfile | None,
    rvl_profile: RvlProfile | None,
    sa175_profile: Sa175Profile | None,
    compliance_profile: ComplianceProfile | None,
    deviation_profile: DeviationProfile | None,
    cross_checks: list[CrossCheck],
    warnings: list[ParserIssue] | None = None,
    errors: list[ParserIssue] | None = None,
) -> dict:
    warning_list = sorted(warnings or [], key=_issue_sort_key)
    error_list = sorted(errors or [], key=_issue_sort_key)

    stages = _build_stage_reports(
        inventory=inventory,
        warnings=warning_list,
        errors=error_list,
        standards_profile=standards_profile,
        bom_profile=bom_profile,
        rvl_profile=rvl_profile,
        sa175_profile=sa175_profile,
        compliance_profile=compliance_profile,
        deviation_profile=deviation_profile,
    )

    status = _compute_status(stages=stages, warnings=warning_list, errors=error_list, cross_checks=cross_checks)

    parser_report = PackageParserReport(
        status=status,
        parser_version=PARSER_VERSION,
        stages=stages,
        warnings=warning_list,
        errors=error_list,
        cross_checks=sorted(cross_checks, key=_cross_check_sort_key),
    )

    envelope = PackageParseEnvelope(
        rfq_id=rfq_id,
        parser_version=PARSER_VERSION,
        parsed_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        input_type=inventory.input_type,
        input_path=None,
        package_inventory=inventory,
        package_identity=identity,
        section_registry=registry,
        standards_profile=standards_profile,
        bom_profile=bom_profile,
        rvl_profile=rvl_profile,
        sa175_profile=sa175_profile,
        compliance_profile=compliance_profile,
        deviation_profile=deviation_profile,
        parser_report=parser_report,
    )
    return asdict(envelope)


def _build_stage_reports(
    inventory: PackageInventory,
    warnings: list[ParserIssue],
    errors: list[ParserIssue],
    standards_profile: StandardsProfile | None,
    bom_profile: BomProfile | None,
    rvl_profile: RvlProfile | None,
    sa175_profile: Sa175Profile | None,
    compliance_profile: ComplianceProfile | None,
    deviation_profile: DeviationProfile | None,
) -> list[StageReport]:
    scan_warnings = _count_issues(warnings, "scan")
    scan_errors = _count_issues(errors, "scan")
    recognition_warnings = _count_issues(warnings, "recognition")
    recognition_errors = _count_issues(errors, "recognition")
    extraction_warnings = _count_issues(warnings, "extraction")
    extraction_errors = _count_issues(errors, "extraction")
    assembly_warnings = _count_issues(warnings, "assembly")
    assembly_errors = _count_issues(errors, "assembly")

    extraction_outputs = [
        standards_profile,
        bom_profile,
        rvl_profile,
        sa175_profile,
        compliance_profile,
        deviation_profile,
    ]
    extraction_processed = len(extraction_outputs)
    extraction_failed = extraction_errors
    extraction_succeeded = extraction_processed - extraction_failed

    return [
        StageReport(
            stage="scan",
            status=_stage_status(scan_warnings, scan_errors),
            items_processed=inventory.total_files_raw + inventory.total_folders,
            items_succeeded=inventory.total_files_raw + inventory.total_folders - scan_errors,
            items_failed=scan_errors,
            warning_count=scan_warnings,
            error_count=scan_errors,
        ),
        StageReport(
            stage="recognition",
            status=_stage_status(recognition_warnings, recognition_errors),
            items_processed=2,
            items_succeeded=2 - recognition_errors,
            items_failed=recognition_errors,
            warning_count=recognition_warnings,
            error_count=recognition_errors,
        ),
        StageReport(
            stage="extraction",
            status=_stage_status(extraction_warnings, extraction_errors),
            items_processed=extraction_processed,
            items_succeeded=extraction_succeeded,
            items_failed=extraction_failed,
            warning_count=extraction_warnings,
            error_count=extraction_errors,
        ),
        StageReport(
            stage="assembly",
            status=_stage_status(assembly_warnings, assembly_errors),
            items_processed=1,
            items_succeeded=1 - assembly_errors,
            items_failed=assembly_errors,
            warning_count=assembly_warnings,
            error_count=assembly_errors,
        ),
    ]


def _compute_status(
    stages: list[StageReport],
    warnings: list[ParserIssue],
    errors: list[ParserIssue],
    cross_checks: list[CrossCheck],
) -> str:
    if any(stage.status == "failed" for stage in stages):
        return "failed"
    if errors or warnings or any(check.status in {"warn", "fail"} for check in cross_checks):
        return "parsed_with_warnings"
    return "parsed_ok"


def _stage_status(warning_count: int, error_count: int) -> str:
    if error_count > 0:
        return "failed"
    if warning_count > 0:
        return "parsed_with_warnings"
    return "parsed_ok"


def _count_issues(issues: list[ParserIssue], stage_name: str) -> int:
    return sum(1 for issue in issues if issue.field_path == f"stage.{stage_name}")


def _issue_sort_key(issue: ParserIssue) -> tuple[str, int, str, str]:
    return (
        issue.code,
        issue.row_number or -1,
        issue.sheet_name or "",
        issue.message,
    )


def _cross_check_sort_key(check: CrossCheck) -> tuple[str, str, str, str]:
    return (
        check.code,
        check.note or "",
        str(check.left_value or ""),
        str(check.right_value or ""),
    )
