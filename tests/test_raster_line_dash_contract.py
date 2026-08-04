"""RASTER-LINE-DASH-P13 conditions for dependency-free line dashes."""

from __future__ import annotations

import math
from itertools import count

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from InkGen import Canvas, DrawingComponentGroup, DrawingStyle, LineDrawing, RectangleDrawing, raster_renderer, render_drawing_group

_STYLE_IDS = count()


def _style(*, dasharray: tuple[float, ...] = (), offset: float = 0.0, opacity: float = 1.0) -> DrawingStyle:
    return DrawingStyle(
        f"dash-{next(_STYLE_IDS)}",
        stroke="#102030",
        fill="none",
        stroke_width=0.1,
        stroke_opacity=opacity,
        stroke_dasharray=dasharray,
        stroke_dash_offset=offset,
    )


def _x_intervals(
    pattern: tuple[float, ...],
    offset: float = 0.0,
    *,
    length: float = 10.0,
) -> list[tuple[float, float]]:
    normalized = pattern * 2 if len(pattern) % 2 else pattern
    return [(start[0], end[0]) for start, end in raster_renderer._line_dash_segments((0.0, 0.0), (length, 0.0), normalized, offset)]


@pytest.mark.condition("RASTER-LINE-DASH-P13")
def test_even_pattern_and_phase_partition_line_in_logical_units() -> None:
    """RASTER-LINE-DASH-P13: Pattern lengths and phase select exact line intervals."""
    assert _x_intervals((2.0, 1.0)) == [(0.0, 2.0), (3.0, 5.0), (6.0, 8.0), (9.0, 10.0)]
    assert _x_intervals((2.0, 1.0), 1.0) == [(0.0, 1.0), (2.0, 4.0), (5.0, 7.0), (8.0, 10.0)]
    assert _x_intervals((2.0, 1.0), 4.0) == _x_intervals((2.0, 1.0), 1.0)
    assert _x_intervals((1.0, 3.0), 2.0) != _x_intervals((1.0, 3.0), 0.0)
    assert _x_intervals((1.0, 1.0), 1_000_000_000.0, length=1.0) == [(0.0, 1.0)]


@pytest.mark.condition("RASTER-LINE-DASH-P13")
def test_odd_patterns_repeat_and_zero_slots_preserve_svg_pdf_parity() -> None:
    """RASTER-LINE-DASH-P13: Odd arrays double and zero slots advance without looping."""
    assert raster_renderer._validated_line_dash(_style(dasharray=(2.0, 1.0, 1.0))) == (
        (2.0, 1.0, 1.0, 2.0, 1.0, 1.0),
        0.0,
    )
    assert raster_renderer._validated_line_dash(_style(dasharray=(2.0, 1.0, 3.0, 4.0))) == (
        (2.0, 1.0, 3.0, 4.0),
        0.0,
    )
    assert _x_intervals((2.0, 1.0, 1.0)) == [(0.0, 2.0), (3.0, 4.0), (6.0, 7.0), (8.0, 10.0)]
    assert _x_intervals((0.0, 2.0)) == []
    assert _x_intervals((2.0, 0.0), length=5.0) == [(0.0, 2.0), (2.0, 4.0), (4.0, 5.0)]
    assert _x_intervals((1.0, 1.0, 2.0, 1.0), length=6.0) == [(0.0, 1.0), (2.0, 4.0), (5.0, 6.0)]


@pytest.mark.condition("RASTER-LINE-DASH-P13")
def test_degenerate_dashed_line_is_a_transparent_butt_cap_noop() -> None:
    """RASTER-LINE-DASH-P13: A zero-length dashed line emits no painted segment."""
    assert raster_renderer._line_dash_segments((2.0, 3.0), (2.0, 3.0), (1.0, 1.0), 0.0) == []


@pytest.mark.condition("RASTER-LINE-DASH-P13")
def test_public_render_path_paints_dashes_gaps_phase_and_alpha() -> None:
    """RASTER-LINE-DASH-P13: Public RGBA output preserves dashes and stroke opacity."""
    lines = [
        LineDrawing((0.0, 0.5), (1.0, 0.5), _style(dasharray=(0.2, 0.2), opacity=0.5)),
        LineDrawing((0.0, 0.8), (1.0, 0.8), _style(dasharray=(0.2, 0.2), offset=0.2)),
    ]
    result = render_drawing_group(DrawingComponentGroup("dashes", lines), Canvas(1.2, 1.0, "in"), dpi=10, supersample=1)
    with result.asset.image() as image:
        assert image.getpixel((1, 5)) == (16, 32, 48, 128)
        assert image.getpixel((3, 5)) == (0, 0, 0, 0)
        assert image.getpixel((0, 8)) == (0, 0, 0, 0)
        assert image.getpixel((3, 8)) == (16, 32, 48, 255)


@pytest.mark.condition("RASTER-LINE-DASH-P13")
def test_non_line_dashes_and_orphan_phase_remain_outside_closed_domain() -> None:
    """RASTER-LINE-DASH-P13: The slice does not silently broaden other primitives."""
    rectangle = RectangleDrawing((0, 0), 1, 1, 0, _style(dasharray=(1.0, 1.0)))
    orphan_phase = LineDrawing((0, 0), (1, 0), _style(offset=1.0))
    with pytest.raises(ValueError, match="supported only for raster LineDrawing P13"):
        render_drawing_group(DrawingComponentGroup("rectangle", [rectangle]), Canvas(2, 2, "in"), dpi=10)
    with pytest.raises(ValueError, match="offset requires a nonempty dash array"):
        render_drawing_group(DrawingComponentGroup("phase", [orphan_phase]), Canvas(2, 2, "in"), dpi=10)


@pytest.mark.condition("RASTER-LINE-DASH-P13")
@pytest.mark.parametrize(
    ("attribute", "value", "error"),
    [
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
    ],
)
def test_live_dash_corruption_fails_before_surface_allocation(
    monkeypatch: pytest.MonkeyPatch,
    attribute: str,
    value: object,
    error: type[Exception],
) -> None:
    """RASTER-LINE-DASH-P13: Mutable style corruption cannot reach Pillow allocation."""
    style = _style(dasharray=(1.0, 1.0))
    setattr(style, attribute, value)
    monkeypatch.setattr(raster_renderer.Image, "new", lambda *args, **kwargs: pytest.fail("surface allocated"))
    line = LineDrawing((0, 0), (1, 0), style)
    with pytest.raises(error):
        render_drawing_group(DrawingComponentGroup("invalid", [line]), Canvas(2, 2, "in"), dpi=10)


@pytest.mark.condition("RASTER-LINE-DASH-P13")
def test_pathological_dash_count_fails_before_surface_allocation(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASTER-LINE-DASH-P13: Tiny periods cannot create unbounded paint operations."""
    style = _style(dasharray=(0.000001, 0.000001))
    monkeypatch.setattr(raster_renderer.Image, "new", lambda *args, **kwargs: pytest.fail("surface allocated"))
    line = LineDrawing((0, 0), (1, 0), style)
    with pytest.raises(ValueError, match="100,000-step limit"):
        render_drawing_group(DrawingComponentGroup("bounded", [line]), Canvas(2, 2, "in"), dpi=10)


@pytest.mark.condition("RASTER-LINE-DASH-P13")
def test_dash_step_limit_accepts_exact_boundary_and_rejects_next_step(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASTER-LINE-DASH-P13: The operation bound has an exact inclusive boundary."""
    monkeypatch.setattr(raster_renderer, "_MAX_DASH_STEPS", 3)
    assert _x_intervals((1.0, 1.0), length=3.0) == [(0.0, 1.0), (2.0, 3.0)]
    with pytest.raises(ValueError, match="3-step limit"):
        _x_intervals((1.0, 1.0), length=4.0)


@pytest.mark.condition("RASTER-LINE-DASH-P13")
@settings(max_examples=100, deadline=None)
@given(
    length=st.floats(min_value=0.01, max_value=100.0, allow_nan=False, allow_infinity=False),
    pattern=st.lists(
        st.floats(min_value=0.01, max_value=10.0, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=6,
    ),
    offset=st.floats(min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
)
def test_dash_segments_are_ordered_bounded_and_on_the_source_line(length: float, pattern: list[float], offset: float) -> None:
    """RASTER-LINE-DASH-P13: All generated intervals are ordered subsets of the line."""
    normalized = tuple(pattern * 2 if len(pattern) % 2 else pattern)
    segments = raster_renderer._line_dash_segments((0.0, 2.0), (length, 2.0), normalized, offset)
    previous_end = 0.0
    for start, end in segments:
        assert 0.0 <= start[0] < end[0] <= length
        assert start[0] >= previous_end
        assert start[1] == end[1] == 2.0
        previous_end = end[0]
