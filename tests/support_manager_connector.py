from __future__ import annotations

from pathlib import Path

from src.connectors.manager_connector import ManagerConnector


class LocalFixtureManagerConnector(ManagerConnector):
    """Deterministic manager connector for local lifecycle-flow tests."""

    def __init__(self):
        super().__init__(base_url="http://local-fixtures")

    async def get_rfq_context(self, rfq_id: str) -> dict:
        return {
            "rfq_id": rfq_id,
            "rfq_code": f"RFQ-{rfq_id[:8].upper()}",
            "client_name": "GHI",
            "project_title": "Collection Vessel",
            "source_package_refs": [
                {
                    "reference": "local://source_package_sample_001",
                    "display_name": "source-package-sample-001.zip",
                    "stage_id": "stage-source-package",
                    "stage_name": "Inquiry / Offer Request Received",
                    "uploaded_at": "2026-03-24T10:45:00Z",
                }
            ],
            "created_at": "2026-03-24T11:00:00Z",
        }

    async def get_rfq_metadata(self, rfq_id: str) -> dict:
        return {
            "rfq_id": rfq_id,
            "rfq_code": f"RFQ-{rfq_id[:8].upper()}",
            "status": "In preparation",
            "client_name": "GHI",
            "title": "Collection Vessel",
            "created_at": "2026-03-24T11:00:00Z",
            "outcome_reason": None,
        }

    async def get_workbook_reference(self, rfq_id: str) -> dict:
        return {
            "workbook_ref": "local://workbook_sample_001",
            "filename": "ghi_workbook_32_sheets.xls",
            "upload_timestamp": "2026-03-24T11:55:00Z",
            "storage_reference": "local://workbook_sample_001",
            "stage_id": "stage-estimation",
            "stage_name": "Estimating",
        }

    async def get_workbook_context(
        self,
        rfq_id: str,
        workbook_ref: str | None = None,
        workbook_filename: str | None = None,
        uploaded_at: str | None = None,
    ) -> dict:
        effective_ref = workbook_ref or "local://workbook_sample_001"
        path = self.fetch_workbook_local_path(effective_ref)
        return {
            "rfq_id": rfq_id,
            "workbook_ref": effective_ref,
            "workbook_filename": workbook_filename or path.name,
            "uploaded_at": uploaded_at or "2026-03-24T11:55:00Z",
            "local_workbook_path": str(path),
            "rfq_display": {
                "rfq_code": f"RFQ-{rfq_id[:8].upper()}",
                "project_title": "Collection Vessel",
                "client_name": "GHI",
            },
        }

    def fetch_workbook_local_path(self, workbook_ref: str) -> Path:
        return super().fetch_workbook_local_path(workbook_ref or "local://workbook_sample_001")

    def fetch_package_local_path(self, package_ref: str) -> Path:
        return super().fetch_package_local_path(package_ref or "local://source_package_sample_001")
