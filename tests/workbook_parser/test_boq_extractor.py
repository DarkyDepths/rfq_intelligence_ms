from pathlib import Path

import pytest

from src.services.workbook_parser.extractors.boq_extractor import BoqExtractor
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
    def __init__(
        self,
        base: WorkbookReader,
        label_overrides: dict[tuple[str, int, int], object] | None = None,
        numeric_overrides: dict[tuple[str, int, int], float | int | None] | None = None,
    ):
        self._base = base
        self._label_overrides = label_overrides or {}
        self._numeric_overrides = numeric_overrides or {}

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
        key = (sheet_name, row, col)
        if key in self._numeric_overrides:
            value = self._numeric_overrides[key]
            if value is None:
                return None
            return float(value)
        return self._base.get_numeric_value(sheet_name, row, col)

    def get_date_value(self, sheet_name: str, row: int, col: int) -> str | None:
        return self._base.get_date_value(sheet_name, row, col)

    def get_merged_regions_count(self, sheet_name: str) -> int:
        return self._base.get_merged_regions_count(sheet_name)


class MissingBoqSheetReader(WorkbookReader):
    def open(self, workbook_path: str) -> None:
        return None

    def get_sheet_names(self) -> list[str]:
        return ["General", "Bid S", "Top Sheet", "Cash Flow", "Mat Break-up"]

    def has_sheet(self, sheet_name: str) -> bool:
        return sheet_name != "B-O-Q"

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


def test_boq_extractor_extracts_populated_block_and_price_table_from_fixture():
    result = BoqExtractor(_build_reader()).extract()

    assert len(result.anchor_checks) == 7
    assert all(check.passed for check in result.anchor_checks)
    assert result.issues == []
    assert result.sheet_report.status == "parsed_ok"

    assert result.sheet_report.rows_scanned == 48
    assert result.sheet_report.rows_kept == 1
    assert result.sheet_report.rows_skipped == 47

    assert len(result.boq_item_details) == 1
    item = result.boq_item_details[0]

    assert item.item_block_index == 1
    assert item.tag_number == "K18-D-0003"
    assert item.description == "DRAIN COLLECTION VESSEL"
    assert item.qty == pytest.approx(1.0)
    assert len(item.components) >= 50
    assert len(item.sections_found) >= 6
    assert "Internal Detail" in item.sections_found
    assert "Nozzle Detail" in item.sections_found

    assert item.grand_total.total_amount_sr == pytest.approx(202293.23814702753)
    assert item.computed_total.total_amount_sr == pytest.approx(202293.23814702753)
    assert item.computed_total.finish_weight_kg == pytest.approx(10249.474758574539)
    assert item.grand_total_vs_computed_match is True

    assert len(result.material_price_table) >= 20
    assert result.material_price_table[0].sheet_row == 2191
    assert result.material_price_table[0].material_spec == "SA"
    assert result.material_price_table[2].material_spec == "SA516 Gr 70"
    assert result.material_price_table[2].sar_per_kg == pytest.approx(2.1037500000000002)
    assert result.material_price_table[2].usd_per_ton_offer == pytest.approx(550.0)


def test_boq_extractor_handles_formula_error_like_grand_total_cells_without_crashing():
    reader = OverrideReader(
        base=_build_reader(),
        numeric_overrides={
            ("B-O-Q", 139, 17): None,
        },
    )

    result = BoqExtractor(reader).extract()

    assert result.sheet_report.status == "parsed_ok"
    assert len(result.boq_item_details) == 1
    item = result.boq_item_details[0]
    assert item.grand_total.total_amount_sr is None
    assert item.computed_total.total_amount_sr == pytest.approx(202293.23814702753)
    assert item.grand_total_vs_computed_match is True


def test_boq_extractor_population_is_not_dependent_on_grand_total_row():
    reader = OverrideReader(
        base=_build_reader(),
        numeric_overrides={
            ("B-O-Q", 139, 13): 0.0,
            ("B-O-Q", 139, 15): 0.0,
            ("B-O-Q", 139, 17): 0.0,
        },
    )

    result = BoqExtractor(reader).extract()

    assert len(result.boq_item_details) == 1
    item = result.boq_item_details[0]
    assert item.tag_number == "K18-D-0003"
    assert item.computed_total.total_amount_sr == pytest.approx(202293.23814702753)
    assert item.computed_total.total_amount_sr > 0


def test_boq_extractor_reports_optional_anchor_mismatch_as_warning():
    reader = OverrideReader(
        base=_build_reader(),
        label_overrides={
            ("B-O-Q", 2189, 11): "USX",
        },
    )

    result = BoqExtractor(reader).extract()

    issue_codes = {issue.code for issue in result.issues}
    assert "BOQ_MISSING_REQUIRED_ANCHOR" in issue_codes
    assert result.sheet_report.status == "parsed_with_warnings"
    assert result.sheet_report.warning_count >= 1
    assert result.sheet_report.error_count == 0
    assert any(check.cell_ref == "K2189" and not check.passed for check in result.anchor_checks)


def test_boq_extractor_missing_sheet_returns_failed_result():
    result = BoqExtractor(MissingBoqSheetReader()).extract()

    issue_codes = {issue.code for issue in result.issues}
    assert "BOQ_MISSING_REQUIRED_SHEET" in issue_codes
    assert result.sheet_report.status == "failed"
    assert result.sheet_report.error_count == 1
    assert result.boq_item_details == []
    assert result.material_price_table == []