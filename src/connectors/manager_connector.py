"""
manager_connector.py — Thin Read-Only Client to rfq_manager_ms

BACAB Layer: Connector (external system integration)

Responsibility:
    Provides a minimal, stable interface for fetching data from
    rfq_manager_ms. This is an architectural boundary — intelligence
    must not depend on manager's internal DB schema or ORM models.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import httpx

from src.config.settings import settings
from src.utils.exceptions import NotFoundError


class ManagerConnector:
    """Thin read-only client to rfq_manager_ms."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.api_base_url = f"{self.base_url}/rfq-manager/v1"
        self.timeout_seconds = settings.MANAGER_REQUEST_TIMEOUT_SECONDS

    def _local_fixtures_root(self) -> Path:
        configured = os.getenv("LOCAL_FIXTURES_DIR")
        if configured:
            return Path(configured).resolve()
        return (Path(__file__).resolve().parents[2] / "local_fixtures").resolve()

    def _manager_uploads_mount_path(self) -> Path:
        configured = os.getenv("MANAGER_UPLOADS_MOUNT_PATH") or settings.MANAGER_UPLOADS_MOUNT_PATH
        return Path(configured).resolve()

    async def _get_json(self, path: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(f"{self.api_base_url}{path}")
        response.raise_for_status()
        return response.json()

    async def _get_rfq_detail(self, rfq_id: str) -> dict:
        return await self._get_json(f"/rfqs/{rfq_id}")

    async def _list_stage_summaries(self, rfq_id: str) -> list[dict]:
        payload = await self._get_json(f"/rfqs/{rfq_id}/stages")
        return payload.get("data", [])

    async def _get_stage_detail(self, rfq_id: str, stage_id: str) -> dict:
        return await self._get_json(f"/rfqs/{rfq_id}/stages/{stage_id}")

    async def _list_all_stage_files(self, rfq_id: str) -> list[dict]:
        stage_summaries = await self._list_stage_summaries(rfq_id)
        files: list[dict] = []
        for stage in stage_summaries:
            detail = await self._get_stage_detail(rfq_id, stage["id"])
            for file_item in detail.get("files", []):
                files.append(
                    {
                        **file_item,
                        "stage_id": stage["id"],
                        "stage_name": stage.get("name"),
                    }
                )
        return files

    @staticmethod
    def _normalize_storage_reference(reference: str) -> str:
        normalized = (reference or "").strip().replace("\\", "/").lstrip("/")
        if normalized.startswith("uploads/"):
            normalized = normalized[len("uploads/") :]
        return normalized

    def _resolve_shared_upload_path(self, storage_reference: str | None) -> Path | None:
        if not storage_reference:
            return None

        normalized = self._normalize_storage_reference(storage_reference)
        if not normalized:
            return None

        direct_path = Path(normalized)
        if direct_path.exists():
            return direct_path.resolve()

        mounted = (self._manager_uploads_mount_path() / normalized).resolve()
        if mounted.exists():
            return mounted

        return None

    @staticmethod
    def _parse_uploaded_at(value: str | None) -> datetime:
        if not value:
            return datetime.now(timezone.utc)
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return datetime.now(timezone.utc)

    @staticmethod
    def _sort_files_by_uploaded_at(files: list[dict]) -> list[dict]:
        return sorted(
            files,
            key=lambda item: ManagerConnector._parse_uploaded_at(item.get("uploaded_at")),
            reverse=True,
        )

    @staticmethod
    def _to_source_package_ref(file_item: dict) -> dict:
        storage_reference = file_item.get("storage_reference")
        return {
            "reference": storage_reference or file_item.get("download_url"),
            "display_name": file_item.get("filename") or "source-package.zip",
            "stage_id": file_item.get("stage_id"),
            "stage_name": file_item.get("stage_name"),
            "uploaded_at": file_item.get("uploaded_at"),
        }

    async def get_rfq_context(self, rfq_id: str) -> dict:
        """Fetch minimal, stable RFQ/source-package context for intelligence slices."""
        rfq = await self._get_rfq_detail(rfq_id)
        stage_files = await self._list_all_stage_files(rfq_id)
        source_package_files = [
            file_item for file_item in stage_files if file_item.get("type") == "Client RFQ"
        ]

        return {
            "rfq_id": rfq_id,
            "rfq_code": rfq.get("rfq_code"),
            "client_name": rfq.get("client"),
            "project_title": rfq.get("name"),
            "source_package_refs": [
                self._to_source_package_ref(file_item)
                for file_item in self._sort_files_by_uploaded_at(source_package_files)
            ],
            "created_at": rfq.get("created_at"),
        }

    async def get_rfq_metadata(self, rfq_id: str) -> dict:
        rfq = await self._get_rfq_detail(rfq_id)
        return {
            "rfq_id": rfq_id,
            "rfq_code": rfq.get("rfq_code"),
            "status": rfq.get("status"),
            "client_name": rfq.get("client"),
            "title": rfq.get("name"),
            "created_at": rfq.get("created_at"),
            "outcome_reason": rfq.get("outcome_reason"),
        }

    async def get_workbook_reference(self, rfq_id: str) -> dict:
        stage_files = await self._list_all_stage_files(rfq_id)
        workbook_files = [
            file_item
            for file_item in stage_files
            if file_item.get("type") == "Estimation Workbook"
        ]
        if not workbook_files:
            raise NotFoundError(f"No estimation workbook file found for RFQ '{rfq_id}'")

        latest = self._sort_files_by_uploaded_at(workbook_files)[0]
        return {
            "workbook_ref": latest.get("storage_reference") or latest.get("download_url"),
            "filename": latest.get("filename"),
            "upload_timestamp": latest.get("uploaded_at"),
            "storage_reference": latest.get("storage_reference"),
            "stage_id": latest.get("stage_id"),
            "stage_name": latest.get("stage_name"),
        }

    async def get_workbook_context(
        self,
        rfq_id: str,
        workbook_ref: str | None = None,
        workbook_filename: str | None = None,
        uploaded_at: str | None = None,
    ) -> dict:
        """Return minimal workbook-uploaded context for deterministic processing."""
        rfq = await self._get_rfq_detail(rfq_id)

        if workbook_ref and workbook_filename and uploaded_at:
            effective_ref = workbook_ref
            effective_filename = workbook_filename
            effective_uploaded_at = uploaded_at
        else:
            workbook_reference = await self.get_workbook_reference(rfq_id)
            effective_ref = workbook_ref or workbook_reference["workbook_ref"]
            effective_filename = workbook_filename or workbook_reference["filename"]
            effective_uploaded_at = uploaded_at or workbook_reference["upload_timestamp"]

        path = self.fetch_workbook_local_path(effective_ref)

        return {
            "rfq_id": rfq_id,
            "workbook_ref": effective_ref,
            "workbook_filename": effective_filename or path.name,
            "uploaded_at": effective_uploaded_at,
            "local_workbook_path": str(path),
            "rfq_display": {
                "rfq_code": rfq.get("rfq_code"),
                "project_title": rfq.get("name"),
                "client_name": rfq.get("client"),
            },
        }

    def fetch_workbook_local_path(self, workbook_ref: str) -> Path:
        """Resolve workbook reference to a local development fixture path."""
        if workbook_ref and Path(workbook_ref).exists():
            return Path(workbook_ref).resolve()

        shared_upload = self._resolve_shared_upload_path(workbook_ref)
        if shared_upload is not None:
            return shared_upload

        default_path = (
            self._local_fixtures_root()
            / "workbook_uploaded"
            / "workbook_sample_001"
            / "ghi_workbook_32_sheets.xls"
        )
        if workbook_ref.startswith("local://") and default_path.exists():
            return default_path
        if default_path.exists():
            return default_path

        raise FileNotFoundError(
            f"Could not resolve workbook reference '{workbook_ref}' to a local path."
        )

    def fetch_package_local_path(self, package_ref: str) -> Path:
        """Resolve package reference to a local development fixture path."""
        if package_ref and Path(package_ref).exists():
            return Path(package_ref).resolve()

        shared_upload = self._resolve_shared_upload_path(package_ref)
        if shared_upload is not None:
            return shared_upload

        fixture_package_root = (
            self._local_fixtures_root()
            / "rfq_created"
            / "source_package_sample_001"
            / "SA-AYPP-6-MR-022_COLLECTION VESSEL - CDS-REV-00"
        )
        local_ref_map = {
            "local://source_package_sample_001": fixture_package_root,
        }

        resolved = local_ref_map.get(package_ref)
        if resolved is not None and resolved.exists():
            return resolved.resolve()

        raise FileNotFoundError(
            f"Could not resolve package reference '{package_ref}' to a local path."
        )
