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


class ManagerConnector:
    """Thin read-only client to rfq_manager_ms. Fetches only what intelligence needs."""

    def __init__(self, base_url: str):
        self.base_url = base_url

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
