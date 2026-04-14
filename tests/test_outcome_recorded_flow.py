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


def _rfq_created_event(rfq_id: str, event_id: str = "evt-rfq-created-outcome-pre") -> dict:
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


def _outcome_recorded_event(
    rfq_id: str,
    event_id: str = "evt-outcome-1",
    outcome: str = "awarded",
    outcome_reason: str | None = "best value",
) -> dict:
    payload = {
        "rfq_id": rfq_id,
        "outcome": outcome,
        "recorded_at": "2026-03-24T15:00:00Z",
    }
    if outcome_reason is not None:
        payload["outcome_reason"] = outcome_reason

    return {
        "event_id": event_id,
        "event_type": "outcome.recorded",
        "event_version": "1.0",
        "producer": "rfq_manager_ms",
        "emitted_at": "2026-03-24T15:01:00Z",
        "payload": payload,
    }


@pytest.mark.asyncio
async def test_outcome_recorded_happy_path_enriches_analytical_and_refreshes_snapshot(db_session):
    datasource, _, handler = _build_services(db_session)
    rfq_id = str(uuid.uuid4())

    await handler.handle_rfq_created(_rfq_created_event(rfq_id=rfq_id, event_id="evt-pre-outcome-1"))
    result = await handler.handle_outcome_recorded(
        _outcome_recorded_event(rfq_id=rfq_id, event_id="evt-outcome-happy-1", outcome="awarded")
    )

    assert result["status"] == "processed"

    current = datasource.list_current_artifacts_for_rfq(uuid.UUID(rfq_id))
    analytical = current["rfq_analytical_record"].content
    snapshot = current["rfq_intelligence_snapshot"].content

    assert analytical["outcome_enrichment"]["outcome_status"] == "awarded"
    assert analytical["outcome_enrichment"]["recorded_at"] == "2026-03-24T15:00:00Z"
    assert analytical["outcome_enrichment"]["outcome_source_event_type"] == "outcome.recorded"

    assert snapshot["outcome_summary"]["status"] == "recorded"
    assert snapshot["outcome_summary"]["outcome"] == "awarded"


@pytest.mark.asyncio
async def test_outcome_recorded_idempotency_same_event_id_no_duplicate_versions(db_session):
    datasource, processed_event_datasource, handler = _build_services(db_session)
    rfq_id = str(uuid.uuid4())

    await handler.handle_rfq_created(_rfq_created_event(rfq_id=rfq_id, event_id="evt-pre-outcome-2"))
    event = _outcome_recorded_event(rfq_id=rfq_id, event_id="evt-outcome-dup-1", outcome="lost")

    first = await handler.handle_outcome_recorded(event)
    second = await handler.handle_outcome_recorded(event)

    assert first["status"] == "processed"
    assert second["status"] == "duplicate"

    artifacts = datasource.list_artifacts(uuid.UUID(rfq_id))
    counts = {}
    for artifact in artifacts:
        counts[artifact.artifact_type] = counts.get(artifact.artifact_type, 0) + 1

    assert counts.get("rfq_analytical_record") == 2
    assert counts.get("rfq_intelligence_snapshot") == 2

    processed = processed_event_datasource.get_by_event_id("evt-outcome-dup-1")
    assert processed is not None
    assert processed.status == "completed"


@pytest.mark.asyncio
async def test_outcome_recorded_failure_rolls_back_no_partial_current_corruption(db_session):
    datasource, processed_event_datasource, handler = _build_services(db_session)
    rfq_id = str(uuid.uuid4())

    await handler.handle_rfq_created(_rfq_created_event(rfq_id=rfq_id, event_id="evt-pre-outcome-3"))

    before = datasource.get_current_artifact(uuid.UUID(rfq_id), "rfq_analytical_record")
    before_version = before.version
    before_event_id = before.source_event_id

    original = handler.snapshot_service.rebuild_snapshot_for_rfq

    def _fail_snapshot(*args, **kwargs):
        raise RuntimeError("forced outcome snapshot failure")

    handler.snapshot_service.rebuild_snapshot_for_rfq = _fail_snapshot

    with pytest.raises(RuntimeError):
        await handler.handle_outcome_recorded(
            _outcome_recorded_event(rfq_id=rfq_id, event_id="evt-outcome-fail-1", outcome="cancelled")
        )

    handler.snapshot_service.rebuild_snapshot_for_rfq = original

    after = datasource.get_current_artifact(uuid.UUID(rfq_id), "rfq_analytical_record")
    assert after.version == before_version
    assert after.source_event_id == before_event_id

    processed = processed_event_datasource.get_by_event_id("evt-outcome-fail-1")
    assert processed is not None
    assert processed.status == "failed"


@pytest.mark.asyncio
async def test_outcome_recorded_without_prior_analytical_creates_minimal_record(db_session):
    datasource, _, handler = _build_services(db_session)
    rfq_id = str(uuid.uuid4())

    result = await handler.handle_outcome_recorded(
        _outcome_recorded_event(rfq_id=rfq_id, event_id="evt-outcome-no-prior-1", outcome="awarded")
    )

    assert result["status"] == "processed"

    current = datasource.list_current_artifacts_for_rfq(uuid.UUID(rfq_id))
    assert "rfq_analytical_record" in current

    analytical = current["rfq_analytical_record"].content
    assert analytical["rfq_identifiers"]["rfq_id"] == rfq_id
    assert analytical["outcome_enrichment"]["outcome_status"] == "awarded"
    assert analytical["completeness_flags"]["intake_profile_available"] is False
    assert analytical["completeness_flags"]["workbook_profile_available"] is False


@pytest.mark.asyncio
async def test_outcome_snapshot_truthfulness_keeps_dormant_capabilities_unavailable(db_session):
    datasource, _, handler = _build_services(db_session)
    rfq_id = str(uuid.uuid4())

    await handler.handle_outcome_recorded(
        _outcome_recorded_event(rfq_id=rfq_id, event_id="evt-outcome-truth-1", outcome="lost")
    )

    snapshot = datasource.get_current_artifact(uuid.UUID(rfq_id), "rfq_intelligence_snapshot")
    content = snapshot.content

    assert content["outcome_summary"]["status"] == "recorded"
    assert content["outcome_summary"]["outcome"] == "lost"
    assert content["availability_matrix"]["benchmarking"] == "insufficient_historical_base"
    assert content["availability_matrix"]["similarity"] == "insufficient_historical_base"
