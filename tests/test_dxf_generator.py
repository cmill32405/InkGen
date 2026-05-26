"""Tests for dependency-free DXF output."""

from __future__ import annotations

from uuid import uuid4

import pytest

from InkGen.component import PathCommand
from InkGen.drawing_components import (
    CircleDrawing,
    DrawingComponentGroup,
    LineDrawing,
    PathDrawing,
    PolygonalDrawing,
    RectangleDrawing,
    TextDrawing,
)
from InkGen.dxf_generator import DXFDocument
from InkGen.style import DrawingStyle, Font, TextStyle


def _styles() -> tuple[DrawingStyle, TextStyle]:
    drawing_style = DrawingStyle(f"dxf_line_{uuid4().hex}", stroke="#000000", fill="none")
    text_style = TextStyle(f"dxf_text_{uuid4().hex}", Font(size=9.0))
    return drawing_style, text_style


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
