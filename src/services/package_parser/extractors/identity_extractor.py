"""Package identity extraction for parser Stage B."""

from __future__ import annotations

import re

from src.services.package_parser.contracts import PackageIdentity, PackageInventory


_ROOT_IDENTITY_RE = re.compile(r"^([\w-]+-MR-\d+)[_\s]+(.+?)[-\s]*REV[-\s]*(\d+)\s*$")
_PROJECT_CODE_RE = re.compile(r"^(.+)-MR-\d+$")
_MR_SHORT_RE = re.compile(r"MR-\d+$")


class IdentityExtractor:
    """Extract package identity from root name and filename-level MR detections."""

    def extract(self, inventory: PackageInventory) -> PackageIdentity:
        package_root_name = inventory.package_root_name

        mr_number: str | None = None
        revision: str | None = None
        material_description: str | None = None
        project_code: str | None = None
        mr_number_short: str | None = None

        root_match = _ROOT_IDENTITY_RE.match(package_root_name)
        if root_match is not None:
            mr_number = root_match.group(1)
            material_description = root_match.group(2).strip()
            revision = root_match.group(3)

            mr_short_match = _MR_SHORT_RE.search(mr_number)
            if mr_short_match is not None:
                mr_number_short = mr_short_match.group(0)

            project_match = _PROJECT_CODE_RE.match(mr_number)
            if project_match is not None:
                project_code = project_match.group(1)

        mr_numbers_in_filenames = self._ordered_unique(
            [entry.mr_number_in_filename for entry in inventory.files if entry.mr_number_in_filename is not None]
        )

        mr_number_mismatches = self._ordered_unique(
            [
                detected
                for detected in mr_numbers_in_filenames
                if detected != mr_number_short
            ]
        )

        return PackageIdentity(
            mr_number=mr_number,
            mr_number_short=mr_number_short,
            revision=revision,
            material_description=material_description,
            project_code=project_code,
            package_root_name=package_root_name,
            mr_numbers_in_filenames=mr_numbers_in_filenames,
            mr_number_mismatches=mr_number_mismatches,
        )

    @staticmethod
    def _ordered_unique(values: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            ordered.append(value)
        return ordered
