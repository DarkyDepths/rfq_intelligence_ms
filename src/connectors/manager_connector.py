"""
manager_connector.py — Thin Read-Only Client to rfq_manager_ms

BACAB Layer: Connector (external system integration)

Responsibility:
    Provides a minimal, stable interface for fetching data from
    rfq_manager_ms. This is an architectural boundary — intelligence
    must not depend on manager's internal DB schema or ORM models.

    It may read only:
        - RFQ id and basic metadata (code, status, client name)
        - File references (blob storage paths, filenames)
        - Workbook reference (blob path, filename, upload timestamp)
        - Minimal display context (RFQ title, creation date)

    It must NOT:
        - Mirror or depend on manager's internal DB schema
        - Read manager's stage/workflow/subtask internals
        - Assume manager's response format is stable beyond the agreed contract
        - Import manager models or share ORM entities

Current status: STUB — not yet wired to actual manager API.

TODO:
    - Implement HTTP calls via httpx to manager API
    - Add error handling and timeout configuration
    - Define the agreed contract fields
"""

import os
from pathlib import Path


class ManagerConnector:
    """Thin read-only client to rfq_manager_ms. Fetches only what intelligence needs."""

    def __init__(self, base_url: str):
        self.base_url = base_url

    def _local_fixtures_root(self) -> Path:
        configured = os.getenv("LOCAL_FIXTURES_DIR")
        if configured:
            return Path(configured).resolve()
        return (Path(__file__).resolve().parents[2] / "local_fixtures").resolve()

    async def get_rfq_context(self, rfq_id: str) -> dict:
        """
        Fetch minimal, stable RFQ/source-package context for intelligence slices.

        Current implementation is a deterministic stub contract that can be
        replaced with real manager API calls later without changing callers.
        """
        return {
            "rfq_id": rfq_id,
            "rfq_code": f"RFQ-{rfq_id[:8].upper()}",
            "client_name": "Unknown client",
            "project_title": "RFQ context pending manager enrichment",
            "source_package_refs": [
                {
                    "reference": f"rfq-files/{rfq_id}/source-package.zip",
                    "display_name": "source-package.zip",
                }
            ],
            "created_at": None,
        }

    async def get_rfq_metadata(self, rfq_id: str) -> dict:
        """
        Fetch RFQ metadata and file references from manager.

        Returns a dict with: rfq_id, code, status, client_name,
        title, created_at, file_references.

        TODO: Call manager API for RFQ metadata + file references.
        """
        raise NotImplementedError("Manager connector not yet wired")

    async def get_workbook_reference(self, rfq_id: str) -> dict:
        """
        Fetch workbook file reference from manager.

        Returns a dict with: blob_path, filename, upload_timestamp.

        TODO: Call manager API for workbook file reference.
        """
        raise NotImplementedError("Manager connector not yet wired")

    async def get_workbook_context(
        self,
        rfq_id: str,
        workbook_ref: str | None = None,
        workbook_filename: str | None = None,
        uploaded_at: str | None = None,
    ) -> dict:
        """Return minimal workbook-uploaded context for deterministic processing."""
        effective_ref = workbook_ref or "local://workbook_sample_001"
        path = self.fetch_workbook_local_path(effective_ref)

        return {
            "rfq_id": rfq_id,
            "workbook_ref": effective_ref,
            "workbook_filename": workbook_filename or path.name,
            "uploaded_at": uploaded_at,
            "local_workbook_path": str(path),
            "rfq_display": {
                "rfq_code": f"RFQ-{rfq_id[:8].upper()}",
                "project_title": "Workbook context pending manager enrichment",
            },
        }

    def fetch_workbook_local_path(self, workbook_ref: str) -> Path:
        """Resolve workbook reference to a local development fixture path."""
        if workbook_ref and Path(workbook_ref).exists():
            return Path(workbook_ref).resolve()

        default_path = self._local_fixtures_root() / "workbook_uploaded" / "workbook_sample_001" / "ghi_workbook_32_sheets.xls"
        if workbook_ref.startswith("local://") and default_path.exists():
            return default_path
        if default_path.exists():
            return default_path

        raise FileNotFoundError(
            f"Could not resolve workbook reference '{workbook_ref}' to a local fixture path."
        )
