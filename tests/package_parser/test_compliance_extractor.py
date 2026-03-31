from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

from src.services.package_parser.extractors.compliance_extractor import ComplianceExtractor
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


def test_compliance_extractor_returns_none_for_current_real_fixture_without_workbooks() -> None:
    fixture_root = _fixture_package_root()
    inventory = TreeScanner().scan(fixture_root)
    registry = SectionClassifier().classify(inventory)

    compliance_profile, deviation_profile = ComplianceExtractor().extract(inventory, registry, fixture_root)

    assert any(section.canonical_key == "notes_to_vendor" for section in registry.matched_sections)
    assert compliance_profile is None
    assert deviation_profile is None


def test_compliance_extractor_parses_synthetic_workbooks_without_sample_hardcoding(tmp_path: Path) -> None:
    package_root = tmp_path / "SYNTH-3-MR-009_VENDOR NOTES-REV-00"
    notes_section = package_root / "15-Notes to Vendor"
    notes_section.mkdir(parents=True)

    compliance_path = notes_section / "15_vendor_COMPLIANCE_sheet_v2.xlsx"
    compliance_workbook = Workbook()
    compliance_sheet = compliance_workbook.active
    compliance_sheet.title = "requirements"
    compliance_sheet["A2"] = "Material Description"
    compliance_sheet["B2"] = "SYNTH MATERIAL"
    compliance_sheet["A3"] = "MR Number"
    compliance_sheet["B3"] = "MR-009"
    compliance_sheet["A4"] = "9COM"
    compliance_sheet["B4"] = "7000000007"
    compliance_sheet["B6"] = "1.0"
    compliance_sheet["D6"] = "GENERAL"
    compliance_sheet["B7"] = "1.1"
    compliance_sheet["D7"] = "Provide nameplate"
    compliance_sheet["G7"] = "Nameplate required"
    compliance_sheet["B8"] = "2.0"
    compliance_sheet["D8"] = "STANDARDS AND CODES"
    compliance_sheet["B9"] = "2.1"
    compliance_sheet["D9"] = "Follow code"
    compliance_sheet["G9"] = "Comply with ASME"
    compliance_workbook.save(compliance_path)
    compliance_workbook.close()

    deviation_path = notes_section / "15_Project_Deviation_LIST_v2.xlsx"
    deviation_workbook = Workbook()
    deviation_sheet = deviation_workbook.active
    deviation_sheet.title = "deviation"
    deviation_sheet["A2"] = "BI Number"
    deviation_sheet["B2"] = "BI-123"
    deviation_sheet["A3"] = "Project Title"
    deviation_sheet["B3"] = "SYNTH PROJECT"
    deviation_sheet["A4"] = "MR Number"
    deviation_sheet["B4"] = "MR-009"
    deviation_sheet["A5"] = "Material Title"
    deviation_sheet["B5"] = "SYNTH MATERIAL"
    deviation_sheet["A11"] = "Vendor"
    deviation_sheet["B11"] = "Description"
    deviation_sheet["A12"] = "Vendor A"
    deviation_sheet["B12"] = "Deviation item"
    deviation_workbook.save(deviation_path)
    deviation_workbook.close()

    (notes_section / "MR Index_15.pdf").write_text("ignore", encoding="utf-8")
    (notes_section / "notes.txt").write_text("ignore", encoding="utf-8")

    inventory = TreeScanner().scan(package_root)
    registry = SectionClassifier().classify(inventory)

    compliance_profile, deviation_profile = ComplianceExtractor().extract(inventory, registry, package_root)

    assert compliance_profile is not None
    assert compliance_profile.source_file == "15-Notes to Vendor/15_vendor_COMPLIANCE_sheet_v2.xlsx"
    assert compliance_profile.material_description == "SYNTH MATERIAL"
    assert compliance_profile.mr_number == "MR-009"
    assert compliance_profile.nine_com == "7000000007"
    assert compliance_profile.total_items == 2
    assert compliance_profile.section_labels == ["GENERAL", "STANDARDS AND CODES"]
    assert [item.item_no for item in compliance_profile.line_items] == ["1.1", "2.1"]

    assert deviation_profile is not None
    assert deviation_profile.source_file == "15-Notes to Vendor/15_Project_Deviation_LIST_v2.xlsx"
    assert deviation_profile.bi_number == "BI-123"
    assert deviation_profile.project_title == "SYNTH PROJECT"
    assert deviation_profile.mr_number == "MR-009"
    assert deviation_profile.material_title == "SYNTH MATERIAL"
    assert deviation_profile.total_rows == 1
    assert deviation_profile.has_vendor_entries is True
