"""RASTER-LINE-JOIN-P15 conditions for neutral raster stroke joins."""

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
    PathDrawing,
    PolygonalDrawing,
    QuadraticBezierDrawing,
    RectangleDrawing,
    RegularPolygonDrawing,
    raster_renderer,
    render_drawing_group,
)
from InkGen.gradients import LinearGradientFill

_STYLE_IDS = count()


def _style(line_join: str, *, width: float = 0.6, opacity: float = 1.0) -> DrawingStyle:
    return DrawingStyle(
        f"line-join-{next(_STYLE_IDS)}",
        fill="none",
        stroke="#102030",
        stroke_width=width,
        stroke_opacity=opacity,
        stroke_linejoin=line_join,
    )


@pytest.mark.condition("RASTER-LINE-JOIN-P15")
def test_bevel_join_polygon_is_the_exact_outer_corner_triangle() -> None:
    """RASTER-LINE-JOIN-P15: Bevel geometry connects the two outer offsets."""
    assert raster_renderer._bevel_join_polygon((0.0, 10.0), (10.0, 10.0), (10.0, 20.0), 4) == [
        (10.0, 10.0),
        (10.0, 8.0),
        (12.0, 10.0),
    ]
    assert raster_renderer._bevel_join_polygon((10.0, 20.0), (10.0, 10.0), (0.0, 10.0), 4) == [
        (10.0, 10.0),
        (12.0, 10.0),
        (10.0, 8.0),
    ]


@pytest.mark.condition("RASTER-LINE-JOIN-P15")
@pytest.mark.parametrize(
    "points",
    [
        ((0.0, 0.0), (0.0, 0.0), (1.0, 1.0)),
        ((0.0, 0.0), (1.0, 1.0), (1.0, 1.0)),
        ((0.0, 0.0), (1.0, 1.0), (2.0, 2.0)),
        ((2.0, 2.0), (1.0, 1.0), (0.0, 0.0)),
    ],
)
def test_bevel_join_degenerate_and_collinear_vertices_add_no_polygon(
    points: tuple[tuple[float, float], tuple[float, float], tuple[float, float]],
) -> None:
    """RASTER-LINE-JOIN-P15: Undefined or zero-area joins are deterministic no-ops."""
    assert raster_renderer._bevel_join_polygon(*points, 4) == []


@pytest.mark.condition("RASTER-LINE-JOIN-P15")
def test_join_helper_short_open_and_degenerate_paths_add_no_spurious_paint() -> None:
    """RASTER-LINE-JOIN-P15: Short and degenerate helper paths paint only real segments."""
    blank = Image.new("RGBA", (12, 12), (0, 0, 0, 0))
    blank_draw = ImageDraw.Draw(blank)
    for points in ([], [(1.0, 1.0)]):
        raster_renderer._draw_joined_polyline(
            blank_draw,
            points,
            (16, 32, 48, 255),
            2,
            "round",
            closed=True,
        )
    assert blank.getbbox() is None

    open_duplicate = Image.new("RGBA", (12, 12), (0, 0, 0, 0))
    raster_renderer._draw_joined_polyline(
        ImageDraw.Draw(open_duplicate),
        [(1.0, 1.0), (1.0, 1.0), (8.0, 8.0)],
        (16, 32, 48, 255),
        2,
        "round",
        closed=False,
    )
    assert open_duplicate.getpixel((4, 4)) == (16, 32, 48, 255)

    collinear_bevel = Image.new("RGBA", (12, 12), (0, 0, 0, 0))
    raster_renderer._draw_joined_polyline(
        ImageDraw.Draw(collinear_bevel),
        [(1.0, 1.0), (4.0, 4.0), (8.0, 8.0)],
        (16, 32, 48, 255),
        2,
        "bevel",
        closed=True,
    )
    assert collinear_bevel.getpixel((4, 4)) == (16, 32, 48, 255)


@pytest.mark.condition("RASTER-LINE-JOIN-P15")
@given(
    previous=st.tuples(st.floats(-100, 100), st.floats(-100, 100)),
    vertex=st.tuples(st.floats(-100, 100), st.floats(-100, 100)),
    following=st.tuples(st.floats(-100, 100), st.floats(-100, 100)),
    width=st.integers(min_value=1, max_value=100),
)
def test_bevel_outer_offsets_are_exactly_half_a_stroke_from_the_vertex(
    previous: tuple[float, float],
    vertex: tuple[float, float],
    following: tuple[float, float],
    width: int,
) -> None:
    """RASTER-LINE-JOIN-P15: Every admitted bevel offset has radius width / 2."""
    polygon = raster_renderer._bevel_join_polygon(previous, vertex, following, width)
    if polygon:
        assert len(polygon) == 3
        assert polygon[0] == vertex
        assert math.hypot(polygon[1][0] - vertex[0], polygon[1][1] - vertex[1]) == pytest.approx(width / 2)
        assert math.hypot(polygon[2][0] - vertex[0], polygon[2][1] - vertex[1]) == pytest.approx(width / 2)


@pytest.mark.condition("RASTER-LINE-JOIN-P15")
@pytest.mark.parametrize("line_join", ["round", "bevel"])
def test_public_polygon_rectangle_and_regular_polygon_render_non_miter_joins(line_join: str) -> None:
    """RASTER-LINE-JOIN-P15: Every supported corner-bearing primitive reaches PNG output."""
    style = _style(line_join)
    components = [
        PolygonalDrawing([(0.5, 1.5), (1.0, 0.5), (1.5, 1.5)], style),
        RectangleDrawing((2.0, 0.5), 1.0, 1.0, 0.0, style),
        RegularPolygonDrawing((4.0, 1.0), 4, 0.6, style, angle=45.0),
    ]
    result = render_drawing_group(DrawingComponentGroup(f"{line_join}-joins", components), Canvas(5, 2, "in"), dpi=20, supersample=1)
    with result.asset.image() as image:
        assert image.mode == "RGBA"
        assert image.getbbox() is not None
        assert image.getpixel((20, 10))[3] > 0
        assert image.getpixel((40, 10))[3] > 0
        assert image.getpixel((80, 8))[3] > 0


@pytest.mark.condition("RASTER-LINE-JOIN-P15")
def test_round_and_bevel_join_outputs_are_visibly_distinct() -> None:
    """RASTER-LINE-JOIN-P15: Join selectors alter acute outer-corner support."""
    points = [(0.4, 1.6), (1.0, 0.4), (1.6, 1.6)]
    outputs = []
    for line_join in ("round", "bevel"):
        component = PolygonalDrawing(points, _style(line_join, width=0.8))
        result = render_drawing_group(DrawingComponentGroup(line_join, [component]), Canvas(2, 2, "in"), dpi=20, supersample=1)
        with result.asset.image() as image:
            outputs.append(image.getchannel("A").tobytes())
    assert outputs[0] != outputs[1]


@pytest.mark.condition("RASTER-LINE-JOIN-P15")
@pytest.mark.parametrize("line_join", ["round", "bevel"])
def test_gradient_rectangle_preserves_fill_and_non_miter_stroke(line_join: str) -> None:
    """RASTER-LINE-JOIN-P15: Gradient paint and explicit join paint compose independently."""
    component = RectangleDrawing(
        (0.5, 0.5),
        1.0,
        1.0,
        0.0,
        _style(line_join, width=0.2),
        LinearGradientFill(((0.0, "#ff0000"), (1.0, "#0000ff")), 0.0),
    )
    result = render_drawing_group(DrawingComponentGroup("gradient-join", [component]), Canvas(2, 2, "in"), dpi=20, supersample=1)
    with result.asset.image() as image:
        assert image.getpixel((20, 20))[3] == 255
        assert image.getpixel((10, 10)) == (16, 32, 48, 255)


@pytest.mark.condition("RASTER-LINE-JOIN-P15")
def test_dynamic_miter_selector_preserves_legacy_polygon_output() -> None:
    """RASTER-LINE-JOIN-P15: Value equality retains the exact established miter path."""
    outputs = []
    for line_join in ("miter", "".join(("m", "i", "t", "e", "r"))):
        component = PolygonalDrawing([(0.5, 1.5), (1.0, 0.5), (1.5, 1.5)], _style(line_join))
        result = render_drawing_group(DrawingComponentGroup("miter", [component]), Canvas(2, 2, "in"), dpi=20, supersample=1)
        outputs.append(result.asset.data)
    assert outputs[0] == outputs[1]


@pytest.mark.condition("RASTER-LINE-JOIN-P15")
@pytest.mark.parametrize("primitive", ["line", "circle"])
def test_join_selectors_are_neutral_for_primitives_without_vertices(primitive: str) -> None:
    """RASTER-LINE-JOIN-P15: Join style cannot alter a line or circle with no join."""
    outputs = []
    for line_join in ("miter", "round", "bevel"):
        style = _style(line_join)
        component = LineDrawing((0.5, 1.0), (1.5, 1.0), style) if primitive == "line" else CircleDrawing((1.0, 1.0), 0.5, style)
        result = render_drawing_group(DrawingComponentGroup(line_join, [component]), Canvas(2, 2, "in"), dpi=20, supersample=1)
        outputs.append(result.asset.data)
    assert outputs[0] == outputs[1] == outputs[2]


@pytest.mark.condition("RASTER-LINE-JOIN-P15")
@pytest.mark.parametrize("line_join", ["round", "bevel"])
@pytest.mark.parametrize("primitive", ["path", "curve"])
def test_sampled_geometry_joins_remain_closed_before_surface_allocation(
    monkeypatch: pytest.MonkeyPatch,
    line_join: str,
    primitive: str,
) -> None:
    """RASTER-LINE-JOIN-P15: Tessellation points are not misclassified as semantic joins."""
    style = _style(line_join)
    component = PathDrawing(style) if primitive == "path" else QuadraticBezierDrawing((0, 0), (1, 0), (1, 1), style)
    monkeypatch.setattr(raster_renderer.Image, "new", lambda *args, **kwargs: pytest.fail("surface allocated"))
    with pytest.raises(ValueError, match="straight-edge primitives P15"):
        render_drawing_group(DrawingComponentGroup("unsupported-join", [component]), Canvas(2, 2, "in"), dpi=20)


@pytest.mark.condition("RASTER-LINE-JOIN-P15")
@pytest.mark.parametrize(("value", "error"), [(object(), TypeError), ("arcs", ValueError)])
def test_live_join_corruption_fails_before_surface_allocation(
    monkeypatch: pytest.MonkeyPatch,
    value: object,
    error: type[Exception],
) -> None:
    """RASTER-LINE-JOIN-P15: Private selector corruption cannot reach Pillow."""
    style = _style("round")
    style._stroke_linejoin = value
    component = PolygonalDrawing([(0, 0), (1, 0), (1, 1)], style)
    monkeypatch.setattr(raster_renderer.Image, "new", lambda *args, **kwargs: pytest.fail("surface allocated"))
    with pytest.raises(error):
        render_drawing_group(DrawingComponentGroup("corrupt-join", [component]), Canvas(2, 2, "in"), dpi=20)


@pytest.mark.condition("RASTER-LINE-JOIN-P15")
def test_nondefault_miter_limit_remains_outside_p15_before_allocation(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASTER-LINE-JOIN-P15: Join support does not approximate the separate miter-limit contract."""
    style = _style("round")
    style.stroke_miterlimit = 2.0
    component = PolygonalDrawing([(0, 0), (1, 0), (1, 1)], style)
    monkeypatch.setattr(raster_renderer.Image, "new", lambda *args, **kwargs: pytest.fail("surface allocated"))
    with pytest.raises(ValueError, match="nondefault stroke miter limits"):
        render_drawing_group(DrawingComponentGroup("miter-limit", [component]), Canvas(2, 2, "in"), dpi=20)


@pytest.mark.condition("RASTER-LINE-JOIN-P15")
def test_transparent_stroke_with_non_miter_join_remains_a_noop() -> None:
    """RASTER-LINE-JOIN-P15: Join geometry cannot create paint without visible stroke."""
    component = PolygonalDrawing([(0.5, 1.5), (1.0, 0.5), (1.5, 1.5)], _style("round", opacity=0.0))
    result = render_drawing_group(DrawingComponentGroup("transparent-join", [component]), Canvas(2, 2, "in"), dpi=20)
    with result.asset.image() as image:
        assert image.getbbox() is None
