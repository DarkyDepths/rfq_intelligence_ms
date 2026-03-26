from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.connectors.manager_connector import ManagerConnector
from src.database import SessionLocal
from src.datasources.artifact_datasource import ArtifactDatasource
from src.datasources.batch_seed_run_datasource import BatchSeedRunDatasource
from src.services.workbook_service import WorkbookService
from src.services.workbook_parser.batch_seed_runner import (
    execute_historical_batch_seed_run,
    discover_workbook_files,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run deterministic workbook parser over historical workbook folders.",
    )
    parser.add_argument("--input-dir", required=True, help="Root directory containing historical workbooks.")
    parser.add_argument(
        "--glob",
        default="**/*.xls*",
        help="Glob pattern used to discover workbook files (default: **/*.xls*).",
    )
    parser.add_argument(
        "--expected-parser-version",
        default="workbook-parser-v2.1",
        help="Freeze guard for parser_version; mismatches are marked as failed.",
    )
    parser.add_argument(
        "--output-json",
        default=None,
        help="Optional path to write the full batch result JSON.",
    )
    parser.add_argument(
        "--persist-artifacts",
        action="store_true",
        help="Persist workbook_profile/cost_breakdown_profile/parser_report artifacts for each workbook.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    workbook_paths = discover_workbook_files(input_dir=args.input_dir, pattern=args.glob)
    session = SessionLocal()
    try:
        run_summary_datasource = BatchSeedRunDatasource(session)

        workbook_service = None
        if args.persist_artifacts:
            artifact_datasource = ArtifactDatasource(session)
            connector = ManagerConnector(base_url="http://rfq-manager-not-used-in-batch-seed")
            workbook_service = WorkbookService(datasource=artifact_datasource, connector=connector)

        result = execute_historical_batch_seed_run(
            workbook_paths=workbook_paths,
            expected_parser_version=args.expected_parser_version,
            persist_artifacts=args.persist_artifacts,
            input_scope_root=args.input_dir,
            workbook_service=workbook_service,
            batch_seed_run_datasource=run_summary_datasource,
        )
    finally:
        session.close()

    if args.output_json:
        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(json.dumps(result["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
