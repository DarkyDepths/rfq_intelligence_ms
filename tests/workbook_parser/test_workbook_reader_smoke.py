from pathlib import Path

from src.services.workbook_parser.readers.xls_workbook_reader import XlsWorkbookReader


FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "local_fixtures"
    / "workbook_uploaded"
    / "workbook_sample_001"
    / "ghi_workbook_32_sheets.xls"
)


def test_workbook_reader_smoke_opens_and_reads_core_sheets():
    reader = XlsWorkbookReader()
    reader.open(FIXTURE_PATH.as_posix())

    sheet_names = reader.get_sheet_names()

    assert "General" in sheet_names
    assert "Bid S" in sheet_names
    assert "Top Sheet" in sheet_names

    assert reader.has_sheet("General")
    assert reader.has_sheet("Bid S")
    assert reader.has_sheet("Top Sheet")

    assert len(sheet_names) >= 3
    assert reader.get_merged_regions_count("General") >= 0
    assert reader.get_merged_regions_count("Bid S") >= 0
    assert reader.get_merged_regions_count("Top Sheet") >= 0
