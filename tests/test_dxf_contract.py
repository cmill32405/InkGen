"""DXF renderer contract tests."""

from __future__ import annotations

from uuid import uuid4

import pytest

from InkGen.component import PathCommand
from InkGen.drawing_components import (
    ArcDrawing,
    CircleDrawing,
    CubicBezierDrawing,
    DrawingComponentGroup,
    LineDrawing,
    OutputFormat,
    PathDrawing,
    RectangleDrawing,
    RegularPolygonDrawing,
    TextDrawing,
)
from InkGen.dxf_generator import DXFDocument, DXFRenderContext, _append_corner_arc, _component_to_entities, _format_value, _rectangle_points
from InkGen.style import DrawingStyle, Font, TextStyle


def _drawing_style() -> DrawingStyle:
    return DrawingStyle(f"dxf_contract_{uuid4().hex}", stroke="#000000", fill="none")


def _text_style() -> TextStyle:
    return TextStyle(f"dxf_text_{uuid4().hex}", Font(size=9.0))


def _vertices(payload: str) -> list[tuple[float, float]]:
    lines = payload.splitlines()
    vertices: list[tuple[float, float]] = []
    index = 0
    while index < len(lines) - 1:
        if lines[index] == "10":
            x = float(lines[index + 1])
            assert lines[index + 2] == "20"
            y = float(lines[index + 3])
            vertices.append((x, y))
            index += 4
        else:
            index += 1
    return vertices


@pytest.mark.condition("DXF-P1")
def test_dxf_context_and_numeric_format_are_deterministic() -> None:
    """DXF-P1: Context coordinate conversion and value formatting stay deterministic."""
    default_context = DXFRenderContext()
    flipped_context = DXFRenderContext(canvas_height=100.0)

    assert default_context.point(2, 3) == (2.0, 3.0)
    assert flipped_context.point(2, 3) == (2.0, 97.0)
    assert _format_value(2.0) == "2"
    assert _format_value(2.000001) == "2.000001"
    assert _format_value(2.125000) == "2.125"
    assert _format_value("layer") == "layer"


@pytest.mark.condition("DXF-P1")
def test_dxf_context_rejects_malformed_coordinate_boundaries() -> None:
    """DXF-P1: Context coordinates and canvas heights must be finite non-boolean numbers."""
    context = DXFRenderContext(canvas_height=100.0)

    for value in [True, False, float("nan"), float("inf"), -float("inf"), "1", object()]:
        with pytest.raises((TypeError, ValueError)):
            DXFRenderContext(canvas_height=value)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            DXFDocument(canvas_height=value)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            context.point(value, 2.0)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            context.point(1.0, value)  # type: ignore[arg-type]

    with pytest.raises(ValueError):
        DXFRenderContext(canvas_height=-0.1)
    with pytest.raises(ValueError):
        DXFDocument(canvas_height=-0.1)

    assert context.point(1.0, 2.0) == (1.0, 98.0)
    assert DXFRenderContext(canvas_height=0.0).point(1.0, 2.0) == (1.0, -2.0)
    assert DXFDocument(canvas_height=0.0).to_dxf_string().endswith("0\nEOF\n")


@pytest.mark.condition("DXF-P1")
def test_dxf_document_layers_and_ascii_text_contract() -> None:
    """DXF-P1: DXFDocument emits layer codes, flipped coordinates, and ASCII text."""
    style = _drawing_style()
    group = DrawingComponentGroup("source-layer")
    group.add_component(LineDrawing((1.0, 2.0), (3.0, 4.0), style))
    group.add_component(TextDrawing("ZONE\nA", (5.0, 6.0), _text_style()))
    document = DXFDocument(canvas_height=100.0)

    document.add_group(group, layer="override")
    payload = document.to_dxf_string()

    assert payload.count("\n8\noverride\n") == 2
    assert "\n10\n1\n20\n98\n" in payload
    assert "\n11\n3\n21\n96\n" in payload
    assert (
        _component_to_entities(TextDrawing("ZONE\nA", (5.0, 6.0), _text_style()), DXFRenderContext(canvas_height=100.0, layer="L"))[0]
        == "0\nTEXT\n8\nL\n10\n5\n20\n94\n30\n0\n40\n3.175\n1\nZONE A"
    )
    payload.encode("ascii")


@pytest.mark.condition("DXF-P1")
def test_dxf_document_layer_fallback_and_write_guard(tmp_path) -> None:
    """DXF-P1: DXFDocument uses layer fallbacks and rejects missing output directories."""
    style = _drawing_style()
    labeled = DrawingComponentGroup("source-layer")
    labeled.add_component(LineDrawing((0.0, 0.0), (1.0, 1.0), style))
    unlabeled = DrawingComponentGroup("")
    unlabeled.add_component(LineDrawing((2.0, 2.0), (3.0, 3.0), style))
    document = DXFDocument()

    document.add_group(labeled)
    document.add_group(unlabeled)
    payload = document.to_dxf_string()

    assert "\n8\nsource-layer\n" in payload
    assert "\n8\n0\n" in payload
    with pytest.raises(ValueError, match="file path does not exist"):
        document.create_dxf(str(tmp_path / "missing" / "drawing.dxf"))

    target = tmp_path / "drawing.dxf"
    document.create_dxf(str(target))
    assert target.read_text(encoding="ascii") == document.to_dxf_string()


@pytest.mark.condition("DXF-P1")
def test_dxf_rectangle_and_path_closure_contracts() -> None:
    """DXF-P1: Rectangle and path exports preserve vertex counts and closure flags."""
    style = _drawing_style()
    rounded = RectangleDrawing((10.0, 20.0), 30.0, 40.0, (5.0, 8.0), style)
    rounded_points = _rectangle_points(rounded)
    closed_path = PathDrawing(
        style,
        [
            PathCommand("M", [(0.0, 0.0)]),
            PathCommand("L", [(10.0, 0.0)]),
            PathCommand("L", [(10.0, 10.0)]),
            PathCommand("Z", []),
        ],
    )
    open_path = PathDrawing(style, [PathCommand("M", [(0.0, 0.0)]), PathCommand("L", [(10.0, 0.0)])])

    rounded_entity = _component_to_entities(rounded, DXFRenderContext(layer="rounded"))[0]
    path_entity = _component_to_entities(closed_path, DXFRenderContext(layer="path"))[0]
    open_path_entity = _component_to_entities(open_path, DXFRenderContext(layer="path"))[0]
    expected_rounded_points = [
        (15.0, 20.0),
        (35.0, 20.0),
        (36.913417, 20.608964),
        (38.535534, 22.343146),
        (39.619398, 24.938533),
        (40.0, 28.0),
        (40.0, 52.0),
        (39.619398, 55.061467),
        (38.535534, 57.656854),
        (36.913417, 59.391036),
        (35.0, 60.0),
        (15.0, 60.0),
        (13.086583, 59.391036),
        (11.464466, 57.656854),
        (10.380602, 55.061467),
        (10.0, 52.0),
        (10.0, 28.0),
        (10.380602, 24.938533),
        (11.464466, 22.343146),
        (13.086583, 20.608964),
    ]

    assert len(rounded_points) == 20
    assert rounded_points == expected_rounded_points
    assert rounded_points[0] != rounded_points[-1]
    assert rounded_entity.startswith("0\nLWPOLYLINE\n8\nrounded\n90\n20\n70\n1\n")
    assert path_entity.startswith("0\nLWPOLYLINE\n8\npath\n90\n3\n70\n1\n")
    assert open_path_entity.startswith("0\nLWPOLYLINE\n8\npath\n90\n2\n70\n0\n")
    assert _vertices(rounded_entity) == expected_rounded_points


@pytest.mark.condition("DXF-P1")
def test_dxf_sharp_rectangle_and_corner_duplicate_contract() -> None:
    """DXF-P1: Sharp rectangles and sampled corner arcs avoid duplicate points."""
    style = _drawing_style()
    sharp = RectangleDrawing((1.0, 2.0), 3.0, 4.0, 0.0, style)
    zero_y_radius = RectangleDrawing((1.0, 2.0), 3.0, 4.0, (1.0, 0.0), style)
    small_radius = RectangleDrawing((0.1234567, 0.7654321), 10.0, 10.0, (1.0, 2.0), style)
    points = [(1.0, 0.0)]
    trailing_duplicate = [(0.0, 0.0), (1.0, 0.0)]

    _append_corner_arc(points, center=(0.0, 0.0), rx=1.0, ry=1.0, start_degrees=0.0, end_degrees=0.0)
    _append_corner_arc(trailing_duplicate, center=(0.0, 0.0), rx=1.0, ry=1.0, start_degrees=0.0, end_degrees=0.0)

    assert _rectangle_points(sharp) == [(1.0, 2.0), (4.0, 2.0), (4.0, 6.0), (1.0, 6.0)]
    assert _rectangle_points(zero_y_radius) == [(1.0, 2.0), (4.0, 2.0), (4.0, 6.0), (1.0, 6.0)]
    assert _rectangle_points(small_radius)[0] == (1.123457, 0.765432)
    assert len(_rectangle_points(small_radius)) == 20
    assert points == [(1.0, 0.0)]
    assert trailing_duplicate == [(0.0, 0.0), (1.0, 0.0)]


@pytest.mark.condition("DXF-P1")
def test_dxf_circle_entity_contract() -> None:
    """DXF-P1: Circle entities preserve center, flipped y coordinate, and radius."""
    circle = CircleDrawing((10.0, 12.0), 5.0, _drawing_style())

    entity = _component_to_entities(circle, DXFRenderContext(canvas_height=100.0, layer="C"))[0]

    assert entity == "0\nCIRCLE\n8\nC\n10\n10\n20\n88\n30\n0\n40\n5"


@pytest.mark.condition("DXF-P1")
def test_dxf_pdf_sampled_geometry_contract_for_indirect_components() -> None:
    """DXF-P1: DXF indirect geometry branches reuse PDF-sampled points."""
    style = _drawing_style()
    context = DXFRenderContext(layer="sampled")
    components = [
        ArcDrawing((0.0, 0.0), 5.0, 3.0, 0.0, 90.0, style),
        CubicBezierDrawing((0.0, 0.0), (3.0, 6.0), (6.0, 6.0), (9.0, 0.0), style),
        RegularPolygonDrawing((5.0, 5.0), 5, 4.0, style, angle=18.0),
        PathDrawing(style, [PathCommand("M", [(0.0, 0.0)]), PathCommand("L", [(3.0, 0.0)])]),
    ]

    for component in components:
        entity = _component_to_entities(component, context)[0]
        expected_points = [(round(float(x), 6), round(float(y), 6)) for x, y in component.to_component(OutputFormat.PDF).points]

        assert "\n8\nsampled\n" in entity
        assert f"\n90\n{len(expected_points)}\n" in entity
        assert _vertices(entity) == expected_points
