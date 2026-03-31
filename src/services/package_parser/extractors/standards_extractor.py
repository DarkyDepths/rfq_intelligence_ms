"""Standards extraction for package parser Stage C."""

from __future__ import annotations

import re
from pathlib import Path

from src.services.package_parser.contracts import (
    PackageInventory,
    SectionMatch,
    SectionRegistry,
    StandardReference,
    StandardsProfile,
)


_SAMSS_RE = re.compile(r"SAMSS[-_]?(\d{3})", re.IGNORECASE)
_SAES_RE = re.compile(r"SAES[-_]?([A-Z][-_]\d{3})", re.IGNORECASE)
_SAEP_RE = re.compile(r"SAEP[-_]?(\d+)", re.IGNORECASE)
_STD_DWG_RE = re.compile(r"STD[\s._-]*DWG(?:[-_\s]*([A-Z0-9][A-Z0-9._-]*))?", re.IGNORECASE)
_NUMBERED_SUBFOLDER_RE = re.compile(r"^(\d+)\.\s*(.+)$")
_EXTRACTION_METHOD = "filename_regex"


class StandardsExtractor:
    """Extract filename-based standards metadata from section 06."""

    def extract(self, inventory: PackageInventory, registry: SectionRegistry) -> StandardsProfile | None:
        section = self._find_standards_section(registry)
        if section is None:
            return None

        subfolder_structure = self._detect_subfolder_structure(inventory, section)

        samss: list[StandardReference] = []
        saes: list[StandardReference] = []
        saep: list[StandardReference] = []
        std_dwg: list[StandardReference] = []
        other: list[StandardReference] = []

        section_prefix = f"{section.folder_relative_path}/"
        for file_entry in inventory.files:
            if (
                file_entry.is_system_file
                or file_entry.is_mr_index
                or not file_entry.relative_path.startswith(section_prefix)
            ):
                continue

            reference = self._build_reference(
                filename=file_entry.filename,
                relative_path=file_entry.relative_path,
                subfolder_family=self._subfolder_family_for_file(
                    file_relative_path=file_entry.relative_path,
                    section_relative_path=section.folder_relative_path,
                ),
            )

            if reference.family == "samss":
                samss.append(reference)
            elif reference.family == "saes":
                saes.append(reference)
            elif reference.family == "saep":
                saep.append(reference)
            elif reference.family == "std_dwg":
                std_dwg.append(reference)
            else:
                other.append(reference)

        total_count = len(samss) + len(saes) + len(saep) + len(std_dwg) + len(other)
        return StandardsProfile(
            total_count=total_count,
            samss=samss,
            saes=saes,
            saep=saep,
            std_dwg=std_dwg,
            other=other,
            samss_count=len(samss),
            saes_count=len(saes),
            saep_count=len(saep),
            std_dwg_count=len(std_dwg),
            subfolder_structure=subfolder_structure,
        )

    @staticmethod
    def _find_standards_section(registry: SectionRegistry) -> SectionMatch | None:
        for section in registry.matched_sections:
            if section.canonical_key == "applicable_standards":
                return section
        return None

    def _detect_subfolder_structure(self, inventory: PackageInventory, section: SectionMatch) -> list[str]:
        section_prefix = f"{section.folder_relative_path}/"
        section_depth = section.folder_relative_path.count("/")

        return [
            folder.name
            for folder in inventory.folders
            if folder.relative_path.startswith(section_prefix)
            and folder.depth == section_depth + 1
            and _NUMBERED_SUBFOLDER_RE.match(folder.name) is not None
        ]

    def _build_reference(
        self,
        filename: str,
        relative_path: str,
        subfolder_family: str | None,
    ) -> StandardReference:
        standard_id: str
        family: str

        samss_match = _SAMSS_RE.search(filename)
        if samss_match is not None:
            family = "samss"
            standard_id = f"SAMSS-{samss_match.group(1)}"
        else:
            saes_match = _SAES_RE.search(filename)
            if saes_match is not None:
                family = "saes"
                standard_id = f"SAES-{saes_match.group(1).upper().replace('_', '-')}"
            else:
                saep_match = _SAEP_RE.search(filename)
                if saep_match is not None:
                    family = "saep"
                    standard_id = f"SAEP-{saep_match.group(1)}"
                else:
                    std_dwg_match = _STD_DWG_RE.search(filename)
                    if std_dwg_match is not None:
                        family = "std_dwg"
                        suffix = std_dwg_match.group(1)
                        standard_id = "STD DWG" if suffix is None else f"STD DWG-{suffix.upper()}"
                    elif subfolder_family == "std_dwg":
                        family = "std_dwg"
                        standard_id = self._fallback_standard_id(filename).upper().replace("_", " ")
                    else:
                        family = "other"
                        standard_id = self._fallback_standard_id(filename)

        return StandardReference(
            filename=filename,
            standard_id=standard_id,
            family=family,
            relative_path=relative_path,
            extraction_method=_EXTRACTION_METHOD,
        )

    @staticmethod
    def _subfolder_family_for_file(file_relative_path: str, section_relative_path: str) -> str | None:
        section_prefix = f"{section_relative_path}/"
        relative_suffix = file_relative_path[len(section_prefix):]
        first_segment = relative_suffix.split("/", 1)[0]
        match = _NUMBERED_SUBFOLDER_RE.match(first_segment)
        if match is None:
            return None

        label = match.group(2).lower()
        if "samss" in label:
            return "samss"
        if "saes" in label:
            return "saes"
        if "saep" in label:
            return "saep"
        if "std" in label:
            return "std_dwg"
        return "other"

    @staticmethod
    def _fallback_standard_id(filename: str) -> str:
        return Path(filename).stem
