"""Behavioral tests for flow-document output contracts."""

from __future__ import annotations

import zipfile
from io import BytesIO
from uuid import uuid4

import pytest

from InkGen.document_outputs import DOCX_FIXED_TIMESTAMP, FlowDocument
from InkGen.drawing_components import DrawingComponentGroup, LineDrawing, OutputFormat, RectangleDrawing
from InkGen.paragraph import LineSpacingRule, Paragraph
from InkGen.style import DrawingStyle, Font, TextStyle
from InkGen.table import Table


class _InvalidDrawingPrimitive:
    def to_component(self, output_format: OutputFormat | str) -> object:
        """Return an invalid concrete materialization for failure-path tests."""
        return object()


class _AttributeOnlyDrawingPrimitive:
    to_component = None


def _text_style() -> TextStyle:
    return TextStyle(f"flow_text_{uuid4().hex}", Font(size=11.0))


def _drawing_style() -> DrawingStyle:
    return DrawingStyle(f"flow_draw_{uuid4().hex}", stroke="#222222", fill="none", stroke_width=0.2)


def _paragraph(text: str) -> Paragraph:
    return Paragraph(
        text,
        position=(0.0, 0.0),
        width=120.0,
        style=_text_style(),
        alignment="justify",
        first_line_indent=5.0,
        line_spacing=1.15,
        line_spacing_rule=LineSpacingRule.MULTIPLE,
        keep_with_next=True,
    )


def _table() -> Table:
    table = Table(position=(0.0, 0.0))
    table.add_column(width=25.0)
    table.add_column(width=25.0)
    table.add_row(height=8.0)
    table.cell(0, 0).add_paragraph("PN")
    table.cell(0, 1).add_paragraph("Qty")
    return table


def _drawing_group() -> DrawingComponentGroup:
    group = DrawingComponentGroup("flow-drawing")
    group.add_component(RectangleDrawing((1.0, 2.0), 10.0, 5.0, 0.0, _drawing_style()))
    return group


@pytest.mark.condition("FLOW-DOCUMENT-P1")
def test_flow_document_docx_bytes_are_deterministic() -> None:
    """FLOW-DOCUMENT-P1: Repeated DOCX generation emits stable package bytes."""
    document = FlowDocument(title="Stable")
    document.add_paragraph(_paragraph("Alpha & beta"))

    first = document.to_docx_bytes()
    second = document.to_docx_bytes()

    assert first == second
    with zipfile.ZipFile(BytesIO(first)) as package:
        assert all(package.getinfo(name).date_time == DOCX_FIXED_TIMESTAMP for name in package.namelist())
        assert package.namelist() == [
            "[Content_Types].xml",
            "_rels/.rels",
            "word/document.xml",
            "word/styles.xml",
            "word/_rels/document.xml.rels",
        ]


@pytest.mark.condition("FLOW-DOCUMENT-P1")
def test_flow_document_escapes_text_across_output_formats() -> None:
    """FLOW-DOCUMENT-P1: DOCX, HTML, and RTF escape format control characters."""
    document = FlowDocument(title="Control {Doc}")
    document.add_paragraph(_paragraph("A&B <tag> {x}\\y"))

    with zipfile.ZipFile(BytesIO(document.to_docx_bytes())) as package:
        document_xml = package.read("word/document.xml").decode("utf-8")
    html = document.to_html()
    rtf = document.to_rtf()

    assert "A&amp;B &lt;tag&gt; {x}\\y" in document_xml
    assert "A&amp;B &lt;tag&gt; {x}\\y" in html
    assert r"Control \{Doc\}" in rtf
    assert r"A&B <tag> \{x\}\\y" in rtf


@pytest.mark.condition("FLOW-DOCUMENT-TITLE-P2")
@pytest.mark.parametrize("title", [123, object(), ["Doc"]])
def test_flow_document_rejects_non_string_titles(title: object) -> None:
    """FLOW-DOCUMENT-TITLE-P2: Flow-document titles must be strings or None."""
    with pytest.raises(TypeError, match="title must be a string or None"):
        FlowDocument(title=title)  # type: ignore[arg-type]


@pytest.mark.condition("FLOW-DOCUMENT-TITLE-P2")
@pytest.mark.parametrize("title", [None, ""])
def test_flow_document_default_title_is_preserved(title: str | None) -> None:
    """FLOW-DOCUMENT-TITLE-P2: None and empty titles keep the existing default."""
    document = FlowDocument(title=title)

    assert document.title == "InkGen Document"
    assert "<h1>InkGen Document</h1>" in document.to_html()


@pytest.mark.condition("FLOW-DOCUMENT-TITLE-P2")
def test_flow_document_title_hydration_rejects_malformed_title() -> None:
    """FLOW-DOCUMENT-TITLE-P2: Serialized titles cannot be silently stringified."""
    payload = {"FlowDocument": {"title": object(), "blocks": []}}

    with pytest.raises(TypeError, match="title must be a string or None"):
        FlowDocument.create_from_dict(payload)


@pytest.mark.condition("FLOW-DOCUMENT-TITLE-P2")
def test_flow_document_valid_title_round_trips_and_escapes() -> None:
    """FLOW-DOCUMENT-TITLE-P2: Valid titles round-trip and remain escaped in outputs."""
    document = FlowDocument(title="A&B <Doc> {1}")
    clone = FlowDocument.create_from_dict(document.parameters)

    assert clone.parameters == document.parameters
    assert "<h1>A&amp;B &lt;Doc&gt; {1}</h1>" in clone.to_html()
    assert r"\b A&B <Doc> \{1\}\b0\par" in clone.to_rtf()


@pytest.mark.condition("FLOW-DOCUMENT-P1")
def test_flow_document_preserves_mixed_block_order_after_round_trip() -> None:
    """FLOW-DOCUMENT-P1: Parameters preserve paragraph, table, and drawing block order."""
    document = FlowDocument(title="Mixed")
    paragraph = _paragraph("Intro")
    table = _table()
    drawing = _drawing_group()

    document.add_paragraph(paragraph)
    document.add_table(table)
    document.add_drawing_group(drawing)

    clone = FlowDocument.create_from_dict(
        document.parameters,
        {
            paragraph.style.name: paragraph.style,
            drawing.components[0].style.name: drawing.components[0].style,
        },
    )

    assert [block.__class__.__name__ for block in clone.blocks] == ["Paragraph", "Table", "DrawingComponentGroup"]
    assert clone.parameters == document.parameters
    assert clone.to_plain_text() == "Intro\n\nPN\tQty\n\n[Drawing: flow-drawing; RectangleDrawing]"


@pytest.mark.condition("FLOW-DOCUMENT-P1")
def test_flow_document_rejects_invalid_drawing_materialization() -> None:
    """FLOW-DOCUMENT-P1: Invalid drawing recipes fail before silent output omission."""
    document = FlowDocument()
    group = DrawingComponentGroup("invalid")
    group.components.append(_InvalidDrawingPrimitive())  # type: ignore[arg-type]
    document.add_drawing_group(group)

    with pytest.raises(TypeError, match="must return an InkGen Component"):
        document.to_html()
    with pytest.raises(TypeError, match="must return an InkGen Component"):
        document.to_docx_bytes()

    group.components.clear()
    group.components.append(_AttributeOnlyDrawingPrimitive())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="must implement to_component"):
        document.to_html()


@pytest.mark.condition("FLOW-DOCUMENT-P1")
def test_flow_document_docx_drawing_polyline_uses_group_relative_points() -> None:
    """FLOW-DOCUMENT-P1: DOCX VML drawing points are relative to drawing bounds."""
    document = FlowDocument()
    group = DrawingComponentGroup("linework")
    group.add_component(LineDrawing((2.0, 3.0), (5.0, 7.0), _drawing_style()))
    document.add_drawing_group(group)

    with zipfile.ZipFile(BytesIO(document.to_docx_bytes())) as package:
        document_xml = package.read("word/document.xml").decode("utf-8")

    assert 'coordsize="3 4"' in document_xml
    assert '<v:polyline points="0,0 3,4"/>' in document_xml


@pytest.mark.condition("FLOW-DOCUMENT-P1")
def test_flow_document_text_writers_create_requested_files(tmp_path) -> None:
    """FLOW-DOCUMENT-P1: HTML, RTF, and text writers persist generated payloads."""
    document = FlowDocument(title="Files")
    document.add_paragraph(_paragraph("Persisted"))
    html_path = tmp_path / "document.html"
    rtf_path = tmp_path / "document.rtf"
    text_path = tmp_path / "document.txt"

    document.create_html(str(html_path))
    document.create_rtf(str(rtf_path))
    document.create_text(str(text_path))

    assert html_path.read_text(encoding="utf-8") == document.to_html()
    assert rtf_path.read_text(encoding="utf-8") == document.to_rtf()
    assert text_path.read_text(encoding="utf-8") == "Persisted"
