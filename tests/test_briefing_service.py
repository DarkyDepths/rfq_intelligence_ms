import uuid
from types import SimpleNamespace

from src.datasources.artifact_datasource import ArtifactDatasource
from src.services.briefing_service import BriefingService
from src.services.intake_service import IntakeService
from src.connectors.manager_connector import ManagerConnector


def _event_meta() -> dict:
    return {
        "event_id": "evt-002",
        "event_type": "rfq.created",
        "event_version": "1.0",
        "emitted_at": "2026-03-24T10:10:00Z",
        "producer": "rfq_manager_ms",
    }


def test_build_briefing_from_intake_persists_partial_artifact(db_session):
    datasource = ArtifactDatasource(db_session)
    intake_service = IntakeService(datasource=datasource, connector=ManagerConnector(base_url="http://manager"))
    briefing_service = BriefingService(datasource=datasource)

    rfq_id = str(uuid.uuid4())
    intake_artifact = intake_service.build_intake_profile_from_rfq_created(
        rfq_context={
            "rfq_id": rfq_id,
            "rfq_code": "RFQ-TEST-002",
            "client_name": "Client X",
            "project_title": "Project X",
            "source_package_refs": [{"reference": f"rfq-files/{rfq_id}/source.zip", "display_name": "source.zip"}],
            "created_at": None,
        },
        event_meta=_event_meta(),
    )

    artifact = briefing_service.build_briefing_from_intake(intake_artifact=intake_artifact, event_meta=_event_meta())

    assert artifact.artifact_type == "intelligence_briefing"
    assert artifact.status == "partial"
    assert artifact.content["section_availability"]["benchmarking"] == "insufficient_historical_base"
    assert artifact.content["section_availability"]["workbook_comparison"] == "not_ready"
    assert artifact.content["review_posture"] == "supportive_review"


def test_build_briefing_from_parsed_intake_produces_deterministic_enriched_v1(db_session):
    datasource = ArtifactDatasource(db_session)
    briefing_service = BriefingService(datasource=datasource)
    rfq_id = uuid.uuid4()

    intake_artifact = SimpleNamespace(
        rfq_id=rfq_id,
        content={
            "artifact_meta": {
                "slice": "rfq.created_package_parsed_v1",
            },
            "source_package": {
                "primary_reference": "local://source_package_sample_001",
            },
            "package_structure": {
                "status": "parsed",
            },
            "package_identity": {
                "mr_number": "SA-AYPP-6-MR-022",
                "mr_number_short": "MR-022",
                "material_description": "COLLECTION VESSEL - CDS",
            },
            "document_understanding": {
                "standards_profile": {
                    "samss_count": 9,
                    "saes_count": 19,
                    "saep_count": 10,
                    "std_dwg_count": 5,
                },
                "bom_profile": {
                    "tag_numbers_found": ["K18-D-0003"],
                    "design_codes_found": ["ASME SECTION VIII DIV1"],
                },
                "rvl_profile": {
                    "total_vendors": 10,
                },
                "sa175_profile": {
                    "total_count": 4,
                },
                "compliance_profile": None,
                "deviation_profile": None,
            },
            "canonical_project_profile": {
                "rfq_id": str(rfq_id),
                "rfq_code": "RFQ-TEST-ENRICHED",
                "project_title": "Project X",
                "client_name": "Client X",
                "tag_numbers": ["K18-D-0003"],
                "design_codes": ["ASME SECTION VIII DIV1"],
                "standards_count": {"samss": 9, "saes": 19, "saep": 10, "std_dwg": 5},
            },
            "quality_and_gaps": {
                "gaps": ["specs/datasheet content extraction"],
                "review_flags": ["MR number mismatch between package and RVL"],
            },
            "downstream_readiness": {
                "briefing_ready": True,
                "workbook_comparison_ready": True,
                "requires_human_review": True,
            },
            "parser_report_status": "parsed_with_warnings",
        },
    )

    artifact = briefing_service.build_briefing_from_intake(intake_artifact=intake_artifact, event_meta=_event_meta())

    assert artifact.artifact_type == "intelligence_briefing"
    assert artifact.status == "partial"
    assert artifact.content["artifact_meta"]["slice"] == "rfq.created_deterministic_enriched_v1"
    assert artifact.content["section_availability"]["document_understanding"] == "partial_deterministic"
    assert artifact.content["section_availability"]["workbook_comparison"] == "ready_from_package_intake"
    assert artifact.content["what_is_known"]["mr_number"] == "SA-AYPP-6-MR-022"
    assert artifact.content["what_is_known"]["vendor_count"] == 10
    assert artifact.content["what_is_known"]["standards_count"]["samss"] == 9
    assert artifact.content["compliance_flags_or_placeholders"]["sa175_form_count"] == 4
    assert artifact.content["compliance_flags_or_placeholders"]["review_flags"] == [
        "MR number mismatch between package and RVL"
    ]
    assert artifact.content["package_readiness"]["parser_report_status"] == "parsed_with_warnings"


def test_build_briefing_from_parsed_intake_with_parser_warnings_still_succeeds(db_session):
    datasource = ArtifactDatasource(db_session)
    briefing_service = BriefingService(datasource=datasource)
    rfq_id = uuid.uuid4()

    intake_artifact = SimpleNamespace(
        rfq_id=rfq_id,
        content={
            "package_structure": {
                "status": "parsed",
            },
            "source_package": {
                "primary_reference": "local://source_package_sample_001",
            },
            "package_identity": {
                "mr_number_short": "MR-022",
            },
            "document_understanding": {
                "standards_profile": None,
                "bom_profile": None,
                "rvl_profile": {
                    "total_vendors": 3,
                },
                "sa175_profile": None,
                "compliance_profile": None,
                "deviation_profile": None,
            },
            "canonical_project_profile": {
                "rfq_id": str(rfq_id),
                "rfq_code": "RFQ-TEST-PARTIAL",
                "project_title": "Project Y",
                "client_name": "Client Y",
                "tag_numbers": [],
                "design_codes": [],
                "standards_count": {"samss": 0, "saes": 0, "saep": 0, "std_dwg": 0},
            },
            "quality_and_gaps": {
                "gaps": ["semantic QAQC understanding"],
                "review_flags": ["PACKAGE_MR_vs_RVL_MR"],
            },
            "downstream_readiness": {
                "briefing_ready": True,
                "workbook_comparison_ready": False,
                "requires_human_review": True,
            },
            "parser_report_status": "parsed_with_warnings",
        },
    )

    artifact = briefing_service.build_briefing_from_intake(intake_artifact=intake_artifact, event_meta=_event_meta())

    assert artifact.status == "partial"
    assert artifact.content["artifact_meta"]["slice"] == "rfq.created_deterministic_enriched_v1"
    assert artifact.content["risk_notes_or_placeholders"]["status"] == "partial_deterministic"
    assert artifact.content["section_availability"]["workbook_comparison"] == "not_ready"
    assert artifact.content["package_readiness"]["requires_human_review"] is True
