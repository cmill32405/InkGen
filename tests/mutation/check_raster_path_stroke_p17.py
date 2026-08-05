"""Fast deterministic witnesses for semantic raster path strokes P17."""

from __future__ import annotations

import hashlib
from itertools import count

from check_raster_line_cap_p14 import main as line_cap_main
from check_raster_line_dash_p13 import main as line_dash_main
from check_raster_line_join_p15 import main as line_join_main
from check_raster_miter_limit_p16 import (
    _assert_geometry as miter_geometry_check,
)
from check_raster_miter_limit_p16 import (
    _assert_operations as miter_operations_check,
)
from check_raster_miter_limit_p16 import (
    _assert_point_dispatch as miter_point_dispatch_check,
)
from check_raster_miter_limit_p16 import (
    _assert_validation as miter_validation_check,
)

from InkGen.boundary import Canvas
from InkGen.component import PathCommand
from InkGen.drawing_components import DrawingComponentGroup, PathDrawing, QuadraticBezierDrawing, RectangleDrawing
from InkGen.raster_renderer import (
    _distinct_path_neighbor,
    _draw_open_path_caps,
    _draw_path_endpoint_cap,
    _draw_path_segment_bodies,
    _draw_path_strokes,
    _draw_semantic_path_stroke,
    _draw_stroke_join,
    _open_path_endpoint_tangents,
    _PathSampler,
    _sampled_path_geometry,
    _sampled_path_subpaths,
    _scaled_path_subpaths,
    _scaled_sampled_subpath,
    _semantic_path_join_triples,
    _unit_tangent,
    _validate_path_miter_geometry,
    _validate_raster_stroke_style,
    render_drawing_group,
)
from InkGen.style import DrawingStyle

_STYLE_IDS = count()
STROKE = (16, 32, 48, 255)


class _RecordingDraw:
    """Record exact Pillow primitive calls without pixel ambiguity."""

    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def line(self, points: object, *, fill: object, width: int) -> None:
        self.calls.append(("line", list(points), fill, width))  # type: ignore[arg-type]

    def ellipse(self, box: object, *, fill: object) -> None:
        self.calls.append(("ellipse", box, fill))

    def polygon(self, points: object, *, fill: object) -> None:
        self.calls.append(("polygon", list(points), fill))  # type: ignore[arg-type]


def _style(
    *,
    cap: str = "butt",
    join: str = "miter",
    limit: float = 10.0,
    fill: str = "none",
    stroke: str = "#102030",
    stroke_opacity: float = 1.0,
) -> DrawingStyle:
    return DrawingStyle(
        f"mutation-path-stroke-{next(_STYLE_IDS)}",
        fill=fill,
        stroke=stroke,
        stroke_width=0.4,
        stroke_opacity=stroke_opacity,
        stroke_linecap=cap,
        stroke_linejoin=join,
        stroke_miterlimit=limit,
    )


def _path(style: DrawingStyle, *, closed: bool = False) -> PathDrawing:
    commands = [
        PathCommand("M", [(1.0, 3.0)]),
        PathCommand("Q", [(1.0, 1.0), (3.0, 1.0)]),
        PathCommand("L", [(4.0, 3.0)]),
    ]
    if closed:
        commands.append(PathCommand("Z"))
    return PathDrawing(style, commands)


def _raises(error: type[Exception], call: object, text: str) -> None:
    try:
        call()  # type: ignore[operator]
    except error as exc:
        assert text in str(exc)
        return
    raise AssertionError(f"expected {error.__name__}")


def _assert_sampling() -> None:
    path = _path(_style())
    subpath = _sampled_path_geometry(path)[0]
    assert len(subpath.points) == 34
    assert subpath.endpoint_indices == (0, 32, 33)
    assert subpath.segment_count == 2
    assert not subpath.closed
    assert _sampled_path_subpaths(path) == [list(subpath.points)]
    scaled = _scaled_sampled_subpath(subpath, 2.0)
    assert scaled.points[0] == (2.0, 6.0)
    assert scaled.points[-1] == (8.0, 6.0)
    assert scaled.endpoint_indices == subpath.endpoint_indices
    assert scaled.segment_count == 2 and not scaled.closed
    assert _scaled_path_subpaths(path, 2.0) == [list(scaled.points)]

    closed = _sampled_path_geometry(_path(_style(), closed=True))[0]
    assert closed.closed and closed.segment_count == 3
    assert closed.points[-1] == closed.points[0]
    assert closed.endpoint_indices == (0, 32, 33)

    corrupt = PathDrawing(_style())
    object.__setattr__(corrupt, "commands", "ML")
    _raises(TypeError, lambda: _sampled_path_geometry(corrupt), "must be a sequence")

    sampler = _PathSampler(PathDrawing(_style()))
    for call, text in (
        (lambda: sampler._close([]), "close requires"),
        (lambda: sampler._append_segment([(0.0, 0.0), (1.0, 1.0)]), "segment requires"),
        (sampler._current_point, "command requires"),
        (lambda: sampler._finish(closed=False), "finish requires"),
    ):
        _raises(AssertionError, call, text)


def _assert_topology() -> None:
    subpath = _sampled_path_geometry(_path(_style()))[0]
    joins = _semantic_path_join_triples(subpath)
    assert joins == [(subpath.points[31], subpath.points[32], subpath.points[33])]
    assert _distinct_path_neighbor(subpath, 0, -1) is None
    start_tangent, end_tangent = _open_path_endpoint_tangents(subpath)
    assert start_tangent == _unit_tangent(subpath.points[0], subpath.points[1])
    assert end_tangent == _unit_tangent(subpath.points[-2], subpath.points[-1])

    closed = _sampled_path_geometry(_path(_style(), closed=True))[0]
    assert len(_semantic_path_join_triples(closed)) == 3

    equal = PathDrawing(
        _style(),
        [PathCommand("M", [(1.0, 1.0)]), PathCommand("L", [(1.0, 1.0), (1.0, 1.0)])],
    )
    degenerate = _sampled_path_geometry(equal)[0]
    assert _semantic_path_join_triples(degenerate) == []
    assert _distinct_path_neighbor(degenerate, 0, 1) is None

    duplicate_run = _sampled_path_geometry(
        PathDrawing(
            _style(),
            [
                PathCommand("M", [(0.0, 0.0)]),
                PathCommand("L", [(0.0, 0.0), (0.0, 0.0), (2.0, 3.0)]),
                PathCommand("Z"),
            ],
        )
    )[0]
    assert _distinct_path_neighbor(duplicate_run, 0, 1) == (2.0, 3.0)
    assert _distinct_path_neighbor(duplicate_run, 0, -1) == (2.0, 3.0)

    one_sided = _sampled_path_geometry(
        PathDrawing(
            _style(),
            [PathCommand("M", [(0.0, 0.0)]), PathCommand("L", [(0.0, 0.0), (1.0, 0.0)])],
        )
    )[0]
    assert _semantic_path_join_triples(one_sided) == []

    long_open = _sampled_path_geometry(
        PathDrawing(
            _style(),
            [PathCommand("M", [(0.0, 0.0)]), PathCommand("L", [(float(index), 0.0) for index in range(1, 300)])],
        )
    )[0]
    assert _distinct_path_neighbor(long_open, len(long_open.points) - 1, 1) is None


def _assert_cap_geometry() -> None:
    round_draw = _RecordingDraw()
    _draw_path_endpoint_cap(round_draw, (10.0, 20.0), (1.0, 0.0), STROKE, 4, "round", at_start=True)  # type: ignore[arg-type]
    assert round_draw.calls == [("ellipse", (8.0, 18.0, 12.0, 22.0), STROKE)]

    square_draw = _RecordingDraw()
    _draw_path_endpoint_cap(square_draw, (10.0, 20.0), (1.0, 0.0), STROKE, 4, "square", at_start=True)  # type: ignore[arg-type]
    assert square_draw.calls == [("polygon", [(10.0, 22.0), (8.0, 22.0), (8.0, 18.0), (10.0, 18.0)], STROKE)]

    subpath = _scaled_sampled_subpath(_sampled_path_geometry(_path(_style(cap="square")))[0], 10.0)
    both = _RecordingDraw()
    _draw_open_path_caps(both, subpath, STROKE, 4, "square")  # type: ignore[arg-type]
    assert len(both.calls) == 2
    assert all(call[0] == "polygon" for call in both.calls)
    assert max(point[0] for point in both.calls[0][1]) < 15.0  # type: ignore[index]
    assert min(point[0] for point in both.calls[1][1]) > 35.0  # type: ignore[index]

    diagonal = _RecordingDraw()
    _draw_path_endpoint_cap(diagonal, (10.0, 10.0), (0.6, 0.8), STROKE, 10, "square", at_start=False)  # type: ignore[arg-type]
    assert diagonal.calls == [("polygon", [(6.0, 13.0), (9.0, 17.0), (17.0, 11.0), (14.0, 7.0)], STROKE)]

    single = _sampled_path_geometry(
        PathDrawing(
            _style(cap="square"),
            [PathCommand("M", [(1.0, 2.0)]), PathCommand("L", [(4.0, 2.0)])],
        )
    )[0]
    single_caps = _RecordingDraw()
    _draw_open_path_caps(single_caps, _scaled_sampled_subpath(single, 10.0), STROKE, 4, "square")  # type: ignore[arg-type]
    assert single_caps.calls == [
        ("polygon", [(10.0, 22.0), (8.0, 22.0), (8.0, 18.0), (10.0, 18.0)], STROKE),
        ("polygon", [(40.0, 22.0), (42.0, 22.0), (42.0, 18.0), (40.0, 18.0)], STROKE),
    ]

    dynamic_round = "".join(("ro", "und"))
    round_literal = "round"
    assert dynamic_round == round_literal and id(dynamic_round) != id(round_literal)
    dynamic_round_draw = _RecordingDraw()
    _draw_path_endpoint_cap(dynamic_round_draw, (10.0, 20.0), (1.0, 0.0), STROKE, 4, dynamic_round, at_start=True)  # type: ignore[arg-type]
    assert dynamic_round_draw.calls == [("ellipse", (8.0, 18.0, 12.0, 22.0), STROKE)]

    move_only = _sampled_path_geometry(PathDrawing(_style(cap="round"), [PathCommand("M", [(1.0, 1.0)])]))[0]
    none = _RecordingDraw()
    _draw_open_path_caps(none, move_only, STROKE, 4, "round")  # type: ignore[arg-type]
    assert none.calls == []

    zero = _sampled_path_geometry(PathDrawing(_style(cap="round"), [PathCommand("M", [(1.0, 1.0)]), PathCommand("L", [(1.0, 1.0)])]))[0]
    dot = _RecordingDraw()
    _draw_open_path_caps(dot, _scaled_sampled_subpath(zero, 10.0), STROKE, 4, "round")  # type: ignore[arg-type]
    assert dot.calls == [("ellipse", (8.0, 8.0, 12.0, 12.0), STROKE)]
    square_dot = _RecordingDraw()
    _draw_open_path_caps(square_dot, _scaled_sampled_subpath(zero, 10.0), STROKE, 4, "square")  # type: ignore[arg-type]
    assert square_dot.calls == [("polygon", [(8.0, 12.0), (12.0, 12.0), (12.0, 8.0), (8.0, 8.0)], STROKE)]


def _assert_stroke_dispatch() -> None:
    default_style = _style()
    default_path = _path(default_style)
    default_geometry = _sampled_path_geometry(default_path)
    default = _RecordingDraw()
    _draw_path_strokes(default, default_geometry, default_style, 2.0, STROKE, 4)  # type: ignore[arg-type]
    assert len(default.calls) == 1 and default.calls[0][0] == "line"

    cap_style = _style(cap="round")
    capped = _RecordingDraw()
    _draw_semantic_path_stroke(capped, _sampled_path_geometry(_path(cap_style))[0], cap_style, 2.0, STROKE, 4)  # type: ignore[arg-type]
    assert [call[0] for call in capped.calls] == ["line", "ellipse", "ellipse"]

    join_style = _style(join="bevel")
    joined_subpath = _sampled_path_geometry(_path(join_style))[0]
    joined = _RecordingDraw()
    _draw_semantic_path_stroke(joined, joined_subpath, join_style, 2.0, STROKE, 4)  # type: ignore[arg-type]
    assert [call[0] for call in joined.calls] == ["line", "line", "polygon"]

    closed = _sampled_path_geometry(_path(join_style, closed=True))[0]
    bodies = _RecordingDraw()
    _draw_path_segment_bodies(bodies, closed, 2.0, STROKE, 4)  # type: ignore[arg-type]
    assert [call[0] for call in bodies.calls] == ["line", "line", "line"]
    assert bodies.calls[-1][1] == [(8.0, 6.0), (2.0, 6.0)]
    assert bodies.calls[0][1] == [(round(point[0] * 2.0), round(point[1] * 2.0)) for point in closed.points[:33]]

    dynamic_miter = "".join(("mi", "ter"))
    dynamic_butt = "".join(("bu", "tt"))
    miter_literal = "miter"
    butt_literal = "butt"
    assert dynamic_miter == miter_literal and id(dynamic_miter) != id(miter_literal)
    assert dynamic_butt == butt_literal and id(dynamic_butt) != id(butt_literal)
    dynamic_style = _style()
    dynamic_style._stroke_linejoin = dynamic_miter
    dynamic_style._stroke_linecap = dynamic_butt
    dynamic_draw = _RecordingDraw()
    _draw_semantic_path_stroke(
        dynamic_draw,
        _sampled_path_geometry(_path(dynamic_style))[0],
        dynamic_style,
        2.0,
        STROKE,
        4,
    )  # type: ignore[arg-type]
    assert len(dynamic_draw.calls) == 1 and dynamic_draw.calls[0][0] == "line"

    dynamic_bevel = "".join(("be", "vel"))
    bevel_literal = "bevel"
    assert dynamic_bevel == bevel_literal and id(dynamic_bevel) != id(bevel_literal)
    bevel_draw = _RecordingDraw()
    _draw_stroke_join(bevel_draw, (0.0, 0.0), (2.0, 0.0), (2.0, 2.0), STROKE, 4, dynamic_bevel, 10.0)  # type: ignore[arg-type]
    assert bevel_draw.calls == [("polygon", [(2.0, 0.0), (2.0, -2.0), (4.0, 0.0)], STROKE)]


def _assert_validation() -> None:
    for style in (_style(cap="round"), _style(join="round"), _style(limit=2.0)):
        _validate_raster_stroke_style(_path(style), style, 20.0)
    _validate_path_miter_geometry(_path(_style(limit=2.0)), 20.0, 8, 2.0)

    rectangle = RectangleDrawing((0, 0), 1, 1, 0, _style(cap="round"))
    _raises(
        ValueError,
        lambda: _validate_raster_stroke_style(rectangle, rectangle.style),
        "LineDrawing P14 or PathDrawing P17",
    )
    curve = QuadraticBezierDrawing((0, 0), (1, 0), (1, 1), _style(join="round"))
    _raises(ValueError, lambda: _validate_raster_stroke_style(curve, curve.style), "straight-edge primitives P15")

    def unsafe_path(style: DrawingStyle) -> PathDrawing:
        return PathDrawing(
            style,
            [
                PathCommand("M", [(53_687_090.0, 1.0)]),
                PathCommand("L", [(53_687_091.1, 1.0), (53_687_091.1, 2.0)]),
            ],
        )

    default = _style()
    _validate_raster_stroke_style(unsafe_path(default), default, 40.0)
    for neutral in (
        _style(join="round", limit=20.0),
        _style(join="bevel", limit=20.0),
        _style(limit=20.0, stroke="none"),
    ):
        _validate_raster_stroke_style(unsafe_path(neutral), neutral, 40.0)
    low = _style(limit=2.0)
    _raises(ValueError, lambda: _validate_raster_stroke_style(unsafe_path(low), low, 40.0), "safe coordinate range")

    dynamic_miter = "".join(("mi", "ter"))
    interned_miter = "miter"
    assert dynamic_miter == interned_miter and dynamic_miter is not interned_miter
    dynamic = _style(limit=20.0)
    dynamic._stroke_linejoin = dynamic_miter
    _raises(ValueError, lambda: _validate_raster_stroke_style(unsafe_path(dynamic), dynamic, 40.0), "safe coordinate range")
    curve_default = QuadraticBezierDrawing((0, 0), (1, 0), (1, 1), dynamic)
    dynamic._stroke_miterlimit = 10.0
    _validate_raster_stroke_style(curve_default, dynamic)


def _digest(path: PathDrawing) -> str:
    result = render_drawing_group(
        DrawingComponentGroup("mutation-path-stroke", [path]),
        Canvas(5.0, 5.0, "in"),
        dpi=20,
        supersample=1,
    )
    return hashlib.sha256(result.asset.data).hexdigest()


def _assert_public_outputs() -> None:
    outputs = {
        "default": _digest(_path(_style())),
        "round-cap": _digest(_path(_style(cap="round"))),
        "square-cap": _digest(_path(_style(cap="square"))),
        "round-join": _digest(_path(_style(join="round"))),
        "bevel-join": _digest(_path(_style(join="bevel"))),
        "low-miter": _digest(_path(_style(limit=1.0))),
        "high-miter": _digest(_path(_style(limit=20.0))),
        "closed": _digest(_path(_style(cap="round", join="round"), closed=True)),
        "filled": _digest(_path(_style(cap="square", join="bevel", fill="#80A0C0"))),
    }
    assert outputs["low-miter"] == outputs["bevel-join"]
    del outputs["low-miter"]
    assert len(set(outputs.values())) == len(outputs)

    translucent = PathDrawing(
        _style(join="bevel", fill="#80A0C0", stroke_opacity=0.5),
        [
            PathCommand("M", [(1.0, 1.0)]),
            PathCommand("L", [(4.0, 1.0), (2.5, 4.0)]),
        ],
    )
    result = render_drawing_group(
        DrawingComponentGroup("mutation-translucent-path-stroke", [translucent]),
        Canvas(5.0, 5.0, "in"),
        dpi=20,
        supersample=1,
    )
    with result.asset.image() as image:
        assert image.getpixel((20, 20)) == (72, 96, 120, 255)
        assert image.getpixel((0, 0)) == (0, 0, 0, 0)


def main() -> None:
    line_dash_main()
    line_cap_main()
    line_join_main()
    miter_validation_check()
    miter_point_dispatch_check()
    miter_geometry_check()
    miter_operations_check()
    _assert_sampling()
    _assert_topology()
    _assert_cap_geometry()
    _assert_stroke_dispatch()
    _assert_validation()
    _assert_public_outputs()


if __name__ == "__main__":
    main()
