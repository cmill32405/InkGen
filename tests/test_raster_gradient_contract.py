"""RASTER-GRADIENT-P10 conditions for neutral linear-gradient rectangles."""

from __future__ import annotations

from uuid import uuid4

import pytest

import InkGen.raster_renderer as raster_renderer
from InkGen import BairdParams
from InkGen.boundary import Canvas
from InkGen.drawing_components import DrawingComponentGroup, RectangleDrawing
from InkGen.gradients import LinearGradientFill
from InkGen.raster_renderer import render_and_degrade_drawing_group, render_drawing_group
from InkGen.style import DrawingStyle


def _style(
    *,
    stroke: str = "none",
    fill: str = "none",
    stroke_width: float = 0.0,
    fill_opacity: float = 1.0,
) -> DrawingStyle:
    return DrawingStyle(
        f"raster_gradient_{uuid4().hex}",
        stroke=stroke,
        fill=fill,
        stroke_width=stroke_width,
        fill_opacity=fill_opacity,
    )


def _gradient(
    *,
    angle_deg: float = 0.0,
    stops: tuple[tuple[float, str], ...] = ((0.0, "#000000"), (1.0, "#ffffff")),
) -> LinearGradientFill:
    return LinearGradientFill(stops, angle_deg)


def _rectangle(
    *,
    angle_deg: float = 0.0,
    stops: tuple[tuple[float, str], ...] = ((0.0, "#000000"), (1.0, "#ffffff")),
    style: DrawingStyle | None = None,
    position: tuple[float, float] = (1.0, 1.0),
    width: float = 4.0,
    height: float = 2.0,
    corner_radii: float | tuple[float, float] = 0.0,
) -> RectangleDrawing:
    return RectangleDrawing(
        position,
        width,
        height,
        corner_radii,
        style or _style(),
        _gradient(angle_deg=angle_deg, stops=stops),
    )


@pytest.mark.condition("RASTER-GRADIENT-P10")
@pytest.mark.parametrize(
    ("angle", "first", "second"),
    [
        (0.0, (30, 40), (90, 40)),
        (90.0, (60, 50), (60, 30)),
        (180.0, (90, 40), (30, 40)),
        (270.0, (60, 30), (60, 50)),
    ],
)
def test_cardinal_gradient_direction_matches_visual_ccw_axis(
    angle: float,
    first: tuple[int, int],
    second: tuple[int, int],
) -> None:
    """RASTER-GRADIENT-P10: Cardinal axes preserve the neutral visual direction."""
    result = render_drawing_group(
        DrawingComponentGroup("cardinal", [_rectangle(angle_deg=angle)]),
        Canvas(6, 4, "in"),
        dpi=20,
        supersample=1,
    )

    with result.asset.image() as image:
        first_pixel = image.getpixel(first)
        second_pixel = image.getpixel(second)

    assert first_pixel[0] < second_pixel[0]
    assert first_pixel[1] < second_pixel[1]
    assert first_pixel[2] < second_pixel[2]
    assert first_pixel[3] == second_pixel[3] == 255


@pytest.mark.condition("RASTER-GRADIENT-P10")
def test_oblique_n_stop_gradient_interpolates_and_extends_endpoint_colors() -> None:
    """RASTER-GRADIENT-P10: N-stop colors interpolate and pad missing endpoints."""
    rectangle = _rectangle(
        angle_deg=0.0,
        stops=((0.25, "#ff0000"), (0.5, "#00ff00"), (0.75, "#0000ff")),
    )
    result = render_drawing_group(
        DrawingComponentGroup("n-stop", [rectangle]),
        Canvas(6, 4, "in"),
        dpi=20,
        supersample=1,
    )

    with result.asset.image() as image:
        left = image.getpixel((22, 40))
        middle = image.getpixel((60, 40))
        right = image.getpixel((98, 40))

    assert left[:3] == (255, 0, 0)
    assert middle[1] > 240 and middle[0] < 15 and middle[2] < 15
    assert right[:3] == (0, 0, 255)


@pytest.mark.condition("RASTER-GRADIENT-P10")
def test_gradient_overrides_solid_fill_and_preserves_fill_opacity() -> None:
    """RASTER-GRADIENT-P10: Gradient paint owns RGB while style owns fill alpha."""
    rectangle = _rectangle(
        style=_style(fill="#ff00ff", fill_opacity=0.25),
        stops=((0.0, "#ff0000"), (1.0, "#0000ff")),
    )
    result = render_drawing_group(
        DrawingComponentGroup("alpha", [rectangle]),
        Canvas(6, 4, "in"),
        dpi=20,
        supersample=1,
    )

    with result.asset.image() as image:
        pixel = image.getpixel((60, 40))

    assert pixel[0] in range(124, 132)
    assert pixel[1] == 0
    assert pixel[2] in range(124, 132)
    assert pixel[3] == 64


def _interpolated_rgb(gradient: LinearGradientFill, position: float) -> tuple[int, int, int]:
    stops = gradient.extended_stops()
    for left, right in zip(stops, stops[1:], strict=False):
        if position <= right.offset:
            fraction = (position - left.offset) / (right.offset - left.offset)
            channels = []
            for index in (1, 3, 5):
                start = int(left.color[index : index + 2], 16)
                end = int(right.color[index : index + 2], 16)
                channels.append(round(start + (end - start) * fraction))
            return channels[0], channels[1], channels[2]
    color = stops[-1].color
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def _expected_sharp_gradient_frame(
    rectangle: RectangleDrawing,
    canvas: Canvas,
    *,
    dpi: int,
) -> list[tuple[int, int, int, int]]:
    assert rectangle.fill_gradient is not None
    gradient = LinearGradientFill.from_dict(rectangle.fill_gradient)
    raw_axis = gradient.axis_for_box(rectangle.position, rectangle.width, rectangle.height)
    axis = tuple(value * dpi for value in raw_axis)
    delta_x = axis[2] - axis[0]
    delta_y = axis[3] - axis[1]
    squared_length = delta_x * delta_x + delta_y * delta_y
    left = round(rectangle.position[0] * dpi)
    top = round(rectangle.position[1] * dpi)
    right = round((rectangle.position[0] + rectangle.width) * dpi)
    bottom = round((rectangle.position[1] + rectangle.height) * dpi)
    width = round(canvas.width * dpi)
    height = round(canvas.height * dpi)
    alpha = round(rectangle.style.fill_opacity * 255.0)
    expected: list[tuple[int, int, int, int]] = []
    for y in range(height):
        for x in range(width):
            if left <= x <= right and top <= y <= bottom:
                position = ((x + 0.5 - axis[0]) * delta_x + (y + 0.5 - axis[1]) * delta_y) / squared_length
                red, green, blue = _interpolated_rgb(gradient, min(1.0, max(0.0, position)))
                expected.append((red, green, blue, alpha))
            else:
                expected.append((0, 0, 0, 0))
    return expected


@pytest.mark.condition("RASTER-GRADIENT-P10")
@pytest.mark.parametrize(
    ("position", "width", "height"),
    [((1.0, 1.0), 4.0, 2.0), ((-1.0, -0.5), 3.5, 2.25)],
)
def test_every_sharp_gradient_pixel_matches_independent_piecewise_oracle(
    monkeypatch: pytest.MonkeyPatch,
    position: tuple[float, float],
    width: float,
    height: float,
) -> None:
    """RASTER-GRADIENT-P10: Projection, clipping, tiling, and RGB are exact per pixel."""
    canvas = Canvas(4, 3, "in")
    rectangle = _rectangle(
        position=position,
        width=width,
        height=height,
        angle_deg=37.0,
        stops=((0.0, "#102030"), (0.3, "#f04020"), (0.8, "#20d080"), (1.0, "#f0e0d0")),
        style=_style(fill="#abcdef", fill_opacity=0.6),
    )
    monkeypatch.setattr(raster_renderer, "_GRADIENT_TILE_PIXELS", 5)

    result = render_drawing_group(
        DrawingComponentGroup("oracle", [rectangle]),
        canvas,
        dpi=4,
        supersample=1,
    )

    with result.asset.image() as image:
        actual = list(image.getdata())
    assert actual == _expected_sharp_gradient_frame(rectangle, canvas, dpi=4)


@pytest.mark.condition("RASTER-GRADIENT-P10")
def test_lowest_nonzero_fill_alpha_remains_visible() -> None:
    """RASTER-GRADIENT-P10: Alpha byte one cannot collapse to the zero-opacity no-op."""
    rectangle = _rectangle(style=_style(fill_opacity=1.0 / 255.0))
    result = render_drawing_group(
        DrawingComponentGroup("alpha-one", [rectangle]),
        Canvas(6, 4, "in"),
        dpi=20,
        supersample=1,
    )

    with result.asset.image() as image:
        assert image.getpixel((60, 40))[3] == 1


@pytest.mark.condition("RASTER-GRADIENT-P10")
def test_rounded_gradient_clips_fill_and_paints_stroke_separately() -> None:
    """RASTER-GRADIENT-P10: Rounded corners clip shading without clipping the stroke."""
    rectangle = _rectangle(
        corner_radii=(0.5, 0.75),
        style=_style(stroke="#00ff00", fill="#123456", stroke_width=0.1),
        stops=((0.0, "#ff0000"), (1.0, "#0000ff")),
    )
    result = render_drawing_group(
        DrawingComponentGroup("rounded", [rectangle]),
        Canvas(6, 4, "in"),
        dpi=40,
        supersample=1,
    )

    with result.asset.image() as image:
        corner = image.getpixel((40, 40))
        top_right_corner = image.getpixel((200, 40))
        bottom_right_corner = image.getpixel((200, 120))
        bottom_left_corner = image.getpixel((40, 120))
        center = image.getpixel((120, 80))
        top_stroke = image.getpixel((120, 40))

    assert corner[3] == 0
    assert top_right_corner[3] == 0
    assert bottom_right_corner[3] == 0
    assert bottom_left_corner[3] == 0
    assert center[0] > 80 and center[2] > 80 and center[1] == 0
    assert top_stroke[1] > 240 and top_stroke[0] < 15 and top_stroke[2] < 15


@pytest.mark.condition("RASTER-GRADIENT-P10")
@pytest.mark.parametrize("corner_radii", [(0.0, 0.5), (0.5, 0.0)])
def test_one_zero_corner_radius_preserves_sharp_gradient_bytes(corner_radii: tuple[float, float]) -> None:
    """RASTER-GRADIENT-P10: Either zero radius selects the established sharp mask."""
    sharp = _rectangle(corner_radii=0.0, angle_deg=23.0)
    one_zero = _rectangle(corner_radii=corner_radii, angle_deg=23.0)
    canvas = Canvas(6, 4, "in")

    sharp_result = render_drawing_group(DrawingComponentGroup("sharp", [sharp]), canvas, dpi=20, supersample=1)
    one_zero_result = render_drawing_group(DrawingComponentGroup("one-zero", [one_zero]), canvas, dpi=20, supersample=1)

    assert one_zero_result.asset.data == sharp_result.asset.data


@pytest.mark.condition("RASTER-GRADIENT-P10")
def test_one_pixel_rounded_radius_does_not_collapse_to_sharp_mask() -> None:
    """RASTER-GRADIENT-P10: A positive one-pixel radius still selects rounded clipping."""
    rectangle = _rectangle(corner_radii=(0.25, 0.5))
    result = render_drawing_group(
        DrawingComponentGroup("one-pixel-radius", [rectangle]),
        Canvas(6, 4, "in"),
        dpi=4,
        supersample=1,
    )

    with result.asset.image() as image:
        assert image.getpixel((4, 4))[3] == 0
        assert image.getpixel((12, 8))[3] == 255


@pytest.mark.condition("RASTER-GRADIENT-P10")
@pytest.mark.parametrize("corner_radii", [(0.25, 0.5), (0.5, 0.25)])
def test_gradient_uses_rounded_helper_for_each_positive_pixel_radius(
    monkeypatch: pytest.MonkeyPatch,
    corner_radii: tuple[float, float],
) -> None:
    """RASTER-GRADIENT-P10: Positive pixel radii round both fill mask and stroke."""
    calls = 0
    original = raster_renderer._draw_rounded_rectangle

    def record(*args: object, **kwargs: object) -> None:
        nonlocal calls
        calls += 1
        original(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(raster_renderer, "_draw_rounded_rectangle", record)
    rectangle = _rectangle(
        corner_radii=corner_radii,
        style=_style(stroke="#00ff00", stroke_width=0.25),
    )
    render_drawing_group(
        DrawingComponentGroup("rounded-dispatch", [rectangle]),
        Canvas(6, 4, "in"),
        dpi=4,
        supersample=1,
    )

    assert calls == 2


@pytest.mark.condition("RASTER-GRADIENT-P10")
@pytest.mark.parametrize("corner_radii", [(0.0, 0.5), (0.5, 0.0)])
def test_gradient_skips_rounded_helper_when_either_pixel_radius_is_zero(
    monkeypatch: pytest.MonkeyPatch,
    corner_radii: tuple[float, float],
) -> None:
    """RASTER-GRADIENT-P10: A zero pixel radius takes both sharp fill and stroke paths."""
    calls = 0
    original = raster_renderer._draw_rounded_rectangle

    def record(*args: object, **kwargs: object) -> None:
        nonlocal calls
        calls += 1
        original(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(raster_renderer, "_draw_rounded_rectangle", record)
    rectangle = _rectangle(
        corner_radii=corner_radii,
        style=_style(stroke="#00ff00", stroke_width=0.25),
    )
    render_drawing_group(
        DrawingComponentGroup("sharp-dispatch", [rectangle]),
        Canvas(6, 4, "in"),
        dpi=4,
        supersample=1,
    )

    assert calls == 0


@pytest.mark.condition("RASTER-GRADIENT-P10")
def test_off_canvas_gradient_keeps_full_rectangle_axis() -> None:
    """RASTER-GRADIENT-P10: Clipping does not renormalize the source gradient axis."""
    rectangle = _rectangle(position=(-2.0, 0.5), width=4.0, height=1.0)
    result = render_drawing_group(
        DrawingComponentGroup("off-canvas", [rectangle]),
        Canvas(2, 2, "in"),
        dpi=20,
        supersample=1,
    )

    with result.asset.image() as image:
        left = image.getpixel((1, 20))
        right = image.getpixel((38, 20))

    assert 120 < left[0] < 150
    assert right[0] > 240
    assert left[0] < right[0]


@pytest.mark.condition("RASTER-GRADIENT-P10")
def test_zero_opacity_and_fully_clipped_gradients_are_transparent_noops() -> None:
    """RASTER-GRADIENT-P10: Invisible or disjoint gradient fills paint no pixels."""
    invisible = _rectangle(style=_style(fill_opacity=0.0))
    outside = _rectangle(position=(10.0, 10.0))

    result = render_drawing_group(
        DrawingComponentGroup("noops", [invisible, outside]),
        Canvas(2, 2, "in"),
        dpi=20,
        supersample=1,
    )

    with result.asset.image() as image:
        assert image.getbbox() is None


@pytest.mark.condition("RASTER-GRADIENT-P10")
def test_gradient_tile_partition_does_not_change_png_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASTER-GRADIENT-P10: Tile partitioning is an implementation detail, not output state."""
    group = DrawingComponentGroup("tiles", [_rectangle(angle_deg=37.0)])
    canvas = Canvas(6, 4, "in")
    baseline = render_drawing_group(group, canvas, dpi=20, supersample=1)

    original_fromarray = raster_renderer.Image.fromarray
    tile_pixel_counts: list[int] = []

    def record_tile(array: object) -> object:
        tile_pixel_counts.append(array.shape[0] * array.shape[1])  # type: ignore[attr-defined]
        assert array.shape[2] == 3  # type: ignore[attr-defined]
        return original_fromarray(array)

    monkeypatch.setattr(raster_renderer, "_GRADIENT_TILE_PIXELS", 17)
    monkeypatch.setattr(raster_renderer.Image, "fromarray", record_tile)
    tiled = render_drawing_group(group, canvas, dpi=20, supersample=1)

    assert tiled.asset.data == baseline.asset.data
    assert tiled.manifest == baseline.manifest
    assert tile_pixel_counts
    assert max(tile_pixel_counts) <= 17


@pytest.mark.condition("RASTER-GRADIENT-P10")
def test_zero_opacity_returns_before_interpolation_work(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASTER-GRADIENT-P10: Transparent gradients allocate no projection arrays or masks."""
    surface = raster_renderer.Image.new("RGBA", (4, 4), (0, 0, 0, 0))

    def fail_array(*args: object, **kwargs: object) -> None:
        raise AssertionError("zero opacity must return before interpolation")

    monkeypatch.setattr(raster_renderer.np, "arange", fail_array)
    raster_renderer._render_linear_gradient_rectangle(
        surface,
        (0, 0, 3, 3),
        0,
        0,
        _gradient(),
        (0.0, 0.0, 3.0, 0.0),
        0.0,
    )


@pytest.mark.condition("RASTER-GRADIENT-P10")
def test_disjoint_gradient_returns_before_interpolation_work(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASTER-GRADIENT-P10: Disjointness on either axis short-circuits array work."""
    surface = raster_renderer.Image.new("RGBA", (4, 4), (0, 0, 0, 0))

    def fail_array(*args: object, **kwargs: object) -> None:
        raise AssertionError("disjoint gradient must return before interpolation")

    monkeypatch.setattr(raster_renderer.np, "arange", fail_array)
    raster_renderer._render_linear_gradient_rectangle(
        surface,
        (5, 0, 6, 3),
        0,
        0,
        _gradient(),
        (5.0, 0.0, 6.0, 0.0),
        1.0,
    )
    raster_renderer._render_linear_gradient_rectangle(
        surface,
        (0, 5, 3, 6),
        0,
        0,
        _gradient(),
        (0.0, 5.0, 3.0, 5.0),
        1.0,
    )


@pytest.mark.condition("RASTER-GRADIENT-P10")
@pytest.mark.parametrize("tile_limit", [0, 5])
def test_gradient_tiles_never_exceed_surface_or_configured_limit(
    monkeypatch: pytest.MonkeyPatch,
    tile_limit: int,
) -> None:
    """RASTER-GRADIENT-P10: Extreme clipping and a zero limit still produce bounded destinations."""
    original_alpha_composite = raster_renderer.Image.Image.alpha_composite
    tile_count = 0

    def checked_alpha_composite(self: object, image: object, *args: object, **kwargs: object) -> None:
        nonlocal tile_count
        destination = kwargs.get("dest", (0, 0))
        tile_count += 1
        assert image.width * image.height <= max(1, tile_limit)  # type: ignore[attr-defined]
        assert 0 <= destination[0] and 0 <= destination[1]  # type: ignore[index]
        assert destination[0] + image.width <= self.width  # type: ignore[index,attr-defined]
        assert destination[1] + image.height <= self.height  # type: ignore[index,attr-defined]
        original_alpha_composite(self, image, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(raster_renderer, "_GRADIENT_TILE_PIXELS", tile_limit)
    monkeypatch.setattr(raster_renderer.Image.Image, "alpha_composite", checked_alpha_composite)
    rectangle = _rectangle(position=(-1.0, -0.5), width=6.0, height=4.0, angle_deg=31.0)
    render_drawing_group(
        DrawingComponentGroup("tile-bounds", [rectangle]),
        Canvas(4, 3, "in"),
        dpi=4,
        supersample=1,
    )

    assert tile_count > 0


@pytest.mark.condition("RASTER-GRADIENT-P10")
def test_single_pixel_gradient_intersection_is_not_discarded() -> None:
    """RASTER-GRADIENT-P10: Equal clipped bounds still describe one paintable pixel."""
    rectangle = _rectangle(position=(1.95, 1.95), width=0.01, height=0.01)
    result = render_drawing_group(
        DrawingComponentGroup("one-pixel", [rectangle]),
        Canvas(2, 2, "in"),
        dpi=20,
        supersample=1,
    )

    with result.asset.image() as image:
        assert image.getpixel((39, 39))[3] == 255


@pytest.mark.condition("RASTER-GRADIENT-P10")
def test_unrepresentable_gradient_axis_fails_before_surface_allocation(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASTER-GRADIENT-P10: Derived axis overflow cannot reach NumPy or Pillow."""
    rectangle = _rectangle(position=(0.0, 0.0), width=1e200, height=1.0)

    def fail_allocation(*args: object, **kwargs: object) -> None:
        raise AssertionError("surface allocation must not run")

    monkeypatch.setattr(raster_renderer.Image, "new", fail_allocation)
    with pytest.raises(ValueError, match="gradient axis length must be finite"):
        render_drawing_group(
            DrawingComponentGroup("overflow", [rectangle]),
            Canvas(6, 4, "in"),
            dpi=20,
        )


@pytest.mark.condition("RASTER-GRADIENT-P10")
def test_scaled_gradient_axis_coordinates_must_remain_finite(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASTER-GRADIENT-P10: Coordinate overflow fails before image allocation."""
    rectangle = _rectangle(position=(1e308, 0.0), width=1.0, height=1.0)

    def fail_allocation(*args: object, **kwargs: object) -> None:
        raise AssertionError("surface allocation must not run")

    monkeypatch.setattr(raster_renderer.Image, "new", fail_allocation)
    with pytest.raises(ValueError, match="gradient axis must be finite"):
        render_drawing_group(
            DrawingComponentGroup("coordinate-overflow", [rectangle]),
            Canvas(6, 4, "in"),
            dpi=20,
        )


@pytest.mark.condition("RASTER-GRADIENT-P10")
def test_defensive_zero_length_axis_fails_before_surface_allocation(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASTER-GRADIENT-P10: A violated neutral-axis contract cannot reach rendering."""
    rectangle = _rectangle()

    def fail_allocation(*args: object, **kwargs: object) -> None:
        raise AssertionError("surface allocation must not run")

    monkeypatch.setattr(LinearGradientFill, "axis_for_box", lambda *args: (1.0, 2.0, 1.0, 2.0))
    monkeypatch.setattr(raster_renderer.Image, "new", fail_allocation)
    with pytest.raises(ValueError, match="gradient axis must have positive length"):
        render_drawing_group(
            DrawingComponentGroup("zero-axis", [rectangle]),
            Canvas(6, 4, "in"),
            dpi=20,
        )


@pytest.mark.condition("RASTER-GRADIENT-P10")
def test_subpixel_valid_gradient_axis_is_accepted() -> None:
    """RASTER-GRADIENT-P10: Positive axes below one squared pixel remain valid."""
    rectangle = _rectangle(position=(0.0, 0.0), width=0.01, height=0.01)
    result = render_drawing_group(
        DrawingComponentGroup("subpixel-axis", [rectangle]),
        Canvas(1, 1, "in"),
        dpi=4,
        supersample=1,
    )

    with result.asset.image() as image:
        assert image.getpixel((0, 0))[3] == 255


@pytest.mark.condition("RASTER-GRADIENT-P10")
def test_live_gradient_mutation_fails_before_surface_allocation(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASTER-GRADIENT-P10: Mutable payload corruption is rejected before allocation."""
    rectangle = _rectangle()
    assert rectangle.fill_gradient is not None
    rectangle.fill_gradient["stops"][0][1] = "bad"  # type: ignore[index]

    def fail_allocation(*args: object, **kwargs: object) -> None:
        raise AssertionError("surface allocation must not run")

    monkeypatch.setattr(raster_renderer.Image, "new", fail_allocation)
    with pytest.raises(ValueError, match="gradient stop color"):
        render_drawing_group(
            DrawingComponentGroup("mutated", [rectangle]),
            Canvas(6, 4, "in"),
            dpi=20,
        )


@pytest.mark.condition("RASTER-GRADIENT-P10")
def test_gradient_composes_with_baird_using_the_explicit_substrate() -> None:
    """RASTER-GRADIENT-P10: Clean gradient alpha feeds the standalone scan path."""
    group = DrawingComponentGroup(
        "baird-gradient",
        [_rectangle(style=_style(fill_opacity=0.5), stops=((0.0, "#ff0000"), (1.0, "#0000ff")))],
    )
    result = render_and_degrade_drawing_group(
        group,
        Canvas(6, 4, "in"),
        BairdParams.clean(),
        seed=11,
        background_rgb=(10, 20, 30),
        dpi=20,
        render_supersample=1,
    )

    with result.clean.asset.image() as clean, result.degraded.asset.image() as degraded:
        clean_pixel = clean.getpixel((60, 40))
        degraded_pixel = degraded.getpixel((60, 40))

    assert clean_pixel[3] in range(127, 129)
    assert degraded_pixel[0] > 10
    assert degraded_pixel[2] > 30
    assert result.degraded.manifest["background_rgb"] == [10, 20, 30]
