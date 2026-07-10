"""Tests for circle renderer proof obligations."""

from __future__ import annotations

from uuid import uuid4

import pytest

from InkGen.drawing_components import CircleDrawing, DrawingComponentGroup, OutputFormat
from InkGen.dxf_generator import DXFDocument
from InkGen.pdf_generator import CirclePDF
from InkGen.style import DrawingStyle
from InkGen.svg_generator import CircleSVG

KAPPA = 0.5522847498307936


def _pdf_number(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".") or "0"


def _dxf_group_values(payload: str, code: str) -> list[str]:
    lines = payload.splitlines()
    start = lines.index("CIRCLE") - 1
    entity_lines = lines[start : start + 16]
    values: list[str] = []
    for index in range(0, len(entity_lines) - 1, 2):
        line = entity_lines[index]
        if line == code:
            values.append(entity_lines[index + 1])
    return values


@pytest.fixture
def drawing_style() -> DrawingStyle:
    """Return a drawing style for circle contract tests."""
    return DrawingStyle(name=f"circle_contract_{uuid4().hex}", stroke="#000000", stroke_width=0.2, fill="none")


@pytest.mark.condition("CIRCLE-P1")
def test_circle_pdf_rejects_invalid_radius_boundaries(drawing_style: DrawingStyle) -> None:
    """CIRCLE-P1: CirclePDF rejects non-positive and non-numeric radii."""
    with pytest.raises(ValueError, match="Radii must be greater than 0"):
        CirclePDF((10.0, 20.0), 0.0, drawing_style)
    with pytest.raises(ValueError, match="Radii must be greater than 0"):
        CirclePDF((10.0, 20.0), -0.5, drawing_style)
    with pytest.raises(ValueError, match="Radii must be greater than 0"):
        CirclePDF((10.0, 20.0), (5.0, 5.0), drawing_style)  # type: ignore[arg-type]

    circle = CirclePDF((10.0, 20.0), 0.5, drawing_style)
    assert circle.radius == pytest.approx(0.5)


@pytest.mark.condition("CIRCLE-P1")
def test_circle_pdf_emits_four_cubic_bezier_segments(drawing_style: DrawingStyle) -> None:
    """CIRCLE-P1: CirclePDF uses the standard four-cubic circle approximation."""
    circle = CirclePDF((10.0, 20.0), 5.0, drawing_style)
    control = 5.0 * KAPPA

    content = circle.generate_pdf()
    lines = content.splitlines()

    expected_path = [
        f"{_pdf_number(15.0)} {_pdf_number(20.0)} m",
        f"{_pdf_number(15.0)} {_pdf_number(20.0 + control)} {_pdf_number(10.0 + control)} {_pdf_number(25.0)} 10 25 c",
        f"{_pdf_number(10.0 - control)} 25 5 {_pdf_number(20.0 + control)} 5 20 c",
        f"5 {_pdf_number(20.0 - control)} {_pdf_number(10.0 - control)} 15 10 15 c",
        f"{_pdf_number(10.0 + control)} 15 15 {_pdf_number(20.0 - control)} 15 20 c",
        "h",
    ]
    for operator in expected_path:
        assert operator in lines
    assert content.count(" c") == 4
    assert "\nh\n" in content
    assert content.endswith("\nS\nQ")


@pytest.mark.condition("CIRCLE-P1")
def test_circle_drawing_materializes_svg_and_pdf_components(drawing_style: DrawingStyle) -> None:
    """CIRCLE-P1: Neutral circle recipes materialize to SVG and PDF components."""
    circle = CircleDrawing((10.0, 20.0), 5.0, drawing_style)

    svg_component = circle.to_component(OutputFormat.SVG)
    pdf_component = circle.to_component(OutputFormat.PDF)

    assert isinstance(svg_component, CircleSVG)
    assert isinstance(pdf_component, CirclePDF)
    assert svg_component.position == pdf_component.position == (10.0, 20.0)
    assert svg_component.radius == pdf_component.radius == 5.0


@pytest.mark.condition("CIRCLE-P1")
def test_dxf_circle_drawing_emits_native_circle_entity(drawing_style: DrawingStyle) -> None:
    """CIRCLE-P1: DXF circle export emits one native CIRCLE entity."""
    circle = CircleDrawing((10.0, 20.0), 5.0, drawing_style)
    group = DrawingComponentGroup("circle")
    group.add_component(circle)

    document = DXFDocument()
    document.add_group(group)
    payload = document.to_dxf_string()

    assert payload.count("\nCIRCLE\n") == 1
    assert "\n0\nCIRCLE\n" in payload
    assert "\n8\ncircle\n" in payload
    assert _dxf_group_values(payload, "10") == ["10"]
    assert _dxf_group_values(payload, "20") == ["20"]
    assert _dxf_group_values(payload, "30") == ["0"]
    assert _dxf_group_values(payload, "40") == ["5"]
