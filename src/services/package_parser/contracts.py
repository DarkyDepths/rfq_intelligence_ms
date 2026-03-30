"""Frozen typed contracts for deterministic package parser v1.0."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from src.services.package_parser.issues import PackageParserReport

RootFileRole = Literal[
    "mr_index_root",
    "internal_review_file",
    "unclassified_root_extra",
]

MatchMethod = Literal[
    "number_prefix",
    "name_heuristic",
    "unmatched",
]

MatchConfidence = Literal["high", "medium", "low"]

StandardFamily = Literal["samss", "saes", "saep", "std_dwg", "other"]


@dataclass(frozen=True)
class FileEntry:
    """Single file in the package."""

    relative_path: str
    filename: str
    extension: str
    size_bytes: int
    depth: int
    parent_folder: str
    is_mr_index: bool = False
    mr_number_in_filename: str | None = None
    section_prefix: str | None = None
    is_system_file: bool = False
    root_role: RootFileRole | None = None


@dataclass(frozen=True)
class FolderEntry:
    """Single folder in the package."""

    relative_path: str
    name: str
    depth: int
    file_count: int
    subfolder_count: int
    number_prefix: int | None = None
    label: str | None = None


@dataclass(frozen=True)
class PackageInventory:
    """Complete raw inventory of the MR package."""

    package_root_name: str
    input_type: str
    total_files: int
    total_files_raw: int
    total_folders: int
    total_size_bytes: int
    files: list[FileEntry]
    folders: list[FolderEntry]
    root_files: list[FileEntry]
    file_extension_counts: dict[str, int]
    system_file_count: int
    scanned_at: str


@dataclass(frozen=True)
class SectionMatch:
    """Mapping of one actual folder to a canonical section."""

    folder_name: str
    folder_relative_path: str
    canonical_key: str
    match_method: MatchMethod
    match_confidence: MatchConfidence
    number_prefix: int | None
    file_count: int
    mr_index_present: bool
    has_subfolders: bool


@dataclass(frozen=True)
class SectionRegistry:
    """Result of structure recognition."""

    matched_sections: list[SectionMatch]
    unmatched_folders: list[FolderEntry]
    missing_canonical_sections: list[str]
    numbered_section_count: int
    unnumbered_section_count: int
    total_mr_index_count: int


@dataclass(frozen=True)
class PackageIdentity:
    """Identity fields extracted from package root and file patterns."""

    mr_number: str | None = None
    mr_number_short: str | None = None
    revision: str | None = None
    material_description: str | None = None
    project_code: str | None = None
    package_root_name: str | None = None
    mr_numbers_in_filenames: list[str] = field(default_factory=list)
    mr_number_mismatches: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class StandardReference:
    """Single standard document detected by filename."""

    filename: str
    standard_id: str
    family: StandardFamily
    relative_path: str
    extraction_method: str


@dataclass(frozen=True)
class StandardsProfile:
    """All standards detected in the package."""

    total_count: int
    samss: list[StandardReference]
    saes: list[StandardReference]
    saep: list[StandardReference]
    std_dwg: list[StandardReference]
    other: list[StandardReference]
    samss_count: int
    saes_count: int
    saep_count: int
    std_dwg_count: int
    subfolder_structure: list[str]


@dataclass(frozen=True)
class BomLineItem:
    """Single line from the Bill of Materials spreadsheet."""

    sheet_row: int
    mr_line_item: str | None = None
    line_item: str | None = None
    nine_com: str | None = None
    plant_no: str | None = None
    pipeline: str | None = None
    design_code: str | None = None
    service: str | None = None
    material_type: str | None = None
    location: str | None = None
    technical_spec: str | None = None
    tag_number: str | None = None
    data_sheet: str | None = None
    reference_drawings: str | None = None
    quantity: float | None = None


@dataclass(frozen=True)
class BomProfile:
    """Extracted BOM data from folder 02."""

    source_file: str
    sheet_name: str
    line_items: list[BomLineItem]
    total_line_items: int
    tag_numbers_found: list[str]
    nine_com_codes_found: list[str]
    design_codes_found: list[str]
    locations_found: list[str]


@dataclass(frozen=True)
class RvlVendorEntry:
    """Single vendor from the Restricted Vendor List."""

    nine_com: str | None = None
    material_description: str | None = None
    manufacturer_id: str | None = None
    vendor_name: str | None = None
    country_code: str | None = None
    country_name: str | None = None


@dataclass(frozen=True)
class RvlProfile:
    """Extracted RVL data from folder 03."""

    source_file: str
    source_format: str
    vendors: list[RvlVendorEntry]
    total_vendors: int
    unique_vendor_names: list[str]
    unique_countries: list[str]
    nine_com_codes: list[str]
    mr_number_in_rvl: str | None = None


@dataclass(frozen=True)
class Sa175FormEntry:
    """Single SA-175 form detected by filename."""

    filename: str
    form_number: str
    relative_path: str


@dataclass(frozen=True)
class Sa175Profile:
    """SA-175 forms detected in folder 07."""

    forms: list[Sa175FormEntry]
    total_count: int
    form_numbers: list[str]


@dataclass(frozen=True)
class ComplianceLineItem:
    """Single compliance requirement from the TBC compliance sheet."""

    sheet_row: int
    item_no: str | None = None
    description: str | None = None
    specified_requirement: str | None = None
    section_label: str | None = None


@dataclass(frozen=True)
class ComplianceProfile:
    """Extracted compliance data from folder 15 TBC compliance sheet."""

    source_file: str
    line_items: list[ComplianceLineItem]
    total_items: int
    section_labels: list[str]
    material_description: str | None = None
    mr_number: str | None = None
    nine_com: str | None = None


@dataclass(frozen=True)
class DeviationProfile:
    """Metadata extracted from the Deviation List spreadsheet in folder 15."""

    source_file: str
    total_rows: int
    has_vendor_entries: bool
    bi_number: str | None = None
    project_title: str | None = None
    mr_number: str | None = None
    material_title: str | None = None


@dataclass(frozen=True)
class PackageParseEnvelope:
    """Top-level output of the package parser orchestrator."""

    rfq_id: str
    parser_version: str
    parsed_at: str
    input_type: str
    input_path: str | None
    package_inventory: PackageInventory
    package_identity: PackageIdentity
    section_registry: SectionRegistry
    standards_profile: StandardsProfile | None
    bom_profile: BomProfile | None
    rvl_profile: RvlProfile | None
    sa175_profile: Sa175Profile | None
    compliance_profile: ComplianceProfile | None
    deviation_profile: DeviationProfile | None
    parser_report: PackageParserReport


__all__ = [
    "BomLineItem",
    "BomProfile",
    "ComplianceLineItem",
    "ComplianceProfile",
    "DeviationProfile",
    "FileEntry",
    "FolderEntry",
    "MatchConfidence",
    "MatchMethod",
    "PackageIdentity",
    "PackageInventory",
    "PackageParseEnvelope",
    "RootFileRole",
    "RvlProfile",
    "RvlVendorEntry",
    "Sa175FormEntry",
    "Sa175Profile",
    "SectionMatch",
    "SectionRegistry",
    "StandardFamily",
    "StandardReference",
    "StandardsProfile",
]
