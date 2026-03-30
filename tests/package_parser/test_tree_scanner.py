from __future__ import annotations

from pathlib import Path

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


def test_tree_scanner_builds_expected_inventory_for_golden_fixture() -> None:
    scanner = TreeScanner()
    inventory = scanner.scan(_fixture_package_root())

    assert inventory.package_root_name == _PACKAGE_ROOT_NAME
    assert inventory.input_type == "directory"
    assert inventory.total_files == 55
    assert inventory.total_files_raw == 56
    assert inventory.system_file_count == 1
    assert len(inventory.root_files) == 2

    root_roles = {entry.root_role for entry in inventory.root_files}
    assert "mr_index_root" in root_roles
    assert "internal_review_file" in root_roles

    ds_store_entries = [entry for entry in inventory.files if entry.filename == ".DS_Store"]
    assert len(ds_store_entries) == 1
    assert ds_store_entries[0].is_system_file is True

    assert all(not entry.is_system_file for entry in inventory.root_files)


def test_tree_scanner_detects_folder_numbering_and_special_unnumbered_folder() -> None:
    scanner = TreeScanner()
    inventory = scanner.scan(_fixture_package_root())

    by_name = {folder.name: folder for folder in inventory.folders}

    assert by_name["00-Approval Sheet"].number_prefix == 0
    assert by_name["06-Applicable Standards"].number_prefix == 6
    assert by_name["15-Notes to Vendor"].number_prefix == 15

    assert by_name["Revision History-MR Comment Log"].number_prefix is None
