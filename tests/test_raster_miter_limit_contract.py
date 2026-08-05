"""RASTER-MITER-LIMIT-P16 conditions for bounded raster miter joins."""

from __future__ import annotations

import math
from itertools import count

import pytest
from hypothesis import given
from hypothesis import strategies as st
from PIL import Image, ImageDraw

from InkGen import (
    Canvas,
    CircleDrawing,
    DrawingComponentGroup,
    DrawingStyle,
    LineDrawing,
    PolygonalDrawing,
    QuadraticBezierDrawing,
    RectangleDrawing,
    RegularPolygonDrawing,
    raster_renderer,
    render_drawing_group,
)

_STYLE_IDS = count()


def _style(
    miter_limit: float = 10.0,
    *,
    line_join: str = "miter",
    width: float = 0.6,
    opacity: float = 1.0,
) -> DrawingStyle:
    return DrawingStyle(
        f"miter-limit-{next(_STYLE_IDS)}",
        fill="none",
        stroke="#102030",
        stroke_width=width,
        stroke_opacity=opacity,
        stroke_linejoin=line_join,
        stroke_miterlimit=miter_limit,
    )


@pytest.mark.condition("RASTER-MITER-LIMIT-P16")
def test_right_angle_uses_bevel_below_and_miter_at_exact_threshold() -> None:
    """P16: A miter is retained exactly when its width ratio does not exceed the limit."""
    points = (0.0, 10.0), (10.0, 10.0), (10.0, 20.0)
    assert raster_renderer._miter_join_polygon(*points, 4, 1.0) == [
        (10.0, 10.0),
        (10.0, 8.0),
        (12.0, 10.0),
    ]
    polygon = raster_renderer._miter_join_polygon(*points, 4, math.sqrt(2.0))
    assert polygon[:2] == [(10.0, 10.0), (10.0, 8.0)]
    assert polygon[2] == pytest.approx((12.0, 8.0))
    assert polygon[3] == (12.0, 10.0)


@pytest.mark.condition("RASTER-MITER-LIMIT-P16")
@given(
    angle=st.floats(min_value=1.0, max_value=179.0, allow_nan=False, allow_infinity=False),
    width=st.integers(min_value=1, max_value=100),
)
def test_admitted_miter_satisfies_offset_and_bisector_distance_invariants(angle: float, width: int) -> None:
    """P16: Exact geometry follows the closed-form half-angle miter equation."""
    radians = math.radians(angle)
    previous = (-1.0, 0.0)
    vertex = (0.0, 0.0)
    following = (math.cos(radians), math.sin(radians))
    ratio = 1.0 / math.cos(radians / 2.0)
    polygon = raster_renderer._miter_join_polygon(previous, vertex, following, width, ratio * (1.0 + 1e-12))
    radius = width / 2.0
    assert len(polygon) == 4
    assert math.dist(vertex, polygon[1]) == pytest.approx(radius)
    assert math.dist(vertex, polygon[2]) == pytest.approx(radius * ratio)
    assert math.dist(vertex, polygon[3]) == pytest.approx(radius)
    assert len(raster_renderer._miter_join_polygon(previous, vertex, following, width, ratio * (1.0 - 1e-12))) == 3


def _primitive(name: str, style: DrawingStyle) -> object:
    if name == "rectangle":
        return RectangleDrawing((0.5, 0.5), 1.0, 1.0, 0.0, style)
    if name == "polygon":
        return PolygonalDrawing([(0.4, 1.6), (1.0, 0.4), (1.6, 1.6)], style)
    return RegularPolygonDrawing((1.0, 1.0), 4, 0.7, style, angle=45.0)


@pytest.mark.condition("RASTER-MITER-LIMIT-P16")
@pytest.mark.parametrize("primitive", ["rectangle", "polygon", "regular_polygon"])
def test_public_sharp_primitive_outputs_distinguish_low_and_high_limits(primitive: str) -> None:
    """P16: Every supported sharp primitive dispatches through bounded miter geometry."""
    outputs = []
    for limit in (1.0, 20.0):
        component = _primitive(primitive, _style(limit, width=0.8))
        result = render_drawing_group(DrawingComponentGroup(primitive, [component]), Canvas(2, 2, "in"), dpi=20, supersample=1)
        with result.asset.image() as image:
            outputs.append(image.getchannel("A").tobytes())
    assert outputs[0] != outputs[1]


@pytest.mark.condition("RASTER-MITER-LIMIT-P16")
def test_default_limit_preserves_exact_legacy_png() -> None:
    """P16: The default value continues to select the byte-identical legacy renderer path."""
    outputs = []
    for limit in (10.0, float("10")):
        component = PolygonalDrawing([(0.4, 1.6), (1.0, 0.4), (1.6, 1.6)], _style(limit))
        outputs.append(render_drawing_group(DrawingComponentGroup("legacy", [component]), Canvas(2, 2, "in"), dpi=20).asset.data)
    assert outputs[0] == outputs[1]


@pytest.mark.condition("RASTER-MITER-LIMIT-P16")
@pytest.mark.parametrize("line_join", ["round", "bevel"])
def test_limit_is_neutral_for_non_miter_join(line_join: str) -> None:
    """P16: Round and bevel joins do not consult the miter limit."""
    outputs = []
    for limit in (1.0, 100.0):
        component = PolygonalDrawing([(0.4, 1.6), (1.0, 0.4), (1.6, 1.6)], _style(limit, line_join=line_join))
        outputs.append(render_drawing_group(DrawingComponentGroup(line_join, [component]), Canvas(2, 2, "in"), dpi=20).asset.data)
    assert outputs[0] == outputs[1]


@pytest.mark.condition("RASTER-MITER-LIMIT-P16")
@pytest.mark.parametrize("primitive", ["line", "circle", "rounded_rectangle", "rounded_polygon"])
def test_limit_is_neutral_when_no_sharp_join_exists(primitive: str) -> None:
    """P16: Join-free and explicitly rounded geometry cannot acquire a miter artifact."""
    outputs = []
    for limit in (1.0, 100.0):
        style = _style(limit)
        if primitive == "line":
            component = LineDrawing((0.5, 1.0), (1.5, 1.0), style)
        elif primitive == "circle":
            component = CircleDrawing((1.0, 1.0), 0.5, style)
        elif primitive == "rounded_rectangle":
            component = RectangleDrawing((0.5, 0.5), 1.0, 1.0, 0.2, style)
        else:
            component = RegularPolygonDrawing((1.0, 1.0), 4, 0.7, style, angle=45.0, corner_radius=0.2)
        outputs.append(render_drawing_group(DrawingComponentGroup(primitive, [component]), Canvas(2, 2, "in"), dpi=20).asset.data)
    assert outputs[0] == outputs[1]


@pytest.mark.condition("RASTER-MITER-LIMIT-P16")
def test_nondefault_limit_rejects_sampled_geometry_before_allocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """P16: Tessellation vertices are not presented as semantic miter joins."""
    style = _style(2.0)
    component = QuadraticBezierDrawing((0, 0), (1, 0), (1, 1), style)
    monkeypatch.setattr(raster_renderer.Image, "new", lambda *args, **kwargs: pytest.fail("surface allocated"))
    with pytest.raises(ValueError, match="straight-edge primitives P16"):
        render_drawing_group(DrawingComponentGroup("sampled", [component]), Canvas(2, 2, "in"), dpi=20)


@pytest.mark.condition("RASTER-MITER-LIMIT-P16")
@pytest.mark.parametrize(
    ("value", "error"),
    [(object(), TypeError), (float("nan"), ValueError), (float("inf"), ValueError), (0.0, ValueError), (-1.0, ValueError)],
)
def test_live_miter_limit_corruption_fails_before_allocation(
    monkeypatch: pytest.MonkeyPatch,
    value: object,
    error: type[Exception],
) -> None:
    """P16: Corrupted live style state cannot reach Pillow or allocate a surface."""
    style = _style()
    style._stroke_miterlimit = value
    component = PolygonalDrawing([(0, 0), (1, 0), (1, 1)], style)
    monkeypatch.setattr(raster_renderer.Image, "new", lambda *args, **kwargs: pytest.fail("surface allocated"))
    with pytest.raises(error):
        render_drawing_group(DrawingComponentGroup("corrupt", [component]), Canvas(2, 2, "in"), dpi=20)


@pytest.mark.condition("RASTER-MITER-LIMIT-P16")
def test_near_reversal_bevel_fallback_stays_bounded() -> None:
    """P16: A finite low limit rejects a near-unbounded miter before constructing its tip."""
    polygon = raster_renderer._miter_join_polygon((0.0, 0.0), (1.0, 0.0), (0.0, 1e-12), 10, 2.0)
    assert len(polygon) == 3
    assert all(math.isfinite(coordinate) and abs(coordinate) < 10.0 for point in polygon for coordinate in point)


@pytest.mark.condition("RASTER-MITER-LIMIT-P16")
@pytest.mark.parametrize(
    "points",
    [
        ((0.0, 0.0), (0.0, 0.0), (1.0, 1.0)),
        ((0.0, 0.0), (1.0, 1.0), (1.0, 1.0)),
        ((0.0, 0.0), (1.0, 1.0), (2.0, 2.0)),
    ],
)
def test_degenerate_miter_vertices_add_no_polygon(
    points: tuple[tuple[float, float], tuple[float, float], tuple[float, float]],
) -> None:
    """P16: Repeated and collinear vertices have no positive-area miter wedge."""
    assert raster_renderer._miter_join_polygon(*points, 4, 2.0) == []


@pytest.mark.condition("RASTER-MITER-LIMIT-P16")
def test_join_helper_skips_empty_miter_wedge() -> None:
    """P16: A duplicate open vertex paints only its real segment."""
    surface = Image.new("RGBA", (12, 12), (0, 0, 0, 0))
    raster_renderer._draw_joined_polyline(
        ImageDraw.Draw(surface),
        [(1.0, 1.0), (1.0, 1.0), (8.0, 8.0)],
        (16, 32, 48, 255),
        2,
        "miter",
        2.0,
        closed=False,
    )
    assert surface.getpixel((4, 4)) == (16, 32, 48, 255)


@pytest.mark.condition("RASTER-MITER-LIMIT-P16")
def test_private_zero_bisector_defensively_returns_bevel(monkeypatch: pytest.MonkeyPatch) -> None:
    """P16: Bypassing the finite public limit cannot divide by a zero bisector."""
    tangents = iter(((1.0, 0.0), (0.0, 1.0), (1.0, 0.0), (-1.0, 0.0)))
    monkeypatch.setattr(raster_renderer, "_unit_tangent", lambda *args: next(tangents))
    assert raster_renderer._miter_join_polygon((0, 0), (1, 0), (1, 1), 4, math.inf) == [
        (1, 0),
        (1.0, -2.0),
        (3.0, 0.0),
    ]


@pytest.mark.condition("RASTER-MITER-LIMIT-P16")
@pytest.mark.parametrize("value", [math.nan, math.inf, 2_147_483_648.0, -2_147_483_648.0])
def test_generated_join_coordinates_enforce_direct_safe_bound(value: float) -> None:
    """P16: Every non-finite or out-of-range generated coordinate is rejected."""
    with pytest.raises(ValueError, match="safe coordinate range"):
        raster_renderer._bounded_join_polygon([(value, 0.0)])


@pytest.mark.condition("RASTER-MITER-LIMIT-P16")
def test_unrepresentable_admitted_miter_fails_before_allocation(monkeypatch: pytest.MonkeyPatch) -> None:
    """P16: An admitted but unsafe miter cannot overflow the raster backend."""
    style = _style(1e12, width=1e9)
    component = PolygonalDrawing([(0.0, 0.0), (1.0, 0.0), (0.0, 1e-6)], style)
    monkeypatch.setattr(raster_renderer.Image, "new", lambda *args, **kwargs: pytest.fail("surface allocated"))
    with pytest.raises(ValueError, match="safe coordinate range"):
        render_drawing_group(DrawingComponentGroup("unsafe", [component]), Canvas(2, 2, "in"), dpi=20)
