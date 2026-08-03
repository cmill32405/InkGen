"""RASTER-PATH-ARC-P7 conditions for SVG endpoint-arc path commands."""

from __future__ import annotations

import math
from uuid import uuid4

import pytest

import InkGen.raster_renderer as raster_renderer
from InkGen.baird import BairdParams
from InkGen.boundary import Canvas
from InkGen.component import Arc, CubicBezier, PathCommand, QuadraticBezier
from InkGen.drawing_components import DrawingComponentGroup, PathDrawing
from InkGen.raster_renderer import render_and_degrade_drawing_group, render_drawing_group
from InkGen.style import DrawingStyle


def _style() -> DrawingStyle:
    return DrawingStyle(
        f"raster_path_arc_{uuid4().hex}",
        stroke="#123456",
        fill="none",
        stroke_width=0.08,
    )


def _arc_command(
    points: list[tuple[float, float]],
    *,
    radii: tuple[float, float] = (1.0, 1.0),
    rotation: float = 0.0,
    large_arc: int | bool = 0,
    sweep: int | bool = 1,
) -> PathCommand:
    command = PathCommand("A", points)
    command.flags = {
        "radii": radii,
        "rotation": rotation,
        "large_arc": large_arc,
        "sweep": sweep,
    }
    return command


@pytest.mark.condition("RASTER-PATH-ARC-P7")
@pytest.mark.parametrize(
    ("large_arc", "sweep", "expected_midpoint"),
    [
        (0, 1, (0.7071, 0.7071)),
        (0, 0, (0.2929, 0.2929)),
        (1, 1, (1.7071, 1.7071)),
        (1, 0, (-0.7071, -0.7071)),
    ],
)
def test_endpoint_arc_flags_select_all_four_unit_circle_solutions(
    large_arc: int,
    sweep: int,
    expected_midpoint: tuple[float, float],
) -> None:
    """RASTER-PATH-ARC-P7: Arc flags select the proven center and sweep."""
    path = PathDrawing(
        _style(),
        [PathCommand("M", [(1.0, 0.0)]), _arc_command([(0.0, 1.0)], large_arc=large_arc, sweep=sweep)],
    )

    sampled = raster_renderer._sampled_path_subpaths(path)[0]

    assert len(sampled) == 33
    assert sampled[0] == (1.0, 0.0)
    assert sampled[16] == pytest.approx(expected_midpoint, abs=1e-4)
    assert sampled[-1] == (0.0, 1.0)


@pytest.mark.condition("RASTER-PATH-ARC-P7")
@pytest.mark.parametrize(
    ("large_arc", "sweep", "expected_midpoint"),
    [
        (0, 0, (0.9, 0.241)),
        (0, 1, (0.966, 0.259)),
        (1, 0, (-0.966, -0.259)),
        (1, 1, (2.832, 0.759)),
    ],
)
def test_small_endpoint_arc_spans_normalize_signed_delta(
    large_arc: int,
    sweep: int,
    expected_midpoint: tuple[float, float],
) -> None:
    """RASTER-PATH-ARC-P7: Sub-radian spans normalize in both directions."""
    path = PathDrawing(
        _style(),
        [
            PathCommand("M", [(1.0, 0.0)]),
            _arc_command([(0.866, 0.5)], large_arc=large_arc, sweep=sweep),
        ],
    )

    sampled = raster_renderer._sampled_path_subpaths(path)[0]

    assert sampled[16] == expected_midpoint


@pytest.mark.condition("RASTER-PATH-ARC-P7")
@pytest.mark.parametrize(("large_arc", "sweep"), [(large_arc, sweep) for large_arc in (0, 1) for sweep in (0, 1)])
def test_subnormal_chords_preserve_small_or_large_span(large_arc: int, sweep: int) -> None:
    """RASTER-PATH-ARC-P7: Chord-derived spans do not collapse at tiny angles."""
    endpoint = (1.0, 1.0)
    path = PathDrawing(
        _style(),
        [
            PathCommand("M", [(0.0, 0.0)]),
            _arc_command([endpoint], radii=(1e153, 1e153), large_arc=large_arc, sweep=sweep),
        ],
    )

    sampled = raster_renderer._sampled_path_subpaths(path)[0]

    if large_arc:
        assert len(sampled) == 33
        assert math.hypot(*sampled[16]) == pytest.approx(2e153)
    else:
        assert sampled == [(0.0, 0.0), endpoint]
    assert sampled[-1] == endpoint


@pytest.mark.condition("RASTER-PATH-ARC-P7")
@pytest.mark.parametrize(
    ("start_angle", "end_angle", "rotation"),
    [(15.0, 135.0, 25.0), (210.0, -60.0, -37.5)],
)
def test_rotated_endpoint_arcs_reuse_canonical_arc_samples(
    start_angle: float,
    end_angle: float,
    rotation: float,
) -> None:
    """RASTER-PATH-ARC-P7: Derived center arcs use the canonical sampler."""
    style = _style()
    canonical = Arc((4.0, 5.0), 3.0, 1.5, start_angle, end_angle, style, rotation).points
    delta = end_angle - start_angle
    path = PathDrawing(
        style,
        [
            PathCommand("M", [canonical[0]]),
            _arc_command(
                [(-99.0, -99.0), canonical[-1]],
                radii=(-3.0, -1.5),
                rotation=rotation,
                large_arc=abs(delta) > 180.0,
                sweep=delta >= 0.0,
            ),
        ],
    )

    sampled = raster_renderer._sampled_path_subpaths(path)[0]

    assert len(sampled) == len(canonical)
    assert sampled[0] == canonical[0]
    assert sampled[-1] == canonical[-1]
    for actual, expected in zip(sampled[1:-1], canonical[1:-1], strict=True):
        assert actual == pytest.approx(expected, abs=0.002)


@pytest.mark.condition("RASTER-PATH-ARC-P7")
def test_omitted_nondegenerate_arc_fields_use_svg_defaults() -> None:
    """RASTER-PATH-ARC-P7: Omitted rotation and flags default to zero."""
    style = _style()
    canonical = Arc((4.0, 5.0), 3.0, 1.5, 135.0, 15.0, style).points
    command = PathCommand("A", [canonical[-1]])
    command.flags = {"radii": (3.0, 1.5)}
    path = PathDrawing(style, [PathCommand("M", [canonical[0]]), command])

    sampled = raster_renderer._sampled_path_subpaths(path)[0]

    for actual, expected in zip(sampled, canonical, strict=True):
        assert actual == pytest.approx(expected, abs=0.002)


@pytest.mark.condition("RASTER-PATH-ARC-P7")
def test_integer_subclass_flags_use_value_equality_for_center_choice() -> None:
    """RASTER-PATH-ARC-P7: Accepted integer flags retain value semantics."""

    class Flag(int):
        pass

    path = PathDrawing(
        _style(),
        [
            PathCommand("M", [(1.0, 0.0)]),
            _arc_command([(0.0, 1.0)], large_arc=Flag(0), sweep=Flag(0)),
        ],
    )

    sampled = raster_renderer._sampled_path_subpaths(path)[0]

    assert sampled[16] == (0.293, 0.293)


@pytest.mark.condition("RASTER-PATH-ARC-P7")
@pytest.mark.parametrize(
    ("radii", "expected_midpoint"),
    [((1.0, 2.0), (3.0, -2.0)), ((2.0, 1.0), (6.0, 1.0))],
)
def test_unequal_undersized_radii_use_both_axes_in_correction(
    radii: tuple[float, float],
    expected_midpoint: tuple[float, float],
) -> None:
    """RASTER-PATH-ARC-P7: Radius correction scales both unequal axes."""
    path = PathDrawing(
        _style(),
        [PathCommand("M", [(0.0, 0.0)]), _arc_command([(4.0, 4.0)], radii=radii)],
    )

    sampled = raster_renderer._sampled_path_subpaths(path)[0]

    assert sampled[16] == expected_midpoint


@pytest.mark.condition("RASTER-PATH-ARC-P7")
def test_radius_correction_clamps_binary_rounding_above_one() -> None:
    """RASTER-PATH-ARC-P7: Corrected lambda remains in the asin domain."""
    transformed = (8.00027869794814e260, 4.9270965480091934e269)
    start = transformed
    end = (-transformed[0], -transformed[1])
    path = PathDrawing(
        _style(),
        [
            PathCommand("M", [start]),
            _arc_command(
                [end],
                radii=(2.4288052087747965e84, 2.936758915281059e92),
                sweep=1,
            ),
        ],
    )

    sampled = raster_renderer._sampled_path_subpaths(path)[0]

    assert len(sampled) == 33
    assert sampled[0] == start
    assert sampled[-1] == end


@pytest.mark.condition("RASTER-PATH-ARC-P7")
def test_huge_rotation_is_reduced_before_trigonometry() -> None:
    """RASTER-PATH-ARC-P7: Periodic reduction avoids huge-angle precision loss."""
    huge_rotation = 1e20
    paths = []
    for rotation in (huge_rotation, huge_rotation % 360.0):
        paths.append(
            PathDrawing(
                _style(),
                [
                    PathCommand("M", [(1.0, 0.0)]),
                    _arc_command([(0.0, 1.0)], radii=(2.0, 1.0), rotation=rotation),
                ],
            )
        )

    assert raster_renderer._sampled_path_subpaths(paths[0]) == raster_renderer._sampled_path_subpaths(paths[1])


@pytest.mark.condition("RASTER-PATH-ARC-P7")
def test_endpoint_replacement_wraps_the_canonical_sampler(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASTER-PATH-ARC-P7: Reconstructed samples retain exact path endpoints."""

    class _FakeArc:
        def __init__(self, *args: object, **kwargs: object) -> None:
            self.points = [(-9.0, -8.0), (7.0, 6.0)]

    monkeypatch.setattr(raster_renderer, "SampledArc", _FakeArc)
    start = (1.0, 2.0)
    end = (3.0, 4.0)
    command = _arc_command([end], radii=(3.0, 2.0), rotation=15.0)

    assert raster_renderer._sampled_svg_endpoint_arc(start, end, command, _style()) == [start, end]


@pytest.mark.condition("RASTER-PATH-ARC-P7")
def test_undersized_radii_are_scaled_to_reach_the_endpoint() -> None:
    """RASTER-PATH-ARC-P7: SVG radius correction preserves exact endpoints."""
    path = PathDrawing(
        _style(),
        [PathCommand("M", [(0.0, 0.0)]), _arc_command([(4.0, 0.0)], radii=(1.0, 1.0))],
    )

    sampled = raster_renderer._sampled_path_subpaths(path)[0]

    assert len(sampled) == 33
    assert sampled[0] == (0.0, 0.0)
    assert sampled[16] == pytest.approx((2.0, -2.0), abs=1e-4)
    assert sampled[-1] == (4.0, 0.0)


@pytest.mark.condition("RASTER-PATH-ARC-P7")
def test_degenerate_endpoint_arcs_follow_svg_line_and_noop_rules() -> None:
    """RASTER-PATH-ARC-P7: Zero radii make a line and equal endpoints a no-op."""
    default_arc = PathCommand("A", [(2.0, 1.0)])
    equal_arc = _arc_command([(2.0, 1.0)], radii=(3.0, 2.0), rotation=45.0, large_arc=1, sweep=0)
    path = PathDrawing(
        _style(),
        [PathCommand("M", [(1.0, 1.0)]), default_arc, equal_arc, PathCommand("L", [(3.0, 1.0)])],
    )

    assert raster_renderer._sampled_path_subpaths(path) == [[(1.0, 1.0), (2.0, 1.0), (3.0, 1.0)]]

    vertical_zero = PathDrawing(
        _style(),
        [PathCommand("M", [(1.0, 1.0)]), _arc_command([(2.0, 1.0)], radii=(1.0, 0.0))],
    )
    assert raster_renderer._sampled_path_subpaths(vertical_zero) == [[(1.0, 1.0), (2.0, 1.0)]]


@pytest.mark.condition("RASTER-PATH-ARC-P7")
def test_arc_resets_both_smooth_control_families() -> None:
    """RASTER-PATH-ARC-P7: A prevents cubic or quadratic controls leaking."""
    style = _style()
    arc = _arc_command([(4.0, 0.0)], radii=(0.0, 2.0))
    path = PathDrawing(
        style,
        [
            PathCommand("M", [(0.0, 0.0)]),
            PathCommand("C", [(1.0, 1.0), (2.0, 1.0), (3.0, 0.0)]),
            arc,
            PathCommand("S", [(5.0, 1.0), (6.0, 0.0)]),
            PathCommand("Q", [(7.0, 1.0), (8.0, 0.0)]),
            arc,
            PathCommand("T", [(10.0, 0.0)]),
        ],
    )
    expected = CubicBezier((0.0, 0.0), (1.0, 1.0), (2.0, 1.0), (3.0, 0.0), style).points
    expected.append((4.0, 0.0))
    expected.extend(CubicBezier((4.0, 0.0), (4.0, 0.0), (5.0, 1.0), (6.0, 0.0), style).points[1:])
    expected.extend(QuadraticBezier((6.0, 0.0), (7.0, 1.0), (8.0, 0.0), style).points[1:])
    expected.append((4.0, 0.0))
    expected.extend(QuadraticBezier((4.0, 0.0), (4.0, 0.0), (10.0, 0.0), style).points[1:])

    assert raster_renderer._sampled_path_subpaths(path) == [expected]


@pytest.mark.condition("RASTER-PATH-ARC-P7")
@pytest.mark.parametrize(
    ("flags", "exception", "message"),
    [
        (None, TypeError, "flags must be a mapping"),
        ([], TypeError, "flags must be a mapping"),
        ({"radii": "1,2"}, TypeError, "radii must be a two-value sequence"),
        ({"radii": (1.0,)}, ValueError, "radii must contain exactly two values"),
        ({"radii": (1.0, 2.0, 3.0)}, ValueError, "radii must contain exactly two values"),
        ({"radii": (True, 1.0)}, TypeError, "radius must be numeric"),
        ({"radii": (object(), 1.0)}, TypeError, "radius must be numeric"),
        ({"radii": (math.nan, 1.0)}, ValueError, "radius must be finite"),
        ({"rotation": True}, TypeError, "rotation must be numeric"),
        ({"rotation": "clockwise"}, TypeError, "rotation must be numeric"),
        ({"rotation": math.inf}, ValueError, "rotation must be finite"),
        ({"large_arc": 2}, ValueError, "large_arc must be 0 or 1"),
        ({"sweep": 0.0}, TypeError, "sweep must be an integer flag"),
    ],
)
def test_malformed_live_arc_flags_fail_before_surface_allocation(
    monkeypatch: pytest.MonkeyPatch,
    flags: object,
    exception: type[Exception],
    message: str,
) -> None:
    """RASTER-PATH-ARC-P7: Mutated flag data fails before pixel allocation."""
    command = PathCommand("A", [(1.0, 1.0)])
    command.flags = flags
    path = PathDrawing(_style(), [PathCommand("M", [(0.0, 0.0)]), command])
    monkeypatch.setattr(raster_renderer.Image, "new", lambda *args, **kwargs: pytest.fail("surface allocated"))

    with pytest.raises(exception, match=message):
        render_drawing_group(DrawingComponentGroup("invalid-arc", [path]), Canvas(2, 2, "in"), dpi=20)


@pytest.mark.condition("RASTER-PATH-ARC-P7")
@pytest.mark.parametrize(
    ("endpoint", "radii", "message"),
    [
        ((1e308, 0.0), (1e-308, 1e-308), "radius correction"),
        ((1.0, 0.0), (1e308, 1e308), "center conversion"),
        ((1e100, 0.0), (1e250, 1e250), "center conversion"),
    ],
)
def test_unstable_finite_arc_geometry_fails_before_surface_allocation(
    monkeypatch: pytest.MonkeyPatch,
    endpoint: tuple[float, float],
    radii: tuple[float, float],
    message: str,
) -> None:
    """RASTER-PATH-ARC-P7: Non-finite derived geometry is rejected early."""
    path = PathDrawing(
        _style(),
        [PathCommand("M", [(0.0, 0.0)]), _arc_command([endpoint], radii=radii)],
    )
    monkeypatch.setattr(raster_renderer.Image, "new", lambda *args, **kwargs: pytest.fail("surface allocated"))

    with pytest.raises(ValueError, match=message):
        render_drawing_group(DrawingComponentGroup("unstable-arc", [path]), Canvas(2, 2, "in"), dpi=20)


@pytest.mark.condition("RASTER-PATH-ARC-P7")
def test_corrupted_command_tag_fails_before_surface_allocation(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASTER-PATH-ARC-P7: A corrupted live command tag cannot bypass dispatch."""
    command = PathCommand("L", [(1.0, 1.0)])
    command._type = "R"
    path = PathDrawing(_style(), [PathCommand("M", [(0.0, 0.0)]), command])
    monkeypatch.setattr(raster_renderer.Image, "new", lambda *args, **kwargs: pytest.fail("surface allocated"))

    with pytest.raises(ValueError, match="path command R is not supported"):
        render_drawing_group(DrawingComponentGroup("corrupt-command", [path]), Canvas(2, 2, "in"), dpi=20)


@pytest.mark.condition("RASTER-PATH-ARC-P7")
def test_empty_arc_fails_before_surface_allocation(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASTER-PATH-ARC-P7: A requires an endpoint before allocation."""
    path = PathDrawing(_style(), [PathCommand("M", [(0.0, 0.0)]), PathCommand("A")])
    monkeypatch.setattr(raster_renderer.Image, "new", lambda *args, **kwargs: pytest.fail("surface allocated"))

    with pytest.raises(ValueError, match="A requires an endpoint"):
        render_drawing_group(DrawingComponentGroup("empty-arc", [path]), Canvas(2, 2, "in"), dpi=20)


@pytest.mark.condition("RASTER-PATH-ARC-P7")
def test_endpoint_arc_renders_through_public_scan_path() -> None:
    """RASTER-PATH-ARC-P7: Endpoint arcs reach clean and Baird assets."""
    path = PathDrawing(
        _style(),
        [
            PathCommand("M", [(0.5, 1.5)]),
            _arc_command([(3.5, 1.5)], radii=(1.5, 0.75), rotation=25.0, large_arc=1, sweep=1),
        ],
    )

    result = render_and_degrade_drawing_group(
        DrawingComponentGroup("endpoint-arc", [path]),
        Canvas(4, 3, "in"),
        BairdParams.clean(),
        seed=23,
        background_rgb=(255, 255, 255),
        dpi=20,
        render_supersample=2,
    )

    assert result.clean.component_count == 1
    with result.clean.asset.image() as clean:
        assert clean.getbbox() is not None
    with result.degraded.asset.image() as degraded:
        assert degraded.getbbox() == (0, 0, 80, 60)
