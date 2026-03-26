from pathlib import Path

import pytest

from src.services.workbook_parser.extractors.boq_extractor import BoqExtractionResult, BoqExtractor
from src.services.workbook_parser.issues import ParserIssue, SheetReport
from src.services.workbook_parser.parser_orchestrator import WorkbookParserOrchestrator
from src.services.workbook_parser.readers.xls_workbook_reader import XlsWorkbookReader


FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "local_fixtures"
    / "workbook_uploaded"
    / "workbook_sample_001"
    / "ghi_workbook_32_sheets.xls"
)


def test_parser_wires_boq_profile_top_level_on_success():
    envelope = WorkbookParserOrchestrator().parse(
        workbook_path=FIXTURE_PATH.as_posix(),
        rfq_id="RFQ-PACK2-BOQ-HAPPY",
    )

    assert envelope["boq_profile"] is not None
    boq = envelope["boq_profile"]
    assert len(boq["boq_item_details"]) >= 1
    assert boq["boq_item_details"][0]["tag_number"] == "K18-D-0003"
    assert len(boq["material_price_table"]) >= 20

    sheet_reports = envelope["parser_report"]["sheet_reports"]
    assert sheet_reports["boq"] is not None
    assert sheet_reports["boq"]["status"] in {"parsed_ok", "parsed_with_warnings"}

    anchor_checks = [check for check in envelope["parser_report"]["anchor_checks"] if check["sheet_name"] == "B-O-Q"]
    assert len(anchor_checks) >= 1

    assert envelope["workbook_profile"]["rfq_identity"] is not None
    assert envelope["cost_breakdown_profile"]["financial_profile"] is not None
    assert envelope["cost_breakdown_profile"]["material_decomposition"] is not None


def test_parser_propagates_boq_issues_and_sheet_report(monkeypatch):
    original_extract = BoqExtractor.extract

    def _extract_with_warning(self):
        result = original_extract(self)
        warning_issue = ParserIssue(
            code="BOQ_TEST_WARNING",
            severity="warning",
            sheet_name="B-O-Q",
            cell_ref="A1",
            row_number=1,
            field_path=None,
            message="Synthetic warning for integration propagation",
            expected_value="ok",
            actual_value="warn",
            raw_value="warn",
        )
        return BoqExtractionResult(
            boq_item_details=result.boq_item_details,
            material_price_table=result.material_price_table,
            anchor_checks=result.anchor_checks,
            issues=[*result.issues, warning_issue],
            sheet_report=SheetReport(
                sheet_name="B-O-Q",
                status="parsed_with_warnings",
                merged_regions_count=result.sheet_report.merged_regions_count,
                expected_body_range=result.sheet_report.expected_body_range,
                rows_scanned=result.sheet_report.rows_scanned,
                rows_kept=result.sheet_report.rows_kept,
                rows_skipped=result.sheet_report.rows_skipped,
                warning_count=result.sheet_report.warning_count + 1,
                error_count=result.sheet_report.error_count,
            ),
        )

    monkeypatch.setattr(BoqExtractor, "extract", _extract_with_warning)

    envelope = WorkbookParserOrchestrator().parse(
        workbook_path=FIXTURE_PATH.as_posix(),
        rfq_id="RFQ-PACK2-BOQ-REPORTING",
    )

    warning_codes = {issue["code"] for issue in envelope["parser_report"]["warnings"]}
    assert "BOQ_TEST_WARNING" in warning_codes

    sheet_report = envelope["parser_report"]["sheet_reports"]["boq"]
    assert sheet_report["status"] == "parsed_with_warnings"
    assert sheet_report["warning_count"] >= 1


def test_parser_soft_fail_missing_boq_sheet_reports_skipped_and_continues(monkeypatch):
    original_has_sheet = XlsWorkbookReader.has_sheet

    def _has_sheet_without_boq(self, sheet_name: str) -> bool:
        if sheet_name == "B-O-Q":
            return False
        return original_has_sheet(self, sheet_name)

    monkeypatch.setattr(XlsWorkbookReader, "has_sheet", _has_sheet_without_boq)

    envelope = WorkbookParserOrchestrator().parse(
        workbook_path=FIXTURE_PATH.as_posix(),
        rfq_id="RFQ-PACK2-BOQ-MISSING",
    )

    assert envelope["boq_profile"] is None
    assert envelope["parser_report"]["sheet_reports"]["boq"]["status"] == "skipped"

    assert envelope["workbook_profile"]["rfq_identity"] is not None
    assert envelope["cost_breakdown_profile"]["financial_profile"] is not None
    assert envelope["cost_breakdown_profile"]["material_decomposition"] is not None


def test_parser_soft_fail_boq_crash_reports_failed_and_continues(monkeypatch):
    def _raise_extract(self):
        raise RuntimeError("boom-boq")

    monkeypatch.setattr(BoqExtractor, "extract", _raise_extract)

    envelope = WorkbookParserOrchestrator().parse(
        workbook_path=FIXTURE_PATH.as_posix(),
        rfq_id="RFQ-PACK2-BOQ-FAILED",
    )

    assert envelope["boq_profile"] is None
    sheet_report = envelope["parser_report"]["sheet_reports"]["boq"]
    assert sheet_report["status"] == "failed"
    assert sheet_report["error_count"] == 1

    error_codes = {issue["code"] for issue in envelope["parser_report"]["errors"]}
    assert "B_O_Q_EXTRACTION_FAILED" in error_codes

    assert envelope["workbook_profile"]["rfq_identity"] is not None
    assert envelope["cost_breakdown_profile"]["financial_profile"] is not None
    assert envelope["cost_breakdown_profile"]["material_decomposition"] is not None


