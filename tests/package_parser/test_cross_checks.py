from __future__ import annotations

from pathlib import Path

from src.services.package_parser.cross_checks import run_cross_checks
from src.services.package_parser.extractors.bom_extractor import BomExtractor
from src.services.package_parser.extractors.compliance_extractor import ComplianceExtractor
from src.services.package_parser.extractors.identity_extractor import IdentityExtractor
from src.services.package_parser.extractors.rvl_extractor import RvlExtractor
from src.services.package_parser.extractors.section_classifier import SectionClassifier
from src.services.package_parser.scanners.tree_scanner import TreeScanner


_PACKAGE_ROOT_NAME = "SA-AYPP-6-MR-022_COLLECTION VESSEL - CDS-REV-00"


def _fixture_package_root() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    fixture_root = (
        repo_root
        / "local_fixtures"
        / "rfq_created"
        / "source_package_sample_001"
        / _PACKAGE_ROOT_NAME
    )
    if not fixture_root.exists():
        raise FileNotFoundError(f"Fixture package root not found: {fixture_root}")
    return fixture_root


def test_cross_checks_evaluate_real_fixture_mr_and_9com_consistency() -> None:
    fixture_root = _fixture_package_root()
    inventory = TreeScanner().scan(fixture_root)
    identity = IdentityExtractor().extract(inventory)
    registry = SectionClassifier().classify(inventory)
    bom_profile = BomExtractor().extract(inventory, registry, fixture_root)
    rvl_profile = RvlExtractor().extract(inventory, registry, fixture_root)
    compliance_profile, deviation_profile = ComplianceExtractor().extract(inventory, registry, fixture_root)

    checks = run_cross_checks(
        identity=identity,
        bom_profile=bom_profile,
        rvl_profile=rvl_profile,
        compliance_profile=compliance_profile,
        deviation_profile=deviation_profile,
        registry=registry,
        inventory=inventory,
    )

    assert checks

    mr_rvl_check = next(check for check in checks if check.code == "PACKAGE_MR_vs_RVL_MR")
    bom_rvl_check = next(check for check in checks if check.code == "BOM_9COM_vs_RVL_9COM")
    mr_index_check = next(check for check in checks if check.code == "MR_INDEX_COMPLETENESS")
    prefix_checks = [check for check in checks if check.code == "SECTION_PREFIX_CONSISTENCY"]

    assert mr_rvl_check.status == "warn"
    assert mr_rvl_check.left_value == "MR-022"
    assert mr_rvl_check.right_value == "MR-023"

    assert bom_rvl_check.status == "pass"
    assert "6000002521" in (bom_rvl_check.left_value or "")
    assert "6000002521" in (bom_rvl_check.note or "")

    assert mr_index_check.status in {"pass", "warn"}
    assert mr_index_check.left_value == 6
    assert mr_index_check.right_value == 16

    assert prefix_checks
    assert any(check.status == "pass" for check in prefix_checks)


def test_cross_checks_skip_missing_side_and_warn_on_prefix_mismatch() -> None:
    fixture_root = _fixture_package_root()
    inventory = TreeScanner().scan(fixture_root)
    identity = IdentityExtractor().extract(inventory)
    registry = SectionClassifier().classify(inventory)

    mutated_files = []
    for file_entry in inventory.files:
        if file_entry.relative_path == "02-MR Description-BOM/02_BOM_SA-AYPP-6-MR-022_COLLECTION VESSEL- CDS.xlsx":
            mutated_files.append(file_entry.__class__(**{**file_entry.__dict__, "section_prefix": "03"}))
        else:
            mutated_files.append(file_entry)

    mutated_inventory = inventory.__class__(**{**inventory.__dict__, "files": mutated_files})
    checks = run_cross_checks(
        identity=identity,
        bom_profile=None,
        rvl_profile=None,
        compliance_profile=None,
        deviation_profile=None,
        registry=registry,
        inventory=mutated_inventory,
    )

    bom_rvl_check = next(check for check in checks if check.code == "BOM_9COM_vs_RVL_9COM")
    mismatch_check = next(
        check
        for check in checks
        if check.code == "SECTION_PREFIX_CONSISTENCY"
        and check.note == "02-MR Description-BOM/02_BOM_SA-AYPP-6-MR-022_COLLECTION VESSEL- CDS.xlsx"
    )

    assert bom_rvl_check.status == "skipped"
    assert mismatch_check.status == "warn"
    assert mismatch_check.left_value == "03"
    assert mismatch_check.right_value == "02"
