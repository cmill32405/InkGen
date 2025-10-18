import pytest

import InkGen.table as table_module
from InkGen.table import AutoFitRule, Table


def make_basic_table(rows: int = 0, cols: int = 0, *, position=(0.0, 0.0)) -> Table:
    table = Table(position=position)
    for _ in range(cols):
        table.add_column(width=10.0)
    for _ in range(rows):
        table.add_row(height=5.0)
    return table


def test_table_add_row_column_manages_matrix():
    table = Table(position=(10.0, 5.0))
    table.add_column(width=12.5)
    table.add_column(width=15.0)
    table.add_row(height=8.0)
    table.add_row(height=9.0)

    assert table.row_count == 2
    assert table.column_count == 2
    assert len(table.rows) == 2
    assert len(table.columns) == 2
    assert table.rows[0].height == pytest.approx(8.0)
    assert table.columns[1].width == pytest.approx(15.0)
    assert table.cell(0, 1) is table.row_cells(0)[1]


def test_cell_add_paragraph_records_style_and_triggers_autofit():
    table = make_basic_table(rows=1, cols=1)
    table.rows[0].height_rule = AutoFitRule.EXPAND
    table.columns[0].width_rule = AutoFitRule.FIT
    table.autofit = True

    cell = table.cell(0, 0)
    cell.add_paragraph("Hello world", style_id="style-123")

    assert cell.paragraphs == ["Hello world"]
    assert cell.paragraph_styles == ["style-123"]
    assert table.autofit_queue == [((0, 0), AutoFitRule.EXPAND, AutoFitRule.FIT)]


def test_merge_cells_marks_region():
    table = make_basic_table(rows=2, cols=2)

    start = table.cell(0, 0)
    end = table.cell(1, 1)
    start.merge(end)

    for r in range(2):
        for c in range(2):
            cell = table.cell(r, c)
            assert cell.merged is True
            assert cell.merge_start == (0, 0)
            assert cell.merge_end == (1, 1)


def test_table_parameters_round_trip():
    table = make_basic_table(rows=1, cols=1, position=(2.0, 3.0))
    cell = table.cell(0, 0)
    cell.add_paragraph("Data", style_id="style-data")

    params = table.parameters
    clone = Table.create_from_dict(params)

    assert clone.position == (2.0, 3.0)
    assert clone.autofit is False
    assert clone.row_count == 1
    assert clone.column_count == 1
    assert clone.cell_padding == (1.0, 1.0, 1.0, 1.0)
    assert clone.cell(0, 0).paragraphs == ["Data"]
    assert clone.cell(0, 0).paragraph_styles == ["style-data"]


def test_table_geometry_properties():
    table = make_basic_table(rows=1, cols=1, position=(1.0, 1.0))
    bbox = table.bbox
    assert bbox == ((1.0, 1.0), (11.0, 6.0))
    assert set(table.points) == {
        (1.0, 1.0),
        (11.0, 1.0),
        (11.0, 6.0),
        (1.0, 6.0),
    }
    assert set(table.convex_hull) == {
        (1.0, 1.0),
        (11.0, 1.0),
        (11.0, 6.0),
        (1.0, 6.0),
    }


def test_table_padding_serialization():
    table = make_basic_table(rows=1, cols=1)
    table.cell_padding = (2.0, 1.5, 1.2, 0.5)
    params = table.parameters
    assert params['Table']['padding'] == [2.0, 1.5, 1.2, 0.5]
    clone = Table.create_from_dict(params)
    assert clone.cell_padding == (2.0, 1.5, 1.2, 0.5)


def test_table_padding_getters_and_normalization():
    table = Table(position=(0.0, 0.0))
    table.cell_padding = 2.5
    assert table.cell_padding == (2.5, 2.5, 2.5, 2.5)
    assert table.padding_top == pytest.approx(2.5)
    assert table.padding_right == pytest.approx(2.5)
    assert table.padding_bottom == pytest.approx(2.5)
    assert table.padding_left == pytest.approx(2.5)

    table.cell_padding = [1.0, 2.0, 3.0, 4.0]
    assert table.cell_padding == (1.0, 2.0, 3.0, 4.0)
    with pytest.raises(ValueError):
        table.cell_padding = [1.0, 2.0, 3.0]

    assert table_module._normalize_padding(1.5) == (1.5, 1.5, 1.5, 1.5)
    assert table_module._normalize_padding((0.5, 0.75, 1.0, 1.25)) == (0.5, 0.75, 1.0, 1.25)
    with pytest.raises(ValueError):
        table_module._normalize_padding((1.0, 2.0, 3.0))


def test_table_validate_insert_index_bounds():
    table = Table(position=(0.0, 0.0))
    with pytest.raises(IndexError):
        table._validate_insert_index(1, 0)


def test_row_and_column_rule_validation():
    table = make_basic_table(rows=1, cols=1)
    row = table.rows[0]
    column = table.columns[0]

    with pytest.raises(ValueError):
        row.height = -1.0
    with pytest.raises(TypeError):
        row.height_rule = "expand"  # type: ignore[assignment]

    with pytest.raises(ValueError):
        column.width = -1.0
    with pytest.raises(TypeError):
        column.width_rule = "fit"  # type: ignore[assignment]


def test_cell_alignment_and_paragraph_validation():
    table = make_basic_table(rows=1, cols=1)
    cell = table.cell(0, 0)

    with pytest.raises(ValueError):
        cell.vertical_alignment = "diagonal"
    with pytest.raises(TypeError):
        cell.add_paragraph(123)  # type: ignore[arg-type]
