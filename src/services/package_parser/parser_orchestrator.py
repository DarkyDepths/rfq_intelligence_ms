"""Deterministic package parser orchestrator."""

from __future__ import annotations

import logging
from pathlib import Path

from src.services.package_parser.assembler import build_envelope
from src.services.package_parser.cross_checks import run_cross_checks
from src.services.package_parser.extractors.bom_extractor import BomExtractor
from src.services.package_parser.extractors.compliance_extractor import ComplianceExtractor
from src.services.package_parser.extractors.identity_extractor import IdentityExtractor
from src.services.package_parser.extractors.rvl_extractor import RvlExtractor
from src.services.package_parser.extractors.sa175_extractor import Sa175Extractor
from src.services.package_parser.extractors.section_classifier import SectionClassifier
from src.services.package_parser.extractors.standards_extractor import StandardsExtractor
from src.services.package_parser.issues import ParserIssue
from src.services.package_parser.scanners.tree_scanner import TreeScanner
from src.services.package_parser.scanners.zip_scanner import ZipScanner


class PackageParserOrchestrator:
    """Run the 4-stage deterministic package parsing pipeline."""

    def __init__(self) -> None:
        self._scanner = TreeScanner()
        self._zip_scanner = ZipScanner()
        self._identity_extractor = IdentityExtractor()
        self._section_classifier = SectionClassifier()
        self._standards_extractor = StandardsExtractor()
        self._bom_extractor = BomExtractor()
        self._rvl_extractor = RvlExtractor()
        self._sa175_extractor = Sa175Extractor()
        self._compliance_extractor = ComplianceExtractor()

    def parse(self, package_root_path: str | Path, rfq_id: str) -> dict:
        package_root = Path(package_root_path)
        if package_root.suffix.lower() == ".zip":
            with self._zip_scanner.open_package(package_root) as (resolved_root, inventory):
                return self._parse_inventory(resolved_root, inventory, rfq_id)
        if package_root.is_dir():
            inventory = self._scanner.scan(package_root)
            return self._parse_inventory(package_root, inventory, rfq_id)
        raise ValueError(f"Unsupported input: {package_root_path}")

    def _parse_inventory(self, package_root: Path, inventory, rfq_id: str) -> dict:
        identity = self._identity_extractor.extract(inventory)
        registry = self._section_classifier.classify(inventory)

        warnings: list[ParserIssue] = []
        errors: list[ParserIssue] = []

        standards_profile = self._try_extract(
            stage_errors=errors,
            code="STANDARDS_EXTRACTION_FAILED",
            field_path="stage.extraction",
            func=lambda: self._standards_extractor.extract(inventory, registry),
        )
        bom_profile = self._try_extract(
            stage_errors=errors,
            code="BOM_EXTRACTION_FAILED",
            field_path="stage.extraction",
            func=lambda: self._bom_extractor.extract(inventory, registry, package_root),
        )
        rvl_profile = self._try_extract(
            stage_errors=errors,
            code="RVL_EXTRACTION_FAILED",
            field_path="stage.extraction",
            func=lambda: self._rvl_extractor.extract(inventory, registry, package_root),
        )
        sa175_profile = self._try_extract(
            stage_errors=errors,
            code="SA175_EXTRACTION_FAILED",
            field_path="stage.extraction",
            func=lambda: self._sa175_extractor.extract(inventory, registry),
        )
        compliance_profile, deviation_profile = self._try_extract_compliance(
            inventory=inventory,
            registry=registry,
            package_root=package_root,
            stage_errors=errors,
        )

        cross_checks = run_cross_checks(
            identity=identity,
            bom_profile=bom_profile,
            rvl_profile=rvl_profile,
            compliance_profile=compliance_profile,
            deviation_profile=deviation_profile,
            registry=registry,
            inventory=inventory,
        )

        return build_envelope(
            rfq_id=rfq_id,
            inventory=inventory,
            identity=identity,
            registry=registry,
            standards_profile=standards_profile,
            bom_profile=bom_profile,
            rvl_profile=rvl_profile,
            sa175_profile=sa175_profile,
            compliance_profile=compliance_profile,
            deviation_profile=deviation_profile,
            cross_checks=cross_checks,
            warnings=warnings,
            errors=errors,
        )

    def _try_extract(self, stage_errors: list[ParserIssue], code: str, field_path: str, func):
        try:
            return func()
        except Exception as exc:
            logging.getLogger(__name__).exception("Package parser extraction failed for %s", code)
            stage_errors.append(
                ParserIssue(
                    code=code,
                    severity="error",
                    sheet_name=None,
                    cell_ref=None,
                    row_number=None,
                    field_path=field_path,
                    message=f"Extractor crashed: {exc}",
                    expected_value=None,
                    actual_value=None,
                    raw_value=None,
                )
            )
            return None

    def _try_extract_compliance(
        self,
        inventory,
        registry,
        package_root: Path,
        stage_errors: list[ParserIssue],
    ) -> tuple[object | None, object | None]:
        try:
            return self._compliance_extractor.extract(inventory, registry, package_root)
        except Exception as exc:
            logging.getLogger(__name__).exception("Package parser extraction failed for compliance/deviation")
            stage_errors.append(
                ParserIssue(
                    code="COMPLIANCE_EXTRACTION_FAILED",
                    severity="error",
                    sheet_name=None,
                    cell_ref=None,
                    row_number=None,
                    field_path="stage.extraction",
                    message=f"Extractor crashed: {exc}",
                    expected_value=None,
                    actual_value=None,
                    raw_value=None,
                )
            )
            return None, None
