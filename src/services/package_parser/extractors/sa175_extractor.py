"""SA-175 extraction for package parser Stage C."""

from __future__ import annotations

import re
from typing import Iterable

from src.services.package_parser.contracts import (
    PackageInventory,
    Sa175FormEntry,
    Sa175Profile,
    SectionMatch,
    SectionRegistry,
)


_SA175_RE = re.compile(r"175[-_](\d{6})", re.IGNORECASE)


class Sa175Extractor:
    """Detect SA-175 forms by filename inside the canonical section 07."""

    def extract(self, inventory: PackageInventory, registry: SectionRegistry) -> Sa175Profile | None:
        section = self._find_section(registry)
        if section is None:
            return None

        section_prefix = f"{section.folder_relative_path}/"
        forms = [
            Sa175FormEntry(
                filename=file_entry.filename,
                form_number=f"175-{match.group(1)}",
                relative_path=file_entry.relative_path,
            )
            for file_entry in inventory.files
            if not file_entry.is_system_file
            and not file_entry.is_mr_index
            and file_entry.relative_path.startswith(section_prefix)
            for match in [ _SA175_RE.search(file_entry.filename) ]
            if match is not None
        ]

        if not forms:
            return None

        return Sa175Profile(
            forms=forms,
            total_count=len(forms),
            form_numbers=self._ordered_unique(form.form_number for form in forms),
        )

    @staticmethod
    def _find_section(registry: SectionRegistry) -> SectionMatch | None:
        for section in registry.matched_sections:
            if section.canonical_key == "sa175_forms":
                return section
        return None

    @staticmethod
    def _ordered_unique(values: Iterable[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            ordered.append(value)
        return ordered
