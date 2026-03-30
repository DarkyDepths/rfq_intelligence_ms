from __future__ import annotations

from pathlib import Path

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


def test_section_classifier_matches_numbered_and_revision_history_sections() -> None:
    inventory = TreeScanner().scan(_fixture_package_root())
    registry = SectionClassifier().classify(inventory)

    numbered_matches = [m for m in registry.matched_sections if m.match_method == "number_prefix"]
    heuristic_matches = [m for m in registry.matched_sections if m.match_method == "name_heuristic"]

    assert len(numbered_matches) == 16
    assert all(m.match_confidence == "high" for m in numbered_matches)

    revision_history = [m for m in heuristic_matches if m.canonical_key == "revision_history"]
    assert len(revision_history) == 1
    assert revision_history[0].folder_name == "Revision History-MR Comment Log"
    assert revision_history[0].match_confidence == "medium"

    assert registry.missing_canonical_sections == []
    assert registry.numbered_section_count == 16
    assert registry.unnumbered_section_count == 1


def test_section_classifier_mr_index_coverage_and_unmatched_behavior() -> None:
    inventory = TreeScanner().scan(_fixture_package_root())
    registry = SectionClassifier().classify(inventory)

    assert registry.unmatched_folders == []

    expected_mr_index_coverage = sum(
        1
        for section in registry.matched_sections
        if section.mr_index_present
    )
    assert registry.total_mr_index_count == expected_mr_index_coverage
