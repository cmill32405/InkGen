"""Tests for dependency-free DXF output."""

from __future__ import annotations

from uuid import uuid4

import pytest

from InkGen.component import PathCommand
from InkGen.drawing_components import (
    CircleDrawing,
    DrawingComponentGroup,
    LineDrawing,
    OutputFormat,
    PathDrawing,
    PolygonalDrawing,
    QuadraticBezierDrawing,
    RectangleDrawing,
    TextDrawing,
)
from InkGen.dxf_generator import DXFDocument, DXFRenderContext, _lwpolyline_entity
from InkGen.style import DrawingStyle, Font, TextStyle


def _styles() -> tuple[DrawingStyle, TextStyle]:
    drawing_style = DrawingStyle(f"dxf_line_{uuid4().hex}", stroke="#000000", fill="none")
    text_style = TextStyle(f"dxf_text_{uuid4().hex}", Font(size=9.0))
    return drawing_style, text_style


def _dxf_polyline_vertices(payload: str) -> list[tuple[float, float]]:
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


@pytest.mark.condition("PDF-P3")
def test_dxf_document_exports_neutral_drawing_group() -> None:
    """PDF-P3: DXFDocument exports neutral drawing primitives as DXF entities."""
    drawing_style, text_style = _styles()
    group = DrawingComponentGroup("drawing")
    group.add_component(RectangleDrawing((10.0, 20.0), 30.0, 40.0, 0.0, drawing_style))
    group.add_component(LineDrawing((1.0, 2.0), (3.0, 4.0), drawing_style))
    group.add_component(CircleDrawing((10.0, 10.0), 5.0, drawing_style))
    group.add_component(PolygonalDrawing([(0.0, 0.0), (2.0, 0.0), (1.0, 2.0)], drawing_style))
    group.add_component(PathDrawing(drawing_style, [PathCommand("M", [(0.0, 0.0)]), PathCommand("L", [(3.0, 0.0)])]))
    group.add_component(TextDrawing("ZONE A", (5.0, 6.0), text_style))

    document = DXFDocument(canvas_height=100.0)
    document.add_group(group)
    payload = document.to_dxf_string()

    assert payload.startswith("0\nSECTION\n2\nHEADER")
    assert "\nLWPOLYLINE\n" in payload
    assert "\nLINE\n" in payload
    assert "\nCIRCLE\n" in payload
    assert "\nTEXT\n" in payload
    assert payload.count("\nLWPOLYLINE\n") == 3
    assert "\nZONE A\n" in payload
    assert "\n20\n80\n" in payload
    assert payload.endswith("0\nEOF\n")


@pytest.mark.condition("PDF-P3")
def test_dxf_document_writes_file_and_rejects_bad_paths(tmp_path) -> None:
    """PDF-P3: DXFDocument writes ASCII DXF and fails loudly for missing directories."""
    drawing_style, _ = _styles()
    group = DrawingComponentGroup("line")
    group.add_component(LineDrawing((0.0, 0.0), (1.0, 1.0), drawing_style))
    document = DXFDocument()
    document.add_group(group)

    target = tmp_path / "drawing.dxf"
    document.create_dxf(str(target))

    assert target.read_text(encoding="ascii") == document.to_dxf_string()
    with pytest.raises(ValueError, match="file path does not exist"):
        document.create_dxf(str(tmp_path / "missing" / "drawing.dxf"))


@pytest.mark.condition("PDF-P3")
def test_dxf_document_rejects_unsupported_groups_and_components() -> None:
    """PDF-P3: DXFDocument fails loudly for unsupported DXF inputs."""
    document = DXFDocument()

    with pytest.raises(TypeError, match="group must be a DrawingComponentGroup"):
        document.add_group(object())  # type: ignore[arg-type]

    group = DrawingComponentGroup("bad")
    group.components.append(object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="Unsupported DXF component"):
        document.add_group(group)


@pytest.mark.condition("CURVE-P1")
def test_dxf_quadratic_bezier_reuses_pdf_sample_points() -> None:
    """CURVE-P1: DXF curve export uses the neutral curve's PDF-sampled points."""
    drawing_style, _ = _styles()
    curve = QuadraticBezierDrawing((0.0, 0.0), (3.0, 6.0), (9.0, 0.0), drawing_style)
    group = DrawingComponentGroup("curve")
    group.add_component(curve)
    expected_points = curve.to_component(OutputFormat.PDF).points

    document = DXFDocument()
    document.add_group(group)
    payload = document.to_dxf_string()

    assert "\nLWPOLYLINE\n" in payload
    assert "\n0\nLWPOLYLINE\n" in payload
    assert "\n8\ncurve\n" in payload
    assert f"\n90\n{len(expected_points)}\n" in payload
    assert "\n70\n0\n" in payload
    assert _dxf_polyline_vertices(payload) == expected_points


@pytest.mark.condition("CURVE-P1")
def test_dxf_polyline_entity_records_open_and_closed_flags() -> None:
    """CURVE-P1: DXF polylines preserve group codes and closure flags."""
    context = DXFRenderContext(layer="curve")

    open_entity = _lwpolyline_entity([(0.0, 0.0), (1.0, 1.0)], context, closed=False)
    closed_entity = _lwpolyline_entity([(0.0, 0.0), (1.0, 1.0)], context, closed=True)

    assert open_entity.startswith("0\nLWPOLYLINE\n8\ncurve\n90\n2\n70\n0\n")
    assert closed_entity.startswith("0\nLWPOLYLINE\n8\ncurve\n90\n2\n70\n1\n")
