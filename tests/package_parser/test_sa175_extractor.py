from __future__ import annotations

from pathlib import Path

from src.services.package_parser.contracts import FileEntry, PackageInventory, SectionMatch, SectionRegistry
from src.services.package_parser.extractors.sa175_extractor import Sa175Extractor
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


def test_sa175_extractor_returns_none_for_current_real_fixture_without_forms() -> None:
    fixture_root = _fixture_package_root()
    inventory = TreeScanner().scan(fixture_root)
    registry = SectionClassifier().classify(inventory)

    profile = Sa175Extractor().extract(inventory, registry)

    assert any(section.canonical_key == "sa175_forms" for section in registry.matched_sections)
    assert profile is None


def test_sa175_extractor_filters_noise_and_mixed_case_filenames() -> None:
    inventory = PackageInventory(
        package_root_name="synthetic",
        input_type="directory",
        total_files=5,
        total_files_raw=5,
        total_folders=1,
        total_size_bytes=0,
        files=[
            FileEntry(
                relative_path="07-SA-175 Forms/Form_175-010710.pdf",
                filename="Form_175-010710.pdf",
                extension=".pdf",
                size_bytes=1,
                depth=1,
                parent_folder="07-SA-175 Forms",
            ),
            FileEntry(
                relative_path="07-SA-175 Forms/sa_175-321900.PDF",
                filename="sa_175-321900.PDF",
                extension=".pdf",
                size_bytes=1,
                depth=1,
                parent_folder="07-SA-175 Forms",
            ),
            FileEntry(
                relative_path="07-SA-175 Forms/MR Index_07.pdf",
                filename="MR Index_07.pdf",
                extension=".pdf",
                size_bytes=1,
                depth=1,
                parent_folder="07-SA-175 Forms",
                is_mr_index=True,
            ),
            FileEntry(
                relative_path="07-SA-175 Forms/random_note.txt",
                filename="random_note.txt",
                extension=".txt",
                size_bytes=1,
                depth=1,
                parent_folder="07-SA-175 Forms",
            ),
            FileEntry(
                relative_path="07-SA-175 Forms/.DS_Store",
                filename=".DS_Store",
                extension="",
                size_bytes=1,
                depth=1,
                parent_folder="07-SA-175 Forms",
                is_system_file=True,
            ),
        ],
        folders=[],
        root_files=[],
        file_extension_counts={".pdf": 3, ".txt": 1},
        system_file_count=1,
        scanned_at="2026-03-31T00:00:00+00:00",
    )
    registry = SectionRegistry(
        matched_sections=[
            SectionMatch(
                folder_name="07-SA-175 Forms",
                folder_relative_path="07-SA-175 Forms",
                canonical_key="sa175_forms",
                match_method="number_prefix",
                match_confidence="high",
                number_prefix=7,
                file_count=4,
                mr_index_present=True,
                has_subfolders=False,
            )
        ],
        unmatched_folders=[],
        missing_canonical_sections=[],
        numbered_section_count=1,
        unnumbered_section_count=0,
        total_mr_index_count=1,
    )

    profile = Sa175Extractor().extract(inventory, registry)

    assert profile is not None
    assert profile.total_count == 2
    assert profile.form_numbers == ["175-010710", "175-321900"]
    assert [entry.form_number for entry in profile.forms] == ["175-010710", "175-321900"]
    assert all(entry.filename != "MR Index_07.pdf" for entry in profile.forms)
