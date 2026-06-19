"""Tests for text outline proof obligations."""

from __future__ import annotations

import math

import matplotlib.font_manager as fm
import pytest
from fontTools.ttLib import TTFont

from InkGen import text_outline
from InkGen.text_outline import (
    _px_to_units,
    outline_for_text,
    sample_path_points,
    set_add_one_pixel_margin_default,
)

FONT_PATH = fm.findfont(fm.FontProperties(family="DejaVu Sans"))


def _bounds_width(bbox: list[tuple[float, float]]) -> float:
    """Return the width of bbox coordinates returned by outline_for_text."""
    return bbox[2][0] - bbox[0][0]


def _bounds_height(bbox: list[tuple[float, float]]) -> float:
    """Return the height of bbox coordinates returned by outline_for_text."""
    return bbox[1][1] - bbox[0][1]


@pytest.mark.condition("TEXT-OUTLINE-P1")
def test_text_outline_converts_pixels_using_requested_units_and_dpi() -> None:
    """TEXT-OUTLINE-P1: Pixel conversion honors units and explicit DPI."""
    assert _px_to_units(96.0, units="in", dpi=96.0) == pytest.approx(1.0)
    assert _px_to_units(300.0, units="in", dpi=300.0) == pytest.approx(1.0)
    assert _px_to_units(150.0, units="mm", dpi=300.0) == pytest.approx(12.7)
    assert _px_to_units(5.0, units="px", dpi=300.0) == 5.0


@pytest.mark.condition("TEXT-OUTLINE-P1")
def test_text_outline_samples_all_path_segments_deterministically() -> None:
    """TEXT-OUTLINE-P1: Path sampling includes segment endpoints and finite points."""
    path_description = "M 0 0 L 10 0 L 10 10 z"

    points = sample_path_points(path_description, px_step=2.0, units="px")

    assert points[0] == (0.0, 0.0)
    assert (10.0, 0.0) in points
    assert (10.0, 10.0) in points
    assert len(points) > 4
    assert all(math.isfinite(x) and math.isfinite(y) for x, y in points)

    line_points = sample_path_points("M 0 0 L 10 0", px_step=2.0, units="px")
    assert line_points == [(0.0, 0.0), (2.0, 0.0), (4.0, 0.0), (6.0, 0.0), (8.0, 0.0), (10.0, 0.0)]

    zero_length_points = sample_path_points("M 0 0 L 0 0", px_step=2.0, units="px")
    assert zero_length_points == [(0.0, 0.0), (0.0, 0.0)]

    dense_default_points = sample_path_points("M 0 0 L 10 0")
    assert len(dense_default_points) > 70


@pytest.mark.condition("TEXT-OUTLINE-P1")
def test_text_outline_returns_finite_geometry_for_visible_text() -> None:
    """TEXT-OUTLINE-P1: Visible text returns path, samples, bbox, hull, and path bbox."""
    outline = outline_for_text(
        text="InkGen",
        font_path=FONT_PATH,
        size_px=24.0,
        x=3.0,
        y=4.0,
        units="px",
        add_one_pixel_margin=False,
        y_down=True,
    )

    assert isinstance(outline["svg_path"], str)
    assert outline["svg_path"]
    assert outline["points"]
    assert outline["bbox"]
    assert outline["convex_hull"]
    assert outline["path_bbox"] is not None
    assert _bounds_width(outline["bbox"]) > 0.0
    assert _bounds_height(outline["bbox"]) > 0.0
    assert all(math.isfinite(value) for point in outline["bbox"] for value in point)
    assert all(math.isfinite(value) for point in outline["convex_hull"] for value in point)


@pytest.mark.condition("TEXT-OUTLINE-P1")
def test_text_outline_margin_expands_bounds_by_requested_unit_size() -> None:
    """TEXT-OUTLINE-P1: One-pixel margin expands the outline bbox in document units."""
    base = outline_for_text(
        text="Margin",
        font_path=FONT_PATH,
        size_px=20.0,
        x=0.0,
        y=0.0,
        units="mm",
        dpi=300.0,
        add_one_pixel_margin=False,
    )
    expanded = outline_for_text(
        text="Margin",
        font_path=FONT_PATH,
        size_px=20.0,
        x=0.0,
        y=0.0,
        units="mm",
        dpi=300.0,
        add_one_pixel_margin=True,
    )

    margin = 25.4 / 300.0
    assert expanded["bbox"][0][0] == pytest.approx(base["bbox"][0][0] - margin, abs=1e-4)
    assert expanded["bbox"][0][1] == pytest.approx(base["bbox"][0][1] - margin, abs=1e-4)
    assert expanded["bbox"][2][0] == pytest.approx(base["bbox"][2][0] + margin, abs=1e-4)
    assert expanded["bbox"][2][1] == pytest.approx(base["bbox"][2][1] + margin, abs=1e-4)


@pytest.mark.condition("TEXT-OUTLINE-P1")
def test_text_outline_global_margin_default_matches_explicit_margin() -> None:
    """TEXT-OUTLINE-P1: Global margin default is used only when argument is None."""
    set_add_one_pixel_margin_default(True)
    try:
        auto = outline_for_text(
            text="Global",
            font_path=FONT_PATH,
            size_px=18.0,
            x=0.0,
            y=0.0,
            units="mm",
            add_one_pixel_margin=None,
        )
    finally:
        set_add_one_pixel_margin_default(False)

    explicit = outline_for_text(
        text="Global",
        font_path=FONT_PATH,
        size_px=18.0,
        x=0.0,
        y=0.0,
        units="mm",
        add_one_pixel_margin=True,
    )
    disabled = outline_for_text(
        text="Global",
        font_path=FONT_PATH,
        size_px=18.0,
        x=0.0,
        y=0.0,
        units="mm",
        add_one_pixel_margin=None,
    )

    assert auto["bbox"] == explicit["bbox"]
    assert disabled["bbox"] != explicit["bbox"]
    assert text_outline.ADD_ONE_PIXEL_MARGIN_DEFAULT is False


@pytest.mark.condition("TEXT-OUTLINE-P1")
def test_text_outline_whitespace_uses_font_metric_fallback_and_dpi() -> None:
    """TEXT-OUTLINE-P1: Whitespace outlines use font metrics and DPI-aware units."""
    low_dpi = outline_for_text(
        text="   ",
        font_path=FONT_PATH,
        size_px=24.0,
        x=0.0,
        y=0.0,
        units="mm",
        dpi=96.0,
        add_one_pixel_margin=False,
    )
    high_dpi = outline_for_text(
        text="   ",
        font_path=FONT_PATH,
        size_px=24.0,
        x=0.0,
        y=0.0,
        units="mm",
        dpi=192.0,
        add_one_pixel_margin=False,
    )

    assert low_dpi["svg_path"] == ""
    assert low_dpi["points"] == []
    assert low_dpi["path_bbox"] is None
    assert low_dpi["bbox"]
    assert low_dpi["convex_hull"]
    assert _bounds_width(low_dpi["bbox"]) > 0.0
    assert _bounds_height(low_dpi["bbox"]) > 0.0
    assert _bounds_width(high_dpi["bbox"]) == pytest.approx(_bounds_width(low_dpi["bbox"]) / 2.0)
    assert _bounds_height(high_dpi["bbox"]) == pytest.approx(_bounds_height(low_dpi["bbox"]) / 2.0)

    font = TTFont(FONT_PATH)
    space_glyph_name = font["cmap"].getBestCmap()[ord(" ")]
    adv_fu = font["hmtx"][space_glyph_name][0] * 3
    upem = font["head"].unitsPerEm
    expected_width = adv_fu * (24.0 / float(upem)) * (25.4 / 96.0)
    assert _bounds_width(low_dpi["bbox"]) == pytest.approx(expected_width)
