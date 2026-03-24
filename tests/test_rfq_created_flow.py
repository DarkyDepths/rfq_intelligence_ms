import uuid

import pytest

from src.connectors.manager_connector import ManagerConnector
from src.datasources.artifact_datasource import ArtifactDatasource
from src.event_handlers.lifecycle_handlers import LifecycleHandlers
from src.services.analytical_record_service import AnalyticalRecordService
from src.services.briefing_service import BriefingService
from src.services.intake_service import IntakeService
from src.services.review_service import ReviewService
from src.services.snapshot_service import SnapshotService
from src.services.workbook_service import WorkbookService


def _build_services(db_session):
    datasource = ArtifactDatasource(db_session)
    connector = ManagerConnector(base_url="http://manager")
    intake_service = IntakeService(datasource=datasource, connector=connector)
    briefing_service = BriefingService(datasource=datasource)
    workbook_service = WorkbookService(datasource=datasource, connector=connector)
    review_service = ReviewService(datasource=datasource)
    snapshot_service = SnapshotService(datasource=datasource)
    analytical_record_service = AnalyticalRecordService(datasource=datasource)

    return (
        datasource,
        LifecycleHandlers(
            intake_service=intake_service,
            briefing_service=briefing_service,
            workbook_service=workbook_service,
            review_service=review_service,
            snapshot_service=snapshot_service,
            analytical_record_service=analytical_record_service,
        ),
    )


def _rfq_created_event(rfq_id: str, event_id: str = "evt-rfq-created") -> dict:
    return {
        "event_id": event_id,
        "event_type": "rfq.created",
        "event_version": "1.0",
        "producer": "rfq_manager_ms",
        "emitted_at": "2026-03-24T11:00:00Z",
        "payload": {
            "rfq_id": rfq_id,
        },
    }


@pytest.mark.asyncio
async def test_handle_rfq_created_processes_event_and_returns_structured_result(db_session):
    _, handler = _build_services(db_session)
    rfq_id = str(uuid.uuid4())

    result = await handler.handle_rfq_created(_rfq_created_event(rfq_id=rfq_id, event_id="evt-100"))

    assert result["status"] == "processed"
    assert result["rfq_id"] == rfq_id
    assert "rfq_intelligence_snapshot" in result["artifacts"]


@pytest.mark.asyncio
async def test_snapshot_endpoint_before_and_after_rfq_created_flow(client, db_session):
    rfq_id = str(uuid.uuid4())

    before = client.get(f"/intelligence/v1/rfqs/{rfq_id}/snapshot")
    assert before.status_code == 404

    _, handler = _build_services(db_session)
    await handler.handle_rfq_created(_rfq_created_event(rfq_id=rfq_id, event_id="evt-101"))

    after = client.get(f"/intelligence/v1/rfqs/{rfq_id}/snapshot")
    assert after.status_code == 200

    body = after.json()
    assert body["artifact_type"] == "rfq_intelligence_snapshot"
    assert body["content"]["workbook_panel"]["status"] == "not_ready"
    assert body["content"]["review_panel"]["status"] == "not_ready"


@pytest.mark.asyncio
async def test_current_artifact_versions_exist_after_rfq_created_flow(db_session):
    datasource, handler = _build_services(db_session)
    rfq_id = str(uuid.uuid4())

    await handler.handle_rfq_created(_rfq_created_event(rfq_id=rfq_id, event_id="evt-102"))

    current = datasource.list_current_artifacts_for_rfq(uuid.UUID(rfq_id))
    assert "rfq_intake_profile" in current
    assert "intelligence_briefing" in current
    assert "rfq_analytical_record" in current
    assert "rfq_intelligence_snapshot" in current
