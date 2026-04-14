import uuid
from pathlib import Path

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
from src.services.workbook_parser import compute_structure
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


def _rfq_created_event(rfq_id: str, event_id: str = "evt-rfq-created-workbook-pre") -> dict:
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


def _workbook_uploaded_event(rfq_id: str, event_id: str = "evt-workbook-uploaded-1") -> dict:
    return {
        "event_id": event_id,
        "event_type": "workbook.uploaded",
        "event_version": "1.0",
        "producer": "rfq_manager_ms",
        "emitted_at": "2026-03-24T12:00:00Z",
        "payload": {
            "rfq_id": rfq_id,
            "workbook_ref": "local://workbook_sample_001",
            "workbook_filename": "ghi_workbook_32_sheets.xls",
            "uploaded_at": "2026-03-24T11:55:00Z",
        },
    }


def _fixture_workbook_exists() -> bool:
    root = Path(__file__).resolve().parents[1]
    path = root / "local_fixtures" / "workbook_uploaded" / "workbook_sample_001" / "ghi_workbook_32_sheets.xls"
    return path.exists()


@pytest.mark.asyncio
async def test_workbook_uploaded_happy_path_creates_artifacts_and_updates_snapshot(db_session):
    if not _fixture_workbook_exists():
        pytest.skip("Local workbook fixture is not available")

    datasource, _, handler = _build_services(db_session)
    rfq_id = str(uuid.uuid4())

    await handler.handle_rfq_created(_rfq_created_event(rfq_id=rfq_id, event_id="evt-pre-1"))
    result = await handler.handle_workbook_uploaded(_workbook_uploaded_event(rfq_id=rfq_id, event_id="evt-wb-1"))

    assert result["status"] == "processed"

    current = datasource.list_current_artifacts_for_rfq(uuid.UUID(rfq_id))
    assert "workbook_profile" in current
    assert "cost_breakdown_profile" in current
    assert "parser_report" in current
    assert "workbook_review_report" in current
    assert "rfq_analytical_record" in current
    assert "rfq_intelligence_snapshot" in current

    snapshot = current["rfq_intelligence_snapshot"].content
    assert snapshot["artifact_meta"]["slice"] == "v1_incremental_intelligence"
    assert snapshot["artifact_meta"]["slice"] != "rfq.created_vertical_slice_v1"
    assert snapshot["availability_matrix"]["workbook_profile"] == "available"
    assert snapshot["availability_matrix"]["cost_breakdown_profile"] == "available"
    assert snapshot["availability_matrix"]["parser_report"] == "available"
    assert snapshot["availability_matrix"]["workbook_review_report"] == "available"
    assert snapshot["workbook_panel"]["parser_status"] in {"parsed_ok", "parsed_with_warnings"}


@pytest.mark.asyncio
async def test_workbook_endpoints_404_before_and_200_after_processing(client, db_session):
    if not _fixture_workbook_exists():
        pytest.skip("Local workbook fixture is not available")

    _, _, handler = _build_services(db_session)
    rfq_id = str(uuid.uuid4())

    before_profile = client.get(f"/intelligence/v1/rfqs/{rfq_id}/workbook-profile")
    before_review = client.get(f"/intelligence/v1/rfqs/{rfq_id}/workbook-review")
    assert before_profile.status_code == 404
    assert before_review.status_code == 404

    await handler.handle_workbook_uploaded(_workbook_uploaded_event(rfq_id=rfq_id, event_id="evt-wb-2"))

    after_profile = client.get(f"/intelligence/v1/rfqs/{rfq_id}/workbook-profile")
    after_review = client.get(f"/intelligence/v1/rfqs/{rfq_id}/workbook-review")
    snapshot = client.get(f"/intelligence/v1/rfqs/{rfq_id}/snapshot")

    assert after_profile.status_code == 200
    assert after_review.status_code == 200
    assert snapshot.status_code == 200


def test_workbook_structure_missing_extra_logic_behaves_correctly():
    structure = compute_structure(
        expected_sheet_names=["S1", "S2", "S3"],
        actual_sheet_names=["S1", "S3", "S4"],
    )

    assert structure["missing_sheets"] == ["S2"]
    assert structure["extra_sheets"] == ["S4"]
    assert structure["sheet_count_found"] == 3


@pytest.mark.asyncio
async def test_pairing_validation_is_not_assessed_and_honest(db_session):
    if not _fixture_workbook_exists():
        pytest.skip("Local workbook fixture is not available")

    datasource, _, handler = _build_services(db_session)
    rfq_id = str(uuid.uuid4())

    await handler.handle_workbook_uploaded(_workbook_uploaded_event(rfq_id=rfq_id, event_id="evt-wb-3"))

    workbook_profile = datasource.get_current_artifact(uuid.UUID(rfq_id), "workbook_profile")
    pairing = workbook_profile.content["pairing_validation"]

    assert pairing["pairing_status"] == "not_assessed"
    assert "without assuming linkage" in pairing["notes"].lower()


@pytest.mark.asyncio
async def test_duplicate_workbook_uploaded_event_idempotency(db_session):
    if not _fixture_workbook_exists():
        pytest.skip("Local workbook fixture is not available")

    datasource, processed_event_datasource, handler = _build_services(db_session)
    rfq_id = str(uuid.uuid4())
    event = _workbook_uploaded_event(rfq_id=rfq_id, event_id="evt-wb-dup")

    first = await handler.handle_workbook_uploaded(event)
    second = await handler.handle_workbook_uploaded(event)

    assert first["status"] == "processed"
    assert second["status"] == "duplicate"

    artifacts = datasource.list_artifacts(uuid.UUID(rfq_id))
    counts = {}
    for artifact in artifacts:
        counts[artifact.artifact_type] = counts.get(artifact.artifact_type, 0) + 1

    assert counts.get("workbook_profile") == 1
    assert counts.get("cost_breakdown_profile") == 1
    assert counts.get("parser_report") == 1
    assert counts.get("workbook_review_report") == 1
    assert counts.get("rfq_analytical_record") == 1
    assert counts.get("rfq_intelligence_snapshot") == 1

    processed = processed_event_datasource.get_by_event_id("evt-wb-dup")
    assert processed is not None
    assert processed.status == "completed"


@pytest.mark.asyncio
async def test_workbook_uploaded_rerun_new_event_versions_artifacts_deterministically(db_session):
    if not _fixture_workbook_exists():
        pytest.skip("Local workbook fixture is not available")

    datasource, _, handler = _build_services(db_session)
    rfq_id = str(uuid.uuid4())

    await handler.handle_workbook_uploaded(_workbook_uploaded_event(rfq_id=rfq_id, event_id="evt-wb-rerun-1"))
    await handler.handle_workbook_uploaded(_workbook_uploaded_event(rfq_id=rfq_id, event_id="evt-wb-rerun-2"))

    artifacts = datasource.list_artifacts(uuid.UUID(rfq_id))
    counts = {}
    for artifact in artifacts:
        counts[artifact.artifact_type] = counts.get(artifact.artifact_type, 0) + 1

    assert counts.get("workbook_profile") == 2
    assert counts.get("cost_breakdown_profile") == 2
    assert counts.get("parser_report") == 2
    assert counts.get("workbook_review_report") == 2
    assert counts.get("rfq_analytical_record") == 2
    assert counts.get("rfq_intelligence_snapshot") == 2

    current = datasource.list_current_artifacts_for_rfq(uuid.UUID(rfq_id))
    assert current["workbook_profile"].version == 2
    assert current["cost_breakdown_profile"].version == 2
    assert current["parser_report"].version == 2


@pytest.mark.asyncio
async def test_workbook_flow_failure_rolls_back_and_no_partial_new_currents(db_session):
    if not _fixture_workbook_exists():
        pytest.skip("Local workbook fixture is not available")

    datasource, processed_event_datasource, handler = _build_services(db_session)
    rfq_id = str(uuid.uuid4())

    original = handler.review_service.build_workbook_review_report

    def _fail(*args, **kwargs):
        raise RuntimeError("forced workbook review failure")

    handler.review_service.build_workbook_review_report = _fail

    with pytest.raises(RuntimeError):
        await handler.handle_workbook_uploaded(_workbook_uploaded_event(rfq_id=rfq_id, event_id="evt-wb-fail"))

    handler.review_service.build_workbook_review_report = original

    current = datasource.list_current_artifacts_for_rfq(uuid.UUID(rfq_id))
    assert "workbook_profile" not in current
    assert "workbook_review_report" not in current

    processed = processed_event_datasource.get_by_event_id("evt-wb-fail")
    assert processed is not None
    assert processed.status == "failed"


@pytest.mark.asyncio
async def test_template_mismatch_persists_failed_parser_report_and_truthful_snapshot(db_session, monkeypatch):
    datasource, _, handler = _build_services(db_session)
    rfq_id = str(uuid.uuid4())

    def _fake_parser(*args, **kwargs):
        return {
            "template_recognition": {
                "template_family": "ghi_estimation_workbook_v1",
                "sheet_count_found": 1,
                "expected_sheet_count": 3,
                "recognition_status": "partial",
                "recognition_notes": "forced mismatch for test",
                "parser_version": "workbook-parser-v1.1",
            },
            "workbook_structure": {
                "sheet_names": ["General"],
                "sheet_count_found": 1,
                "expected_sheet_count": 3,
                "missing_sheets": ["Bid S", "Top Sheet"],
                "extra_sheets": [],
            },
            "high_value_extracts": {
                "text_hits": [],
                "numeric_sample": [],
            },
            "workbook_parse_envelope": {
                "rfq_id": "RFQ-UNKNOWN",
                "template_name": "ghi_estimation_workbook_v1",
                "workbook_format": "xls",
                "workbook_file_name": "mismatch.xls",
                "workbook_blob_path": None,
                "template_match": False,
                "parsed_at": "2026-03-25T00:00:00Z",
                "parser_version": "workbook-parser-v1.1",
                "workbook_profile": {
                    "rfq_identity": {
                        "project_name": "Forced mismatch workbook",
                    }
                },
                "cost_breakdown_profile": {
                    "bid_summary_lines": [],
                    "top_sheet_lines": [],
                },
                "parser_report": {
                    "status": "failed",
                    "parsed_sheets": [],
                    "skipped_sheets": ["Bid S", "Top Sheet"],
                    "warnings": [],
                    "errors": [
                        {
                            "code": "GENERAL_MISSING_REQUIRED_SHEET",
                            "severity": "error",
                            "sheet_name": "Bid S",
                            "cell_ref": None,
                            "row_number": None,
                            "field_path": None,
                            "message": "Required sheet missing",
                            "expected_value": "Bid S",
                            "actual_value": None,
                            "raw_value": None,
                        }
                    ],
                    "anchor_checks": [],
                    "cross_checks": [],
                    "sheet_reports": {
                        "general": {
                            "sheet_name": "General",
                            "status": "failed",
                            "merged_regions_count": None,
                            "expected_body_range": None,
                            "rows_scanned": None,
                            "rows_kept": None,
                            "rows_skipped": None,
                            "warning_count": 0,
                            "error_count": 1,
                        },
                        "bid_s": {
                            "sheet_name": "Bid S",
                            "status": "failed",
                            "merged_regions_count": None,
                            "expected_body_range": None,
                            "rows_scanned": None,
                            "rows_kept": None,
                            "rows_skipped": None,
                            "warning_count": 0,
                            "error_count": 1,
                        },
                        "top_sheet": {
                            "sheet_name": "Top Sheet",
                            "status": "failed",
                            "merged_regions_count": None,
                            "expected_body_range": None,
                            "rows_scanned": None,
                            "rows_kept": None,
                            "rows_skipped": None,
                            "warning_count": 0,
                            "error_count": 1,
                        },
                    },
                },
            },
        }

    monkeypatch.setattr("src.services.workbook_service.parse_workbook_deterministic", _fake_parser)

    result = await handler.handle_workbook_uploaded(
        _workbook_uploaded_event(rfq_id=rfq_id, event_id="evt-wb-template-fail")
    )

    assert result["status"] == "processed_with_failures"
    assert result["artifacts"]["parser_report"]["status"] == "failed"
    assert result["artifacts"]["workbook_review_report"]["status"] == "skipped"

    current = datasource.list_current_artifacts_for_rfq(uuid.UUID(rfq_id))
    assert "workbook_profile" in current
    assert "cost_breakdown_profile" in current
    assert "parser_report" in current
    assert "workbook_review_report" not in current

    snapshot = current["rfq_intelligence_snapshot"].content
    assert snapshot["availability_matrix"]["parser_report"] == "available"
    assert snapshot["availability_matrix"]["workbook_review_report"] == "not_ready"
    assert snapshot["workbook_panel"]["parser_status"] == "failed"


def test_review_suppresses_placeholder_title_mismatch_findings(db_session):
    datasource = ArtifactDatasource(db_session)
    review_service = ReviewService(datasource=datasource)
    rfq_id = uuid.uuid4()
    event_meta = {
        "event_id": "evt-review-placeholder",
        "event_type": "workbook.uploaded",
    }

    intake_artifact = datasource.create_new_artifact_version(
        rfq_id=rfq_id,
        artifact_type="rfq_intake_profile",
        content={
            "canonical_project_profile": {
                "project_title": "RFQ context pending manager enrichment",
            }
        },
        status="partial",
        source_event_type="rfq.created",
        source_event_id="evt-intake-placeholder",
    )
    workbook_profile_artifact = datasource.create_new_artifact_version(
        rfq_id=rfq_id,
        artifact_type="workbook_profile",
        content={
            "workbook_structure": {},
            "canonical_estimate_profile": {
                "detected_identifiers": {
                    "project_title": "Workbook context pending manager enrichment",
                }
            },
        },
        status="partial",
        source_event_type="workbook.uploaded",
        source_event_id="evt-workbook-placeholder",
    )

    review_artifact = review_service.build_workbook_review_report(
        rfq_id=str(rfq_id),
        workbook_profile_artifact=workbook_profile_artifact,
        event_meta=event_meta,
        intake_artifact=intake_artifact,
        commit=False,
    )

    assert review_artifact.content["intake_vs_workbook_findings"] == []


def test_review_emits_real_title_mismatch_when_both_values_are_meaningful(db_session):
    datasource = ArtifactDatasource(db_session)
    review_service = ReviewService(datasource=datasource)
    rfq_id = uuid.uuid4()
    event_meta = {
        "event_id": "evt-review-real-mismatch",
        "event_type": "workbook.uploaded",
    }

    intake_artifact = datasource.create_new_artifact_version(
        rfq_id=rfq_id,
        artifact_type="rfq_intake_profile",
        content={
            "canonical_project_profile": {
                "project_title": "GHI Water Upgrade Lot A",
            }
        },
        status="partial",
        source_event_type="rfq.created",
        source_event_id="evt-intake-real",
    )
    workbook_profile_artifact = datasource.create_new_artifact_version(
        rfq_id=rfq_id,
        artifact_type="workbook_profile",
        content={
            "workbook_structure": {},
            "canonical_estimate_profile": {
                "detected_identifiers": {
                    "project_title": "GHI Water Upgrade Lot B",
                }
            },
        },
        status="partial",
        source_event_type="workbook.uploaded",
        source_event_id="evt-workbook-real",
    )

    review_artifact = review_service.build_workbook_review_report(
        rfq_id=str(rfq_id),
        workbook_profile_artifact=workbook_profile_artifact,
        event_meta=event_meta,
        intake_artifact=intake_artifact,
        commit=False,
    )

    findings = review_artifact.content["intake_vs_workbook_findings"]
    assert len(findings) == 1
    assert findings[0]["finding_id"] == "intake_workbook_project_label_diff"
    assert findings[0]["status"] == "active"
