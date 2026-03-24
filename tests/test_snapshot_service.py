import uuid

from src.connectors.manager_connector import ManagerConnector
from src.datasources.artifact_datasource import ArtifactDatasource
from src.services.analytical_record_service import AnalyticalRecordService
from src.services.briefing_service import BriefingService
from src.services.intake_service import IntakeService
from src.services.snapshot_service import SnapshotService


def _event_meta() -> dict:
    return {
        "event_id": "evt-003",
        "event_type": "rfq.created",
        "event_version": "1.0",
        "emitted_at": "2026-03-24T10:20:00Z",
        "producer": "rfq_manager_ms",
    }


def test_rebuild_snapshot_for_rfq_creates_snapshot_with_unavailable_workbook_sections(db_session):
    datasource = ArtifactDatasource(db_session)
    intake_service = IntakeService(datasource=datasource, connector=ManagerConnector(base_url="http://manager"))
    briefing_service = BriefingService(datasource=datasource)
    analytical_service = AnalyticalRecordService(datasource=datasource)
    snapshot_service = SnapshotService(datasource=datasource)

    rfq_id = str(uuid.uuid4())
    event_meta = _event_meta()
    context = {
        "rfq_id": rfq_id,
        "rfq_code": "RFQ-TEST-003",
        "client_name": "Client Y",
        "project_title": "Project Y",
        "source_package_refs": [{"reference": f"rfq-files/{rfq_id}/source.zip", "display_name": "source.zip"}],
        "created_at": None,
    }

    intake_artifact = intake_service.build_intake_profile_from_rfq_created(rfq_context=context, event_meta=event_meta)
    briefing_service.build_briefing_from_intake(intake_artifact=intake_artifact, event_meta=event_meta)
    analytical_service.build_initial_analytical_record(rfq_context=context, intake_artifact=intake_artifact, event_meta=event_meta)

    snapshot = snapshot_service.rebuild_snapshot_for_rfq(rfq_id=rfq_id, source_event_meta=event_meta)

    assert snapshot.artifact_type == "rfq_intelligence_snapshot"
    assert snapshot.status == "partial"
    assert snapshot.content["availability_matrix"]["workbook_profile"] == "not_ready"
    assert snapshot.content["review_panel"]["status"] == "not_ready"
    assert snapshot.content["requires_human_review"] is True
