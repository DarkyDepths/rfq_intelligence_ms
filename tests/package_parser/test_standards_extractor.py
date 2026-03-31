from __future__ import annotations

import re
from pathlib import Path

from src.services.package_parser.contracts import SectionRegistry
from src.services.package_parser.extractors.section_classifier import SectionClassifier
from src.services.package_parser.extractors.standards_extractor import StandardsExtractor
from src.services.package_parser.scanners.tree_scanner import TreeScanner


_PACKAGE_ROOT_NAME = "SA-AYPP-6-MR-022_COLLECTION VESSEL - CDS-REV-00"
_SAMSS_RE = re.compile(r"SAMSS[-_]?(\d{3})", re.IGNORECASE)
_SAES_RE = re.compile(r"SAES[-_]?([A-Z][-_]\d{3})", re.IGNORECASE)
_SAEP_RE = re.compile(r"SAEP[-_]?(\d+)", re.IGNORECASE)
_STD_DWG_RE = re.compile(r"STD[\s._-]*DWG(?:[-_\s]*([A-Z0-9][A-Z0-9._-]*))?", re.IGNORECASE)


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

    expected_counts = _expected_counts_from_fixture(inventory, applicable_section.folder_relative_path)
    assert profile.total_count == expected_counts["total"]
    assert profile.samss_count == expected_counts["samss"]
    assert profile.saes_count == expected_counts["saes"]
    assert profile.saep_count == expected_counts["saep"]
    assert profile.std_dwg_count == expected_counts["std_dwg"]
    assert len(profile.other) == expected_counts["other"]

    assert profile.total_count == 37
    assert profile.samss_count == 9
    assert profile.saes_count == 19
    assert profile.saep_count == 9
    assert profile.std_dwg_count == 0
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


def _expected_counts_from_fixture(inventory, section_relative_path: str) -> dict[str, int]:
    counts = {"samss": 0, "saes": 0, "saep": 0, "std_dwg": 0, "other": 0, "total": 0}
    section_prefix = f"{section_relative_path}/"

    for file_entry in inventory.files:
        if file_entry.is_system_file or not file_entry.relative_path.startswith(section_prefix):
            continue

        counts["total"] += 1
        if _SAMSS_RE.search(file_entry.filename) is not None:
            counts["samss"] += 1
        elif _SAES_RE.search(file_entry.filename) is not None:
            counts["saes"] += 1
        elif _SAEP_RE.search(file_entry.filename) is not None:
            counts["saep"] += 1
        elif _STD_DWG_RE.search(file_entry.filename) is not None:
            counts["std_dwg"] += 1
        else:
            counts["other"] += 1

    return counts
