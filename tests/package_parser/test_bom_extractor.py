from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

from src.services.package_parser.extractors.bom_extractor import BomExtractor
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


def test_bom_extractor_parses_real_fixture_bom_workbook() -> None:
    fixture_root = _fixture_package_root()
    inventory = TreeScanner().scan(fixture_root)
    registry = SectionClassifier().classify(inventory)

    bom_profile = BomExtractor().extract(inventory, registry, fixture_root)

    assert bom_profile is not None
    assert bom_profile.source_file == (
        "02-MR Description-BOM/02_BOM_SA-AYPP-6-MR-022_COLLECTION VESSEL- CDS.xlsx"
    )
    assert bom_profile.sheet_name == "BOM"
    assert bom_profile.total_line_items == 1
    assert bom_profile.tag_numbers_found == ["K18-D-0003"]
    assert bom_profile.nine_com_codes_found == ["6000002521"]
    assert bom_profile.design_codes_found == ["ASME SECTION VIII DIV1"]
    assert bom_profile.locations_found == ["YANBU"]

    line_item = bom_profile.line_items[0]
    assert line_item.sheet_row == 7
    assert line_item.mr_line_item == "1"
    assert line_item.line_item == "A.1"
    assert line_item.nine_com == "6000002521"
    assert line_item.plant_no == "K18"
    assert line_item.pipeline == "EAST/WEST PIPELINE #2"
    assert line_item.design_code == "ASME SECTION VIII DIV1"
    assert line_item.service == "COLLECTION VESSEL"
    assert line_item.material_type == "Vessel"
    assert line_item.location == "YANBU"
    assert line_item.technical_spec == "PE-020034"
    assert line_item.tag_number == "K18-D-0003"
    assert line_item.data_sheet == "PE-020007"
    assert line_item.reference_drawings == "P&ID: 'PA-011022"
    assert line_item.quantity is None


def test_bom_extractor_parses_synthetic_workbook_without_sample_specific_assumptions(tmp_path: Path) -> None:
    package_root = tmp_path / "SYNTH-1-MR-001_SAMPLE ITEM-REV-00"
    bom_section = package_root / "02-MR Description-BOM"
    bom_section.mkdir(parents=True)

    workbook_path = bom_section / "02_bom_export.xlsx"
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Equipment Register"
    worksheet["A1"] = "Synthetic Title"
    worksheet["A3"] = "mr li"
    worksheet["B3"] = "Line   Item"
    worksheet["C3"] = "9com"
    worksheet["D3"] = "Plant No"
    worksheet["E3"] = "Design Code"
    worksheet["F3"] = "Service"
    worksheet["G3"] = "matl / eqpt type"
    worksheet["H3"] = "Location"
    worksheet["I3"] = "Tech Spec"
    worksheet["J3"] = "Tag Number"
    worksheet["K3"] = "Data Sheet"
    worksheet["L3"] = "Reference Drawings"
    worksheet["M3"] = "QTY"
    worksheet.append([])
    worksheet["A5"] = 12
    worksheet["B5"] = "B.7"
    worksheet["C5"] = 7000000001
    worksheet["D5"] = "P55"
    worksheet["E5"] = "ASME B31.3"
    worksheet["F5"] = "FILTER"
    worksheet["G5"] = "Strainer"
    worksheet["H5"] = "JUBAIL"
    worksheet["I5"] = "TS-001"
    worksheet["J5"] = "P55-F-0007"
    worksheet["K5"] = "DS-001"
    worksheet["L5"] = "DRG-100"
    worksheet["M5"] = 2
    workbook.save(workbook_path)
    workbook.close()

    (bom_section / "02_Subcomponents List for SYNTH-1-MR-001.xlsx").write_text("ignore", encoding="utf-8")
    (bom_section / "02_Scope Of Supply.pdf").write_text("ignore", encoding="utf-8")

    inventory = TreeScanner().scan(package_root)
    registry = SectionClassifier().classify(inventory)

    bom_profile = BomExtractor().extract(inventory, registry, package_root)

    assert bom_profile is not None
    assert bom_profile.source_file == "02-MR Description-BOM/02_bom_export.xlsx"
    assert bom_profile.sheet_name == "Equipment Register"
    assert bom_profile.total_line_items == 1
    assert bom_profile.tag_numbers_found == ["P55-F-0007"]
    assert bom_profile.nine_com_codes_found == ["7000000001"]
    assert bom_profile.design_codes_found == ["ASME B31.3"]
    assert bom_profile.locations_found == ["JUBAIL"]

    line_item = bom_profile.line_items[0]
    assert line_item.sheet_row == 5
    assert line_item.mr_line_item == "12"
    assert line_item.line_item == "B.7"
    assert line_item.nine_com == "7000000001"
    assert line_item.plant_no == "P55"
    assert line_item.design_code == "ASME B31.3"
    assert line_item.service == "FILTER"
    assert line_item.material_type == "Strainer"
    assert line_item.location == "JUBAIL"
    assert line_item.technical_spec == "TS-001"
    assert line_item.tag_number == "P55-F-0007"
    assert line_item.data_sheet == "DS-001"
    assert line_item.reference_drawings == "DRG-100"
    assert line_item.quantity == 2.0
