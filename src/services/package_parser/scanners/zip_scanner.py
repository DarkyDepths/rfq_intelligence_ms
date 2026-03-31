"""ZIP scanner for deterministic package parser Stage A."""

from __future__ import annotations

import gc
import re
import tempfile
import zipfile
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import Iterator

from src.services.package_parser.contracts import PackageInventory
from src.services.package_parser.normalizers import is_system_dir, is_system_file
from src.services.package_parser.scanners.tree_scanner import TreeScanner


_PACKAGE_ROOT_RE = re.compile(r"^([\w-]+-MR-\d+)[_\s]+(.+?)[-\s]*REV[-\s]*(\d+)\s*$")
_NUMBERED_SECTION_RE = re.compile(r"^\d{1,2}\s*-\s+")


class ZipScanner:
    """Extract a package ZIP, resolve the package root, and delegate to TreeScanner."""

    def __init__(self) -> None:
        self._tree_scanner = TreeScanner()

    def scan(self, zip_path: Path) -> PackageInventory:
        with self.open_package(zip_path) as (_, inventory):
            return inventory

    @contextmanager
    def open_package(self, zip_path: Path) -> Iterator[tuple[Path, PackageInventory]]:
        archive_path = Path(zip_path).resolve()
        if not archive_path.exists() or not archive_path.is_file():
            raise FileNotFoundError(f"ZIP file not found: {zip_path}")

        with tempfile.TemporaryDirectory(prefix="package_parser_zip_") as temp_dir:
            extraction_root = Path(temp_dir)
            self._extract_archive(archive_path, extraction_root)
            package_root = self._detect_package_root(extraction_root)
            inventory = replace(self._tree_scanner.scan(package_root), input_type="zip")
            try:
                yield package_root, inventory
            finally:
                gc.collect()

    def _extract_archive(self, archive_path: Path, extraction_root: Path) -> None:
        try:
            with zipfile.ZipFile(archive_path) as archive:
                members = archive.infolist()
                if not members:
                    raise ValueError(f"ZIP archive is empty: {archive_path}")

                self._validate_members(members, extraction_root)
                archive.extractall(extraction_root)
        except zipfile.BadZipFile as exc:
            raise ValueError(f"Invalid ZIP archive: {archive_path}") from exc

    def _validate_members(self, members: list[zipfile.ZipInfo], extraction_root: Path) -> None:
        base_path = extraction_root.resolve()
        for member in members:
            member_path = Path(member.filename)
            if member_path.is_absolute():
                raise ValueError(f"ZIP archive contains an absolute path: {member.filename}")

            target_path = (extraction_root / member.filename).resolve()
            try:
                target_path.relative_to(base_path)
            except ValueError as exc:
                raise ValueError(f"ZIP archive contains an unsafe path: {member.filename}") from exc

    def _detect_package_root(self, extraction_root: Path) -> Path:
        top_level_entries = self._list_non_system_entries(extraction_root)
        if not top_level_entries:
            raise ValueError("ZIP archive contains no usable files or directories.")

        if len(top_level_entries) == 1 and top_level_entries[0].is_dir():
            return self._resolve_single_directory(top_level_entries[0])

        candidate_dirs = self._collect_candidate_dirs(top_level_entries)
        matching_roots = [candidate for candidate in candidate_dirs if _PACKAGE_ROOT_RE.match(candidate.name) is not None]
        if len(matching_roots) == 1:
            return matching_roots[0]
        if len(matching_roots) > 1:
            raise ValueError("ZIP archive contains multiple possible package root directories.")

        scored_candidates = [
            (self._package_root_score(candidate), candidate)
            for candidate in candidate_dirs
        ]
        scored_candidates = [entry for entry in scored_candidates if entry[0] > 0]
        if not scored_candidates:
            raise ValueError("Could not resolve package root directory from ZIP archive.")

        scored_candidates.sort(key=lambda item: (-item[0], item[1].as_posix().lower()))
        best_score = scored_candidates[0][0]
        best_candidates = [candidate for score, candidate in scored_candidates if score == best_score]
        if len(best_candidates) > 1:
            raise ValueError("ZIP archive package root is ambiguous.")
        return best_candidates[0]

    def _collect_candidate_dirs(self, entries: list[Path]) -> list[Path]:
        candidates: dict[str, Path] = {}
        for entry in entries:
            if not entry.is_dir():
                continue
            resolved = self._resolve_single_directory(entry).resolve()
            candidates[resolved.as_posix().lower()] = resolved
        return sorted(candidates.values(), key=lambda path: path.as_posix().lower())

    def _resolve_single_directory(self, directory: Path) -> Path:
        current = directory
        while True:
            entries = self._list_non_system_entries(current)
            child_dirs = [entry for entry in entries if entry.is_dir()]
            child_files = [entry for entry in entries if entry.is_file()]
            matching_child_dirs = [
                child_dir for child_dir in child_dirs if _PACKAGE_ROOT_RE.match(child_dir.name) is not None
            ]

            if len(child_dirs) == 1 and not child_files:
                current = child_dirs[0]
                continue

            if len(matching_child_dirs) == 1 and _PACKAGE_ROOT_RE.match(current.name) is None:
                current = matching_child_dirs[0]
                continue

            return current

    def _package_root_score(self, directory: Path) -> int:
        entries = self._list_non_system_entries(directory)
        numbered_dirs = sum(1 for entry in entries if entry.is_dir() and _NUMBERED_SECTION_RE.match(entry.name) is not None)
        root_files = sum(1 for entry in entries if entry.is_file())
        return numbered_dirs * 100 + root_files

    def _list_non_system_entries(self, directory: Path) -> list[Path]:
        entries: list[Path] = []
        for entry in sorted(directory.iterdir(), key=lambda path: path.name.lower()):
            if entry.name.startswith("."):
                continue
            if entry.is_dir():
                if is_system_dir(entry.name):
                    continue
            elif is_system_file(entry.name):
                continue
            entries.append(entry)
        return entries
