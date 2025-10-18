"""
Unit Tests for the TextFitter utility.
"""
import random

import matplotlib.pyplot as plt
import pytest
from shapely.affinity import translate as shapely_translate
from shapely.errors import TopologicalError
from shapely.geometry import (
    GeometryCollection,
    MultiPolygon,
    Point,
    Polygon as ShapelyPolygon,
    box as shapely_box,
)

import InkGen.text_fitter as text_fitter_module
from InkGen.text_fitter import (
    TextFitter,
    FitterShape,
    TextBlock,
    PX_TO_MM,
    component_to_fitter_shape,
    plot_polygon,
    save_debug_image,
)
from InkGen.svg_generator import RegularPolygonSVG
from InkGen.style import DrawingStyle

FONT_PATH = "C:/Windows/Fonts/arial.ttf"


@pytest.fixture
def text_fitter_instance():
    """Provides a reusable TextFitter instance for tests."""
    return TextFitter()


def test_calculate_inner_boundary_simple(text_fitter_instance):
    square = ShapelyPolygon([(0, 0), (100, 0), (100, 100), (0, 100)])
    shape = FitterShape(polygon=square, line_thickness_range=(2, 2), padding=5)
    inner_boundary, _ = text_fitter_instance._calculate_inner_boundary(shape)
    expected = ShapelyPolygon([(6, 6), (94, 6), (94, 94), (6, 94)])
    assert inner_boundary.equals(expected)


def test_component_to_fitter_shape():
    dummy_style = DrawingStyle("dummy")
    inkgen_shape = RegularPolygonSVG(position=(50, 50), sides=6, radius=50, style=dummy_style)
    fitter_shape = component_to_fitter_shape(inkgen_shape)
    assert fitter_shape is not None
    assert isinstance(fitter_shape.polygon, ShapelyPolygon)
    assert fitter_shape.polygon.area > 0


def test_fit_in_rectangle(text_fitter_instance):
    """Tests fitting and wrapping inside a simple rectangle."""
    rect = ShapelyPolygon([(0, 0), (200, 0), (200, 100), (0, 100)])
    shape = FitterShape(polygon=rect, padding=2)
    text_block = TextBlock(
        text="This is a moderately long sentence that should wrap to multiple lines.",
        font_path=FONT_PATH,
    )
    result = text_fitter_instance.fit(text_block, shape)
    assert result is not None
    assert len(result.fitted_text_lines) > 1
    assert result.font_size > 6
    assert result.text_geometry is not None
    assert not result.text_geometry.is_empty
    assert shape.polygon.contains(result.text_convex_hull)
    assert shape.polygon.contains(result.text_bounding_box)
    assert result.text_convex_hull.equals(result.text_bounding_box)


def test_fit_in_triangle(text_fitter_instance):
    """Tests fitting text inside a non-rectangular shape."""
    triangle = ShapelyPolygon([(100, 0), (200, 200), (0, 200)])
    shape = FitterShape(polygon=triangle, padding=5)
    text_block = TextBlock(text="Hello", font_path=FONT_PATH)
    result = text_fitter_instance.fit(text_block, shape)
    assert result is not None
    assert len(result.fitted_text_lines) == 1
    assert result.text_geometry is not None
    assert not result.text_geometry.is_empty
    assert shape.polygon.contains(result.text_convex_hull)
    assert shape.polygon.contains(result.text_bounding_box)
    assert result.text_convex_hull.equals(result.text_bounding_box)


def test_fail_to_fit(text_fitter_instance):
    """Tests that the fit method returns None when text cannot possibly fit."""
    small_box = ShapelyPolygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    shape = FitterShape(polygon=small_box, padding=1)
    text_block = TextBlock(text="This text is far too long", font_path=FONT_PATH)
    result = text_fitter_instance.fit(text_block, shape)
    assert result is None


def test_plot_polygon_handles_variants():
    fig, ax = plt.subplots()
    plot_polygon(ax, ShapelyPolygon(), "red", "empty")
    multi = MultiPolygon([shapely_box(0, 0, 1, 1), shapely_box(2, 2, 3, 3)])
    plot_polygon(ax, multi, "blue", "multi")
    plot_polygon(ax, shapely_box(0, 0, 1, 1), "green", "single")
    plt.close(fig)


def test_save_debug_image_creates_png(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    boundary = shapely_box(0, 0, 5, 5)
    text_poly = shapely_box(1, 1, 3, 3)
    save_debug_image(boundary, text_poly, font_size=12, text="DebugImage")
    files = list((tmp_path / "debug_images").glob("debug_fit_fail_*.png"))
    assert files


def test_get_pil_font_fallback_on_missing_file(text_fitter_instance):
    font = text_fitter_instance._get_pil_font("C:/missing_font_file.ttf", 12)
    assert hasattr(font, "getlength")


def test_polygon_from_coords_error_and_fixups(text_fitter_instance):
    assert text_fitter_instance._polygon_from_coords([(0, 0), (1, 0)]) is None
    invalid = [(0, 0), (2, 2), (0, 2), (2, 0), (0, 0)]
    polygon = text_fitter_instance._polygon_from_coords(invalid)
    assert polygon is not None
    assert polygon.is_valid


def test_create_line_outline_whitespace_returns_none(text_fitter_instance):
    assert text_fitter_instance._create_line_outline("   ", FONT_PATH, 12, 0.0, 0.0) is None


def test_create_line_outline_handles_outline_error(monkeypatch, text_fitter_instance):
    monkeypatch.setattr(text_fitter_module, "outline_for_text", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("fail")))
    assert text_fitter_instance._create_line_outline("Text", FONT_PATH, 12, 0.0, 0.0) is None


def test_create_line_outline_uses_bbox(monkeypatch, text_fitter_instance):
    def fake_outline(*args, **kwargs):
        return {
            "convex_hull": [],
            "bbox": [(0.0, 0.0), (2.0, 0.0), (2.0, 1.0), (0.0, 1.0)],
        }

    monkeypatch.setattr(text_fitter_module, "outline_for_text", fake_outline)
    polygon = text_fitter_instance._create_line_outline("Box", FONT_PATH, 10, 0.0, 0.0)
    assert polygon is not None
    assert pytest.approx(polygon.area, rel=1e-6) == pytest.approx((2.0 * PX_TO_MM) * (1.0 * PX_TO_MM), rel=1e-6)


def test_merge_polygons_geometry_collection(monkeypatch, text_fitter_instance):
    monkeypatch.setattr(text_fitter_module, "unary_union", lambda polys: GeometryCollection())
    assert text_fitter_instance._merge_polygons([shapely_box(0, 0, 1, 1)]) is None


def test_merge_polygons_invalid_buffer(monkeypatch, text_fitter_instance):
    class DummyGeom:
        geom_type = "Polygon"
        is_empty = False
        is_valid = False

        def buffer(self, *_args, **_kwargs):
            raise TopologicalError("boom")

    monkeypatch.setattr(text_fitter_module, "unary_union", lambda polys: DummyGeom())
    assert text_fitter_instance._merge_polygons([shapely_box(0, 0, 1, 1)]) is None


def test_adaptive_word_wrap_blank_text(text_fitter_instance):
    font = text_fitter_instance._get_pil_font(FONT_PATH, 12)
    assert text_fitter_instance._adaptive_word_wrap("", shapely_box(0, 0, 10, 10), font, 12, FONT_PATH, None) is None


def test_adaptive_word_wrap_narrow_slice_failure(text_fitter_instance):
    class StubFont:
        def getlength(self, text: str) -> float:
            return len(text) * 100.0

        def getmetrics(self):
            return 10, 2

    inner = shapely_box(0, 0, 5, 2)
    stub = StubFont()
    result = text_fitter_instance._adaptive_word_wrap("cannot fit", inner, stub, 12, FONT_PATH, None)
    assert result is None


def test_max_axis_shift_zero_bound(text_fitter_instance):
    geom = shapely_box(0, 0, 1, 1)
    inner = shapely_box(0, 0, 1, 1)
    assert text_fitter_instance._max_axis_shift(inner, geom, "x", 1, 0.0) == 0.0


def test_axis_shift_limits_invalid_axis(text_fitter_instance):
    geom = shapely_box(0, 0, 1, 1)
    inner = shapely_box(0, 0, 2, 2)
    with pytest.raises(ValueError):
        text_fitter_instance._axis_shift_limits(inner, geom, "z", 0.0)


def test_sample_axis_offset_covers_positive_and_negative():
    fitter = TextFitter(rng=random.Random(0))
    first = fitter._sample_axis_offset(-2.0, 3.0)
    second = fitter._sample_axis_offset(-2.0, 3.0)
    assert first < 0.0 <= second


def test_compute_jitter_offsets_multipolygon_and_y_axis():
    fitter = TextFitter(rng=random.Random(1))
    inner = MultiPolygon([shapely_box(0, 0, 5, 5), shapely_box(6, 0, 11, 5)])
    outer = shapely_box(0, 0, 12, 6)
    geometry = shapely_box(6.5, 1.0, 7.5, 2.0)
    dx, dy, shifted = fitter._compute_jitter_offsets(inner, outer, geometry, jitter_x=False, jitter_y=True, safety_margin=0.0)
    assert outer.contains(shifted)


def test_compute_jitter_offsets_binary_search(monkeypatch):
    fitter = TextFitter(rng=random.Random(2))
    inner = shapely_box(0, 0, 10, 10)
    outer = shapely_box(1, 0, 9, 10)
    geometry = shapely_box(0.5, 2.0, 4.5, 6.0)

    monkeypatch.setattr(TextFitter, "_sample_axis_offset", lambda self, min_off, max_off: max_off)

    dx, dy, shifted = fitter._compute_jitter_offsets(inner, outer, geometry, jitter_x=True, jitter_y=False, safety_margin=0.0)
    assert dx > 0.0
    assert outer.contains(shifted)


def test_compute_jitter_offsets_fallback(monkeypatch):
    fitter = TextFitter(rng=random.Random(3))
    inner = shapely_box(0, 0, 5, 5)
    outer = shapely_box(0, 0, 5, 5)
    geometry = shapely_box(6, 0, 7, 1)

    monkeypatch.setattr(TextFitter, "_axis_shift_limits", lambda self, *_args, **_kwargs: (0.0, 0.0))
    dx, dy, shifted = fitter._compute_jitter_offsets(inner, outer, geometry, jitter_x=True, jitter_y=False, safety_margin=0.0)
    assert dx == dy == 0.0
    assert shifted.equals(geometry)


def test_fit_with_jitter_acceptance(monkeypatch):
    base_fitter = TextFitter(rng=random.Random(5))
    rect = shapely_box(0, 0, 150, 80)
    shape = FitterShape(polygon=rect, padding=2)
    text_block = TextBlock(text="Jitter acceptance path", font_path=FONT_PATH)
    baseline = base_fitter.fit(text_block, shape)
    assert baseline is not None

    jitter_fitter = TextFitter(rng=random.Random(6))

    def accept_offsets(inner, outer, geometry, jitter_x, jitter_y, safety_margin):
        shifted = shapely_translate(geometry, xoff=0.5, yoff=0.0)
        return 0.5, 0.0, shifted

    monkeypatch.setattr(jitter_fitter, "_compute_jitter_offsets", accept_offsets)
    result = jitter_fitter.fit(text_block, shape, jitter_x=True)
    assert result is not None
    assert result.line_positions != baseline.line_positions


def test_fit_outline_fallback(monkeypatch):
    fitter = TextFitter(rng=random.Random(7))
    rect = shapely_box(0, 0, 120, 60)
    shape = FitterShape(polygon=rect, padding=2)
    text_block = TextBlock(text="Outline missing fallback", font_path=FONT_PATH)

    original_outline = fitter._create_line_outline

    def always_none(*args, **kwargs):
        return None

    monkeypatch.setattr(fitter, "_create_line_outline", always_none)
    result = fitter.fit(text_block, shape)
    assert result is not None
    assert result.line_positions

    monkeypatch.setattr(fitter, "_create_line_outline", original_outline)


def test_component_to_fitter_shape_radius_branch():
    class CircleStub:
        position = (1.0, 2.0)
        radius = 3.0

    shape = component_to_fitter_shape(CircleStub())
    assert shape is not None
    assert shape.polygon.area > 0


def test_component_to_fitter_shape_returns_none():
    class EmptyStub:
        pass

    assert component_to_fitter_shape(EmptyStub()) is None


def test_polygon_from_coords_handles_invalid_and_empty(text_fitter_instance):
    invalid_coords = [(0, 0), (1, 1), (1, 0), (0, 1)]
    polygon = text_fitter_instance._polygon_from_coords(invalid_coords)
    assert polygon is not None
    assert not polygon.is_empty
    assert text_fitter_instance._polygon_from_coords([]) is None


def test_merge_polygons_validates_inputs(text_fitter_instance):
    assert text_fitter_instance._merge_polygons([None]) is None
    poly_one = shapely_box(0, 0, 1, 1)
    poly_two = shapely_box(1, 0, 2, 1)
    merged = text_fitter_instance._merge_polygons([poly_one, poly_two])
    assert merged is not None
    assert merged.area > poly_one.area


def test_calculate_inner_boundary_handles_excess_padding():
    fitter = TextFitter(rng=random.Random(7))
    tiny_square = shapely_box(0, 0, 4, 4)
    shape = FitterShape(polygon=tiny_square, line_thickness_range=(6, 6), padding=2)
    inner_boundary, thickness = fitter._calculate_inner_boundary(shape)
    assert inner_boundary is None
    assert pytest.approx(thickness, abs=1e-6) == 6


def test_adaptive_word_wrap_respects_max_width(text_fitter_instance):
    inner = shapely_box(0, 0, 10, 10)
    font = text_fitter_instance._get_pil_font(FONT_PATH, 12)
    wrapped = text_fitter_instance._adaptive_word_wrap(
        text="Supercalifragilisticexpialidocious",
        inner_boundary=inner,
        font=font,
        font_size=12,
        font_path=FONT_PATH,
        max_line_width=5.0,
    )
    assert wrapped is None


def test_compute_jitter_offsets_produces_shift():
    fitter = TextFitter(rng=random.Random(123))
    inner = shapely_box(0, 0, 20, 10)
    outer = shapely_box(0, 0, 25, 15)
    geometry = shapely_box(2, 2, 6, 6)
    dx, dy, shifted = fitter._compute_jitter_offsets(inner, outer, geometry, jitter_x=True, jitter_y=False, safety_margin=0.0)
    assert dx != 0.0 or dy != 0.0
    assert inner.contains(shifted)
    assert outer.contains(shifted)


def test_compute_jitter_offsets_no_axes_returns_original(text_fitter_instance):
    geometry = shapely_box(0, 0, 2, 2)
    inner = shapely_box(0, 0, 4, 4)
    dx, dy, shifted = text_fitter_instance._compute_jitter_offsets(inner, inner, geometry, False, False, 0.0)
    assert dx == dy == 0.0
    assert shifted.equals(geometry)


def test_fit_with_jitter_rejection(monkeypatch):
    baseline_fitter = TextFitter(rng=random.Random(5))
    rect = shapely_box(0, 0, 120, 60)
    shape = FitterShape(polygon=rect, padding=2)
    text_block = TextBlock(text="Jitter should bail out if candidate escapes.", font_path=FONT_PATH)
    baseline = baseline_fitter.fit(text_block, shape)
    assert baseline is not None

    jitter_fitter = TextFitter(rng=random.Random(5))

    def forced_out_of_bounds(inner, outer, geometry, jitter_x, jitter_y, safety_margin):
        shifted = shapely_translate(geometry, xoff=inner.bounds[2] * 2)
        return 25.0, 0.0, shifted

    monkeypatch.setattr(jitter_fitter, "_compute_jitter_offsets", forced_out_of_bounds)
    result = jitter_fitter.fit(text_block, shape, jitter_x=True)
    assert result is not None
    assert result.line_positions == baseline.line_positions

