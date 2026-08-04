"""RASTER-LINE-CAP-P14 conditions for neutral raster line caps."""

from __future__ import annotations

import math
from itertools import count

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from InkGen import Canvas, DrawingComponentGroup, DrawingStyle, LineDrawing, RectangleDrawing, raster_renderer, render_drawing_group

_STYLE_IDS = count()


def _style(
    line_cap: str,
    *,
    dasharray: tuple[float, ...] = (),
    offset: float = 0.0,
    opacity: float = 1.0,
    width: float = 0.4,
    stroke: str = "#102030",
) -> DrawingStyle:
    return DrawingStyle(
        f"line-cap-{next(_STYLE_IDS)}",
        stroke=stroke,
        fill="none",
        stroke_width=width,
        stroke_opacity=opacity,
        stroke_dasharray=dasharray,
        stroke_dash_offset=offset,
        stroke_linecap=line_cap,
    )


@pytest.mark.condition("RASTER-LINE-CAP-P14")
def test_square_cap_polygon_extends_half_width_along_tangent_and_normal() -> None:
    """RASTER-LINE-CAP-P14: Square caps are the exact projected stroke rectangle."""
    assert raster_renderer._square_cap_polygon((5.0, 10.0), (15.0, 10.0), 4) == [
        (3.0, 12.0),
        (17.0, 12.0),
        (17.0, 8.0),
        (3.0, 8.0),
    ]
    assert raster_renderer._square_cap_polygon((10.0, 10.0), (10.0, 10.0), 4) == [
        (8.0, 12.0),
        (12.0, 12.0),
        (12.0, 8.0),
        (8.0, 8.0),
    ]
    assert raster_renderer._square_cap_polygon((15.0, 10.0), (5.0, 10.0), 6, (0.0, 1.0)) == [
        (18.0, 7.0),
        (2.0, 7.0),
        (2.0, 13.0),
        (18.0, 13.0),
    ]


@pytest.mark.condition("RASTER-LINE-CAP-P14")
def test_public_solid_round_and_square_caps_have_distinct_exact_rgba_pixels() -> None:
    """RASTER-LINE-CAP-P14: Public output paints round and square endpoint supports."""
    lines = [
        LineDrawing((0.5, 0.6), (1.5, 0.6), _style("round", opacity=0.5)),
        LineDrawing((0.5, 1.4), (1.5, 1.4), _style("square", opacity=0.5)),
    ]
    result = render_drawing_group(DrawingComponentGroup("solid-caps", lines), Canvas(2, 2, "in"), dpi=10, supersample=1)
    with result.asset.image() as image:
        assert image.getpixel((3, 6)) == (16, 32, 48, 128)
        assert image.getpixel((3, 4)) == (0, 0, 0, 0)
        assert image.getpixel((3, 12)) == (16, 32, 48, 128)
        assert image.getpixel((17, 16)) == (16, 32, 48, 128)
        assert image.getpixel((10, 14)) == (16, 32, 48, 128)


@pytest.mark.condition("RASTER-LINE-CAP-P14")
def test_public_round_cap_paints_both_endpoints_when_line_direction_is_reversed() -> None:
    """RASTER-LINE-CAP-P14: Round-cap support is invariant under endpoint order."""
    line = LineDrawing((1.5, 1.0), (0.5, 1.0), _style("round"))
    result = render_drawing_group(DrawingComponentGroup("reverse-round", [line]), Canvas(2, 2, "in"), dpi=10, supersample=1)
    with result.asset.image() as image:
        assert image.getpixel((3, 10)) == (16, 32, 48, 255)
        assert image.getpixel((17, 10)) == (16, 32, 48, 255)


@pytest.mark.condition("RASTER-LINE-CAP-P14")
def test_zero_length_solid_caps_follow_neutral_svg_semantics() -> None:
    """RASTER-LINE-CAP-P14: Butt is empty; round and square paint centered shapes."""
    lines = [
        LineDrawing((0.5, 0.5), (0.5, 0.5), _style("butt")),
        LineDrawing((1.0, 1.0), (1.0, 1.0), _style("round")),
        LineDrawing((1.5, 1.5), (1.5, 1.5), _style("square")),
    ]
    result = render_drawing_group(DrawingComponentGroup("zero-caps", lines), Canvas(2, 2, "in"), dpi=10, supersample=1)
    with result.asset.image() as image:
        assert image.getpixel((5, 5)) == (0, 0, 0, 0)
        assert image.getpixel((10, 10)) == (16, 32, 48, 255)
        assert image.getpixel((8, 8)) == (0, 0, 0, 0)
        assert image.getpixel((13, 13)) == (16, 32, 48, 255)


@pytest.mark.condition("RASTER-LINE-CAP-P14")
def test_zero_length_on_dashes_emit_cap_centers_with_phase_and_endpoint_inclusion() -> None:
    """RASTER-LINE-CAP-P14: Zero on-slots become oriented caps at exact cadence points."""
    assert raster_renderer._zero_length_dash_centers((0.0, 0.0), (5.0, 0.0), (0.0, 2.0), 0.0, 10) == [
        (0.0, 0.0),
        (2.0, 0.0),
        (4.0, 0.0),
    ]
    assert raster_renderer._zero_length_dash_centers((0.0, 0.0), (5.0, 0.0), (0.0, 2.0), 1.0, 10) == [
        (1.0, 0.0),
        (3.0, 0.0),
        (5.0, 0.0),
    ]
    assert raster_renderer._zero_length_dash_centers((0.0, 0.0), (5.0, 0.0), (2.0, 0.0), 0.0, 10) == []
    assert raster_renderer._zero_length_dash_centers((2.0, 3.0), (2.0, 3.0), (0.0, 0.0, 0.0, 1.0), 0.0, 1) == [(2.0, 3.0)]
    assert raster_renderer._zero_length_dash_centers(
        (0.0, 0.0),
        (4.0, 0.0),
        (1.0, 1.0, 0.0, 0.0),
        0.0,
        10,
    ) == [(2.0, 0.0), (4.0, 0.0)]
    assert raster_renderer._zero_length_dash_centers((0.0, 0.0), (1.0, 0.0), (0.0, 1e308), 1e308, 10) == [(0.0, 0.0)]
    with pytest.raises(ValueError, match="operation limit"):
        raster_renderer._zero_length_dash_centers((2.0, 3.0), (2.0, 3.0), (1.0, 1.0), 0.0, 0)


@pytest.mark.condition("RASTER-LINE-CAP-P14")
def test_public_round_zero_dash_pattern_paints_dots_without_filling_gaps() -> None:
    """RASTER-LINE-CAP-P14: A zero-on dash pattern is a deterministic dotted line."""
    line = LineDrawing((0.5, 1.0), (1.5, 1.0), _style("round", dasharray=(0.0, 0.4), width=0.2))
    result = render_drawing_group(DrawingComponentGroup("dots", [line]), Canvas(2, 2, "in"), dpi=10, supersample=1)
    with result.asset.image() as image:
        assert [image.getpixel((x, 10))[3] for x in range(4, 16)] == [255, 255, 255, 0, 255, 255, 255, 0, 255, 255, 255, 0]


@pytest.mark.condition("RASTER-LINE-CAP-P14")
def test_public_positive_dashes_apply_square_caps_to_every_painted_segment() -> None:
    """RASTER-LINE-CAP-P14: Every positive on-segment receives both square caps."""
    line = LineDrawing((0.5, 1.0), (1.5, 1.0), _style("square", dasharray=(0.2, 0.4), width=0.2))
    result = render_drawing_group(DrawingComponentGroup("square-dashes", [line]), Canvas(2, 2, "in"), dpi=10, supersample=1)
    with result.asset.image() as image:
        assert [image.getpixel((x, 10))[3] for x in range(4, 16)] == [255, 255, 255, 255, 255, 0, 255, 255, 255, 255, 255, 0]


@pytest.mark.condition("RASTER-LINE-CAP-P14")
def test_zero_length_dashed_line_cap_depends_on_phase() -> None:
    """RASTER-LINE-CAP-P14: A degenerate dashed line paints only when phase is on."""
    lines = [
        LineDrawing((0.5, 0.5), (0.5, 0.5), _style("round", dasharray=(1.0, 1.0))),
        LineDrawing((1.5, 1.5), (1.5, 1.5), _style("round", dasharray=(1.0, 1.0), offset=1.0)),
    ]
    result = render_drawing_group(DrawingComponentGroup("zero-dash-phase", lines), Canvas(2, 2, "in"), dpi=10, supersample=1)
    with result.asset.image() as image:
        assert image.getpixel((5, 5)) == (16, 32, 48, 255)
        assert image.getpixel((15, 15)) == (0, 0, 0, 0)


@pytest.mark.condition("RASTER-LINE-CAP-P14")
def test_cap_geometry_has_an_exact_combined_operation_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASTER-LINE-CAP-P14: Positive segments and zero caps share one bounded budget."""
    monkeypatch.setattr(raster_renderer, "_MAX_DASH_STEPS", 2)
    segments, centers = raster_renderer._line_cap_dash_geometry((0.0, 0.0), (1.0, 0.0), (0.0, 1.0), 0.0)
    assert segments == []
    assert centers == [(0.0, 0.0), (1.0, 0.0)]
    monkeypatch.setattr(raster_renderer, "_MAX_DASH_STEPS", 1)
    with pytest.raises(ValueError, match="1-operation limit"):
        raster_renderer._line_cap_dash_geometry((0.0, 0.0), (1.0, 0.0), (0.0, 1.0), 0.0)


@pytest.mark.condition("RASTER-LINE-CAP-P14")
@pytest.mark.parametrize("line_cap", ["round", "square"])
def test_cap_operation_limit_fails_before_surface_allocation(monkeypatch: pytest.MonkeyPatch, line_cap: str) -> None:
    """RASTER-LINE-CAP-P14: Hostile dotted recipes fail before Pillow allocation."""
    monkeypatch.setattr(raster_renderer, "_MAX_DASH_STEPS", 1)
    monkeypatch.setattr(raster_renderer.Image, "new", lambda *args, **kwargs: pytest.fail("surface allocated"))
    line = LineDrawing((0.0, 0.0), (1.0, 0.0), _style(line_cap, dasharray=(0.0, 1.0)))
    with pytest.raises(ValueError, match="1-operation limit"):
        render_drawing_group(DrawingComponentGroup("bounded-caps", [line]), Canvas(2, 2, "in"), dpi=10)


@pytest.mark.condition("RASTER-LINE-CAP-P14")
@pytest.mark.parametrize("line_cap", ["round", "square"])
def test_non_line_caps_remain_outside_the_closed_domain_before_allocation(
    monkeypatch: pytest.MonkeyPatch,
    line_cap: str,
) -> None:
    """RASTER-LINE-CAP-P14: P14 does not silently broaden cap support to shapes."""
    monkeypatch.setattr(raster_renderer.Image, "new", lambda *args, **kwargs: pytest.fail("surface allocated"))
    rectangle = RectangleDrawing((0, 0), 1, 1, 0, _style(line_cap))
    with pytest.raises(ValueError, match="supported only for raster LineDrawing P14"):
        render_drawing_group(DrawingComponentGroup("invalid-cap-shape", [rectangle]), Canvas(2, 2, "in"), dpi=10)


@pytest.mark.condition("RASTER-LINE-CAP-P14")
@pytest.mark.parametrize(("value", "error"), [(object(), TypeError), ("triangle", ValueError)])
def test_live_line_cap_corruption_fails_before_surface_allocation(
    monkeypatch: pytest.MonkeyPatch,
    value: object,
    error: type[Exception],
) -> None:
    """RASTER-LINE-CAP-P14: Private style corruption cannot bypass the cap domain."""
    style = _style("round")
    style._stroke_linecap = value
    monkeypatch.setattr(raster_renderer.Image, "new", lambda *args, **kwargs: pytest.fail("surface allocated"))
    with pytest.raises(error):
        render_drawing_group(
            DrawingComponentGroup("corrupt-cap", [LineDrawing((0, 0), (1, 0), style)]),
            Canvas(2, 2, "in"),
            dpi=10,
        )


@pytest.mark.condition("RASTER-LINE-CAP-P14")
def test_finite_dash_values_with_overflowing_period_fail_before_surface_allocation(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASTER-LINE-CAP-P14: A non-finite aggregate cadence cannot reach cap geometry."""
    style = _style("round", dasharray=(1.0, 1.0))
    style._stroke_dasharray = (1e308, 1e308)
    monkeypatch.setattr(raster_renderer.Image, "new", lambda *args, **kwargs: pytest.fail("surface allocated"))
    with pytest.raises(ValueError, match="dash period must be finite"):
        render_drawing_group(
            DrawingComponentGroup("overflowing-period", [LineDrawing((0, 0), (1, 0), style)]),
            Canvas(2, 2, "in"),
            dpi=10,
        )


@pytest.mark.condition("RASTER-LINE-CAP-P14")
def test_odd_dash_array_is_duplicated_once_before_cap_geometry() -> None:
    """RASTER-LINE-CAP-P14: Odd dash arrays use the SVG even-cycle normalization."""
    style = _style("round", dasharray=(1.0, 2.0, 3.0))
    assert raster_renderer._validated_line_dash(style) == ((1.0, 2.0, 3.0, 1.0, 2.0, 3.0), 0.0)


@pytest.mark.condition("RASTER-LINE-CAP-P14")
def test_dynamic_butt_value_preserves_legacy_line_and_shape_dispatch() -> None:
    """RASTER-LINE-CAP-P14: Dispatch uses value equality, not string identity or ordering."""
    dynamic_butt = "".join(("b", "u", "t", "t"))
    line = LineDrawing((0.5, 1.0), (1.5, 1.0), _style(dynamic_butt))
    result = render_drawing_group(DrawingComponentGroup("dynamic-butt", [line]), Canvas(2, 2, "in"), dpi=10)
    with result.asset.image() as image:
        assert image.getpixel((3, 10)) == (0, 0, 0, 0)
        assert image.getpixel((10, 10))[3] > 0

    rectangle = RectangleDrawing((0.5, 0.5), 1.0, 1.0, 0.0, _style(dynamic_butt, stroke="none"))
    rectangle.style._stroke_linecap = dynamic_butt
    raster_renderer._validate_raster_stroke_style(rectangle, rectangle.style)


@pytest.mark.condition("RASTER-LINE-CAP-P14")
def test_non_butt_cap_with_no_visible_stroke_is_a_transparent_noop() -> None:
    """RASTER-LINE-CAP-P14: Cap geometry cannot create paint without a stroke."""
    line = LineDrawing((0.5, 1.0), (1.5, 1.0), _style("square", stroke="none"))
    result = render_drawing_group(DrawingComponentGroup("no-stroke-cap", [line]), Canvas(2, 2, "in"), dpi=10)
    with result.asset.image() as image:
        assert image.getbbox() is None


@pytest.mark.condition("RASTER-LINE-CAP-P14")
@settings(max_examples=100, deadline=None)
@given(
    start_x=st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    start_y=st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    delta_x=st.floats(min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False),
    delta_y=st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    width=st.integers(min_value=1, max_value=100),
)
def test_square_cap_property_projects_corners_to_exact_tangent_and_normal_bounds(
    start_x: float,
    start_y: float,
    delta_x: float,
    delta_y: float,
    width: int,
) -> None:
    """RASTER-LINE-CAP-P14: Every square-cap corner satisfies the support equations."""
    start = (start_x, start_y)
    end = (start_x + delta_x, start_y + delta_y)
    unit_x, unit_y = raster_renderer._unit_tangent(start, end)
    normal_x, normal_y = -unit_y, unit_x
    radius = width / 2.0
    corners = raster_renderer._square_cap_polygon(start, end, width)
    tangent_projections = [point[0] * unit_x + point[1] * unit_y for point in corners]
    normal_projections = [point[0] * normal_x + point[1] * normal_y for point in corners]
    start_projection = start_x * unit_x + start_y * unit_y
    end_projection = end[0] * unit_x + end[1] * unit_y
    center_normal = start_x * normal_x + start_y * normal_y
    assert min(tangent_projections) == pytest.approx(start_projection - radius)
    assert max(tangent_projections) == pytest.approx(end_projection + radius)
    assert min(normal_projections) == pytest.approx(center_normal - radius)
    assert max(normal_projections) == pytest.approx(center_normal + radius)
    assert math.isclose(math.hypot(unit_x, unit_y), 1.0)
