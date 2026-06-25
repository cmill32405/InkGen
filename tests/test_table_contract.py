"""Tests for table proof obligations."""

from __future__ import annotations

from uuid import uuid4

import pytest

import InkGen.table as table_module
from InkGen.document_outputs import FlowDocument
from InkGen.style import DrawingStyle, Font, TextStyle
from InkGen.svg_generator import ComponentGroupSVG, RectangleSVG, TableSVG, TextSVG
from InkGen.table import AutoFitRule, Table


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


class _StringEquivalent:
    def __init__(self, value: str) -> None:
        self._value = value

    def __eq__(self, other: object) -> bool:
        return other == self._value

    def __hash__(self) -> int:
        return hash(self._value)


class _EqualitySpoofingTable(Table):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Table)


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


@pytest.mark.condition("TABLE-CELL-ALIGNMENT-P2")
def test_table_cell_vertical_alignment_rejects_non_string_selectors() -> None:
    """TABLE-CELL-ALIGNMENT-P2: Alignment accepts only real strings."""
    cell = _table().cell(0, 0)
    cell.vertical_alignment = "middle"

    for value in [_StringEquivalent("bottom"), b"bottom", object(), None]:
        with pytest.raises(TypeError, match="Alignment must be a string"):
            cell.vertical_alignment = value  # type: ignore[assignment]
        assert cell.vertical_alignment == "middle"

    with pytest.raises(ValueError, match="Alignment must be one"):
        cell.vertical_alignment = "diagonal"
    assert cell.vertical_alignment == "middle"


@pytest.mark.condition("TABLE-CELL-ALIGNMENT-P2")
def test_table_cell_vertical_alignment_hydration_rejects_non_string_selector() -> None:
    """TABLE-CELL-ALIGNMENT-P2: Serialized alignment cannot bypass string validation."""
    payload = _table().parameters
    payload["Table"]["matrix"][0][0]["vertical_alignment"] = _StringEquivalent("bottom")

    with pytest.raises(TypeError, match="Alignment must be a string"):
        Table.create_from_dict(payload)


@pytest.mark.condition("TABLE-CELL-ALIGNMENT-P2")
def test_table_cell_vertical_alignment_valid_strings_hydrate_and_render() -> None:
    """TABLE-CELL-ALIGNMENT-P2: Valid alignment remains live through hydration and SVG output."""
    table = _table()
    table.cell(0, 0).vertical_alignment = "middle"

    clone = Table.create_from_dict(table.parameters)
    assert clone.cell(0, 0).vertical_alignment == "middle"

    group = TableSVG.from_table(
        clone,
        group_label="aligned-table",
        border_style=_border_style(),
        text_styles=_text_styles(),
    )
    text_components = [component for component in group.components() if type(component) is TextSVG]
    assert len(text_components) == 1
    assert text_components[0].text == "A1"

    document = FlowDocument(title="Aligned table")
    document.add_table(clone)
    assert "A1" in document.to_plain_text()


@pytest.mark.condition("TABLE-CELL-STYLE-ID-P2")
def test_table_cell_paragraph_style_id_rejects_non_string_values() -> None:
    """TABLE-CELL-STYLE-ID-P2: Paragraph style IDs accept only strings or None."""
    cell = _table().cell(0, 0)

    for value in [_StringEquivalent("body"), b"body", object(), 1]:
        with pytest.raises(TypeError, match="style_id must be a string or None"):
            cell.add_paragraph("Bad style", style_id=value)  # type: ignore[arg-type]

    assert cell.paragraphs == ["A1"]
    assert cell.paragraph_styles == ["body"]
    cell.add_paragraph("No style", style_id=None)
    assert cell.paragraph_styles[-1] is None


@pytest.mark.condition("TABLE-CELL-STYLE-ID-P2")
def test_table_cell_paragraph_style_id_hydration_rejects_non_string_values() -> None:
    """TABLE-CELL-STYLE-ID-P2: Serialized style IDs cannot bypass validation."""
    payload = _table().parameters
    payload["Table"]["matrix"][0][0]["paragraphs"][0]["style_id"] = _StringEquivalent("body")

    with pytest.raises(TypeError, match="style_id must be a string or None"):
        Table.create_from_dict(payload)


@pytest.mark.condition("TABLE-CELL-STYLE-ID-P2")
def test_table_cell_paragraph_style_id_valid_values_hydrate_and_render() -> None:
    """TABLE-CELL-STYLE-ID-P2: Valid style IDs remain live through hydration and SVG output."""
    table = _table()
    table.cell(0, 0).add_paragraph("Default", style_id=None)

    clone = Table.create_from_dict(table.parameters)
    assert clone.cell(0, 0).paragraph_styles == ["body", None]

    text_styles = _text_styles()
    text_styles[None] = TextStyle(name=f"default_table_style_{uuid4().hex}", font=Font())  # type: ignore[index]
    group = TableSVG.from_table(
        clone,
        group_label="style-table",
        border_style=_border_style(),
        text_styles=text_styles,  # type: ignore[arg-type]
    )
    text_components = [component for component in group.components() if type(component) is TextSVG]
    assert [component.text for component in text_components] == ["A1", "Default"]


def _merged_table_payload() -> dict:
    table = Table(position=(0.0, 0.0))
    table.add_column(width=12.0)
    table.add_column(width=8.0)
    table.add_row(height=6.0)
    table.add_row(height=4.0)
    table.cell(0, 0).add_paragraph("Merged", style_id="body")
    table.cell(0, 0).merge(table.cell(1, 1))
    return table.parameters


@pytest.mark.condition("TABLE-CELL-MERGE-P2")
def test_table_cell_merge_hydration_rejects_non_bool_merge_flags() -> None:
    """TABLE-CELL-MERGE-P2: Serialized merge flags accept only real bool values."""
    payload = _merged_table_payload()
    payload["Table"]["matrix"][0][0]["merged"] = "false"

    with pytest.raises(TypeError, match="merged must be a bool"):
        Table.create_from_dict(payload)


@pytest.mark.condition("TABLE-CELL-MERGE-P2")
def test_table_cell_merge_hydration_defaults_missing_merge_flag_to_false() -> None:
    """TABLE-CELL-MERGE-P2: Missing serialized merge flags hydrate as unmerged."""
    payload = _table().parameters
    del payload["Table"]["matrix"][0][0]["merged"]

    clone = Table.create_from_dict(payload)

    assert clone.cell(0, 0).merged is False


@pytest.mark.condition("TABLE-CELL-MERGE-P2")
@pytest.mark.parametrize(
    ("field", "value", "exception", "message"),
    [
        ("merge_start", "0,0", TypeError, "two-integer coordinate"),
        ("merge_start", [0], ValueError, "exactly two indexes"),
        ("merge_start", [True, 0], TypeError, "indexes must be integers"),
        ("merge_start", [-1, 0], ValueError, "inside table bounds"),
        ("merge_end", [0.0, 1], TypeError, "indexes must be integers"),
        ("merge_end", [2, 1], ValueError, "inside table bounds"),
        ("merge_end", [3, 1], ValueError, "inside table bounds"),
        ("merge_end", [1, -1], ValueError, "inside table bounds"),
        ("merge_end", [1, 2], ValueError, "inside table bounds"),
        ("merge_end", [1, 3], ValueError, "inside table bounds"),
    ],
)
def test_table_cell_merge_hydration_rejects_invalid_coordinates(
    field: str,
    value: object,
    exception: type[Exception],
    message: str,
) -> None:
    """TABLE-CELL-MERGE-P2: Serialized merge coordinates must be bounded integer pairs."""
    payload = _merged_table_payload()
    payload["Table"]["matrix"][0][0][field] = value

    with pytest.raises(exception, match=message):
        Table.create_from_dict(payload)


@pytest.mark.condition("TABLE-CELL-MERGE-P2")
def test_table_cell_merge_hydration_valid_state_remains_live() -> None:
    """TABLE-CELL-MERGE-P2: Valid merge state hydrates and remains usable by output paths."""
    clone = Table.create_from_dict(_merged_table_payload())

    for row_index in range(2):
        for column_index in range(2):
            cell = clone.cell(row_index, column_index)
            assert cell.merged is True
            assert cell.merge_start == (0, 0)
            assert cell.merge_end == (1, 1)

    group = TableSVG.from_table(
        clone,
        group_label="merged-table",
        border_style=_border_style(),
        text_styles=_text_styles(),
    )
    assert any(type(component) is TextSVG and component.text == "Merged" for component in group.components())

    document = FlowDocument(title="Merged table")
    document.add_table(clone)
    assert "Merged" in document.to_plain_text()


@pytest.mark.condition("TABLE-AUTOFIT-RULE-P2")
@pytest.mark.parametrize(
    ("collection", "field"),
    [
        ("columns", "width_rule"),
        ("rows", "height_rule"),
    ],
)
def test_table_autofit_rule_hydration_rejects_non_string_selectors(collection: str, field: str) -> None:
    """TABLE-AUTOFIT-RULE-P2: Serialized autofit rules must be real strings."""
    payload = _table().parameters
    payload["Table"][collection][0][field] = _StringEquivalent("FIT")

    with pytest.raises(TypeError, match=f"{field} must be a string"):
        Table.create_from_dict(payload)


@pytest.mark.condition("TABLE-AUTOFIT-RULE-P2")
@pytest.mark.parametrize(
    ("collection", "field"),
    [
        ("columns", "width_rule"),
        ("rows", "height_rule"),
    ],
)
def test_table_autofit_rule_hydration_rejects_unknown_strings(collection: str, field: str) -> None:
    """TABLE-AUTOFIT-RULE-P2: Serialized autofit rules must match supported enum values."""
    payload = _table().parameters
    payload["Table"][collection][0][field] = "SHRINK"

    with pytest.raises(ValueError):
        Table.create_from_dict(payload)


@pytest.mark.condition("TABLE-AUTOFIT-RULE-P2")
def test_table_autofit_rule_hydration_valid_strings_remain_live() -> None:
    """TABLE-AUTOFIT-RULE-P2: Valid hydrated rules remain live through queue registration."""
    payload = _table().parameters
    payload["Table"]["auto_fit"] = True
    payload["Table"]["columns"][0]["width_rule"] = "FIT"
    payload["Table"]["rows"][0]["height_rule"] = "CUT"

    clone = Table.create_from_dict(payload)
    clone.cell(0, 0).add_paragraph("Queued")

    assert clone.columns[0].width_rule is AutoFitRule.FIT
    assert clone.rows[0].height_rule is AutoFitRule.CUT
    assert clone.autofit_queue[-1] == ((0, 0), AutoFitRule.CUT, AutoFitRule.FIT)


@pytest.mark.condition("TABLE-PAYLOAD-ENVELOPE-P2")
@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ("not a mapping", "table payload must be a mapping"),
        ({"Table": "not a mapping"}, "Table payload must be a mapping"),
    ],
)
def test_table_hydration_rejects_malformed_root_payloads(payload: object, message: str) -> None:
    """TABLE-PAYLOAD-ENVELOPE-P2: Root table payloads must be mappings."""
    with pytest.raises(TypeError, match=message):
        Table.create_from_dict(payload)  # type: ignore[arg-type]


@pytest.mark.condition("TABLE-PAYLOAD-ENVELOPE-P2")
@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda payload: payload["Table"].__setitem__("columns", "bad"), "columns must be a sequence"),
        (lambda payload: payload["Table"]["columns"].__setitem__(0, []), "column payload must be a mapping"),
        (lambda payload: payload["Table"].__setitem__("rows", "bad"), "rows must be a sequence"),
        (lambda payload: payload["Table"]["rows"].__setitem__(0, []), "row payload must be a mapping"),
        (lambda payload: payload["Table"].__setitem__("matrix", "bad"), "matrix must be a sequence"),
        (lambda payload: payload["Table"]["matrix"].__setitem__(0, "bad"), "matrix row must be a sequence"),
        (lambda payload: payload["Table"]["matrix"][0].__setitem__(0, []), "cell payload must be a mapping"),
        (lambda payload: payload["Table"]["matrix"][0][0].__setitem__("paragraphs", "bad"), "paragraphs must be a sequence"),
        (lambda payload: payload["Table"]["matrix"][0][0]["paragraphs"].__setitem__(0, []), "paragraph payload must be a mapping"),
    ],
)
def test_table_hydration_rejects_malformed_collection_envelopes(mutate, message: str) -> None:
    """TABLE-PAYLOAD-ENVELOPE-P2: Nested table payload envelopes must be explicit shapes."""
    payload = _table().parameters
    mutate(payload)

    with pytest.raises(TypeError, match=message):
        Table.create_from_dict(payload)


@pytest.mark.condition("TABLE-PAYLOAD-ENVELOPE-P2")
def test_table_hydration_valid_envelopes_remain_live() -> None:
    """TABLE-PAYLOAD-ENVELOPE-P2: Valid payload envelopes still hydrate and render."""
    clone = Table.create_from_dict(_table().parameters)

    assert clone.cell(0, 0).text == "A1"

    group = TableSVG.from_table(
        clone,
        group_label="payload-table",
        border_style=_border_style(),
        text_styles=_text_styles(),
    )
    assert any(type(component) is TextSVG and component.text == "A1" for component in group.components())

    document = FlowDocument(title="Payload table")
    document.add_table(clone)
    assert "A1" in document.to_plain_text()


def _two_by_two_table() -> Table:
    """Return a 2x2 table for index-boundary tests."""
    table = Table(position=(2.0, 3.0))
    table.add_column(width=10.0)
    table.add_column(width=20.0)
    table.add_row(height=4.0)
    table.add_row(height=5.0)
    table.cell(0, 0).add_paragraph("A1", style_id="body")
    table.cell(0, 1).add_paragraph("A2", style_id="body")
    table.cell(1, 0).add_paragraph("B1", style_id="body")
    table.cell(1, 1).add_paragraph("B2", style_id="body")
    return table


@pytest.mark.condition("TABLE-INDEX-P2")
def test_table_public_access_indexes_reject_bool_and_non_integer_values() -> None:
    """TABLE-INDEX-P2: Table accessors require non-bool integer indexes."""
    table = _two_by_two_table()

    assert table.cell(1, 0).text == "B1"
    assert [cell.text for cell in table.row_cells(0)] == ["A1", "A2"]
    assert [cell.text for cell in table.column_cells(1)] == ["A2", "B2"]
    assert table.cell_bounds(1, 1) == ((12.0, 7.0), 20.0, 5.0)

    table.add_column(width=30.0)
    table.add_row(height=6.0)
    table.cell(2, 2).add_paragraph("C3", style_id="body")
    assert table.cell(2, 2).text == "C3"
    assert table.cell_bounds(2, 2) == ((32.0, 12.0), 30.0, 6.0)

    invalid_calls = [
        lambda: table.cell(True, 0),
        lambda: table.cell(0, False),
        lambda: table.cell(0.0, 0),  # type: ignore[arg-type]
        lambda: table.cell(0, object()),  # type: ignore[arg-type]
        lambda: table.row_cells(False),
        lambda: table.column_cells(True),
        lambda: table.cell_bounds(True, 0),
        lambda: table.cell_bounds(0, False),
    ]
    for call in invalid_calls:
        with pytest.raises(TypeError, match="must be an integer"):
            call()

    out_of_bounds_calls = [
        lambda: table.cell(-1, 0),
        lambda: table.cell(0, 3),
        lambda: table.row_cells(3),
        lambda: table.column_cells(-1),
        lambda: table.cell_bounds(3, 0),
    ]
    for call in out_of_bounds_calls:
        with pytest.raises(IndexError, match="outside valid range"):
            call()


@pytest.mark.condition("TABLE-INDEX-P2")
def test_table_insert_locations_reject_bool_and_non_integer_values() -> None:
    """TABLE-INDEX-P2: Row and column insertion locations require non-bool integers."""
    table = Table(position=(0.0, 0.0))
    table.add_column(width=10.0)
    table.add_row(height=5.0)

    for call in [
        lambda: table.add_column(location=True, width=15.0),  # type: ignore[arg-type]
        lambda: table.add_row(location=False, height=6.0),  # type: ignore[arg-type]
        lambda: table.add_column(location=0.0, width=15.0),  # type: ignore[arg-type]
        lambda: table.add_row(location=object(), height=6.0),  # type: ignore[arg-type]
    ]:
        with pytest.raises(TypeError, match="must be an integer"):
            call()

    assert table.row_count == 1
    assert table.column_count == 1

    table.add_column(location=1, width=15.0)
    table.add_row(location=0, height=6.0)

    assert [column.width for column in table.columns] == [10.0, 15.0]
    assert [row.height for row in table.rows] == [6.0, 5.0]


@pytest.mark.condition("TABLE-INDEX-P2")
def test_row_column_and_paragraph_indexes_reject_bool_and_non_integer_values() -> None:
    """TABLE-INDEX-P2: Row, column, and paragraph accessors require integer indexes."""
    table = _two_by_two_table()
    row = table.rows[0]
    column = table.columns[1]
    cell = table.cell(0, 0)
    cell.add_paragraph("A1 second", style_id="body")

    assert row.column(1).text == "A2"
    assert column.row(1).text == "B2"
    assert cell.paragraph(1) == "A1 second"

    for call in [
        lambda: row.column(True),
        lambda: column.row(False),
        lambda: cell.paragraph(True),
        lambda: cell.remove_paragraph(False),
        lambda: row.column("1"),  # type: ignore[arg-type]
        lambda: column.row(1.0),  # type: ignore[arg-type]
    ]:
        with pytest.raises(TypeError, match="must be an integer"):
            call()

    for call in [
        lambda: row.column(2),
        lambda: column.row(-1),
        lambda: cell.paragraph(2),
        lambda: cell.remove_paragraph(-1),
    ]:
        with pytest.raises(IndexError, match="outside valid range"):
            call()

    assert cell.paragraphs == ["A1", "A1 second"]
    cell.remove_paragraph(0)
    assert cell.paragraphs == ["A1 second"]


@pytest.mark.condition("TABLE-INDEX-P2")
def test_table_valid_indexes_remain_live_through_svg_and_flow_document() -> None:
    """TABLE-INDEX-P2: Valid integer indexes still feed table output paths."""
    table = _two_by_two_table()

    group = TableSVG.from_table(
        table,
        group_label="indexed-table",
        border_style=_border_style(),
        text_styles=_text_styles(),
    )
    assert any(type(component) is TextSVG and component.text == "B2" for component in group.components())

    document = FlowDocument(title="Indexed table")
    document.add_table(table)

    assert "A1\tA2" in document.to_plain_text()
    assert "B1\tB2" in document.to_plain_text()


@pytest.mark.condition("TABLE-MATRIX-DIMENSIONS-P2")
@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda payload: payload["Table"].pop("matrix"), "matrix row count must match table rows"),
        (lambda payload: payload["Table"].__setitem__("matrix", []), "matrix row count must match table rows"),
        (lambda payload: payload["Table"]["matrix"].pop(), "matrix row count must match table rows"),
        (lambda payload: payload["Table"]["matrix"].append(payload["Table"]["matrix"][0].copy()), "matrix row count must match table rows"),
        (lambda payload: payload["Table"]["matrix"][0].pop(), "matrix column count must match table columns"),
        (
            lambda payload: payload["Table"]["matrix"][0].append(payload["Table"]["matrix"][0][0].copy()),
            "matrix column count must match table columns",
        ),
    ],
)
def test_table_hydration_rejects_mismatched_matrix_dimensions(mutate, message: str) -> None:
    """TABLE-MATRIX-DIMENSIONS-P2: Hydrated matrix dimensions must match rows and columns."""
    payload = _two_by_two_table().parameters
    mutate(payload)

    with pytest.raises(ValueError, match=message):
        Table.create_from_dict(payload)


@pytest.mark.condition("TABLE-MATRIX-DIMENSIONS-P2")
def test_table_hydration_rectangular_matrix_remains_live() -> None:
    """TABLE-MATRIX-DIMENSIONS-P2: Rectangular matrices hydrate without data loss."""
    clone = Table.create_from_dict(_two_by_two_table().parameters)

    assert clone.row_count == 2
    assert clone.column_count == 2
    assert clone.cell(0, 0).text == "A1"
    assert clone.cell(1, 1).text == "B2"

    group = TableSVG.from_table(
        clone,
        group_label="matrix-table",
        border_style=_border_style(),
        text_styles=_text_styles(),
    )
    assert any(type(component) is TextSVG and component.text == "B2" for component in group.components())

    document = FlowDocument(title="Matrix table")
    document.add_table(clone)
    assert "A1\tA2" in document.to_plain_text()
    assert "B1\tB2" in document.to_plain_text()


@pytest.mark.condition("TABLE-MATRIX-DIMENSIONS-P2")
def test_table_hydration_matrix_dimensions_compare_by_value_not_identity() -> None:
    """TABLE-MATRIX-DIMENSIONS-P2: Matrix dimensions compare numeric value, not object identity."""
    row_heavy_table = Table(position=(0.0, 0.0))
    row_heavy_table.add_column(width=1.0)
    for _ in range(300):
        row_heavy_table.add_row(height=1.0)

    row_heavy_clone = Table.create_from_dict(row_heavy_table.parameters)
    assert row_heavy_clone.row_count == 300
    assert row_heavy_clone.column_count == 1

    column_heavy_table = Table(position=(0.0, 0.0))
    for _ in range(300):
        column_heavy_table.add_column(width=1.0)
    column_heavy_table.add_row(height=1.0)

    column_heavy_clone = Table.create_from_dict(column_heavy_table.parameters)
    assert column_heavy_clone.row_count == 1
    assert column_heavy_clone.column_count == 300


@pytest.mark.condition("TABLE-REQUIRED-FIELDS-P2")
@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda payload: payload["Table"].pop("position"), "Table must include position"),
        (lambda payload: payload["Table"].pop("auto_fit"), "Table must include auto_fit"),
        (lambda payload: payload["Table"]["columns"][0].pop("width"), "column payload must include width"),
        (lambda payload: payload["Table"]["columns"][0].pop("width_rule"), "column payload must include width_rule"),
        (lambda payload: payload["Table"]["rows"][0].pop("height"), "row payload must include height"),
        (lambda payload: payload["Table"]["rows"][0].pop("height_rule"), "row payload must include height_rule"),
        (lambda payload: payload["Table"]["matrix"][0][0]["paragraphs"][0].pop("text"), "paragraph payload must include text"),
    ],
)
def test_table_hydration_rejects_missing_required_fields(mutate, message: str) -> None:
    """TABLE-REQUIRED-FIELDS-P2: Missing required table fields fail explicitly."""
    payload = _two_by_two_table().parameters
    mutate(payload)

    with pytest.raises(ValueError, match=message):
        Table.create_from_dict(payload)


@pytest.mark.condition("TABLE-REQUIRED-FIELDS-P2")
def test_table_hydration_required_fields_preserve_valid_round_trip() -> None:
    """TABLE-REQUIRED-FIELDS-P2: Required-field checks preserve valid table payloads."""
    clone = Table.create_from_dict(_two_by_two_table().parameters)

    assert clone.position == (2.0, 3.0)
    assert clone.autofit is False
    assert clone.cell(0, 0).text == "A1"
    assert clone.cell(1, 1).text == "B2"

    group = TableSVG.from_table(
        clone,
        group_label="required-field-table",
        border_style=_border_style(),
        text_styles=_text_styles(),
    )
    assert any(type(component) is TextSVG and component.text == "B2" for component in group.components())

    document = FlowDocument(title="Required fields")
    document.add_table(clone)
    assert "A1\tA2" in document.to_plain_text()
    assert "B1\tB2" in document.to_plain_text()


@pytest.mark.condition("TABLE-MERGE-ARG-P2")
@pytest.mark.parametrize("other", [None, object(), "cell", 1])
def test_table_cell_merge_rejects_non_cell_arguments(other: object) -> None:
    """TABLE-MERGE-ARG-P2: Cell.merge accepts only Cell instances."""
    cell = _two_by_two_table().cell(0, 0)

    with pytest.raises(TypeError, match="Can only merge with another Cell"):
        cell.merge(other)  # type: ignore[arg-type]

    assert cell.merged is False
    assert cell.merge_start == (0, 0)
    assert cell.merge_end == (0, 0)


@pytest.mark.condition("TABLE-MERGE-ARG-P2")
def test_table_cell_merge_preserves_cross_table_rejection() -> None:
    """TABLE-MERGE-ARG-P2: Cell.merge still rejects cells from different tables."""
    table = _EqualitySpoofingTable(position=(0.0, 0.0))
    table.add_column(width=1.0)
    table.add_row(height=1.0)
    other_table = _EqualitySpoofingTable(position=(0.0, 0.0))
    other_table.add_column(width=1.0)
    other_table.add_row(height=1.0)
    cell = table.cell(0, 0)
    other = other_table.cell(0, 0)

    with pytest.raises(ValueError, match="Cells belong to different tables"):
        cell.merge(other)

    assert cell.merged is False


@pytest.mark.condition("TABLE-MERGE-ARG-P2")
def test_table_cell_merge_valid_argument_remains_live() -> None:
    """TABLE-MERGE-ARG-P2: Valid direct merges still feed output paths."""
    table = _two_by_two_table()
    table.add_column(width=30.0)
    table.add_row(height=6.0)
    table.cell(2, 2).add_paragraph("C3", style_id="body")

    merged = table.cell(0, 0).merge(table.cell(2, 2))

    assert merged is table.cell(0, 0)
    for row_index in range(3):
        for column_index in range(3):
            cell = table.cell(row_index, column_index)
            assert cell.merged is True
            assert cell.merge_start == (0, 0)
            assert cell.merge_end == (2, 2)

    group = TableSVG.from_table(
        table,
        group_label="direct-merge-table",
        border_style=_border_style(),
        text_styles=_text_styles(),
    )
    assert any(type(component) is TextSVG and component.text == "A1" for component in group.components())

    document = FlowDocument(title="Direct merge")
    document.add_table(table)
    assert "A1" in document.to_plain_text()
