"""Section classification for package parser Stage B."""

from __future__ import annotations

from src.services.package_parser.contracts import (
    FolderEntry,
    PackageInventory,
    SectionMatch,
    SectionRegistry,
)


NUMBERED_SECTION_MAP: dict[int, str] = {
    0: "approval_sheet",
    1: "mr_checklist",
    2: "description_bom",
    3: "rvl",
    4: "specs_datasheets",
    5: "project_drawings",
    6: "applicable_standards",
    7: "sa175_forms",
    8: "nmr",
    9: "spdp",
    10: "qaqc_requirements",
    11: "general_requirements",
    12: "vendor_doc_requirements",
    13: "routing_slip",
    14: "packing_specs",
    15: "notes_to_vendor",
}

ALIAS_MAP: dict[str, tuple[str, ...]] = {
    "approval_sheet": ("approval", "rfa"),
    "mr_checklist": ("checklist",),
    "description_bom": ("description", "bom", "bill of material"),
    "rvl": ("rvl", "restricted vendor", "vendor list"),
    "specs_datasheets": ("spec", "datasheet", "data sheet"),
    "project_drawings": ("drawing", "p&id"),
    "applicable_standards": ("standard", "applicable"),
    "sa175_forms": ("sa-175", "sa175", "175 form"),
    "nmr": ("nmr",),
    "spdp": ("spdp",),
    "qaqc_requirements": ("qaqc", "qa/qc", "quality"),
    "general_requirements": ("general req",),
    "vendor_doc_requirements": ("vendor doc", "vendor document req"),
    "routing_slip": ("routing", "route slip"),
    "packing_specs": ("packing", "packaging"),
    "notes_to_vendor": ("notes to vendor", "vendor notes"),
    "revision_history": ("revision", "comment log", "mr comment"),
}

EXPECTED_CANONICAL_KEYS: set[str] = set(NUMBERED_SECTION_MAP.values()) | {"revision_history"}


class SectionClassifier:
    """Classify top-level package folders into canonical sections."""

    def classify(self, inventory: PackageInventory) -> SectionRegistry:
        top_level_folders = sorted((f for f in inventory.folders if f.depth == 0), key=lambda f: f.relative_path.lower())

        matched_sections: list[SectionMatch] = []
        unmatched_folders: list[FolderEntry] = []

        numbered_section_count = 0
        unnumbered_section_count = 0

        for folder in top_level_folders:
            if folder.number_prefix is not None:
                numbered_section_count += 1
                canonical_key = NUMBERED_SECTION_MAP.get(folder.number_prefix)
                if canonical_key is None:
                    unmatched_folders.append(folder)
                    continue
                matched_sections.append(
                    self._build_section_match(
                        inventory=inventory,
                        folder=folder,
                        canonical_key=canonical_key,
                        match_method="number_prefix",
                        match_confidence="high",
                    )
                )
                continue

            unnumbered_section_count += 1
            canonical_key = self._match_alias(folder.name)
            if canonical_key is None:
                unmatched_folders.append(folder)
                continue

            matched_sections.append(
                self._build_section_match(
                    inventory=inventory,
                    folder=folder,
                    canonical_key=canonical_key,
                    match_method="name_heuristic",
                    match_confidence="medium",
                )
            )

        matched_keys = {section.canonical_key for section in matched_sections}
        missing_canonical_sections = sorted(EXPECTED_CANONICAL_KEYS - matched_keys)
        total_mr_index_count = sum(1 for section in matched_sections if section.mr_index_present)

        return SectionRegistry(
            matched_sections=matched_sections,
            unmatched_folders=unmatched_folders,
            missing_canonical_sections=missing_canonical_sections,
            numbered_section_count=numbered_section_count,
            unnumbered_section_count=unnumbered_section_count,
            total_mr_index_count=total_mr_index_count,
        )

    def _build_section_match(
        self,
        inventory: PackageInventory,
        folder: FolderEntry,
        canonical_key: str,
        match_method: str,
        match_confidence: str,
    ) -> SectionMatch:
        prefix = f"{folder.relative_path}/"

        files_in_folder = [
            file
            for file in inventory.files
            if file.relative_path.startswith(prefix)
            and not file.is_system_file
        ]

        mr_index_present = any(file.is_mr_index for file in files_in_folder)
        content_file_count = sum(1 for file in files_in_folder if not file.is_mr_index)
        has_subfolders = folder.subfolder_count > 0

        return SectionMatch(
            folder_name=folder.name,
            folder_relative_path=folder.relative_path,
            canonical_key=canonical_key,
            match_method=match_method,
            match_confidence=match_confidence,
            number_prefix=folder.number_prefix,
            file_count=content_file_count,
            mr_index_present=mr_index_present,
            has_subfolders=has_subfolders,
        )

    @staticmethod
    def _match_alias(folder_name: str) -> str | None:
        normalized = folder_name.lower()
        for canonical_key, aliases in ALIAS_MAP.items():
            if any(alias in normalized for alias in aliases):
                return canonical_key
        return None
