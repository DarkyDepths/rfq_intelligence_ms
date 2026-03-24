"""Deterministic parser helpers for the V1 workbook vertical slice."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import xlrd


EXPECTED_SHEET_COUNT = 36


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
    """Parse workbook using deterministic, template-oriented extraction."""
    path = Path(workbook_path)
    if not path.exists():
        raise FileNotFoundError(f"Workbook file not found: {workbook_path}")

    workbook = xlrd.open_workbook(path.as_posix())
    sheet_names = workbook.sheet_names()

    if expected_sheet_names:
        structure = compute_structure(expected_sheet_names, sheet_names)
    else:
        structure = {
            "expected_sheet_count": EXPECTED_SHEET_COUNT,
            "sheet_count_found": len(sheet_names),
            "missing_sheets": [],
            "extra_sheets": [],
        }

    recognition_status = (
        "matched"
        if structure["sheet_count_found"] == EXPECTED_SHEET_COUNT and not structure["missing_sheets"]
        else "partial"
    )

    workbook_summary = {
        "sheet_names": sheet_names,
        "sheet_count_found": structure["sheet_count_found"],
        "expected_sheet_count": structure["expected_sheet_count"],
        "missing_sheets": structure["missing_sheets"],
        "extra_sheets": structure["extra_sheets"],
    }

    high_value = _extract_high_value_cells(workbook)

    return {
        "template_recognition": {
            "template_family": "ghi_estimation_workbook",
            "sheet_count_found": structure["sheet_count_found"],
            "expected_sheet_count": structure["expected_sheet_count"],
            "recognition_status": recognition_status,
            "recognition_notes": (
                "Expected sheet names were not provided; recognition based on sheet-count heuristic."
                if not expected_sheet_names
                else "Recognition used expected sheet-name comparison."
            ),
        },
        "workbook_structure": workbook_summary,
        "high_value_extracts": high_value,
    }


def _extract_high_value_cells(workbook: xlrd.book.Book) -> dict[str, Any]:
    """Extract conservative workbook facts without claiming full semantic parsing."""
    text_hits: list[dict[str, Any]] = []
    numeric_hits: list[dict[str, Any]] = []

    keywords = ["total", "currency", "project", "client", "delivery", "lead"]

    for sheet in workbook.sheets():
        max_rows = min(sheet.nrows, 120)
        max_cols = min(sheet.ncols, 20)

        for r in range(max_rows):
            for c in range(max_cols):
                value = sheet.cell_value(r, c)
                if isinstance(value, str):
                    normalized = value.strip()
                    if not normalized:
                        continue
                    lower = normalized.lower()
                    if any(k in lower for k in keywords):
                        text_hits.append(
                            {
                                "sheet": sheet.name,
                                "row": r,
                                "col": c,
                                "text": normalized[:200],
                            }
                        )
                elif isinstance(value, (int, float)) and value not in (0, 0.0):
                    if len(numeric_hits) < 100:
                        numeric_hits.append(
                            {
                                "sheet": sheet.name,
                                "row": r,
                                "col": c,
                                "value": float(value),
                            }
                        )

    return {
        "text_hits": text_hits[:120],
        "numeric_sample": numeric_hits,
    }
