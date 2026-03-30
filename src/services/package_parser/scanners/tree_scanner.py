"""Directory tree scanner for package parser Stage A."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path

from src.services.package_parser.contracts import FileEntry, FolderEntry, PackageInventory
from src.services.package_parser.normalizers import (
    is_system_dir,
    is_system_file,
    normalize_relative_path,
)


_NUMBERED_FOLDER_RE = re.compile(r"^(\d{1,2})\s*-\s*(.+)$")
_MR_INDEX_RE = re.compile(r"^MR\s*Index(?:[_\s]*(\d+))?\.\w+$", re.IGNORECASE)
_MR_IN_FILENAME_RE = re.compile(r"MR-(\d+)", re.IGNORECASE)
_SECTION_PREFIX_RE = re.compile(r"^(\d{1,2})[_\-]")
_INTERNAL_REVIEW_RE = re.compile(r"(crs|internal)", re.IGNORECASE)


class TreeScanner:
    """Scan a package directory into a frozen PackageInventory."""

    def scan(self, root_path: Path) -> PackageInventory:
        root = root_path.resolve()
        if not root.exists() or not root.is_dir():
            raise FileNotFoundError(f"Package root directory not found: {root_path}")

        files: list[FileEntry] = []
        folders: list[FolderEntry] = []
        root_files: list[FileEntry] = []
        file_extension_counts: dict[str, int] = {}

        total_size_bytes = 0
        system_file_count = 0

        for current_dir, dirnames, filenames in os.walk(root):
            dirnames.sort(key=lambda name: name.lower())
            filenames.sort(key=lambda name: name.lower())

            current_path = Path(current_dir)
            rel_dir = current_path.relative_to(root)

            if rel_dir.parts:
                folder_depth = len(rel_dir.parts) - 1
                number_prefix, label = self._parse_numbered_folder(current_path.name)

                folder_file_count = 0
                for name in filenames:
                    rel_file_parts = (*rel_dir.parts, name)
                    if not self._is_system_file(name, rel_file_parts):
                        folder_file_count += 1

                folders.append(
                    FolderEntry(
                        relative_path=normalize_relative_path(rel_dir.as_posix()),
                        name=current_path.name,
                        depth=folder_depth,
                        file_count=folder_file_count,
                        subfolder_count=len(dirnames),
                        number_prefix=number_prefix,
                        label=label,
                    )
                )

            for name in filenames:
                file_path = current_path / name
                rel_file = file_path.relative_to(root)
                rel_file_parts = rel_file.parts
                depth = len(rel_file_parts) - 1
                system_flag = self._is_system_file(name, rel_file_parts)

                mr_index_match = _MR_INDEX_RE.match(name)
                is_mr_index = mr_index_match is not None
                mr_number_in_filename = self._extract_mr_number(name)
                section_prefix = self._extract_section_prefix(name)
                root_role = self._classify_root_role(
                    filename=name,
                    depth=depth,
                    is_system_file_flag=system_flag,
                    is_mr_index=is_mr_index,
                    mr_index_section_suffix=(mr_index_match.group(1) if mr_index_match else None),
                )

                try:
                    size_bytes = file_path.stat().st_size
                except OSError:
                    size_bytes = 0

                total_size_bytes += size_bytes
                if system_flag:
                    system_file_count += 1

                entry = FileEntry(
                    relative_path=normalize_relative_path(rel_file.as_posix()),
                    filename=name,
                    extension=file_path.suffix.lower(),
                    size_bytes=size_bytes,
                    depth=depth,
                    parent_folder=current_path.name,
                    is_mr_index=is_mr_index,
                    mr_number_in_filename=mr_number_in_filename,
                    section_prefix=section_prefix,
                    is_system_file=system_flag,
                    root_role=root_role,
                )
                files.append(entry)

                if depth == 0 and not system_flag:
                    root_files.append(entry)

                if not system_flag:
                    file_extension_counts[entry.extension] = file_extension_counts.get(entry.extension, 0) + 1

        files.sort(key=lambda item: item.relative_path.lower())
        folders.sort(key=lambda item: item.relative_path.lower())
        root_files.sort(key=lambda item: item.relative_path.lower())

        total_files_raw = len(files)
        total_files = total_files_raw - system_file_count

        return PackageInventory(
            package_root_name=root.name,
            input_type="directory",
            total_files=total_files,
            total_files_raw=total_files_raw,
            total_folders=len(folders),
            total_size_bytes=total_size_bytes,
            files=files,
            folders=folders,
            root_files=root_files,
            file_extension_counts=file_extension_counts,
            system_file_count=system_file_count,
            scanned_at=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def _parse_numbered_folder(folder_name: str) -> tuple[int | None, str | None]:
        match = _NUMBERED_FOLDER_RE.match(folder_name)
        if match is None:
            return None, None
        return int(match.group(1)), match.group(2).strip() or None

    @staticmethod
    def _extract_mr_number(filename: str) -> str | None:
        match = _MR_IN_FILENAME_RE.search(filename)
        if match is None:
            return None
        return f"MR-{match.group(1)}"

    @staticmethod
    def _extract_section_prefix(filename: str) -> str | None:
        match = _SECTION_PREFIX_RE.match(filename)
        if match is None:
            return None
        return match.group(1).zfill(2)

    @staticmethod
    def _is_dotfile(filename: str) -> bool:
        return filename.startswith(".")

    def _is_system_file(self, filename: str, rel_file_parts: tuple[str, ...]) -> bool:
        if self._is_dotfile(filename) or is_system_file(filename):
            return True

        for folder in rel_file_parts[:-1]:
            if is_system_dir(folder):
                return True
        return False

    @staticmethod
    def _classify_root_role(
        filename: str,
        depth: int,
        is_system_file_flag: bool,
        is_mr_index: bool,
        mr_index_section_suffix: str | None,
    ) -> str | None:
        if depth != 0 or is_system_file_flag:
            return None

        if is_mr_index and mr_index_section_suffix is None:
            return "mr_index_root"

        if _INTERNAL_REVIEW_RE.search(filename) is not None:
            return "internal_review_file"

        return "unclassified_root_extra"
