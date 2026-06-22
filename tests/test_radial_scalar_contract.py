"""Behavioral tests for radial scalar validation boundaries."""

from __future__ import annotations

from uuid import uuid4

import pytest

from InkGen.component import PolarCoordinateDrawingComponent, RegularPolygonDrawingComponent
from InkGen.drawing_components import CircleDrawing, DrawingComponentGroup, OutputFormat, RegularPolygonDrawing
from InkGen.dxf_generator import DXFDocument
from InkGen.pdf_generator import CirclePDF, RegularPolygonPDF
from InkGen.style import DrawingStyle
from InkGen.svg_generator import CircleSVG


def _style() -> DrawingStyle:
    """Return a unique drawing style for radial scalar tests."""
    return DrawingStyle(f"radial_scalar_contract_{uuid4().hex}", stroke="#000000", fill="none")


@pytest.mark.condition("RADIAL-SCALAR-P2")
def test_circle_radius_rejects_boolean_and_nonfinite_values() -> None:
    """RADIAL-SCALAR-P2: Circle radii must be finite positive non-booleans."""
    style = _style()

    for circle_type in (CirclePDF, CircleSVG):
        with pytest.raises(TypeError):
            circle_type((0.0, 0.0), True, style)  # type: ignore[arg-type]
        for value in [float("nan"), float("inf"), -float("inf"), 0.0, -1.0, object(), "bad"]:
            with pytest.raises(ValueError):
                circle_type((0.0, 0.0), value, style)  # type: ignore[arg-type]

    circle = CircleSVG((0.0, 0.0), 2.0, style)
    before = circle.parameters

    with pytest.raises(TypeError):
        circle.radius = False  # type: ignore[assignment]
    assert circle.parameters == before

    with pytest.raises(ValueError):
        circle.radius = float("nan")
    assert circle.parameters == before


@pytest.mark.condition("RADIAL-SCALAR-P2")
def test_polar_length_angle_reject_boolean_and_nonfinite_values() -> None:
    """RADIAL-SCALAR-P2: Polar length and angle reject invalid scalar values."""
    style = _style()

    for value in [float("nan"), float("inf"), -float("inf"), True, object(), "bad"]:
        with pytest.raises((TypeError, ValueError)):
            PolarCoordinateDrawingComponent((0.0, 0.0), value, 45.0, style)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            PolarCoordinateDrawingComponent((0.0, 0.0), 5.0, value, style)  # type: ignore[arg-type]

    polar = PolarCoordinateDrawingComponent((0.0, 0.0), 5.0, 45.0, style)
    before = polar.parameters

    for value in [float("nan"), float("inf"), -float("inf"), False, object(), "bad"]:
        with pytest.raises((TypeError, ValueError)):
            polar.length = value  # type: ignore[assignment]
        assert polar.parameters == before

        with pytest.raises((TypeError, ValueError)):
            polar.angle = value  # type: ignore[assignment]
        assert polar.parameters == before


@pytest.mark.condition("RADIAL-SCALAR-P2")
def test_regular_polygon_radius_corner_and_angle_reject_invalid_scalars() -> None:
    """RADIAL-SCALAR-P2: Regular polygon scalar boundaries reject invalid inputs."""
    style = _style()

    for value in [float("nan"), float("inf"), -float("inf"), True, object(), "bad"]:
        with pytest.raises((TypeError, ValueError)):
            RegularPolygonDrawingComponent((0.0, 0.0), 3, value, style)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            RegularPolygonDrawingComponent((0.0, 0.0), 3, 10.0, style, angle=value)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            RegularPolygonDrawingComponent((0.0, 0.0), 3, 10.0, style, corner_radius=value)  # type: ignore[arg-type]

    polygon = RegularPolygonDrawingComponent((0.0, 0.0), 3, 10.0, style, angle=15.0, corner_radius=2.0)
    before = polygon.parameters

    for value in [float("nan"), float("inf"), -float("inf"), False, object(), "bad"]:
        with pytest.raises((TypeError, ValueError)):
            polygon.radius = value  # type: ignore[assignment]
        assert polygon.parameters == before

        with pytest.raises((TypeError, ValueError)):
            polygon.angle = value  # type: ignore[assignment]
        assert polygon.parameters == before

        with pytest.raises((TypeError, ValueError)):
            polygon.corner_radius = value  # type: ignore[assignment]
        assert polygon.parameters == before


@pytest.mark.condition("RADIAL-SCALAR-P2")
def test_neutral_radial_drawings_consume_scalar_boundaries() -> None:
    """RADIAL-SCALAR-P2: Neutral radial drawings fail before renderer output."""
    style = _style()

    with pytest.raises(TypeError):
        CircleDrawing((0.0, 0.0), True, style).to_component(OutputFormat.PDF)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        RegularPolygonDrawing((0.0, 0.0), 3, 10.0, style, corner_radius=float("nan")).to_component(OutputFormat.PDF)

    group = DrawingComponentGroup("radial_scalar")
    group.add_component(RegularPolygonDrawing((0.0, 0.0), 3, 10.0, style, corner_radius=True))  # type: ignore[arg-type]
    document = DXFDocument()

    with pytest.raises(TypeError):
        document.add_group(group)


@pytest.mark.condition("RADIAL-SCALAR-P2")
def test_valid_radial_scalars_remain_supported() -> None:
    """RADIAL-SCALAR-P2: Valid finite radial scalars preserve behavior."""
    style = _style()

    circle = CircleSVG((1.0, 2.0), 3.5, style)
    assert circle.radius == 3.5
    circle.radius = 4.25
    assert circle.radius == 4.25
    circle.radius = 0.5
    assert circle.radius == 0.5
    before = circle.parameters

    with pytest.raises(ValueError):
        circle.radius = -1.0
    assert circle.parameters == before

    polygon = RegularPolygonPDF((10.0, 10.0), 5, 8.0, style, angle=-30.0, corner_radius=2.5)
    assert polygon.sides == 5
    assert polygon.radius == pytest.approx(8.0, abs=1e-3)
    assert polygon.angle == pytest.approx(-30.0, abs=2e-3)
    assert polygon.corner_radius == 2.5
