"""RASTER-CURVE-P2 conditions for neutral Bezier raster rendering."""

from __future__ import annotations

from uuid import uuid4

import pytest

import InkGen.raster_renderer as raster_renderer
from InkGen.baird import BairdParams
from InkGen.boundary import Canvas
from InkGen.component import CubicBezier, QuadraticBezier
from InkGen.drawing_components import (
    CubicBezierDrawing,
    DrawingComponentGroup,
    QuadraticBezierDrawing,
)
from InkGen.raster_renderer import render_and_degrade_drawing_group, render_drawing_group
from InkGen.style import DrawingStyle


def _style(
    *,
    stroke: str = "#000000",
    fill: str = "none",
    stroke_width: float = 0.08,
    fill_opacity: float = 1.0,
) -> DrawingStyle:
    return DrawingStyle(
        f"raster_curve_{uuid4().hex}",
        stroke=stroke,
        fill=fill,
        stroke_width=stroke_width,
        fill_opacity=fill_opacity,
    )


def _curves(style: DrawingStyle) -> list[QuadraticBezierDrawing | CubicBezierDrawing]:
    return [
        QuadraticBezierDrawing((0.5, 2.5), (2.0, 0.25), (3.5, 2.5), style),
        CubicBezierDrawing((0.5, 0.5), (1.0, 2.5), (3.0, 2.5), (3.5, 0.5), style),
    ]


@pytest.mark.condition("RASTER-CURVE-P2")
def test_quadratic_and_cubic_curves_render_through_public_scan_path() -> None:
    """RASTER-CURVE-P2: Neutral curves reach clean and Baird-degraded assets."""
    group = DrawingComponentGroup("curves", _curves(_style(stroke="#102030")))

    result = render_and_degrade_drawing_group(
        group,
        Canvas(4, 3, "in"),
        BairdParams.clean(),
        seed=7,
        background_rgb=(255, 255, 255),
        dpi=20,
        render_supersample=2,
    )

    assert result.clean.component_count == 2
    with result.clean.asset.image() as clean:
        assert clean.getbbox() is not None
        assert clean.getpixel((10, 50))[3] > 0
        assert clean.getpixel((70, 10))[3] > 0
    with result.degraded.asset.image() as degraded:
        assert degraded.getbbox() == (0, 0, 80, 60)
        assert degraded.getpixel((10, 50)) != (255, 255, 255)


class _RecordingDraw:
    """Record Pillow polyline calls for exact dependency-contract assertions."""

    def __init__(self) -> None:
        self.calls: list[tuple[list[tuple[int, int]], tuple[int, int, int, int], int]] = []

    def line(
        self,
        points: list[tuple[int, int]],
        *,
        fill: tuple[int, int, int, int],
        width: int,
    ) -> None:
        self.calls.append((points, fill, width))


@pytest.mark.condition("RASTER-CURVE-P2")
def test_raster_curves_reuse_established_shared_sample_points(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASTER-CURVE-P2: Raster polylines consume the shared 33-point geometry."""
    style = _style(stroke="#123456", stroke_width=0.5)
    quadratic, cubic = _curves(style)
    recorder = _RecordingDraw()
    monkeypatch.setattr(raster_renderer.ImageDraw, "Draw", lambda surface: recorder)

    raster_renderer._render_component(object(), quadratic, 10.0)  # type: ignore[arg-type]
    raster_renderer._render_component(object(), cubic, 10.0)  # type: ignore[arg-type]

    expected_quadratic = QuadraticBezier(
        quadratic.start_point,
        quadratic.control_point,
        quadratic.end_point,
        style,
    ).points
    expected_cubic = CubicBezier(
        cubic.start_point,
        cubic.control_point1,
        cubic.control_point2,
        cubic.end_point,
        style,
    ).points
    assert recorder.calls == [
        ([raster_renderer._scaled_point(point, 10.0) for point in expected_quadratic], (18, 52, 86, 255), 5),
        ([raster_renderer._scaled_point(point, 10.0) for point in expected_cubic], (18, 52, 86, 255), 5),
    ]
    assert len(recorder.calls[0][0]) == len(recorder.calls[1][0]) == 33


@pytest.mark.condition("RASTER-CURVE-P2")
@pytest.mark.parametrize("curve_index", [0, 1])
def test_curve_fills_fail_instead_of_silently_closing_open_curves(curve_index: int) -> None:
    """RASTER-CURVE-P2: Open curve fills remain outside the declared raster domain."""
    curve = _curves(_style(fill="#abcdef"))[curve_index]

    with pytest.raises(ValueError, match="curve fills are not supported"):
        render_drawing_group(DrawingComponentGroup("filled", [curve]), Canvas(4, 3, "in"), dpi=20)


@pytest.mark.condition("RASTER-CURVE-P2")
def test_transparent_curve_fill_is_not_treated_as_visible() -> None:
    """RASTER-CURVE-P2: Zero-opacity fill does not exclude a stroked curve."""
    result = render_drawing_group(
        DrawingComponentGroup(
            "transparent_fill",
            _curves(_style(stroke="#123456", fill="#abcdef", fill_opacity=0.0)),
        ),
        Canvas(4, 3, "in"),
        dpi=20,
    )

    assert result.component_count == 2
    with result.asset.image() as image:
        assert image.getpixel((10, 50))[3] > 0


@pytest.mark.condition("RASTER-CURVE-P2")
def test_no_stroke_curves_are_valid_transparent_noops() -> None:
    """RASTER-CURVE-P2: A valid unpainted curve does not invent visible pixels."""
    result = render_drawing_group(
        DrawingComponentGroup("invisible", _curves(_style(stroke="none", stroke_width=0.0))),
        Canvas(4, 3, "in"),
        dpi=20,
    )

    assert result.component_count == 2
    with result.asset.image() as image:
        assert image.getbbox() is None
