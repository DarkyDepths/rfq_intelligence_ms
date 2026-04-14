import uuid

import pytest

from src.datasources.artifact_datasource import ArtifactDatasource
from src.datasources.processed_event_datasource import ProcessedEventDatasource
from src.event_handlers.lifecycle_handlers import LifecycleHandlers
from src.services.analytical_record_service import AnalyticalRecordService
from src.services.briefing_service import BriefingService
from src.services.event_processing_service import EventProcessingService
from src.services.intake_service import IntakeService
from src.services.review_service import ReviewService
from src.services.snapshot_service import SnapshotService
from src.services.workbook_service import WorkbookService
from tests.support_manager_connector import LocalFixtureManagerConnector


def _build_services(db_session):
    datasource = ArtifactDatasource(db_session)
    processed_event_datasource = ProcessedEventDatasource(db_session)
    event_processing_service = EventProcessingService(processed_event_datasource)
    connector = LocalFixtureManagerConnector()
    intake_service = IntakeService(datasource=datasource, connector=connector)
    briefing_service = BriefingService(datasource=datasource)
    workbook_service = WorkbookService(datasource=datasource, connector=connector)
    review_service = ReviewService(datasource=datasource)
    snapshot_service = SnapshotService(datasource=datasource)
    analytical_record_service = AnalyticalRecordService(datasource=datasource)

    return (
        datasource,
        processed_event_datasource,
        LifecycleHandlers(
            intake_service=intake_service,
            briefing_service=briefing_service,
            workbook_service=workbook_service,
            review_service=review_service,
            snapshot_service=snapshot_service,
            analytical_record_service=analytical_record_service,
            event_processing_service=event_processing_service,
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
    _, _, handler = _build_services(db_session)
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

    _, _, handler = _build_services(db_session)
    await handler.handle_rfq_created(_rfq_created_event(rfq_id=rfq_id, event_id="evt-101"))

    after = client.get(f"/intelligence/v1/rfqs/{rfq_id}/snapshot")
    assert after.status_code == 200

    body = after.json()
    assert body["artifact_type"] == "rfq_intelligence_snapshot"
    assert body["content"]["workbook_panel"]["status"] == "not_ready"
    assert body["content"]["review_panel"]["status"] == "not_ready"


@pytest.mark.asyncio
async def test_current_artifact_versions_exist_after_rfq_created_flow(db_session):
    datasource, _, handler = _build_services(db_session)
    rfq_id = str(uuid.uuid4())

    await handler.handle_rfq_created(_rfq_created_event(rfq_id=rfq_id, event_id="evt-102"))

    current = datasource.list_current_artifacts_for_rfq(uuid.UUID(rfq_id))
    assert "rfq_intake_profile" in current
    assert "intelligence_briefing" in current
    assert "rfq_analytical_record" in current
    assert "rfq_intelligence_snapshot" in current


@pytest.mark.asyncio
async def test_duplicate_event_idempotency_does_not_create_new_versions(db_session):
    datasource, processed_event_datasource, handler = _build_services(db_session)
    rfq_id = str(uuid.uuid4())
    event = _rfq_created_event(rfq_id=rfq_id, event_id="evt-dup-1")

    first = await handler.handle_rfq_created(event)
    second = await handler.handle_rfq_created(event)

    assert first["status"] == "processed"
    assert second["status"] == "duplicate"

    artifacts = datasource.list_artifacts(uuid.UUID(rfq_id))
    counts = {}
    for artifact in artifacts:
        counts[artifact.artifact_type] = counts.get(artifact.artifact_type, 0) + 1

    assert counts.get("rfq_intake_profile") == 1
    assert counts.get("intelligence_briefing") == 1
    assert counts.get("rfq_analytical_record") == 1
    assert counts.get("rfq_intelligence_snapshot") == 1

    processed = processed_event_datasource.get_by_event_id("evt-dup-1")
    assert processed is not None
    assert processed.status == "completed"


@pytest.mark.asyncio
async def test_failure_rolls_back_artifacts_and_marks_event_failed(db_session):
    datasource, processed_event_datasource, handler = _build_services(db_session)
    rfq_id = str(uuid.uuid4())

    original = handler.briefing_service.build_briefing_from_intake

    def _fail_after_intake(*args, **kwargs):
        raise RuntimeError("forced briefing failure")

    handler.briefing_service.build_briefing_from_intake = _fail_after_intake

    with pytest.raises(RuntimeError):
        await handler.handle_rfq_created(_rfq_created_event(rfq_id=rfq_id, event_id="evt-fail-1"))

    handler.briefing_service.build_briefing_from_intake = original

    current = datasource.list_current_artifacts_for_rfq(uuid.UUID(rfq_id))
    assert current == {}

    processed = processed_event_datasource.get_by_event_id("evt-fail-1")
    assert processed is not None
    assert processed.status == "failed"
    assert processed.error_message is not None
    assert "forced briefing failure" in processed.error_message


@pytest.mark.asyncio
async def test_retry_after_failure_with_same_event_id_succeeds_cleanly(db_session):
    datasource, processed_event_datasource, handler = _build_services(db_session)
    rfq_id = str(uuid.uuid4())
    event = _rfq_created_event(rfq_id=rfq_id, event_id="evt-retry-1")

    original = handler.briefing_service.build_briefing_from_intake

    def _fail_once(*args, **kwargs):
        raise RuntimeError("forced once")

    handler.briefing_service.build_briefing_from_intake = _fail_once
    with pytest.raises(RuntimeError):
        await handler.handle_rfq_created(event)

    handler.briefing_service.build_briefing_from_intake = original
    second = await handler.handle_rfq_created(event)

    assert second["status"] == "processed"

    artifacts = datasource.list_artifacts(uuid.UUID(rfq_id))
    counts = {}
    for artifact in artifacts:
        counts[artifact.artifact_type] = counts.get(artifact.artifact_type, 0) + 1

    assert counts.get("rfq_intake_profile") == 1
    assert counts.get("intelligence_briefing") == 1
    assert counts.get("rfq_analytical_record") == 1
    assert counts.get("rfq_intelligence_snapshot") == 1

    processed = processed_event_datasource.get_by_event_id("evt-retry-1")
    assert processed is not None
    assert processed.status == "completed"
