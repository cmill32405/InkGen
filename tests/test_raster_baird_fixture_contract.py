"""RASTER-BAIRD-E2E-P19 end-to-end fixture contract tests."""

from __future__ import annotations

import re
import zlib
from dataclasses import FrozenInstanceError

import pytest

from InkGen import (
    BairdParams,
    DocumentPDF,
    RasterBairdPDFFixture,
    build_raster_baird_pdf_fixture,
)
from InkGen.pdf_generator import ImagePDF
from InkGen.raster_baird_fixtures import _fixture_drawing_group


def _fixture(*, background_rgb: tuple[int, int, int] = (226, 236, 244)) -> RasterBairdPDFFixture:
    return build_raster_baird_pdf_fixture(
        params=BairdParams.clean(),
        seed=7,
        background_rgb=background_rgb,
        dpi=50.8,
        render_supersample=1,
    )


def _flate_streams(pdf_bytes: bytes) -> list[bytes]:
    streams = re.findall(rb"stream\n(?P<content>.*?)\nendstream", pdf_bytes, re.S)
    return [zlib.decompress(stream) for stream in streams if stream.startswith(b"x\x9c")]


@pytest.mark.condition("RASTER-BAIRD-E2E-P19")
def test_fixture_is_deterministic_across_the_public_pipeline() -> None:
    """P19: Fixed inputs reproduce both PNG assets, PDF bytes, and provenance."""
    first = _fixture()
    second = _fixture()

    assert first.scan.clean.asset.data == second.scan.clean.asset.data
    assert first.scan.degraded.asset.data == second.scan.degraded.asset.data
    assert first.document.to_pdf_bytes() == second.document.to_pdf_bytes()
    assert first.manifest == second.manifest
    assert first.manifest["condition"] == "RASTER-BAIRD-E2E-P19"
    assert first.manifest["scan"] == first.scan.manifest


@pytest.mark.condition("RASTER-BAIRD-E2E-P19")
def test_fixture_default_selects_the_canonical_baird_profile() -> None:
    """P19: Omitting params applies Baird's canonical degradation defaults."""
    fixture = build_raster_baird_pdf_fixture()

    assert fixture.scan.degraded.parameters == BairdParams()
    assert fixture.scan.degraded.seed == 19
    assert fixture.scan.degraded.background_rgb == (226, 236, 244)
    assert fixture.scan.clean.dpi == 72.0
    assert fixture.scan.clean.supersample == 2
    assert (fixture.scan.clean.asset.width, fixture.scan.clean.asset.height) == (340, 227)
    assert fixture.scan.degraded.asset.data != fixture.scan.clean.asset.data


@pytest.mark.condition("RASTER-BAIRD-E2E-P19")
def test_fixture_source_drawing_pins_every_requested_visual_contract() -> None:
    """P19: Fixed geometry and presentation make the reusable fixture stable."""
    group = _fixture_drawing_group()
    translucent, outline, accent, text = group.components

    assert group.group_label == "raster_baird_source"
    assert (translucent.position, translucent.width, translucent.height, translucent.corner_radii) == (
        (-8.0, -6.0),
        48.0,
        30.0,
        (4.0, 7.0),
    )
    assert (
        translucent.style.stroke,
        translucent.style.stroke_width,
        translucent.style.fill,
        translucent.style.fill_opacity,
    ) == ("#12384a", 0.8, "#2f7da3", 0.45)
    assert (outline.position, outline.width, outline.height, outline.corner_radii) == ((8.0, 8.0), 104.0, 64.0, 0.0)
    assert (outline.style.stroke, outline.style.stroke_width, outline.style.fill) == ("#17212b", 0.6, "none")
    assert (accent.point_1, accent.point_2) == ((14.0, 49.0), (106.0, 49.0))
    assert (accent.style.stroke, accent.style.stroke_width, accent.style.fill) == ("#b2342c", 1.2, "none")
    assert (text.text, text.position, text.style.color) == ("INKGEN RASTER / BAIRD", (15.0, 39.0), "#111111")
    assert (text.style.font.weight, text.style.font.size) == ("bold", 14.0)


@pytest.mark.condition("RASTER-BAIRD-E2E-P19")
def test_clean_fixture_proves_text_vectors_transparency_and_canvas_clipping() -> None:
    """P19: One neutral drawing exercises every requested clean-render surface."""
    fixture = _fixture()

    with fixture.scan.clean.asset.image() as clean:
        alpha = clean.getchannel("A")
        assert clean.size == (240, 160)
        assert clean.mode == "RGBA"
        assert 0 < clean.getpixel((0, 0))[3] < 255
        assert clean.getpixel((239, 159)) == (0, 0, 0, 0)
        assert alpha.crop((25, 55, 225, 90)).getbbox() is not None
        assert clean.getpixel((100, 98))[3] > 0
        painted_bounds = alpha.getbbox()
        assert painted_bounds is not None
        assert painted_bounds[:2] == (0, 0)
        assert painted_bounds[2] < clean.width
        assert painted_bounds[3] < clean.height


@pytest.mark.condition("RASTER-BAIRD-E2E-P19")
def test_explicit_colored_substrate_controls_the_opaque_scan() -> None:
    """P19: The named substrate affects transparent pixels before Baird output."""
    dark = _fixture(background_rgb=(12, 24, 36))
    light = _fixture(background_rgb=(210, 225, 240))

    with dark.scan.degraded.asset.image() as dark_image, light.scan.degraded.asset.image() as light_image:
        dark_pixel = dark_image.getpixel((120, 12))
        light_pixel = light_image.getpixel((120, 12))

    assert dark.scan.clean.asset.data == light.scan.clean.asset.data
    assert dark_pixel[0] == dark_pixel[1] == dark_pixel[2]
    assert light_pixel[0] == light_pixel[1] == light_pixel[2]
    assert dark_pixel[0] < light_pixel[0]
    assert dark.scan.degraded.manifest["background_rgb"] == [12, 24, 36]
    assert light.scan.degraded.manifest["background_rgb"] == [210, 225, 240]


@pytest.mark.condition("RASTER-BAIRD-E2E-P19")
def test_degraded_asset_embeds_unchanged_through_neutral_pdf_image_path() -> None:
    """P19: The opaque scan is the sole PDF page image and retains its RGB samples."""
    fixture = _fixture()
    groups = fixture.document.page(1).layer("base").groups()
    components = tuple(groups[0].components())
    payload = fixture.document.to_pdf_bytes()

    assert len(groups) == 1
    assert groups[0].group_label == "raster_baird_scan"
    assert len(components) == 1
    assert isinstance(components[0], ImagePDF)
    assert components[0].image is fixture.scan.degraded.asset
    assert components[0].position == (0.1, 0.1)
    assert components[0].width == pytest.approx(119.8)
    assert components[0].height == pytest.approx(79.8)
    assert payload.startswith(b"%PDF-1.4\n")
    assert payload.count(b"/Subtype /Image") == 1
    assert b"/SMask" not in payload
    assert b"BT" not in payload
    assert b" Tj" not in payload
    with fixture.scan.degraded.asset.image() as degraded:
        assert degraded.convert("RGB").tobytes() in _flate_streams(payload)


@pytest.mark.condition("RASTER-BAIRD-E2E-P19")
def test_fixture_exposes_image_only_truth_and_complete_manifest() -> None:
    """P19: Downstream consumers can identify and reproduce the known fixture."""
    fixture = _fixture()
    extraction_truth = fixture.document.extraction_truth()
    grammar_truth = fixture.document.grammar_truth()

    assert {(record["field"], record["role"], record["source_channel"]) for record in extraction_truth} >= {
        ("scanned_page_image", "image", "image"),
        ("scanned_page", "region", "body"),
    }
    assert any(
        record["condition_id"] == "RASTER-BAIRD-E2E-P19"
        and record["kind"] == "assessment"
        and record["value"]["known_fixture"] is True
        and record["value"]["extractable_text"] is False
        for record in grammar_truth
    )
    assert fixture.manifest["pdf_embedding"] == {
        "canvas": {"width": 120.0, "height": 80.0, "units": "mm"},
        "pages": 1,
        "source": "generated://inkgen/raster-baird-e2e.png",
        "image_pixels": [240, 160],
        "inset": 0.1,
    }


@pytest.mark.condition("RASTER-BAIRD-E2E-P19")
def test_fixture_delegates_invalid_inputs_and_rejects_invalid_envelopes() -> None:
    """P19: Existing owners reject malformed render, degradation, and result inputs."""
    with pytest.raises(TypeError, match="params must be BairdParams"):
        build_raster_baird_pdf_fixture(params=object())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="background_rgb"):
        build_raster_baird_pdf_fixture(background_rgb=(1, 2, 999))
    with pytest.raises(ValueError, match="dpi must be greater than zero"):
        build_raster_baird_pdf_fixture(dpi=0)
    with pytest.raises(TypeError):
        build_raster_baird_pdf_fixture(BairdParams.clean())  # type: ignore[misc]

    valid = _fixture()
    with pytest.raises(TypeError, match="scan must be a RasterBairdResult"):
        RasterBairdPDFFixture(object(), valid.document)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="document must be a DocumentPDF"):
        RasterBairdPDFFixture(valid.scan, object())  # type: ignore[arg-type]
    with pytest.raises(FrozenInstanceError):
        valid.scan = valid.scan
    assert not hasattr(valid, "__dict__")
    assert isinstance(valid.document, DocumentPDF)
