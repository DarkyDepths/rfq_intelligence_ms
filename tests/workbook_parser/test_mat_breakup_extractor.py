from pathlib import Path

import pytest

from src.services.workbook_parser.extractors.mat_breakup_extractor import MatBreakupExtractor
from src.services.workbook_parser.readers.workbook_reader import WorkbookReader
from src.services.workbook_parser.readers.xls_workbook_reader import XlsWorkbookReader


FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "local_fixtures"
    / "workbook_uploaded"
    / "workbook_sample_001"
    / "ghi_workbook_32_sheets.xls"
)


class OverrideReader(WorkbookReader):
    def __init__(self, base: WorkbookReader, label_overrides: dict[tuple[str, int, int], object] | None = None):
        self._base = base
        self._label_overrides = label_overrides or {}

    def open(self, workbook_path: str) -> None:
        self._base.open(workbook_path)

    def get_sheet_names(self) -> list[str]:
        return self._base.get_sheet_names()

    def has_sheet(self, sheet_name: str) -> bool:
        return self._base.has_sheet(sheet_name)

    def get_cell_value(self, sheet_name: str, row: int, col: int) -> object:
        return self._base.get_cell_value(sheet_name, row, col)

    def get_label_value(self, sheet_name: str, row: int, col: int) -> str | None:
        key = (sheet_name, row, col)
        if key in self._label_overrides:
            value = self._label_overrides[key]
            if value is None:
                return None
            return str(value)
        return self._base.get_label_value(sheet_name, row, col)

    def get_numeric_value(self, sheet_name: str, row: int, col: int) -> float | None:
        return self._base.get_numeric_value(sheet_name, row, col)

    def get_date_value(self, sheet_name: str, row: int, col: int) -> str | None:
        return self._base.get_date_value(sheet_name, row, col)

    def get_merged_regions_count(self, sheet_name: str) -> int:
        return self._base.get_merged_regions_count(sheet_name)


class MissingMatBreakupSheetReader(WorkbookReader):
    def open(self, workbook_path: str) -> None:
        return None

    def get_sheet_names(self) -> list[str]:
        return ["General", "Bid S", "Top Sheet", "Cash Flow"]

    def has_sheet(self, sheet_name: str) -> bool:
        return sheet_name != "Mat Break-up"

    def get_cell_value(self, sheet_name: str, row: int, col: int) -> object:
        return None

    def get_label_value(self, sheet_name: str, row: int, col: int) -> str | None:
        return None

    def get_numeric_value(self, sheet_name: str, row: int, col: int) -> float | None:
        return None

    def get_date_value(self, sheet_name: str, row: int, col: int) -> str | None:
        return None

    def get_merged_regions_count(self, sheet_name: str) -> int:
        return 0


def _build_reader() -> XlsWorkbookReader:
    reader = XlsWorkbookReader()
    reader.open(FIXTURE_PATH.as_posix())
    return reader


def test_mat_breakup_extractor_extracts_expected_material_decomposition_from_fixture():
    result = MatBreakupExtractor(_build_reader()).extract()

    assert len(result.anchor_checks) == 13
    assert all(check.passed for check in result.anchor_checks)

    decomposition = result.material_decomposition
    assert len(decomposition.items) == 1

    item = decomposition.items[0]
    assert item.item_number == 1
    assert item.item_qty == pytest.approx(1.0)
    assert len(item.categories) == 13

    first_category = item.categories[0]
    assert first_category.sheet_row == 27
    assert first_category.code == "PL"
    assert first_category.canonical_key == "plate"
    assert first_category.description == "Plate"
    assert first_category.weight_finish_ton == pytest.approx(7.160935062816668)
    assert first_category.cost_total_sr == pytest.approx(105743.7807149016)

    assert item.grand_total.weight_finish_ton == pytest.approx(10.249474758574534)
    assert item.grand_total.cost_total_sr == pytest.approx(202293.2381470275)

    assert decomposition.summary.grand_total.cost_total_sr == pytest.approx(202293.2381470275)
    assert decomposition.summary.grand_total.weight_finish_ton == pytest.approx(10.249474758574534)
    assert "plate" in decomposition.summary.categories
    assert "gasket" in decomposition.summary.categories

    assert result.material_cost_loading_present is True
    assert result.issues == []
    assert result.sheet_report.status == "parsed_ok"
    assert result.sheet_report.rows_scanned == 50
    assert result.sheet_report.rows_kept == 1
    assert result.sheet_report.rows_skipped == 49

    extracted_text_values = []
    for extracted_item in decomposition.items:
        for category in extracted_item.categories:
            extracted_text_values.extend([category.code, category.canonical_key, category.description, category.material_spec])
    extracted_text_values.extend(decomposition.summary.categories)
    assert all(value is None or "ERROR" not in value.upper() for value in extracted_text_values)


def test_mat_breakup_extractor_reports_anchor_mismatch_and_skips_blank_block_safely():
    base_reader = _build_reader()
    reader = OverrideReader(
        base=base_reader,
        label_overrides={
            ("Mat Break-up", 5, 9): "Wrong Per Ton Header",
            ("Mat Break-up", 27, 4): None,
        },
    )

    result = MatBreakupExtractor(reader).extract()

    issue_codes = {issue.code for issue in result.issues}
    assert "MAT_BREAKUP_MISSING_REQUIRED_ANCHOR" in issue_codes
    assert result.sheet_report.status == "parsed_with_warnings"
    assert result.sheet_report.warning_count >= 1
    assert result.sheet_report.error_count == 0
    assert len(result.material_decomposition.items) == 1
    assert any(check.cell_ref == "I5" and not check.passed for check in result.anchor_checks)


def test_mat_breakup_extractor_missing_sheet_returns_failed_result():
    result = MatBreakupExtractor(MissingMatBreakupSheetReader()).extract()

    issue_codes = {issue.code for issue in result.issues}
    assert "MAT_BREAKUP_MISSING_REQUIRED_SHEET" in issue_codes
    assert result.sheet_report.status == "failed"
    assert result.sheet_report.error_count == 1
    assert result.material_decomposition.items == []