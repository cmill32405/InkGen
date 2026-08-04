"""Fast deterministic witnesses for raster line-dash P13 mutation workers."""

from __future__ import annotations

import math
from itertools import count

from PIL import Image, ImageDraw

from InkGen import raster_renderer
from InkGen.drawing_components import LineDrawing
from InkGen.raster_renderer import (
    _dash_cursor,
    _draw_dashed_line,
    _draw_line_component,
    _line_dash_segments,
    _next_dash_slot,
    _nonnegative_finite_number,
    _point_along_line,
    _validated_line_dash,
)
from InkGen.style import DrawingStyle

_STYLE_IDS = count()
STROKE = (16, 32, 48, 128)


def _style(pattern: tuple[float, ...] = (), offset: float = 0.0) -> DrawingStyle:
    return DrawingStyle(
        f"mutation-dash-{next(_STYLE_IDS)}",
        stroke="#102030",
        fill="none",
        stroke_width=1.0,
        stroke_dasharray=pattern,
        stroke_dash_offset=offset,
    )


def _intervals(
    length: float,
    pattern: tuple[float, ...],
    offset: float = 0.0,
) -> list[tuple[float, float]]:
    return [(a[0], b[0]) for a, b in _line_dash_segments((0.0, 0.0), (length, 0.0), pattern, offset)]


def _raises(error: type[Exception], call: object) -> None:
    try:
        call()  # type: ignore[operator]
    except error:
        return
    raise AssertionError(f"expected {error.__name__}")


def _assert_validation() -> None:
    assert _validated_line_dash(_style()) is None
    assert _validated_line_dash(_style((2.0, 1.0), 7.0)) == ((2.0, 1.0), 7.0)
    assert _validated_line_dash(_style((2.0, 1.0, 3.0))) == ((2.0, 1.0, 3.0, 2.0, 1.0, 3.0), 0.0)
    assert _validated_line_dash(_style((2.0, 1.0, 3.0, 4.0))) == ((2.0, 1.0, 3.0, 4.0), 0.0)

    for value in (True, "1", object()):
        _raises(TypeError, lambda value=value: _nonnegative_finite_number(value, "value"))
    for value in (-1.0, math.nan, math.inf, -math.inf):
        _raises(ValueError, lambda value=value: _nonnegative_finite_number(value, "value"))
    assert _nonnegative_finite_number(0, "value") == 0.0
    assert _nonnegative_finite_number(2.5, "value") == 2.5

    corruptions = [
        ("_stroke_dasharray", "1,2", TypeError),
        ("_stroke_dasharray", b"\x01\x02", TypeError),
        ("_stroke_dasharray", object(), TypeError),
        ("_stroke_dasharray", (True, 1.0), TypeError),
        ("_stroke_dasharray", (-1.0, 1.0), ValueError),
        ("_stroke_dasharray", (math.nan, 1.0), ValueError),
        ("_stroke_dasharray", (0.0, 0.0), ValueError),
        ("_stroke_dash_offset", True, TypeError),
        ("_stroke_dash_offset", math.inf, ValueError),
        ("_stroke_dash_offset", -1.0, ValueError),
    ]
    for attribute, value, error in corruptions:
        style = _style((1.0, 1.0))
        setattr(style, attribute, value)
        _raises(error, lambda style=style: _validated_line_dash(style))

    orphan = _style()
    orphan._stroke_dash_offset = 1.0
    _raises(ValueError, lambda: _validated_line_dash(orphan))


def _assert_segmentation() -> None:
    assert _intervals(10.0, (2.0, 1.0)) == [(0.0, 2.0), (3.0, 5.0), (6.0, 8.0), (9.0, 10.0)]
    assert _intervals(10.0, (2.0, 1.0), 1.0) == [(0.0, 1.0), (2.0, 4.0), (5.0, 7.0), (8.0, 10.0)]
    assert _intervals(10.0, (2.0, 1.0), 4.0) == _intervals(10.0, (2.0, 1.0), 1.0)
    assert _intervals(4.0, (1.0, 3.0), 2.0) == [(2.0, 3.0)]
    assert _intervals(1.0, (1.0, 1.0), 1_000_000_000.0) == [(0.0, 1.0)]
    assert _intervals(10.0, (2.0, 1.0), 2.0) == [(1.0, 3.0), (4.0, 6.0), (7.0, 9.0)]
    assert _intervals(10.0, (0.0, 2.0)) == []
    assert _intervals(5.0, (2.0, 0.0)) == [(0.0, 2.0), (2.0, 4.0), (4.0, 5.0)]
    assert _intervals(6.0, (1.0, 1.0, 2.0, 1.0)) == [(0.0, 1.0), (2.0, 4.0), (5.0, 6.0)]
    assert _line_dash_segments((2.0, 3.0), (2.0, 3.0), (1.0, 1.0), 0.0) == []

    diagonal = _line_dash_segments((1.0, 2.0), (4.0, 6.0), (2.0, 1.0), 0.0)
    assert diagonal == [((1.0, 2.0), (2.2, 3.6)), ((2.8, 4.4), (4.0, 6.0))]
    reverse = _line_dash_segments((10.0, 0.0), (0.0, 0.0), (2.0, 1.0), 0.0)
    assert reverse[0] == ((10.0, 0.0), (8.0, 0.0))
    assert reverse[-1] == ((1.0, 0.0), (0.0, 0.0))

    _raises(ValueError, lambda: _line_dash_segments((0.0, 0.0), (1.0, 0.0), (0.000001, 0.000001), 0.0))
    original_limit = raster_renderer._MAX_DASH_STEPS
    raster_renderer._MAX_DASH_STEPS = 3
    try:
        assert _intervals(3.0, (1.0, 1.0)) == [(0.0, 1.0), (2.0, 3.0)]
        _raises(ValueError, lambda: _intervals(4.0, (1.0, 1.0)))
    finally:
        raster_renderer._MAX_DASH_STEPS = original_limit
    assert _dash_cursor((0.0, 2.0), 0.0) == (1, 2.0)
    assert _dash_cursor((2.0, 1.0), 1.0) == (0, 1.0)
    assert _dash_cursor((2.0, 1.0), 2.0) == (1, 1.0)
    assert _dash_cursor((0.5, 0.5), 0.75) == (1, 0.25)
    assert _dash_cursor((0.5, 0.25, 1.0, 0.75), 1.0) == (2, 0.75)
    assert _next_dash_slot((2.0, 1.0), 0, 0.5) == (0, 0.5)
    assert _next_dash_slot((2.0, 0.0, 1.0, 1.0), 0, 0.0) == (2, 1.0)
    assert _point_along_line((1.0, 2.0), 3.0, 4.0, 0.4) == (2.2, 3.6)

    for length in (0.01, 0.5, 3.0, 11.0):
        for pattern in ((0.25, 0.5), (1.0, 2.0), (0.0, 1.0), (1.0, 0.0)):
            for offset in (0.0, 0.1, 10.0):
                segments = _line_dash_segments((0.0, 2.0), (length, 2.0), pattern, offset)
                previous_end = 0.0
                for start, end in segments:
                    assert 0.0 <= start[0] < end[0] <= length
                    assert start[0] >= previous_end
                    assert start[1] == end[1] == 2.0
                    previous_end = end[0]


def _assert_paint_wiring() -> None:
    surface = Image.new("RGBA", (14, 12), (0, 0, 0, 0))
    draw = ImageDraw.Draw(surface)
    _draw_dashed_line(draw, (0.0, 0.5), (1.0, 0.5), 10.0, STROKE, 1, (0.2, 0.2), 0.0)
    assert surface.getpixel((1, 5)) == STROKE
    assert surface.getpixel((3, 5)) == (0, 0, 0, 0)

    solid_surface = Image.new("RGBA", (14, 12), (0, 0, 0, 0))
    solid = LineDrawing((0.0, 0.5), (1.0, 0.5), _style())
    _draw_line_component(ImageDraw.Draw(solid_surface), solid, 10.0, STROKE, 1)
    assert solid_surface.getpixel((3, 5)) == STROKE

    dashed_surface = Image.new("RGBA", (14, 12), (0, 0, 0, 0))
    dashed = LineDrawing((0.0, 0.5), (1.0, 0.5), _style((0.2, 0.2)))
    _draw_line_component(ImageDraw.Draw(dashed_surface), dashed, 10.0, STROKE, 1)
    assert dashed_surface.getpixel((1, 5)) == STROKE
    assert dashed_surface.getpixel((3, 5)) == (0, 0, 0, 0)

    invisible = Image.new("RGBA", (14, 12), (0, 0, 0, 0))
    _draw_line_component(ImageDraw.Draw(invisible), dashed, 10.0, None, 0)
    assert invisible.getbbox() is None


def main() -> None:
    """Run all deterministic P13 mutation witnesses."""
    _assert_validation()
    _assert_segmentation()
    _assert_paint_wiring()


if __name__ == "__main__":
    main()
