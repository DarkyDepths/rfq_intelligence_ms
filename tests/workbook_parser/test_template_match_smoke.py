from pathlib import Path

from src.services.workbook_parser.readers.xls_workbook_reader import XlsWorkbookReader
from src.services.workbook_parser.template_matcher import TemplateMatcher


FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "local_fixtures"
    / "workbook_uploaded"
    / "workbook_sample_001"
    / "ghi_workbook_32_sheets.xls"
)


def test_template_matcher_smoke_for_v11_first_pack():
    reader = XlsWorkbookReader()
    reader.open(FIXTURE_PATH.as_posix())

    matcher = TemplateMatcher(reader)
    result = matcher.validate()

    assert reader.has_sheet("General")
    assert reader.has_sheet("Bid S")
    assert reader.has_sheet("Top Sheet")

    checked_sheets = {check.sheet_name for check in result.anchor_checks}
    assert "General" in checked_sheets
    assert "Bid S" in checked_sheets
    assert "Top Sheet" in checked_sheets

    assert result.template_match is True
    assert len(result.anchor_checks) >= 40

    error_codes = {issue.code for issue in result.issues if issue.severity == "error"}
    assert "GENERAL_MISSING_REQUIRED_SHEET" not in error_codes
    assert "BID_S_MISSING_REQUIRED_SHEET" not in error_codes
    assert "TOP_SHEET_MISSING_REQUIRED_SHEET" not in error_codes
