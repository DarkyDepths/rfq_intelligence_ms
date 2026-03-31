from __future__ import annotations

from pathlib import Path

from src.services.package_parser.parser_orchestrator import PackageParserOrchestrator


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


def test_package_parser_orchestrator_parses_real_fixture_end_to_end() -> None:
    fixture_root = _fixture_package_root()

    envelope = PackageParserOrchestrator().parse(fixture_root, rfq_id="rfq-step8-test")

    assert envelope["rfq_id"] == "rfq-step8-test"
    assert envelope["parser_version"] == "package-parser-v1.0"
    assert envelope["input_type"] == "directory"
    assert envelope["input_path"] is None

    assert envelope["package_inventory"] is not None
    assert envelope["package_identity"] is not None
    assert envelope["section_registry"] is not None
    assert envelope["standards_profile"] is not None
    assert envelope["bom_profile"] is not None
    assert envelope["rvl_profile"] is not None
    assert "sa175_profile" in envelope
    assert "compliance_profile" in envelope
    assert "deviation_profile" in envelope
    assert envelope["sa175_profile"] is None
    assert envelope["compliance_profile"] is None
    assert envelope["deviation_profile"] is None

    assert envelope["package_identity"]["mr_number"] == "SA-AYPP-6-MR-022"
    assert envelope["package_identity"]["mr_number_short"] == "MR-022"
    assert envelope["package_identity"]["revision"] == "00"
    assert envelope["section_registry"]["missing_canonical_sections"] == []

    assert envelope["standards_profile"]["samss_count"] == 9
    assert envelope["standards_profile"]["saes_count"] == 19
    assert envelope["bom_profile"]["total_line_items"] == 1
    assert envelope["bom_profile"]["tag_numbers_found"] == ["K18-D-0003"]
    assert envelope["rvl_profile"]["source_format"] == "docx"
    assert envelope["rvl_profile"]["mr_number_in_rvl"] == "MR-023"
    assert envelope["rvl_profile"]["total_vendors"] >= 10

    parser_report = envelope["parser_report"]
    assert parser_report is not None
    assert parser_report["parser_version"] == "package-parser-v1.0"
    assert parser_report["status"] == "parsed_with_warnings"
    assert len(parser_report["stages"]) == 4
    assert parser_report["warnings"] == []
    assert parser_report["errors"] == []

    checks = parser_report["cross_checks"]
    codes = [check["code"] for check in checks]
    assert "PACKAGE_MR_vs_RVL_MR" in codes
    assert "BOM_9COM_vs_RVL_9COM" in codes
    assert "MR_INDEX_COMPLETENESS" in codes
    assert "SECTION_PREFIX_CONSISTENCY" in codes

    mr_check = next(check for check in checks if check["code"] == "PACKAGE_MR_vs_RVL_MR")
    assert mr_check["status"] == "warn"
    assert mr_check["left_value"] == "MR-022"
    assert mr_check["right_value"] == "MR-023"
