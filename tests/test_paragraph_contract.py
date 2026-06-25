"""Tests for paragraph proof obligations."""

from __future__ import annotations

from uuid import uuid4

import pytest

from InkGen.document_outputs import FlowDocument
from InkGen.paragraph import LineSpacingRule, Paragraph, ParagraphAlignment, TabStop
from InkGen.pdf_generator import ComponentGroupPDF
from InkGen.style import Font, TextStyle
from InkGen.svg_generator import ComponentGroupSVG


def _style() -> TextStyle:
    """Return a unique text style for paragraph contract tests."""
    return TextStyle(f"paragraph_contract_{uuid4().hex}", Font(size=10.0))


def _paragraph(text: str = "Alpha beta gamma") -> Paragraph:
    """Return a valid paragraph for live-path tests."""
    return Paragraph(text, position=(4.0, 6.0), width=32.0, style=_style(), line_spacing=1.2)


class _StringifiesToLeft:
    def __str__(self) -> str:
        """Return a valid paragraph alignment despite not being a string."""
        return "left"


class _StringifiesToMultiple:
    def __str__(self) -> str:
        """Return a valid line-spacing rule despite not being a string."""
        return "multiple"


@pytest.mark.condition("PARAGRAPH-P1")
def test_paragraph_rejects_nonfinite_boolean_and_malformed_positions() -> None:
    """PARAGRAPH-P1: Paragraph origins must be finite numeric coordinates."""
    style = _style()
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
            Paragraph("bad", position=position, style=style)  # type: ignore[arg-type]

    paragraph = Paragraph("ok", position=(0.0, 0.0), style=style)
    paragraph.position = (-2.5, 3.5)
    assert paragraph.position == (-2.5, 3.5)


@pytest.mark.condition("PARAGRAPH-P1")
def test_paragraph_rejects_invalid_numeric_measurements() -> None:
    """PARAGRAPH-P1: Paragraph measurements must be finite and respect field bounds."""
    style = _style()

    for field in ("width", "hanging_indent", "left_indent", "right_indent", "space_before", "space_after"):
        with pytest.raises(ValueError, match="at least"):
            Paragraph("bad", style=style, **{field: -0.1})
        with pytest.raises(ValueError, match="finite"):
            Paragraph("bad", style=style, **{field: float("nan")})
        with pytest.raises(TypeError, match="numeric"):
            Paragraph("bad", style=style, **{field: True})
    with pytest.raises(TypeError, match="numeric"):
        Paragraph("bad", style=style, width=object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="numeric"):
        Paragraph("bad", style=style, width="wide")  # type: ignore[arg-type]

    for value in (float("nan"), float("inf")):
        with pytest.raises(ValueError, match="finite"):
            Paragraph("bad", style=style, first_line_indent=value)
    with pytest.raises(TypeError, match="numeric"):
        Paragraph("bad", style=style, first_line_indent=False)

    paragraph = Paragraph("ok", style=style, first_line_indent=-3.0, width=0.0)
    assert paragraph.first_line_indent == pytest.approx(-3.0)
    assert paragraph.width == pytest.approx(0.0)


@pytest.mark.condition("PARAGRAPH-P1")
def test_paragraph_rejects_invalid_line_spacing_and_outline_level() -> None:
    """PARAGRAPH-P1: Line spacing is finite positive and outline level is an integer level."""
    style = _style()

    for value in (0.0, -1.0):
        with pytest.raises(ValueError, match="greater than"):
            Paragraph("bad", style=style, line_spacing=value)
    for value in (float("nan"), float("inf")):
        with pytest.raises(ValueError, match="finite"):
            Paragraph("bad", style=style, line_spacing=value)
    with pytest.raises(TypeError, match="numeric"):
        Paragraph("bad", style=style, line_spacing=True)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="integer"):
        Paragraph("bad", style=style, outline_level=-1)
    with pytest.raises(ValueError, match="integer"):
        Paragraph("bad", style=style, outline_level=True)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="integer"):
        Paragraph("bad", style=style, outline_level=10)
    assert Paragraph("ok", style=style, outline_level=0).outline_level == 0
    assert Paragraph("ok", style=style, outline_level=9).outline_level == 9


@pytest.mark.condition("PARAGRAPH-P1")
def test_tab_stops_reject_invalid_positions() -> None:
    """PARAGRAPH-P1: Tab stops must be finite non-negative positions."""
    for value in (-0.1, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            TabStop(value)
    with pytest.raises(TypeError, match="numeric"):
        TabStop(True)  # type: ignore[arg-type]

    assert TabStop(0.0).position == pytest.approx(0.0)
    assert TabStop(2.0, "right").alignment is ParagraphAlignment.RIGHT  # type: ignore[arg-type]

    paragraph = _paragraph()
    with pytest.raises(ValueError, match="finite"):
        paragraph.add_tab_stop(float("nan"))
    stop = paragraph.add_tab_stop(8.0, alignment="right")
    assert stop == TabStop(8.0, ParagraphAlignment.RIGHT)


@pytest.mark.condition("PARAGRAPH-ENUM-SELECTOR-P2")
def test_paragraph_rejects_stringifiable_enum_selectors() -> None:
    """PARAGRAPH-ENUM-SELECTOR-P2: Enum selectors must be enums or real strings."""
    style = _style()

    with pytest.raises(TypeError, match="alignment must be a ParagraphAlignment or string"):
        Paragraph("bad", style=style, alignment=_StringifiesToLeft())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="line_spacing_rule must be a LineSpacingRule or string"):
        Paragraph("bad", style=style, line_spacing_rule=_StringifiesToMultiple())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="tab stop alignment must be a ParagraphAlignment or string"):
        TabStop(1.0, _StringifiesToLeft())  # type: ignore[arg-type]

    paragraph = _paragraph()
    with pytest.raises(TypeError, match="alignment must be a ParagraphAlignment or string"):
        paragraph.alignment = _StringifiesToLeft()  # type: ignore[assignment]
    with pytest.raises(TypeError, match="line_spacing_rule must be a LineSpacingRule or string"):
        paragraph.line_spacing_rule = _StringifiesToMultiple()  # type: ignore[assignment]
    with pytest.raises(TypeError, match="tab stop alignment must be a ParagraphAlignment or string"):
        paragraph.add_tab_stop(2.0, alignment=_StringifiesToLeft())  # type: ignore[arg-type]


@pytest.mark.condition("PARAGRAPH-P1")
def test_paragraph_hydration_uses_public_validation_boundaries() -> None:
    """PARAGRAPH-P1: Serialized payloads cannot bypass paragraph validation."""
    paragraph = _paragraph("Persisted")
    payload = paragraph.parameters
    payload["Paragraph"]["text"] = 123
    with pytest.raises(TypeError, match="text"):
        Paragraph.create_from_dict(payload, {paragraph.style.name: paragraph.style})

    payload = paragraph.parameters
    payload["Paragraph"]["keep_together"] = "yes"
    with pytest.raises(TypeError, match="bool"):
        Paragraph.create_from_dict(payload, {paragraph.style.name: paragraph.style})

    payload = paragraph.parameters
    payload["Paragraph"]["outline_level"] = True
    with pytest.raises(ValueError, match="integer"):
        Paragraph.create_from_dict(payload, {paragraph.style.name: paragraph.style})

    payload = paragraph.parameters
    payload["Paragraph"]["tab_stops"] = [{"position": float("inf"), "alignment": "left", "leader": None}]
    with pytest.raises(ValueError, match="finite"):
        Paragraph.create_from_dict(payload, {paragraph.style.name: paragraph.style})


@pytest.mark.condition("PARAGRAPH-ENUM-SELECTOR-P2")
@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("alignment", _StringifiesToLeft(), "alignment must be a ParagraphAlignment or string"),
        ("line_spacing_rule", _StringifiesToMultiple(), "line_spacing_rule must be a LineSpacingRule or string"),
    ],
)
def test_paragraph_hydration_rejects_stringifiable_enum_selectors(
    field: str,
    value: object,
    message: str,
) -> None:
    """PARAGRAPH-ENUM-SELECTOR-P2: Hydration cannot stringify enum selectors."""
    paragraph = _paragraph("Persisted")
    payload = paragraph.parameters
    payload["Paragraph"][field] = value

    with pytest.raises(TypeError, match=message):
        Paragraph.create_from_dict(payload, {paragraph.style.name: paragraph.style})

    payload = paragraph.parameters
    payload["Paragraph"]["tab_stops"] = [{"position": 1.0, "alignment": _StringifiesToLeft(), "leader": None}]
    with pytest.raises(TypeError, match="tab stop alignment must be a ParagraphAlignment or string"):
        Paragraph.create_from_dict(payload, {paragraph.style.name: paragraph.style})


@pytest.mark.condition("PARAGRAPH-STYLES-MAPPING-P2")
@pytest.mark.parametrize("styles", [object(), ["style-name"], "style-name", b"style-name"])
def test_paragraph_hydration_rejects_malformed_style_override_maps(styles: object) -> None:
    """PARAGRAPH-STYLES-MAPPING-P2: Style overrides must be mappings before hydration."""
    paragraph = _paragraph("Persisted")

    with pytest.raises(TypeError, match="styles must be a mapping or None"):
        Paragraph.create_from_dict(paragraph.parameters, styles)  # type: ignore[arg-type]

    clone = Paragraph.create_from_dict(paragraph.parameters, {paragraph.style.name: paragraph.style})
    assert clone.style is paragraph.style


@pytest.mark.condition("PARAGRAPH-ROOT-PAYLOAD-P2")
@pytest.mark.parametrize("payload", [object(), "paragraph", b"paragraph"])
def test_paragraph_hydration_rejects_malformed_root_payloads(payload: object) -> None:
    """PARAGRAPH-ROOT-PAYLOAD-P2: Paragraph hydration roots must be mappings."""
    with pytest.raises(TypeError, match="Paragraph payload must be a mapping"):
        Paragraph.create_from_dict(payload)


@pytest.mark.condition("PARAGRAPH-ROOT-PAYLOAD-P2")
@pytest.mark.parametrize("wrapped_payload", [object(), "paragraph", b"paragraph"])
def test_paragraph_hydration_rejects_malformed_wrapped_payloads(wrapped_payload: object) -> None:
    """PARAGRAPH-ROOT-PAYLOAD-P2: Wrapped paragraph payloads must be mappings."""
    with pytest.raises(TypeError, match="Paragraph payload must be a mapping"):
        Paragraph.create_from_dict({"Paragraph": wrapped_payload})


@pytest.mark.condition("PARAGRAPH-ROOT-PAYLOAD-P2")
def test_paragraph_hydration_preserves_direct_payload_compatibility() -> None:
    """PARAGRAPH-ROOT-PAYLOAD-P2: Direct unwrapped paragraph payloads remain supported."""
    paragraph = _paragraph("Direct")
    payload = paragraph.parameters["Paragraph"]

    clone = Paragraph.create_from_dict(payload, {paragraph.style.name: paragraph.style})

    assert clone.parameters == paragraph.parameters


@pytest.mark.condition("PARAGRAPH-STYLE-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("style_payload", "exception_type", "message"),
    [
        (None, ValueError, "Paragraph payload must include style"),
        (object(), TypeError, "Paragraph style payload must be a mapping"),
        ({}, ValueError, "Paragraph style payload must include TextStyle"),
        ({"DrawingStyle": {"name": "wrong-kind"}}, ValueError, "Paragraph style payload must include TextStyle"),
        ({"TextStyle": object()}, TypeError, "Paragraph TextStyle payload must be a mapping"),
        ({"TextStyle": {}}, TypeError, "Paragraph TextStyle name must be a string"),
        ({"TextStyle": {"name": object()}}, TypeError, "Paragraph TextStyle name must be a string"),
    ],
)
def test_paragraph_hydration_rejects_malformed_style_payloads(
    style_payload: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """PARAGRAPH-STYLE-PAYLOAD-P2: Paragraph style envelopes fail before style lookup."""
    paragraph = _paragraph("Persisted")
    payload = paragraph.parameters
    if style_payload is None:
        del payload["Paragraph"]["style"]
    else:
        payload["Paragraph"]["style"] = style_payload

    with pytest.raises(exception_type, match=message):
        Paragraph.create_from_dict(payload, {paragraph.style.name: paragraph.style})


@pytest.mark.condition("PARAGRAPH-STYLE-PAYLOAD-P2")
def test_flow_document_paragraph_hydration_rejects_malformed_style_payloads() -> None:
    """PARAGRAPH-STYLE-PAYLOAD-P2: FlowDocument preserves paragraph style payload errors."""
    paragraph = _paragraph("Persisted")
    flow_payload = {
        "FlowDocument": {
            "title": "Bad Paragraph Style",
            "blocks": [{"type": "paragraph", "payload": paragraph.parameters}],
        },
    }
    paragraph_payload = flow_payload["FlowDocument"]["blocks"][0]["payload"]
    paragraph_payload["Paragraph"]["style"] = {"TextStyle": {"name": object()}}

    with pytest.raises(TypeError, match="Paragraph TextStyle name must be a string"):
        FlowDocument.create_from_dict(flow_payload, {paragraph.style.name: paragraph.style})


@pytest.mark.condition("PARAGRAPH-STYLE-PAYLOAD-P2")
def test_paragraph_hydration_preserves_valid_style_override_lookup() -> None:
    """PARAGRAPH-STYLE-PAYLOAD-P2: Valid style override lookup remains live."""
    paragraph = _paragraph("Persisted")
    clone = Paragraph.create_from_dict(paragraph.parameters, {paragraph.style.name: paragraph.style})

    assert clone.style is paragraph.style


@pytest.mark.condition("PARAGRAPH-TAB-INDEX-P2")
def test_paragraph_remove_tab_stop_rejects_python_index_coercion() -> None:
    """PARAGRAPH-TAB-INDEX-P2: Tab-stop removal indexes must be explicit public indexes."""
    paragraph = _paragraph("Indexed")
    paragraph.add_tab_stop(1.0)
    paragraph.add_tab_stop(2.0)
    original = paragraph.tab_stops

    type_errors = [True, False, object()]
    for index in type_errors:
        with pytest.raises(TypeError, match="tab stop index must be an integer"):
            paragraph.remove_tab_stop(index)  # type: ignore[arg-type]
        assert paragraph.tab_stops == original

    range_errors = [-1, 2, 3]
    for index in range_errors:
        with pytest.raises(IndexError, match="tab stop index out of range"):
            paragraph.remove_tab_stop(index)
        assert paragraph.tab_stops == original


@pytest.mark.condition("PARAGRAPH-TAB-INDEX-P2")
def test_paragraph_remove_tab_stop_preserves_valid_order_and_round_trip() -> None:
    """PARAGRAPH-TAB-INDEX-P2: Valid tab-stop removal preserves paragraph serialization."""
    style = _style()
    paragraph = Paragraph("Indexed", style=style)
    paragraph.add_tab_stop(4.0)
    paragraph.add_tab_stop(2.0)
    paragraph.add_tab_stop(6.0)

    paragraph.remove_tab_stop(1)

    assert [stop.position for stop in paragraph.tab_stops] == [2.0, 6.0]
    paragraph.remove_tab_stop(0)
    assert [stop.position for stop in paragraph.tab_stops] == [6.0]
    clone = Paragraph.create_from_dict(paragraph.parameters, {style.name: style})
    assert clone.tab_stops == paragraph.tab_stops
    assert clone.to_drawing_group("tab-index").to_group("svg").components()


@pytest.mark.condition("PARAGRAPH-TAB-STOPS-P2")
@pytest.mark.parametrize("tab_stops", ["tabs", b"tabs", object()])
def test_paragraph_constructor_rejects_malformed_tab_stop_collections(tab_stops: object) -> None:
    """PARAGRAPH-TAB-STOPS-P2: Direct tab-stop collections must be real sequences."""
    with pytest.raises(TypeError, match="tab_stops must be a sequence of TabStop values"):
        Paragraph("bad", style=_style(), tab_stops=tab_stops)  # type: ignore[arg-type]


@pytest.mark.condition("PARAGRAPH-TAB-STOPS-P2")
def test_paragraph_constructor_rejects_non_tab_stop_entries() -> None:
    """PARAGRAPH-TAB-STOPS-P2: Direct tab-stop entries must be TabStop values."""
    with pytest.raises(TypeError, match="tab_stops entries must be TabStop values"):
        Paragraph("bad", style=_style(), tab_stops=[TabStop(1.0), object()])  # type: ignore[list-item]

    paragraph = Paragraph("ok", style=_style(), tab_stops=(TabStop(2.0), TabStop(1.0)))
    assert paragraph.tab_stops == (TabStop(2.0), TabStop(1.0))


@pytest.mark.condition("PARAGRAPH-TAB-STOPS-P2")
@pytest.mark.parametrize("tab_stops", ["tabs", b"tabs", object()])
def test_paragraph_hydration_rejects_malformed_tab_stop_collections(tab_stops: object) -> None:
    """PARAGRAPH-TAB-STOPS-P2: Serialized tab-stop collections fail before iteration."""
    paragraph = _paragraph("Persisted")
    payload = paragraph.parameters
    payload["Paragraph"]["tab_stops"] = tab_stops

    with pytest.raises(TypeError, match="tab_stops must be a sequence of mappings"):
        Paragraph.create_from_dict(payload, {paragraph.style.name: paragraph.style})


@pytest.mark.condition("PARAGRAPH-TAB-STOPS-P2")
def test_paragraph_hydration_rejects_non_mapping_tab_stop_entries() -> None:
    """PARAGRAPH-TAB-STOPS-P2: Serialized tab-stop entries must be mappings."""
    paragraph = _paragraph("Persisted")
    payload = paragraph.parameters
    payload["Paragraph"]["tab_stops"] = [{"position": 1.0}, object()]

    with pytest.raises(TypeError, match="tab_stops entries must be mappings"):
        Paragraph.create_from_dict(payload, {paragraph.style.name: paragraph.style})


@pytest.mark.condition("PARAGRAPH-TABSTOP-PAYLOAD-P2")
@pytest.mark.parametrize("payload", [object(), "tab-stop", ["position", 1.0]])
def test_tab_stop_factory_rejects_malformed_payload_roots(payload: object) -> None:
    """PARAGRAPH-TABSTOP-PAYLOAD-P2: Tab-stop factory payloads must be mappings."""
    with pytest.raises(TypeError, match="tab stop payload must be a mapping"):
        TabStop.create_from_dict(payload)


@pytest.mark.condition("PARAGRAPH-TABSTOP-PAYLOAD-P2")
@pytest.mark.parametrize("payload", [{}, {"alignment": "left"}])
def test_tab_stop_factory_rejects_missing_position(payload: object) -> None:
    """PARAGRAPH-TABSTOP-PAYLOAD-P2: Tab-stop factory payloads require position."""
    with pytest.raises(ValueError, match="tab stop payload must include position"):
        TabStop.create_from_dict(payload)

    assert TabStop.create_from_dict({"position": 1.0}) == TabStop(1.0)


@pytest.mark.condition("PARAGRAPH-TABSTOP-PAYLOAD-P2")
def test_paragraph_hydration_rejects_tab_stop_entries_missing_position() -> None:
    """PARAGRAPH-TABSTOP-PAYLOAD-P2: Paragraph hydration preserves tab-stop payload errors."""
    paragraph = _paragraph("Persisted")
    payload = paragraph.parameters
    payload["Paragraph"]["tab_stops"] = [{"alignment": "left"}]

    with pytest.raises(ValueError, match="tab stop payload must include position"):
        Paragraph.create_from_dict(payload, {paragraph.style.name: paragraph.style})


@pytest.mark.condition("PARAGRAPH-TABSTOP-LEADER-P2")
@pytest.mark.parametrize("leader", [123, object()])
def test_tab_stop_rejects_malformed_leaders(leader: object) -> None:
    """PARAGRAPH-TABSTOP-LEADER-P2: Direct tab-stop leaders must be strings or None."""
    with pytest.raises(TypeError, match="tab stop leader must be a string or None"):
        TabStop(1.0, leader=leader)  # type: ignore[arg-type]

    assert TabStop(1.0, leader=".").leader == "."
    assert TabStop(1.0, leader=None).leader is None


@pytest.mark.condition("PARAGRAPH-TABSTOP-LEADER-P2")
@pytest.mark.parametrize("leader", [123, object()])
def test_paragraph_add_tab_stop_rejects_malformed_leaders(leader: object) -> None:
    """PARAGRAPH-TABSTOP-LEADER-P2: Paragraph tab-stop insertion validates leaders."""
    paragraph = _paragraph("Leaders")
    original = paragraph.tab_stops

    with pytest.raises(TypeError, match="tab stop leader must be a string or None"):
        paragraph.add_tab_stop(1.0, leader=leader)  # type: ignore[arg-type]

    assert paragraph.tab_stops == original
    assert paragraph.add_tab_stop(1.0, leader="").leader == ""


@pytest.mark.condition("PARAGRAPH-TABSTOP-LEADER-P2")
@pytest.mark.parametrize("leader", [123, object()])
def test_paragraph_hydration_rejects_malformed_tab_stop_leaders(leader: object) -> None:
    """PARAGRAPH-TABSTOP-LEADER-P2: Hydrated tab-stop leaders must be strings or None."""
    paragraph = _paragraph("Persisted")
    payload = paragraph.parameters
    payload["Paragraph"]["tab_stops"] = [{"position": 1.0, "leader": leader}]

    with pytest.raises(TypeError, match="tab stop leader must be a string or None"):
        Paragraph.create_from_dict(payload, {paragraph.style.name: paragraph.style})


@pytest.mark.condition("PARAGRAPH-P1")
def test_paragraph_contract_remains_live_through_render_and_document_paths() -> None:
    """PARAGRAPH-P1: Valid paragraphs still materialize and export through dependent paths."""
    paragraph = Paragraph(
        "Alpha beta gamma delta",
        position=(4.0, 6.0),
        width=28.0,
        style=_style(),
        alignment="right",
        line_spacing_rule=LineSpacingRule.EXACTLY,
        line_spacing=5.0,
    )

    lines = paragraph.layout_lines()
    assert len(lines) >= 1
    assert all(line.position[0] >= paragraph.position[0] for line in lines)

    drawing_group = paragraph.to_drawing_group("paragraph_contract")
    assert isinstance(drawing_group.to_group("svg"), ComponentGroupSVG)
    assert isinstance(drawing_group.to_group("pdf"), ComponentGroupPDF)

    document = FlowDocument(title="Paragraph contract")
    document.add_paragraph(paragraph)
    assert "Alpha beta" in document.to_plain_text()
    assert "Alpha beta" in document.to_html()
