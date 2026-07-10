"""Behavioral tests for the line renderer contract."""

from __future__ import annotations

import uuid

import pytest
from shapely import Point

from InkGen.document_outputs import FlowDocument
from InkGen.drawing_components import DrawingComponentGroup, LineDrawing, OutputFormat
from InkGen.dxf_generator import DXFDocument
from InkGen.pdf_generator import LinePDF
from InkGen.style import DrawingStyle
from InkGen.svg_generator import LineSVG


@pytest.fixture
def drawing_style() -> DrawingStyle:
    """Return a unique visible drawing style."""
    return DrawingStyle(name=f"line_{uuid.uuid4().hex}", stroke="#000000", stroke_width=0.2, fill="none")


def _dxf_line_codes(payload: str) -> dict[str, str]:
    lines = payload.splitlines()
    start = lines.index("LINE") - 1
    entity_lines = lines[start : start + 22]
    values: dict[str, str] = {}
    for index in range(0, len(entity_lines) - 1, 2):
        values[entity_lines[index]] = entity_lines[index + 1]
    return values


@pytest.mark.condition("LINE-P1")
def test_line_component_preserves_points_bbox_and_hull(drawing_style: DrawingStyle) -> None:
    """LINE-P1: Lines preserve endpoints and expose exact two-point geometry."""
    line = LinePDF((1.25, 2.5), (9.75, 6.0), drawing_style)

    assert line.point_1 == (1.25, 2.5)
    assert line.point_2 == (9.75, 6.0)
    assert line.points == [(1.25, 2.5), (9.75, 6.0)]
    assert line.bbox == [(1.25, 2.5), (9.75, 6.0)]
    assert line.convex_hull == [(1.25, 2.5), (9.75, 6.0)]

    zero_cases = [
        ((0.0, 1.0), (2.0, 3.0)),
        ((1.0, 0.0), (2.0, 3.0)),
        ((1.0, 2.0), (0.0, 3.0)),
        ((1.0, 2.0), (3.0, 0.0)),
    ]
    for point_1, point_2 in zero_cases:
        zero_line = LinePDF(point_1, point_2, drawing_style)
        assert zero_line.points == [point_1, point_2]

    line.point_2 = Point((3.5, 4.5))  # type: ignore[assignment]
    assert line.point_2 == (3.5, 4.5)


@pytest.mark.condition("LINE-P1")
def test_line_component_rejects_invalid_point_boundaries(drawing_style: DrawingStyle) -> None:
    """LINE-P1: Line endpoints reject malformed, non-finite, boolean, and negative coordinates."""
    invalid_points = [
        ((float("nan"), 1.0), (2.0, 3.0), ValueError),
        ((float("inf"), 1.0), (2.0, 3.0), ValueError),
        ((1.0, float("-inf")), (2.0, 3.0), ValueError),
        ((True, 1.0), (2.0, 3.0), TypeError),
        ((1.0,), (2.0, 3.0), ValueError),
        ((1.0, 2.0, 3.0), (2.0, 3.0), ValueError),
        (("x", 1.0), (2.0, 3.0), ValueError),
        ((-0.1, 1.0), (2.0, 3.0), ValueError),
        ((1.0, -0.1), (2.0, 3.0), ValueError),
        ((1.0, 1.0), (-0.1, 3.0), ValueError),
        ((1.0, 1.0), (2.0, -0.1), ValueError),
    ]
    for point_1, point_2, error_type in invalid_points:
        with pytest.raises(error_type):
            LinePDF(point_1, point_2, drawing_style)  # type: ignore[arg-type]

    line = LinePDF((1.0, 1.0), (2.0, 2.0), drawing_style)
    with pytest.raises(ValueError):
        line.point_1 = (float("nan"), 1.0)
    with pytest.raises(TypeError):
        line.point_2 = (1.0, False)  # type: ignore[assignment]
    with pytest.raises(ValueError):
        line.point_2 = (-1.0, 2.0)
    with pytest.raises(ValueError):
        line.point_1 = Point((float("nan"), 1.0))  # type: ignore[assignment]

    assert line.points == [(1.0, 1.0), (2.0, 2.0)]


@pytest.mark.condition("LINE-P1")
def test_line_svg_emits_exact_open_path(drawing_style: DrawingStyle) -> None:
    """LINE-P1: LineSVG emits one open path from point_1 to point_2."""
    line = LineSVG((1.25, 2.5), (9.75, 6.0), drawing_style)

    assert (
        line.generate_svg()
        == f"""<path
            style="fill:none;stroke:#000000;stroke-width:0.2;stroke-opacity:1.0"
            d="M 1.25,2.5 L 9.75,6.0"
            id="path{line.id}" />"""
    )


@pytest.mark.condition("LINE-P1")
def test_line_pdf_emits_exact_open_stroked_path(drawing_style: DrawingStyle) -> None:
    """LINE-P1: LinePDF emits an open stroked path without close or fill operators."""
    line = LinePDF((1.25, 2.5), (9.75, 6.0), drawing_style)

    assert line.generate_pdf() == "\n".join(
        [
            "q",
            "0 0 0 RG",
            "0.2 w",
            "1.25 2.5 m",
            "9.75 6 l",
            "S",
            "Q",
        ]
    )

    fill_style = DrawingStyle(name=f"line_fill_{uuid.uuid4().hex}", stroke="#000000", stroke_width=0.2, fill="#ff0000")
    filled_line = LinePDF((1.0, 2.0), (3.0, 4.0), fill_style)
    assert filled_line.generate_pdf() == "\n".join(
        [
            "q",
            "0 0 0 RG",
            "0.2 w",
            "1 2 m",
            "3 4 l",
            "S",
            "Q",
        ]
    )


@pytest.mark.condition("LINE-P1")
def test_line_primitives_round_trip_parameters(drawing_style: DrawingStyle) -> None:
    """LINE-P1: SVG and PDF line primitives recreate from serialized parameters."""
    svg = LineSVG((1.25, 2.5), (9.75, 6.0), drawing_style)
    pdf = LinePDF((1.25, 2.5), (9.75, 6.0), drawing_style)

    assert LineSVG.create_from_dict(svg.parameters, drawing_style).parameters == svg.parameters
    assert LinePDF.create_from_dict(pdf.parameters, drawing_style).parameters == pdf.parameters


@pytest.mark.condition("LINE-P1")
def test_line_drawing_materializes_svg_and_pdf_components(drawing_style: DrawingStyle) -> None:
    """LINE-P1: Neutral line recipes materialize to SVG and PDF line components."""
    drawing = LineDrawing((1.25, 2.5), (9.75, 6.0), drawing_style)

    svg = drawing.to_component("svg")
    pdf = drawing.to_component(OutputFormat.PDF)

    assert isinstance(svg, LineSVG)
    assert isinstance(pdf, LinePDF)
    assert svg.points == [(1.25, 2.5), (9.75, 6.0)]
    assert pdf.points == [(1.25, 2.5), (9.75, 6.0)]
    with pytest.raises(ValueError):
        drawing.to_component("dxf")


@pytest.mark.condition("LINE-DRAWING-GEOMETRY-P2")
def test_line_drawing_normalizes_geometry_before_materialization(drawing_style: DrawingStyle) -> None:
    """LINE-DRAWING-GEOMETRY-P2: Neutral line endpoints normalize at construction."""
    drawing = LineDrawing([0, 2], [3, 0], drawing_style)  # type: ignore[arg-type]

    assert drawing.point_1 == (0.0, 2.0)
    assert drawing.point_2 == (3.0, 0.0)
    assert drawing.to_component(OutputFormat.SVG).points == [(0.0, 2.0), (3.0, 0.0)]
    assert drawing.to_component(OutputFormat.PDF).points == [(0.0, 2.0), (3.0, 0.0)]


@pytest.mark.condition("LINE-DRAWING-GEOMETRY-P2")
@pytest.mark.parametrize(
    ("point_1", "point_2"),
    [
        ("12", (2.0, 3.0)),
        ([1.0], (2.0, 3.0)),
        ([1.0, 2.0, 3.0], (2.0, 3.0)),
        ({"x": 1.0, "y": 2.0}, (2.0, 3.0)),
        ((object(), 1.0), (2.0, 3.0)),
        (("x", 1.0), (2.0, 3.0)),
        ((True, 1.0), (2.0, 3.0)),
        ((float("nan"), 1.0), (2.0, 3.0)),
        ((-0.1, 1.0), (2.0, 3.0)),
        ((1.0, 1.0), (-0.1, 3.0)),
    ],
)
def test_line_drawing_rejects_malformed_geometry_payloads(
    drawing_style: DrawingStyle,
    point_1: object,
    point_2: object,
) -> None:
    """LINE-DRAWING-GEOMETRY-P2: Neutral line endpoints reject malformed payloads."""
    with pytest.raises((TypeError, ValueError)):
        LineDrawing(point_1, point_2, drawing_style)  # type: ignore[arg-type]


@pytest.mark.condition("LINE-DRAWING-GEOMETRY-P2")
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("point_1", "12"),
        ("point_1", [1.0]),
        ("point_1", [1.0, 2.0, 3.0]),
        ("point_2", {"x": 3.0, "y": 4.0}),
        ("point_1", (object(), 1.0)),
        ("point_1", ("x", 1.0)),
        ("point_1", (True, 1.0)),
        ("point_2", (3.0, float("nan"))),
        ("point_1", (-0.1, 1.0)),
        ("point_2", (3.0, -0.1)),
    ],
)
def test_flow_document_hydration_rejects_malformed_line_geometry_payloads(
    drawing_style: DrawingStyle,
    field: str,
    value: object,
) -> None:
    """LINE-DRAWING-GEOMETRY-P2: Flow documents cannot hydrate bad line endpoints."""
    group = DrawingComponentGroup("line-flow")
    group.add_component(LineDrawing((1.0, 2.0), (3.0, 4.0), drawing_style))
    document = FlowDocument(title="Bad Line")
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
    component_payload[field] = value

    with pytest.raises((TypeError, ValueError)):
        FlowDocument.create_from_dict(payload, {drawing_style.name: drawing_style})


@pytest.mark.condition("LINE-P1")
def test_dxf_line_drawing_exports_line_entity_with_canvas_transform(drawing_style: DrawingStyle) -> None:
    """LINE-P1: DXF line export emits a LINE entity and applies canvas-height Y inversion."""
    drawing = LineDrawing((1.25, 2.5), (9.75, 6.0), drawing_style)
    document = DXFDocument(canvas_height=20.0)
    group = DrawingComponentGroup("line_layer", [drawing])

    document.add_group(group)
    payload = document.to_dxf_string()
    codes = _dxf_line_codes(payload)

    assert "\nLINE\n" in payload
    assert "\n0\nLINE\n" in payload
    assert "\nLWPOLYLINE\n" not in payload
    assert codes["8"] == "line_layer"
    assert codes["10"] == "1.25"
    assert codes["20"] == "17.5"
    assert codes["30"] == "0"
    assert codes["11"] == "9.75"
    assert codes["21"] == "14"
    assert codes["31"] == "0"
