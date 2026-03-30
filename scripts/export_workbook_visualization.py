from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from src.connectors.manager_connector import ManagerConnector
from src.database import SessionLocal
from src.datasources.artifact_datasource import ArtifactDatasource
from src.datasources.batch_seed_run_datasource import BatchSeedRunDatasource
from src.datasources.processed_event_datasource import ProcessedEventDatasource
from src.event_handlers.lifecycle_handlers import LifecycleHandlers
from src.services.analytical_record_service import AnalyticalRecordService
from src.services.briefing_service import BriefingService
from src.services.event_processing_service import EventProcessingService
from src.services.intake_service import IntakeService
from src.services.review_service import ReviewService
from src.services.snapshot_service import SnapshotService
from src.services.workbook_parser import parse_workbook_deterministic
from src.services.workbook_parser.batch_seed_runner import execute_historical_batch_seed_run
from src.services.workbook_service import WorkbookService


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run parser + persisted workbook flow and export visualization JSON files "
            "(envelope, run summary, event result, artifacts)."
        )
    )
    parser.add_argument("--workbook-path", required=True, help="Path to workbook file (.xls/.xlsx/.xlsm).")
    parser.add_argument(
        "--rfq-id",
        default="11111111-1111-1111-1111-111111111111",
        help="RFQ id used for workbook.uploaded flow (default: fixed demo UUID).",
    )
    parser.add_argument(
        "--output-dir",
        default="tmp/visualization",
        help="Directory to write exported JSON files.",
    )
    parser.add_argument(
        "--expected-parser-version",
        default="workbook-parser-v2.1",
        help="Freeze guard used in batch seeding run summary.",
    )
    parser.add_argument(
        "--manager-base-url",
        default="http://rfq-manager-not-used-for-visualization",
        help="Manager connector base URL (not used for local workbook path mode).",
    )
    parser.add_argument(
        "--skip-batch-seed",
        action="store_true",
        help="Skip persisted batch-seed run summary generation and export only parser/event artifacts.",
    )
    return parser


def _artifact_to_dict(artifact) -> dict:
    return {
        "id": str(artifact.id),
        "rfq_id": str(artifact.rfq_id),
        "artifact_type": artifact.artifact_type,
        "version": artifact.version,
        "status": artifact.status,
        "is_current": bool(artifact.is_current),
        "schema_version": artifact.schema_version,
        "source_event_type": artifact.source_event_type,
        "source_event_id": artifact.source_event_id,
        "created_at": artifact.created_at.isoformat() if artifact.created_at else None,
        "updated_at": artifact.updated_at.isoformat() if artifact.updated_at else None,
        "content": artifact.content,
    }


def _write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    args = _build_parser().parse_args()
    workbook_path = Path(args.workbook_path).resolve()
    if not workbook_path.exists() or not workbook_path.is_file():
        raise FileNotFoundError(f"Workbook not found: {workbook_path}")

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1) Direct parser envelope export.
    parse_result = parse_workbook_deterministic(workbook_path=str(workbook_path))
    _write_json(output_dir / "parser_envelope.json", parse_result["workbook_parse_envelope"])
    _write_json(output_dir / "parser_full_result.json", parse_result)

    session = SessionLocal()
    try:
        artifact_ds = ArtifactDatasource(session)
        processed_ds = ProcessedEventDatasource(session)
        batch_seed_ds = BatchSeedRunDatasource(session)

        connector = ManagerConnector(base_url=args.manager_base_url)

        intake_service = IntakeService(datasource=artifact_ds, connector=connector)
        briefing_service = BriefingService(datasource=artifact_ds)
        workbook_service = WorkbookService(datasource=artifact_ds, connector=connector)
        review_service = ReviewService(datasource=artifact_ds)
        snapshot_service = SnapshotService(datasource=artifact_ds)
        analytical_service = AnalyticalRecordService(datasource=artifact_ds)
        event_processing_service = EventProcessingService(datasource=processed_ds)

        handlers = LifecycleHandlers(
            intake_service=intake_service,
            briefing_service=briefing_service,
            workbook_service=workbook_service,
            review_service=review_service,
            snapshot_service=snapshot_service,
            analytical_record_service=analytical_service,
            event_processing_service=event_processing_service,
        )

        # 2) Batch-seed run summary export (persisted run record).
        if not args.skip_batch_seed:
            try:
                batch_result = execute_historical_batch_seed_run(
                    workbook_paths=[str(workbook_path)],
                    expected_parser_version=args.expected_parser_version,
                    persist_artifacts=True,
                    input_scope_root=str(workbook_path.parent),
                    workbook_service=workbook_service,
                    batch_seed_run_datasource=batch_seed_ds,
                )
                _write_json(output_dir / "batch_seed_run_result.json", batch_result)
            except Exception as exc:
                _write_json(
                    output_dir / "batch_seed_run_error.json",
                    {
                        "status": "failed",
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                    },
                )

        # 3) End-to-end workbook.uploaded handler export.
        event_id = f"viz-workbook-uploaded-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        event = {
            "event_id": event_id,
            "event_type": "workbook.uploaded",
            "event_version": "1.0",
            "emitted_at": datetime.now(timezone.utc).isoformat(),
            "producer": "visualization-script",
            "payload": {
                "rfq_id": args.rfq_id,
                "workbook_ref": str(workbook_path),
                "workbook_filename": workbook_path.name,
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
            },
        }
        workbook_event_result = asyncio.run(handlers.handle_workbook_uploaded(event))
        _write_json(output_dir / "workbook_uploaded_event_result.json", workbook_event_result)

        # 4) Export all artifacts for that RFQ for easy visual inspection.
        artifacts = artifact_ds.list_artifacts(args.rfq_id)
        artifact_index = []
        for artifact in artifacts:
            as_dict = _artifact_to_dict(artifact)
            artifact_index.append(
                {
                    "id": as_dict["id"],
                    "artifact_type": as_dict["artifact_type"],
                    "version": as_dict["version"],
                    "status": as_dict["status"],
                    "is_current": as_dict["is_current"],
                    "created_at": as_dict["created_at"],
                }
            )
            _write_json(output_dir / f"artifact_{artifact.artifact_type}_v{artifact.version}.json", as_dict)

        _write_json(output_dir / "artifacts_index.json", artifact_index)

    finally:
        session.close()

    summary = {
        "output_dir": str(output_dir),
        "files": [
            "parser_envelope.json",
            "parser_full_result.json",
            "batch_seed_run_result.json",
            "workbook_uploaded_event_result.json",
            "artifacts_index.json",
            "artifact_<type>_v<version>.json",
        ],
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
