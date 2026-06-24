"""Tests for table proof obligations."""

from __future__ import annotations

from uuid import uuid4

import pytest

import InkGen.table as table_module
from InkGen.document_outputs import FlowDocument
from InkGen.style import DrawingStyle, Font, TextStyle
from InkGen.svg_generator import ComponentGroupSVG, RectangleSVG, TableSVG, TextSVG
from InkGen.table import Table


def _table() -> Table:
    """Return a minimal 1x1 table with text content."""
    table = Table(position=(5.0, 7.0))
    table.add_column(width=12.0)
    table.add_row(height=6.0)
    table.cell(0, 0).add_paragraph("A1", style_id="body")
    return table


def _border_style() -> DrawingStyle:
    """Return a unique border style."""
    return DrawingStyle(name=f"table_border_{uuid4().hex}", stroke="#000000", stroke_width=0.2, fill="none")


def _text_styles() -> dict[str, TextStyle]:
    """Return text styles keyed by table paragraph style id."""
    return {"body": TextStyle(name=f"table_body_{uuid4().hex}", font=Font())}


@pytest.mark.condition("TABLE-P1")
def test_table_rejects_nonfinite_and_boolean_positions() -> None:
    """TABLE-P1: Table origins must be finite numeric coordinates."""
    invalid_positions = [
        (float("nan"), 0.0),
        (0.0, float("inf")),
        (True, 0.0),
        (0.0, False),
        (0.0,),
        (0.0, 1.0, 2.0),
    ]

    for position in invalid_positions:
        with pytest.raises((TypeError, ValueError)):
            Table(position=position)  # type: ignore[arg-type]

    table = Table(position=(0.0, 0.0))
    with pytest.raises(ValueError, match="finite"):
        table.position = (0.0, float("-inf"))
    table.position = (-5.0, 2.5)
    assert table.position == (-5.0, 2.5)


@pytest.mark.condition("TABLE-P1")
def test_table_rejects_invalid_row_column_dimensions() -> None:
    """TABLE-P1: Row heights and column widths must be finite non-negative numbers."""
    table = Table(position=(0.0, 0.0))

    for width in (-0.1, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            table.add_column(width=width)
    with pytest.raises(TypeError):
        table.add_column(width=True)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="numeric"):
        table.add_column(width=object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="numeric"):
        table.add_column(width="wide")  # type: ignore[arg-type]

    table.add_column(width=0.0)
    for height in (-0.1, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            table.add_row(height=height)
    with pytest.raises(TypeError):
        table.add_row(height=False)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="numeric"):
        table.add_row(height=object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="numeric"):
        table.add_row(height="tall")  # type: ignore[arg-type]

    row = table.add_row(height=0.0)
    column = table.columns[0]
    row.height = 1.5
    column.width = 2.5
    assert row.height == pytest.approx(1.5)
    assert column.width == pytest.approx(2.5)


@pytest.mark.condition("TABLE-P1")
def test_table_padding_validation_is_shared_by_model_and_svg_renderer() -> None:
    """TABLE-P1: Table and TableSVG reject non-finite, negative, and boolean padding."""
    table = _table()

    for padding in (-1.0, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            table.cell_padding = padding
        with pytest.raises(ValueError):
            table_module._normalize_padding((1.0, 1.0, padding, 1.0))
        with pytest.raises(ValueError):
            TableSVG.from_table(
                table,
                border_style=_border_style(),
                text_styles=_text_styles(),
                cell_padding=padding,
            )

    with pytest.raises(TypeError):
        table.cell_padding = True  # type: ignore[assignment]
    with pytest.raises(ValueError, match="four"):
        table.cell_padding = [1.0, 1.0, 1.0, 1.0, 1.0]
    with pytest.raises(TypeError):
        TableSVG.from_table(
            table,
            border_style=_border_style(),
            text_styles=_text_styles(),
            cell_padding=(1.0, True, 1.0, 1.0),  # type: ignore[arg-type]
        )


@pytest.mark.condition("TABLE-P1")
def test_table_parameters_reject_invalid_hydrated_geometry() -> None:
    """TABLE-P1: Serialized table payloads cannot hydrate invalid dimensions."""
    table = _table()
    payload = table.parameters
    payload["Table"]["columns"][0]["width"] = float("nan")

    with pytest.raises(ValueError, match="finite"):
        Table.create_from_dict(payload)

    payload = table.parameters
    payload["Table"]["padding"] = [1.0, 1.0, -0.5, 1.0]

    with pytest.raises(ValueError, match="non-negative"):
        Table.create_from_dict(payload)


@pytest.mark.condition("TABLE-P1")
def test_table_svg_and_flow_document_use_valid_table_contract() -> None:
    """TABLE-P1: Valid table geometry remains live through SVG and flow-document paths."""
    table = _table()

    group = TableSVG.from_table(
        table,
        group_label="tbl",
        border_style=_border_style(),
        text_styles=_text_styles(),
        cell_padding=(0.5, 0.5, 0.5, 0.5),
    )

    assert isinstance(group, ComponentGroupSVG)
    components = list(group.components())
    assert [type(component) for component in components] == [RectangleSVG, TextSVG]
    assert components[0].width == pytest.approx(12.0)
    assert components[0].height == pytest.approx(6.0)
    assert components[1].text == "A1"

    document = FlowDocument(title="Table contract")
    document.add_table(table)
    assert "A1" in document.to_html()
    assert "A1" in document.to_plain_text()


@pytest.mark.condition("TABLE-AUTOFIT-P2")
@pytest.mark.parametrize("value", [1, 0, "false", "", object()])
def test_table_autofit_rejects_non_bool_values(value: object) -> None:
    """TABLE-AUTOFIT-P2: Autofit accepts only real bool values."""
    with pytest.raises(TypeError, match="autofit must be a bool"):
        Table(autofit=value)  # type: ignore[arg-type]

    table = Table(autofit=True)
    before = table.autofit
    with pytest.raises(TypeError, match="autofit must be a bool"):
        table.autofit = value  # type: ignore[assignment]
    assert table.autofit is before


@pytest.mark.condition("TABLE-AUTOFIT-P2")
def test_table_autofit_hydration_rejects_non_bool_values() -> None:
    """TABLE-AUTOFIT-P2: Serialized auto_fit cannot bypass bool validation."""
    table = _table()
    payload = table.parameters
    payload["Table"]["auto_fit"] = "false"

    with pytest.raises(TypeError, match="autofit must be a bool"):
        Table.create_from_dict(payload)


@pytest.mark.condition("TABLE-AUTOFIT-P2")
def test_table_autofit_true_still_registers_queue_entries() -> None:
    """TABLE-AUTOFIT-P2: Valid true autofit still drives queue registration."""
    table = Table(autofit=True)
    table.add_column(width=5.0)
    table.add_row(height=4.0)

    table.cell(0, 0).add_paragraph("queued")

    assert table.autofit is True
    assert table.autofit_queue == [((0, 0), table.rows[0].height_rule, table.columns[0].width_rule)]


@pytest.mark.condition("TABLE-AUTOFIT-P2")
def test_table_autofit_false_suppresses_queue_entries() -> None:
    """TABLE-AUTOFIT-P2: Valid false autofit suppresses queue registration."""
    table = Table(autofit=False)
    table.add_column(width=5.0)
    table.add_row(height=4.0)

    table.cell(0, 0).add_paragraph("not queued")

    assert table.autofit is False
    assert table.autofit_queue == []
