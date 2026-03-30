"""Small normalization helpers for deterministic package parsing."""

from __future__ import annotations

from pathlib import PurePosixPath


SYSTEM_FILE_PATTERNS = {".ds_store", "thumbs.db", ".gitkeep", "desktop.ini"}
SYSTEM_DIR_PATTERNS = {"__macosx"}


def normalize_filename(filename: str) -> str:
    return filename.strip()


def normalize_relative_path(path: str) -> str:
    normalized = str(PurePosixPath(path.replace("\\", "/")))
    return normalized.strip("/")


def is_system_file(filename: str) -> bool:
    return normalize_filename(filename).lower() in SYSTEM_FILE_PATTERNS


def is_system_dir(dirname: str) -> bool:
    return dirname.strip().lower() in SYSTEM_DIR_PATTERNS


__all__ = [
    "SYSTEM_DIR_PATTERNS",
    "SYSTEM_FILE_PATTERNS",
    "is_system_dir",
    "is_system_file",
    "normalize_filename",
    "normalize_relative_path",
]
