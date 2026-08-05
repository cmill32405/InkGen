"""Fast deterministic witnesses for raster line-join P15 mutation workers."""

from __future__ import annotations

import hashlib
import math
from itertools import count

from PIL import Image, ImageDraw

from InkGen.drawing_components import (
    CircleDrawing,
    LineDrawing,
    PathDrawing,
    PolygonalDrawing,
    QuadraticBezierDrawing,
    RectangleDrawing,
    RegularPolygonDrawing,
)
from InkGen.gradients import LinearGradientFill
from InkGen.raster_renderer import (
    _bevel_join_polygon,
    _draw_joined_polyline,
    _draw_polygon,
    _render_component,
    _validate_raster_stroke_style,
    _validated_line_join,
)
from InkGen.style import DrawingStyle

_STYLE_IDS = count()
STROKE = (16, 32, 48, 255)


class _RecordingDraw:
    """Record exact Pillow primitive calls without raster ambiguity."""

    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def line(self, points: object, *, fill: object, width: int) -> None:
        self.calls.append(("line", points, fill, width))

    def ellipse(self, box: object, *, fill: object) -> None:
        self.calls.append(("ellipse", box, fill))

    def polygon(self, points: object, *, fill: object) -> None:
        self.calls.append(("polygon", points, fill))


def _style(line_join: str = "miter", *, stroke: str = "#102030", width: float = 4.0) -> DrawingStyle:
    return DrawingStyle(
        f"mutation-join-{next(_STYLE_IDS)}",
        fill="none",
        stroke=stroke,
        stroke_width=width,
        stroke_linejoin=line_join,
    )


def _raises(error: type[Exception], call: object) -> None:
    try:
        call()  # type: ignore[operator]
    except error:
        return
    raise AssertionError(f"expected {error.__name__}")


def _assert_validation() -> None:
    for value in ("miter", "round", "bevel"):
        assert _validated_line_join(_style(value)) == value
    invalid_type = _style()
    invalid_type._stroke_linejoin = object()
    _raises(TypeError, lambda: _validated_line_join(invalid_type))
    invalid_value = _style()
    invalid_value._stroke_linejoin = "arcs"
    _raises(ValueError, lambda: _validated_line_join(invalid_value))

    supported = [
        RectangleDrawing((0, 0), 2, 2, 0, _style("round")),
        LineDrawing((0, 0), (1, 1), _style("round")),
        CircleDrawing((1, 1), 1, _style("round")),
        PolygonalDrawing([(0, 0), (1, 0), (1, 1)], _style("bevel")),
        RegularPolygonDrawing((2, 2), 3, 1, _style("bevel")),
    ]
    for component in supported:
        _validate_raster_stroke_style(component, component.style)

    for unsupported in (
        PathDrawing(_style("round")),
        QuadraticBezierDrawing((0, 0), (1, 0), (1, 1), _style("bevel")),
    ):
        _raises(ValueError, lambda component=unsupported: _validate_raster_stroke_style(component, component.style))

    bad_limit = _style("round")
    bad_limit._stroke_miterlimit = 2.0
    _raises(
        ValueError,
        lambda: _validate_raster_stroke_style(
            PolygonalDrawing([(0, 0), (1, 0), (1, 1)], bad_limit),
            bad_limit,
        ),
    )


def _assert_geometry() -> None:
    clockwise = _bevel_join_polygon((0.0, 10.0), (10.0, 10.0), (10.0, 20.0), 4)
    assert clockwise == [(10.0, 10.0), (10.0, 8.0), (12.0, 10.0)]
    counterclockwise = _bevel_join_polygon((10.0, 20.0), (10.0, 10.0), (0.0, 10.0), 4)
    assert counterclockwise == [(10.0, 10.0), (12.0, 10.0), (10.0, 8.0)]
    diagonal = _bevel_join_polygon((0.0, 0.0), (3.0, 4.0), (6.0, 0.0), 10)
    assert diagonal[0] == (3.0, 4.0)
    assert math.hypot(diagonal[1][0] - 3.0, diagonal[1][1] - 4.0) == 5.0
    assert math.hypot(diagonal[2][0] - 3.0, diagonal[2][1] - 4.0) == 5.0
    assert _bevel_join_polygon((0.0, 0.0), (0.0, 0.0), (1.0, 1.0), 4) == []
    assert _bevel_join_polygon((0.0, 0.0), (1.0, 1.0), (1.0, 1.0), 4) == []
    assert _bevel_join_polygon((0.0, 0.0), (1.0, 1.0), (2.0, 2.0), 4) == []
    assert _bevel_join_polygon((2.0, 2.0), (1.0, 1.0), (0.0, 0.0), 4) == []
    equal_previous = tuple([0.0, 0.0])
    equal_vertex = tuple([0.0, 0.0])
    assert equal_previous == equal_vertex and equal_previous is not equal_vertex
    assert _bevel_join_polygon(equal_previous, equal_vertex, (1.0, 1.0), 4) == []
    following_reference = (1.0, 1.0)
    equal_following = tuple(list(following_reference))
    assert equal_following == following_reference and equal_following is not following_reference
    assert _bevel_join_polygon((0.0, 0.0), (1.0, 1.0), equal_following, 4) == []
    shallow_right = _bevel_join_polygon((0.0, 0.0), (1.0, 0.0), (2.0, -0.1), 4)
    assert shallow_right[1][1] == 2.0
    assert shallow_right[2][0] > 1.0
    assert shallow_right[2][1] > 0.0


def _assert_operations() -> None:
    points = [(0.0, 10.0), (10.0, 10.0), (10.0, 20.0)]
    closed_round = _RecordingDraw()
    _draw_joined_polyline(closed_round, points, STROKE, 4, "round", closed=True)  # type: ignore[arg-type]
    assert closed_round.calls == [
        ("line", [(0.0, 10.0), (10.0, 10.0)], STROKE, 4),
        ("line", [(10.0, 10.0), (10.0, 20.0)], STROKE, 4),
        ("line", [(10.0, 20.0), (0.0, 10.0)], STROKE, 4),
        ("ellipse", (-2.0, 8.0, 2.0, 12.0), STROKE),
        ("ellipse", (8.0, 8.0, 12.0, 12.0), STROKE),
        ("ellipse", (8.0, 18.0, 12.0, 22.0), STROKE),
    ]

    open_round = _RecordingDraw()
    _draw_joined_polyline(open_round, points, STROKE, 4, "round", closed=False)  # type: ignore[arg-type]
    assert open_round.calls == [
        ("line", [(0.0, 10.0), (10.0, 10.0)], STROKE, 4),
        ("line", [(10.0, 10.0), (10.0, 20.0)], STROKE, 4),
        ("ellipse", (8.0, 8.0, 12.0, 12.0), STROKE),
    ]

    wide_round = _RecordingDraw()
    _draw_joined_polyline(wide_round, points, STROKE, 6, "".join(("r", "o", "u", "n", "d")), closed=False)  # type: ignore[arg-type]
    assert wide_round.calls == [
        ("line", [(0.0, 10.0), (10.0, 10.0)], STROKE, 6),
        ("line", [(10.0, 10.0), (10.0, 20.0)], STROKE, 6),
        ("ellipse", (7.0, 7.0, 13.0, 13.0), STROKE),
    ]

    closed_bevel = _RecordingDraw()
    _draw_joined_polyline(closed_bevel, points, STROKE, 4, "bevel", closed=True)  # type: ignore[arg-type]
    assert closed_bevel.calls[:3] == closed_round.calls[:3]
    assert closed_bevel.calls[3:] == [
        ("polygon", [(0.0, 10.0), (-1.414213562373095, 11.414213562373096), (0.0, 8.0)], STROKE),
        ("polygon", [(10.0, 10.0), (10.0, 8.0), (12.0, 10.0)], STROKE),
        ("polygon", [(10.0, 20.0), (12.0, 20.0), (8.585786437626904, 21.414213562373096)], STROKE),
    ]

    duplicate = _RecordingDraw()
    _draw_joined_polyline(
        duplicate,  # type: ignore[arg-type]
        [(1.0, 1.0), tuple([1.0, 1.0]), (8.0, 8.0)],
        STROKE,
        2,
        "bevel",
        closed=False,
    )
    assert duplicate.calls == [("line", [(1.0, 1.0), (8.0, 8.0)], STROKE, 2)]

    duplicate_round = _RecordingDraw()
    _draw_joined_polyline(
        duplicate_round,  # type: ignore[arg-type]
        [(1.0, 1.0), tuple([1.0, 1.0]), (8.0, 8.0)],
        STROKE,
        2,
        "round",
        closed=False,
    )
    assert duplicate_round.calls == [("line", [(1.0, 1.0), (8.0, 8.0)], STROKE, 2)]

    equal_following_round = _RecordingDraw()
    _draw_joined_polyline(
        equal_following_round,  # type: ignore[arg-type]
        [(0.0, 0.0), (1.0, 1.0), tuple([1.0, 1.0])],
        STROKE,
        2,
        "round",
        closed=False,
    )
    assert equal_following_round.calls == [("line", [(0.0, 0.0), (1.0, 1.0)], STROKE, 2)]

    empty = _RecordingDraw()
    _draw_joined_polyline(empty, [], STROKE, 4, "round", closed=True)  # type: ignore[arg-type]
    _draw_joined_polyline(empty, [(1.0, 1.0)], STROKE, 4, "bevel", closed=True)  # type: ignore[arg-type]
    assert empty.calls == []

    polygon = _RecordingDraw()
    _draw_polygon(polygon, [(1.0, 2.0), (3.0, 4.0)], 2.0, STROKE, STROKE, 4, "round")  # type: ignore[arg-type]
    assert polygon.calls == [
        ("polygon", [(2, 4), (6, 8)], STROKE),
        ("line", [(2, 4), (6, 8)], STROKE, 4),
        ("line", [(6, 8), (2, 4)], STROKE, 4),
        ("ellipse", (0.0, 2.0, 4.0, 6.0), STROKE),
        ("ellipse", (4.0, 6.0, 8.0, 10.0), STROKE),
    ]

    miter = _RecordingDraw()
    _draw_polygon(
        miter,
        [(1.0, 2.0), (3.0, 4.0)],
        2.0,
        None,
        STROKE,
        4,
        "".join(("m", "i", "t", "e", "r")),
    )  # type: ignore[arg-type]
    assert miter.calls == [("line", [(2, 4), (6, 8), (2, 4)], STROKE, 4)]


def _paint(line_join: str, *, closed: bool = True) -> Image.Image:
    surface = Image.new("RGBA", (31, 31), (0, 0, 0, 0))
    _draw_joined_polyline(
        ImageDraw.Draw(surface),
        [(5.0, 25.0), (15.0, 5.0), (25.0, 25.0)],
        STROKE,
        8,
        line_join,
        closed=closed,
    )
    return surface


def _assert_paint() -> None:
    round_surface = _paint("round")
    bevel_surface = _paint("bevel")
    assert round_surface.getbbox() is not None
    assert bevel_surface.getbbox() is not None
    assert round_surface.getchannel("A").tobytes() != bevel_surface.getchannel("A").tobytes()
    assert round_surface.getpixel((5, 25)) == STROKE
    assert bevel_surface.getpixel((5, 25)) == STROKE

    open_round = _paint("round", closed=False)
    assert open_round.getpixel((5, 25)) == STROKE
    assert open_round.getpixel((15, 5)) == STROKE
    assert open_round.getpixel((25, 25)) == STROKE

    empty = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    empty_draw = ImageDraw.Draw(empty)
    _draw_joined_polyline(empty_draw, [], STROKE, 4, "round", closed=True)
    _draw_joined_polyline(empty_draw, [(1.0, 1.0)], STROKE, 4, "bevel", closed=True)
    assert empty.getbbox() is None

    duplicate = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    _draw_joined_polyline(
        ImageDraw.Draw(duplicate),
        [(1.0, 1.0), (1.0, 1.0), (8.0, 8.0)],
        STROKE,
        2,
        "bevel",
        closed=False,
    )
    assert duplicate.getpixel((4, 4)) == STROKE

    direct_polygon = Image.new("RGBA", (31, 31), (0, 0, 0, 0))
    _draw_polygon(
        ImageDraw.Draw(direct_polygon),
        [(0.5, 2.5), (1.5, 0.5), (2.5, 2.5)],
        10.0,
        None,
        STROKE,
        8,
        "round",
    )
    assert direct_polygon.getpixel((15, 5)) == STROKE


def _assert_dispatch() -> None:
    outputs: dict[tuple[str, str], bytes] = {}
    for line_join in ("round", "bevel"):
        style = _style(line_join, width=0.4)
        components = {
            "rectangle": RectangleDrawing((0.3, 0.7), 1.4, 0.8, 0.0, style),
            "gradient": RectangleDrawing(
                (0.3, 0.7),
                1.4,
                0.8,
                0.0,
                style,
                LinearGradientFill(((0.0, "#ff0000"), (1.0, "#0000ff")), 0.0),
            ),
            "polygon": PolygonalDrawing([(0.5, 2.5), (1.0, 1.5), (1.5, 2.5)], style),
            "regular": RegularPolygonDrawing((2.5, 1.0), 4, 0.6, style, angle=45.0),
            "rounded_regular": RegularPolygonDrawing((2.5, 1.0), 4, 0.6, style, angle=45.0, corner_radius=0.2),
        }
        for name, component in components.items():
            surface = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
            _render_component(surface, component, 10.0)
            assert surface.getbbox() is not None
            outputs[name, line_join] = surface.tobytes()

    for name in ("rectangle", "gradient", "polygon", "regular"):
        assert outputs[name, "round"] != outputs[name, "bevel"]
    assert outputs["rounded_regular", "round"] == outputs["rounded_regular", "bevel"]
    assert {key: hashlib.sha256(value).hexdigest() for key, value in outputs.items()} == {
        ("rectangle", "round"): "8e728c7cb71a0d749549c90a737028f269ec372ae2313c40eeb5ced39e01a70c",
        ("gradient", "round"): "7e6e579d4aeba3407dbce4ce865836e478c7da211ae7fd9b28847cf9b6a842c5",
        ("polygon", "round"): "e8d8dc04444ae36a33b09ed029a1a851e5432068b78005ec284b617430911d59",
        ("regular", "round"): "b2022008ecbb931d2b2b0217f52ba0f4461e8771a0207f9b2247928ae39d1507",
        ("rounded_regular", "round"): "fd3da2d5f73e2fe9451b1518021c1e242893594f456705da7f03aeb40a008fb6",
        ("rectangle", "bevel"): "a73897e3fc36ba5a289c0c0d61c8723e936f6becb1a9a7eed693e631a79deaa9",
        ("gradient", "bevel"): "69373cfebaff8c7735605f8deda4ae2058ae684f74b4a6bfd38e49bd462f6482",
        ("polygon", "bevel"): "8ca36901a5b56236d6a5483591a27ed2a1b320688d16ee643367f65037071b0b",
        ("regular", "bevel"): "9765019bc2eb476c8a5dbf1abc628bac940a855a9cf067619f3aefe5d16a6f38",
        ("rounded_regular", "bevel"): "fd3da2d5f73e2fe9451b1518021c1e242893594f456705da7f03aeb40a008fb6",
    }

    dynamic_miter = "".join(("m", "i", "t", "e", "r"))
    literal_miter = "miter"
    assert dynamic_miter == literal_miter and dynamic_miter is not literal_miter
    dynamic_style = _style(dynamic_miter, width=0.4)
    literal_style = _style("miter", width=0.4)
    dynamic_components = (
        RectangleDrawing((0.3, 0.7), 1.4, 0.8, 0.0, dynamic_style),
        RectangleDrawing(
            (0.3, 0.7),
            1.4,
            0.8,
            0.0,
            dynamic_style,
            LinearGradientFill(((0.0, "#ff0000"), (1.0, "#0000ff")), 0.0),
        ),
        PolygonalDrawing([(0.5, 2.5), (1.0, 1.5), (1.5, 2.5)], dynamic_style),
        RegularPolygonDrawing((2.5, 1.0), 4, 0.6, dynamic_style, angle=45.0),
    )
    literal_components = (
        RectangleDrawing((0.3, 0.7), 1.4, 0.8, 0.0, literal_style),
        RectangleDrawing(
            (0.3, 0.7),
            1.4,
            0.8,
            0.0,
            literal_style,
            LinearGradientFill(((0.0, "#ff0000"), (1.0, "#0000ff")), 0.0),
        ),
        PolygonalDrawing([(0.5, 2.5), (1.0, 1.5), (1.5, 2.5)], literal_style),
        RegularPolygonDrawing((2.5, 1.0), 4, 0.6, literal_style, angle=45.0),
    )
    for dynamic_component, literal_component in zip(dynamic_components, literal_components, strict=True):
        dynamic_surface = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
        literal_surface = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
        _render_component(dynamic_surface, dynamic_component, 10.0)
        _render_component(literal_surface, literal_component, 10.0)
        assert dynamic_surface.tobytes() == literal_surface.tobytes()

    invisible_style = _style("round", stroke="none", width=0.4)
    invisible_components = (
        RectangleDrawing((0.3, 0.7), 1.4, 0.8, 0.0, invisible_style),
        RectangleDrawing(
            (0.3, 0.7),
            1.4,
            0.8,
            0.0,
            invisible_style,
            LinearGradientFill(((0.0, "#ff0000"), (1.0, "#0000ff")), 0.0),
        ),
    )
    invisible_bounds = []
    for component in invisible_components:
        surface = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
        _render_component(surface, component, 10.0)
        invisible_bounds.append(surface.getbbox())
    assert invisible_bounds == [None, (3, 7, 18, 16)]

    unsupported_dynamic_miter = PathDrawing(dynamic_style)
    _validate_raster_stroke_style(unsupported_dynamic_miter, dynamic_style)

    no_stroke = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
    _render_component(
        no_stroke,
        PolygonalDrawing([(0.5, 2.5), (1.0, 1.5), (1.5, 2.5)], _style("round", stroke="none")),
        10.0,
    )
    assert no_stroke.getbbox() is None


def main() -> None:
    _assert_validation()
    _assert_geometry()
    _assert_operations()
    _assert_paint()
    _assert_dispatch()


if __name__ == "__main__":
    main()
