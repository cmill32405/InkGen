import matplotlib.font_manager as fm
import pytest

from InkGen import text_outline
from InkGen.text_outline import (
    _px_to_units,
    outline_for_text,
    sample_path_points,
    set_add_one_pixel_margin_default,
)

FONT_PATH = fm.findfont(fm.FontProperties(family="DejaVu Sans"))


def test_set_add_one_pixel_margin_default_toggles_flag():
    set_add_one_pixel_margin_default(True)
    assert text_outline.ADD_ONE_PIXEL_MARGIN_DEFAULT is True
    set_add_one_pixel_margin_default(False)
    assert text_outline.ADD_ONE_PIXEL_MARGIN_DEFAULT is False


def test_px_to_units_conversions():
    assert pytest.approx(_px_to_units(96, units="in"), rel=1e-6) == 1.0
    assert pytest.approx(_px_to_units(10, units="mm"), rel=1e-6) == 10 * (25.4 / 96.0)
    assert _px_to_units(5, units="px") == 5


def test_sample_path_points_follows_segments():
    path_description = "M 0 0 L 10 0 L 10 10 z"
    pts = sample_path_points(path_description, px_step=2.0, units="px")
    assert pts[0] == (0.0, 0.0)
    assert (10.0, 10.0) in pts
    assert len(pts) > 4


def test_outline_for_text_margin_controls_bounds():
    base = outline_for_text(
        text="InkGen",
        font_path=FONT_PATH,
        size_px=24,
        x=0.0,
        y=0.0,
        add_one_pixel_margin=False,
    )
    expanded = outline_for_text(
        text="InkGen",
        font_path=FONT_PATH,
        size_px=24,
        x=0.0,
        y=0.0,
        add_one_pixel_margin=True,
    )
    base_bounds = base["bbox"]
    expanded_bounds = expanded["bbox"]
    assert expanded_bounds[0][0] < base_bounds[0][0]
    assert expanded_bounds[2][1] > base_bounds[2][1]


def test_outline_respects_global_margin_default():
    set_add_one_pixel_margin_default(True)
    try:
        auto = outline_for_text(
            text="Global",
            font_path=FONT_PATH,
            size_px=18,
            x=0.0,
            y=0.0,
            add_one_pixel_margin=None,
        )
    finally:
        set_add_one_pixel_margin_default(False)

    manual = outline_for_text(
        text="Global",
        font_path=FONT_PATH,
        size_px=18,
        x=0.0,
        y=0.0,
        add_one_pixel_margin=True,
    )
    assert auto["bbox"] == manual["bbox"]
