import uuid
from pathlib import Path

from src.connectors.manager_connector import ManagerConnector
from src.datasources.artifact_datasource import ArtifactDatasource
from src.services.intake_service import IntakeService


def _event_meta() -> dict:
    return {
        "event_id": "evt-001",
        "event_type": "rfq.created",
        "event_version": "1.0",
        "emitted_at": "2026-03-24T10:00:00Z",
        "producer": "rfq_manager_ms",
    }


class _TrackingConnector(ManagerConnector):
    def __init__(self, *, package_path: Path | None):
        super().__init__(base_url="http://manager")
        self.package_path = package_path
        self.package_refs: list[str] = []

    def fetch_package_local_path(self, package_ref: str) -> Path:
        self.package_refs.append(package_ref)
        if self.package_path is None:
            raise FileNotFoundError(package_ref)
        return self.package_path


class _FakePackageParser:
    def __init__(self, status: str = "parsed_ok"):
        self.status = status
        self.calls: list[tuple[Path, str]] = []

    def parse(self, package_path, rfq_id: str) -> dict:
        resolved_path = Path(package_path)
        self.calls.append((resolved_path, rfq_id))
        return {
            "rfq_id": rfq_id,
            "parser_version": "package-parser-v1.0",
            "parsed_at": "2026-03-31T00:00:00Z",
            "input_type": "directory",
            "input_path": None,
            "package_inventory": {
                "package_root_name": "SAMPLE-MR-001 ITEM-REV-00",
                "input_type": "directory",
                "total_files": 5,
                "total_files_raw": 5,
                "total_folders": 2,
                "total_size_bytes": 1234,
                "files": [],
                "folders": [],
                "root_files": [],
                "file_extension_counts": {".pdf": 3, ".xlsx": 1, ".docx": 1},
                "system_file_count": 0,
                "scanned_at": "2026-03-31T00:00:00Z",
            },
            "package_identity": {
                "mr_number": "SA-AYPP-6-MR-022",
                "mr_number_short": "MR-022",
                "revision": "00",
                "material_description": "COLLECTION VESSEL - CDS",
                "project_code": "SA-AYPP-6",
                "package_root_name": "SAMPLE-MR-001 ITEM-REV-00",
                "mr_numbers_in_filenames": ["MR-022", "MR-023"],
                "mr_number_mismatches": ["MR-023"],
            },
            "section_registry": {
                "matched_sections": [],
                "unmatched_folders": [{"name": "Revision History-MR Comment Log"}],
                "missing_canonical_sections": [],
                "numbered_section_count": 16,
                "unnumbered_section_count": 1,
                "total_mr_index_count": 16,
            },
            "standards_profile": {
                "total_count": 43,
                "samss": [],
                "saes": [],
                "saep": [],
                "std_dwg": [],
                "other": [],
                "samss_count": 9,
                "saes_count": 19,
                "saep_count": 10,
                "std_dwg_count": 5,
                "subfolder_structure": ["1. SAMSS", "2. SAES"],
            },
            "bom_profile": {
                "source_file": "02/fixture.xlsx",
                "sheet_name": "BOM",
                "line_items": [],
                "total_line_items": 1,
                "tag_numbers_found": ["K18-D-0003"],
                "nine_com_codes_found": ["6000002521"],
                "design_codes_found": ["ASME SECTION VIII DIV1"],
                "locations_found": ["YANBU"],
            },
            "rvl_profile": {
                "source_file": "03/fixture.docx",
                "source_format": "docx",
                "vendors": [],
                "total_vendors": 10,
                "unique_vendor_names": ["Vendor A"],
                "unique_countries": ["SA"],
                "nine_com_codes": ["6000002521"],
                "mr_number_in_rvl": "MR-023",
            },
            "sa175_profile": None,
            "compliance_profile": None,
            "deviation_profile": None,
            "parser_report": {
                "status": self.status,
                "parser_version": "package-parser-v1.0",
                "stages": [],
                "warnings": [],
                "errors": [],
                "cross_checks": [
                    {
                        "code": "PACKAGE_MR_vs_RVL_MR",
                        "status": "warn" if self.status != "parsed_ok" else "pass",
                        "left_field_path": "package_identity.mr_number_short",
                        "right_field_path": "rvl_profile.mr_number_in_rvl",
                        "left_value": "MR-022",
                        "right_value": "MR-023" if self.status != "parsed_ok" else "MR-022",
                        "tolerance_abs": None,
                        "tolerance_rel": None,
                        "delta_abs": None,
                        "delta_rel": None,
                        "note": None,
                    }
                ],
            },
        }


def test_build_intake_profile_from_rfq_created_persists_partial_artifact(db_session):
    datasource = ArtifactDatasource(db_session)
    connector = ManagerConnector(base_url="http://manager")
    service = IntakeService(datasource=datasource, connector=connector)

    rfq_id = str(uuid.uuid4())
    rfq_context = {
        "rfq_id": rfq_id,
        "rfq_code": "RFQ-TEST-001",
        "client_name": "Albassam",
        "project_title": "GHI Tanks",
        "source_package_refs": [
            {
                "reference": f"rfq-files/{rfq_id}/source-package.zip",
                "display_name": "source-package.zip",
            }
        ],
        "created_at": "2026-03-24T09:30:00Z",
    }

    artifact = service.build_intake_profile_from_rfq_created(rfq_context=rfq_context, event_meta=_event_meta())

    assert artifact.artifact_type == "rfq_intake_profile"
    assert artifact.status == "partial"
    assert artifact.is_current is True
    assert artifact.content["artifact_meta"]["slice"] == "rfq.created_vertical_slice_v1"
    assert artifact.content["canonical_project_profile"]["rfq_code"] == "RFQ-TEST-001"
    assert artifact.content["downstream_readiness"]["briefing_ready"] is True
    assert artifact.content["downstream_readiness"]["historical_matching_ready"] is False


def test_build_intake_profile_from_rfq_created_uses_package_parser_when_path_available(db_session):
    datasource = ArtifactDatasource(db_session)
    connector = _TrackingConnector(package_path=Path("d:/fixtures/package-root"))
    package_parser = _FakePackageParser(status="parsed_ok")
    service = IntakeService(datasource=datasource, connector=connector, package_parser=package_parser)

    rfq_id = str(uuid.uuid4())
    rfq_context = {
        "rfq_id": rfq_id,
        "rfq_code": "RFQ-TEST-002",
        "client_name": "Albassam",
        "project_title": "GHI Tanks",
        "source_package_refs": [
            {
                "reference": "local://source_package_sample_001",
                "display_name": "source-package.zip",
            }
        ],
        "created_at": "2026-03-24T09:30:00Z",
    }

    artifact = service.build_intake_profile_from_rfq_created(rfq_context=rfq_context, event_meta=_event_meta())

    assert connector.package_refs == ["local://source_package_sample_001"]
    assert package_parser.calls == [(Path("d:/fixtures/package-root"), rfq_id)]
    assert artifact.status == "complete"
    assert artifact.content["artifact_meta"]["slice"] == "rfq.created_package_parsed_v1"
    assert artifact.content["artifact_meta"]["parser_version"] == "package-parser-v1.0"
    assert artifact.content["source_package"]["visibility_level"] == "parsed"
    assert artifact.content["source_package"]["package_root_name"] == "SAMPLE-MR-001 ITEM-REV-00"
    assert artifact.content["package_identity"]["mr_number"] == "SA-AYPP-6-MR-022"
    assert artifact.content["document_understanding"]["bom_profile"] is not None
    assert artifact.content["canonical_project_profile"]["tag_numbers"] == ["K18-D-0003"]
    assert artifact.content["canonical_project_profile"]["vendor_count"] == 10
    assert artifact.content["parser_report_status"] == "parsed_ok"


def test_build_intake_profile_from_rfq_created_keeps_partial_when_parser_has_warnings(db_session):
    datasource = ArtifactDatasource(db_session)
    connector = _TrackingConnector(package_path=Path("d:/fixtures/package-root"))
    package_parser = _FakePackageParser(status="parsed_with_warnings")
    service = IntakeService(datasource=datasource, connector=connector, package_parser=package_parser)

    rfq_id = str(uuid.uuid4())
    rfq_context = {
        "rfq_id": rfq_id,
        "rfq_code": "RFQ-TEST-003",
        "client_name": "Albassam",
        "project_title": "GHI Tanks",
        "source_package_refs": [
            {
                "reference": "local://source_package_sample_001",
                "display_name": "source-package.zip",
            }
        ],
        "created_at": "2026-03-24T09:30:00Z",
    }

    artifact = service.build_intake_profile_from_rfq_created(rfq_context=rfq_context, event_meta=_event_meta())

    assert artifact.status == "partial"
    assert artifact.content["artifact_meta"]["slice"] == "rfq.created_package_parsed_v1"
    assert artifact.content["parser_report_status"] == "parsed_with_warnings"
    assert artifact.content["quality_and_gaps"]["review_flags"] == ["MR number mismatch between package and RVL"]
    assert artifact.content["downstream_readiness"]["requires_human_review"] is True


def test_manager_connector_fetch_package_local_path_resolves_local_fixture_alias() -> None:
    connector = ManagerConnector(base_url="http://manager")

    package_path = connector.fetch_package_local_path("local://source_package_sample_001")

    assert package_path.exists()
    assert package_path.is_dir()
    assert package_path.name == "SA-AYPP-6-MR-022_COLLECTION VESSEL - CDS-REV-00"
