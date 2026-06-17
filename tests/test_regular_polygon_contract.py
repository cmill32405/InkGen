"""Tests for regular polygon renderer proof obligations."""

from __future__ import annotations

import math
from uuid import uuid4

import pytest

from InkGen.component import RegularPolygonDrawingComponent
from InkGen.drawing_components import DrawingComponentGroup, OutputFormat, RegularPolygonDrawing
from InkGen.dxf_generator import DXFDocument
from InkGen.pdf_generator import RegularPolygonPDF
from InkGen.style import DrawingStyle


def _regular_polygon_points(
    position: tuple[float, float],
    sides: int,
    radius: float,
    angle: float,
) -> list[tuple[float, float]]:
    return [
        (
            position[0] + radius * math.cos(math.radians((angle + 90.0 + point_index * 360.0 / sides) % 360.0)),
            position[1] + radius * math.sin(math.radians((angle + 90.0 + point_index * 360.0 / sides) % 360.0)),
        )
        for point_index in range(sides)
    ]


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


def _pdf_number(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".") or "0"


@pytest.fixture
def drawing_style() -> DrawingStyle:
    """Return a drawing style for regular polygon contract tests."""
    return DrawingStyle(name=f"regular_polygon_contract_{uuid4().hex}", stroke="#000000", stroke_width=0.2, fill="none")


@pytest.mark.condition("REGPOLY-P1")
def test_regular_polygon_vertices_follow_radius_angle_formula(drawing_style: DrawingStyle) -> None:
    """REGPOLY-P1: Regular polygon vertices follow InkGen's radius/angle formula."""
    cases = [
        ((20.0, 20.0), 3, 10.0, 0.0),
        ((15.0, 12.0), 5, 7.5, 15.0),
        ((8.0, 9.0), 8, 2.25, -30.0),
        ((20.0, 20.0), 7, 6.0, 12.0),
    ]

    for position, sides, radius, angle in cases:
        polygon = RegularPolygonDrawingComponent(position, sides, radius, drawing_style, angle)
        expected_points = _regular_polygon_points(position, sides, polygon.radius, polygon.angle)

        assert len(polygon.points) == sides
        for actual, expected in zip(polygon.points, expected_points, strict=True):
            assert actual == (pytest.approx(expected[0]), pytest.approx(expected[1]))
            assert math.dist(position, actual) == pytest.approx(radius, abs=1e-3)


@pytest.mark.condition("REGPOLY-P1")
def test_regular_polygon_rejects_invalid_boundaries(drawing_style: DrawingStyle) -> None:
    """REGPOLY-P1: Regular polygon validation fails at public boundaries."""
    with pytest.raises(ValueError, match="3 or more sides"):
        RegularPolygonDrawingComponent((0.0, 0.0), 2, 10.0, drawing_style)
    with pytest.raises(TypeError, match="integer"):
        RegularPolygonDrawingComponent((0.0, 0.0), 3.5, 10.0, drawing_style)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="greater than zero"):
        RegularPolygonDrawingComponent((0.0, 0.0), 3, 0.0, drawing_style)
    with pytest.raises(ValueError, match="greater than zero"):
        RegularPolygonDrawingComponent((10.0, 10.0), 3, -0.5, drawing_style)
    with pytest.raises(ValueError, match="non-negative"):
        RegularPolygonDrawingComponent((0.0, 0.0), 3, 10.0, drawing_style, corner_radius=-0.1)
    with pytest.raises(ValueError, match="not exceed half"):
        RegularPolygonDrawingComponent((0.0, 0.0), 3, 10.0, drawing_style, corner_radius=5.1)

    small_polygon = RegularPolygonDrawingComponent((10.0, 10.0), 3, 0.5, drawing_style)
    assert small_polygon.radius == pytest.approx(0.5, abs=1e-3)

    polygon = RegularPolygonDrawingComponent((0.0, 0.0), 3, 10.0, drawing_style, corner_radius=5.0)
    assert polygon.corner_radius == 5.0
    with pytest.raises(ValueError, match="not exceed half"):
        polygon.radius = 8.0

    setter_polygon = RegularPolygonDrawingComponent((10.0, 10.0), 3, 10.0, drawing_style)
    setter_polygon.radius = 0.5
    assert setter_polygon.radius == pytest.approx(0.5, abs=1e-3)
    with pytest.raises(ValueError, match="greater than zero"):
        setter_polygon.radius = 0.0
    with pytest.raises(ValueError, match="greater than zero"):
        setter_polygon.radius = -0.5

    exact_half_polygon = RegularPolygonDrawingComponent((10.0, 10.0), 3, 10.0, drawing_style, corner_radius=4.0)
    exact_half_polygon.radius = 8.0
    assert exact_half_polygon.radius == pytest.approx(8.0, abs=1e-3)

    fractional_half_polygon = RegularPolygonDrawingComponent((10.0, 10.0), 3, 9.0, drawing_style, corner_radius=4.5)
    assert fractional_half_polygon.corner_radius == 4.5

    fractional_setter_polygon = RegularPolygonDrawingComponent((10.0, 10.0), 3, 10.0, drawing_style, corner_radius=4.6)
    fractional_setter_polygon.radius = 9.5
    assert fractional_setter_polygon.radius == pytest.approx(9.5, abs=1e-3)


@pytest.mark.condition("REGPOLY-P1")
def test_regular_polygon_pdf_emits_closed_path_from_component_points(drawing_style: DrawingStyle) -> None:
    """REGPOLY-P1: RegularPolygonPDF emits a closed path from component vertices."""
    polygon = RegularPolygonPDF((1.0, 2.0), 5, 4.0, drawing_style, angle=10.0)
    points = polygon.points

    content = polygon.generate_pdf()

    assert f"{_pdf_number(points[0][0])} {_pdf_number(points[0][1])} m" in content
    assert content.count(" l") == len(points) - 1
    assert "\nh\n" in content
    assert content.endswith("\nS\nQ")


@pytest.mark.condition("REGPOLY-P1")
def test_regular_polygon_drawing_materializes_pdf_component(drawing_style: DrawingStyle) -> None:
    """REGPOLY-P1: Neutral regular polygons materialize to RegularPolygonPDF."""
    polygon = RegularPolygonDrawing((2.0, 3.0), 6, 5.0, drawing_style, angle=30.0)

    concrete = polygon.to_component(OutputFormat.PDF)

    assert isinstance(concrete, RegularPolygonPDF)
    assert concrete.points == RegularPolygonPDF((2.0, 3.0), 6, 5.0, drawing_style, angle=30.0).points


@pytest.mark.condition("REGPOLY-P1")
def test_dxf_regular_polygon_reuses_pdf_points_as_closed_polyline(drawing_style: DrawingStyle) -> None:
    """REGPOLY-P1: DXF regular polygon export uses PDF-materialized vertices."""
    polygon = RegularPolygonDrawing((2.0, 3.0), 6, 5.0, drawing_style, angle=30.0)
    group = DrawingComponentGroup("regular_polygon")
    group.add_component(polygon)
    expected_points = polygon.to_component(OutputFormat.PDF).points

    document = DXFDocument()
    document.add_group(group)
    payload = document.to_dxf_string()

    assert "\nLWPOLYLINE\n" in payload
    assert "\n8\nregular_polygon\n" in payload
    assert f"\n90\n{len(expected_points)}\n" in payload
    assert "\n70\n1\n" in payload
    actual_points = _dxf_polyline_vertices(payload)
    assert len(actual_points) == len(expected_points)
    for actual, expected in zip(actual_points, expected_points, strict=True):
        assert actual == (pytest.approx(expected[0], abs=1e-6), pytest.approx(expected[1], abs=1e-6))
