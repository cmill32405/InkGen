"""Tests for flow-document output formats."""

from __future__ import annotations

import zipfile
from io import BytesIO
from uuid import uuid4

import pytest
from PIL import Image

from InkGen.component import PathCommand
from InkGen.document_outputs import DocumentOutputFormat, FlowDocument
from InkGen.drawing_components import (
    CircleDrawing,
    DrawingComponentGroup,
    ImageDrawing,
    LineDrawing,
    PathDrawing,
    RectangleDrawing,
    TextDrawing,
)
from InkGen.image_assets import RasterImageAsset
from InkGen.paragraph import LineSpacingRule, Paragraph
from InkGen.style import DrawingStyle, Font, TextStyle
from InkGen.table import Table


def _paragraph(text: str = "Hello document world") -> Paragraph:
    style = TextStyle(f"doc_text_{uuid4().hex}", Font(size=11.0))
    return Paragraph(
        text,
        position=(0.0, 0.0),
        width=120.0,
        style=style,
        alignment="justify",
        first_line_indent=5.0,
        space_before=2.0,
        space_after=3.0,
        line_spacing=1.15,
        line_spacing_rule=LineSpacingRule.MULTIPLE,
        keep_with_next=True,
    )


def _table() -> Table:
    table = Table(position=(0.0, 0.0))
    table.add_column(width=25.0)
    table.add_column(width=35.0)
    table.add_row(height=8.0)
    table.add_row(height=8.0)
    table.cell(0, 0).add_paragraph("Item")
    table.cell(0, 1).add_paragraph("Description")
    table.cell(1, 0).add_paragraph("001")
    table.cell(1, 1).add_paragraph("Synthetic bracket")
    return table


def _drawing_group() -> DrawingComponentGroup:
    drawing_style = DrawingStyle(f"doc_draw_{uuid4().hex}", stroke="#000000", fill="none")
    text_style = TextStyle(f"doc_note_{uuid4().hex}", Font(size=8.0))
    group = DrawingComponentGroup("document-detail")
    group.add_component(RectangleDrawing((0.0, 0.0), 20.0, 10.0, 0.0, drawing_style))
    group.add_component(LineDrawing((0.0, 0.0), (20.0, 10.0), drawing_style))
    group.add_component(CircleDrawing((8.0, 5.0), 3.0, drawing_style))
    group.add_component(PathDrawing(drawing_style, [PathCommand("M", [(2.0, 2.0)]), PathCommand("L", [(6.0, 2.0)])]))
    group.add_component(TextDrawing("DETAIL A", (2.0, 8.0), text_style))
    return group


def _image_asset(color: tuple[int, int, int, int] = (255, 0, 0, 128)) -> RasterImageAsset:
    image = Image.new("RGBA", (2, 1), color)
    image.putpixel((0, 0), (255, 0, 0, 0))
    output = BytesIO()
    image.save(output, format="PNG")
    return RasterImageAsset.from_bytes(output.getvalue())


def _jpeg_asset(*, orientation: int = 1) -> tuple[RasterImageAsset, bytes]:
    image = Image.new("RGB", (2, 3), (255, 0, 0))
    output = BytesIO()
    save_kwargs: dict[str, object] = {}
    if orientation != 1:
        exif = Image.Exif()
        exif[274] = orientation
        save_kwargs["exif"] = exif
    image.save(output, format="JPEG", **save_kwargs)
    data = output.getvalue()
    return RasterImageAsset.from_bytes(data), data


@pytest.mark.condition("PDF-P3")
def test_flow_document_exports_minimal_docx_package() -> None:
    """PDF-P3: FlowDocument writes a valid minimal DOCX package from paragraphs."""
    document = FlowDocument(title="Synthetic Instructions")
    document.add_paragraph(_paragraph("Alpha & beta"))

    payload = document.to_docx_bytes()
    with zipfile.ZipFile(BytesIO(payload)) as package:
        names = set(package.namelist())
        document_xml = package.read("word/document.xml").decode("utf-8")

    assert "[Content_Types].xml" in names
    assert "_rels/.rels" in names
    assert "word/document.xml" in names
    assert "word/styles.xml" in names
    assert "Alpha &amp; beta" in document_xml
    assert 'w:jc w:val="both"' in document_xml
    assert "<w:keepNext/>" in document_xml


@pytest.mark.condition("PDF-P3")
def test_flow_document_exports_html_rtf_and_text() -> None:
    """PDF-P3: FlowDocument supports lightweight document interchange formats."""
    document = FlowDocument(title="Doc")
    document.add_paragraph(_paragraph("Line one\nLine two"))

    html = document.to_html()
    markdown = document.to_markdown()
    rtf = document.to_rtf()
    text = document.to_plain_text()

    assert DocumentOutputFormat.MARKDOWN.value == "md"
    assert "<!doctype html>" in html
    assert "Line one<br>Line two" in html
    assert markdown == "# Doc\n\nLine one  \nLine two\n"
    assert r"{\rtf1" in rtf
    assert r"\qj" in rtf
    assert text == "Line one\nLine two"


@pytest.mark.condition("PDF-P3")
def test_flow_document_round_trips_parameters() -> None:
    """PDF-P3: FlowDocument serializes and recreates paragraph content."""
    document = FlowDocument(title="Round Trip")
    paragraph = _paragraph("Persist me")
    document.add_paragraph(paragraph)

    clone = FlowDocument.create_from_dict(document.parameters, {paragraph.style.name: paragraph.style})

    assert clone.parameters == document.parameters
    assert clone.to_plain_text() == "Persist me"


@pytest.mark.condition("PDF-P3")
def test_flow_document_exports_tables_and_drawing_primitives() -> None:
    """PDF-P3: FlowDocument exports ordered paragraphs, tables, and drawing primitives."""
    document = FlowDocument(title="Mixed")
    paragraph = _paragraph("Assembly notes")
    table = _table()
    drawing = _drawing_group()
    styles = {
        paragraph.style.name: paragraph.style,
        drawing.components[0].style.name: drawing.components[0].style,
        drawing.components[-1].style.name: drawing.components[-1].style,
    }

    document.add_paragraph(paragraph)
    document.add_table(table)
    document.add_drawing_group(drawing)

    text = document.to_plain_text()
    html = document.to_html()
    markdown = document.to_markdown()
    clone = FlowDocument.create_from_dict(document.parameters, styles)
    with zipfile.ZipFile(BytesIO(document.to_docx_bytes())) as package:
        document_xml = package.read("word/document.xml").decode("utf-8")

    assert [block.__class__.__name__ for block in document.blocks] == ["Paragraph", "Table", "DrawingComponentGroup"]
    assert "Assembly notes" in text
    assert "Item\tDescription" in text
    assert "[Drawing: document-detail;" in text
    assert "<table>" in html
    assert "<svg" in html
    assert "DETAIL A" in html
    assert "| Item | Description |" in markdown
    assert "| --- | --- |" in markdown
    assert "<svg" in markdown
    assert "DETAIL A" in markdown
    assert "<w:tbl>" in document_xml
    assert "<w:pict>" not in document_xml
    assert "<wp:anchor" in document_xml
    assert "<wps:wsp>" in document_xml
    assert 'prst="rect"' in document_xml
    assert 'prst="ellipse"' in document_xml
    assert "DETAIL A" in document_xml
    assert clone.to_plain_text() == text


@pytest.mark.condition("RASTER-IMAGE-P2")
def test_flow_document_docx_embeds_image_drawings_as_native_media_parts() -> None:
    """RASTER-IMAGE-P2: DOCX image drawings use package media parts and DrawingML."""
    asset = _image_asset()
    group = DrawingComponentGroup("image-docx")
    group.add_component(ImageDrawing(asset, (1.0, 2.0), 30.0, 15.0))
    document = FlowDocument(title="Images")
    document.add_drawing_group(group)

    with zipfile.ZipFile(BytesIO(document.to_docx_bytes())) as package:
        names = set(package.namelist())
        document_xml = package.read("word/document.xml").decode("utf-8")
        rels_xml = package.read("word/_rels/document.xml.rels").decode("utf-8")
        content_types = package.read("[Content_Types].xml").decode("utf-8")
        media = package.read("word/media/image1.png")

    with Image.open(BytesIO(media)) as image:
        image.load()
        assert image.mode == "RGBA"
        assert image.getpixel((0, 0))[3] == 0

    assert "word/media/image1.png" in names
    assert '<Default Extension="png" ContentType="image/png"/>' in content_types
    assert 'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"' in rels_xml
    assert 'Target="media/image1.png"' in rels_xml
    assert "<w:drawing>" in document_xml
    assert 'r:embed="rId1"' in document_xml
    assert 'cx="1080000" cy="540000"' in document_xml
    assert "data:image" not in document_xml


@pytest.mark.condition("RASTER-IMAGE-P3")
def test_flow_document_docx_preserves_identity_png_source_bytes() -> None:
    """RASTER-IMAGE-P3: DOCX keeps safe PNG source bytes instead of re-encoding."""
    asset = _image_asset()
    group = DrawingComponentGroup("png-docx")
    group.add_component(ImageDrawing(asset, (1.0, 2.0), 30.0, 15.0))
    document = FlowDocument(title="PNG Images")
    document.add_drawing_group(group)

    with zipfile.ZipFile(BytesIO(document.to_docx_bytes())) as package:
        media = package.read("word/media/image1.png")

    assert media == asset.data


@pytest.mark.condition("RASTER-IMAGE-P3")
def test_flow_document_docx_preserves_identity_jpegs_as_native_media_parts() -> None:
    """RASTER-IMAGE-P3: DOCX keeps identity-orientation JPEG media native."""
    asset, jpeg = _jpeg_asset()
    group = DrawingComponentGroup("jpeg-docx")
    group.add_component(ImageDrawing(asset, (1.0, 2.0), 30.0, 15.0))
    document = FlowDocument(title="JPEG Images")
    document.add_drawing_group(group)

    with zipfile.ZipFile(BytesIO(document.to_docx_bytes())) as package:
        names = set(package.namelist())
        rels_xml = package.read("word/_rels/document.xml.rels").decode("utf-8")
        content_types = package.read("[Content_Types].xml").decode("utf-8")
        media = package.read("word/media/image1.jpg")

    assert "word/media/image1.jpg" in names
    assert media == jpeg
    assert '<Default Extension="jpg" ContentType="image/jpeg"/>' in content_types
    assert 'Target="media/image1.jpg"' in rels_xml


@pytest.mark.condition("RASTER-IMAGE-P3")
def test_flow_document_docx_normalizes_oriented_jpegs_to_png_media_parts() -> None:
    """RASTER-IMAGE-P3: DOCX normalizes oriented JPEGs before media packaging."""
    asset, _ = _jpeg_asset(orientation=6)
    group = DrawingComponentGroup("oriented-jpeg-docx")
    group.add_component(ImageDrawing(asset, (1.0, 2.0), 30.0, 15.0))
    document = FlowDocument(title="Oriented JPEG Images")
    document.add_drawing_group(group)

    with zipfile.ZipFile(BytesIO(document.to_docx_bytes())) as package:
        names = set(package.namelist())
        rels_xml = package.read("word/_rels/document.xml.rels").decode("utf-8")
        content_types = package.read("[Content_Types].xml").decode("utf-8")
        media = package.read("word/media/image1.png")

    with Image.open(BytesIO(media)) as image:
        image.load()
        assert image.size == (3, 2)

    assert "word/media/image1.png" in names
    assert "word/media/image1.jpg" not in names
    assert '<Default Extension="png" ContentType="image/png"/>' in content_types
    assert 'Target="media/image1.png"' in rels_xml


@pytest.mark.condition("RASTER-IMAGE-P2")
def test_flow_document_docx_assigns_distinct_relationships_to_distinct_images() -> None:
    """RASTER-IMAGE-P2: DOCX media registry assigns deterministic image parts."""
    group = DrawingComponentGroup("two-images")
    group.add_component(ImageDrawing(_image_asset((255, 0, 0, 128)), (1.0, 2.0), 3.0, 4.0))
    group.add_component(ImageDrawing(_image_asset((0, 0, 255, 128)), (5.0, 6.0), 7.0, 8.0))
    document = FlowDocument(title="Two Images")
    document.add_drawing_group(group)

    with zipfile.ZipFile(BytesIO(document.to_docx_bytes())) as package:
        names = package.namelist()
        document_xml = package.read("word/document.xml").decode("utf-8")
        rels_xml = package.read("word/_rels/document.xml.rels").decode("utf-8")

    assert "word/media/image1.png" in names
    assert "word/media/image2.png" in names
    assert 'r:embed="rId1"' in document_xml
    assert 'r:embed="rId2"' in document_xml
    assert 'Target="media/image1.png"' in rels_xml
    assert 'Target="media/image2.png"' in rels_xml


@pytest.mark.condition("RASTER-IMAGE-P2", "FLOW-DOCUMENT-DRAWINGML-P3")
def test_flow_document_docx_keeps_vector_coordinates_when_images_share_drawing_group() -> None:
    """RASTER-IMAGE-P2: Native images do not distort DOCX DrawingML vectors."""
    group = DrawingComponentGroup("mixed-image-vector")
    group.add_component(RectangleDrawing((1.0, 2.0), 10.0, 5.0, 0.0, DrawingStyle(f"mixed_{uuid4().hex}")))
    group.add_component(ImageDrawing(_image_asset(), (20.0, 30.0), 3.0, 4.0))
    document = FlowDocument(title="Mixed Image")
    document.add_drawing_group(group)

    with zipfile.ZipFile(BytesIO(document.to_docx_bytes())) as package:
        document_xml = package.read("word/document.xml").decode("utf-8")

    assert '<wp:positionH relativeFrom="column"><wp:posOffset>0</wp:posOffset></wp:positionH>' in document_xml
    assert '<wp:positionV relativeFrom="paragraph"><wp:posOffset>0</wp:posOffset></wp:positionV>' in document_xml
    assert 'cx="360000" cy="180000"' in document_xml
    assert "word/media/image" not in document_xml
    assert "<w:drawing>" in document_xml
    assert "<w:pict>" not in document_xml


@pytest.mark.condition("RASTER-IMAGE-P2")
def test_flow_document_image_drawing_parameters_round_trip_without_style() -> None:
    """RASTER-IMAGE-P2: FlowDocument serializes image drawings without style payloads."""
    group = DrawingComponentGroup("image-round-trip")
    group.add_component(ImageDrawing(_image_asset(), (1.0, 2.0), 3.0, 4.0))
    document = FlowDocument(title="Image Round Trip")
    document.add_drawing_group(group)

    clone = FlowDocument.create_from_dict(document.parameters)

    assert clone.parameters == document.parameters
    assert clone.to_plain_text() == "[Drawing: image-round-trip; ImageDrawing]"


@pytest.mark.condition("RASTER-IMAGE-P2")
def test_flow_document_image_and_path_hydration_dispatch_dynamic_type_strings() -> None:
    """RASTER-IMAGE-P2: Image and path drawing hydration uses string equality."""
    style = DrawingStyle(f"path_{uuid4().hex}", stroke="#000000", fill="none")
    group = DrawingComponentGroup("dynamic-types")
    group.add_component(ImageDrawing(_image_asset(), (1.0, 2.0), 3.0, 4.0))
    group.add_component(PathDrawing(style, [PathCommand("M", [(1.0, 2.0)]), PathCommand("L", [(3.0, 4.0)])]))
    document = FlowDocument(title="Dynamic Types")
    document.add_drawing_group(group)
    payload = document.parameters
    flow_payload = payload["FlowDocument"]
    assert isinstance(flow_payload, dict)
    blocks = flow_payload["blocks"]
    assert isinstance(blocks, list)
    components = blocks[0]["payload"]["components"]
    assert isinstance(components, list)
    path_payload = components[1]["payload"]
    assert isinstance(path_payload, dict)
    assert path_payload["commands"] == [
        {"type": "M", "points": [(1.0, 2.0)]},
        {"type": "L", "points": [(3.0, 4.0)]},
    ]
    for component_payload in components:
        component_type = component_payload["type"]
        assert isinstance(component_type, str)
        component_payload["type"] = "".join([component_type[:-1], component_type[-1:]])

    clone = FlowDocument.create_from_dict(payload, {style.name: style})

    assert clone.parameters == document.parameters


@pytest.mark.condition("RASTER-IMAGE-P2")
@pytest.mark.parametrize("component_payload", [{"payload": {}}, {"type": "ImageDrawing"}])
def test_flow_document_image_drawing_hydration_rejects_partial_component_envelopes(component_payload: object) -> None:
    """RASTER-IMAGE-P2: Image component hydration requires full type/payload envelope."""
    payload = {
        "FlowDocument": {
            "title": "Bad Envelope",
            "blocks": [
                {
                    "type": "drawing",
                    "payload": {
                        "group_label": "bad-envelope",
                        "components": [component_payload],
                    },
                }
            ],
        }
    }

    with pytest.raises(ValueError, match="component must include type and payload"):
        FlowDocument.create_from_dict(payload)


@pytest.mark.condition("RASTER-IMAGE-P2")
def test_flow_document_image_drawing_hydration_rejects_missing_image_payload() -> None:
    """RASTER-IMAGE-P2: Image drawing hydration requires serialized image bytes."""
    group = DrawingComponentGroup("bad-image")
    group.add_component(ImageDrawing(_image_asset(), (1.0, 2.0), 3.0, 4.0))
    document = FlowDocument(title="Bad Image")
    document.add_drawing_group(group)
    payload = document.parameters
    flow_payload = payload["FlowDocument"]
    assert isinstance(flow_payload, dict)
    blocks = flow_payload["blocks"]
    assert isinstance(blocks, list)
    block_payload = blocks[0]["payload"]
    assert isinstance(block_payload, dict)
    components = block_payload["components"]
    assert isinstance(components, list)
    image_payload = components[0]["payload"]
    assert isinstance(image_payload, dict)
    image_payload.pop("image")

    with pytest.raises(ValueError, match="image drawing payload must include image"):
        FlowDocument.create_from_dict(payload)


@pytest.mark.condition("PDF-P3")
def test_flow_document_file_writers_fail_on_missing_directory(tmp_path) -> None:
    """PDF-P3: FlowDocument file writers fail loudly for invalid output paths."""
    document = FlowDocument()
    document.add_paragraph(_paragraph())

    target = tmp_path / "document.docx"
    document.create_docx(str(target))
    assert target.read_bytes() == document.to_docx_bytes()

    with pytest.raises(ValueError, match="file path does not exist"):
        document.create_html(str(tmp_path / "missing" / "document.html"))


@pytest.mark.condition("PDF-P3")
def test_flow_document_rejects_non_paragraph_content() -> None:
    """PDF-P3: FlowDocument accepts only Paragraph objects."""
    document = FlowDocument()

    with pytest.raises(TypeError, match="paragraph must be a Paragraph"):
        document.add_paragraph(object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="table must be a Table"):
        document.add_table(object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="group must be a DrawingComponentGroup"):
        document.add_drawing_group(object())  # type: ignore[arg-type]
