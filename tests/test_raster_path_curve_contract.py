"""RASTER-PATH-CURVE-P6 conditions for sampled Bezier path commands."""

from __future__ import annotations

from uuid import uuid4

import pytest

import InkGen.raster_renderer as raster_renderer
from InkGen.baird import BairdParams
from InkGen.boundary import Canvas
from InkGen.component import CubicBezier, PathCommand, QuadraticBezier
from InkGen.drawing_components import DrawingComponentGroup, PathDrawing
from InkGen.raster_renderer import render_and_degrade_drawing_group, render_drawing_group
from InkGen.style import DrawingStyle


def _style() -> DrawingStyle:
    return DrawingStyle(
        f"raster_path_curve_{uuid4().hex}",
        stroke="#123456",
        fill="none",
        stroke_width=0.08,
    )


def _extend_without_repeated_start(
    target: list[tuple[float, float]],
    sampled: list[tuple[float, float]],
) -> None:
    target.extend(sampled[1:])


@pytest.mark.condition("RASTER-PATH-CURVE-P6")
def test_smooth_control_reflection_is_exact_in_both_axes() -> None:
    """RASTER-PATH-CURVE-P6: Reflection applies R(K, P) = 2P - K per axis."""
    assert raster_renderer._reflect_path_control((2.0, 3.0), (5.0, 7.0)) == (8.0, 11.0)


@pytest.mark.condition("RASTER-PATH-CURVE-P6")
def test_bezier_path_commands_use_canonical_samples_and_smooth_reflection() -> None:
    """RASTER-PATH-CURVE-P6: C/S/Q/T reuse canonical samples and controls."""
    style = _style()
    path = PathDrawing(
        style,
        [
            PathCommand("M", [(0.0, 0.0)]),
            PathCommand(
                "C",
                [
                    (1.0, 0.0),
                    (2.0, 1.0),
                    (3.0, 1.0),
                    (4.0, 1.0),
                    (5.0, 0.0),
                    (6.0, 0.0),
                ],
            ),
            PathCommand("S", [(7.0, -1.0), (8.0, 0.0), (9.0, 1.0), (10.0, 0.0)]),
            PathCommand("Q", [(11.0, 1.0), (12.0, 0.0), (13.0, -1.0), (14.0, 0.0)]),
            PathCommand("T", [(16.0, 0.0), (18.0, 0.0)]),
        ],
    )
    expected = CubicBezier((0.0, 0.0), (1.0, 0.0), (2.0, 1.0), (3.0, 1.0), style).points
    for segment in [
        CubicBezier((3.0, 1.0), (4.0, 1.0), (5.0, 0.0), (6.0, 0.0), style).points,
        CubicBezier((6.0, 0.0), (7.0, 0.0), (7.0, -1.0), (8.0, 0.0), style).points,
        CubicBezier((8.0, 0.0), (9.0, 1.0), (9.0, 1.0), (10.0, 0.0), style).points,
        QuadraticBezier((10.0, 0.0), (11.0, 1.0), (12.0, 0.0), style).points,
        QuadraticBezier((12.0, 0.0), (13.0, -1.0), (14.0, 0.0), style).points,
        QuadraticBezier((14.0, 0.0), (15.0, 1.0), (16.0, 0.0), style).points,
        QuadraticBezier((16.0, 0.0), (17.0, -1.0), (18.0, 0.0), style).points,
    ]:
        _extend_without_repeated_start(expected, segment)

    assert raster_renderer._sampled_path_subpaths(path) == [expected]


@pytest.mark.condition("RASTER-PATH-CURVE-P6")
def test_smooth_controls_reset_after_linear_commands() -> None:
    """RASTER-PATH-CURVE-P6: Linear commands reset S/T reflection state."""
    style = _style()
    path = PathDrawing(
        style,
        [
            PathCommand("M", [(0.0, 0.0)]),
            PathCommand("C", [(1.0, 1.0), (2.0, 1.0), (3.0, 0.0)]),
            PathCommand("L", [(4.0, 0.0)]),
            PathCommand("S", [(5.0, 1.0), (6.0, 0.0)]),
            PathCommand("Q", [(7.0, 1.0), (8.0, 0.0)]),
            PathCommand("L", [(9.0, 0.0)]),
            PathCommand("T", [(10.0, 0.0)]),
        ],
    )
    expected = CubicBezier((0.0, 0.0), (1.0, 1.0), (2.0, 1.0), (3.0, 0.0), style).points
    expected.append((4.0, 0.0))
    for segment in [
        CubicBezier((4.0, 0.0), (4.0, 0.0), (5.0, 1.0), (6.0, 0.0), style).points,
        QuadraticBezier((6.0, 0.0), (7.0, 1.0), (8.0, 0.0), style).points,
    ]:
        _extend_without_repeated_start(expected, segment)
    expected.append((9.0, 0.0))
    _extend_without_repeated_start(
        expected,
        QuadraticBezier((9.0, 0.0), (9.0, 0.0), (10.0, 0.0), style).points,
    )

    assert raster_renderer._sampled_path_subpaths(path) == [expected]


@pytest.mark.condition("RASTER-PATH-CURVE-P6")
def test_curve_families_and_new_subpaths_reset_other_smooth_state() -> None:
    """RASTER-PATH-CURVE-P6: Curve-family and subpath changes reset controls."""
    style = _style()
    path = PathDrawing(
        style,
        [
            PathCommand("M", [(0.0, 0.0)]),
            PathCommand("C", [(1.0, 1.0), (2.0, 1.0), (3.0, 0.0)]),
            PathCommand("Q", [(4.0, 1.0), (5.0, 0.0)]),
            PathCommand("S", [(6.0, 1.0), (7.0, 0.0)]),
            PathCommand("C", [(8.0, 1.0), (9.0, 1.0), (10.0, 0.0)]),
            PathCommand("T", [(11.0, 0.0)]),
            PathCommand("M", [(20.0, 0.0)]),
            PathCommand("S", [(21.0, 1.0), (22.0, 0.0)]),
            PathCommand("Z"),
        ],
    )
    first = CubicBezier((0.0, 0.0), (1.0, 1.0), (2.0, 1.0), (3.0, 0.0), style).points
    for segment in [
        QuadraticBezier((3.0, 0.0), (4.0, 1.0), (5.0, 0.0), style).points,
        CubicBezier((5.0, 0.0), (5.0, 0.0), (6.0, 1.0), (7.0, 0.0), style).points,
        CubicBezier((7.0, 0.0), (8.0, 1.0), (9.0, 1.0), (10.0, 0.0), style).points,
        QuadraticBezier((10.0, 0.0), (10.0, 0.0), (11.0, 0.0), style).points,
    ]:
        _extend_without_repeated_start(first, segment)
    second = CubicBezier((20.0, 0.0), (20.0, 0.0), (21.0, 1.0), (22.0, 0.0), style).points
    second.append((20.0, 0.0))

    assert raster_renderer._sampled_path_subpaths(path) == [first, second]


@pytest.mark.condition("RASTER-PATH-CURVE-P6")
def test_empty_grouped_bezier_commands_are_transparent_noops() -> None:
    """RASTER-PATH-CURVE-P6: Empty C/S/Q groups do not invent geometry."""
    path = PathDrawing(
        _style(),
        [
            PathCommand("M", [(1.0, 1.0)]),
            PathCommand("C"),
            PathCommand("S"),
            PathCommand("Q"),
            PathCommand("L", [(2.0, 2.0)]),
        ],
    )

    assert raster_renderer._sampled_path_subpaths(path) == [[(1.0, 1.0), (2.0, 2.0)]]


@pytest.mark.condition("RASTER-PATH-CURVE-P6")
@pytest.mark.parametrize(
    ("command", "message"),
    [
        (PathCommand("C", [(1.0, 1.0), (2.0, 2.0)]), "C requires points in groups of three"),
        (PathCommand("S", [(1.0, 1.0)]), "S requires points in groups of two"),
        (PathCommand("Q", [(1.0, 1.0)]), "Q requires points in groups of two"),
        (PathCommand("T"), "T requires an endpoint"),
    ],
)
def test_invalid_or_unsupported_curve_commands_fail_before_surface_allocation(
    monkeypatch: pytest.MonkeyPatch,
    command: PathCommand,
    message: str,
) -> None:
    """RASTER-PATH-CURVE-P6: Invalid curves fail before pixel allocation."""
    path = PathDrawing(_style(), [PathCommand("M", [(0.0, 0.0)]), command])
    monkeypatch.setattr(raster_renderer.Image, "new", lambda *args, **kwargs: pytest.fail("surface allocated"))

    with pytest.raises(ValueError, match=message):
        render_drawing_group(DrawingComponentGroup("invalid-curve", [path]), Canvas(2, 2, "in"), dpi=20)


@pytest.mark.condition("RASTER-PATH-CURVE-P6")
def test_bezier_path_renders_through_public_scan_path() -> None:
    """RASTER-PATH-CURVE-P6: Sampled paths reach clean and Baird assets."""
    path = PathDrawing(
        _style(),
        [
            PathCommand("M", [(0.5, 1.5)]),
            PathCommand("Q", [(2.0, 0.25), (3.5, 1.5)]),
            PathCommand("C", [(3.0, 2.5), (1.0, 2.5), (0.5, 1.5)]),
        ],
    )

    result = render_and_degrade_drawing_group(
        DrawingComponentGroup("bezier-path", [path]),
        Canvas(4, 3, "in"),
        BairdParams.clean(),
        seed=17,
        background_rgb=(255, 255, 255),
        dpi=20,
        render_supersample=2,
    )

    assert result.clean.component_count == 1
    with result.clean.asset.image() as clean:
        assert clean.getbbox() is not None
    with result.degraded.asset.image() as degraded:
        assert degraded.getbbox() == (0, 0, 80, 60)
