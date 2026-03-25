"""Deterministic workbook parser package (Step 9 skeleton)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import xlrd

from src.services.workbook_parser.assembler import PARSER_VERSION, TEMPLATE_NAME
from src.services.workbook_parser.parser_orchestrator import WorkbookParserOrchestrator


def compute_structure(expected_sheet_names: list[str], actual_sheet_names: list[str]) -> dict[str, Any]:
    """Compute expected/found workbook structure metrics."""
    expected_set = set(expected_sheet_names)
    actual_set = set(actual_sheet_names)

    missing = sorted(expected_set - actual_set)
    extra = sorted(actual_set - expected_set)

    return {
        "expected_sheet_count": len(expected_sheet_names),
        "sheet_count_found": len(actual_sheet_names),
        "missing_sheets": missing,
        "extra_sheets": extra,
    }


def parse_workbook_deterministic(
    workbook_path: str,
    expected_sheet_names: list[str] | None = None,
) -> dict[str, Any]:
    """Compatibility entrypoint retained for existing WorkbookService flow."""
    path = Path(workbook_path)
    if not path.exists():
        raise FileNotFoundError(f"Workbook file not found: {workbook_path}")

    workbook = xlrd.open_workbook(path.as_posix(), formatting_info=True)
    sheet_names = workbook.sheet_names()

    expected = expected_sheet_names or ["General", "Bid S", "Top Sheet"]
    structure = compute_structure(expected_sheet_names=expected, actual_sheet_names=sheet_names)

    orchestrator = WorkbookParserOrchestrator()
    envelope = orchestrator.parse(
        workbook_path=workbook_path,
        rfq_id="RFQ-UNKNOWN",
        workbook_file_name=path.name,
        workbook_blob_path=None,
    )

    return {
        "template_recognition": {
            "template_family": TEMPLATE_NAME,
            "sheet_count_found": structure["sheet_count_found"],
            "expected_sheet_count": structure["expected_sheet_count"],
            "recognition_status": "matched" if envelope["template_match"] else "partial",
            "recognition_notes": "Recognition uses required sheet and anchor validation for General/Bid S/Top Sheet.",
            "parser_version": PARSER_VERSION,
        },
        "workbook_structure": {
            "sheet_names": sheet_names,
            "sheet_count_found": structure["sheet_count_found"],
            "expected_sheet_count": structure["expected_sheet_count"],
            "missing_sheets": structure["missing_sheets"],
            "extra_sheets": structure["extra_sheets"],
        },
        "high_value_extracts": _extract_high_value_cells(workbook),
        "workbook_parse_envelope": envelope,
    }


def _extract_high_value_cells(workbook: xlrd.book.Book) -> dict[str, Any]:
    text_hits: list[dict[str, Any]] = []
    numeric_hits: list[dict[str, Any]] = []
    keywords = ["total", "currency", "project", "client", "delivery", "lead"]

    for sheet in workbook.sheets():
        max_rows = min(sheet.nrows, 120)
        max_cols = min(sheet.ncols, 20)

        for row in range(max_rows):
            for col in range(max_cols):
                value = sheet.cell_value(row, col)
                if isinstance(value, str):
                    normalized = value.strip()
                    if not normalized:
                        continue
                    if any(token in normalized.lower() for token in keywords):
                        text_hits.append(
                            {
                                "sheet": sheet.name,
                                "row": row,
                                "col": col,
                                "text": normalized[:200],
                            }
                        )
                elif isinstance(value, (int, float)) and value not in (0, 0.0):
                    if len(numeric_hits) < 100:
                        numeric_hits.append(
                            {
                                "sheet": sheet.name,
                                "row": row,
                                "col": col,
                                "value": float(value),
                            }
                        )

    return {
        "text_hits": text_hits[:120],
        "numeric_sample": numeric_hits,
    }


__all__ = ["WorkbookParserOrchestrator", "compute_structure", "parse_workbook_deterministic"]
