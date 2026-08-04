"""Fast deterministic witnesses for raster line-cap P14 mutation workers."""

from __future__ import annotations

import math
from itertools import count

from PIL import Image, ImageDraw

from InkGen import raster_renderer
from InkGen.drawing_components import LineDrawing, RectangleDrawing
from InkGen.raster_renderer import (
    _draw_capped_line_component,
    _draw_capped_segment,
    _draw_dispatched_line_component,
    _line_cap_dash_geometry,
    _square_cap_polygon,
    _unit_tangent,
    _validate_raster_stroke_style,
    _validated_line_cap,
    _validated_line_dash,
    _zero_length_dash_centers,
)
from InkGen.style import DrawingStyle

_STYLE_IDS = count()
STROKE = (16, 32, 48, 128)


def _style(
    line_cap: str = "butt",
    *,
    pattern: tuple[float, ...] = (),
    offset: float = 0.0,
    stroke: str = "#102030",
) -> DrawingStyle:
    return DrawingStyle(
        f"mutation-cap-{next(_STYLE_IDS)}",
        stroke=stroke,
        fill="none",
        stroke_width=4.0,
        stroke_dasharray=pattern,
        stroke_dash_offset=offset,
        stroke_linecap=line_cap,
    )


def _raises(error: type[Exception], call: object) -> None:
    try:
        call()  # type: ignore[operator]
    except error:
        return
    raise AssertionError(f"expected {error.__name__}")


def _assert_validation() -> None:
    for value in ("butt", "round", "square"):
        assert _validated_line_cap(_style(value)) == value
    invalid_type = _style()
    invalid_type._stroke_linecap = object()
    _raises(TypeError, lambda: _validated_line_cap(invalid_type))
    invalid_value = _style()
    invalid_value._stroke_linecap = "triangle"
    _raises(ValueError, lambda: _validated_line_cap(invalid_value))

    line = LineDrawing((0.0, 0.0), (5.0, 0.0), _style("round"))
    _validate_raster_stroke_style(line, line.style)
    rectangle = RectangleDrawing((0.0, 0.0), 1.0, 1.0, 0.0, _style("round"))
    _raises(ValueError, lambda: _validate_raster_stroke_style(rectangle, rectangle.style))
    dashed_rectangle = RectangleDrawing((0.0, 0.0), 1.0, 1.0, 0.0, _style(pattern=(1.0, 1.0)))
    _raises(ValueError, lambda: _validate_raster_stroke_style(dashed_rectangle, dashed_rectangle.style))
    butt_rectangle = RectangleDrawing((0.0, 0.0), 1.0, 1.0, 0.0, _style())
    _validate_raster_stroke_style(butt_rectangle, butt_rectangle.style)
    dynamic_butt_rectangle = RectangleDrawing((0.0, 0.0), 1.0, 1.0, 0.0, _style())
    dynamic_butt_rectangle.style._stroke_linecap = "".join(("b", "u", "t", "t"))
    _validate_raster_stroke_style(dynamic_butt_rectangle, dynamic_butt_rectangle.style)

    invalid_join = _style()
    invalid_join._stroke_linejoin = "round"
    _raises(ValueError, lambda: _validate_raster_stroke_style(LineDrawing((0, 0), (1, 0), invalid_join), invalid_join))
    invalid_miter = _style()
    invalid_miter._stroke_miterlimit = 5.0
    _raises(ValueError, lambda: _validate_raster_stroke_style(LineDrawing((0, 0), (1, 0), invalid_miter), invalid_miter))

    overflow = _style("round", pattern=(1.0, 1.0))
    overflow._stroke_dasharray = (1e308, 1e308)
    _raises(ValueError, lambda: _validated_line_dash(overflow))
    odd_dash = _style(pattern=(1.0, 2.0, 3.0))
    assert _validated_line_dash(odd_dash) == ((1.0, 2.0, 3.0, 1.0, 2.0, 3.0), 0.0)

    original_limit = raster_renderer._MAX_DASH_STEPS
    raster_renderer._MAX_DASH_STEPS = 1
    try:
        dotted_butt = _style("".join(("b", "u", "t", "t")), pattern=(0.0, 1.0))
        _validate_raster_stroke_style(LineDrawing((0, 0), (1, 0), dotted_butt), dotted_butt)
        dotted_round = _style("round", pattern=(0.0, 1.0))
        _raises(
            ValueError,
            lambda: _validate_raster_stroke_style(LineDrawing((0, 0), (1, 0), dotted_round), dotted_round),
        )
    finally:
        raster_renderer._MAX_DASH_STEPS = original_limit


def _assert_geometry() -> None:
    assert _unit_tangent((2.0, 3.0), (2.0, 3.0)) == (1.0, 0.0)
    tangent = _unit_tangent((1.0, 2.0), (4.0, 6.0))
    assert math.isclose(tangent[0], 0.6)
    assert math.isclose(tangent[1], 0.8)
    assert _square_cap_polygon((5.0, 10.0), (15.0, 10.0), 4) == [
        (3.0, 12.0),
        (17.0, 12.0),
        (17.0, 8.0),
        (3.0, 8.0),
    ]
    assert _square_cap_polygon((10.0, 10.0), (10.0, 10.0), 4, (0.0, 1.0)) == [
        (8.0, 8.0),
        (8.0, 12.0),
        (12.0, 12.0),
        (12.0, 8.0),
    ]
    assert _square_cap_polygon((5.0, 10.0), (15.0, 10.0), 6, (0.0, 1.0)) == [
        (2.0, 13.0),
        (18.0, 13.0),
        (18.0, 7.0),
        (2.0, 7.0),
    ]
    assert _square_cap_polygon((15.0, 10.0), (5.0, 10.0), 6, (0.0, 1.0)) == [
        (18.0, 7.0),
        (2.0, 7.0),
        (2.0, 13.0),
        (18.0, 13.0),
    ]
    equal_square_start = tuple([10.0, 10.0])
    equal_square_end = tuple([10.0, 10.0])
    assert equal_square_start == equal_square_end and equal_square_start is not equal_square_end
    assert _square_cap_polygon(equal_square_start, equal_square_end, 4, (0.0, 1.0)) == [
        (8.0, 8.0),
        (8.0, 12.0),
        (12.0, 12.0),
        (12.0, 8.0),
    ]

    assert _zero_length_dash_centers((0.0, 0.0), (5.0, 0.0), (0.0, 2.0), 0.0, 10) == [
        (0.0, 0.0),
        (2.0, 0.0),
        (4.0, 0.0),
    ]
    assert _zero_length_dash_centers((0.0, 0.0), (5.0, 0.0), (0.0, 2.0), 1.0, 10) == [
        (1.0, 0.0),
        (3.0, 0.0),
        (5.0, 0.0),
    ]
    assert _zero_length_dash_centers((0.0, 0.0), (5.0, 0.0), (2.0, 0.0), 0.0, 10) == []
    assert _zero_length_dash_centers((0.0, 0.0), (7.0, 0.0), (1.0, 1.0, 0.0, 2.0), 0.5, 10) == [
        (1.5, 0.0),
        (5.5, 0.0),
    ]
    assert _zero_length_dash_centers((0.0, 0.0), (7.0, 0.0), (0.0, 5.0), 3.0, 10) == [
        (2.0, 0.0),
        (7.0, 0.0),
    ]
    assert _zero_length_dash_centers((0.0, 0.0), (5.0, 0.0), (0.0, 2.0), 0.5, 10) == [
        (1.5, 0.0),
        (3.5, 0.0),
    ]
    assert _zero_length_dash_centers((0.0, 0.0), (4.0, 0.0), (1.0, 1.0, 0.0, 0.0), 0.0, 10) == [
        (2.0, 0.0),
        (4.0, 0.0),
    ]
    assert _zero_length_dash_centers((0.0, 0.0), (1.0, 0.0), (0.25, 0.25, 0.0, 0.0), 0.0, 10) == [
        (0.5, 0.0),
        (1.0, 0.0),
    ]
    assert _zero_length_dash_centers((0.0, 0.0), (1.0, 0.0), (0.0, 1e308), 1e308, 10) == [(0.0, 0.0)]
    assert _zero_length_dash_centers((2.0, 3.0), (2.0, 3.0), (1.0, 1.0), 0.0, 1) == [(2.0, 3.0)]
    assert _zero_length_dash_centers((2.0, 3.0), (2.0, 3.0), (1.0, 1.0), 1.0, 1) == []
    assert _zero_length_dash_centers((2.0, 3.0), (2.0, 3.0), (0.0, 0.0, 0.0, 1.0), 0.0, 1) == [(2.0, 3.0)]
    assert _zero_length_dash_centers((2.0, 3.0), (2.0, 3.0), (0.0, 1.0, 1.0, 1.0), 1.0, 1) == [(2.0, 3.0)]
    _raises(ValueError, lambda: _zero_length_dash_centers((2.0, 3.0), (2.0, 3.0), (1.0, 1.0), 0.0, 0))
    _raises(ValueError, lambda: _zero_length_dash_centers((0.0, 0.0), (300.0, 0.0), (0.0, 1.0), 0.0, 300))

    original_limit = raster_renderer._MAX_DASH_STEPS
    raster_renderer._MAX_DASH_STEPS = 2
    try:
        assert _line_cap_dash_geometry((0.0, 0.0), (1.0, 0.0), (0.0, 1.0), 0.0) == (
            [],
            [(0.0, 0.0), (1.0, 0.0)],
        )
        raster_renderer._MAX_DASH_STEPS = 1
        _raises(ValueError, lambda: _line_cap_dash_geometry((0.0, 0.0), (1.0, 0.0), (0.0, 1.0), 0.0))
        _raises(ValueError, lambda: _line_cap_dash_geometry((0.0, 0.0), (1.0, 0.0), (1.0, 0.0, 0.0, 1.0), 0.0))
    finally:
        raster_renderer._MAX_DASH_STEPS = original_limit


def _assert_paint() -> None:
    round_surface = Image.new("RGBA", (21, 21), (0, 0, 0, 0))
    _draw_capped_segment(ImageDraw.Draw(round_surface), (5.0, 10.0), (15.0, 10.0), STROKE, 4, "round")
    assert round_surface.getpixel((3, 10)) == STROKE
    assert round_surface.getpixel((3, 8)) == (0, 0, 0, 0)
    assert round_surface.getpixel((17, 10)) == STROKE
    assert round_surface.getpixel((10, 10)) == STROKE
    assert round_surface.getpixel((18, 10)) == (0, 0, 0, 0)

    reverse_round = Image.new("RGBA", (21, 21), (0, 0, 0, 0))
    _draw_capped_segment(ImageDraw.Draw(reverse_round), (15.0, 10.0), (5.0, 10.0), STROKE, 4, "round")
    assert reverse_round.getpixel((10, 10)) == STROKE
    assert reverse_round.getpixel((3, 10)) == STROKE
    assert reverse_round.getpixel((17, 10)) == STROKE

    dynamic_square = Image.new("RGBA", (21, 21), (0, 0, 0, 0))
    _draw_capped_segment(
        ImageDraw.Draw(dynamic_square),
        (5.0, 10.0),
        (15.0, 10.0),
        STROKE,
        4,
        "".join(("s", "q", "u", "a", "r", "e")),
    )
    assert dynamic_square.getpixel((3, 8)) == STROKE

    square_surface = Image.new("RGBA", (21, 21), (0, 0, 0, 0))
    _draw_capped_segment(ImageDraw.Draw(square_surface), (5.0, 10.0), (15.0, 10.0), STROKE, 4, "square")
    assert square_surface.getpixel((3, 8)) == STROKE
    assert square_surface.getpixel((17, 12)) == STROKE

    zero_round = Image.new("RGBA", (21, 21), (0, 0, 0, 0))
    _draw_capped_segment(ImageDraw.Draw(zero_round), (10.0, 10.0), (10.0, 10.0), STROKE, 4, "round")
    assert zero_round.getpixel((10, 10)) == STROKE
    assert zero_round.getpixel((8, 8)) == (0, 0, 0, 0)
    assert zero_round.getpixel((13, 10)) == (0, 0, 0, 0)

    equal_start = tuple([10.0, 10.0])
    equal_end = tuple([10.0, 10.0])
    assert equal_start == equal_end and equal_start is not equal_end
    dynamic_zero_round = Image.new("RGBA", (21, 21), (0, 0, 0, 0))
    _draw_capped_segment(ImageDraw.Draw(dynamic_zero_round), equal_start, equal_end, STROKE, 4, "round")
    assert dynamic_zero_round.getpixel((13, 10)) == (0, 0, 0, 0)

    zero_square = Image.new("RGBA", (21, 21), (0, 0, 0, 0))
    _draw_capped_segment(ImageDraw.Draw(zero_square), (10.0, 10.0), (10.0, 10.0), STROKE, 4, "square", (0.0, 1.0))
    assert zero_square.getpixel((8, 8)) == STROKE

    solid = Image.new("RGBA", (21, 21), (0, 0, 0, 0))
    solid_line = LineDrawing((5.0, 10.0), (15.0, 10.0), _style("square"))
    _draw_capped_line_component(ImageDraw.Draw(solid), solid_line, 1.0, STROKE, 4)
    assert solid.getpixel((3, 8)) == STROKE

    dashed = Image.new("RGBA", (21, 21), (0, 0, 0, 0))
    dashed_line = LineDrawing((5.0, 10.0), (15.0, 10.0), _style("round", pattern=(0.0, 4.0)))
    _draw_capped_line_component(ImageDraw.Draw(dashed), dashed_line, 1.0, STROKE, 2)
    assert dashed.getpixel((5, 10)) == STROKE
    assert dashed.getpixel((7, 10)) == (0, 0, 0, 0)
    assert dashed.getpixel((9, 10)) == STROKE

    positive_dashed = Image.new("RGBA", (21, 21), (0, 0, 0, 0))
    positive_dashed_line = LineDrawing((5.0, 10.0), (15.0, 10.0), _style("round", pattern=(2.0, 4.0)))
    _draw_capped_line_component(ImageDraw.Draw(positive_dashed), positive_dashed_line, 1.0, STROKE, 2)
    assert positive_dashed.getpixel((6, 10)) == STROKE
    assert positive_dashed.getpixel((9, 10)) == (0, 0, 0, 0)

    invisible = Image.new("RGBA", (21, 21), (0, 0, 0, 0))
    _draw_capped_line_component(ImageDraw.Draw(invisible), solid_line, 1.0, None, 0)
    assert invisible.getbbox() is None

    butt_zero = Image.new("RGBA", (21, 21), (0, 0, 0, 0))
    _draw_dispatched_line_component(
        ImageDraw.Draw(butt_zero),
        LineDrawing((10.0, 10.0), (10.0, 10.0), _style("butt")),
        1.0,
        STROKE,
        4,
    )
    assert butt_zero.getbbox() is None
    butt_solid = Image.new("RGBA", (21, 21), (0, 0, 0, 0))
    _draw_dispatched_line_component(
        ImageDraw.Draw(butt_solid),
        LineDrawing((5.0, 10.0), (15.0, 10.0), _style("butt")),
        1.0,
        STROKE,
        4,
    )
    assert butt_solid.getpixel((10, 10)) == STROKE
    reverse_butt = Image.new("RGBA", (21, 21), (0, 0, 0, 0))
    _draw_dispatched_line_component(
        ImageDraw.Draw(reverse_butt),
        LineDrawing((15.0, 10.0), (5.0, 10.0), _style("".join(("b", "u", "t", "t")))),
        1.0,
        STROKE,
        4,
    )
    assert reverse_butt.getpixel((10, 10)) == STROKE
    assert reverse_butt.getpixel((3, 10)) == (0, 0, 0, 0)
    dispatched_round = Image.new("RGBA", (21, 21), (0, 0, 0, 0))
    _draw_dispatched_line_component(ImageDraw.Draw(dispatched_round), solid_line, 1.0, STROKE, 4)
    assert dispatched_round.getpixel((3, 8)) == STROKE


def main() -> None:
    """Run all deterministic P14 mutation witnesses."""
    _assert_validation()
    _assert_geometry()
    _assert_paint()


if __name__ == "__main__":
    main()
