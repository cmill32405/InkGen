"""RASTER-ARC-P4 conditions for neutral elliptical-arc raster rendering."""

from __future__ import annotations

from uuid import uuid4

import pytest

import InkGen.raster_renderer as raster_renderer
from InkGen.baird import BairdParams
from InkGen.boundary import Canvas
from InkGen.component import Arc
from InkGen.drawing_components import ArcDrawing, DrawingComponentGroup
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
        f"raster_arc_{uuid4().hex}",
        stroke=stroke,
        fill=fill,
        stroke_width=stroke_width,
        fill_opacity=fill_opacity,
    )


@pytest.mark.condition("RASTER-ARC-P4")
def test_rotated_arc_renders_through_public_scan_path() -> None:
    """RASTER-ARC-P4: Neutral arcs reach clean and Baird-degraded assets."""
    arc = ArcDrawing((2.0, 1.5), 1.25, 0.75, -45.0, 225.0, _style(stroke="#102030"), rotation=20.0)

    result = render_and_degrade_drawing_group(
        DrawingComponentGroup("arc", [arc]),
        Canvas(4, 3, "in"),
        BairdParams.clean(),
        seed=7,
        background_rgb=(255, 255, 255),
        dpi=20,
        render_supersample=2,
    )

    assert result.clean.component_count == 1
    with result.clean.asset.image() as clean:
        assert clean.getbbox() is not None
    with result.degraded.asset.image() as degraded:
        assert degraded.getbbox() == (0, 0, 80, 60)
        assert degraded.getextrema() != ((255, 255), (255, 255), (255, 255))


class _RecordingDraw:
    """Record Pillow polyline calls for exact dependency assertions."""

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


@pytest.mark.condition("RASTER-ARC-P4")
@pytest.mark.parametrize(
    ("start_angle", "end_angle", "rotation"),
    [(0.0, 90.0, 0.0), (120.0, -30.0, 0.0), (-45.0, 225.0, 37.5)],
)
def test_raster_arc_reuses_established_shared_sample_points(
    monkeypatch: pytest.MonkeyPatch,
    start_angle: float,
    end_angle: float,
    rotation: float,
) -> None:
    """RASTER-ARC-P4: Raster output consumes canonical Arc points exactly."""
    style = _style(stroke="#123456", stroke_width=0.5)
    arc = ArcDrawing((5.0, 7.0), 3.0, 2.0, start_angle, end_angle, style, rotation)
    recorder = _RecordingDraw()
    monkeypatch.setattr(raster_renderer.ImageDraw, "Draw", lambda surface: recorder)

    raster_renderer._render_component(object(), arc, 10.0)  # type: ignore[arg-type]

    expected = Arc(
        arc.center,
        arc.radius_x,
        arc.radius_y,
        arc.start_angle,
        arc.end_angle,
        style,
        arc.rotation,
    ).points
    assert recorder.calls == [([raster_renderer._scaled_point(point, 10.0) for point in expected], (18, 52, 86, 255), 5)]
    assert len(recorder.calls[0][0]) == 33


@pytest.mark.condition("RASTER-ARC-P4")
def test_zero_span_arc_matches_open_path_transparent_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASTER-ARC-P4: A move-only zero-span arc does not invent a painted dot."""
    arc = ArcDrawing((1.0, 1.0), 0.5, 0.25, 30.0, 30.0, _style(stroke="#123456"))
    recorder = _RecordingDraw()
    monkeypatch.setattr(raster_renderer.ImageDraw, "Draw", lambda surface: recorder)

    raster_renderer._render_component(object(), arc, 10.0)  # type: ignore[arg-type]

    assert recorder.calls == []


@pytest.mark.condition("RASTER-ARC-P4")
def test_minimal_two_point_open_polyline_is_painted() -> None:
    """RASTER-ARC-P4: The shared open-curve helper paints its minimal path."""
    recorder = _RecordingDraw()

    raster_renderer._draw_curve(recorder, [(1.0, 2.0), (3.0, 4.0)], 10.0, (1, 2, 3, 4), 2)  # type: ignore[arg-type]

    assert recorder.calls == [([(10, 20), (30, 40)], (1, 2, 3, 4), 2)]


@pytest.mark.condition("RASTER-ARC-P4")
def test_visible_arc_fill_fails_instead_of_silently_closing_open_arc() -> None:
    """RASTER-ARC-P4: Open arc fills remain outside the raster domain."""
    arc = ArcDrawing((1.0, 1.0), 0.5, 0.25, 0.0, 90.0, _style(fill="#abcdef"))

    with pytest.raises(ValueError, match="arc fills are not supported"):
        render_drawing_group(DrawingComponentGroup("filled", [arc]), Canvas(2, 2, "in"), dpi=20)


@pytest.mark.condition("RASTER-ARC-P4")
def test_transparent_arc_fill_is_not_treated_as_visible() -> None:
    """RASTER-ARC-P4: Zero-opacity fill does not exclude a stroked arc."""
    arc = ArcDrawing(
        (1.0, 1.0),
        0.5,
        0.25,
        0.0,
        180.0,
        _style(stroke="#123456", fill="#abcdef", fill_opacity=0.0),
    )

    result = render_drawing_group(DrawingComponentGroup("transparent fill", [arc]), Canvas(2, 2, "in"), dpi=20)

    assert result.component_count == 1
    with result.asset.image() as image:
        assert image.getbbox() is not None


@pytest.mark.condition("RASTER-ARC-P4")
def test_no_stroke_arc_is_valid_transparent_noop() -> None:
    """RASTER-ARC-P4: A valid unpainted arc does not invent visible pixels."""
    arc = ArcDrawing((1.0, 1.0), 0.5, 0.25, 0.0, 180.0, _style(stroke="none", stroke_width=0.0))

    result = render_drawing_group(DrawingComponentGroup("invisible", [arc]), Canvas(2, 2, "in"), dpi=20)

    assert result.component_count == 1
    with result.asset.image() as image:
        assert image.getbbox() is None
