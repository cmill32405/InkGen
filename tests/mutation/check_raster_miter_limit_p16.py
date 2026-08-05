"""Fast deterministic witnesses for raster miter-limit P16 mutation workers."""

from __future__ import annotations

import hashlib
import math
from itertools import count

from InkGen.boundary import Canvas
from InkGen.drawing_components import (
    CircleDrawing,
    DrawingComponentGroup,
    LineDrawing,
    PathDrawing,
    PolygonalDrawing,
    QuadraticBezierDrawing,
    RectangleDrawing,
    RegularPolygonDrawing,
)
from InkGen.raster_renderer import (
    _MAX_RASTER_COORDINATE,
    _bounded_join_polygon,
    _draw_joined_polyline,
    _draw_polygon,
    _has_visible_stroke,
    _miter_join_polygon,
    _nondefault_miter_points,
    _validate_miter_geometry,
    _validate_raster_stroke_style,
    _validated_scaled_stroke_width,
    render_drawing_group,
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


def _style(
    limit: float = 10.0,
    *,
    join: str = "miter",
    stroke: str = "#102030",
    width: float = 0.6,
    opacity: float = 1.0,
) -> DrawingStyle:
    return DrawingStyle(
        f"mutation-miter-{next(_STYLE_IDS)}",
        fill="none",
        stroke=stroke,
        stroke_width=width,
        stroke_opacity=opacity,
        stroke_linejoin=join,
        stroke_miterlimit=limit,
    )


def _raises(error: type[Exception], call: object, text: str | None = None) -> None:
    try:
        call()  # type: ignore[operator]
    except error as exc:
        if text is not None:
            assert text in str(exc)
        return
    raise AssertionError(f"expected {error.__name__}")


def _assert_validation() -> None:
    style = _style(2.0)
    polygon = PolygonalDrawing([(0, 0), (1, 0), (1, 1)], style)
    _validate_raster_stroke_style(polygon, style, 20.0)
    assert _has_visible_stroke(style)
    assert _validated_scaled_stroke_width(style, 20.0) == 12

    for invisible in (
        _style(2.0, stroke="none"),
        _style(2.0, opacity=0.0),
        _style(2.0, width=0.0),
    ):
        assert not _has_visible_stroke(invisible)
        _validate_raster_stroke_style(PathDrawing(invisible), invisible, 20.0)

    for value, error in ((object(), TypeError), (math.nan, ValueError), (math.inf, ValueError), (0.0, ValueError), (-1.0, ValueError)):
        corrupt = _style()
        corrupt._stroke_miterlimit = value
        _raises(error, lambda item=corrupt: _validate_raster_stroke_style(polygon, item))

    for component in (
        PathDrawing(_style(2.0)),
        QuadraticBezierDrawing((0, 0), (1, 0), (1, 1), _style(2.0)),
    ):
        _raises(
            ValueError,
            lambda item=component: _validate_raster_stroke_style(item, item.style),
            "straight-edge primitives P16",
        )

    for component in (
        LineDrawing((0, 0), (1, 0), _style(2.0)),
        CircleDrawing((1, 1), 1, _style(2.0)),
        RectangleDrawing((0, 0), 1, 1, 0.2, _style(2.0)),
        RegularPolygonDrawing((1, 1), 4, 1, _style(2.0), corner_radius=0.2),
    ):
        _validate_raster_stroke_style(component, component.style)

    huge = _style(2.0, width=_MAX_RASTER_COORDINATE)
    _raises(ValueError, lambda: _validated_scaled_stroke_width(huge, 2.0), "safe coordinate range")


def _assert_point_dispatch() -> None:
    rectangle = RectangleDrawing((1, 2), 3, 4, 0, _style(2.0))
    assert _nondefault_miter_points(rectangle, 2.0) == [(2, 4), (8, 4), (8, 12), (2, 12)]
    assert _nondefault_miter_points(RectangleDrawing((1, 2), 3, 4, 0.5, _style(2.0)), 2.0) == []
    polygon = PolygonalDrawing([(0, 0), (1, 0), (1, 1)], _style(2.0))
    assert _nondefault_miter_points(polygon, 3.0) == [(0, 0), (3, 0), (3, 3)]
    assert len(_nondefault_miter_points(RegularPolygonDrawing((2, 2), 3, 1, _style(2.0)), 2.0)) == 3
    assert _nondefault_miter_points(LineDrawing((0, 0), (1, 0), _style(2.0)), 2.0) == []
    assert _nondefault_miter_points(CircleDrawing((1, 1), 1, _style(2.0)), 2.0) == []
    _validate_miter_geometry([], 4, 2.0)
    _validate_miter_geometry([(0, 0)], 4, 2.0)
    _validate_miter_geometry([(0, 0), (10, 0), (10, 10)], 4, 2.0)


def _assert_geometry() -> None:
    points = (0.0, 10.0), (10.0, 10.0), (10.0, 20.0)
    bevel = _miter_join_polygon(*points, 4, 1.0)
    assert bevel == [(10.0, 10.0), (10.0, 8.0), (12.0, 10.0)]
    miter = _miter_join_polygon(*points, 4, math.sqrt(2.0))
    assert miter[:2] == [(10.0, 10.0), (10.0, 8.0)]
    assert math.dist((10.0, 10.0), miter[2]) == 2.0 * math.sqrt(2.0)
    assert miter[2][0] == 12.0 and abs(miter[2][1] - 8.0) < 1e-12
    assert miter[3] == (12.0, 10.0)

    reverse = _miter_join_polygon((0.0, 0.0), (1.0, 0.0), (0.0, 1e-12), 10, 2.0)
    assert len(reverse) == 3
    assert all(math.isfinite(value) and abs(value) < 10.0 for point in reverse for value in point)
    assert _miter_join_polygon((0, 0), (0, 0), (1, 1), 4, 2.0) == []
    assert _miter_join_polygon((0, 0), (1, 1), (2, 2), 4, 2.0) == []
    assert _bounded_join_polygon([(0.0, -_MAX_RASTER_COORDINATE)]) == [(0.0, -_MAX_RASTER_COORDINATE)]
    for value in (math.nan, math.inf, _MAX_RASTER_COORDINATE + 1.0, -_MAX_RASTER_COORDINATE - 1.0):
        _raises(ValueError, lambda item=value: _bounded_join_polygon([(item, 0.0)]), "safe coordinate range")


def _assert_operations() -> None:
    points = [(0.0, 10.0), (10.0, 10.0), (10.0, 20.0)]
    low = _RecordingDraw()
    _draw_joined_polyline(low, points, STROKE, 4, "miter", 1.0, closed=False)  # type: ignore[arg-type]
    assert low.calls == [
        ("line", points[:2], STROKE, 4),
        ("line", points[1:], STROKE, 4),
        ("polygon", [(10.0, 10.0), (10.0, 8.0), (12.0, 10.0)], STROKE),
    ]
    high = _RecordingDraw()
    _draw_joined_polyline(high, points, STROKE, 4, "miter", math.sqrt(2.0), closed=False)  # type: ignore[arg-type]
    assert high.calls[:2] == low.calls[:2]
    assert high.calls[2][0] == "polygon" and len(high.calls[2][1]) == 4  # type: ignore[arg-type]

    default = _RecordingDraw()
    _draw_polygon(default, [(1, 2), (3, 4)], 2.0, None, STROKE, 4)  # type: ignore[arg-type]
    assert default.calls == [("line", [(2, 4), (6, 8), (2, 4)], STROKE, 4)]
    bounded = _RecordingDraw()
    _draw_polygon(bounded, [(0, 1), (1, 0), (2, 1)], 10.0, None, STROKE, 4, "miter", 1.0)  # type: ignore[arg-type]
    assert len(bounded.calls) == 6
    assert [call[0] for call in bounded.calls] == ["line", "line", "line", "polygon", "polygon", "polygon"]


def _render_digest(component: object) -> str:
    group = DrawingComponentGroup("mutation-miter", [component])  # type: ignore[list-item]
    return hashlib.sha256(render_drawing_group(group, Canvas(2, 2, "in"), dpi=20, supersample=1).asset.data).hexdigest()


def _assert_dispatch() -> None:
    outputs: dict[tuple[str, float], str] = {}
    for limit in (1.0, 20.0):
        components = {
            "rectangle": RectangleDrawing((0.5, 0.5), 1.0, 1.0, 0.0, _style(limit, width=0.8)),
            "polygon": PolygonalDrawing([(0.4, 1.6), (1.0, 0.4), (1.6, 1.6)], _style(limit, width=0.8)),
            "regular": RegularPolygonDrawing((1.0, 1.0), 4, 0.7, _style(limit, width=0.8), angle=45.0),
        }
        for name, component in components.items():
            outputs[name, limit] = _render_digest(component)
    assert all(outputs[name, 1.0] != outputs[name, 20.0] for name in ("rectangle", "polygon", "regular"))
    assert outputs == {
        ("rectangle", 1.0): "4173d7bf490422f0db9de43e8b71ec4859721d490acfa86420c23b240a9f47ad",
        ("polygon", 1.0): "f7fb51d7ada40a562c23ace65be3876398010636410e159e3f47720389052bf5",
        ("regular", 1.0): "4173d7bf490422f0db9de43e8b71ec4859721d490acfa86420c23b240a9f47ad",
        ("rectangle", 20.0): "6b7350cad13022cc77f3de1b7e8720735a60326a05109840b72b0bde95fb95ec",
        ("polygon", 20.0): "d513d2361e4bd7eb20bbc02329d080ddf86e372c05c041505e92ff3ea2ec90fe",
        ("regular", 20.0): "6b7350cad13022cc77f3de1b7e8720735a60326a05109840b72b0bde95fb95ec",
    }

    neutral = []
    for limit in (1.0, 100.0):
        neutral.append(_render_digest(PolygonalDrawing([(0.4, 1.6), (1.0, 0.4), (1.6, 1.6)], _style(limit, join="round"))))
    assert neutral[0] == neutral[1]


def main() -> None:
    _assert_validation()
    _assert_point_dispatch()
    _assert_geometry()
    _assert_operations()
    _assert_dispatch()


if __name__ == "__main__":
    main()
