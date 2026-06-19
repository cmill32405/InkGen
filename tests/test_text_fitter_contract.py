"""Tests for TextFitter proof obligations."""

from __future__ import annotations

import random

import matplotlib.font_manager as fm
import pytest
from shapely.affinity import translate as shapely_translate
from shapely.geometry import Point
from shapely.geometry import box as shapely_box

from InkGen.style import DrawingStyle
from InkGen.svg_generator import RegularPolygonSVG
from InkGen.text_fitter import FitterShape, TextBlock, TextFitter, component_to_fitter_shape

FONT_PATH = fm.findfont(fm.FontProperties(family="DejaVu Sans"))


@pytest.mark.condition("TEXT-FITTER-P1")
def test_text_fitter_fits_wrapped_text_inside_convex_shape() -> None:
    """TEXT-FITTER-P1: Successful fits return contained text geometry and metadata."""
    fitter = TextFitter(rng=random.Random(11))
    shape = FitterShape(
        polygon=shapely_box(0.0, 0.0, 180.0, 90.0),
        line_thickness_range=(2.0, 2.0),
        padding=3.0,
    )
    text_block = TextBlock(
        text="Synthetic drawing notes should wrap inside the drawing boundary.",
        font_path=FONT_PATH,
        font_size_range=(6, 18),
        min_font_size_px=6,
        max_line_width=85.0,
    )

    result = fitter.fit(text_block, shape)

    assert result is not None
    assert len(result.fitted_text_lines) > 1
    assert len(result.line_positions) == len(result.fitted_text_lines)
    assert len(result.line_widths) == len(result.fitted_text_lines)
    assert 6 <= result.font_size <= 18
    assert result.final_line_thickness == 2.0
    assert result.text_geometry is not None
    assert not result.text_geometry.is_empty
    assert shape.polygon.covers(result.text_geometry)
    assert shape.polygon.covers(result.text_convex_hull)
    assert result.text_bounding_box.equals(result.text_convex_hull)


@pytest.mark.condition("TEXT-FITTER-P1")
def test_text_fitter_returns_none_for_impossible_or_unsafe_fits() -> None:
    """TEXT-FITTER-P1: Impossible text fits fail closed without partial output."""
    fitter = TextFitter(rng=random.Random(12))

    excessive_padding = FitterShape(
        polygon=shapely_box(0.0, 0.0, 4.0, 4.0),
        line_thickness_range=(6.0, 6.0),
        padding=2.0,
    )
    ordinary_text = TextBlock(text="safe failure", font_path=FONT_PATH, font_size_range=(6, 8))
    assert fitter.fit(ordinary_text, excessive_padding) is None

    narrow_shape = FitterShape(
        polygon=shapely_box(0.0, 0.0, 10.0, 8.0),
        line_thickness_range=(1.0, 1.0),
        padding=1.0,
    )
    impossible_word = TextBlock(
        text="supercalifragilisticexpialidocious",
        font_path=FONT_PATH,
        font_size_range=(6, 8),
        min_font_size_px=6,
        max_line_width=4.0,
    )
    assert fitter.fit(impossible_word, narrow_shape) is None


@pytest.mark.condition("TEXT-FITTER-P1")
def test_text_fitter_uses_rectangle_fallback_when_outlines_are_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """TEXT-FITTER-P1: Missing glyph outlines fall back to conservative line boxes."""
    fitter = TextFitter(rng=random.Random(13))
    shape = FitterShape(
        polygon=shapely_box(0.0, 0.0, 120.0, 60.0),
        line_thickness_range=(1.0, 1.0),
        padding=2.0,
    )
    text_block = TextBlock(text="outline fallback", font_path=FONT_PATH, font_size_range=(6, 14))

    monkeypatch.setattr(fitter, "_create_line_outline", lambda *_args, **_kwargs: None)

    result = fitter.fit(text_block, shape)

    assert result is not None
    assert result.fitted_text_lines
    assert shape.polygon.covers(result.text_geometry)
    assert shape.polygon.covers(result.text_convex_hull)


@pytest.mark.condition("TEXT-FITTER-P1")
def test_text_fitter_jitter_accepts_contained_offsets_and_rejects_escape(monkeypatch: pytest.MonkeyPatch) -> None:
    """TEXT-FITTER-P1: Jitter changes positions only when the candidate remains contained."""
    shape = FitterShape(
        polygon=shapely_box(0.0, 0.0, 140.0, 70.0),
        line_thickness_range=(1.0, 1.0),
        padding=2.0,
    )
    text_block = TextBlock(text="jitter proof path", font_path=FONT_PATH, font_size_range=(6, 14))
    baseline = TextFitter(rng=random.Random(14)).fit(text_block, shape)
    assert baseline is not None

    accepting_fitter = TextFitter(rng=random.Random(14))

    def contained_offset(_inner, _outer, geometry, _jitter_x, _jitter_y, _safety_margin):
        shifted = shapely_translate(geometry, xoff=0.5, yoff=0.0)
        return 0.5, 0.0, shifted

    monkeypatch.setattr(accepting_fitter, "_compute_jitter_offsets", contained_offset)
    accepted = accepting_fitter.fit(text_block, shape, jitter_x=True)
    assert accepted is not None
    assert accepted.line_positions != baseline.line_positions
    assert shape.polygon.covers(accepted.text_geometry)

    accepting_y_fitter = TextFitter(rng=random.Random(14))

    def contained_y_offset(_inner, _outer, geometry, _jitter_x, _jitter_y, _safety_margin):
        shifted = shapely_translate(geometry, xoff=0.0, yoff=0.5)
        return 0.0, 0.5, shifted

    monkeypatch.setattr(accepting_y_fitter, "_compute_jitter_offsets", contained_y_offset)
    accepted_y = accepting_y_fitter.fit(text_block, shape, jitter_y=True)
    assert accepted_y is not None
    assert accepted_y.line_positions != baseline.line_positions
    assert shape.polygon.covers(accepted_y.text_geometry)

    rejecting_fitter = TextFitter(rng=random.Random(14))

    def escaping_offset(_inner, _outer, geometry, _jitter_x, _jitter_y, _safety_margin):
        shifted = shapely_translate(geometry, xoff=1_000.0, yoff=0.0)
        return 1_000.0, 0.0, shifted

    monkeypatch.setattr(rejecting_fitter, "_compute_jitter_offsets", escaping_offset)
    rejected = rejecting_fitter.fit(text_block, shape, jitter_x=True)
    assert rejected is not None
    assert rejected.line_positions == baseline.line_positions
    assert shape.polygon.covers(rejected.text_geometry)


@pytest.mark.condition("TEXT-FITTER-P1")
def test_text_fitter_jitter_margin_is_clamped_before_offset_calculation(monkeypatch: pytest.MonkeyPatch) -> None:
    """TEXT-FITTER-P1: Jitter margin is clamped to a non-negative safety value."""
    shape = FitterShape(polygon=shapely_box(0.0, 0.0, 140.0, 70.0), line_thickness_range=(1.0, 1.0), padding=2.0)
    text_block = TextBlock(text="jitter margin", font_path=FONT_PATH, font_size_range=(6, 14))
    observed_margins: list[float] = []

    def record_margin(_inner, _outer, geometry, _jitter_x, _jitter_y, safety_margin):
        observed_margins.append(safety_margin)
        return 0.0, 0.0, geometry

    negative_fitter = TextFitter(rng=random.Random(18))
    monkeypatch.setattr(negative_fitter, "_compute_jitter_offsets", record_margin)
    assert negative_fitter.fit(text_block, shape, jitter_x=True, jitter_margin=-2.0) is not None

    positive_fitter = TextFitter(rng=random.Random(18))
    monkeypatch.setattr(positive_fitter, "_compute_jitter_offsets", record_margin)
    assert positive_fitter.fit(text_block, shape, jitter_x=True, jitter_margin=0.25) is not None

    assert observed_margins == [0.0, 0.25]


@pytest.mark.condition("TEXT-FITTER-P1")
def test_text_fitter_binary_search_selects_largest_valid_font_size(monkeypatch: pytest.MonkeyPatch) -> None:
    """TEXT-FITTER-P1: Fit uses binary search to return the largest valid font size."""
    fitter = TextFitter(rng=random.Random(15))
    shape = FitterShape(polygon=shapely_box(0.0, 0.0, 80.0, 40.0), line_thickness_range=(1.0, 1.0), padding=1.0)
    text_block = TextBlock(text="binary search", font_path=FONT_PATH, font_size_range=(6, 14), min_font_size_px=6)
    geometry = shapely_box(10.0, 10.0, 20.0, 20.0)
    checked_sizes: list[int] = []

    def fake_check_fit(_text_block, _inner_boundary, font_size):
        checked_sizes.append(font_size)
        if font_size <= 11:
            return [("binary search", 10.0, 10.0, 10.0)], geometry
        return None

    monkeypatch.setattr(fitter, "_check_fit", fake_check_fit)
    monkeypatch.setattr(fitter, "_create_line_outline", lambda *_args, **_kwargs: geometry)

    result = fitter.fit(text_block, shape)

    assert result is not None
    assert result.font_size == 11
    assert checked_sizes == [10, 12, 11]
    assert result.fitted_text_lines == ["binary search"]
    assert result.text_convex_hull.equals(geometry.convex_hull)


@pytest.mark.condition("TEXT-FITTER-P1")
def test_text_fitter_enforces_minimum_font_size_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    """TEXT-FITTER-P1: Fits below the configured minimum font size fail closed."""
    fitter = TextFitter(rng=random.Random(16))
    shape = FitterShape(polygon=shapely_box(0.0, 0.0, 80.0, 40.0), line_thickness_range=(1.0, 1.0), padding=1.0)
    text_block = TextBlock(text="min threshold", font_path=FONT_PATH, font_size_range=(4, 6), min_font_size_px=7)
    geometry = shapely_box(10.0, 10.0, 20.0, 20.0)

    monkeypatch.setattr(fitter, "_check_fit", lambda *_args, **_kwargs: ([("min threshold", 10.0, 10.0, 10.0)], geometry))

    assert fitter.fit(text_block, shape) is None

    exact_min_block = TextBlock(text="exact threshold", font_path=FONT_PATH, font_size_range=(7, 7), min_font_size_px=7)
    exact_min_fitter = TextFitter(rng=random.Random(16))
    monkeypatch.setattr(exact_min_fitter, "_check_fit", lambda *_args, **_kwargs: ([("exact threshold", 10.0, 10.0, 10.0)], geometry))
    monkeypatch.setattr(exact_min_fitter, "_create_line_outline", lambda *_args, **_kwargs: geometry)
    exact_min_result = exact_min_fitter.fit(exact_min_block, shape)
    assert exact_min_result is not None
    assert exact_min_result.font_size == 7


@pytest.mark.condition("TEXT-FITTER-P1")
def test_text_fitter_word_wrap_uses_shape_width_and_centers_lines(monkeypatch: pytest.MonkeyPatch) -> None:
    """TEXT-FITTER-P1: Word wrap uses horizontal bounds and centers accepted lines."""
    fitter = TextFitter(rng=random.Random(17))
    inner = shapely_box(10.0, 2.0, 70.0, 42.0)

    class StubFont:
        def getlength(self, text: str) -> float:
            return len(text) * 10.0

        def getmetrics(self) -> tuple[int, int]:
            return 10, 2

    class WideStubFont:
        def getlength(self, text: str) -> float:
            return len(text) * 20.0

        def getmetrics(self) -> tuple[int, int]:
            return 10, 2

    class ExactWidthFont:
        def getlength(self, _text: str) -> float:
            return 60.0 / (25.4 / 96.0)

        def getmetrics(self) -> tuple[int, int]:
            return 10, 2

    monkeypatch.setattr(fitter, "_create_line_outline", lambda *_args, **_kwargs: None)

    wrapped = fitter._adaptive_word_wrap(
        "aa bb cc",
        inner_boundary=inner,
        font=StubFont(),  # type: ignore[arg-type]
        font_size=12,
        font_path=FONT_PATH,
        max_line_width=8.0,
    )

    assert wrapped is not None
    lines, geometry = wrapped
    assert [line for line, *_ in lines] == ["aa", "bb", "cc"]
    assert all(width <= 8.0 for *_position, width in lines)
    assert lines[0][1] == pytest.approx(40.0 - lines[0][3] / 2.0)
    line_height = (10 + 2) * (25.4 / 96.0)
    expected_first_baseline = inner.centroid.y - (3 * line_height) / 2.0 + 10 * (25.4 / 96.0)
    assert lines[0][2] == pytest.approx(expected_first_baseline)
    assert inner.covers(geometry)

    no_max_width = fitter._adaptive_word_wrap(
        "aa bb cc",
        inner_boundary=inner,
        font=StubFont(),  # type: ignore[arg-type]
        font_size=12,
        font_path=FONT_PATH,
        max_line_width=None,
    )
    assert no_max_width is not None
    no_max_lines, _ = no_max_width
    assert [line for line, *_ in no_max_lines] == ["aa bb cc"]

    asymmetric_height = fitter._adaptive_word_wrap(
        "aa bb cc",
        inner_boundary=inner,
        font=WideStubFont(),  # type: ignore[arg-type]
        font_size=12,
        font_path=FONT_PATH,
        max_line_width=None,
    )
    assert asymmetric_height is not None
    asymmetric_height_lines, _ = asymmetric_height
    assert [line for line, *_ in asymmetric_height_lines] == ["aa bb cc"]

    high_y_inner = shapely_box(10.0, 30.0, 70.0, 90.0)
    asymmetric_y_min = fitter._adaptive_word_wrap(
        "aa bb cc",
        inner_boundary=high_y_inner,
        font=WideStubFont(),  # type: ignore[arg-type]
        font_size=12,
        font_path=FONT_PATH,
        max_line_width=None,
    )
    assert asymmetric_y_min is not None
    asymmetric_y_lines, _ = asymmetric_y_min
    assert [line for line, *_ in asymmetric_y_lines] == ["aa bb cc"]

    exact_width = fitter._adaptive_word_wrap(
        "aa",
        inner_boundary=shapely_box(0.0, 0.0, 60.0, 40.0),
        font=ExactWidthFont(),  # type: ignore[arg-type]
        font_size=12,
        font_path=FONT_PATH,
        max_line_width=None,
    )
    assert exact_width is not None
    exact_lines, _ = exact_width
    assert [line for line, *_ in exact_lines] == ["aa"]


@pytest.mark.condition("TEXT-FITTER-P1")
def test_text_fitter_replaces_line_boxes_with_final_outline_geometry(monkeypatch: pytest.MonkeyPatch) -> None:
    """TEXT-FITTER-P1: Final outline correction updates result geometry and hull."""
    fitter = TextFitter(rng=random.Random(19))
    shape = FitterShape(polygon=shapely_box(0.0, 0.0, 80.0, 40.0), line_thickness_range=(1.0, 1.0), padding=1.0)
    text_block = TextBlock(text="outline correction", font_path=FONT_PATH, font_size_range=(8, 8), min_font_size_px=8)
    initial_geometry = shapely_box(1.0, 1.0, 2.0, 2.0)
    outline_geometry = shapely_box(10.0, 10.0, 20.0, 20.0)

    monkeypatch.setattr(fitter, "_check_fit", lambda *_args, **_kwargs: ([("outline correction", 10.0, 10.0, 10.0)], initial_geometry))
    monkeypatch.setattr(fitter, "_create_line_outline", lambda *_args, **_kwargs: outline_geometry)

    result = fitter.fit(text_block, shape)

    assert result is not None
    assert result.text_geometry.equals(outline_geometry)
    assert result.text_convex_hull.equals(outline_geometry.convex_hull)
    assert result.line_positions == [(10.0, 10.0)]


@pytest.mark.condition("TEXT-FITTER-P1")
def test_component_to_fitter_shape_uses_convex_hull_or_radius_contract() -> None:
    """TEXT-FITTER-P1: Component adapters derive fitting polygons from known geometry."""
    style = DrawingStyle("text_fitter_contract_polygon")
    polygon_component = RegularPolygonSVG(position=(50.0, 50.0), sides=6, radius=20.0, style=style)

    polygon_shape = component_to_fitter_shape(polygon_component, thickness_range=(2.0, 2.0), padding=3.0)
    assert polygon_shape is not None
    assert polygon_shape.line_thickness_range == (2.0, 2.0)
    assert polygon_shape.padding == 3.0
    assert polygon_shape.polygon.is_valid
    assert polygon_shape.polygon.area > 0.0

    class CircleStub:
        position = (10.0, 12.0)
        radius = 4.0

    circle_shape = component_to_fitter_shape(CircleStub())
    assert circle_shape is not None
    assert circle_shape.line_thickness_range == (1.0, 3.0)
    assert circle_shape.padding == 1.0
    assert circle_shape.polygon.covers(Point(10.0, 12.0))
    assert circle_shape.polygon.area > 0.0

    class EmptyStub:
        pass

    assert component_to_fitter_shape(EmptyStub()) is None
