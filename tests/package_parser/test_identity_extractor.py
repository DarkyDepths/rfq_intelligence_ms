from __future__ import annotations

from pathlib import Path

from src.services.package_parser.extractors.identity_extractor import IdentityExtractor
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


def test_identity_extractor_parses_package_root_and_mismatch_mr_codes() -> None:
    inventory = TreeScanner().scan(_fixture_package_root())
    identity = IdentityExtractor().extract(inventory)

    assert identity.mr_number == "SA-AYPP-6-MR-022"
    assert identity.mr_number_short == "MR-022"
    assert identity.revision == "00"
    assert identity.material_description == "COLLECTION VESSEL - CDS"
    assert identity.project_code == "SA-AYPP-6"
    assert identity.package_root_name == _PACKAGE_ROOT_NAME

    assert "MR-022" in identity.mr_numbers_in_filenames
    assert "MR-023" in identity.mr_numbers_in_filenames
    assert identity.mr_number_mismatches == ["MR-023"]
