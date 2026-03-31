from __future__ import annotations

import os
import zipfile
from pathlib import Path

import pytest

from src.services.package_parser.parser_orchestrator import PackageParserOrchestrator
from src.services.package_parser.scanners.tree_scanner import TreeScanner
from src.services.package_parser.scanners.zip_scanner import ZipScanner


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


def _create_package_zip(source_root: Path, zip_path: Path, wrapper_name: str | None = None) -> Path:
    package_prefix = Path(source_root.name)
    if wrapper_name is not None:
        package_prefix = Path(wrapper_name) / package_prefix

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        if wrapper_name is not None:
            archive.writestr(f"{wrapper_name}/", "")
        archive.writestr(f"{package_prefix.as_posix()}/", "")

        for current_dir, dirnames, filenames in os.walk(source_root):
            dirnames.sort(key=lambda name: name.lower())
            filenames.sort(key=lambda name: name.lower())

            current_path = Path(current_dir)
            rel_dir = current_path.relative_to(source_root)
            if rel_dir.parts:
                archive.writestr(f"{(package_prefix / rel_dir).as_posix()}/", "")

            for filename in filenames:
                file_path = current_path / filename
                archive.write(file_path, (package_prefix / rel_dir / filename).as_posix())

    return zip_path


def _root_file_projection(inventory) -> list[tuple[str, str, str | None, bool]]:
    return [
        (entry.relative_path, entry.filename, entry.root_role, entry.is_mr_index)
        for entry in inventory.root_files
    ]


def test_zip_scanner_matches_directory_inventory_for_real_fixture(tmp_path: Path) -> None:
    fixture_root = _fixture_package_root()
    zip_path = _create_package_zip(
        source_root=fixture_root,
        zip_path=tmp_path / "fixture_package_wrapped.zip",
        wrapper_name="wrapped-export",
    )

    directory_inventory = TreeScanner().scan(fixture_root)
    zip_inventory = ZipScanner().scan(zip_path)

    assert zip_inventory.input_type == "zip"
    assert zip_inventory.package_root_name == directory_inventory.package_root_name
    assert zip_inventory.total_files == directory_inventory.total_files
    assert zip_inventory.total_files_raw == directory_inventory.total_files_raw
    assert zip_inventory.system_file_count == directory_inventory.system_file_count
    assert zip_inventory.total_folders == directory_inventory.total_folders
    assert zip_inventory.file_extension_counts == directory_inventory.file_extension_counts
    assert _root_file_projection(zip_inventory) == _root_file_projection(directory_inventory)


def test_zip_parser_orchestrator_matches_directory_logical_output(tmp_path: Path) -> None:
    fixture_root = _fixture_package_root()
    zip_path = _create_package_zip(
        source_root=fixture_root,
        zip_path=tmp_path / "fixture_package.zip",
    )

    orchestrator = PackageParserOrchestrator()
    directory_envelope = orchestrator.parse(fixture_root, rfq_id="rfq-zip-test")
    zip_envelope = orchestrator.parse(zip_path, rfq_id="rfq-zip-test")

    assert directory_envelope["package_identity"] == zip_envelope["package_identity"]

    directory_registry = directory_envelope["section_registry"]
    zip_registry = zip_envelope["section_registry"]
    assert zip_registry["numbered_section_count"] == directory_registry["numbered_section_count"]
    assert zip_registry["unnumbered_section_count"] == directory_registry["unnumbered_section_count"]
    assert zip_registry["total_mr_index_count"] == directory_registry["total_mr_index_count"]
    assert zip_registry["missing_canonical_sections"] == directory_registry["missing_canonical_sections"]

    assert directory_envelope["standards_profile"] is not None
    assert zip_envelope["standards_profile"] is not None
    assert directory_envelope["bom_profile"] is not None
    assert zip_envelope["bom_profile"] is not None
    assert directory_envelope["rvl_profile"] is not None
    assert zip_envelope["rvl_profile"] is not None
    assert (directory_envelope["sa175_profile"] is None) == (zip_envelope["sa175_profile"] is None)
    assert (directory_envelope["compliance_profile"] is None) == (zip_envelope["compliance_profile"] is None)
    assert (directory_envelope["deviation_profile"] is None) == (zip_envelope["deviation_profile"] is None)

    assert zip_envelope["standards_profile"]["total_count"] == directory_envelope["standards_profile"]["total_count"]
    assert zip_envelope["bom_profile"]["total_line_items"] == directory_envelope["bom_profile"]["total_line_items"]
    assert zip_envelope["rvl_profile"]["total_vendors"] == directory_envelope["rvl_profile"]["total_vendors"]

    directory_check_codes = {check["code"] for check in directory_envelope["parser_report"]["cross_checks"]}
    zip_check_codes = {check["code"] for check in zip_envelope["parser_report"]["cross_checks"]}
    assert zip_check_codes == directory_check_codes


def test_zip_scanner_raises_for_invalid_zip(tmp_path: Path) -> None:
    corrupt_zip = tmp_path / "corrupt_package.zip"
    corrupt_zip.write_bytes(b"not a zip archive")

    with pytest.raises(ValueError, match="Invalid ZIP archive"):
        ZipScanner().scan(corrupt_zip)
