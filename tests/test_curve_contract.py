"""Tests for curve renderer proof obligations."""

from __future__ import annotations

import pytest

from InkGen.component import PRECISION, QuadraticBezier
from InkGen.style import DrawingStyle


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


@pytest.fixture
def drawing_style() -> DrawingStyle:
    """Return a drawing style for curve contract tests."""
    return DrawingStyle(name="curve_contract", stroke="#000000", stroke_width=0.2, fill="none")


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
