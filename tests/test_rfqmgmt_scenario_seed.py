from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from scripts.seed_rfqmgmt_intelligence import (
    GOLDEN_SCENARIO_KEY,
    seed_intelligence_from_manifest,
)
from src.datasources.artifact_datasource import ArtifactDatasource


def _manifest_entry(
    scenario_key: str,
    intelligence_profile: str,
    *,
    manual_only: bool = False,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> dict:
    rfq_id = str(uuid.uuid4())
    created = created_at or datetime.now(timezone.utc) - timedelta(days=12)
    updated = updated_at or datetime.now(timezone.utc) - timedelta(days=1)
    return {
        "scenario_key": scenario_key,
        "batch": "must-have",
        "manual_only": manual_only,
        "intelligence_profile": intelligence_profile,
        "rfq_id": rfq_id,
        "rfq_code": f"IF-{scenario_key[-2:]}01",
        "name": f"{scenario_key} Scenario RFQ",
        "client": "Scenario Client",
        "industry": "Water",
        "country": "Saudi Arabia",
        "priority": "normal",
        "status": "In preparation",
        "workflow_code": "GHI-LONG",
        "current_stage_id": None,
        "current_stage_name": "RFQ received",
        "deadline": (created.date() + timedelta(days=30)).isoformat(),
        "owner": "Scenario Owner",
        "description": f"[SCENARIO:{scenario_key}] test seed",
        "outcome_reason": None,
        "created_at": created.isoformat(),
        "updated_at": updated.isoformat(),
    }


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def test_seed_intelligence_skips_manual_and_none_profiles(db_session):
    manifest = {
        "scenarios": [
            _manifest_entry("RFQ-01", "none"),
            _manifest_entry(GOLDEN_SCENARIO_KEY, "manual_golden", manual_only=True),
            _manifest_entry("RFQ-02", "early_partial"),
        ]
    }

    result = seed_intelligence_from_manifest(db_session, manifest)

    assert [item["scenario_key"] for item in result["seeded"]] == ["RFQ-02"]
    assert {"scenario_key": "RFQ-01", "reason": "no_intelligence_seed_required"} in result["skipped"]
    assert {"scenario_key": GOLDEN_SCENARIO_KEY, "reason": "manual_only"} in result["skipped"]


def test_mature_partial_seed_creates_route_backing_artifacts(client, db_session):
    entry = _manifest_entry("RFQ-09", "mature_partial")
    manifest = {"scenarios": [entry]}

    seed_intelligence_from_manifest(db_session, manifest)

    datasource = ArtifactDatasource(db_session)
    current = datasource.list_current_artifacts_for_rfq(uuid.UUID(entry["rfq_id"]))

    assert set(current) == {
        "rfq_intake_profile",
        "intelligence_briefing",
        "workbook_profile",
        "cost_breakdown_profile",
        "parser_report",
        "workbook_review_report",
        "rfq_analytical_record",
        "rfq_intelligence_snapshot",
    }
    assert current["rfq_intelligence_snapshot"].content["availability_matrix"]["workbook_profile"] == "available"
    assert current["rfq_intelligence_snapshot"].content["review_panel"]["status"] == "partial"

    workbook_profile = client.get(f"/intelligence/v1/rfqs/{entry['rfq_id']}/workbook-profile")
    workbook_review = client.get(f"/intelligence/v1/rfqs/{entry['rfq_id']}/workbook-review")
    snapshot = client.get(f"/intelligence/v1/rfqs/{entry['rfq_id']}/snapshot")

    assert workbook_profile.status_code == 200
    assert workbook_review.status_code == 200
    assert snapshot.status_code == 200


def test_stale_partial_seed_backdates_intelligence_relative_to_manager_update(db_session):
    manager_updated_at = datetime.now(timezone.utc) - timedelta(hours=4)
    entry = _manifest_entry(
        "RFQ-04",
        "stale_partial",
        created_at=manager_updated_at - timedelta(days=5),
        updated_at=manager_updated_at,
    )
    manifest = {"scenarios": [entry]}

    seed_intelligence_from_manifest(db_session, manifest)

    datasource = ArtifactDatasource(db_session)
    snapshot = datasource.get_current_artifact(uuid.UUID(entry["rfq_id"]), "rfq_intelligence_snapshot")

    assert snapshot is not None
    assert _as_utc(snapshot.updated_at) < manager_updated_at
    assert (snapshot.source_event_id or "").startswith("scenario-seed:RFQ-04:")


def test_failed_workbook_seed_keeps_review_unavailable_and_parser_failed(db_session):
    entry = _manifest_entry("RFQ-07", "failed_workbook")
    manifest = {"scenarios": [entry]}

    seed_intelligence_from_manifest(db_session, manifest)

    datasource = ArtifactDatasource(db_session)
    current = datasource.list_current_artifacts_for_rfq(uuid.UUID(entry["rfq_id"]))

    assert current["parser_report"].status == "failed"
    assert "workbook_review_report" not in current
    assert current["rfq_intelligence_snapshot"].content["workbook_panel"]["parser_status"] == "failed"
    assert current["rfq_intelligence_snapshot"].content["availability_matrix"]["workbook_review_report"] == "not_ready"
