"""RASTER-ROUNDED-RECT-P8 conditions for dependency-free raster output."""

from __future__ import annotations

from uuid import uuid4

import pytest
from PIL import Image

import InkGen.raster_renderer as raster_renderer
from InkGen import (
    BairdParams,
    Canvas,
    DrawingComponentGroup,
    DrawingStyle,
    RectangleDrawing,
    render_and_degrade_drawing_group,
    render_drawing_group,
)


def _style(
    *,
    fill: str = "none",
    stroke: str = "none",
    stroke_width: float = 0.0,
    fill_opacity: float = 1.0,
    stroke_opacity: float = 1.0,
) -> DrawingStyle:
    return DrawingStyle(
        f"raster_rounded_rect_{uuid4().hex}",
        fill=fill,
        stroke=stroke,
        stroke_width=stroke_width,
        fill_opacity=fill_opacity,
        stroke_opacity=stroke_opacity,
    )


class _RecordingDraw:
    """Record the exact primitive calls used to paint an elliptical rectangle."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def rectangle(self, *args: object, **kwargs: object) -> None:
        self.calls.append(("rectangle", args, kwargs))

    def pieslice(self, *args: object, **kwargs: object) -> None:
        self.calls.append(("pieslice", args, kwargs))

    def line(self, *args: object, **kwargs: object) -> None:
        self.calls.append(("line", args, kwargs))

    def arc(self, *args: object, **kwargs: object) -> None:
        self.calls.append(("arc", args, kwargs))


@pytest.mark.condition("RASTER-ROUNDED-RECT-P8")
def test_elliptical_rounded_rectangle_emits_exact_fill_and_stroke_operations() -> None:
    """P8: Asymmetric radii map to four quarter ellipses and cardinal edges."""
    draw = _RecordingDraw()
    fill = (10, 20, 30, 128)
    stroke = (40, 50, 60, 255)

    raster_renderer._draw_rounded_rectangle(  # noqa: SLF001
        draw,
        (10, 20, 50, 80),
        10,
        20,
        fill=fill,
        stroke=stroke,
        stroke_width=3,
    )

    assert draw.calls == [
        ("rectangle", ((20, 20, 40, 80),), {"fill": fill}),
        ("rectangle", ((10, 40, 50, 60),), {"fill": fill}),
        ("pieslice", ((10, 20, 30, 60), 180, 270), {"fill": fill}),
        ("pieslice", ((30, 20, 50, 60), 270, 360), {"fill": fill}),
        ("pieslice", ((30, 40, 50, 80), 0, 90), {"fill": fill}),
        ("pieslice", ((10, 40, 30, 80), 90, 180), {"fill": fill}),
        ("line", ([(20, 20), (40, 20)],), {"fill": stroke, "width": 3}),
        ("line", ([(50, 40), (50, 60)],), {"fill": stroke, "width": 3}),
        ("line", ([(40, 80), (20, 80)],), {"fill": stroke, "width": 3}),
        ("line", ([(10, 60), (10, 40)],), {"fill": stroke, "width": 3}),
        ("arc", ((10, 20, 30, 60), 180, 270), {"fill": stroke, "width": 3}),
        ("arc", ((30, 20, 50, 60), 270, 360), {"fill": stroke, "width": 3}),
        ("arc", ((30, 40, 50, 80), 0, 90), {"fill": stroke, "width": 3}),
        ("arc", ((10, 40, 30, 80), 90, 180), {"fill": stroke, "width": 3}),
    ]

    stroke_only = _RecordingDraw()
    raster_renderer._draw_rounded_rectangle(  # noqa: SLF001
        stroke_only,
        (10, 20, 50, 80),
        10,
        20,
        fill=None,
        stroke=stroke,
        stroke_width=3,
    )
    assert [call[0] for call in stroke_only.calls] == ["line"] * 4 + ["arc"] * 4

    unpainted = _RecordingDraw()
    raster_renderer._draw_rounded_rectangle(  # noqa: SLF001
        unpainted,
        (10, 20, 50, 80),
        10,
        20,
        fill=None,
        stroke=None,
        stroke_width=0,
    )
    assert unpainted.calls == []


@pytest.mark.condition("RASTER-ROUNDED-RECT-P8")
def test_public_render_preserves_transparent_corners_and_filled_center() -> None:
    """P8: Rounded corners omit corner pixels without removing the center fill."""
    rounded = RectangleDrawing((1, 1), 4, 2, (1.0, 0.75), _style(fill="#ff0000"))

    result = render_drawing_group(
        DrawingComponentGroup("rounded", [rounded]),
        Canvas(6, 4, "in"),
        dpi=20,
        supersample=4,
    )

    with result.asset.image() as image:
        assert image.getpixel((20, 20))[3] == 0
        assert image.getpixel((60, 40)) == (255, 0, 0, 255)
        assert image.getpixel((20, 40))[0] > 200


@pytest.mark.condition("RASTER-ROUNDED-RECT-P8")
def test_boundary_radii_produce_an_elliptical_capsule() -> None:
    """P8: Half-width and half-height radii remain valid at the closed boundary."""
    capsule = RectangleDrawing((1, 1), 4, 2, (2.0, 1.0), _style(fill="#0000ff"))

    result = render_drawing_group(
        DrawingComponentGroup("capsule", [capsule]),
        Canvas(6, 4, "in"),
        dpi=20,
        supersample=4,
    )

    with result.asset.image() as image:
        assert image.getpixel((20, 20))[3] == 0
        assert image.getpixel((60, 20))[2] > 200
        assert image.getpixel((60, 40))[2] > 200


@pytest.mark.condition("RASTER-ROUNDED-RECT-P8")
def test_rounded_rectangle_fill_alpha_composites_over_explicit_background() -> None:
    """P8: Rounded fill alpha uses the renderer's source-over contract."""
    rounded = RectangleDrawing(
        (1, 1),
        4,
        2,
        0.5,
        _style(fill="#ff0000", fill_opacity=0.5),
    )

    result = render_drawing_group(
        DrawingComponentGroup("rounded alpha", [rounded]),
        Canvas(6, 4, "in"),
        dpi=20,
        supersample=2,
        background_rgba=(0, 0, 255, 255),
    )

    with result.asset.image() as image:
        inside = image.getpixel((60, 40))
        outside = image.getpixel((20, 20))
    assert inside[0] in range(127, 129)
    assert inside[2] in range(127, 129)
    assert inside[3] == 255
    assert outside == (0, 0, 255, 255)


@pytest.mark.condition("RASTER-ROUNDED-RECT-P8")
def test_one_zero_radius_preserves_sharp_rectangle_semantics(monkeypatch: pytest.MonkeyPatch) -> None:
    """P8: If either SVG-style radius is zero, the sharp branch remains exact."""
    recorder = _RecordingDraw()
    monkeypatch.setattr(raster_renderer.ImageDraw, "Draw", lambda surface: recorder)
    zero_x = RectangleDrawing((1, 2), 3, 4, (0.0, 1.0), _style(fill="#102030"))
    zero_y = RectangleDrawing((2, 3), 4, 3, (1.0, 0.0), _style(fill="#405060"))

    raster_renderer._render_component(Image.new("RGBA", (1, 1)), zero_x, 10.0)  # noqa: SLF001
    raster_renderer._render_component(Image.new("RGBA", (1, 1)), zero_y, 10.0)  # noqa: SLF001

    assert recorder.calls == [
        ("rectangle", ((10, 20, 40, 60),), {"fill": (16, 32, 48, 255), "outline": None, "width": 0}),
        ("rectangle", ((20, 30, 60, 60),), {"fill": (64, 80, 96, 255), "outline": None, "width": 0}),
    ]


@pytest.mark.condition("RASTER-ROUNDED-RECT-P8")
def test_pixel_radius_mapping_uses_exact_box_extents_and_half_extent_clamps(monkeypatch: pytest.MonkeyPatch) -> None:
    """P8: Odd and even pixel extents pin radius scaling and half-size bounds."""
    captured: list[tuple[tuple[int, int, int, int], int, int]] = []

    def capture(
        draw: object,
        box: tuple[int, int, int, int],
        radius_x: int,
        radius_y: int,
        **paint: object,
    ) -> None:
        captured.append((box, radius_x, radius_y))

    monkeypatch.setattr(raster_renderer, "_draw_rounded_rectangle", capture)
    odd = RectangleDrawing((1.3, 2.7), 0.3, 0.3, 0.15, _style(fill="#000000"))
    even = RectangleDrawing((1.3, 2.7), 0.4, 0.4, 0.2, _style(fill="#000000"))
    thin_radius = RectangleDrawing((1.0, 2.0), 2.0, 2.0, 0.1, _style(fill="#000000"))

    raster_renderer._render_component(Image.new("RGBA", (1, 1)), odd, 10.0)  # noqa: SLF001
    raster_renderer._render_component(Image.new("RGBA", (1, 1)), even, 10.0)  # noqa: SLF001
    raster_renderer._render_component(Image.new("RGBA", (1, 1)), thin_radius, 2.0)  # noqa: SLF001

    assert captured == [
        ((13, 27, 16, 30), 1, 1),
        ((13, 27, 17, 31), 2, 2),
        ((2, 4, 6, 8), 1, 1),
    ]


@pytest.mark.condition("RASTER-ROUNDED-RECT-P8")
def test_subpixel_rounded_radii_collapse_to_the_sharp_pixel_domain(monkeypatch: pytest.MonkeyPatch) -> None:
    """P8: Unrepresentable rounded pixels fall back without invalid Pillow boxes."""
    recorder = _RecordingDraw()
    monkeypatch.setattr(raster_renderer.ImageDraw, "Draw", lambda surface: recorder)
    rectangle = RectangleDrawing((0, 0), 0.04, 0.04, 0.02, _style(fill="#102030"))

    raster_renderer._render_component(Image.new("RGBA", (1, 1)), rectangle, 10.0)  # noqa: SLF001

    assert recorder.calls == [("rectangle", ((0, 0, 0, 0),), {"fill": (16, 32, 48, 255), "outline": None, "width": 0})]


@pytest.mark.condition("RASTER-ROUNDED-RECT-P8")
def test_live_corner_radius_mutation_fails_before_surface_allocation(monkeypatch: pytest.MonkeyPatch) -> None:
    """P8: Mutated radii are revalidated before Pillow allocates a canvas."""
    rectangle = RectangleDrawing((0, 0), 2, 2, 0.5, _style(fill="#000000"))
    object.__setattr__(rectangle, "corner_radii", (2.0, 0.5))
    allocated = False

    def fail_if_allocated(*args: object, **kwargs: object) -> Image.Image:
        nonlocal allocated
        allocated = True
        raise AssertionError("surface allocation must follow domain validation")

    monkeypatch.setattr(raster_renderer.Image, "new", fail_if_allocated)
    with pytest.raises(ValueError, match="half the width and height"):
        render_drawing_group(DrawingComponentGroup("mutated", [rectangle]), Canvas(2, 2, "in"), dpi=10)
    assert allocated is False


@pytest.mark.condition("RASTER-ROUNDED-RECT-P8")
def test_rounded_rectangle_reaches_public_clean_to_baird_path() -> None:
    """P8: The standalone degradation path consumes rounded clean geometry."""
    rectangle = RectangleDrawing((0.2, 0.2), 0.6, 0.6, 0.2, _style(fill="#000000"))

    result = render_and_degrade_drawing_group(
        DrawingComponentGroup("rounded baird", [rectangle]),
        Canvas(1, 1, "in"),
        BairdParams.clean(),
        seed=7,
        background_rgb=(255, 255, 255),
        dpi=20,
        render_supersample=2,
    )

    assert (result.clean.asset.width, result.clean.asset.height) == (20, 20)
    assert (result.degraded.asset.width, result.degraded.asset.height) == (20, 20)
    with result.clean.asset.image() as clean:
        assert clean.getpixel((4, 4))[3] == 0
        assert clean.getpixel((10, 10))[3] == 255
