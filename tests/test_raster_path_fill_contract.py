"""RASTER-PATH-FILL-P12 conditions for nonzero-winding path fills."""

from __future__ import annotations

from uuid import uuid4

import pytest
from PIL import Image

import InkGen.raster_renderer as raster_renderer
from InkGen.baird import BairdParams
from InkGen.boundary import Canvas
from InkGen.component import PathCommand
from InkGen.drawing_components import DrawingComponentGroup, PathDrawing
from InkGen.raster_renderer import render_and_degrade_drawing_group, render_drawing_group
from InkGen.style import DrawingStyle


def _style(
    *,
    fill: str = "#c02010",
    fill_opacity: float = 1.0,
    stroke: str = "none",
    stroke_opacity: float = 1.0,
    stroke_width: float = 0.0,
) -> DrawingStyle:
    return DrawingStyle(
        f"raster_path_fill_{uuid4().hex}",
        fill=fill,
        fill_opacity=fill_opacity,
        stroke=stroke,
        stroke_opacity=stroke_opacity,
        stroke_width=stroke_width,
    )


def _path(style: DrawingStyle, subpaths: list[list[tuple[float, float]]], *, close: bool = False) -> PathDrawing:
    commands: list[PathCommand] = []
    for points in subpaths:
        commands.append(PathCommand("M", [points[0]]))
        commands.append(PathCommand("L", points[1:]))
        if close:
            commands.append(PathCommand("Z"))
    return PathDrawing(style, commands)


def _render(path: PathDrawing, *, width: float = 10, height: float = 10, dpi: float = 1) -> Image.Image:
    result = render_drawing_group(
        DrawingComponentGroup("path-fill", [path]),
        Canvas(width, height, "in"),
        dpi=dpi,
        supersample=1,
    )
    with result.asset.image() as image:
        return image.copy()


@pytest.mark.condition("RASTER-PATH-FILL-P12")
@pytest.mark.parametrize("close", [False, True])
def test_path_fill_implicitly_closes_open_subpaths(close: bool) -> None:
    """P12: Open and explicit closure have identical fill geometry."""
    path = _path(_style(), [[(1, 1), (8, 1), (1, 8)]], close=close)

    image = _render(path)

    assert image.getpixel((2, 2)) == (192, 32, 16, 255)
    assert image.getpixel((8, 8)) == (0, 0, 0, 0)


@pytest.mark.condition("RASTER-PATH-FILL-P12")
def test_nonzero_winding_keeps_same_orientation_nested_subpath_filled() -> None:
    """P12: Equal nonzero windings add instead of creating an even-odd hole."""
    clockwise = [
        [(1, 1), (9, 1), (9, 9), (1, 9)],
        [(3, 3), (7, 3), (7, 7), (3, 7)],
    ]

    image = _render(_path(_style(), clockwise))

    assert image.getpixel((5, 5)) == (192, 32, 16, 255)


@pytest.mark.condition("RASTER-PATH-FILL-P12")
def test_nonzero_winding_opposite_orientation_creates_hole() -> None:
    """P12: Opposite nested winding cancels to a transparent hole."""
    opposite = [
        [(1, 1), (9, 1), (9, 9), (1, 9)],
        [(3, 3), (3, 7), (7, 7), (7, 3)],
    ]

    image = _render(_path(_style(), opposite))

    assert image.getpixel((2, 2)) == (192, 32, 16, 255)
    assert image.getpixel((5, 5)) == (0, 0, 0, 0)


@pytest.mark.condition("RASTER-PATH-FILL-P12")
def test_self_intersecting_path_fills_only_nonzero_lobes() -> None:
    """P12: Self-intersections are decided by winding, not polygon convexity."""
    bow_tie = [[(1, 1), (9, 9), (1, 9), (9, 1)]]

    image = _render(_path(_style(), bow_tie))

    assert image.getpixel((5, 2)) == (192, 32, 16, 255)
    assert image.getpixel((2, 5)) == (0, 0, 0, 0)


@pytest.mark.condition("RASTER-PATH-FILL-P12")
def test_path_fill_clips_to_canvas_without_changing_source_winding() -> None:
    """P12: Off-canvas edges still determine the visible nonzero interior."""
    path = _path(_style(fill="#102030"), [[(-5, -5), (15, -5), (15, 15), (-5, 15)]])

    image = _render(path)

    assert image.getbbox() == (0, 0, 10, 10)
    assert image.getpixel((0, 0)) == (16, 32, 48, 255)
    assert image.getpixel((9, 9)) == (16, 32, 48, 255)


@pytest.mark.condition("RASTER-PATH-FILL-P12")
@pytest.mark.parametrize(
    "points",
    [
        [(-8, 2), (-4, 2), (-4, 8), (-8, 8)],
        [(2, -8), (8, -8), (8, -4), (2, -4)],
    ],
)
def test_fully_off_canvas_path_fill_is_transparent_noop(
    points: list[tuple[float, float]],
) -> None:
    """P12: A contour with no canvas intersection allocates no local mask."""
    assert _render(_path(_style(), [points])).getbbox() is None


@pytest.mark.condition("RASTER-PATH-FILL-P12")
@pytest.mark.parametrize(
    "commands",
    [None, [PathCommand("M", [(2, 2)])]],
)
def test_empty_and_move_only_filled_paths_are_transparent_noops(
    commands: list[PathCommand] | None,
) -> None:
    """P12: Fill paint cannot invent an area without a contour."""
    path = PathDrawing(_style(), commands)

    assert _render(path).getbbox() is None


@pytest.mark.condition("RASTER-PATH-FILL-P12")
def test_degenerate_path_fill_is_transparent_noop() -> None:
    """P12: Collinear and move-only subpaths do not invent area."""
    path = _path(_style(), [[(1, 1), (5, 1), (8, 1)]])

    assert _render(path).getbbox() is None


@pytest.mark.condition("RASTER-PATH-FILL-P12")
def test_separated_subpaths_leave_inactive_scanlines_transparent() -> None:
    """P12: Empty scanlines between disjoint contours remain transparent."""
    separated = [
        [(1, 1), (4, 1), (4, 3), (1, 3)],
        [(6, 7), (9, 7), (9, 9), (6, 9)],
    ]

    image = _render(_path(_style(), separated))

    assert image.getpixel((2, 2)) == (192, 32, 16, 255)
    assert image.getpixel((5, 5)) == (0, 0, 0, 0)
    assert image.getpixel((7, 8)) == (192, 32, 16, 255)


@pytest.mark.condition("RASTER-PATH-FILL-P12")
def test_fill_then_stroke_uses_source_over_composition() -> None:
    """P12: A translucent stroke composites over, rather than replaces, fill."""
    style = _style(
        fill="#ff0000",
        fill_opacity=0.5,
        stroke="#0000ff",
        stroke_opacity=0.5,
        stroke_width=1.0,
    )
    path = _path(style, [[(1, 1), (8, 1), (8, 8), (1, 8)]], close=True)

    image = _render(path)

    assert image.getpixel((1, 1)) == (85, 0, 170, 192)
    assert image.getpixel((4, 4)) == (255, 0, 0, 128)


@pytest.mark.condition("RASTER-PATH-FILL-P12")
def test_curved_filled_path_uses_sampled_geometry() -> None:
    """P12: Existing sampled curve commands participate in the fill boundary."""
    path = PathDrawing(
        _style(fill="#204060"),
        [
            PathCommand("M", [(1, 5)]),
            PathCommand("Q", [(5, 0), (9, 5)]),
            PathCommand("Q", [(5, 10), (1, 5)]),
        ],
    )

    image = _render(path)

    assert image.getpixel((5, 5)) == (32, 64, 96, 255)
    assert image.getpixel((0, 0)) == (0, 0, 0, 0)


@pytest.mark.condition("RASTER-PATH-FILL-P12")
def test_path_fill_reaches_public_baird_composition() -> None:
    """P12: Filled paths reach both clean and degraded public assets."""
    result = render_and_degrade_drawing_group(
        DrawingComponentGroup("filled", [_path(_style(), [[(1, 1), (4, 1), (4, 4), (1, 4)]])]),
        Canvas(5, 5, "in"),
        BairdParams.clean(),
        seed=17,
        background_rgb=(245, 246, 247),
        dpi=4,
        render_supersample=2,
    )

    with result.clean.asset.image() as clean:
        assert clean.getbbox() is not None
    with result.degraded.asset.image() as degraded:
        assert degraded.mode == "RGB"
        assert degraded.size == (20, 20)


@pytest.mark.condition("RASTER-PATH-FILL-P12")
def test_scaled_path_overflow_fails_before_surface_allocation(monkeypatch: pytest.MonkeyPatch) -> None:
    """P12: Finite source coordinates that overflow pixel space fail early."""
    path = _path(_style(), [[(1e308, 1), (1e308, 2), (1e308, 3)]])
    monkeypatch.setattr(raster_renderer.Image, "new", lambda *args, **kwargs: pytest.fail("surface allocated"))

    with pytest.raises(ValueError, match="raster path geometry must remain finite after scaling"):
        render_drawing_group(
            DrawingComponentGroup("overflow", [path]),
            Canvas(2, 2, "in"),
            dpi=300,
        )
