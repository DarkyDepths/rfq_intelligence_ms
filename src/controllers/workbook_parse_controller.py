"""Thin controller for manual deterministic workbook parsing."""

from __future__ import annotations

from src.services.workbook_parser.parser_orchestrator import WorkbookParserOrchestrator


class WorkbookParseController:
    def __init__(self, orchestrator: WorkbookParserOrchestrator):
        self._orchestrator = orchestrator

    def parse_workbook(
        self,
        workbook_path: str,
        rfq_id: str,
        workbook_file_name: str | None = None,
        workbook_blob_path: str | None = None,
    ) -> dict:
        return self._orchestrator.parse(
            workbook_path=workbook_path,
            rfq_id=rfq_id,
            workbook_file_name=workbook_file_name,
            workbook_blob_path=workbook_blob_path,
        )
