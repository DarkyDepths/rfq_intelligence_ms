import uuid

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
    assert artifact.content["canonical_project_profile"]["rfq_code"] == "RFQ-TEST-001"
    assert artifact.content["downstream_readiness"]["briefing_ready"] is True
    assert artifact.content["downstream_readiness"]["historical_matching_ready"] is False
