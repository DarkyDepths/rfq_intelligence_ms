"""Manual/dev workbook parser route (Step 9 skeleton)."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.app_context import get_workbook_parse_controller
from src.controllers.workbook_parse_controller import WorkbookParseController

router = APIRouter(prefix="/workbook-parser", tags=["Workbook Parser"])


class WorkbookParseRequest(BaseModel):
    workbook_path: str
    rfq_id: str
    workbook_file_name: str | None = None
    workbook_blob_path: str | None = None


@router.post("/parse")
def parse_workbook_for_dev(
    request: WorkbookParseRequest,
    controller: WorkbookParseController = Depends(get_workbook_parse_controller),
):
    workbook_path = Path(request.workbook_path)
    if not workbook_path.exists():
        raise HTTPException(status_code=404, detail=f"Workbook not found: {request.workbook_path}")

    return controller.parse_workbook(
        workbook_path=request.workbook_path,
        rfq_id=request.rfq_id,
        workbook_file_name=request.workbook_file_name,
        workbook_blob_path=request.workbook_blob_path,
    )
