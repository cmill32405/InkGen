"""Tests for curve renderer proof obligations."""

from __future__ import annotations

import math
from uuid import uuid4

import pytest

from InkGen.component import PRECISION, Arc, CubicBezier, QuadraticBezier
from InkGen.drawing_components import ArcDrawing, CubicBezierDrawing, DrawingComponentGroup, OutputFormat
from InkGen.dxf_generator import DXFDocument
from InkGen.pdf_generator import ArcPDF, CubicBezierPDF
from InkGen.style import DrawingStyle


def _arc_point(
    center: tuple[float, float],
    radius_x: float,
    radius_y: float,
    angle: float,
    rotation: float,
) -> tuple[float, float]:
    theta = math.radians(angle)
    rotation_rad = math.radians(rotation)
    x = radius_x * math.cos(theta)
    y = radius_y * math.sin(theta)
    x_rot = x * math.cos(rotation_rad) - y * math.sin(rotation_rad)
    y_rot = x * math.sin(rotation_rad) + y * math.cos(rotation_rad)
    return (
        float(round(center[0] + x_rot, PRECISION)),
        float(round(center[1] + y_rot, PRECISION)),
    )


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


def _quadratic_point(
    start: tuple[float, float],
    control: tuple[float, float],
    end: tuple[float, float],
    t: float,
) -> tuple[float, float]:
    one_minus_t = 1.0 - t
    return (
        one_minus_t**2 * start[0] + 2 * one_minus_t * t * control[0] + t**2 * end[0],
        one_minus_t**2 * start[1] + 2 * one_minus_t * t * control[1] + t**2 * end[1],
    )


def _cubic_point(
    start: tuple[float, float],
    control_1: tuple[float, float],
    control_2: tuple[float, float],
    end: tuple[float, float],
    t: float,
) -> tuple[float, float]:
    one_minus_t = 1.0 - t
    return (
        one_minus_t**3 * start[0] + 3 * one_minus_t**2 * t * control_1[0] + 3 * one_minus_t * t**2 * control_2[0] + t**3 * end[0],
        one_minus_t**3 * start[1] + 3 * one_minus_t**2 * t * control_1[1] + 3 * one_minus_t * t**2 * control_2[1] + t**3 * end[1],
    )


@pytest.fixture
def drawing_style() -> DrawingStyle:
    """Return a drawing style for curve contract tests."""
    return DrawingStyle(name=f"curve_contract_{uuid4().hex}", stroke="#000000", stroke_width=0.2, fill="none")


@pytest.mark.condition("ARC-P1")
def test_arc_samples_follow_ellipse_rotation_formula(drawing_style: DrawingStyle) -> None:
    """ARC-P1: Arc samples follow the rotated ellipse formula."""
    cases = [
        ((0.0, 0.0), 10.0, 5.0, 0.0, 90.0, 0.0),
        ((4.0, -3.0), 8.0, 2.5, -45.0, 135.0, 30.0),
        ((2.0, 7.0), 3.5, 9.0, 180.0, 0.0, -15.0),
    ]

    for center, radius_x, radius_y, start_angle, end_angle, rotation in cases:
        arc = Arc(center, radius_x, radius_y, start_angle, end_angle, drawing_style, rotation)
        points = arc.points
        sample_count = len(points) - 1

        assert sample_count == 32
        assert points[0] == _arc_point(center, radius_x, radius_y, start_angle, rotation)
        assert points[-1] == _arc_point(center, radius_x, radius_y, end_angle, rotation)
        for index, point in enumerate(points):
            angle = start_angle + (end_angle - start_angle) * (index / sample_count)
            assert point == _arc_point(center, radius_x, radius_y, angle, rotation)


@pytest.mark.condition("ARC-P1")
def test_arc_equal_start_and_end_angle_emits_single_sample(drawing_style: DrawingStyle) -> None:
    """ARC-P1: A zero-span arc emits one rotated ellipse point."""
    arc = Arc((1.0, 2.0), 4.0, 6.0, 45.0, 45.0, drawing_style, rotation=90.0)

    assert arc.points == [_arc_point((1.0, 2.0), 4.0, 6.0, 45.0, 90.0)]


@pytest.mark.condition("ARC-P1")
def test_arc_tiny_nonzero_angle_span_still_samples_curve(drawing_style: DrawingStyle) -> None:
    """ARC-P1: A tiny non-zero angle span is not collapsed to one point."""
    arc = Arc((0.0, 0.0), 10.0, 5.0, 0.0, 0.1, drawing_style)

    assert len(arc.points) == 33
    assert arc.points[0] == _arc_point((0.0, 0.0), 10.0, 5.0, 0.0, 0.0)
    assert arc.points[-1] == _arc_point((0.0, 0.0), 10.0, 5.0, 0.1, 0.0)


@pytest.mark.condition("ARC-P1")
def test_arc_rejects_non_positive_radii(drawing_style: DrawingStyle) -> None:
    """ARC-P1: Arc radii fail at the boundary when non-positive."""
    with pytest.raises(ValueError, match="radius_x must be greater than zero"):
        Arc((0.0, 0.0), 0.0, 1.0, 0.0, 90.0, drawing_style)
    with pytest.raises(ValueError, match="radius_y must be greater than zero"):
        Arc((0.0, 0.0), 1.0, -1.0, 0.0, 90.0, drawing_style)

    arc = Arc((0.0, 0.0), 1.0, 1.0, 0.0, 90.0, drawing_style)
    with pytest.raises(ValueError, match="radius_x must be greater than zero"):
        arc.radius_x = -0.5
    with pytest.raises(ValueError, match="radius_y must be greater than zero"):
        arc.radius_y = 0.0


@pytest.mark.condition("ARC-P1")
def test_arc_pdf_emits_sampled_open_polyline(drawing_style: DrawingStyle) -> None:
    """ARC-P1: ArcPDF renders InkGen's sampled arc points as an open PDF path."""
    drawing_style.fill = "#ffffff"
    arc = ArcPDF((0.0, 0.0), 10.0, 5.0, 0.0, 90.0, drawing_style)
    points = arc.points

    content = arc.generate_pdf()

    assert content.endswith("\nS\nQ")
    assert "\nh\n" not in content
    assert f"{points[0][0]:g} {points[0][1]:g} m" in content
    assert f"{points[-1][0]:g} {points[-1][1]:g} l" in content
    assert content.count(" l") == len(points) - 1


@pytest.mark.condition("ARC-P1")
def test_arc_drawing_materializes_pdf_component(drawing_style: DrawingStyle) -> None:
    """ARC-P1: Neutral arc recipes materialize to ArcPDF for PDF output."""
    arc = ArcDrawing((0.0, 0.0), 10.0, 5.0, 0.0, 90.0, drawing_style)

    concrete = arc.to_component(OutputFormat.PDF)

    assert isinstance(concrete, ArcPDF)
    assert concrete.points == ArcPDF((0.0, 0.0), 10.0, 5.0, 0.0, 90.0, drawing_style).points


@pytest.mark.condition("ARC-P1")
def test_dxf_arc_drawing_reuses_pdf_sample_points(drawing_style: DrawingStyle) -> None:
    """ARC-P1: DXF arc export uses the neutral arc's PDF-sampled points."""
    arc = ArcDrawing((0.0, 0.0), 10.0, 5.0, 0.0, 90.0, drawing_style)
    group = DrawingComponentGroup("arc")
    group.add_component(arc)
    expected_points = arc.to_component(OutputFormat.PDF).points

    document = DXFDocument()
    document.add_group(group)
    payload = document.to_dxf_string()

    assert "\nLWPOLYLINE\n" in payload
    assert "\n8\narc\n" in payload
    assert f"\n90\n{len(expected_points)}\n" in payload
    assert "\n70\n0\n" in payload
    assert _dxf_polyline_vertices(payload) == expected_points


@pytest.mark.condition("CURVE-P1")
def test_quadratic_bezier_samples_follow_formula_and_control_bounds(
    drawing_style: DrawingStyle,
) -> None:
    """CURVE-P1: Quadratic Bezier samples are convex combinations of controls."""
    cases = [
        ((0.0, 0.0), (1.0, 1.0), (2.0, 0.0)),
        ((-4.0, 3.0), (7.0, 12.0), (10.0, -2.0)),
        ((5.5, -1.25), (5.5, 8.75), (5.5, 3.5)),
    ]

    for start, control, end in cases:
        bezier = QuadraticBezier(start, control, end, drawing_style)
        points = bezier.points
        sample_count = len(points) - 1
        min_x = min(start[0], control[0], end[0])
        max_x = max(start[0], control[0], end[0])
        min_y = min(start[1], control[1], end[1])
        max_y = max(start[1], control[1], end[1])

        assert points[0] == start
        assert points[-1] == end
        for index, point in enumerate(points):
            expected = _quadratic_point(start, control, end, index / sample_count)
            assert point == (
                pytest.approx(round(expected[0], PRECISION), abs=1e-9),
                pytest.approx(round(expected[1], PRECISION), abs=1e-9),
            )
            assert min_x <= point[0] <= max_x
            assert min_y <= point[1] <= max_y


@pytest.mark.condition("CUBIC-P1")
def test_cubic_bezier_samples_follow_formula_and_control_bounds(
    drawing_style: DrawingStyle,
) -> None:
    """CUBIC-P1: Cubic Bezier samples are convex combinations of controls."""
    cases = [
        ((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0)),
        ((-4.0, 3.0), (5.0, 12.0), (8.0, -6.0), (10.0, 2.0)),
        ((5.5, -1.25), (5.5, 8.75), (2.0, 4.0), (5.5, 3.5)),
    ]

    for start, control_1, control_2, end in cases:
        bezier = CubicBezier(start, control_1, control_2, end, drawing_style)
        points = bezier.points
        sample_count = len(points) - 1
        min_x = min(start[0], control_1[0], control_2[0], end[0])
        max_x = max(start[0], control_1[0], control_2[0], end[0])
        min_y = min(start[1], control_1[1], control_2[1], end[1])
        max_y = max(start[1], control_1[1], control_2[1], end[1])

        assert sample_count == 32
        assert points[0] == start
        assert points[-1] == end
        for index, point in enumerate(points):
            expected = _cubic_point(start, control_1, control_2, end, index / sample_count)
            assert point == (
                pytest.approx(round(expected[0], PRECISION), abs=1e-9),
                pytest.approx(round(expected[1], PRECISION), abs=1e-9),
            )
            assert min_x <= point[0] <= max_x
            assert min_y <= point[1] <= max_y


@pytest.mark.condition("CUBIC-P1")
def test_cubic_bezier_rejects_malformed_points(drawing_style: DrawingStyle) -> None:
    """CUBIC-P1: Cubic Bezier point validation rejects malformed coordinates."""
    with pytest.raises(ValueError, match="Point must contain two numeric values."):
        CubicBezier((0.0,), (1.0, 2.0), (3.0, 4.0), (5.0, 6.0), drawing_style)
    with pytest.raises(ValueError, match="Point must contain two numeric values."):
        CubicBezier((0.0, 1.0, 2.0), (1.0, 2.0), (3.0, 4.0), (5.0, 6.0), drawing_style)

    bezier = CubicBezier((0.0, 1.0), (2.0, 3.0), (4.0, 5.0), (6.0, 7.0), drawing_style)
    with pytest.raises(ValueError, match="Point must contain two numeric values."):
        bezier.control_point1 = (1.0,)
    with pytest.raises(ValueError, match="Point must contain two numeric values."):
        bezier.control_point2 = (1.0, 2.0, 3.0)


@pytest.mark.condition("CUBIC-P1")
def test_cubic_bezier_pdf_emits_exact_cubic_operator(drawing_style: DrawingStyle) -> None:
    """CUBIC-P1: CubicBezierPDF renders one open PDF cubic path command."""
    drawing_style.fill = "#ffffff"
    bezier = CubicBezierPDF((1.0, 2.0), (3.0, 7.0), (6.0, 11.0), (10.0, 5.0), drawing_style)

    content = bezier.generate_pdf()

    assert "1 2 m" in content
    assert "3 7 6 11 10 5 c" in content
    assert "\nh\n" not in content
    assert content.endswith("\nS\nQ")


@pytest.mark.condition("CUBIC-P1")
def test_cubic_drawing_materializes_pdf_component(drawing_style: DrawingStyle) -> None:
    """CUBIC-P1: Neutral cubic recipes materialize to CubicBezierPDF for PDF output."""
    bezier = CubicBezierDrawing((0.0, 0.0), (0.0, 4.0), (8.0, 4.0), (8.0, 0.0), drawing_style)

    concrete = bezier.to_component(OutputFormat.PDF)

    assert isinstance(concrete, CubicBezierPDF)
    assert (
        concrete.points
        == CubicBezierPDF(
            (0.0, 0.0),
            (0.0, 4.0),
            (8.0, 4.0),
            (8.0, 0.0),
            drawing_style,
        ).points
    )


@pytest.mark.condition("CUBIC-P1")
def test_dxf_cubic_bezier_reuses_pdf_sample_points(drawing_style: DrawingStyle) -> None:
    """CUBIC-P1: DXF cubic export uses the neutral cubic's PDF-sampled points."""
    bezier = CubicBezierDrawing((0.0, 0.0), (0.0, 4.0), (8.0, 4.0), (8.0, 0.0), drawing_style)
    group = DrawingComponentGroup("cubic")
    group.add_component(bezier)
    expected_points = bezier.to_component(OutputFormat.PDF).points

    document = DXFDocument()
    document.add_group(group)
    payload = document.to_dxf_string()

    assert "\nLWPOLYLINE\n" in payload
    assert "\n8\ncubic\n" in payload
    assert f"\n90\n{len(expected_points)}\n" in payload
    assert "\n70\n0\n" in payload
    assert _dxf_polyline_vertices(payload) == expected_points
