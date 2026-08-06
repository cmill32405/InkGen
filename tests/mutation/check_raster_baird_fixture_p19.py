"""Fast deterministic witnesses for the raster-Baird PDF fixture P19."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

from InkGen.baird import BairdParams
from InkGen.pdf_generator import DocumentPDF, ImagePDF
from InkGen.raster_baird_fixtures import (
    RasterBairdPDFFixture,
    _fixture_drawing_group,
    _unique_style_name,
    build_raster_baird_pdf_fixture,
)
from InkGen.style import Style


def _raises(error: type[Exception], call: object, text: str) -> None:
    try:
        call()  # type: ignore[operator]
    except error as exc:
        assert text in str(exc)
        return
    raise AssertionError(f"expected {error.__name__}")


def _build(*, background: tuple[int, int, int] = (12, 24, 36)) -> RasterBairdPDFFixture:
    return build_raster_baird_pdf_fixture(
        params=BairdParams.clean(),
        seed=7,
        background_rgb=background,
        dpi=25.4,
        render_supersample=1,
    )


def _assert_public_pipeline() -> None:
    first = _build()
    second = _build()
    assert isinstance(first, RasterBairdPDFFixture)
    assert isinstance(first.document, DocumentPDF)
    assert first.scan.clean.asset.data == second.scan.clean.asset.data
    assert first.scan.degraded.asset.data == second.scan.degraded.asset.data
    assert first.document.to_pdf_bytes() == second.document.to_pdf_bytes()
    assert (first.scan.clean.asset.width, first.scan.clean.asset.height) == (120, 80)
    assert (first.scan.clean.asset.mode, first.scan.degraded.asset.mode) == ("RGBA", "RGB")
    assert first.scan.clean.component_count == 4
    assert first.scan.clean.dpi == 25.4
    assert first.scan.clean.supersample == 1
    assert first.scan.degraded.seed == 7
    assert first.scan.degraded.background_rgb == (12, 24, 36)

    with first.scan.clean.asset.image() as clean:
        assert 0 < clean.getpixel((0, 0))[3] < 255
        assert clean.getpixel((119, 79)) == (0, 0, 0, 0)
        assert clean.getchannel("A").crop((12, 25, 112, 50)).getbbox() is not None
        assert clean.getpixel((50, 49))[3] > 0

    light = _build(background=(210, 225, 240))
    assert first.scan.clean.asset.data == light.scan.clean.asset.data
    with first.scan.degraded.asset.image() as dark, light.scan.degraded.asset.image() as pale:
        assert dark.getpixel((60, 5))[0] < pale.getpixel((60, 5))[0]

    canonical = build_raster_baird_pdf_fixture()
    assert canonical.scan.degraded.parameters == BairdParams()
    assert canonical.scan.degraded.seed == 19
    assert canonical.scan.degraded.background_rgb == (226, 236, 244)
    assert canonical.scan.clean.dpi == 72.0
    assert canonical.scan.clean.supersample == 2
    assert (canonical.scan.clean.asset.width, canonical.scan.clean.asset.height) == (340, 227)
    assert canonical.scan.degraded.asset.data != canonical.scan.clean.asset.data


def _assert_source_drawing() -> None:
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


def _assert_manifest_and_pdf() -> None:
    fixture = _build()
    assert fixture.manifest == {
        "condition": "RASTER-BAIRD-E2E-P19",
        "scan": fixture.scan.manifest,
        "pdf_embedding": {
            "canvas": {"width": 120.0, "height": 80.0, "units": "mm"},
            "pages": 1,
            "source": "generated://inkgen/raster-baird-e2e.png",
            "image_pixels": [120, 80],
            "inset": 0.1,
        },
    }
    groups = fixture.document.page(1).layer("base").groups()
    assert len(groups) == 1 and groups[0].group_label == "raster_baird_scan"
    components = tuple(groups[0].components())
    assert len(components) == 1 and isinstance(components[0], ImagePDF)
    assert components[0].image is fixture.scan.degraded.asset
    assert components[0].position == (0.1, 0.1)
    assert components[0].width == 119.8
    assert components[0].height == 79.8
    payload = fixture.document.to_pdf_bytes()
    assert payload.startswith(b"%PDF-1.4\n")
    assert payload.count(b"/Subtype /Image") == 1
    assert b"BT" not in payload and b" Tj" not in payload
    assert len(fixture.document.extraction_truth()) == 2
    grammar_truth = fixture.document.grammar_truth()
    assert len(grammar_truth) == 2
    cue = next(record for record in grammar_truth if record["kind"] == "cue")
    assessment = next(record for record in grammar_truth if record["kind"] == "assessment")
    assert cue["value"] == {
        "fixture_family": "raster_baird_pdf",
        "rasterized_text": True,
        "source": "generated://inkgen/raster-baird-e2e.png",
    }
    assert assessment["value"] == {
        "fixture_family": "raster_baird_pdf",
        "known_fixture": True,
        "extractable_text": False,
    }


def _assert_boundaries() -> None:
    valid = _build()
    _raises(TypeError, lambda: RasterBairdPDFFixture(object(), valid.document), "scan must be")
    _raises(TypeError, lambda: RasterBairdPDFFixture(valid.scan, object()), "document must be")
    _raises(TypeError, lambda: build_raster_baird_pdf_fixture(params=object()), "params must be")
    _raises(ValueError, lambda: build_raster_baird_pdf_fixture(background_rgb=(1, 2, 999)), "background_rgb")
    _raises(ValueError, lambda: build_raster_baird_pdf_fixture(dpi=0), "dpi must be greater")
    try:
        valid.scan = valid.scan
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("fixture envelope must be frozen")
    assert not hasattr(valid, "__dict__")


def _assert_style_name_partition() -> None:
    base = "raster_baird_e2e_mutation_probe"
    Style.style_names[:] = [name for name in Style.style_names if not name.startswith(base)]
    assert _unique_style_name("mutation_probe") == base
    Style.style_names.append(base)
    assert _unique_style_name("mutation_probe") == f"{base}_2"
    Style.style_names.append(f"{base}_2")
    assert _unique_style_name("mutation_probe") == f"{base}_3"


def main() -> None:
    _assert_public_pipeline()
    _assert_source_drawing()
    _assert_manifest_and_pdf()
    _assert_boundaries()
    _assert_style_name_partition()


if __name__ == "__main__":
    main()
