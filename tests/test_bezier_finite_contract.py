"""Behavioral tests for finite Bezier point boundaries."""

from __future__ import annotations

from uuid import uuid4

import pytest

from InkGen.component import CubicBezier, QuadraticBezier
from InkGen.drawing_components import CubicBezierDrawing, DrawingComponentGroup, QuadraticBezierDrawing
from InkGen.dxf_generator import DXFDocument
from InkGen.pdf_generator import CubicBezierPDF, QuadraticBezierPDF
from InkGen.style import DrawingStyle


def _style() -> DrawingStyle:
    """Return a unique drawing style for Bezier finite-boundary tests."""
    return DrawingStyle(f"bezier_finite_contract_{uuid4().hex}", stroke="#000000", fill="none")


@pytest.mark.condition("BEZIER-FINITE-P2")
def test_quadratic_bezier_preserves_valid_finite_points_and_setters() -> None:
    """BEZIER-FINITE-P2: Finite quadratic points preserve public geometry."""
    bezier = QuadraticBezier((1.25, -2.5), (3.5, 4.25), (7.0, -1.0), _style())

    assert bezier.start_point == (1.25, -2.5)
    assert bezier.control_point == (3.5, 4.25)
    assert bezier.end_point == (7.0, -1.0)
    assert len(bezier.points) == 33

    bezier.start_point = (-4.0, 5.0)
    bezier.control_point = (6.0, 2.0)
    bezier.end_point = (10.0, -3.0)

    assert bezier.start_point == (-4.0, 5.0)
    assert bezier.control_point == (6.0, 2.0)
    assert bezier.end_point == (10.0, -3.0)


@pytest.mark.condition("BEZIER-FINITE-P2")
def test_cubic_bezier_preserves_valid_finite_points_and_setters() -> None:
    """BEZIER-FINITE-P2: Finite cubic points preserve public geometry."""
    bezier = CubicBezier((1.25, -2.5), (3.5, 4.25), (6.5, 8.0), (7.0, -1.0), _style())

    assert bezier.start_point == (1.25, -2.5)
    assert bezier.control_point1 == (3.5, 4.25)
    assert bezier.control_point2 == (6.5, 8.0)
    assert bezier.end_point == (7.0, -1.0)
    assert len(bezier.points) == 33

    bezier.start_point = (-4.0, 5.0)
    bezier.control_point1 = (6.0, 2.0)
    bezier.control_point2 = (8.0, 9.0)
    bezier.end_point = (10.0, -3.0)

    assert bezier.start_point == (-4.0, 5.0)
    assert bezier.control_point1 == (6.0, 2.0)
    assert bezier.control_point2 == (8.0, 9.0)
    assert bezier.end_point == (10.0, -3.0)


@pytest.mark.condition("BEZIER-FINITE-P2")
def test_quadratic_bezier_rejects_invalid_constructor_and_setter_points() -> None:
    """BEZIER-FINITE-P2: Invalid quadratic points fail without mutation."""
    style = _style()
    invalid_values = [float("nan"), float("inf"), -float("inf"), True, object(), "bad"]

    for value in invalid_values:
        with pytest.raises((TypeError, ValueError)):
            QuadraticBezier((value, 0.0), (1.0, 1.0), (2.0, 0.0), style)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            QuadraticBezier((0.0, 0.0), (value, 1.0), (2.0, 0.0), style)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            QuadraticBezier((0.0, 0.0), (1.0, 1.0), (2.0, value), style)  # type: ignore[arg-type]

    for point in [(0.0,), (0.0, 1.0, 2.0)]:
        with pytest.raises(ValueError, match="Point must contain two numeric values."):
            QuadraticBezier(point, (1.0, 1.0), (2.0, 0.0), style)  # type: ignore[arg-type]

    bezier = QuadraticBezier((0.0, 0.0), (1.0, 1.0), (2.0, 0.0), style)
    before = bezier.parameters

    for value in invalid_values:
        with pytest.raises((TypeError, ValueError)):
            bezier.start_point = (value, 0.0)  # type: ignore[assignment]
        assert bezier.parameters == before

        with pytest.raises((TypeError, ValueError)):
            bezier.control_point = (1.0, value)  # type: ignore[assignment]
        assert bezier.parameters == before

        with pytest.raises((TypeError, ValueError)):
            bezier.end_point = (value, 0.0)  # type: ignore[assignment]
        assert bezier.parameters == before

    with pytest.raises(ValueError, match="Point must contain two numeric values."):
        bezier.control_point = (1.0,)  # type: ignore[assignment]
    assert bezier.parameters == before

    with pytest.raises(ValueError, match="Point must contain two numeric values."):
        bezier.end_point = (1.0, 2.0, 3.0)  # type: ignore[assignment]
    assert bezier.parameters == before


@pytest.mark.condition("BEZIER-FINITE-P2")
def test_cubic_bezier_rejects_invalid_constructor_and_setter_points() -> None:
    """BEZIER-FINITE-P2: Invalid cubic points fail without mutation."""
    style = _style()
    invalid_values = [float("nan"), float("inf"), -float("inf"), False, object(), "bad"]

    for value in invalid_values:
        with pytest.raises((TypeError, ValueError)):
            CubicBezier((value, 0.0), (1.0, 1.0), (2.0, 2.0), (3.0, 0.0), style)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            CubicBezier((0.0, 0.0), (value, 1.0), (2.0, 2.0), (3.0, 0.0), style)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            CubicBezier((0.0, 0.0), (1.0, 1.0), (2.0, value), (3.0, 0.0), style)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            CubicBezier((0.0, 0.0), (1.0, 1.0), (2.0, 2.0), (3.0, value), style)  # type: ignore[arg-type]

    for point in [(0.0,), (0.0, 1.0, 2.0)]:
        with pytest.raises(ValueError, match="Point must contain two numeric values."):
            CubicBezier(point, (1.0, 1.0), (2.0, 2.0), (3.0, 0.0), style)  # type: ignore[arg-type]

    bezier = CubicBezier((0.0, 0.0), (1.0, 1.0), (2.0, 2.0), (3.0, 0.0), style)
    before = bezier.parameters

    for value in invalid_values:
        with pytest.raises((TypeError, ValueError)):
            bezier.start_point = (value, 0.0)  # type: ignore[assignment]
        assert bezier.parameters == before

        with pytest.raises((TypeError, ValueError)):
            bezier.control_point1 = (1.0, value)  # type: ignore[assignment]
        assert bezier.parameters == before

        with pytest.raises((TypeError, ValueError)):
            bezier.control_point2 = (value, 2.0)  # type: ignore[assignment]
        assert bezier.parameters == before

        with pytest.raises((TypeError, ValueError)):
            bezier.end_point = (3.0, value)  # type: ignore[assignment]
        assert bezier.parameters == before

    with pytest.raises(ValueError, match="Point must contain two numeric values."):
        bezier.control_point1 = (1.0,)  # type: ignore[assignment]
    assert bezier.parameters == before

    with pytest.raises(ValueError, match="Point must contain two numeric values."):
        bezier.control_point2 = (1.0, 2.0, 3.0)  # type: ignore[assignment]
    assert bezier.parameters == before


@pytest.mark.condition("BEZIER-FINITE-P2")
def test_dependent_pdf_and_dxf_paths_reject_nonfinite_bezier_geometry() -> None:
    """BEZIER-FINITE-P2: PDF and neutral-DXF Bezier paths consume finite boundaries."""
    style = _style()

    with pytest.raises(ValueError):
        QuadraticBezierPDF((0.0, 0.0), (1.0, float("nan")), (2.0, 0.0), style)
    with pytest.raises(ValueError):
        CubicBezierPDF((0.0, 0.0), (1.0, 1.0), (float("inf"), 2.0), (3.0, 0.0), style)

    group = DrawingComponentGroup("bezier_finite")
    group.add_component(QuadraticBezierDrawing((0.0, 0.0), (1.0, float("nan")), (2.0, 0.0), style))
    group.add_component(CubicBezierDrawing((0.0, 0.0), (1.0, 1.0), (float("inf"), 2.0), (3.0, 0.0), style))
    document = DXFDocument()

    with pytest.raises(ValueError):
        document.add_group(group)
