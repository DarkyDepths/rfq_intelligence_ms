"""
intake_service.py — RFQ Intake Parsing Service

BACAB Layer: Service (domain logic, called by controllers and event handlers)

Responsibility:
    Parses the ZIP/MR package from an RFQ and produces the rfq_intake_profile artifact.
    Combines deterministic extraction (folder tree, BOM, standards filenames) with
    LLM extraction for unstructured documents when needed.

Current status: partially implemented for deterministic V1 intake parsing and
truthful fallback content when only manager references are available.

TODO:
    - Intake parsing pipeline
    - Document understanding extraction
    - Canonical field normalization
    - Evidence and quality/gap tracking
    - Wire to artifact_datasource for persistence
"""

from datetime import datetime, timezone
from uuid import UUID

from src.datasources.artifact_datasource import ArtifactDatasource
from src.connectors.manager_connector import ManagerConnector
from src.services.package_parser.parser_orchestrator import PackageParserOrchestrator


class IntakeService:
    """Parses ZIP/MR packages and produces rfq_intake_profile artifacts."""

    def __init__(
        self,
        datasource: ArtifactDatasource,
        connector: ManagerConnector,
        package_parser: PackageParserOrchestrator | None = None,
    ):
        self.datasource = datasource
        self.connector = connector
        self.package_parser = package_parser or PackageParserOrchestrator()

    def reprocess(self, rfq_id: str) -> dict:
        """Accept manual intake reprocess request (stub)."""
        return {
            "status": "accepted",
            "message": "Reprocess request received (stub only — not yet implemented)",
        }

    async def get_rfq_context(self, rfq_id: str) -> dict:
        """Read minimal RFQ context through the manager connector boundary."""
        return await self.connector.get_rfq_context(rfq_id)

    def build_intake_profile_from_rfq_created(
        self,
        rfq_context: dict,
        event_meta: dict,
        commit: bool = True,
    ):
        """Build and persist an intake profile with package parsing when available."""
        rfq_id = UUID(str(rfq_context["rfq_id"]))
        source_package_refs = rfq_context.get("source_package_refs", [])
        primary_reference = source_package_refs[0]["reference"] if source_package_refs else None
        known_fields = {
            "rfq_code": rfq_context.get("rfq_code"),
            "client_name": rfq_context.get("client_name"),
            "project_title": rfq_context.get("project_title"),
            "created_at": rfq_context.get("created_at"),
        }

        package_path = None
        if primary_reference:
            try:
                package_path = self.connector.fetch_package_local_path(primary_reference)
            except FileNotFoundError:
                package_path = None

        artifact_status = "partial"
        if package_path is None:
            content = self._build_stub_content(
                rfq_id=rfq_id,
                source_package_refs=source_package_refs,
                known_fields=known_fields,
                event_meta=event_meta,
            )
        else:
            try:
                envelope = self.package_parser.parse(package_path, str(rfq_id))
                content = self._build_enriched_content(
                    rfq_id=rfq_id,
                    source_package_refs=source_package_refs,
                    known_fields=known_fields,
                    event_meta=event_meta,
                    envelope=envelope,
                )
                artifact_status = "complete" if envelope["parser_report"]["status"] == "parsed_ok" else "partial"
            except Exception:
                content = self._build_parser_failed_content(
                    rfq_id=rfq_id,
                    source_package_refs=source_package_refs,
                    known_fields=known_fields,
                    event_meta=event_meta,
                )

        artifact = self.datasource.create_new_artifact_version(
            rfq_id=rfq_id,
            artifact_type="rfq_intake_profile",
            content=content,
            status=artifact_status,
            source_event_type=event_meta["event_type"],
            source_event_id=event_meta["event_id"],
        )
        if commit:
            self.datasource.db.commit()
            self.datasource.db.refresh(artifact)
        return artifact

    def _build_stub_content(
        self,
        rfq_id: UUID,
        source_package_refs: list[dict],
        known_fields: dict,
        event_meta: dict,
    ) -> dict:
        return {
            "artifact_meta": {
                "artifact_type": "rfq_intake_profile",
                "slice": "rfq.created_vertical_slice_v1",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source_event_id": event_meta["event_id"],
                "source_event_type": event_meta["event_type"],
            },
            "source_package": {
                "references": source_package_refs,
                "primary_reference": source_package_refs[0]["reference"] if source_package_refs else None,
                "visibility_level": "reference_only",
            },
            "package_structure": {
                "status": "limited",
                "summary": "Source package structure is not parsed yet in this slice.",
                "reference_count": len(source_package_refs),
            },
            "document_understanding": {
                "status": "not_ready",
                "summary": "Deep document parsing is not implemented in this first vertical slice.",
            },
            "canonical_project_profile": {
                "rfq_id": str(rfq_id),
                "rfq_code": known_fields["rfq_code"],
                "client_name": known_fields["client_name"],
                "project_title": known_fields["project_title"],
                "created_at": known_fields["created_at"],
            },
            "field_evidence": [
                {
                    "field": "rfq_id",
                    "value": str(rfq_id),
                    "source": "rfq_manager_context",
                    "confidence": "high",
                },
                {
                    "field": "source_package_refs",
                    "value": source_package_refs,
                    "source": "rfq_manager_context",
                    "confidence": "medium",
                },
            ],
            "quality_and_gaps": {
                "status": "partial",
                "known_data_points": [
                    "rfq identifiers",
                    "source package references",
                    "minimal display metadata",
                ],
                "gaps": [
                    "deep file inventory",
                    "document extraction",
                    "structured compliance extraction",
                ],
            },
            "downstream_readiness": {
                "briefing_ready": True,
                "workbook_comparison_ready": False,
                "historical_matching_ready": False,
                "requires_human_review": True,
            },
        }

    def _build_enriched_content(
        self,
        rfq_id: UUID,
        source_package_refs: list[dict],
        known_fields: dict,
        event_meta: dict,
        envelope: dict,
    ) -> dict:
        inventory = envelope["package_inventory"]
        identity = envelope["package_identity"]
        registry = envelope["section_registry"]
        standards = envelope["standards_profile"]
        bom = envelope["bom_profile"]
        rvl = envelope["rvl_profile"]
        sa175 = envelope["sa175_profile"]
        compliance = envelope["compliance_profile"]
        deviation = envelope["deviation_profile"]
        parser_report = envelope["parser_report"]
        cross_checks = parser_report["cross_checks"]

        review_flags = self._build_review_flags(cross_checks)
        known_data_points = self._build_known_data_points(
            standards=standards,
            bom=bom,
            rvl=rvl,
            sa175=sa175,
            compliance=compliance,
        )

        return {
            "artifact_meta": {
                "artifact_type": "rfq_intake_profile",
                "slice": "rfq.created_package_parsed_v1",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source_event_id": event_meta["event_id"],
                "source_event_type": event_meta["event_type"],
                "parser_version": envelope["parser_version"],
            },
            "source_package": {
                "references": source_package_refs,
                "primary_reference": source_package_refs[0]["reference"] if source_package_refs else None,
                "visibility_level": "parsed",
                "input_type": envelope["input_type"],
                "package_root_name": inventory["package_root_name"],
            },
            "package_identity": {
                "mr_number": identity.get("mr_number"),
                "mr_number_short": identity.get("mr_number_short"),
                "revision": identity.get("revision"),
                "material_description": identity.get("material_description"),
                "project_code": identity.get("project_code"),
                "mr_number_mismatches": identity.get("mr_number_mismatches", []),
            },
            "package_structure": {
                "status": "parsed" if parser_report["status"] != "failed" else "failed",
                "total_files": inventory["total_files"],
                "total_files_raw": inventory["total_files_raw"],
                "system_file_count": inventory["system_file_count"],
                "total_folders": inventory["total_folders"],
                "total_size_bytes": inventory["total_size_bytes"],
                "numbered_sections_found": registry["numbered_section_count"],
                "missing_sections": registry["missing_canonical_sections"],
                "extra_unnumbered_sections": [folder["name"] for folder in registry["unmatched_folders"]],
                "mr_index_coverage": f"{registry['total_mr_index_count']}/{registry['numbered_section_count']}",
                "file_extension_summary": inventory["file_extension_counts"],
                "section_registry": registry,
            },
            "document_understanding": {
                "status": "partial_deterministic",
                "summary": (
                    "Deterministic extraction from package structure, spreadsheets, and filename patterns. "
                    "LLM-based document content extraction not yet implemented."
                ),
                "bom_profile": bom,
                "rvl_profile": rvl,
                "standards_profile": standards,
                "sa175_profile": sa175,
                "compliance_profile": compliance,
                "deviation_profile": deviation,
            },
            "canonical_project_profile": {
                "rfq_id": str(rfq_id),
                "rfq_code": known_fields["rfq_code"],
                "client_name": known_fields["client_name"],
                "project_title": known_fields["project_title"],
                "created_at": known_fields["created_at"],
                "material_description": identity.get("material_description"),
                "tag_numbers": bom["tag_numbers_found"] if bom else [],
                "design_codes": bom["design_codes_found"] if bom else [],
                "nine_com_codes": self._ordered_unique(
                    [
                        *(bom["nine_com_codes_found"] if bom else []),
                        *(([compliance["nine_com"]] if compliance and compliance.get("nine_com") else [])),
                        *(rvl["nine_com_codes"] if rvl else []),
                    ]
                ),
                "location": (bom["locations_found"][0] if bom and bom["locations_found"] else None),
                "vendor_count": (rvl["total_vendors"] if rvl else 0),
                "standards_count": {
                    "samss": standards["samss_count"] if standards else 0,
                    "saes": standards["saes_count"] if standards else 0,
                    "saep": standards["saep_count"] if standards else 0,
                    "std_dwg": standards["std_dwg_count"] if standards else 0,
                },
            },
            "field_evidence": self._build_field_evidence(identity, bom, rvl, cross_checks),
            "quality_and_gaps": {
                "status": "partial",
                "known_data_points": known_data_points,
                "gaps": [
                    "specs/datasheet content extraction",
                    "QAQC requirement content",
                    "general requirement content",
                    "scope of supply content",
                ],
                "review_flags": review_flags,
            },
            "downstream_readiness": {
                "briefing_ready": True,
                "workbook_comparison_ready": bom is not None and rvl is not None,
                "historical_matching_ready": False,
                "requires_human_review": parser_report["status"] != "parsed_ok" or bool(review_flags),
            },
            "parser_report_status": parser_report["status"],
        }

    def _build_parser_failed_content(
        self,
        rfq_id: UUID,
        source_package_refs: list[dict],
        known_fields: dict,
        event_meta: dict,
    ) -> dict:
        content = self._build_stub_content(
            rfq_id=rfq_id,
            source_package_refs=source_package_refs,
            known_fields=known_fields,
            event_meta=event_meta,
        )
        content["artifact_meta"]["slice"] = "rfq.created_package_parsed_v1"
        content["artifact_meta"]["parser_version"] = "package-parser-v1.0"
        content["package_structure"] = {
            "status": "failed",
            "summary": "Package parser failed; falling back to reference-only intake content.",
            "reference_count": len(source_package_refs),
        }
        content["document_understanding"] = {
            "status": "not_ready",
            "summary": "Package parser failed before deterministic extraction completed.",
        }
        content["quality_and_gaps"]["gaps"] = [
            *content["quality_and_gaps"]["gaps"],
            "deterministic package parsing failed",
        ]
        content["quality_and_gaps"]["review_flags"] = ["Package parser failure"]
        content["parser_report_status"] = "failed"
        return content

    @staticmethod
    def _build_field_evidence(identity: dict, bom: dict | None, rvl: dict | None, cross_checks: list[dict]) -> list[dict]:
        evidence = [
            {
                "field": "mr_number",
                "value": identity.get("mr_number"),
                "source": "package_root_name",
                "method": "deterministic",
                "confidence": "high",
            }
        ]

        if bom and bom.get("tag_numbers_found"):
            evidence.append(
                {
                    "field": "tag_numbers",
                    "value": bom["tag_numbers_found"],
                    "source": "02_BOM spreadsheet",
                    "method": "deterministic",
                    "confidence": "high",
                }
            )

        if rvl:
            evidence.append(
                {
                    "field": "vendor_count",
                    "value": rvl.get("total_vendors"),
                    "source": "03_RVL docx table",
                    "method": "deterministic",
                    "confidence": "high",
                }
            )

        mr_mismatch = next(
            (
                check
                for check in cross_checks
                if check["code"] == "PACKAGE_MR_vs_RVL_MR" and check["status"] == "warn"
            ),
            None,
        )
        if mr_mismatch is not None:
            evidence.append(
                {
                    "field": "mr_number_mismatch",
                    "value": f"{mr_mismatch['right_value']} in RVL vs {mr_mismatch['left_value']} in package",
                    "source": "cross_check",
                    "method": "deterministic",
                    "confidence": "high",
                }
            )

        return evidence

    @staticmethod
    def _build_review_flags(cross_checks: list[dict]) -> list[str]:
        flags: list[str] = []
        for check in cross_checks:
            if check["status"] not in {"warn", "fail"}:
                continue
            if check["code"] == "PACKAGE_MR_vs_RVL_MR":
                flags.append("MR number mismatch between package and RVL")
            else:
                flags.append(check["code"])
        return flags

    @staticmethod
    def _build_known_data_points(
        standards: dict | None,
        bom: dict | None,
        rvl: dict | None,
        sa175: dict | None,
        compliance: dict | None,
    ) -> list[str]:
        known = ["package identity"]
        if bom is not None:
            known.append("BOM line items")
        if rvl is not None:
            known.append("RVL vendors")
        if standards is not None:
            known.append("standards list")
        if sa175 is not None:
            known.append("SA-175 forms")
        if compliance is not None:
            known.append("compliance items")
        return known

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

    async def process_intake(self, rfq_id: str, event_payload: dict) -> None:
        """
        Run the full intake parsing pipeline for an RFQ.

        Steps (sequential):
            1. Fetch RFQ metadata + file references from manager
            2. Parse package structure (deterministic)
            3. Extract document understanding (heuristic + LLM)
            4. Normalize into canonical_project_profile
            5. Build field_evidence and quality_and_gaps
            6. Persist rfq_intake_profile artifact

        TODO: Implement pipeline.
        """
        raise NotImplementedError("Intake parsing not yet implemented")
