from __future__ import annotations

from pathlib import Path

from src.services.package_parser.contracts import (
    FileEntry,
    FolderEntry,
    PackageInventory,
    SectionMatch,
    SectionRegistry,
)
from src.services.package_parser.extractors.section_classifier import SectionClassifier
from src.services.package_parser.extractors.standards_extractor import StandardsExtractor
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


def test_standards_extractor_parses_fixture_applicable_standards_section() -> None:
    inventory = TreeScanner().scan(_fixture_package_root())
    registry = SectionClassifier().classify(inventory)

    applicable_section = next(
        section
        for section in registry.matched_sections
        if section.canonical_key == "applicable_standards"
    )
    assert applicable_section.folder_name == "06-Applicable Standards"

    profile = StandardsExtractor().extract(inventory, registry)

    assert profile is not None
    assert profile.subfolder_structure == ["1. SAMSS", "2. SAES", "3. SAEP", "4. STD DWG"]
    assert profile.total_count == 37
    assert profile.samss_count == 9
    assert profile.saes_count == 19
    assert profile.saep_count == 9
    assert len(profile.other) == 0

    samss_by_filename = {reference.filename: reference for reference in profile.samss}
    saes_by_filename = {reference.filename: reference for reference in profile.saes}
    saep_by_filename = {reference.filename: reference for reference in profile.saep}

    assert samss_by_filename["01-SAMSS-043.PDF"].standard_id == "SAMSS-043"
    assert samss_by_filename["01-SAMSS-043.PDF"].relative_path.endswith("1. SAMSS/01-SAMSS-043.PDF")
    assert saes_by_filename["SAES-A-004.pdf"].standard_id == "SAES-A-004"
    assert saep_by_filename["SAEP-1142.pdf"].standard_id == "SAEP-1142"

    all_references = [
        *profile.samss,
        *profile.saes,
        *profile.saep,
        *profile.std_dwg,
        *profile.other,
    ]
    assert all(reference.extraction_method == "filename_regex" for reference in all_references)
    assert all(not reference.filename.lower().startswith("mr index") for reference in all_references)


def test_standards_extractor_excludes_mr_index_and_uses_std_dwg_subfolder_fallback() -> None:
    inventory = PackageInventory(
        package_root_name="sample-package",
        input_type="directory",
        total_files=2,
        total_files_raw=2,
        total_folders=2,
        total_size_bytes=2,
        files=[
            FileEntry(
                relative_path="06-Applicable Standards/MR Index 06.pdf",
                filename="MR Index 06.pdf",
                extension=".pdf",
                size_bytes=1,
                depth=1,
                parent_folder="06-Applicable Standards",
                is_mr_index=True,
                mr_number_in_filename=None,
                section_prefix=None,
                is_system_file=False,
                root_role=None,
            ),
            FileEntry(
                relative_path="06-Applicable Standards/4. STD DWG/VESSEL-GA-001.pdf",
                filename="VESSEL-GA-001.pdf",
                extension=".pdf",
                size_bytes=1,
                depth=2,
                parent_folder="4. STD DWG",
                is_mr_index=False,
                mr_number_in_filename=None,
                section_prefix=None,
                is_system_file=False,
                root_role=None,
            ),
        ],
        folders=[
            FolderEntry(
                relative_path="06-Applicable Standards",
                name="06-Applicable Standards",
                depth=0,
                file_count=1,
                subfolder_count=1,
                number_prefix=6,
                label="Applicable Standards",
            ),
            FolderEntry(
                relative_path="06-Applicable Standards/4. STD DWG",
                name="4. STD DWG",
                depth=1,
                file_count=1,
                subfolder_count=0,
                number_prefix=None,
                label=None,
            ),
        ],
        root_files=[],
        file_extension_counts={".pdf": 2},
        system_file_count=0,
        scanned_at="2026-03-31T00:00:00+00:00",
    )
    registry = SectionRegistry(
        matched_sections=[
            SectionMatch(
                folder_name="06-Applicable Standards",
                folder_relative_path="06-Applicable Standards",
                canonical_key="applicable_standards",
                match_method="number_prefix",
                match_confidence="high",
                number_prefix=6,
                file_count=1,
                mr_index_present=True,
                has_subfolders=True,
            )
        ],
        unmatched_folders=[],
        missing_canonical_sections=[],
        numbered_section_count=1,
        unnumbered_section_count=0,
        total_mr_index_count=1,
    )

    profile = StandardsExtractor().extract(inventory, registry)

    assert profile is not None
    assert profile.total_count == 1
    assert profile.std_dwg_count == 1
    assert profile.subfolder_structure == ["4. STD DWG"]
    assert [reference.filename for reference in profile.std_dwg] == ["VESSEL-GA-001.pdf"]
    assert profile.std_dwg[0].standard_id == "VESSEL-GA-001"
    assert all(reference.filename != "MR Index 06.pdf" for reference in profile.std_dwg)
    assert all(reference.filename != "MR Index 06.pdf" for reference in profile.other)
    assert all(reference.extraction_method == "filename_regex" for reference in profile.std_dwg)


def test_standards_extractor_returns_none_when_section_is_absent() -> None:
    inventory = TreeScanner().scan(_fixture_package_root())
    registry = SectionClassifier().classify(inventory)
    registry_without_standards = SectionRegistry(
        matched_sections=[
            section
            for section in registry.matched_sections
            if section.canonical_key != "applicable_standards"
        ],
        unmatched_folders=registry.unmatched_folders,
        missing_canonical_sections=registry.missing_canonical_sections,
        numbered_section_count=registry.numbered_section_count,
        unnumbered_section_count=registry.unnumbered_section_count,
        total_mr_index_count=registry.total_mr_index_count,
    )

    assert StandardsExtractor().extract(inventory, registry_without_standards) is None
