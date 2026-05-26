"""Tests for flow-document output formats."""

from __future__ import annotations

import zipfile
from io import BytesIO
from uuid import uuid4

import pytest

from InkGen.component import PathCommand
from InkGen.document_outputs import FlowDocument
from InkGen.drawing_components import (
    CircleDrawing,
    DrawingComponentGroup,
    LineDrawing,
    PathDrawing,
    RectangleDrawing,
    TextDrawing,
)
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
    rtf = document.to_rtf()
    text = document.to_plain_text()

    assert "<!doctype html>" in html
    assert "Line one<br>Line two" in html
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
    assert "<w:tbl>" in document_xml
    assert "<w:pict>" in document_xml
    assert "<v:group" in document_xml
    assert clone.to_plain_text() == text


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
