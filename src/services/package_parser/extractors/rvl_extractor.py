"""RVL extraction for package parser Stage C."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from docx import Document

from src.services.package_parser.contracts import (
    FileEntry,
    PackageInventory,
    RvlProfile,
    RvlVendorEntry,
    SectionMatch,
    SectionRegistry,
)


_HEADER_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")
_FILENAME_MR_RE = re.compile(r"MR-(\d+)", re.IGNORECASE)
_HEADER_SCAN_LIMIT = 5
_HEADER_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "nine_com": ("9com", "9comcode", "ninecom"),
    "material_description": ("materialdescription", "materialdesc", "description"),
    "manufacturer_id": ("mfrid", "manufacturerid", "mfr", "vendorid"),
    "vendor_name": ("name", "vendorname", "manufacturername"),
    "country_code": ("countrycode",),
    "country_name": ("countryname",),
}


class RvlExtractor:
    """Extract RVL vendors from the canonical folder 03 section."""

    def extract(
        self,
        inventory: PackageInventory,
        registry: SectionRegistry,
        package_root: Path,
    ) -> RvlProfile | None:
        section = self._find_rvl_section(registry)
        if section is None:
            return None

        source_file = self._find_rvl_docx(inventory, section)
        if source_file is None:
            return None

        try:
            document = Document(package_root / source_file.relative_path)
        except OSError:
            return None

        vendors = self._parse_vendors(document)
        return RvlProfile(
            source_file=source_file.relative_path,
            source_format="docx",
            vendors=vendors,
            total_vendors=len(vendors),
            unique_vendor_names=self._ordered_unique(entry.vendor_name for entry in vendors),
            unique_countries=self._ordered_unique(
                entry.country_code if entry.country_code is not None else entry.country_name
                for entry in vendors
            ),
            nine_com_codes=self._ordered_unique(entry.nine_com for entry in vendors),
            mr_number_in_rvl=self._extract_mr_number(source_file),
        )

    @staticmethod
    def _find_rvl_section(registry: SectionRegistry) -> SectionMatch | None:
        for section in registry.matched_sections:
            if section.canonical_key == "rvl":
                return section
        return None

    def _find_rvl_docx(self, inventory: PackageInventory, section: SectionMatch) -> FileEntry | None:
        section_prefix = f"{section.folder_relative_path}/"
        candidates = [
            file_entry
            for file_entry in inventory.files
            if not file_entry.is_system_file
            and not file_entry.is_mr_index
            and file_entry.relative_path.startswith(section_prefix)
            and file_entry.extension.lower() == ".docx"
        ]
        if not candidates:
            return None
        return sorted(
            candidates,
            key=lambda item: (
                0 if "rvl" in item.filename.lower() else 1,
                item.relative_path.lower(),
            ),
        )[0]

    def _parse_vendors(self, document: Document) -> list[RvlVendorEntry]:
        for table in document.tables:
            header_row_index, column_map = self._find_header_row(table)
            if header_row_index is None or column_map is None:
                continue
            return self._parse_table_rows(table, header_row_index, column_map)
        return []

    def _find_header_row(self, table) -> tuple[int | None, dict[str, int] | None]:
        scan_limit = min(len(table.rows), _HEADER_SCAN_LIMIT)
        for row_index in range(scan_limit):
            row_values = [cell.text for cell in table.rows[row_index].cells]
            column_map = self._build_column_map(row_values)
            if self._is_header_map(column_map):
                return row_index, column_map
        return None, None

    def _build_column_map(self, row_values: Iterable[object]) -> dict[str, int]:
        column_map: dict[str, int] = {}

        for column_index, cell_value in enumerate(row_values):
            normalized = self._normalize_header(cell_value)
            if normalized is None:
                continue

            explicit_match = self._match_header_field(normalized)
            if explicit_match is not None and explicit_match not in column_map:
                column_map[explicit_match] = column_index
                continue

            if normalized == "country":
                if "country_code" not in column_map:
                    column_map["country_code"] = column_index
                elif "country_name" not in column_map:
                    column_map["country_name"] = column_index

        return column_map

    @staticmethod
    def _match_header_field(normalized: str) -> str | None:
        for field_name, aliases in _HEADER_FIELD_ALIASES.items():
            if normalized in aliases:
                return field_name
        return None

    @staticmethod
    def _is_header_map(column_map: dict[str, int]) -> bool:
        recognized_count = len(column_map)
        core_count = sum(
            1
            for field_name in ("nine_com", "material_description", "manufacturer_id", "vendor_name")
            if field_name in column_map
        )
        country_present = "country_code" in column_map or "country_name" in column_map
        return recognized_count >= 4 and core_count >= 3 and country_present

    def _parse_table_rows(self, table, header_row_index: int, column_map: dict[str, int]) -> list[RvlVendorEntry]:
        vendors: list[RvlVendorEntry] = []

        for row in table.rows[header_row_index + 1:]:
            row_values = [cell.text for cell in row.cells]
            if self._is_header_map(self._build_column_map(row_values)):
                continue

            entry = RvlVendorEntry(
                nine_com=self._cell_to_text(self._value_at(row_values, column_map.get("nine_com"))),
                material_description=self._cell_to_text(
                    self._value_at(row_values, column_map.get("material_description"))
                ),
                manufacturer_id=self._cell_to_text(self._value_at(row_values, column_map.get("manufacturer_id"))),
                vendor_name=self._cell_to_text(self._value_at(row_values, column_map.get("vendor_name"))),
                country_code=self._cell_to_text(self._value_at(row_values, column_map.get("country_code"))),
                country_name=self._cell_to_text(self._value_at(row_values, column_map.get("country_name"))),
            )
            if self._is_meaningful_vendor_row(entry):
                vendors.append(entry)

        return vendors

    @staticmethod
    def _value_at(row_values: list[object], column_index: int | None) -> object | None:
        if column_index is None or column_index < 0 or column_index >= len(row_values):
            return None
        return row_values[column_index]

    @staticmethod
    def _normalize_header(value: object) -> str | None:
        text = RvlExtractor._cell_to_text(value)
        if text is None:
            return None
        normalized = _HEADER_NORMALIZE_RE.sub("", text.lower())
        return normalized or None

    @staticmethod
    def _cell_to_text(value: object) -> str | None:
        if value is None:
            return None
        text = " ".join(str(value).split())
        return text or None

    @staticmethod
    def _is_meaningful_vendor_row(entry: RvlVendorEntry) -> bool:
        anchor_fields = (
            entry.vendor_name,
            entry.manufacturer_id,
            entry.nine_com,
            entry.material_description,
        )
        if any(value is not None for value in anchor_fields):
            return True

        populated_fields = sum(
            1
            for value in (entry.country_code, entry.country_name)
            if value is not None
        )
        return populated_fields >= 2

    @staticmethod
    def _extract_mr_number(source_file: FileEntry) -> str | None:
        if source_file.mr_number_in_filename is not None:
            return source_file.mr_number_in_filename

        match = _FILENAME_MR_RE.search(source_file.filename)
        if match is None:
            return None
        return f"MR-{match.group(1)}"

    @staticmethod
    def _ordered_unique(values: Iterable[str | None]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for value in values:
            if value is None or value in seen:
                continue
            seen.add(value)
            ordered.append(value)
        return ordered
