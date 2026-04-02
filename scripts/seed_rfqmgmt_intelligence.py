from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.connectors.manager_connector import ManagerConnector
from src.database import SessionLocal
from src.datasources.artifact_datasource import ArtifactDatasource
from src.models.artifact import Artifact
from src.services.analytical_record_service import AnalyticalRecordService
from src.services.briefing_service import BriefingService
from src.services.intake_service import IntakeService
from src.services.review_service import ReviewService
from src.services.snapshot_service import SnapshotService


INTELLIGENCE_MANIFEST_VERSION = "rfqmgmt_intelligence_scenarios_v1"
GOLDEN_SCENARIO_KEY = "RFQ-06"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def _event_meta(scenario_key: str, suffix: str, event_type: str, emitted_at: datetime) -> dict[str, str]:
    return {
        "event_id": f"scenario-seed:{scenario_key}:{suffix}",
        "event_type": event_type,
        "emitted_at": emitted_at.isoformat(),
    }


def _scenario_seed_prefix(scenario_key: str) -> str:
    return f"scenario-seed:{scenario_key}:"


def _manager_context(entry: dict[str, Any], *, source_reference: str | None = None) -> dict[str, Any]:
    reference = source_reference or f"scenario://{entry['scenario_key'].lower()}/source-package.zip"
    return {
        "rfq_id": entry["rfq_id"],
        "rfq_code": entry.get("rfq_code"),
        "client_name": entry.get("client"),
        "project_title": entry.get("name"),
        "source_package_refs": [
            {
                "reference": reference,
                "display_name": f"{entry['scenario_key'].lower()}-source-package.zip",
            }
        ],
        "created_at": entry.get("created_at"),
    }


def _parsed_intake_content(entry: dict[str, Any], event_meta: dict[str, str]) -> dict[str, Any]:
    generated_at = event_meta["emitted_at"]
    client_name = entry.get("client")
    project_title = entry.get("name")
    scenario_key = entry["scenario_key"]
    review_flags = ["Deterministic package findings should be reviewed by the bid team."]
    tag_numbers = [f"{scenario_key}-TAG-01", f"{scenario_key}-TAG-02"]
    design_codes = ["ASME VIII", "API 610"]
    standards_count = {"samss": 3, "saes": 2, "saep": 1, "std_dwg": 1}

    return {
        "artifact_meta": {
            "artifact_type": "rfq_intake_profile",
            "slice": "rfq.created_package_parsed_v1",
            "generated_at": generated_at,
            "source_event_id": event_meta["event_id"],
            "source_event_type": event_meta["event_type"],
            "parser_version": "package-parser-v1.0",
        },
        "source_package": {
            "references": _manager_context(entry)["source_package_refs"],
            "primary_reference": _manager_context(entry)["source_package_refs"][0]["reference"],
            "visibility_level": "parsed",
            "input_type": "scenario_seed",
            "package_root_name": f"{scenario_key}_source_package",
        },
        "package_identity": {
            "mr_number": f"{scenario_key}-MR-001",
            "mr_number_short": f"{scenario_key}-MR",
            "revision": "00",
            "material_description": f"{project_title} packaged materials",
            "project_code": scenario_key,
            "mr_number_mismatches": [],
        },
        "package_structure": {
            "status": "parsed",
            "total_files": 12,
            "total_files_raw": 14,
            "system_file_count": 2,
            "total_folders": 6,
            "total_size_bytes": 2_450_000,
            "numbered_sections_found": 6,
            "missing_sections": ["QAQC requirements"],
            "extra_unnumbered_sections": [],
            "mr_index_coverage": "6/6",
            "file_extension_summary": {"pdf": 6, "xlsx": 2, "docx": 2, "zip": 1, "txt": 1},
            "section_registry": {
                "numbered_section_count": 6,
                "missing_canonical_sections": ["QAQC requirements"],
                "unmatched_folders": [],
                "total_mr_index_count": 6,
            },
        },
        "document_understanding": {
            "status": "partial_deterministic",
            "summary": "Deterministic package extraction prepared from seeded scenario content.",
            "bom_profile": {
                "tag_numbers_found": tag_numbers,
                "design_codes_found": design_codes,
                "nine_com_codes_found": ["100001", "100002"],
                "locations_found": [entry.get("country")],
            },
            "rvl_profile": {
                "total_vendors": 4,
                "nine_com_codes": ["100001", "100002"],
            },
            "standards_profile": {
                "samss_count": standards_count["samss"],
                "saes_count": standards_count["saes"],
                "saep_count": standards_count["saep"],
                "std_dwg_count": standards_count["std_dwg"],
            },
            "sa175_profile": {"total_count": 1},
            "compliance_profile": {"nine_com": "100001"},
            "deviation_profile": {"present": True},
        },
        "canonical_project_profile": {
            "rfq_id": entry["rfq_id"],
            "rfq_code": entry.get("rfq_code"),
            "client_name": client_name,
            "project_title": project_title,
            "created_at": entry.get("created_at"),
            "material_description": f"{project_title} packaged materials",
            "tag_numbers": tag_numbers,
            "design_codes": design_codes,
            "nine_com_codes": ["100001", "100002"],
            "location": entry.get("country"),
            "vendor_count": 4,
            "standards_count": standards_count,
        },
        "field_evidence": [
            {
                "field": "project_title",
                "value": project_title,
                "source": "scenario_seed",
                "method": "deterministic",
                "confidence": "high",
            },
            {
                "field": "client_name",
                "value": client_name,
                "source": "scenario_seed",
                "method": "deterministic",
                "confidence": "high",
            },
        ],
        "quality_and_gaps": {
            "status": "partial",
            "known_data_points": [
                "package identity",
                "BOM line items",
                "RVL vendors",
                "standards list",
            ],
            "gaps": [
                "semantic PDF understanding",
                "deep QAQC extraction",
                "workbook comparison",
            ],
            "review_flags": review_flags,
        },
        "downstream_readiness": {
            "briefing_ready": True,
            "workbook_comparison_ready": True,
            "historical_matching_ready": False,
            "requires_human_review": True,
        },
        "parser_report_status": "parsed_with_warnings",
    }


def _workbook_source(entry: dict[str, Any], uploaded_at: datetime) -> dict[str, Any]:
    return {
        "workbook_ref": f"scenario://{entry['scenario_key'].lower()}/estimation-workbook.xls",
        "workbook_filename": f"{entry['scenario_key'].lower()}_estimation_workbook.xls",
        "uploaded_at": uploaded_at.isoformat(),
        "file_extension": "xls",
        "local_workbook_path": None,
    }


def _workbook_profile_content(
    entry: dict[str, Any],
    event_meta: dict[str, str],
    *,
    parser_status: str,
    missing_sheets: list[str],
    extra_sheets: list[str],
) -> dict[str, Any]:
    workbook_source = _workbook_source(entry, _parse_timestamp(event_meta["emitted_at"]) or _utc_now())
    return {
        "artifact_meta": {
            "artifact_type": "workbook_profile",
            "slice": "workbook.uploaded_vertical_slice_v1",
            "generated_at": event_meta["emitted_at"],
            "source_event_id": event_meta["event_id"],
            "source_event_type": event_meta["event_type"],
        },
        "workbook_source": workbook_source,
        "template_name": "ghi_estimation_workbook_v1",
        "parser_version": "workbook-parser-v2.1",
        "template_match": parser_status != "failed",
        "template_recognition": {
            "template_family": "ghi_estimation_workbook_v1",
            "sheet_count_found": 5 if parser_status != "failed" else 2,
            "expected_sheet_count": 5,
            "recognition_status": "partial" if parser_status != "failed" else "failed",
            "recognition_notes": "Scenario-seeded workbook recognition state.",
            "parser_version": "workbook-parser-v2.1",
        },
        "workbook_structure": {
            "sheet_names": ["General", "Bid S", "Top Sheet", "Cash Flow", "Mat Breakup"],
            "expected_sheet_count": 5,
            "sheet_count_found": 5 - len(missing_sheets) + len(extra_sheets),
            "missing_sheets": missing_sheets,
            "extra_sheets": extra_sheets,
        },
        "canonical_estimate_profile": {
            "rfq_id": entry["rfq_id"],
            "detected_identifiers": {
                "rfq_code": entry.get("rfq_code"),
                "project_title": entry.get("name"),
                "client_name": entry.get("client"),
                "inquiry_no": f"INQ-{entry['scenario_key']}",
            },
        },
        "workbook_profile": {
            "rfq_identity": {
                "project_name": entry.get("name"),
                "client_name": entry.get("client"),
                "inquiry_no": f"INQ-{entry['scenario_key']}",
            },
            "general_summary": {
                "currency": "SAR",
                "estimate_owner": entry.get("owner"),
            },
        },
        "pairing_validation": {
            "pairing_status": "not_assessed",
            "notes": "Scenario-seeded workbook intentionally avoids assuming source package linkage.",
            "external_linkage_required": True,
        },
        "downstream_readiness": {
            "review_report_ready": parser_status != "failed",
            "benchmark_ready": False,
            "similarity_ready": False,
            "requires_human_review": True,
        },
        "parser_report_status": parser_status,
    }


def _cost_breakdown_content(entry: dict[str, Any], event_meta: dict[str, str], *, parser_status: str) -> dict[str, Any]:
    return {
        "artifact_meta": {
            "artifact_type": "cost_breakdown_profile",
            "slice": "workbook.uploaded_vertical_slice_v1",
            "generated_at": event_meta["emitted_at"],
            "source_event_id": event_meta["event_id"],
            "source_event_type": event_meta["event_type"],
        },
        "workbook_source": _workbook_source(entry, _parse_timestamp(event_meta["emitted_at"]) or _utc_now()),
        "template_name": "ghi_estimation_workbook_v1",
        "parser_version": "workbook-parser-v2.1",
        "template_match": parser_status != "failed",
        "cost_breakdown_profile": {
            "bid_summary_lines": [
                {"label": "Equipment", "value": 520_000},
                {"label": "Engineering", "value": 92_000},
                {"label": "Commissioning", "value": 38_000},
            ],
            "top_sheet_lines": [
                {"label": "Subtotal", "value": 650_000},
                {"label": "Markup", "value": 97_500},
            ],
        },
        "parser_report_status": parser_status,
    }


def _parser_report_content(
    entry: dict[str, Any],
    event_meta: dict[str, str],
    *,
    parser_status: str,
    missing_sheets: list[str],
) -> dict[str, Any]:
    parsed_at = event_meta["emitted_at"]
    if parser_status == "failed":
        parser_report = {
            "status": "failed",
            "failure": {
                "code": "WORKBOOK_TEMPLATE_MISMATCH",
                "message": "Scenario-seeded failure: workbook structure is incomplete for reliable parsing.",
            },
        }
    else:
        parser_report = {
            "status": parser_status,
            "parsed_sheets": ["General", "Bid S", "Top Sheet"],
            "skipped_sheets": missing_sheets,
            "warnings": [
                {
                    "code": "WORKBOOK_REVIEW_REQUIRED",
                    "severity": "warning",
                    "sheet_name": "Top Sheet",
                    "message": "Workbook slice is usable but still requires human review.",
                }
            ],
            "errors": [],
            "anchor_checks": [],
            "cross_checks": [],
            "sheet_reports": {
                "general": {"sheet_name": "General", "status": "parsed_with_warnings"},
                "bid_s": {"sheet_name": "Bid S", "status": "parsed_with_warnings"},
                "top_sheet": {"sheet_name": "Top Sheet", "status": "parsed_with_warnings"},
            },
        }

    return {
        "artifact_meta": {
            "artifact_type": "parser_report",
            "slice": "workbook.uploaded_vertical_slice_v1",
            "generated_at": event_meta["emitted_at"],
            "source_event_id": event_meta["event_id"],
            "source_event_type": event_meta["event_type"],
        },
        "workbook_source": _workbook_source(entry, _parse_timestamp(event_meta["emitted_at"]) or _utc_now()),
        "template_name": "ghi_estimation_workbook_v1",
        "parser_version": "workbook-parser-v2.1",
        "template_match": parser_status != "failed",
        "parsed_at": parsed_at,
        "parser_report": parser_report,
    }


def _set_artifact_time(artifact: Artifact, timestamp: datetime) -> None:
    artifact.created_at = timestamp
    artifact.updated_at = timestamp
    content = dict(artifact.content or {})
    artifact_meta = dict(content.get("artifact_meta") or {})
    if artifact_meta:
        artifact_meta["generated_at"] = timestamp.isoformat()
        content["artifact_meta"] = artifact_meta
    if "parsed_at" in content:
        content["parsed_at"] = timestamp.isoformat()
    workbook_source = dict(content.get("workbook_source") or {})
    if workbook_source.get("uploaded_at"):
        workbook_source["uploaded_at"] = timestamp.isoformat()
        content["workbook_source"] = workbook_source
    artifact.content = content


def _stamp_sequence(artifacts: list[Artifact], final_updated_at: datetime) -> None:
    if not artifacts:
        return
    start = final_updated_at - timedelta(minutes=5 * (len(artifacts) - 1))
    for index, artifact in enumerate(artifacts):
        _set_artifact_time(artifact, start + timedelta(minutes=5 * index))


def _profile_final_timestamp(entry: dict[str, Any], *, stale: bool) -> datetime:
    manager_updated = _parse_timestamp(entry.get("updated_at")) or _utc_now()
    manager_created = _parse_timestamp(entry.get("created_at")) or (manager_updated - timedelta(days=2))
    if stale:
        final = manager_updated - timedelta(days=3)
        floor = manager_created + timedelta(hours=1)
        return final if final > floor else floor
    if manager_updated < manager_created:
        return manager_created
    return manager_updated


def _already_seeded(datasource: ArtifactDatasource, rfq_id: UUID, scenario_key: str, expected_types: list[str]) -> bool:
    current = datasource.list_current_artifacts_for_rfq(rfq_id)
    prefix = _scenario_seed_prefix(scenario_key)
    return bool(expected_types) and all(
        current.get(artifact_type) is not None
        and (current[artifact_type].source_event_id or "").startswith(prefix)
        for artifact_type in expected_types
    )


def _create_direct_artifact(
    datasource: ArtifactDatasource,
    *,
    rfq_id: UUID,
    artifact_type: str,
    content: dict[str, Any] | None,
    status: str,
    event_meta: dict[str, str],
):
    return datasource.create_new_artifact_version(
        rfq_id=rfq_id,
        artifact_type=artifact_type,
        content=content,
        status=status,
        source_event_type=event_meta["event_type"],
        source_event_id=event_meta["event_id"],
    )


def _seed_initial_partial_slice(
    datasource: ArtifactDatasource,
    intake_service: IntakeService,
    briefing_service: BriefingService,
    analytical_service: AnalyticalRecordService,
    snapshot_service: SnapshotService,
    entry: dict[str, Any],
    *,
    parsed_intake: bool,
) -> list[Artifact]:
    emitted_at = (_parse_timestamp(entry.get("created_at")) or _utc_now()) + timedelta(hours=2)
    event_meta = _event_meta(entry["scenario_key"], "rfq-created", "rfq.created", emitted_at)
    rfq_context = _manager_context(entry)

    if parsed_intake:
        intake = _create_direct_artifact(
            datasource,
            rfq_id=UUID(entry["rfq_id"]),
            artifact_type="rfq_intake_profile",
            content=_parsed_intake_content(entry, event_meta),
            status="partial",
            event_meta=event_meta,
        )
    else:
        intake = intake_service.build_intake_profile_from_rfq_created(
            rfq_context=rfq_context,
            event_meta=event_meta,
            commit=False,
        )

    briefing = briefing_service.build_briefing_from_intake(
        intake_artifact=intake,
        event_meta=event_meta,
        commit=False,
    )
    analytical = analytical_service.build_initial_analytical_record(
        rfq_context=rfq_context,
        intake_artifact=intake,
        event_meta=event_meta,
        commit=False,
    )
    snapshot = snapshot_service.rebuild_snapshot_for_rfq(
        rfq_id=entry["rfq_id"],
        source_event_meta=event_meta,
        commit=False,
    )
    return [intake, briefing, analytical, snapshot]


def _seed_workbook_slice(
    datasource: ArtifactDatasource,
    review_service: ReviewService,
    analytical_service: AnalyticalRecordService,
    snapshot_service: SnapshotService,
    entry: dict[str, Any],
    *,
    parser_status: str,
    missing_sheets: list[str],
    extra_sheets: list[str],
    with_review: bool,
) -> list[Artifact]:
    emitted_at = (_parse_timestamp(entry.get("updated_at")) or _utc_now()) - timedelta(hours=6)
    event_meta = _event_meta(entry["scenario_key"], "workbook-uploaded", "workbook.uploaded", emitted_at)
    rfq_uuid = UUID(entry["rfq_id"])

    workbook_profile = _create_direct_artifact(
        datasource,
        rfq_id=rfq_uuid,
        artifact_type="workbook_profile",
        content=_workbook_profile_content(
            entry,
            event_meta,
            parser_status=parser_status,
            missing_sheets=missing_sheets,
            extra_sheets=extra_sheets,
        ),
        status="failed" if parser_status == "failed" else "partial",
        event_meta=event_meta,
    )
    cost_breakdown = _create_direct_artifact(
        datasource,
        rfq_id=rfq_uuid,
        artifact_type="cost_breakdown_profile",
        content=_cost_breakdown_content(entry, event_meta, parser_status=parser_status),
        status="failed" if parser_status == "failed" else "partial",
        event_meta=event_meta,
    )
    parser_report = _create_direct_artifact(
        datasource,
        rfq_id=rfq_uuid,
        artifact_type="parser_report",
        content=_parser_report_content(
            entry,
            event_meta,
            parser_status=parser_status,
            missing_sheets=missing_sheets,
        ),
        status="failed" if parser_status == "failed" else "partial",
        event_meta=event_meta,
    )

    artifacts = [workbook_profile, cost_breakdown, parser_report]

    if with_review:
        intake_artifact = datasource.get_current_artifact(rfq_uuid, "rfq_intake_profile")
        briefing_artifact = datasource.get_current_artifact(rfq_uuid, "intelligence_briefing")
        review = review_service.build_workbook_review_report(
            rfq_id=entry["rfq_id"],
            workbook_profile_artifact=workbook_profile,
            event_meta=event_meta,
            intake_artifact=intake_artifact,
            briefing_artifact=briefing_artifact,
            commit=False,
        )
        analytical = analytical_service.enrich_analytical_record_from_workbook(
            rfq_id=entry["rfq_id"],
            workbook_profile_artifact=workbook_profile,
            workbook_review_artifact=review,
            event_meta=event_meta,
            commit=False,
        )
        artifacts.extend([review, analytical])

    snapshot = snapshot_service.rebuild_snapshot_for_rfq(
        rfq_id=entry["rfq_id"],
        source_event_meta=event_meta,
        commit=False,
    )
    artifacts.append(snapshot)
    return artifacts


def _seed_failed_briefing(
    datasource: ArtifactDatasource,
    intake_service: IntakeService,
    snapshot_service: SnapshotService,
    entry: dict[str, Any],
) -> list[Artifact]:
    emitted_at = (_parse_timestamp(entry.get("created_at")) or _utc_now()) + timedelta(hours=3)
    rfq_context = _manager_context(entry)
    intake_event = _event_meta(entry["scenario_key"], "rfq-created", "rfq.created", emitted_at)
    intake = intake_service.build_intake_profile_from_rfq_created(
        rfq_context=rfq_context,
        event_meta=intake_event,
        commit=False,
    )

    briefing_event = _event_meta(entry["scenario_key"], "briefing-failed", "rfq.created", emitted_at + timedelta(minutes=5))
    failed_briefing = _create_direct_artifact(
        datasource,
        rfq_id=UUID(entry["rfq_id"]),
        artifact_type="intelligence_briefing",
        content={
            "artifact_meta": {
                "artifact_type": "intelligence_briefing",
                "slice": "rfq.created_vertical_slice_v1",
                "generated_at": briefing_event["emitted_at"],
                "source_event_id": briefing_event["event_id"],
                "source_event_type": briefing_event["event_type"],
            },
            "executive_summary": "Briefing generation failed during scenario seeding.",
            "what_is_known": {
                "rfq_id": entry["rfq_id"],
                "rfq_code": entry.get("rfq_code"),
                "project_title": entry.get("name"),
                "client_name": entry.get("client"),
            },
            "what_is_missing": ["Briefing generation failed before full intelligence assembly."],
            "section_availability": {
                "document_understanding": "failed",
                "compliance_risk": "failed",
                "workbook_comparison": "not_ready",
                "benchmarking": "insufficient_historical_base",
                "similarity": "insufficient_historical_base",
                "cost_envelope": "not_ready",
            },
            "cold_start_limitations": ["Scenario-seeded briefing failure."],
            "recommended_next_actions": ["Re-run briefing generation after checking intake quality."],
            "review_posture": "supportive_review",
        },
        status="failed",
        event_meta=briefing_event,
    )
    snapshot = snapshot_service.rebuild_snapshot_for_rfq(
        rfq_id=entry["rfq_id"],
        source_event_meta=briefing_event,
        commit=False,
    )
    return [intake, failed_briefing, snapshot]


def _seed_pending_artifact(datasource: ArtifactDatasource, entry: dict[str, Any]) -> list[Artifact]:
    emitted_at = (_parse_timestamp(entry.get("created_at")) or _utc_now()) + timedelta(hours=1)
    event_meta = _event_meta(entry["scenario_key"], "briefing-pending", "rfq.created", emitted_at)
    pending = _create_direct_artifact(
        datasource,
        rfq_id=UUID(entry["rfq_id"]),
        artifact_type="intelligence_briefing",
        content={
            "artifact_meta": {
                "artifact_type": "intelligence_briefing",
                "slice": "rfq.created_vertical_slice_v1",
                "generated_at": event_meta["emitted_at"],
                "source_event_id": event_meta["event_id"],
                "source_event_type": event_meta["event_type"],
            },
            "executive_summary": "Briefing generation has been queued but is not available yet.",
            "section_availability": {
                "document_understanding": "pending",
                "compliance_risk": "pending",
                "workbook_comparison": "not_ready",
                "benchmarking": "insufficient_historical_base",
                "similarity": "insufficient_historical_base",
                "cost_envelope": "not_ready",
            },
            "recommended_next_actions": ["Wait for briefing generation to complete."],
            "review_posture": "supportive_review",
        },
        status="pending",
        event_meta=event_meta,
    )
    return [pending]


def _expected_artifact_types(intelligence_profile: str) -> list[str]:
    if intelligence_profile in {"early_partial", "stale_partial", "thin_partial_stale"}:
        return [
            "rfq_intake_profile",
            "intelligence_briefing",
            "rfq_analytical_record",
            "rfq_intelligence_snapshot",
        ]
    if intelligence_profile in {"mature_partial", "mature_partial_stale_award"}:
        return [
            "rfq_intake_profile",
            "intelligence_briefing",
            "workbook_profile",
            "cost_breakdown_profile",
            "parser_report",
            "workbook_review_report",
            "rfq_analytical_record",
            "rfq_intelligence_snapshot",
        ]
    if intelligence_profile == "failed_workbook":
        return [
            "rfq_intake_profile",
            "intelligence_briefing",
            "workbook_profile",
            "cost_breakdown_profile",
            "parser_report",
            "rfq_analytical_record",
            "rfq_intelligence_snapshot",
        ]
    if intelligence_profile == "failed_briefing":
        return ["rfq_intake_profile", "intelligence_briefing", "rfq_intelligence_snapshot"]
    if intelligence_profile == "pending_artifact":
        return ["intelligence_briefing"]
    return []


def seed_intelligence_from_manifest(session, manager_manifest: dict[str, Any]) -> dict[str, Any]:
    datasource = ArtifactDatasource(session)
    connector = ManagerConnector(base_url="http://rfq-manager-not-used-for-scenario-seeding")
    intake_service = IntakeService(datasource=datasource, connector=connector)
    briefing_service = BriefingService(datasource=datasource)
    analytical_service = AnalyticalRecordService(datasource=datasource)
    review_service = ReviewService(datasource=datasource)
    snapshot_service = SnapshotService(datasource=datasource)

    seeded: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for entry in manager_manifest.get("scenarios", []):
        scenario_key = entry["scenario_key"]
        profile = entry.get("intelligence_profile", "none")
        if scenario_key == GOLDEN_SCENARIO_KEY or entry.get("manual_only"):
            skipped.append({"scenario_key": scenario_key, "reason": "manual_only"})
            continue
        if profile in {"none", "manual_golden"}:
            skipped.append({"scenario_key": scenario_key, "reason": "no_intelligence_seed_required"})
            continue

        rfq_uuid = UUID(entry["rfq_id"])
        expected_types = _expected_artifact_types(profile)
        if _already_seeded(datasource, rfq_uuid, scenario_key, expected_types):
            skipped.append({"scenario_key": scenario_key, "reason": "already_seeded"})
            continue

        artifacts: list[Artifact]
        if profile == "early_partial":
            artifacts = _seed_initial_partial_slice(
                datasource,
                intake_service,
                briefing_service,
                analytical_service,
                snapshot_service,
                entry,
                parsed_intake=False,
            )
            _stamp_sequence(artifacts, _profile_final_timestamp(entry, stale=False))
        elif profile == "stale_partial":
            artifacts = _seed_initial_partial_slice(
                datasource,
                intake_service,
                briefing_service,
                analytical_service,
                snapshot_service,
                entry,
                parsed_intake=False,
            )
            _stamp_sequence(artifacts, _profile_final_timestamp(entry, stale=True))
        elif profile == "thin_partial_stale":
            artifacts = _seed_initial_partial_slice(
                datasource,
                intake_service,
                briefing_service,
                analytical_service,
                snapshot_service,
                entry,
                parsed_intake=False,
            )
            _stamp_sequence(artifacts, _profile_final_timestamp(entry, stale=True))
        elif profile == "mature_partial":
            artifacts = _seed_initial_partial_slice(
                datasource,
                intake_service,
                briefing_service,
                analytical_service,
                snapshot_service,
                entry,
                parsed_intake=True,
            )
            artifacts.extend(
                _seed_workbook_slice(
                    datasource,
                    review_service,
                    analytical_service,
                    snapshot_service,
                    entry,
                    parser_status="parsed_with_warnings",
                    missing_sheets=["Mat Breakup"],
                    extra_sheets=[],
                    with_review=True,
                )
            )
            _stamp_sequence(artifacts, _profile_final_timestamp(entry, stale=False))
        elif profile == "mature_partial_stale_award":
            artifacts = _seed_initial_partial_slice(
                datasource,
                intake_service,
                briefing_service,
                analytical_service,
                snapshot_service,
                entry,
                parsed_intake=True,
            )
            artifacts.extend(
                _seed_workbook_slice(
                    datasource,
                    review_service,
                    analytical_service,
                    snapshot_service,
                    entry,
                    parser_status="parsed_with_warnings",
                    missing_sheets=["Mat Breakup"],
                    extra_sheets=[],
                    with_review=True,
                )
            )
            _stamp_sequence(artifacts, _profile_final_timestamp(entry, stale=True))
        elif profile == "failed_workbook":
            artifacts = _seed_initial_partial_slice(
                datasource,
                intake_service,
                briefing_service,
                analytical_service,
                snapshot_service,
                entry,
                parsed_intake=False,
            )
            artifacts.extend(
                _seed_workbook_slice(
                    datasource,
                    review_service,
                    analytical_service,
                    snapshot_service,
                    entry,
                    parser_status="failed",
                    missing_sheets=["Bid S", "Top Sheet"],
                    extra_sheets=[],
                    with_review=False,
                )
            )
            _stamp_sequence(artifacts, _profile_final_timestamp(entry, stale=False))
        elif profile == "failed_briefing":
            artifacts = _seed_failed_briefing(
                datasource,
                intake_service,
                snapshot_service,
                entry,
            )
            _stamp_sequence(artifacts, _profile_final_timestamp(entry, stale=False))
        elif profile == "pending_artifact":
            artifacts = _seed_pending_artifact(datasource, entry)
            _stamp_sequence(artifacts, _profile_final_timestamp(entry, stale=False))
        else:
            skipped.append({"scenario_key": scenario_key, "reason": f"unsupported_profile:{profile}"})
            continue

        session.commit()
        seeded.append(
            {
                "scenario_key": scenario_key,
                "rfq_id": entry["rfq_id"],
                "intelligence_profile": profile,
                "artifact_types": [artifact.artifact_type for artifact in artifacts],
            }
        )

    return {
        "manifest_version": INTELLIGENCE_MANIFEST_VERSION,
        "generated_at": _utc_now().isoformat(),
        "golden_reserved_scenario": GOLDEN_SCENARIO_KEY,
        "seeded": seeded,
        "skipped": skipped,
    }


def load_manager_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_intelligence_manifest(output_path: Path, manifest: dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _cli_path(value: str) -> Path:
    # Normalize Windows-style separators so container execution on Linux
    # still resolves mounted paths like /app/seed_outputs correctly.
    return Path(value.replace("\\", "/"))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seed direct intelligence artifacts from the RFQMGMT manager scenario manifest.",
    )
    parser.add_argument(
        "--manager-manifest",
        required=True,
        help="Path to the manager scenario manifest JSON emitted by seed_rfqmgmt_scenarios.py.",
    )
    parser.add_argument(
        "--output-json",
        default=str(Path("seed_outputs") / "rfqmgmt_intelligence_manifest.json"),
        help="Path to write the intelligence seeding result JSON.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    manager_manifest_path = _cli_path(args.manager_manifest)
    manager_manifest = load_manager_manifest(manager_manifest_path)

    session = SessionLocal()
    try:
        result = seed_intelligence_from_manifest(session, manager_manifest)
    finally:
        session.close()

    output_path = _cli_path(args.output_json)
    payload = {
        **result,
        "manager_manifest_path": manager_manifest_path.as_posix(),
    }
    write_intelligence_manifest(output_path, payload)

    print(
        json.dumps(
            {
                "manager_manifest_path": manager_manifest_path.as_posix(),
                "output_json": output_path.as_posix(),
                "seeded_scenarios": [item["scenario_key"] for item in result["seeded"]],
                "skipped_scenarios": result["skipped"],
                "golden_reserved_scenario": GOLDEN_SCENARIO_KEY,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
