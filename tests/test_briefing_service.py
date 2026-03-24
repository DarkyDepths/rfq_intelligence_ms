import uuid

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
