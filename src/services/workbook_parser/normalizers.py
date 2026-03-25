"""Small normalization helpers for deterministic workbook parsing."""

from __future__ import annotations

import re


_WS_RE = re.compile(r"\s+")


def normalize_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).replace("\n", " ").replace("\t", " ").strip()
    if not text:
        return None
    return _WS_RE.sub(" ", text)


def normalize_label(value: object) -> str | None:
    text = normalize_text(value)
    if text is None:
        return None
    return text.lower()


def strip_top_sheet_leading_dash(label: str | None) -> str | None:
    if label is None:
        return None
    cleaned = label.strip()
    if cleaned.startswith("-"):
        return cleaned[1:].strip()
    return cleaned


def normalize_empty_to_none(value: object) -> str | None:
    text = normalize_text(value)
    return text if text else None


def normalize_yes_no_flag(value: object) -> bool | None:
    text = normalize_label(value)
    if text is None:
        return None
    if text in {"yes", "y", "true"}:
        return True
    if text in {"no", "n", "false"}:
        return False
    return None


def normalize_numeric(value: object) -> float | int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        text = normalize_text(value)
        if text is None:
            return None
        text = text.replace(",", "")
        try:
            number = float(text)
        except ValueError:
            return None
    if number.is_integer():
        return int(number)
    return number
