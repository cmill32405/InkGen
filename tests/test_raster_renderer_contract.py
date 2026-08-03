"""RASTER-RENDERER-P1 conditions for dependency-free in-memory rendering."""

from __future__ import annotations

import io
from uuid import uuid4

import pytest
from PIL import Image

import InkGen.raster_renderer as raster_renderer
from InkGen.boundary import Canvas
from InkGen.drawing_components import (
    ArcDrawing,
    CircleDrawing,
    DrawingComponentGroup,
    ImageDrawing,
    LineDrawing,
    OutputFormat,
    PolygonalDrawing,
    RectangleDrawing,
    RegularPolygonDrawing,
)
from InkGen.gradients import LinearGradientFill
from InkGen.image_assets import RasterImageAsset
from InkGen.raster_renderer import render_drawing_group
from InkGen.style import DrawingStyle


def _style(
    *,
    stroke: str = "none",
    fill: str = "none",
    stroke_width: float = 0.0,
    stroke_opacity: float = 1.0,
    fill_opacity: float = 1.0,
    stroke_dasharray: tuple[float, ...] = (),
    stroke_dash_offset: float = 0.0,
    stroke_linecap: str = "butt",
    stroke_linejoin: str = "miter",
    stroke_miterlimit: float = 10.0,
) -> DrawingStyle:
    return DrawingStyle(
        f"raster_contract_{uuid4().hex}",
        stroke=stroke,
        fill=fill,
        stroke_width=stroke_width,
        stroke_opacity=stroke_opacity,
        fill_opacity=fill_opacity,
        stroke_dasharray=stroke_dasharray,
        stroke_dash_offset=stroke_dash_offset,
        stroke_linecap=stroke_linecap,
        stroke_linejoin=stroke_linejoin,
        stroke_miterlimit=stroke_miterlimit,
    )


def _asset(mode: str, color: tuple[int, ...], size: tuple[int, int] = (2, 2)) -> RasterImageAsset:
    output = io.BytesIO()
    Image.new(mode, size, color).save(output, format="PNG")
    return RasterImageAsset.from_bytes(output.getvalue())


@pytest.mark.condition("RASTER-RENDERER-P1")
def test_empty_group_renders_deterministic_transparent_physical_canvas() -> None:
    """RASTER-RENDERER-P1: Canvas units and DPI determine stable RGBA dimensions."""
    group = DrawingComponentGroup("empty")
    canvas = Canvas(2.0, 1.0, "in")

    first = render_drawing_group(group, canvas, dpi=10.0, supersample=2)
    second = render_drawing_group(group, canvas, dpi=10.0, supersample=2)

    assert first.asset.data == second.asset.data
    assert (first.asset.width, first.asset.height, first.asset.mode) == (20, 10, "RGBA")
    assert first.asset.has_alpha is True
    assert first.manifest == {
        "renderer": "inkgen-raster-v1",
        "canvas": {"width": 2.0, "height": 1.0, "units": "in"},
        "dpi": 10.0,
        "supersample": 2,
        "background_rgba": None,
        "output_pixels": [20, 10],
        "component_count": 0,
    }
    with first.asset.image() as image:
        assert image.getpixel((0, 0)) == (0, 0, 0, 0)


@pytest.mark.condition("RASTER-RENDERER-P1")
def test_millimeter_canvas_uses_physical_dpi_conversion() -> None:
    """RASTER-RENDERER-P1: Millimeters convert through exactly 25.4 mm/inch."""
    result = render_drawing_group(DrawingComponentGroup("mm"), Canvas(25.4, 12.7, "mm"), dpi=100.0)

    assert (result.asset.width, result.asset.height) == (100, 50)


@pytest.mark.condition("RASTER-RENDERER-P1")
def test_single_sample_render_preserves_source_metadata() -> None:
    """RASTER-RENDERER-P1: Supersample one bypasses reduction and preserves source."""
    result = render_drawing_group(
        DrawingComponentGroup("single"),
        Canvas(1, 1, "in"),
        dpi=10,
        supersample=1,
        source="generated://single",
    )

    assert result.asset.source == "generated://single"
    with result.asset.image() as image:
        assert image.getpixel((0, 0)) == (0, 0, 0, 0)


@pytest.mark.condition("RASTER-RENDERER-P1")
def test_default_dpi_supersample_and_keyword_only_contract() -> None:
    """RASTER-RENDERER-P1: Public defaults and keyword-only controls are pinned."""
    result = render_drawing_group(DrawingComponentGroup("defaults"), Canvas(0.1, 0.1, "in"))

    assert (result.asset.width, result.asset.height) == (30, 30)
    assert result.dpi == 300.0
    assert result.supersample == 2
    with pytest.raises(TypeError):
        render_drawing_group(DrawingComponentGroup("positional"), Canvas(1, 1, "in"), 10, 1)  # type: ignore[misc]


@pytest.mark.condition("RASTER-RENDERER-P1")
def test_tiny_positive_canvas_keeps_one_pixel_per_axis() -> None:
    """RASTER-RENDERER-P1: Positive physical dimensions cannot round to zero pixels."""
    result = render_drawing_group(DrawingComponentGroup("tiny"), Canvas(0.01, 0.01, "in"), dpi=10, supersample=1)

    assert (result.asset.width, result.asset.height) == (1, 1)


@pytest.mark.condition("RASTER-RENDERER-P1")
@pytest.mark.parametrize(
    ("canvas", "dpi", "supersample", "background", "exception", "message"),
    [
        (object(), 10.0, 2, None, TypeError, "canvas must be a Canvas"),
        (Canvas(1, 1, "in"), True, 2, None, TypeError, "dpi must be numeric"),
        (Canvas(1, 1, "in"), 0.0, 2, None, ValueError, "dpi must be greater than zero"),
        (Canvas(1, 1, "in"), float("nan"), 2, None, ValueError, "dpi must be finite"),
        (Canvas(1, 1, "in"), 10.0, True, None, TypeError, "supersample must be an integer"),
        (Canvas(1, 1, "in"), 10.0, 0, None, ValueError, "supersample must be between 1 and 8"),
        (Canvas(1, 1, "in"), 10.0, 9, None, ValueError, "supersample must be between 1 and 8"),
        (Canvas(1, 1, "in"), 10.0, 2, "white", TypeError, "background_rgba must contain four"),
        (Canvas(1, 1, "in"), 10.0, 2, (1, 2, 3), ValueError, "background_rgba must contain four"),
        (Canvas(1, 1, "in"), 10.0, 2, (1, 2, 3, 256), ValueError, "background_rgba channels"),
        (Canvas(1, 1, "in"), 10.0, 2, (1, 2, 3, True), TypeError, "background_rgba channels"),
    ],
)
def test_render_boundary_rejects_invalid_configuration(
    canvas: object,
    dpi: object,
    supersample: object,
    background: object,
    exception: type[Exception],
    message: str,
) -> None:
    """RASTER-RENDERER-P1: Configuration errors fail before image creation."""
    with pytest.raises(exception, match=message):
        render_drawing_group(  # type: ignore[arg-type]
            DrawingComponentGroup("bad"),
            canvas,
            dpi=dpi,
            supersample=supersample,
            background_rgba=background,
        )


@pytest.mark.condition("RASTER-RENDERER-P1")
def test_render_resource_guard_rejects_excessive_supersampled_surface() -> None:
    """RASTER-RENDERER-P1: The public boundary rejects excessive allocations."""
    with pytest.raises(ValueError, match="64,000,000-pixel supersampled limit"):
        render_drawing_group(DrawingComponentGroup("large"), Canvas(100, 100, "in"), dpi=100, supersample=8)


@pytest.mark.condition("RASTER-RENDERER-P1")
def test_resource_limit_comparison_is_strict(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASTER-RENDERER-P1: A surface equal to the limit is permitted; one above fails."""
    monkeypatch.setattr(raster_renderer, "_MAX_SUPERSAMPLED_PIXELS", 100)

    accepted = render_drawing_group(DrawingComponentGroup("exact"), Canvas(1, 1, "in"), dpi=10, supersample=1)
    assert (accepted.asset.width, accepted.asset.height) == (10, 10)
    with pytest.raises(ValueError, match="100-pixel supersampled limit"):
        render_drawing_group(DrawingComponentGroup("over"), Canvas(1.1, 1, "in"), dpi=10, supersample=1)


@pytest.mark.condition("RASTER-RENDERER-P1")
def test_render_rejects_invalid_group_and_live_component_container() -> None:
    """RASTER-RENDERER-P1: The group boundary is revalidated on every render."""
    with pytest.raises(TypeError, match="group must be a DrawingComponentGroup"):
        render_drawing_group(object(), Canvas(1, 1, "in"), dpi=10)  # type: ignore[arg-type]

    group = DrawingComponentGroup("bad container")
    group.components = "bad"  # type: ignore[assignment]
    with pytest.raises(TypeError, match="components must be a sequence"):
        render_drawing_group(group, Canvas(1, 1, "in"), dpi=10)


@pytest.mark.condition("RASTER-RENDERER-P1")
def test_private_numeric_and_background_boundaries_are_exact() -> None:
    """RASTER-RENDERER-P1: Numeric coercion and channel order resist boundary mutations."""
    assert raster_renderer._positive_finite_number(1.0, "value") == 1.0
    with pytest.raises(ValueError, match="greater than zero"):
        raster_renderer._positive_finite_number(-1.0, "value")
    assert raster_renderer._validated_background((1, 2, 3, 4)) == (1, 2, 3, 4)
    with pytest.raises(ValueError, match="contain four"):
        raster_renderer._validated_background((1, 2, 3, 4, 5))
    with pytest.raises(ValueError, match="between zero and 255"):
        raster_renderer._validated_background((-1, 2, 3, 4))


@pytest.mark.condition("RASTER-RENDERER-P1")
def test_background_and_rectangle_fill_preserve_explicit_rgba() -> None:
    """RASTER-RENDERER-P1: Filled rectangles source-over an explicit background."""
    style = _style(fill="#ff0000", fill_opacity=0.5)
    group = DrawingComponentGroup("rectangle", [RectangleDrawing((1, 1), 4, 3, 0, style)])

    result = render_drawing_group(group, Canvas(6, 5, "in"), dpi=10, background_rgba=(0, 0, 255, 255))

    with result.asset.image() as image:
        outside = image.getpixel((5, 5))
        inside = image.getpixel((20, 20))
    assert outside == (0, 0, 255, 255)
    assert inside[0] in range(127, 129)
    assert inside[1] == 0
    assert inside[2] in range(127, 129)
    assert inside[3] == 255


@pytest.mark.condition("RASTER-RENDERER-P1")
def test_stroke_geometry_renders_lines_and_circle_outlines() -> None:
    """RASTER-RENDERER-P1: Scaled line and circle strokes reach expected pixels."""
    style = _style(stroke="#00ff00", stroke_width=0.4)
    group = DrawingComponentGroup(
        "strokes",
        [LineDrawing((1, 1), (5, 1), style), CircleDrawing((3, 3), 1, style)],
    )

    result = render_drawing_group(group, Canvas(6, 5, "in"), dpi=10, supersample=4)

    with result.asset.image() as image:
        assert image.getpixel((30, 10))[1] > 200
        assert image.getpixel((30, 20))[1] > 200
        assert image.getpixel((30, 30))[3] == 0


@pytest.mark.condition("RASTER-RENDERER-P1")
def test_irregular_and_regular_polygons_render_fills() -> None:
    """RASTER-RENDERER-P1: Both neutral polygon contracts render to RGBA."""
    red = _style(fill="#ff0000")
    blue = _style(fill="#0000ff")
    group = DrawingComponentGroup(
        "polygons",
        [
            PolygonalDrawing([(0.5, 0.5), (2.5, 0.5), (1.5, 2.5)], red),
            RegularPolygonDrawing((4.0, 1.5), 4, 1.0, blue, angle=0.0),
        ],
    )

    result = render_drawing_group(group, Canvas(6, 3, "in"), dpi=20)

    with result.asset.image() as image:
        assert image.getpixel((30, 25))[0] > 200
        assert image.getpixel((80, 30))[2] > 200


@pytest.mark.condition("RASTER-RENDERER-P1")
def test_stroke_only_and_unpainted_shapes_use_explicit_paint_contracts() -> None:
    """RASTER-RENDERER-P1: Missing fill and stroke remain unpainted independently."""
    outline = PolygonalDrawing(
        [(0.5, 0.5), (2.5, 0.5), (1.5, 2.5)],
        _style(stroke="#00ff00", stroke_width=0.2),
    )
    invisible_line = LineDrawing((0, 0), (3, 3), _style())

    result = render_drawing_group(DrawingComponentGroup("paint", [outline, invisible_line]), Canvas(3, 3, "in"), dpi=20)

    with result.asset.image() as image:
        assert image.getpixel((30, 10))[1] > 150
        assert image.getpixel((30, 30))[3] == 0


@pytest.mark.condition("RASTER-RENDERER-P1")
def test_image_drawing_preserves_source_alpha_without_white_flattening() -> None:
    """RASTER-RENDERER-P1: Image alpha remains alpha on a transparent canvas."""
    source = _asset("RGBA", (255, 0, 0, 128))
    group = DrawingComponentGroup("image", [ImageDrawing(source, (1, 1), 2, 2)])

    result = render_drawing_group(group, Canvas(4, 4, "in"), dpi=10)

    with result.asset.image() as image:
        pixel = image.getpixel((20, 20))
    assert pixel[0] == 255
    assert pixel[1:3] == (0, 0)
    assert pixel[3] in range(127, 129)


@pytest.mark.condition("RASTER-RENDERER-P1")
def test_component_order_uses_source_over_compositing() -> None:
    """RASTER-RENDERER-P1: Later components paint over earlier components."""
    red = RectangleDrawing((0, 0), 2, 2, 0, _style(fill="#ff0000"))
    blue = RectangleDrawing((1, 1), 2, 2, 0, _style(fill="#0000ff", fill_opacity=0.5))

    result = render_drawing_group(DrawingComponentGroup("order", [red, blue]), Canvas(3, 3, "in"), dpi=10)

    with result.asset.image() as image:
        overlap = image.getpixel((15, 15))
    assert overlap[0] in range(127, 129)
    assert overlap[2] in range(127, 129)
    assert overlap[3] == 255


class _RecordingDraw:
    """Record exact Pillow drawing calls without raster-kernel ambiguity."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def rectangle(self, *args: object, **kwargs: object) -> None:
        self.calls.append(("rectangle", args, kwargs))

    def line(self, *args: object, **kwargs: object) -> None:
        self.calls.append(("line", args, kwargs))

    def ellipse(self, *args: object, **kwargs: object) -> None:
        self.calls.append(("ellipse", args, kwargs))

    def polygon(self, *args: object, **kwargs: object) -> None:
        self.calls.append(("polygon", args, kwargs))


@pytest.mark.condition("RASTER-RENDERER-P1")
def test_exact_primitive_arguments_reach_pillow(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASTER-RENDERER-P1: Every supported vector maps to exact scaled draw arguments."""
    recorder = _RecordingDraw()
    monkeypatch.setattr(raster_renderer.ImageDraw, "Draw", lambda surface: recorder)
    surface = object()
    painted = _style(stroke="#102030", fill="#405060", stroke_width=0.5, stroke_opacity=0.25, fill_opacity=0.5)

    raster_renderer._render_component(surface, RectangleDrawing((1, 2), 3, 4, 0, painted), 10.0)  # type: ignore[arg-type]
    raster_renderer._render_component(surface, LineDrawing((1, 2), (3, 4), painted), 10.0)  # type: ignore[arg-type]
    raster_renderer._render_component(surface, CircleDrawing((3, 4), 2, painted), 10.0)  # type: ignore[arg-type]
    raster_renderer._render_component(surface, PolygonalDrawing([(1, 1), (3, 1), (2, 4)], painted), 10.0)  # type: ignore[arg-type]
    raster_renderer._render_component(surface, RegularPolygonDrawing((5, 5), 4, 2, painted), 10.0)  # type: ignore[arg-type]

    fill = (64, 80, 96, 128)
    stroke = (16, 32, 48, 64)
    assert recorder.calls[0] == ("rectangle", ((10, 20, 40, 60),), {"fill": fill, "outline": stroke, "width": 5})
    assert recorder.calls[1] == ("line", ([(10, 20), (30, 40)],), {"fill": stroke, "width": 5})
    assert recorder.calls[2] == ("ellipse", ((10, 20, 50, 60),), {"fill": fill, "outline": stroke, "width": 5})
    assert recorder.calls[3] == ("polygon", ([(10, 10), (30, 10), (20, 40)],), {"fill": fill})
    assert recorder.calls[4] == (
        "line",
        ([(10, 10), (30, 10), (20, 40), (10, 10)],),
        {"fill": stroke, "width": 5},
    )
    assert recorder.calls[5] == ("polygon", ([(50, 70), (30, 50), (50, 30), (70, 50)],), {"fill": fill})
    assert recorder.calls[6] == (
        "line",
        ([(50, 70), (30, 50), (50, 30), (70, 50), (50, 70)],),
        {"fill": stroke, "width": 5},
    )


@pytest.mark.condition("RASTER-RENDERER-P1")
def test_subpixel_stroke_and_zero_width_stroke_are_distinct(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASTER-RENDERER-P1: Positive subpixel strokes clamp to one; zero stays absent."""
    recorder = _RecordingDraw()
    monkeypatch.setattr(raster_renderer.ImageDraw, "Draw", lambda surface: recorder)
    thin = _style(stroke="#000000", stroke_width=0.01)
    zero = _style(stroke="#000000", fill="#ffffff", stroke_width=0.0)

    raster_renderer._render_component(object(), LineDrawing((0, 0), (1, 1), thin), 10.0)  # type: ignore[arg-type]
    raster_renderer._render_component(object(), RectangleDrawing((0, 0), 1, 1, 0, zero), 10.0)  # type: ignore[arg-type]

    assert recorder.calls[0] == ("line", ([(0, 0), (10, 10)],), {"fill": (0, 0, 0, 255), "width": 1})
    assert recorder.calls[1] == ("rectangle", ((0, 0, 10, 10),), {"fill": (255, 255, 255, 255), "outline": None, "width": 0})


@pytest.mark.condition("RASTER-RENDERER-P1")
def test_regular_polygon_uses_exact_shared_vertex_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASTER-RENDERER-P1: Raster vertices honor established component precision."""
    captured: list[list[tuple[float, float]]] = []
    polygon = RegularPolygonDrawing((5, 7), 5, 2.5, _style(fill="#000000"), angle=13.0)
    expected = polygon.to_component(OutputFormat.SVG)._get_points()  # type: ignore[attr-defined]
    monkeypatch.setattr(raster_renderer, "_draw_polygon", lambda draw, points, scale, fill, stroke, width: captured.append(list(points)))

    raster_renderer._render_component(Image.new("RGBA", (1, 1)), polygon, 100.0)

    assert len(captured) == 1
    for actual_point, expected_point in zip(captured[0], expected, strict=True):
        assert actual_point == (
            pytest.approx(expected_point[0], abs=1e-3),
            pytest.approx(expected_point[1], abs=1e-3),
        )


class _RecordingSurface:
    def __init__(self) -> None:
        self.calls: list[tuple[tuple[int, int], tuple[int, int]]] = []

    def alpha_composite(self, image: Image.Image, *, dest: tuple[int, int]) -> None:
        self.calls.append((image.size, dest))


@pytest.mark.condition("RASTER-RENDERER-P1")
def test_image_scaling_clamps_subpixel_sizes_and_multiplies_normal_sizes() -> None:
    """RASTER-RENDERER-P1: Image geometry uses multiplication and a one-pixel floor."""
    surface = _RecordingSurface()
    source = _asset("RGBA", (1, 2, 3, 4))

    raster_renderer._render_image(surface, ImageDrawing(source, (1.25, 2.5), 0.04, 0.04), 10.0)  # type: ignore[arg-type]
    raster_renderer._render_image(surface, ImageDrawing(source, (1.25, 2.5), 2.0, 3.0), 4.0)  # type: ignore[arg-type]

    assert surface.calls == [((1, 1), (12, 25)), ((8, 12), (5, 10))]


@pytest.mark.condition("RASTER-RENDERER-P1")
def test_style_color_and_scale_helpers_are_exact() -> None:
    """RASTER-RENDERER-P1: Color channels, opacity, and coordinate products are pinned."""
    assert raster_renderer._style_color("#123456", 0.5) == (18, 52, 86, 128)
    assert raster_renderer._style_color("#123456", 1.0) == (18, 52, 86, 255)
    assert raster_renderer._style_color("none", 1.0) is None
    assert raster_renderer._style_color("#123456", 0.0) is None
    assert raster_renderer._scaled_point((1.25, 2.75), 4.0) == (5, 11)
    assert raster_renderer._scaled_box(1.25, 2.75, 3.5, 4.25, 4.0) == (5, 11, 14, 17)


@pytest.mark.condition("RASTER-RENDERER-P1")
def test_unsupported_primitive_and_style_features_fail_loudly() -> None:
    """RASTER-RENDERER-P1: P1 never silently approximates unsupported contracts."""
    arc = ArcDrawing((1, 1), 1, 1, 0, 90, _style(stroke="#000000", stroke_width=1))
    rounded = RectangleDrawing((1, 1), 2, 2, 0.5, _style(fill="#000000"))
    gradient = RectangleDrawing(
        (1, 1),
        2,
        2,
        0,
        _style(fill="#000000"),
        LinearGradientFill(((0.0, "#000000"), (1.0, "#ffffff"))),
    )
    rounded_polygon = RegularPolygonDrawing((1.5, 1.5), 4, 1, _style(fill="#000000"), corner_radius=0.25)
    zero_tuple = RectangleDrawing((0, 0), 1, 1, (0.0, 0.0), _style(fill="#000000"))
    asymmetric_rounding = RectangleDrawing((0, 0), 1, 1, (0.0, 0.25), _style(fill="#000000"))
    dashed = LineDrawing((0, 0), (1, 1), _style(stroke="#000000", stroke_width=1, stroke_dasharray=(1, 1)))
    dash_offset = LineDrawing((0, 0), (1, 1), _style(stroke="#000000", stroke_width=1, stroke_dash_offset=1))
    round_cap = LineDrawing((0, 0), (1, 1), _style(stroke="#000000", stroke_width=1, stroke_linecap="round"))
    round_join = PolygonalDrawing(
        [(0, 0), (1, 0), (1, 1)],
        _style(stroke="#000000", stroke_width=1, stroke_linejoin="round"),
    )
    bevel_join = PolygonalDrawing(
        [(0, 0), (1, 0), (1, 1)],
        _style(stroke="#000000", stroke_width=1, stroke_linejoin="bevel"),
    )
    miter_limit = PolygonalDrawing(
        [(0, 0), (1, 0), (1, 1)],
        _style(stroke="#000000", stroke_width=1, stroke_miterlimit=5),
    )
    high_miter_limit = PolygonalDrawing(
        [(0, 0), (1, 0), (1, 1)],
        _style(stroke="#000000", stroke_width=1, stroke_miterlimit=15),
    )

    for component, message in [
        (arc, "unsupported raster primitive: ArcDrawing"),
        (rounded, "rounded rectangles are not supported"),
        (gradient, "rectangle gradients are not supported"),
        (rounded_polygon, "rounded regular polygons are not supported"),
        (asymmetric_rounding, "rounded rectangles are not supported"),
        (dashed, "dashed strokes are not supported"),
        (dash_offset, "stroke dash offsets are not supported"),
        (round_cap, "only butt stroke caps are supported"),
        (round_join, "only miter stroke joins are supported"),
        (bevel_join, "only miter stroke joins are supported"),
        (miter_limit, "nondefault stroke miter limits are not supported"),
        (high_miter_limit, "nondefault stroke miter limits are not supported"),
    ]:
        with pytest.raises(ValueError, match=message):
            render_drawing_group(DrawingComponentGroup("unsupported", [component]), Canvas(3, 3, "in"), dpi=10)

    assert render_drawing_group(DrawingComponentGroup("zero tuple", [zero_tuple]), Canvas(1, 1, "in"), dpi=10).component_count == 1

    dynamic_defaults = LineDrawing(
        (0, 0),
        (1, 1),
        _style(
            stroke="#000000",
            stroke_width=1,
            stroke_linecap="".join(("b", "u", "t", "t")),
            stroke_linejoin="".join(("m", "i", "t", "e", "r")),
        ),
    )
    assert (
        render_drawing_group(DrawingComponentGroup("dynamic defaults", [dynamic_defaults]), Canvas(1, 1, "in"), dpi=10).component_count == 1
    )


@pytest.mark.condition("RASTER-RENDERER-P1")
def test_mutated_group_is_revalidated_before_allocation() -> None:
    """RASTER-RENDERER-P1: Live component-list mutation cannot be silently ignored."""
    group = DrawingComponentGroup("mutated")
    group.components.append(object())  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="component must implement to_component"):
        render_drawing_group(group, Canvas(1, 1, "in"), dpi=10)
