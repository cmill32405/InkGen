"""Tests for renderer-neutral raster image support."""

from __future__ import annotations

import io
import re
import uuid
import zlib

import pytest
from PIL import Image

from InkGen import image_assets
from InkGen.boundary import Canvas
from InkGen.drawing_components import DrawingComponentGroup, ImageDrawing, OutputFormat
from InkGen.image_assets import RasterImageAsset
from InkGen.pdf_generator import ComponentGroupPDF, DocumentPDF, ImagePDF, TextPDF
from InkGen.style import Font, TextStyle
from InkGen.svg_generator import ImageSVG


def _image_bytes(format_name: str = "PNG", *, mode: str = "RGBA") -> bytes:
    image = Image.new(mode, (2, 1), (255, 0, 0, 128) if "A" in mode else (255, 0, 0))
    if mode == "RGBA":
        image.putpixel((0, 0), (255, 0, 0, 0))
        image.putpixel((1, 0), (0, 0, 255, 128))
    output = io.BytesIO()
    image.save(output, format=format_name)
    return output.getvalue()


def _jpeg_bytes(
    *,
    orientation: int = 1,
    size: tuple[int, int] = (2, 3),
    icc_profile: bytes | None = None,
) -> bytes:
    image = Image.new("RGB", size, (255, 0, 0))
    image.putpixel((0, 0), (0, 255, 0))
    output = io.BytesIO()
    save_kwargs: dict[str, object] = {}
    if orientation != 1:
        exif = Image.Exif()
        exif[274] = orientation
        save_kwargs["exif"] = exif
    if icc_profile is not None:
        save_kwargs["icc_profile"] = icc_profile
    image.save(output, format="JPEG", **save_kwargs)
    return output.getvalue()


def _cmyk_jpeg_bytes(*, icc_profile: bytes | None = None) -> bytes:
    image = Image.new("CMYK", (2, 1), (0, 255, 255, 0))
    output = io.BytesIO()
    save_kwargs: dict[str, object] = {}
    if icc_profile is not None:
        save_kwargs["icc_profile"] = icc_profile
    image.save(output, format="JPEG", **save_kwargs)
    return output.getvalue()


def _palette_transparency_png() -> bytes:
    image = Image.new("P", (1, 1))
    image.putpalette([255, 0, 0] + [0, 0, 0] * 255)
    image.info["transparency"] = 0
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _palette_opaque_png() -> bytes:
    image = Image.new("P", (1, 1))
    image.putpalette([255, 0, 0] + [0, 0, 0] * 255)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _flate_streams(pdf_bytes: bytes) -> list[bytes]:
    streams = re.findall(rb"stream\n(?P<content>.*?)\nendstream", pdf_bytes, re.S)
    return [zlib.decompress(stream) for stream in streams if stream.startswith(b"x\x9c")]


@pytest.mark.condition("RASTER-IMAGE-P1")
def test_raster_image_asset_accepts_pillow_decodable_formats_and_preserves_alpha_metadata() -> None:
    """RASTER-IMAGE-P1: RasterImageAsset accepts Pillow formats and detects alpha."""
    png = RasterImageAsset.from_bytes(_image_bytes("PNG", mode="RGBA"))
    bmp = RasterImageAsset.from_bytes(_image_bytes("BMP", mode="RGB"))

    assert png.format == "PNG"
    assert png.mime_type == "image/png"
    assert png.width == 2
    assert png.height == 1
    assert png.has_alpha is True
    assert bmp.format == "BMP"
    assert bmp.mime_type == "image/bmp"
    assert bmp.has_alpha is False


@pytest.mark.condition("RASTER-IMAGE-P1")
def test_raster_image_asset_detects_palette_transparency() -> None:
    """RASTER-IMAGE-P1: Palette transparency metadata is treated as alpha."""
    asset = RasterImageAsset.from_bytes(_palette_transparency_png())
    opaque = RasterImageAsset.from_bytes(_palette_opaque_png())

    assert asset.mode == "P"
    assert asset.has_alpha is True
    assert opaque.mode == "P"
    assert opaque.has_alpha is False


@pytest.mark.condition("RASTER-IMAGE-P2")
def test_raster_image_asset_applies_exif_orientation_to_decoded_surface() -> None:
    """RASTER-IMAGE-P2: EXIF orientation changes decoded geometry, not source bytes."""
    raw = _jpeg_bytes(orientation=6, size=(2, 3))

    asset = RasterImageAsset.from_bytes(raw)

    assert asset.format == "JPEG"
    assert asset.orientation == 6
    assert (asset.width, asset.height) == (3, 2)
    assert asset.can_passthrough_jpeg is False
    with asset.image() as image:
        assert image.size == (3, 2)


@pytest.mark.condition("RASTER-IMAGE-P2")
def test_raster_image_asset_allows_identity_rgb_jpeg_passthrough() -> None:
    """RASTER-IMAGE-P2: RGB JPEG pass-through is allowed only when orientation is identity."""
    asset = RasterImageAsset.from_bytes(_jpeg_bytes())

    assert asset.orientation == 1
    assert asset.mode == "RGB"
    assert asset.has_alpha is False
    assert asset.can_passthrough_jpeg is True


@pytest.mark.condition("RASTER-IMAGE-P3")
def test_raster_image_asset_allows_identity_cmyk_jpeg_passthrough() -> None:
    """RASTER-IMAGE-P3: Identity CMYK JPEGs can pass through with DeviceCMYK."""
    asset = RasterImageAsset.from_bytes(_cmyk_jpeg_bytes())

    assert asset.format == "JPEG"
    assert asset.mode == "CMYK"
    assert asset.jpeg_passthrough_color_space == "DeviceCMYK"
    assert asset.can_passthrough_jpeg is True


@pytest.mark.condition("RASTER-IMAGE-P2")
def test_raster_image_asset_exif_orientation_falls_back_for_malformed_metadata() -> None:
    """RASTER-IMAGE-P2: Malformed EXIF orientation metadata falls back to identity."""

    class BadExifImage:
        def getexif(self) -> object:
            """Return malformed EXIF metadata for the private boundary helper."""
            raise TypeError("bad exif")

    assert image_assets._exif_orientation(BadExifImage()) == 1  # noqa: SLF001


@pytest.mark.condition("RASTER-IMAGE-P1")
def test_raster_image_asset_rejects_malformed_bytes() -> None:
    """RASTER-IMAGE-P1: Malformed image bytes fail at the asset boundary."""
    with pytest.raises(ValueError, match="Pillow-decodable raster image"):
        RasterImageAsset.from_bytes(b"not an image")


@pytest.mark.condition("RASTER-IMAGE-P1")
def test_raster_image_asset_rejects_malformed_serialized_payloads() -> None:
    """RASTER-IMAGE-P1: Serialized image assets fail loudly when malformed."""
    with pytest.raises(ValueError, match="must include RasterImageAsset"):
        RasterImageAsset.create_from_dict({})
    with pytest.raises(TypeError, match="payload must be a mapping"):
        RasterImageAsset.create_from_dict({"RasterImageAsset": "bad"})
    with pytest.raises(TypeError, match="data_base64 must be a string"):
        RasterImageAsset.create_from_dict({"RasterImageAsset": {"data_base64": 5}})
    with pytest.raises(ValueError, match="valid base64"):
        RasterImageAsset.create_from_dict({"RasterImageAsset": {"data_base64": "not valid **"}})
    payload = RasterImageAsset.from_bytes(_image_bytes()).parameters
    payload["RasterImageAsset"]["source"] = 5
    with pytest.raises(TypeError, match="source must be a string or None"):
        RasterImageAsset.create_from_dict(payload)


@pytest.mark.condition("RASTER-IMAGE-P1")
@pytest.mark.parametrize(
    ("position", "width", "height", "exception_type", "message"),
    [
        ("12", 1.0, 1.0, ValueError, "position must contain two numeric values"),
        (object(), 1.0, 1.0, ValueError, "position must contain two numeric values"),
        ((1.0,), 1.0, 1.0, ValueError, "position must contain two numeric values"),
        ((1.0, 2.0, 3.0), 1.0, 1.0, ValueError, "position must contain two numeric values"),
        ((object(), 2.0), 1.0, 1.0, TypeError, "position coordinate must be numeric"),
        ((True, 2.0), 1.0, 1.0, TypeError, "position coordinate must be numeric"),
        ((float("nan"), 2.0), 1.0, 1.0, ValueError, "position coordinate must be finite"),
        ((1.0, 2.0), 0.0, 1.0, ValueError, "width must be greater than zero"),
        ((1.0, 2.0), -1.0, 1.0, ValueError, "width must be greater than zero"),
        ((1.0, 2.0), 1.0, 0.0, ValueError, "height must be greater than zero"),
        ((1.0, 2.0), 1.0, -1.0, ValueError, "height must be greater than zero"),
    ],
)
def test_image_pdf_rejects_invalid_shared_image_geometry(
    position: object,
    width: object,
    height: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """RASTER-IMAGE-P1: Shared image component geometry fails before rendering."""
    asset = RasterImageAsset.from_bytes(_image_bytes())

    with pytest.raises(exception_type, match=message):
        ImagePDF(asset, position, width, height)  # type: ignore[arg-type]


@pytest.mark.condition("RASTER-IMAGE-P1")
@pytest.mark.parametrize(
    ("position", "width", "height", "exception_type", "message"),
    [
        ("12", 1.0, 1.0, ValueError, "ImageDrawing position must contain two numeric values"),
        ((True, 2.0), 1.0, 1.0, TypeError, "ImageDrawing position coordinates must be numeric values"),
        ((float("nan"), 2.0), 1.0, 1.0, ValueError, "ImageDrawing position coordinates must be finite"),
        ((1.0, 2.0), 0.0, 1.0, ValueError, "ImageDrawing width must be greater than zero"),
        ((1.0, 2.0), 1.0, 0.0, ValueError, "ImageDrawing height must be greater than zero"),
    ],
)
def test_image_drawing_rejects_invalid_neutral_geometry(
    position: object,
    width: object,
    height: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """RASTER-IMAGE-P1: Neutral image geometry fails before materialization."""
    asset = RasterImageAsset.from_bytes(_image_bytes())

    with pytest.raises(exception_type, match=message):
        ImageDrawing(asset, position, width, height)  # type: ignore[arg-type]


@pytest.mark.condition("RASTER-IMAGE-P1")
def test_image_components_reject_non_image_assets() -> None:
    """RASTER-IMAGE-P1: Image components require RasterImageAsset instances."""
    with pytest.raises(TypeError, match="RasterImageAsset"):
        ImageDrawing(object(), (1.0, 2.0), 3.0, 4.0)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="RasterImageAsset"):
        ImagePDF(object(), (1.0, 2.0), 3.0, 4.0)  # type: ignore[arg-type]


@pytest.mark.condition("RASTER-IMAGE-P1")
def test_raster_image_component_rejects_malformed_payloads() -> None:
    """RASTER-IMAGE-P1: Serialized image components fail loudly when malformed."""
    from InkGen.image_assets import RasterImageComponent

    with pytest.raises(ValueError, match="must include RasterImageComponent"):
        RasterImageComponent.create_from_dict({})
    with pytest.raises(TypeError, match="payload must be a mapping"):
        RasterImageComponent.create_from_dict({"RasterImageComponent": "bad"})
    with pytest.raises(ValueError, match="RasterImageAsset"):
        RasterImageComponent.create_from_dict({"RasterImageComponent": {}})
    payload = ImagePDF(RasterImageAsset.from_bytes(_image_bytes()), (1.0, 2.0), 3.0, 4.0).parameters["ImagePDF"]
    with pytest.raises(ValueError, match="image position"):
        RasterImageComponent.create_from_dict({"RasterImageComponent": {**payload, "position": "bad"}})


@pytest.mark.condition("RASTER-IMAGE-P1")
def test_image_drawing_materializes_svg_and_pdf_components() -> None:
    """RASTER-IMAGE-P1: Neutral image drawings materialize to SVG and PDF only."""
    asset = RasterImageAsset.from_bytes(_image_bytes())
    drawing = ImageDrawing(asset, (10.0, 20.0), 30.0, 15.0)

    svg = drawing.to_component(OutputFormat.SVG)
    pdf = drawing.to_component(OutputFormat.PDF)
    group = DrawingComponentGroup("images", [drawing])

    assert isinstance(svg, ImageSVG)
    assert isinstance(pdf, ImagePDF)
    assert group.to_group(OutputFormat.SVG).bbox == group.to_group(OutputFormat.PDF).bbox
    assert svg.points == pdf.points == [(10.0, 20.0), (40.0, 20.0), (40.0, 35.0), (10.0, 35.0)]
    with pytest.raises(ValueError, match="Unsupported output format"):
        drawing.to_component("dxf")


@pytest.mark.condition("RASTER-IMAGE-P1")
def test_image_svg_embeds_png_data_uri_for_supported_input_formats() -> None:
    """RASTER-IMAGE-P1: SVG normalizes supported input formats to PNG data URIs."""
    asset = RasterImageAsset.from_bytes(_image_bytes("BMP", mode="RGB"))
    component = ImageSVG(asset, (3.0, 4.0), 5.0, 6.0)

    payload = component.generate_svg()

    assert 'x="3.0"' in payload
    assert 'y="4.0"' in payload
    assert 'width="5.0"' in payload
    assert 'height="6.0"' in payload
    assert 'href="data:image/png;base64,' in payload


@pytest.mark.condition("RASTER-IMAGE-P1")
def test_document_pdf_embeds_image_xobject_with_alpha_soft_mask() -> None:
    """RASTER-IMAGE-P1: PDF image alpha is emitted as a soft mask, not flattened."""
    asset = RasterImageAsset.from_bytes(_image_bytes("PNG", mode="RGBA"))
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    group = ComponentGroupPDF(f"image_{uuid.uuid4().hex}")
    group.add_component(ImagePDF(asset, (10.0, 20.0), 30.0, 15.0))
    document.page(1).layer("base").add_component_group(group)

    payload = document.to_pdf_bytes()
    streams = _flate_streams(payload)

    assert b"/Subtype /Image" in payload
    assert b"/SMask" in payload
    assert b"/ColorSpace /DeviceRGB" in payload
    assert b"/ColorSpace /DeviceGray" in payload
    assert b"/XObject << /Im1" in payload
    assert "30 0 0 -15 10 35 cm\n/Im1 Do" in payload.decode("latin-1")
    assert b"\x00\x80" in streams


@pytest.mark.condition("RASTER-IMAGE-P1")
def test_image_pdf_opaque_images_do_not_emit_soft_masks() -> None:
    """RASTER-IMAGE-P1: Opaque PDF images do not emit unnecessary SMask resources."""
    asset = RasterImageAsset.from_bytes(_image_bytes("PNG", mode="RGB"))
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    group = ComponentGroupPDF(f"image_{uuid.uuid4().hex}")
    group.add_component(ImagePDF(asset, (1.0, 2.0), 3.0, 4.0))
    document.page(1).layer("base").add_component_group(group)

    payload = document.to_pdf_bytes()

    assert b"/Subtype /Image" in payload
    assert b"/SMask" not in payload
    assert b"/ColorSpace /DeviceRGB" in payload


@pytest.mark.condition("RASTER-IMAGE-P2")
def test_document_pdf_passes_identity_rgb_jpegs_through_as_dct_streams() -> None:
    """RASTER-IMAGE-P2: PDF embeds identity RGB JPEG bytes without recompression."""
    jpeg = _jpeg_bytes()
    asset = RasterImageAsset.from_bytes(jpeg)
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    group = ComponentGroupPDF(f"image_{uuid.uuid4().hex}")
    group.add_component(ImagePDF(asset, (1.0, 2.0), 3.0, 4.0))
    document.page(1).layer("base").add_component_group(group)

    payload = document.to_pdf_bytes()

    assert b"/Filter /DCTDecode" in payload
    assert b"/SMask" not in payload
    assert jpeg in payload


@pytest.mark.condition("RASTER-IMAGE-P3")
def test_document_pdf_passes_identity_cmyk_jpegs_through_as_dct_streams() -> None:
    """RASTER-IMAGE-P3: PDF embeds identity CMYK JPEG bytes as DeviceCMYK."""
    jpeg = _cmyk_jpeg_bytes()
    asset = RasterImageAsset.from_bytes(jpeg)
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    group = ComponentGroupPDF(f"image_{uuid.uuid4().hex}")
    group.add_component(ImagePDF(asset, (1.0, 2.0), 3.0, 4.0))
    document.page(1).layer("base").add_component_group(group)

    payload = document.to_pdf_bytes()

    assert b"/Filter /DCTDecode" in payload
    assert b"/ColorSpace /DeviceCMYK" in payload
    assert b"/SMask" not in payload
    assert jpeg in payload


@pytest.mark.condition("RASTER-IMAGE-P3")
def test_document_pdf_embeds_jpeg_icc_profiles_as_iccbased_color_spaces() -> None:
    """RASTER-IMAGE-P3: JPEG ICC profiles are carried into PDF image resources."""
    profile = b"synthetic-icc-profile"
    jpeg = _jpeg_bytes(icc_profile=profile)
    asset = RasterImageAsset.from_bytes(jpeg)
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    group = ComponentGroupPDF(f"image_{uuid.uuid4().hex}")
    group.add_component(ImagePDF(asset, (1.0, 2.0), 3.0, 4.0))
    document.page(1).layer("base").add_component_group(group)

    payload = document.to_pdf_bytes()

    assert b"/Filter /DCTDecode" in payload
    assert b"/ColorSpace [/ICCBased " in payload
    assert b"/N 3" in payload
    assert b"/Alternate /DeviceRGB" in payload
    assert jpeg in payload


@pytest.mark.condition("RASTER-IMAGE-P3")
def test_document_pdf_embeds_cmyk_jpeg_icc_profiles_with_four_components() -> None:
    """RASTER-IMAGE-P3: CMYK JPEG ICC profiles declare four PDF components."""
    profile = b"synthetic-cmyk-icc-profile"
    jpeg = _cmyk_jpeg_bytes(icc_profile=profile)
    asset = RasterImageAsset.from_bytes(jpeg)
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    group = ComponentGroupPDF(f"image_{uuid.uuid4().hex}")
    group.add_component(ImagePDF(asset, (1.0, 2.0), 3.0, 4.0))
    document.page(1).layer("base").add_component_group(group)

    payload = document.to_pdf_bytes()

    assert b"/ColorSpace [/ICCBased " in payload
    assert b"/N 4" in payload
    assert b"/Alternate /DeviceCMYK" in payload
    assert jpeg in payload


@pytest.mark.condition("RASTER-IMAGE-P2")
def test_document_pdf_decodes_oriented_jpegs_before_embedding() -> None:
    """RASTER-IMAGE-P2: PDF does not pass through JPEG bytes requiring EXIF rotation."""
    jpeg = _jpeg_bytes(orientation=6, size=(2, 3))
    asset = RasterImageAsset.from_bytes(jpeg)
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    group = ComponentGroupPDF(f"image_{uuid.uuid4().hex}")
    group.add_component(ImagePDF(asset, (1.0, 2.0)))
    document.page(1).layer("base").add_component_group(group)

    payload = document.to_pdf_bytes()

    assert b"/Filter /DCTDecode" not in payload
    assert b"/Filter /FlateDecode" in payload
    assert b"/Width 3 /Height 2" in payload


@pytest.mark.condition("RASTER-IMAGE-P1")
def test_document_pdf_reuses_images_and_coexists_with_font_resources() -> None:
    """RASTER-IMAGE-P1: PDF image resources are deterministic and coexist with fonts."""
    first = RasterImageAsset.from_bytes(_image_bytes("PNG", mode="RGB"))
    second = RasterImageAsset.from_bytes(_image_bytes("BMP", mode="RGB"))
    text_style = TextStyle(f"image_text_{uuid.uuid4().hex}", Font(size=8.0))
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_page()
    first_group = ComponentGroupPDF(f"image_{uuid.uuid4().hex}")
    first_group.add_component(ImagePDF(first, (1.0, 2.0), 3.0, 4.0))
    first_group.add_component(ImagePDF(second, (5.0, 6.0), 7.0, 8.0))
    first_group.add_component(TextPDF("A", (9.0, 10.0), text_style))
    second_group = ComponentGroupPDF(f"image_{uuid.uuid4().hex}")
    second_group.add_component(ImagePDF(first, (11.0, 12.0), 13.0, 14.0))
    document.page(1).layer("base").add_component_group(first_group)
    document.page(2).layer("base").add_component_group(second_group)

    payload = document.to_pdf_bytes()

    assert payload.count(b"/Subtype /Image") == 2
    assert b"/XObject << /Im1" in payload
    assert b"/Im2" in payload
    assert b"/Font <<" in payload
    assert b"/Count 2" in payload
    kids_match = re.search(rb"/Kids \[(?P<kids>[^\]]+)\]", payload)
    assert kids_match is not None
    page_ids = [int(value) for value in re.findall(rb"(\d+) 0 R", kids_match.group("kids"))]
    assert len(page_ids) == 2
    for page_id in page_ids:
        assert re.search(rb"%d 0 obj\n<< /Type /Page\b" % page_id, payload) is not None
    assert payload.decode("latin-1").count("/Im1 Do") == 2


@pytest.mark.condition("RASTER-IMAGE-P1")
def test_image_parameters_round_trip_for_svg_and_pdf() -> None:
    """RASTER-IMAGE-P1: Image components preserve serialized parameters."""
    asset = RasterImageAsset.from_bytes(_image_bytes())
    svg = ImageSVG(asset, (1.0, 2.0), 3.0, 4.0)
    pdf = ImagePDF(asset, (1.0, 2.0), 3.0, 4.0)

    assert ImageSVG.create_from_dict(svg.parameters).parameters == svg.parameters
    assert ImagePDF.create_from_dict(pdf.parameters).parameters == pdf.parameters
