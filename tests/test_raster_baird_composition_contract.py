"""RASTER-BAIRD-P1 conditions for standalone drawing-to-scan composition."""

from __future__ import annotations

from uuid import uuid4

import pytest

from InkGen import (
    BairdDegradationResult,
    BairdParams,
    Canvas,
    DrawingComponentGroup,
    DrawingStyle,
    RasterBairdResult,
    RasterRenderResult,
    RectangleDrawing,
    render_and_degrade_drawing_group,
)


def _group() -> DrawingComponentGroup:
    style = DrawingStyle(f"raster_baird_{uuid4().hex}", stroke="none", fill="#000000")
    return DrawingComponentGroup("mark", [RectangleDrawing((0.25, 0.25), 0.5, 0.5, 0, style)])


@pytest.mark.condition("RASTER-BAIRD-P1")
def test_composition_returns_deterministic_clean_and_degraded_assets() -> None:
    """RASTER-BAIRD-P1: One public call returns reproducible clean and scan assets."""
    kwargs = {
        "seed": 17,
        "background_rgb": (230, 240, 250),
        "dpi": 20.0,
        "render_supersample": 2,
        "source": "generated://raster-baird",
    }

    first = render_and_degrade_drawing_group(_group(), Canvas(1, 1, "in"), BairdParams.clean(), **kwargs)
    second = render_and_degrade_drawing_group(_group(), Canvas(1, 1, "in"), BairdParams.clean(), **kwargs)

    assert isinstance(first, RasterBairdResult)
    assert isinstance(first.clean, RasterRenderResult)
    assert isinstance(first.degraded, BairdDegradationResult)
    assert first.clean.asset.data == second.clean.asset.data
    assert first.degraded.asset.data == second.degraded.asset.data
    assert first.manifest == second.manifest
    assert (first.clean.asset.mode, first.degraded.asset.mode) == ("RGBA", "RGB")
    assert first.clean.asset.source == "generated://raster-baird"
    assert first.degraded.asset.source == "generated://raster-baird"
    assert first.manifest == {
        "render": first.clean.manifest,
        "degradation": first.degraded.manifest,
    }


@pytest.mark.condition("RASTER-BAIRD-P1")
def test_explicit_colored_substrate_changes_transparent_page_result() -> None:
    """RASTER-BAIRD-P1: Alpha is composited over the named substrate, never white implicitly."""
    empty = DrawingComponentGroup("empty")
    canvas = Canvas(1, 1, "in")
    params = BairdParams.clean()

    black = render_and_degrade_drawing_group(empty, canvas, params, seed=1, background_rgb=(0, 0, 0), dpi=4, render_supersample=1)
    white = render_and_degrade_drawing_group(empty, canvas, params, seed=1, background_rgb=(255, 255, 255), dpi=4, render_supersample=1)

    with black.clean.asset.image() as clean:
        assert clean.getpixel((0, 0)) == (0, 0, 0, 0)
    with black.degraded.asset.image() as dark, white.degraded.asset.image() as light:
        assert dark.getpixel((0, 0)) == (0, 0, 0)
        assert light.getpixel((0, 0)) == (255, 255, 255)
    assert black.degraded.manifest["background_rgb"] == [0, 0, 0]
    assert white.degraded.manifest["background_rgb"] == [255, 255, 255]


@pytest.mark.condition("RASTER-BAIRD-P1")
def test_composition_requires_substrate_and_delegates_public_validation() -> None:
    """RASTER-BAIRD-P1: Required substrate, params, and seed fail at public boundaries."""
    group = _group()
    canvas = Canvas(1, 1, "in")
    params = BairdParams.clean()

    with pytest.raises(TypeError, match="background_rgb"):
        render_and_degrade_drawing_group(group, canvas, params, seed=1)  # type: ignore[call-arg]
    with pytest.raises(TypeError, match="params must be BairdParams"):
        render_and_degrade_drawing_group(group, canvas, object(), seed=1, background_rgb=(1, 2, 3))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="seed"):
        render_and_degrade_drawing_group(group, canvas, params, seed=-1, background_rgb=(1, 2, 3))
    with pytest.raises(ValueError, match="background_rgb"):
        render_and_degrade_drawing_group(group, canvas, params, seed=1, background_rgb=(1, 2, 999))
    with pytest.raises(TypeError):
        render_and_degrade_drawing_group(group, canvas, params, 1, (1, 2, 3))  # type: ignore[misc]


@pytest.mark.condition("RASTER-BAIRD-P1")
def test_composition_pins_render_defaults() -> None:
    """RASTER-BAIRD-P1: Composition keeps the renderer's 300 DPI and 2x defaults."""
    result = render_and_degrade_drawing_group(
        DrawingComponentGroup("defaults"),
        Canvas(0.01, 0.01, "in"),
        BairdParams.clean(),
        seed=1,
        background_rgb=(255, 255, 255),
    )

    assert result.clean.dpi == 300.0
    assert result.clean.supersample == 2
    assert (result.clean.asset.width, result.clean.asset.height) == (3, 3)


@pytest.mark.condition("RASTER-BAIRD-P1")
def test_composition_result_rejects_invalid_envelopes() -> None:
    """RASTER-BAIRD-P1: Composite result cannot contain unrelated result types."""
    valid = render_and_degrade_drawing_group(
        _group(),
        Canvas(1, 1, "in"),
        BairdParams.clean(),
        seed=1,
        background_rgb=(255, 255, 255),
        dpi=4,
    )

    with pytest.raises(TypeError, match="clean must be a RasterRenderResult"):
        RasterBairdResult(object(), valid.degraded)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="degraded must be a BairdDegradationResult"):
        RasterBairdResult(valid.clean, object())  # type: ignore[arg-type]
