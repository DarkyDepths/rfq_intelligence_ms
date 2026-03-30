"""Issue and report support types for package parser v1.0."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.services.workbook_parser.issues import AnchorCheck, CrossCheck, ParserIssue

PackageParserStatus = Literal["parsed_ok", "parsed_with_warnings", "failed"]
StageName = Literal["scan", "recognition", "extraction", "assembly"]

CROSS_CHECK_CODES: tuple[str, ...] = (
    "PACKAGE_MR_vs_RVL_MR",
    "PACKAGE_MR_vs_BOM_MR",
    "PACKAGE_MR_vs_COMPLIANCE_MR",
    "PACKAGE_MR_vs_DEVIATION_MR",
    "BOM_TAG_vs_WORKBOOK_TAG",
    "BOM_9COM_vs_RVL_9COM",
    "BOM_9COM_vs_COMPLIANCE_9COM",
    "SECTION_PREFIX_CONSISTENCY",
    "MR_INDEX_COMPLETENESS",
)


@dataclass(frozen=True)
class StageReport:
    """Report for a single pipeline stage."""

    stage: StageName
    status: PackageParserStatus
    duration_ms: float | None = None
    items_processed: int = 0
    items_succeeded: int = 0
    items_failed: int = 0
    warning_count: int = 0
    error_count: int = 0


@dataclass(frozen=True)
class PackageParserReport:
    """Overall parser report across all stages."""

    status: PackageParserStatus
    parser_version: str
    stages: list[StageReport]
    warnings: list[ParserIssue]
    errors: list[ParserIssue]
    cross_checks: list[CrossCheck]


__all__ = [
    "AnchorCheck",
    "CROSS_CHECK_CODES",
    "CrossCheck",
    "PackageParserReport",
    "PackageParserStatus",
    "ParserIssue",
    "StageName",
    "StageReport",
]
