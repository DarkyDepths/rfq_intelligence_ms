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

    assert len(sheet_names) >= 30

    assert reader.get_merged_regions_count("General") == 24
    assert reader.get_merged_regions_count("Bid S") == 50
    assert reader.get_merged_regions_count("Top Sheet") == 7

    assert reader.get_label_value("Top Sheet", 10, 2) == "Description"
    assert reader.get_numeric_value("Top Sheet", 10, 2) is None

    assert reader.get_numeric_value("Top Sheet", 10, 7) == 1.0
    assert reader.get_numeric_value("Top Sheet", 10, 8) == 2.0
    assert reader.get_numeric_value("Top Sheet", 10, 9) == 3.0

    assert reader.get_date_value("General", 9, 4) == "2025-08-26"
