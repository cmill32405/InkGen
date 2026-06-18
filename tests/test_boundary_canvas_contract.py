"""Tests for boundary and canvas proof obligations."""

from __future__ import annotations

from uuid import uuid4

import pytest

from InkGen.boundary import Boundary, Canvas
from InkGen.component import ComponentGroup, WidthHeightDrawingComponent
from InkGen.document import Layer
from InkGen.errors import ComponentGroupOffCanvas, IllegalArgumentError, InvalidConvexHull
from InkGen.style import DrawingStyle


def _boundary() -> Boundary:
    """Return a square inner boundary for contract tests."""
    return Boundary([(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)])


def _style() -> DrawingStyle:
    """Return a drawing style with a test-unique name."""
    return DrawingStyle(name=f"boundary_canvas_contract_{uuid4().hex}", stroke="#000000", fill="none")


@pytest.mark.condition("BOUNDARY-CANVAS-P1")
def test_canvas_rejects_bool_nonpositive_and_nonfinite_dimensions() -> None:
    """BOUNDARY-CANVAS-P1: Canvas dimensions must be positive finite numbers."""
    for width, height in [
        (True, 10.0),
        (10.0, False),
        (0.0, 10.0),
        (-1.0, 10.0),
        (10.0, 0.0),
        (10.0, -1.0),
        (float("nan"), 10.0),
        (10.0, float("inf")),
    ]:
        with pytest.raises((TypeError, IllegalArgumentError)):
            Canvas(width, height, "mm")

    canvas = Canvas(10, 20.5, "millimeters")
    small_canvas = Canvas(0.5, 0.25, "mm")

    assert canvas.parameters == {"Canvas": {"width": 10.0, "height": 20.5, "units": "mm"}}
    assert small_canvas.parameters == {"Canvas": {"width": 0.5, "height": 0.25, "units": "mm"}}


@pytest.mark.condition("BOUNDARY-CANVAS-P1")
def test_canvas_units_fail_at_public_boundary() -> None:
    """BOUNDARY-CANVAS-P1: Canvas units must be supported string aliases."""
    for units in [None, 1, True]:
        with pytest.raises(TypeError):
            Canvas(10.0, 10.0, units)  # type: ignore[arg-type]

    with pytest.raises(IllegalArgumentError):
        Canvas(10.0, 10.0, "px")

    assert Canvas(10.0, 10.0, "INCHES").units == "in"


@pytest.mark.condition("BOUNDARY-CANVAS-P1")
def test_boundary_rejects_malformed_degenerate_and_nonfinite_hulls() -> None:
    """BOUNDARY-CANVAS-P1: Boundary hulls must be finite convex polygons."""
    triangle = Boundary([(0.0, 0.0), (2.0, 0.0), (0.0, 2.0)])
    closed_square = Boundary([(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0), (0.0, 0.0)])
    reverse_order_triangle = Boundary([(2.0, 0.0), (0.0, 0.0), (0.0, 2.0)])

    assert triangle.boundary_points == [(0.0, 0.0), (2.0, 0.0), (0.0, 2.0)]
    assert closed_square.boundary_points == [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)]
    assert reverse_order_triangle.boundary_points == [(2.0, 0.0), (0.0, 0.0), (0.0, 2.0)]

    with pytest.raises(InvalidConvexHull):
        Boundary(None)  # type: ignore[arg-type]

    invalid_hulls = [
        [],
        [(0.0, 0.0), (1.0, 1.0)],
        [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0, 1.0)],
        [(0.0, 0.0), (1.0, 0.0), object()],
        [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0)],
        [(0.0, 0.0), (1.0, 0.0), (1.0, float("nan")), (0.0, 1.0)],
        [(0.0, 0.0), (1.0, 0.0), ("1.0", 1.0), (0.0, 1.0)],
        [(0.0, 0.0), (1.0, 0.0), (True, 1.0), (0.0, 1.0)],
    ]

    for hull in invalid_hulls:
        with pytest.raises(InvalidConvexHull):
            Boundary(hull)  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        Boundary([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)], outer_boundary="false")  # type: ignore[arg-type]


@pytest.mark.condition("BOUNDARY-CANVAS-P1")
def test_boundary_check_validates_candidate_hulls_and_strict_flag() -> None:
    """BOUNDARY-CANVAS-P1: Boundary checks reject malformed candidate hulls explicitly."""
    boundary = _boundary()

    assert not boundary.boundary_check([])
    assert boundary.boundary_check([(1.0, 1.0), (9.0, 1.0), (9.0, 9.0), (1.0, 9.0)])

    for points in [
        [(1.0, 1.0)],
        [(1.0, 1.0), (2.0, 2.0)],
        [(1.0, 1.0), (2.0, 1.0), (2.0, 2.0, 3.0)],
        [(1.0, 1.0), (2.0, 1.0), (float("inf"), 2.0)],
        [(1.0, 1.0), (2.0, 1.0), (False, 2.0)],
    ]:
        with pytest.raises(InvalidConvexHull):
            boundary.boundary_check(points)  # type: ignore[arg-type]

    with pytest.raises(InvalidConvexHull):
        boundary.boundary_check(None)  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        boundary.boundary_check([(1.0, 1.0), (2.0, 1.0), (1.0, 2.0)], strict=1)  # type: ignore[arg-type]


@pytest.mark.condition("BOUNDARY-CANVAS-P1")
def test_boundary_canvas_contract_is_live_in_layer_off_canvas_check() -> None:
    """BOUNDARY-CANVAS-P1: Layer containment consumes the hardened canvas boundary."""
    layer = Layer("base", Canvas(20.0, 20.0, "mm"))
    group = ComponentGroup("inside")
    group.add_component(WidthHeightDrawingComponent((2.0, 2.0), 4.0, 4.0, _style()))
    layer.add_component_group(group)

    off_canvas = ComponentGroup("outside")
    off_canvas.add_component(WidthHeightDrawingComponent((18.0, 18.0), 4.0, 4.0, _style()))

    with pytest.raises(ComponentGroupOffCanvas):
        layer.add_component_group(off_canvas)
