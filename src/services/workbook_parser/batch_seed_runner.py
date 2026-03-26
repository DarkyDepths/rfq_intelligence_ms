from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5

from src.services.workbook_parser import parse_workbook_deterministic


HISTORICAL_BATCH_SEED_EVENT_TYPE = "historical.batch_seed.workbook_uploaded"
HISTORICAL_BATCH_SEED_RUN_TYPE = "historical_workbook_batch_seed"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _is_invalid_workbook_path(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return True
    suffix = path.suffix.lower()
    return suffix not in {".xls", ".xlsx", ".xlsm"}


def _compute_overall_status(parsed_ok: int, parsed_with_warnings: int, failed: int, skipped_invalid: int) -> str:
    if failed == 0 and skipped_invalid == 0:
        return "completed"
    if parsed_ok == 0 and parsed_with_warnings == 0 and (failed > 0 or skipped_invalid > 0):
        return "failed"
    return "completed_with_failures"


def _build_samples(results: list[dict], sample_limit: int = 5) -> tuple[list[dict], list[dict]]:
    failure_samples = []
    warning_samples = []

    for row in results:
        if row.get("status") == "failed" and len(failure_samples) < sample_limit:
            error = row.get("error") or {}
            failure_samples.append(
                {
                    "workbook_file_name": row.get("workbook_file_name"),
                    "code": error.get("code"),
                    "message": error.get("message"),
                }
            )
        if row.get("status") == "parsed_with_warnings" and len(warning_samples) < sample_limit:
            warning_samples.append(
                {
                    "workbook_file_name": row.get("workbook_file_name"),
                    "message": "parsed_with_warnings",
                }
            )

    return failure_samples, warning_samples


def _build_run_summary(
    *,
    run_id: str,
    parser_version: str | None,
    freeze_version: str | None,
    started_at: datetime,
    completed_at: datetime,
    persist_artifacts: bool,
    input_scope_root: str | None,
    counts: dict,
    results: list[dict],
) -> dict:
    duration_seconds = (completed_at - started_at).total_seconds()
    failure_samples, warning_samples = _build_samples(results)
    overall_status = _compute_overall_status(
        parsed_ok=counts["parsed_ok"],
        parsed_with_warnings=counts["parsed_with_warnings"],
        failed=counts["failed"],
        skipped_invalid=counts["skipped_invalid"],
    )

    return {
        "run_id": run_id,
        "run_type": HISTORICAL_BATCH_SEED_RUN_TYPE,
        "parser_version": parser_version,
        "freeze_version": freeze_version,
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_seconds": round(duration_seconds, 3),
        "persist_artifacts": persist_artifacts,
        "input_scope_root": input_scope_root,
        "total_files": counts["total_files"],
        "parsed_ok": counts["parsed_ok"],
        "parsed_with_warnings": counts["parsed_with_warnings"],
        "failed": counts["failed"],
        "skipped_invalid": counts["skipped_invalid"],
        "persisted_ok": counts["persisted_ok"],
        "persisted_failed": counts["persisted_failed"],
        "rollback_count": counts["rollback_count"],
        "overall_status": overall_status,
        "failure_samples": failure_samples,
        "warning_samples": warning_samples,
    }


def _build_result_payload(started_at: datetime, completed_at: datetime, expected_parser_version: str | None, results: list[dict], counts: dict, run_summary: dict) -> dict:
    total = counts["total_files"]
    failed = counts["failed"]

    return {
        "batch_meta": {
            "started_at": started_at.isoformat(),
            "finished_at": completed_at.isoformat(),
            "total_workbooks": total,
            "expected_parser_version": expected_parser_version,
            "run_id": run_summary["run_id"],
        },
        "summary": {
            "parsed_ok": counts["parsed_ok"],
            "parsed_with_warnings": counts["parsed_with_warnings"],
            "failed": failed,
            "skipped_invalid": counts["skipped_invalid"],
            "persisted_ok": counts["persisted_ok"],
            "persisted_failed": counts["persisted_failed"],
            "rollback_count": counts["rollback_count"],
            "overall_status": run_summary["overall_status"],
            "success_rate": 0.0 if total == 0 else round((total - failed) / total, 4),
        },
        "run_summary": {
            "run_id": run_summary["run_id"],
            "run_type": run_summary["run_type"],
            "overall_status": run_summary["overall_status"],
        },
        "results": results,
    }


def discover_workbook_files(input_dir: str, pattern: str = "**/*.xls*") -> list[str]:
    base = Path(input_dir)
    if not base.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    if not base.is_dir():
        raise NotADirectoryError(f"Input path is not a directory: {input_dir}")

    files = [path for path in base.glob(pattern) if path.is_file()]
    return sorted(path.as_posix() for path in files)


def run_historical_workbook_batch_seed(
    workbook_paths: list[str],
    expected_parser_version: str | None = None,
) -> dict:
    started_at = _now_utc()

    results: list[dict] = []
    parsed_ok_count = 0
    parsed_with_warnings_count = 0
    failed_count = 0
    skipped_invalid_count = 0

    run_id = str(uuid4())

    for workbook_path in workbook_paths:
        path = Path(workbook_path)
        if _is_invalid_workbook_path(path):
            skipped_invalid_count += 1
            results.append(
                {
                    "workbook_path": path.as_posix(),
                    "workbook_file_name": path.name,
                    "status": "skipped_invalid",
                    "template_match": None,
                    "parser_version": None,
                    "error": {
                        "code": "INVALID_WORKBOOK_PATH",
                        "message": "Path is missing, not a file, or not a supported workbook extension.",
                    },
                }
            )
            continue

        try:
            parse_result = parse_workbook_deterministic(workbook_path=path.as_posix())
            envelope = parse_result["workbook_parse_envelope"]
            parser_report = envelope.get("parser_report") or {}
            parser_status = parser_report.get("status") or "failed"
            parser_version = envelope.get("parser_version")

            if expected_parser_version and parser_version != expected_parser_version:
                failed_count += 1
                results.append(
                    {
                        "workbook_path": path.as_posix(),
                        "workbook_file_name": path.name,
                        "status": "failed",
                        "template_match": envelope.get("template_match"),
                        "parser_version": parser_version,
                        "error": {
                            "code": "PARSER_VERSION_MISMATCH",
                            "message": (
                                f"Expected parser_version '{expected_parser_version}' but got '{parser_version}'"
                            ),
                        },
                    }
                )
                continue

            if parser_status == "parsed_ok":
                parsed_ok_count += 1
            elif parser_status == "parsed_with_warnings":
                parsed_with_warnings_count += 1
            else:
                failed_count += 1

            results.append(
                {
                    "workbook_path": path.as_posix(),
                    "workbook_file_name": path.name,
                    "status": parser_status,
                    "template_match": envelope.get("template_match"),
                    "parser_version": parser_version,
                    "error": None,
                }
            )
        except Exception as exc:
            failed_count += 1
            results.append(
                {
                    "workbook_path": path.as_posix(),
                    "workbook_file_name": path.name,
                    "status": "failed",
                    "template_match": None,
                    "parser_version": None,
                    "error": {
                        "code": "WORKBOOK_PARSE_EXCEPTION",
                        "message": str(exc),
                    },
                }
            )

    completed_at = _now_utc()
    counts = {
        "total_files": len(workbook_paths),
        "parsed_ok": parsed_ok_count,
        "parsed_with_warnings": parsed_with_warnings_count,
        "failed": failed_count,
        "skipped_invalid": skipped_invalid_count,
        "persisted_ok": 0,
        "persisted_failed": 0,
        "rollback_count": 0,
    }
    run_summary = _build_run_summary(
        run_id=run_id,
        parser_version=expected_parser_version,
        freeze_version=expected_parser_version,
        started_at=started_at,
        completed_at=completed_at,
        persist_artifacts=False,
        input_scope_root=None,
        counts=counts,
        results=results,
    )
    return _build_result_payload(started_at, completed_at, expected_parser_version, results, counts, run_summary)


def build_historical_workbook_context(workbook_path: str) -> dict:
    path = Path(workbook_path)
    canonical = path.resolve().as_posix()
    rfq_uuid = uuid5(NAMESPACE_URL, f"rfq-intelligence-ms:historical-seed:{canonical}")

    return {
        "rfq_id": str(rfq_uuid),
        "workbook_ref": f"local://historical-seed/{path.name}",
        "workbook_filename": path.name,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "local_workbook_path": canonical,
    }


def run_historical_workbook_batch_seed_with_persistence(
    workbook_paths: list[str],
    workbook_service,
    expected_parser_version: str | None = None,
) -> dict:
    started_at = _now_utc()
    results: list[dict] = []
    parsed_ok_count = 0
    parsed_with_warnings_count = 0
    failed_count = 0
    skipped_invalid_count = 0
    persisted_ok_count = 0
    persisted_failed_count = 0
    rollback_count = 0

    run_id = str(uuid4())

    for workbook_path in workbook_paths:
        path = Path(workbook_path)
        if _is_invalid_workbook_path(path):
            skipped_invalid_count += 1
            persisted_failed_count += 1
            results.append(
                {
                    "workbook_path": path.as_posix(),
                    "workbook_file_name": path.name,
                    "status": "skipped_invalid",
                    "template_match": None,
                    "parser_version": None,
                    "rfq_id": None,
                    "persisted": False,
                    "artifacts": None,
                    "error": {
                        "code": "INVALID_WORKBOOK_PATH",
                        "message": "Path is missing, not a file, or not a supported workbook extension.",
                    },
                }
            )
            continue

        event_meta = {
            "event_id": f"hist-seed-{uuid4()}",
            "event_type": HISTORICAL_BATCH_SEED_EVENT_TYPE,
        }

        try:
            workbook_context = build_historical_workbook_context(path.as_posix())
            artifacts = workbook_service.build_workbook_parser_artifacts_from_uploaded_event(
                workbook_context=workbook_context,
                event_meta=event_meta,
                commit=False,
            )

            parser_report_artifact = artifacts["parser_report"]
            parser_report_content = parser_report_artifact.content or {}
            parser_status = (parser_report_content.get("parser_report") or {}).get("status") or "failed"
            parser_version = parser_report_content.get("parser_version")
            template_match = parser_report_content.get("template_match")

            if expected_parser_version and parser_version != expected_parser_version:
                workbook_service.datasource.db.rollback()
                rollback_count += 1
                failed_count += 1
                persisted_failed_count += 1
                results.append(
                    {
                        "workbook_path": path.as_posix(),
                        "workbook_file_name": path.name,
                        "status": "failed",
                        "template_match": template_match,
                        "parser_version": parser_version,
                        "rfq_id": workbook_context["rfq_id"],
                        "persisted": False,
                        "artifacts": None,
                        "error": {
                            "code": "PARSER_VERSION_MISMATCH",
                            "message": (
                                f"Expected parser_version '{expected_parser_version}' but got '{parser_version}'"
                            ),
                        },
                    }
                )
                continue

            workbook_service.datasource.db.commit()
            persisted_ok_count += 1

            if parser_status == "parsed_ok":
                parsed_ok_count += 1
            elif parser_status == "parsed_with_warnings":
                parsed_with_warnings_count += 1
            else:
                failed_count += 1

            results.append(
                {
                    "workbook_path": path.as_posix(),
                    "workbook_file_name": path.name,
                    "status": parser_status,
                    "template_match": template_match,
                    "parser_version": parser_version,
                    "rfq_id": workbook_context["rfq_id"],
                    "persisted": True,
                    "artifacts": {
                        "workbook_profile": {
                            "id": str(artifacts["workbook_profile"].id),
                            "version": artifacts["workbook_profile"].version,
                            "status": artifacts["workbook_profile"].status,
                        },
                        "cost_breakdown_profile": {
                            "id": str(artifacts["cost_breakdown_profile"].id),
                            "version": artifacts["cost_breakdown_profile"].version,
                            "status": artifacts["cost_breakdown_profile"].status,
                        },
                        "parser_report": {
                            "id": str(artifacts["parser_report"].id),
                            "version": artifacts["parser_report"].version,
                            "status": artifacts["parser_report"].status,
                        },
                    },
                    "error": None,
                }
            )
        except Exception as exc:
            workbook_service.datasource.db.rollback()
            rollback_count += 1
            failed_count += 1
            persisted_failed_count += 1
            results.append(
                {
                    "workbook_path": path.as_posix(),
                    "workbook_file_name": path.name,
                    "status": "failed",
                    "template_match": None,
                    "parser_version": None,
                    "rfq_id": None,
                    "persisted": False,
                    "artifacts": None,
                    "error": {
                        "code": "WORKBOOK_PERSIST_PIPELINE_EXCEPTION",
                        "message": str(exc),
                    },
                }
            )

    completed_at = _now_utc()
    counts = {
        "total_files": len(workbook_paths),
        "parsed_ok": parsed_ok_count,
        "parsed_with_warnings": parsed_with_warnings_count,
        "failed": failed_count,
        "skipped_invalid": skipped_invalid_count,
        "persisted_ok": persisted_ok_count,
        "persisted_failed": persisted_failed_count,
        "rollback_count": rollback_count,
    }
    run_summary = _build_run_summary(
        run_id=run_id,
        parser_version=expected_parser_version,
        freeze_version=expected_parser_version,
        started_at=started_at,
        completed_at=completed_at,
        persist_artifacts=True,
        input_scope_root=None,
        counts=counts,
        results=results,
    )
    payload = _build_result_payload(started_at, completed_at, expected_parser_version, results, counts, run_summary)
    payload["batch_meta"]["persistence_mode"] = True
    return payload


def execute_historical_batch_seed_run(
    *,
    workbook_paths: list[str],
    expected_parser_version: str | None,
    persist_artifacts: bool,
    input_scope_root: str | None,
    workbook_service=None,
    batch_seed_run_datasource=None,
) -> dict:
    if persist_artifacts:
        if workbook_service is None:
            raise ValueError("workbook_service is required when persist_artifacts=True")
        result = run_historical_workbook_batch_seed_with_persistence(
            workbook_paths=workbook_paths,
            workbook_service=workbook_service,
            expected_parser_version=expected_parser_version,
        )
    else:
        result = run_historical_workbook_batch_seed(
            workbook_paths=workbook_paths,
            expected_parser_version=expected_parser_version,
        )

    run_summary = dict(result.get("summary") or {})
    run_summary.update(
        {
            "run_id": result["batch_meta"]["run_id"],
            "run_type": HISTORICAL_BATCH_SEED_RUN_TYPE,
            "parser_version": expected_parser_version,
            "freeze_version": expected_parser_version,
            "started_at": datetime.fromisoformat(result["batch_meta"]["started_at"]),
            "completed_at": datetime.fromisoformat(result["batch_meta"]["finished_at"]),
            "duration_seconds": round(
                (
                    datetime.fromisoformat(result["batch_meta"]["finished_at"])
                    - datetime.fromisoformat(result["batch_meta"]["started_at"])
                ).total_seconds(),
                3,
            ),
            "persist_artifacts": persist_artifacts,
            "input_scope_root": input_scope_root,
            "total_files": result["batch_meta"]["total_workbooks"],
            "failure_samples": [
                {
                    "workbook_file_name": row.get("workbook_file_name"),
                    "code": (row.get("error") or {}).get("code"),
                    "message": (row.get("error") or {}).get("message"),
                }
                for row in result.get("results", [])
                if row.get("status") == "failed"
            ][:5],
            "warning_samples": [
                {
                    "workbook_file_name": row.get("workbook_file_name"),
                    "message": "parsed_with_warnings",
                }
                for row in result.get("results", [])
                if row.get("status") == "parsed_with_warnings"
            ][:5],
        }
    )

    if batch_seed_run_datasource is not None:
        record = batch_seed_run_datasource.create_run_summary(run_summary, commit=True)
        result["run_summary_record"] = {
            "id": str(record.id),
            "run_id": record.run_id,
            "overall_status": record.overall_status,
        }

    return result
