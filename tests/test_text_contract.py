"""Behavioral tests for the text renderer contract."""

from __future__ import annotations

import uuid

import pytest

from InkGen.component import TextComponent
from InkGen.document_outputs import FlowDocument
from InkGen.drawing_components import DrawingComponentGroup, OutputFormat, TextDrawing
from InkGen.dxf_generator import DXFDocument
from InkGen.pdf_generator import TextPDF
from InkGen.style import Font, TextStyle
from InkGen.svg_generator import TextSVG


@pytest.fixture
def text_style() -> TextStyle:
    """Return a unique visible text style."""
    style = TextStyle(name=f"text_{uuid.uuid4().hex}", font=Font(size=12.0))
    style.color = "#112233"
    return style


def _dxf_text_codes(payload: str) -> dict[str, str]:
    lines = payload.splitlines()
    start = lines.index("TEXT") - 1
    entity_lines = lines[start : start + 18]
    values: dict[str, str] = {}
    for index in range(0, len(entity_lines) - 1, 2):
        values[entity_lines[index]] = entity_lines[index + 1]
    return values


@pytest.mark.condition("TEXT-P1")
def test_text_component_preserves_text_position_and_outline(text_style: TextStyle) -> None:
    """TEXT-P1: Text components preserve text, finite position, and outline geometry."""
    component = TextComponent("Seed", (12.5, 7.5), text_style)

    assert component.text == "Seed"
    assert component.position == (12.5, 7.5)
    assert len(component.points) >= 4
    assert component.bbox[0][0] < component.bbox[1][0]
    assert component.bbox[0][1] < component.bbox[1][1]
    assert component.convex_hull

    component.text = 42
    assert component.text == "42"
    component.position = [1, 2]
    assert component.position == (1.0, 2.0)


@pytest.mark.condition("TEXT-P1")
def test_text_component_rejects_invalid_position_boundaries(text_style: TextStyle) -> None:
    """TEXT-P1: Text positions reject malformed, non-finite, and boolean coordinates."""
    invalid_positions = [
        ((float("nan"), 1.0), ValueError),
        ((float("inf"), 1.0), ValueError),
        ((1.0, float("-inf")), ValueError),
        ((True, 1.0), TypeError),
        ((1.0,), ValueError),
        ((1.0, 2.0, 3.0), ValueError),
        ({"x": 1.0, "y": 2.0}, ValueError),
        (("x", 1.0), ValueError),
    ]
    for position, error_type in invalid_positions:
        with pytest.raises(error_type):
            TextComponent("Seed", position, text_style)  # type: ignore[arg-type]

    component = TextComponent("Seed", (1.0, 2.0), text_style)
    with pytest.raises(ValueError):
        component.position = (float("nan"), 2.0)
    with pytest.raises(TypeError):
        component.position = (1.0, False)  # type: ignore[assignment]

    assert component.position == (1.0, 2.0)


@pytest.mark.condition("TEXT-P1")
def test_text_svg_emits_exact_escaped_text(text_style: TextStyle) -> None:
    """TEXT-P1: TextSVG emits escaped text with deterministic style and anchor fields."""
    component = TextSVG("A&B", (12.5, 7.5), text_style)
    font_size_px = float(text_style.font.size) * (96.0 / 72.0)

    assert (
        component.generate_svg()
        == f"""<text
            style="font-style:{text_style.font.style};font-size:{font_size_px:.6f}px;line-height:1.0;font-family:{text_style.font.family};fill:#112233;stroke:none;text-anchor:start;text-align:start;stroke-dasharray:none"
            x="12.5"
            y="7.5"
            id="text{component.id}"><tspan
                sodipodi:role="line"
                id="tspan{component.id}"
                style="fill:#112233;text-anchor:start;text-align:start;stroke:none;stroke-dasharray:none"
                x="12.5"
                y="7.5">A&amp;B</tspan></text>"""
    )


@pytest.mark.condition("TEXT-P1")
def test_text_pdf_emits_exact_text_object_and_escapes_string(text_style: TextStyle) -> None:
    """TEXT-P1: TextPDF emits text operators and escapes literal-string controls."""
    component = TextPDF("A\\B(C)\nD", (12.5, 7.5), text_style)

    assert component.generate_pdf() == "\n".join(
        [
            "q",
            "0.066667 0.133333 0.2 rg",
            "BT",
            "/F1 12 Tf",
            "1 0 0 -1 12.5 7.5 Tm",
            r"(A\\B\(C\)\nD) Tj",
            "ET",
            "Q",
        ]
    )


@pytest.mark.condition("TEXT-P1")
def test_text_pdf_uses_black_and_ten_point_defensive_defaults(text_style: TextStyle) -> None:
    """TEXT-P1: TextPDF uses deterministic defaults if style internals are incomplete."""
    text_style._color = "not-a-color"  # noqa: SLF001
    text_style._font = object()  # noqa: SLF001

    operators = TextPDF("Seed", (0.0, 0.0), text_style).generate_pdf().splitlines()

    assert operators[1] == "0 0 0 rg"
    assert operators[3] == "/F1 10 Tf"


@pytest.mark.condition("TEXT-P1")
def test_text_primitives_round_trip_parameters(text_style: TextStyle) -> None:
    """TEXT-P1: SVG and PDF text primitives recreate from serialized parameters."""
    svg = TextSVG("Seed", (12.5, 7.5), text_style)
    pdf = TextPDF("Seed", (12.5, 7.5), text_style)

    assert TextSVG.create_from_dict(svg.parameters, text_style).parameters == svg.parameters
    assert TextPDF.create_from_dict(pdf.parameters, text_style).parameters == pdf.parameters


@pytest.mark.condition("TEXT-P1")
def test_text_drawing_materializes_svg_and_pdf_components(text_style: TextStyle) -> None:
    """TEXT-P1: Neutral text recipes materialize to SVG and PDF text components."""
    drawing = TextDrawing("Seed", (12.5, 7.5), text_style)

    svg = drawing.to_component(OutputFormat.SVG)
    pdf = drawing.to_component("pdf")

    assert isinstance(svg, TextSVG)
    assert isinstance(pdf, TextPDF)
    assert svg.text == "Seed"
    assert pdf.text == "Seed"
    assert svg.position == (12.5, 7.5)
    assert pdf.position == (12.5, 7.5)
    with pytest.raises(ValueError):
        drawing.to_component("dxf")


@pytest.mark.condition("TEXT-DRAWING-POSITION-P2")
@pytest.mark.parametrize(
    ("position", "exception_type", "message"),
    [
        ("12", ValueError, "TextDrawing position must contain two numeric values"),
        (b"12", ValueError, "TextDrawing position must contain two numeric values"),
        (object(), ValueError, "TextDrawing position must contain two numeric values"),
        ((1.0,), ValueError, "TextDrawing position must contain two numeric values"),
        ((1.0, 2.0, 3.0), ValueError, "TextDrawing position must contain two numeric values"),
        (("x", 1.0), ValueError, "TextDrawing position must contain two numeric values"),
        ((object(), 1.0), ValueError, "TextDrawing position must contain two numeric values"),
        ((True, 1.0), TypeError, "TextDrawing position coordinates must be numeric values"),
        ((1.0, False), TypeError, "TextDrawing position coordinates must be numeric values"),
        ((float("nan"), 1.0), ValueError, "TextDrawing position coordinates must be finite"),
        ((float("inf"), 1.0), ValueError, "TextDrawing position coordinates must be finite"),
    ],
)
def test_text_drawing_rejects_malformed_positions_before_materialization(
    text_style: TextStyle,
    position: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """TEXT-DRAWING-POSITION-P2: Neutral text anchors fail at construction."""
    with pytest.raises(exception_type, match=message):
        TextDrawing("Seed", position, text_style)  # type: ignore[arg-type]


@pytest.mark.condition("TEXT-DRAWING-POSITION-P2")
def test_text_drawing_normalizes_valid_position_before_materialization(text_style: TextStyle) -> None:
    """TEXT-DRAWING-POSITION-P2: Valid neutral text anchors are normalized once."""
    drawing = TextDrawing("Seed", [-2.5, 7], text_style)  # type: ignore[arg-type]

    assert drawing.position == (-2.5, 7.0)
    assert drawing.to_component(OutputFormat.SVG).position == (-2.5, 7.0)
    assert drawing.to_component(OutputFormat.PDF).position == (-2.5, 7.0)


@pytest.mark.condition("TEXT-DRAWING-TEXT-P2")
@pytest.mark.parametrize("text", [123, 1.5, 1 + 2j, True])
def test_text_drawing_normalizes_scalar_text_before_materialization(text_style: TextStyle, text: object) -> None:
    """TEXT-DRAWING-TEXT-P2: Neutral text recipes store scalar text as strings."""
    drawing = TextDrawing(text, (12.5, 7.5), text_style)  # type: ignore[arg-type]

    assert drawing.text == str(text)
    assert drawing.to_component(OutputFormat.SVG).text == str(text)
    assert drawing.to_component(OutputFormat.PDF).text == str(text)


@pytest.mark.condition("TEXT-DRAWING-TEXT-P2")
@pytest.mark.parametrize("text", [object(), ["NOTE"], {"text": "NOTE"}, None])
def test_text_drawing_rejects_non_scalar_text_payloads(text_style: TextStyle, text: object) -> None:
    """TEXT-DRAWING-TEXT-P2: Neutral text recipes reject malformed text at construction."""
    with pytest.raises(TypeError, match="TextDrawing text must be a string"):
        TextDrawing(text, (12.5, 7.5), text_style)  # type: ignore[arg-type]


@pytest.mark.condition("TEXT-DRAWING-POSITION-P2")
def test_flow_document_hydration_rejects_malformed_text_drawing_positions(text_style: TextStyle) -> None:
    """TEXT-DRAWING-POSITION-P2: Serialized text drawings cannot hold bad anchors."""
    group = DrawingComponentGroup("text-flow-drawing")
    group.add_component(TextDrawing("NOTE", (2.0, 3.0), text_style))
    document = FlowDocument(title="Bad Text Position")
    document.add_drawing_group(group)
    payload = document.parameters
    flow_payload = payload["FlowDocument"]
    assert isinstance(flow_payload, dict)
    blocks = flow_payload["blocks"]
    assert isinstance(blocks, list)
    block_payload = blocks[0]["payload"]
    assert isinstance(block_payload, dict)
    components = block_payload["components"]
    assert isinstance(components, list)
    component_payload = components[0]["payload"]
    assert isinstance(component_payload, dict)
    component_payload["position"] = (float("nan"), 3.0)

    with pytest.raises(ValueError, match="TextDrawing position coordinates must be finite"):
        FlowDocument.create_from_dict(payload, {text_style.name: text_style})


@pytest.mark.condition("TEXT-P1")
def test_dxf_text_drawing_exports_text_entity_with_canvas_transform(text_style: TextStyle) -> None:
    """TEXT-P1: DXF text export emits a TEXT entity, normalized text, and transformed position."""
    drawing = TextDrawing("Line\nBreak", (12.5, 7.5), text_style)
    document = DXFDocument(canvas_height=20.0)
    group = DrawingComponentGroup("text_layer", [drawing])

    document.add_group(group)
    payload = document.to_dxf_string()
    codes = _dxf_text_codes(payload)

    assert "\n0\nTEXT\n" in payload
    assert codes["8"] == "text_layer"
    assert codes["10"] == "12.5"
    assert codes["20"] == "12.5"
    assert codes["30"] == "0"
    assert codes["40"] == "4.233333"
    assert codes["1"] == "Line Break"
