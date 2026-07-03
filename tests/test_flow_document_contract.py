"""Behavioral tests for flow-document output contracts."""

from __future__ import annotations

import zipfile
from io import BytesIO
from uuid import uuid4
from xml.etree import ElementTree

import pytest

from InkGen.component import Component, PathCommand
from InkGen.document_outputs import (
    DOCX_FIXED_TIMESTAMP,
    FlowDocument,
    _component_drawingml,
    _DocxMediaRegistry,
    _drawingml_fill,
    _drawingml_line,
    _drawingml_segments_docx,
    _drawingml_shape_docx,
    _drawingml_text_body,
    _nonnegative_artifact_number,
    _vml_number,
)
from InkGen.drawing_components import (
    ArcDrawing,
    CircleDrawing,
    CubicBezierDrawing,
    DrawingComponentGroup,
    LineDrawing,
    OutputFormat,
    PathDrawing,
    PolygonalDrawing,
    QuadraticBezierDrawing,
    RectangleDrawing,
    RegularPolygonDrawing,
    TextDrawing,
)
from InkGen.paragraph import LineSpacingRule, Paragraph
from InkGen.style import DrawingStyle, Font, TextStyle
from InkGen.table import Table


class _InvalidDrawingPrimitive:
    def to_component(self, output_format: OutputFormat | str) -> object:
        """Return an invalid concrete materialization for failure-path tests."""
        return object()


class _AttributeOnlyDrawingPrimitive:
    to_component = None


class _BareComponentDrawingPrimitive:
    def to_component(self, output_format: OutputFormat | str) -> Component:
        """Return a base component that cannot render as SVG or DOCX DrawingML."""
        return Component()


class _NonStringSvgComponent(Component):
    def generate_svg(self) -> object:
        """Return a malformed SVG fragment for failure-path tests."""
        return object()


class _NonStringSvgDrawingPrimitive:
    def to_component(self, output_format: OutputFormat | str) -> Component:
        """Return a component whose SVG renderer violates the fragment contract."""
        return _NonStringSvgComponent()


class _PointSurfaceComponent(Component):
    def __init__(self, points: object) -> None:
        """Store a test-controlled materialized points surface."""
        super().__init__()
        self._points = points

    @property
    def points(self) -> object:
        """Return the configured points surface."""
        return self._points

    def generate_svg(self) -> str:
        """Return a minimal SVG fragment for document-output tests."""
        return "<path/>"


class _PointSurfaceDrawingPrimitive:
    def __init__(self, points: object) -> None:
        """Store a test-controlled materialized points surface."""
        self._points = points

    def to_component(self, output_format: OutputFormat | str) -> Component:
        """Return a component whose points surface is controlled by the test."""
        return _PointSurfaceComponent(self._points)


class _SerializableDrawingLookalike:
    def __init__(self) -> None:
        """Expose rectangle-like fields without being a RectangleDrawing."""
        self.position = (1.0, 2.0)
        self.width = 3.0
        self.height = 4.0
        self.corner_radii = 0.0
        self.style = _drawing_style()

    def to_component(self, output_format: OutputFormat | str) -> Component:
        """Return a valid component so the serialization type check is isolated."""
        return RectangleDrawing(self.position, self.width, self.height, self.corner_radii, self.style).to_component(output_format)


_SerializableDrawingLookalike.__name__ = "RectangleDrawing"


class _ValueErrorFloat:
    def __float__(self) -> float:
        """Raise ValueError from float conversion for boundary tests."""
        raise ValueError("bad float")


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


def _flow_document_with_paragraph() -> FlowDocument:
    """Return a minimal flow document for writer-boundary tests."""
    document = FlowDocument(title="Writer Boundary")
    document.add_paragraph(_paragraph("Export me"))
    return document


def _all_supported_drawing_group() -> DrawingComponentGroup:
    drawing_style = _drawing_style()
    text_style = _text_style()
    group = DrawingComponentGroup("all-flow-drawings")
    group.add_component(RectangleDrawing((1.0, 2.0), 10.0, 5.0, 0.0, drawing_style))
    group.add_component(LineDrawing((1.0, 1.0), (6.0, 4.0), drawing_style))
    group.add_component(TextDrawing("NOTE", (2.0, 3.0), text_style))
    group.add_component(ArcDrawing(center=(5.0, 5.0), radius_x=4.0, radius_y=3.0, start_angle=0.0, end_angle=90.0, style=drawing_style))
    group.add_component(QuadraticBezierDrawing((0.0, 0.0), (3.0, 4.0), (6.0, 0.0), drawing_style))
    group.add_component(CubicBezierDrawing((0.0, 0.0), (2.0, 5.0), (4.0, 5.0), (6.0, 0.0), drawing_style))
    group.add_component(PathDrawing(drawing_style, [PathCommand("M", [(0.0, 0.0)]), PathCommand("L", [(3.0, 0.0)])]))
    group.add_component(RegularPolygonDrawing(position=(5.0, 5.0), sides=6, radius=3.0, style=drawing_style))
    group.add_component(PolygonalDrawing([(0.0, 0.0), (3.0, 0.0), (3.0, 2.0)], drawing_style))
    group.add_component(CircleDrawing((4.0, 4.0), 2.0, drawing_style))
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
    """FLOW-DOCUMENT-P1: DOCX, HTML, Markdown, and RTF escape format control characters."""
    document = FlowDocument(title="Control {Doc}")
    document.add_paragraph(_paragraph("A&B <tag> {x}\\y"))

    with zipfile.ZipFile(BytesIO(document.to_docx_bytes())) as package:
        document_xml = package.read("word/document.xml").decode("utf-8")
    html = document.to_html()
    markdown = document.to_markdown()
    rtf = document.to_rtf()

    assert "A&amp;B &lt;tag&gt; {x}\\y" in document_xml
    assert "A&amp;B &lt;tag&gt; {x}\\y" in html
    assert "# Control \\{Doc\\}" in markdown
    assert "A&B \\<tag\\> \\{x\\}\\\\y" in markdown
    assert r"Control \{Doc\}" in rtf
    assert r"A&B <tag> \{x\}\\y" in rtf


@pytest.mark.condition("FLOW-DOCUMENT-MARKDOWN-P3")
def test_flow_document_markdown_exports_ordered_blocks_with_escaped_tables_and_svg() -> None:
    """FLOW-DOCUMENT-MARKDOWN-P3: Markdown export preserves escaped flow blocks and SVG drawings."""
    table = Table(position=(0.0, 0.0))
    table.add_column(width=20.0)
    table.add_column(width=20.0)
    table.add_row(height=5.0)
    table.add_row(height=5.0)
    table.cell(0, 0).add_paragraph("Part | No.")
    table.cell(0, 1).add_paragraph("Description")
    table.cell(1, 0).add_paragraph("A-001")
    table.cell(1, 1).add_paragraph("Line one\nLine two")

    document = FlowDocument(title="A&B <Doc>")
    document.add_paragraph(_paragraph("# Step 1\nUse *care*"))
    document.add_table(table)
    document.add_drawing_group(_drawing_group())

    markdown = document.to_markdown()

    assert markdown.startswith("# A&B \\<Doc\\>\n\n\\# Step 1  \nUse \\*care\\*")
    assert "| Part \\| No\\. | Description |" in markdown
    assert "| --- | --- |" in markdown
    assert "| A\\-001 | Line one<br>Line two |" in markdown
    assert "<svg" in markdown
    assert "</svg>\n" in markdown


@pytest.mark.condition("FLOW-DOCUMENT-MARKDOWN-P3")
def test_flow_document_markdown_table_separator_is_inserted_once_after_header() -> None:
    """FLOW-DOCUMENT-MARKDOWN-P3: Markdown tables place one separator after the first row."""
    document = FlowDocument()
    table = Table(position=(0.0, 0.0))
    table.add_column(width=20.0)
    table.add_column(width=20.0)
    table.add_row(height=5.0)
    table.add_row(height=5.0)
    table.cell(0, 0).add_paragraph("PN")
    table.cell(0, 1).add_paragraph("Qty")
    table.cell(1, 0).add_paragraph("A-1")
    table.cell(1, 1).add_paragraph("2")
    document.add_table(table)

    assert document.to_markdown() == ("# InkGen Document\n\n| PN | Qty |\n| --- | --- |\n| A\\-1 | 2 |\n")


@pytest.mark.condition("FLOW-DOCUMENT-MARKDOWN-P3")
def test_flow_document_markdown_omits_zero_column_tables() -> None:
    """FLOW-DOCUMENT-MARKDOWN-P3: Markdown output omits tables with no columns."""
    document = FlowDocument()
    table = Table(position=(0.0, 0.0))
    table.add_row(height=5.0)
    document.add_table(table)

    assert document.to_markdown() == "# InkGen Document\n"


@pytest.mark.condition("FLOW-DOCUMENT-RTF-UNICODE-P2")
def test_flow_document_rtf_escapes_unicode_text() -> None:
    """FLOW-DOCUMENT-RTF-UNICODE-P2: RTF output escapes non-ASCII text."""
    document = FlowDocument(title="Résumé 🚀 \u0080")
    document.add_paragraph(_paragraph("Torque µ Ω 😀 \u8000"))

    rtf = document.to_rtf()

    assert "Résumé" not in rtf
    assert "Torque µ Ω 😀" not in rtf
    assert "\u0080" not in rtf
    assert "\u8000" not in rtf
    assert r"R\u233?sum\u233? \u-10179?\u-8576? \u128?" in rtf
    assert r"Torque \u181? \u937? \u-10179?\u-8704? \u-32768?" in rtf


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
def test_flow_document_hydrates_direct_payload_mapping() -> None:
    """FLOW-DOCUMENT-P1: Direct FlowDocument payloads remain supported."""
    document = FlowDocument(title="Direct")
    paragraph = _paragraph("Direct payload")
    document.add_paragraph(paragraph)
    payload = document.parameters["FlowDocument"]

    clone = FlowDocument.create_from_dict(payload, {paragraph.style.name: paragraph.style})

    assert clone.parameters == document.parameters
    assert clone.to_plain_text() == "Direct payload"


@pytest.mark.condition("FLOW-DOCUMENT-FILEPATH-DIRECTORY-P2")
def test_flow_document_file_writers_reject_file_parent_paths(tmp_path) -> None:
    """FLOW-DOCUMENT-FILEPATH-DIRECTORY-P2: Writer paths require a directory parent."""
    document = _flow_document_with_paragraph()
    file_parent = tmp_path / "not-a-directory"
    file_parent.write_text("occupied", encoding="utf-8")

    for writer, suffix in (
        (document.create_docx, "document.docx"),
        (document.create_html, "document.html"),
        (document.create_rtf, "document.rtf"),
        (document.create_text, "document.txt"),
    ):
        with pytest.raises(ValueError, match="file path does not exist"):
            writer(file_parent / suffix)

    assert file_parent.read_text(encoding="utf-8") == "occupied"


@pytest.mark.condition("FLOW-DOCUMENT-P1")
@pytest.mark.parametrize(
    ("payload", "exception_type", "message"),
    [
        (object(), TypeError, "flow document data must be a mapping"),
        ({"FlowDocument": object()}, TypeError, "FlowDocument payload must be a mapping"),
        ({"FlowDocument": {"title": "Bad", "blocks": "paragraph"}}, TypeError, "FlowDocument blocks must be a sequence"),
        ({"FlowDocument": {"title": "Bad", "blocks": object()}}, TypeError, "FlowDocument blocks must be a sequence"),
        ({"FlowDocument": {"title": "Bad", "paragraphs": "legacy"}}, TypeError, "FlowDocument paragraphs must be a sequence"),
        ({"FlowDocument": {"title": "Bad", "paragraphs": object()}}, TypeError, "FlowDocument paragraphs must be a sequence"),
    ],
)
def test_flow_document_hydration_rejects_malformed_root_payloads(
    payload: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """FLOW-DOCUMENT-P1: Root serialized payloads fail at the document boundary."""
    with pytest.raises(exception_type, match=message):
        FlowDocument.create_from_dict(payload)


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
@pytest.mark.parametrize(
    ("block_payload", "exception_type", "message"),
    [
        (object(), TypeError, "flow document block must be a mapping"),
        ({"payload": {}}, ValueError, "flow document block must include type and payload"),
        ({"type": "paragraph"}, ValueError, "flow document block must include type and payload"),
        ({"type": 123, "payload": {}}, TypeError, "flow document block type must be a string"),
        ({"type": "paragraph", "payload": object()}, TypeError, "flow document block payload must be a mapping"),
        ({"type": "arc", "payload": {}}, ValueError, "Unsupported flow document block type"),
        ({"type": "unsupported", "payload": {}}, ValueError, "Unsupported flow document block type"),
    ],
)
def test_flow_document_hydration_rejects_malformed_block_envelopes(
    block_payload: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """FLOW-DOCUMENT-P1: Serialized block envelopes fail at the document boundary."""
    payload = {
        "FlowDocument": {
            "title": "Malformed Blocks",
            "blocks": [block_payload],
        }
    }

    with pytest.raises(exception_type, match=message):
        FlowDocument.create_from_dict(payload)


@pytest.mark.condition("FLOW-DOCUMENT-P1")
def test_flow_document_hydration_dispatches_dynamic_block_type_strings() -> None:
    """FLOW-DOCUMENT-P1: Block dispatch uses string equality, not object identity."""
    document = FlowDocument(title="Dynamic Dispatch")
    paragraph = _paragraph("Intro")
    table = _table()
    drawing = _drawing_group()
    document.add_paragraph(paragraph)
    document.add_table(table)
    document.add_drawing_group(drawing)

    payload = document.parameters
    flow_payload = payload["FlowDocument"]
    assert isinstance(flow_payload, dict)
    blocks = flow_payload["blocks"]
    assert isinstance(blocks, list)
    for block in blocks:
        assert isinstance(block, dict)
        block_type = block["type"]
        assert isinstance(block_type, str)
        block["type"] = "".join([block_type[:-1], block_type[-1:]])

    clone = FlowDocument.create_from_dict(
        payload,
        {
            paragraph.style.name: paragraph.style,
            drawing.components[0].style.name: drawing.components[0].style,
        },
    )

    assert [block.__class__.__name__ for block in clone.blocks] == ["Paragraph", "Table", "DrawingComponentGroup"]
    assert clone.to_plain_text() == "Intro\n\nPN\tQty\n\n[Drawing: flow-drawing; RectangleDrawing]"


@pytest.mark.condition("DRAWING-GROUP-P1")
def test_flow_document_drawing_group_hydration_rejects_malformed_label() -> None:
    """DRAWING-GROUP-P1: Flow-document hydration cannot stringify drawing labels."""
    payload = {
        "FlowDocument": {
            "title": "Malformed Drawing",
            "blocks": [
                {
                    "type": "drawing",
                    "payload": {
                        "group_label": 123,
                        "components": [],
                    },
                }
            ],
        }
    }

    with pytest.raises(TypeError, match="group_label must be a string"):
        FlowDocument.create_from_dict(payload)


@pytest.mark.condition("FLOW-DOCUMENT-P1")
@pytest.mark.parametrize(
    ("drawing_payload", "exception_type", "message"),
    [
        ({"components": []}, ValueError, "flow document drawing payload must include group_label and components"),
        ({"group_label": "drawing"}, ValueError, "flow document drawing payload must include group_label and components"),
        ({"group_label": "drawing", "components": "not-components"}, TypeError, "flow document drawing components must be a sequence"),
        ({"group_label": "drawing", "components": b"not-components"}, TypeError, "flow document drawing components must be a sequence"),
        ({"group_label": "drawing", "components": object()}, TypeError, "flow document drawing components must be a sequence"),
    ],
)
def test_flow_document_hydration_rejects_malformed_drawing_payloads(
    drawing_payload: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """FLOW-DOCUMENT-P1: Drawing block payloads fail before component iteration."""
    payload = {
        "FlowDocument": {
            "title": "Malformed Drawing",
            "blocks": [
                {
                    "type": "drawing",
                    "payload": drawing_payload,
                }
            ],
        }
    }

    with pytest.raises(exception_type, match=message):
        FlowDocument.create_from_dict(payload)


@pytest.mark.condition("FLOW-DOCUMENT-P1")
@pytest.mark.parametrize(
    ("component_payload", "exception_type", "message"),
    [
        (object(), TypeError, "flow document drawing component must be a mapping"),
        ({"payload": {}}, ValueError, "flow document drawing component must include type and payload"),
        ({"type": "RectangleDrawing"}, ValueError, "flow document drawing component must include type and payload"),
        ({"type": 123, "payload": {}}, TypeError, "flow document drawing component type must be a string"),
        ({"type": "RectangleDrawing", "payload": object()}, TypeError, "flow document drawing component payload must be a mapping"),
        ({"type": "UnsupportedDrawing", "payload": {}}, ValueError, "Unsupported drawing component type"),
    ],
)
def test_flow_document_hydration_rejects_malformed_drawing_component_envelopes(
    component_payload: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """FLOW-DOCUMENT-P1: Drawing component envelopes fail at the document boundary."""
    payload = {
        "FlowDocument": {
            "title": "Malformed Component",
            "blocks": [
                {
                    "type": "drawing",
                    "payload": {
                        "group_label": "components",
                        "components": [component_payload],
                    },
                }
            ],
        }
    }

    with pytest.raises(exception_type, match=message):
        FlowDocument.create_from_dict(payload)


@pytest.mark.condition("FLOW-DOCUMENT-P1")
@pytest.mark.parametrize(
    ("style_payload", "exception_type", "message"),
    [
        (None, ValueError, "flow document drawing component payload must include style"),
        (object(), TypeError, "flow document drawing style payload must be a mapping"),
        ({}, ValueError, "flow document drawing style payload must include DrawingStyle"),
        ({"TextStyle": {"name": "wrong-kind"}}, ValueError, "flow document drawing style payload must include DrawingStyle"),
        ({"DrawingStyle": object()}, TypeError, "flow document drawing style entry must be a mapping"),
        ({"DrawingStyle": {"name": object()}}, TypeError, "flow document drawing style name must be a string"),
    ],
)
def test_flow_document_hydration_rejects_malformed_drawing_style_payloads(
    style_payload: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """FLOW-DOCUMENT-P1: Drawing style envelopes fail before style construction."""
    document = FlowDocument(title="Malformed Style")
    document.add_drawing_group(_drawing_group())
    payload = document.parameters
    flow_payload = payload["FlowDocument"]
    assert isinstance(flow_payload, dict)
    blocks = flow_payload["blocks"]
    assert isinstance(blocks, list)
    block_payload = blocks[0]["payload"]
    assert isinstance(block_payload, dict)
    components = block_payload["components"]
    assert isinstance(components, list)
    component_payload = components[0]["payload"]
    assert isinstance(component_payload, dict)
    if style_payload is None:
        component_payload.pop("style")
    else:
        component_payload["style"] = style_payload

    with pytest.raises(exception_type, match=message):
        FlowDocument.create_from_dict(payload)


@pytest.mark.condition("FLOW-DOCUMENT-P1")
def test_flow_document_hydration_rejects_mismatched_drawing_style_overrides() -> None:
    """FLOW-DOCUMENT-P1: Drawing style overrides must match the component kind."""
    drawing_document = FlowDocument(title="Bad Drawing Style Override")
    drawing = _drawing_group()
    drawing_document.add_drawing_group(drawing)
    drawing_style_name = drawing.components[0].style.name

    text_document = FlowDocument(title="Bad Text Style Override")
    text_group = DrawingComponentGroup("text-flow-drawing")
    text_group.add_component(TextDrawing("NOTE", (2.0, 3.0), _text_style()))
    text_document.add_drawing_group(text_group)
    text_style_name = text_group.components[0].style.name

    with pytest.raises(TypeError, match="must be a DrawingStyle"):
        FlowDocument.create_from_dict(drawing_document.parameters, {drawing_style_name: _text_style()})
    with pytest.raises(TypeError, match="must be a TextStyle"):
        FlowDocument.create_from_dict(text_document.parameters, {text_style_name: _drawing_style()})


@pytest.mark.condition("TEXT-DRAWING-TEXT-P2")
@pytest.mark.parametrize("text", [object(), ["NOTE"], {"text": "NOTE"}, None])
def test_flow_document_hydration_rejects_malformed_text_drawing_payloads(text: object) -> None:
    """TEXT-DRAWING-TEXT-P2: Serialized text drawings cannot hold malformed text."""
    text_style = _text_style()
    text_document = FlowDocument(title="Bad Text Payload")
    text_group = DrawingComponentGroup("text-flow-drawing")
    text_group.add_component(TextDrawing("NOTE", (2.0, 3.0), text_style))
    text_document.add_drawing_group(text_group)
    payload = text_document.parameters
    flow_payload = payload["FlowDocument"]
    assert isinstance(flow_payload, dict)
    blocks = flow_payload["blocks"]
    assert isinstance(blocks, list)
    block_payload = blocks[0]["payload"]
    assert isinstance(block_payload, dict)
    components = block_payload["components"]
    assert isinstance(components, list)
    component_payload = components[0]["payload"]
    assert isinstance(component_payload, dict)
    component_payload["text"] = text

    with pytest.raises(TypeError, match="TextDrawing text must be a string"):
        FlowDocument.create_from_dict(payload, {text_style.name: text_style})


@pytest.mark.condition("FLOW-DOCUMENT-STYLES-MAPPING-P2")
@pytest.mark.parametrize("styles", [object(), ["style-name"], "style-name", b"style-name"])
def test_flow_document_hydration_rejects_malformed_style_override_maps(styles: object) -> None:
    """FLOW-DOCUMENT-STYLES-MAPPING-P2: Style overrides must be a mapping before block hydration."""
    document = FlowDocument(title="Bad Style Map")
    drawing = DrawingComponentGroup("drawing-style-map")
    drawing.add_component(RectangleDrawing((1.0, 2.0), 3.0, 4.0, 0.0, _drawing_style()))
    document.add_drawing_group(drawing)

    with pytest.raises(TypeError, match="styles must be a mapping or None"):
        FlowDocument.create_from_dict(document.parameters, styles)  # type: ignore[arg-type]


@pytest.mark.condition("FLOW-DOCUMENT-P1")
def test_flow_document_hydration_constructs_missing_drawing_style_overrides_by_kind() -> None:
    """FLOW-DOCUMENT-P1: Drawing style fallback construction matches component kind."""
    drawing_style_name = f"raw_draw_{uuid4().hex}"
    text_style_name = f"raw_text_{uuid4().hex}"
    payload = {
        "FlowDocument": {
            "title": "Raw Styles",
            "blocks": [
                {
                    "type": "drawing",
                    "payload": {
                        "group_label": "raw-style-drawing",
                        "components": [
                            {
                                "type": "RectangleDrawing",
                                "payload": {
                                    "position": (1.0, 2.0),
                                    "width": 10.0,
                                    "height": 5.0,
                                    "corner_radii": 0.0,
                                    "style": {
                                        "DrawingStyle": {
                                            "name": drawing_style_name,
                                            "stroke": "#222222",
                                            "stroke_width": 0.2,
                                            "fill": "none",
                                            "stroke_opacity": 1.0,
                                            "fill_opacity": 1.0,
                                        }
                                    },
                                },
                            },
                            {
                                "type": "TextDrawing",
                                "payload": {
                                    "text": "NOTE",
                                    "position": (2.0, 3.0),
                                    "style": {
                                        "TextStyle": {
                                            "name": text_style_name,
                                            "color": "#000000",
                                            "superscript": False,
                                            "subscript": False,
                                            "text_align": "left",
                                            "line_spacing": 1.0,
                                            "font": Font(size=11.0).parameters,
                                        }
                                    },
                                },
                            },
                        ],
                    },
                }
            ],
        }
    }

    clone = FlowDocument.create_from_dict(payload)
    drawing = clone.blocks[0]

    assert isinstance(drawing, DrawingComponentGroup)
    assert isinstance(drawing.components[0].style, DrawingStyle)
    assert drawing.components[0].style.name == drawing_style_name
    assert isinstance(drawing.components[1].style, TextStyle)
    assert drawing.components[1].style.name == text_style_name


@pytest.mark.condition("FLOW-DOCUMENT-P1")
@pytest.mark.parametrize(
    ("commands_payload", "exception_type", "message"),
    [
        ("__missing__", ValueError, "flow document path payload must include commands"),
        ("not-commands", TypeError, "flow document path commands must be a sequence"),
        (b"not-commands", TypeError, "flow document path commands must be a sequence"),
        (object(), TypeError, "flow document path commands must be a sequence"),
        ([object()], TypeError, "flow document path command must be a mapping"),
        ([{"points": []}], ValueError, "flow document path command must include type and points"),
        ([{"type": "M"}], ValueError, "flow document path command must include type and points"),
        ([{"type": "M", "points": "not-points"}], TypeError, "flow document path command points must be a sequence"),
        ([{"type": "M", "points": object()}], TypeError, "flow document path command points must be a sequence"),
        ([{"type": "M", "points": ["12"]}], ValueError, "Points must contain two numeric values."),
        ([{"type": "M", "points": [b"12"]}], ValueError, "Points must contain two numeric values."),
        ([{"type": "M", "points": [{"x": 1.0, "y": 2.0}]}], ValueError, "Points must contain two numeric values."),
    ],
)
def test_flow_document_hydration_rejects_malformed_path_command_payloads(
    commands_payload: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """FLOW-DOCUMENT-P1: Path command envelopes fail before path construction."""
    style = _drawing_style()
    group = DrawingComponentGroup("path-flow-drawing")
    group.add_component(PathDrawing(style, [PathCommand("M", [(0.0, 0.0)])]))
    document = FlowDocument(title="Malformed Path")
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
    path_payload = components[0]["payload"]
    assert isinstance(path_payload, dict)
    if commands_payload == "__missing__":
        path_payload.pop("commands")
    else:
        path_payload["commands"] = commands_payload

    with pytest.raises(exception_type, match=message):
        FlowDocument.create_from_dict(payload, {style.name: style})


@pytest.mark.condition("FLOW-DOCUMENT-P1")
def test_flow_document_hydration_dispatches_dynamic_drawing_component_type_strings() -> None:
    """FLOW-DOCUMENT-P1: Drawing component dispatch uses string equality."""
    document = FlowDocument(title="Dynamic Component")
    drawing = _all_supported_drawing_group()
    document.add_drawing_group(drawing)
    payload = document.parameters
    flow_payload = payload["FlowDocument"]
    assert isinstance(flow_payload, dict)
    blocks = flow_payload["blocks"]
    assert isinstance(blocks, list)
    block_payload = blocks[0]["payload"]
    assert isinstance(block_payload, dict)
    components = block_payload["components"]
    assert isinstance(components, list)
    for component_payload in components:
        assert isinstance(component_payload, dict)
        component_type = component_payload["type"]
        assert isinstance(component_type, str)
        component_payload["type"] = "".join([component_type[:-1], component_type[-1:]])

    styles = {component.style.name: component.style for component in drawing.components if hasattr(component, "style")}
    clone = FlowDocument.create_from_dict(payload, styles)

    assert clone.parameters == document.parameters
    assert clone.to_plain_text() == (
        "[Drawing: all-flow-drawings; RectangleDrawing, LineDrawing, TextDrawing, "
        "ArcDrawing, QuadraticBezierDrawing, CubicBezierDrawing, PathDrawing, "
        "RegularPolygonDrawing, PolygonalDrawing, CircleDrawing]"
    )


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
        document.to_markdown()
    with pytest.raises(TypeError, match="must return an InkGen Component"):
        document.to_docx_bytes()

    group.components.clear()
    group.components.append(_AttributeOnlyDrawingPrimitive())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="must implement to_component"):
        document.to_html()
    with pytest.raises(TypeError, match="must implement to_component"):
        document.to_markdown()


@pytest.mark.condition("FLOW-DOCUMENT-DRAWING-LIVE-COMPONENTS-P2")
def test_flow_document_plain_text_revalidates_mutated_drawing_components() -> None:
    """FLOW-DOCUMENT-DRAWING-LIVE-COMPONENTS-P2: Text summaries reject mutated invalid components."""
    document = FlowDocument()
    group = DrawingComponentGroup("invalid-plain-text")
    group.components.append(object())  # type: ignore[arg-type]
    document.add_drawing_group(group)

    with pytest.raises(TypeError, match="drawing components must implement to_component"):
        document.to_plain_text()


@pytest.mark.condition("FLOW-DOCUMENT-DRAWING-LIVE-COMPONENTS-P2")
def test_flow_document_parameters_revalidate_mutated_drawing_components() -> None:
    """FLOW-DOCUMENT-DRAWING-LIVE-COMPONENTS-P2: Serialized drawings reject mutated invalid components."""
    document = FlowDocument()
    group = DrawingComponentGroup("invalid-parameters")
    document.add_drawing_group(group)

    group.components.append(object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="drawing components must implement to_component"):
        _ = document.parameters

    group.components.clear()
    group.components.append(_InvalidDrawingPrimitive())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="supported serializable drawing primitives"):
        _ = document.parameters


@pytest.mark.condition("FLOW-DOCUMENT-DRAWING-SERIALIZABLE-TYPES-P2")
def test_flow_document_parameters_rejects_supported_name_lookalike_components() -> None:
    """FLOW-DOCUMENT-DRAWING-SERIALIZABLE-TYPES-P2: Serialization requires actual neutral drawing classes."""
    document = FlowDocument()
    group = DrawingComponentGroup("lookalike-parameters")
    group.components.append(_SerializableDrawingLookalike())  # type: ignore[arg-type]
    document.add_drawing_group(group)

    with pytest.raises(TypeError, match="supported serializable drawing primitives"):
        _ = document.parameters


@pytest.mark.condition("FLOW-DOCUMENT-DRAWING-LIVE-COMPONENTS-P2")
def test_flow_document_parameters_preserve_path_drawing_commands() -> None:
    """FLOW-DOCUMENT-DRAWING-LIVE-COMPONENTS-P2: Serialized path drawings preserve commands."""
    style = _drawing_style()
    group = DrawingComponentGroup("path-parameters")
    group.add_component(PathDrawing(style, [PathCommand("M", [(1.0, 2.0)]), PathCommand("L", [(3.0, 4.0)])]))
    document = FlowDocument()
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
    component_payload = components[0]["payload"]
    assert isinstance(component_payload, dict)

    assert component_payload["commands"] == [
        {"type": "M", "points": [(1.0, 2.0)]},
        {"type": "L", "points": [(3.0, 4.0)]},
    ]
    clone = FlowDocument.create_from_dict(payload, {style.name: style})
    cloned_group = clone.blocks[0]
    assert isinstance(cloned_group, DrawingComponentGroup)
    cloned_path = cloned_group.components[0]
    assert isinstance(cloned_path, PathDrawing)
    assert [command.parameters for command in cloned_path.commands] == component_payload["commands"]


@pytest.mark.condition("FLOW-DOCUMENT-SVG-MATERIALIZATION-P2")
def test_flow_document_rejects_materializations_without_render_fragments() -> None:
    """FLOW-DOCUMENT-SVG-MATERIALIZATION-P2: Drawing outputs fail instead of silently omitting malformed fragments."""
    document = FlowDocument()
    group = DrawingComponentGroup("invalid-render-fragment")
    document.add_drawing_group(group)

    group.components.append(_BareComponentDrawingPrimitive())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"SVG materialization must provide generate_svg\(\)"):
        document.to_html()
    with pytest.raises(TypeError, match="PDF materialization must expose points"):
        document.to_docx_bytes()

    group.components.clear()
    group.components.append(_NonStringSvgDrawingPrimitive())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"generate_svg\(\) must return a string"):
        document.to_html()


@pytest.mark.condition("FLOW-DOCUMENT-DRAWING-POINTS-P2", "FLOW-DOCUMENT-DRAWINGML-P3")
def test_flow_document_accepts_valid_materialized_drawing_points() -> None:
    """FLOW-DOCUMENT-DRAWING-POINTS-P2: Valid materialized point surfaces drive HTML and DOCX geometry."""
    document = FlowDocument()
    group = DrawingComponentGroup("valid-points")
    group.components.append(_PointSurfaceDrawingPrimitive([(2.0, 3.0), (6.0, 8.0)]))  # type: ignore[arg-type]
    document.add_drawing_group(group)

    html = document.to_html()
    with zipfile.ZipFile(BytesIO(document.to_docx_bytes())) as package:
        document_xml = package.read("word/document.xml").decode("utf-8")

    assert 'viewBox="2 3 4 5"' in html
    assert "<w:pict>" not in document_xml
    assert "<wp:anchor" in document_xml
    assert "<wps:wsp>" in document_xml
    assert 'prst="line"' in document_xml
    assert '<wp:positionH relativeFrom="column"><wp:posOffset>0</wp:posOffset></wp:positionH>' in document_xml
    assert '<wp:positionV relativeFrom="paragraph"><wp:posOffset>0</wp:posOffset></wp:positionV>' in document_xml
    assert 'cx="144000" cy="180000"' in document_xml


@pytest.mark.condition("FLOW-DOCUMENT-DRAWING-POINTS-P2", "FLOW-DOCUMENT-DRAWINGML-P3")
@pytest.mark.parametrize(
    ("points", "exception_type", "message"),
    [
        (object(), TypeError, "materialized drawing points must be a sequence"),
        ("0,0", TypeError, "materialized drawing points must be a sequence"),
        (b"0,0", TypeError, "materialized drawing points must be a sequence"),
        ([object()], ValueError, "materialized drawing points must contain two coordinates"),
        ([(1.0,)], ValueError, "materialized drawing points must contain two coordinates"),
        ([(1.0, 2.0, 3.0)], ValueError, "materialized drawing points must contain two coordinates"),
        ([(float("nan"), 0.0)], ValueError, "materialized drawing point coordinates must be finite numbers"),
        ([(float("inf"), 0.0)], ValueError, "materialized drawing point coordinates must be finite numbers"),
        ([(True, 0.0)], ValueError, "materialized drawing point coordinates must be finite numbers"),
        ([("1.0", 0.0)], ValueError, "materialized drawing point coordinates must be finite numbers"),
    ],
)
def test_flow_document_rejects_malformed_materialized_drawing_points(
    points: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """FLOW-DOCUMENT-DRAWING-POINTS-P2: Materialized drawing points must be finite coordinate pairs."""
    document = FlowDocument()
    group = DrawingComponentGroup("bad-points")
    group.components.append(_PointSurfaceDrawingPrimitive(points))  # type: ignore[arg-type]
    document.add_drawing_group(group)

    with pytest.raises(exception_type, match=message):
        document.to_html()
    with pytest.raises(exception_type, match=message):
        document.to_docx_bytes()


@pytest.mark.condition("FLOW-DOCUMENT-DRAWINGML-P3")
def test_flow_document_formats_valid_circle_drawingml_and_twips() -> None:
    """FLOW-DOCUMENT-DRAWINGML-P3: Valid artifact numbers are formatted deterministically."""
    paragraph = _paragraph("Spacing")
    paragraph.space_before = 1.0
    document = FlowDocument()
    document.add_paragraph(paragraph)
    group = DrawingComponentGroup("circle-drawingml")
    group.add_component(CircleDrawing((4.0, 4.0), 2.0, _drawing_style()))
    document.add_drawing_group(group)

    with zipfile.ZipFile(BytesIO(document.to_docx_bytes())) as package:
        document_xml = package.read("word/document.xml").decode("utf-8")

    assert 'w:before="57"' in document_xml
    assert "<w:pict>" not in document_xml
    assert 'prst="ellipse"' in document_xml
    assert '<wp:positionH relativeFrom="column"><wp:posOffset>0</wp:posOffset></wp:positionH>' in document_xml
    assert '<wp:positionV relativeFrom="paragraph"><wp:posOffset>0</wp:posOffset></wp:positionV>' in document_xml
    assert 'cx="144000" cy="144000"' in document_xml

    small_document = FlowDocument()
    small_group = DrawingComponentGroup("small-circle-drawingml")
    small_group.add_component(CircleDrawing((1.0, 1.0), 0.5, _drawing_style()))
    small_document.add_drawing_group(small_group)
    with zipfile.ZipFile(BytesIO(small_document.to_docx_bytes())) as package:
        small_document_xml = package.read("word/document.xml").decode("utf-8")

    assert 'prst="ellipse"' in small_document_xml
    assert 'cx="36000" cy="36000"' in small_document_xml


@pytest.mark.condition("FLOW-DOCUMENT-DRAWINGML-P3")
def test_flow_document_artifact_number_formats_fractional_and_near_integer_values() -> None:
    """FLOW-DOCUMENT-DRAWINGML-P3: Artifact numbers preserve fractions and snap near integers."""
    assert _vml_number(1.25) == "1.25"
    assert _vml_number(2.0000000005) == "2"


@pytest.mark.condition("FLOW-DOCUMENT-DRAWINGML-P3")
@pytest.mark.parametrize(
    ("position", "radius", "exception_type", "message"),
    [
        ((True, 2.0), 1.0, TypeError, "CircleDrawing position x must be a finite number"),
        ((2.0, True), 1.0, TypeError, "CircleDrawing position y must be a finite number"),
        ("2,2", 1.0, ValueError, "CircleDrawing position must contain two finite numbers"),
        ("12", 1.0, ValueError, "CircleDrawing position must contain two finite numbers"),
        ((2.0,), 1.0, ValueError, "CircleDrawing position must contain two finite numbers"),
        ((2.0, 2.0, 2.0), 1.0, ValueError, "CircleDrawing position must contain two finite numbers"),
        ((float("nan"), 2.0), 1.0, ValueError, "CircleDrawing position x must be a finite number"),
        ((2.0, float("nan")), 1.0, ValueError, "CircleDrawing position y must be a finite number"),
        ((float("inf"), 2.0), 1.0, ValueError, "CircleDrawing position x must be a finite number"),
        ((2.0, 2.0), True, TypeError, "CircleDrawing radius must be a finite number"),
        ((2.0, 2.0), "1.0", TypeError, "CircleDrawing radius must be a finite number"),
        ((2.0, 2.0), object(), TypeError, "CircleDrawing radius must be a finite number"),
        ((2.0, 2.0), _ValueErrorFloat(), TypeError, "CircleDrawing radius must be a finite number"),
        ((2.0, 2.0), float("nan"), ValueError, "CircleDrawing radius must be a finite number"),
        ((2.0, 2.0), float("inf"), ValueError, "CircleDrawing radius must be a finite number"),
        ((2.0, 2.0), 0.0, ValueError, "CircleDrawing radius must be positive"),
        ((2.0, 2.0), -1.0, ValueError, "CircleDrawing radius must be positive"),
    ],
)
def test_flow_document_rejects_malformed_circle_drawingml_numbers(
    position: object,
    radius: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """FLOW-DOCUMENT-DRAWINGML-P3: Circle DrawingML numbers must preserve geometry contracts."""
    circle = CircleDrawing((2.0, 2.0), 1.0, _drawing_style())
    object.__setattr__(circle, "position", position)
    object.__setattr__(circle, "radius", radius)
    document = FlowDocument()
    group = DrawingComponentGroup("bad-circle-drawingml")
    group.add_component(circle)
    document.add_drawing_group(group)

    with pytest.raises(exception_type, match=message):
        document.to_html()
    with pytest.raises(exception_type, match=message):
        document.to_docx_bytes()


@pytest.mark.condition("FLOW-DOCUMENT-DRAWINGML-P3")
@pytest.mark.parametrize(
    ("space_before", "exception_type", "message"),
    [
        (True, TypeError, "twip value must be a finite number"),
        ("1.0", TypeError, "twip value must be a finite number"),
        (float("nan"), ValueError, "twip value must be a finite number"),
        (float("inf"), ValueError, "twip value must be a finite number"),
    ],
)
def test_flow_document_rejects_malformed_docx_twip_numbers(
    space_before: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """FLOW-DOCUMENT-DRAWINGML-P3: DOCX twip values reject malformed live state."""
    paragraph = _paragraph("Bad spacing")
    paragraph._space_before = space_before  # type: ignore[assignment]
    document = FlowDocument()
    document.add_paragraph(paragraph)

    with pytest.raises(exception_type, match=message):
        document.to_docx_bytes()


@pytest.mark.condition("FLOW-DOCUMENT-DRAWINGML-P3")
def test_flow_document_docx_drawingml_line_uses_group_relative_points() -> None:
    """FLOW-DOCUMENT-DRAWINGML-P3: DOCX DrawingML linework is relative to drawing bounds."""
    document = FlowDocument()
    group = DrawingComponentGroup("linework")
    group.add_component(LineDrawing((2.0, 3.0), (5.0, 7.0), _drawing_style()))
    document.add_drawing_group(group)

    with zipfile.ZipFile(BytesIO(document.to_docx_bytes())) as package:
        document_xml = package.read("word/document.xml").decode("utf-8")

    assert "<w:pict>" not in document_xml
    assert "<wp:anchor" in document_xml
    assert "<wps:wsp>" in document_xml
    assert 'prst="line"' in document_xml
    assert '<wp:positionH relativeFrom="column"><wp:posOffset>0</wp:posOffset></wp:positionH>' in document_xml
    assert '<wp:positionV relativeFrom="paragraph"><wp:posOffset>0</wp:posOffset></wp:positionV>' in document_xml
    assert 'cx="108000" cy="144000"' in document_xml


@pytest.mark.condition("FLOW-DOCUMENT-DRAWINGML-P3")
def test_flow_document_docx_drawingml_preserves_style_text_and_line_flips() -> None:
    """FLOW-DOCUMENT-DRAWINGML-P3: DOCX DrawingML keeps style, text, and reversed line direction."""
    drawing_style = DrawingStyle(
        f"drawingml_style_{uuid4().hex}",
        stroke="#445566",
        stroke_width=0.5,
        fill="#112233",
        stroke_opacity=0.5,
        fill_opacity=0.25,
    )
    text_style = TextStyle(f"drawingml_text_{uuid4().hex}", Font(size=12.0))
    text_style.color = "#abcdef"
    document = FlowDocument()
    group = DrawingComponentGroup("styled-drawingml")
    group.add_component(RectangleDrawing((1.0, 1.0), 2.0, 3.0, 0.0, drawing_style))
    group.add_component(TextDrawing("A&B", (4.0, 5.0), text_style))
    group.add_component(LineDrawing((10.0, 10.0), (2.0, 1.0), drawing_style))
    document.add_drawing_group(group)

    with zipfile.ZipFile(BytesIO(document.to_docx_bytes())) as package:
        document_xml = package.read("word/document.xml").decode("utf-8")

    assert '<a:srgbClr val="112233"><a:alpha val="25000"/></a:srgbClr>' in document_xml
    assert '<a:ln w="18000"><a:solidFill><a:srgbClr val="445566"><a:alpha val="50000"/></a:srgbClr>' in document_xml
    assert 'flipH="1" flipV="1"' in document_xml
    assert "A&amp;B" in document_xml
    assert '<w:color w:val="ABCDEF"/>' in document_xml
    assert '<w:sz w:val="24"/>' in document_xml


@pytest.mark.condition("FLOW-DOCUMENT-DRAWINGML-P3")
def test_flow_document_docx_drawingml_allows_empty_materialized_point_sequences() -> None:
    """FLOW-DOCUMENT-DRAWINGML-P3: Empty materialized point surfaces emit no shape."""
    document = FlowDocument()
    group = DrawingComponentGroup("empty-points")
    group.components.append(_PointSurfaceDrawingPrimitive([]))  # type: ignore[arg-type]
    document.add_drawing_group(group)

    with zipfile.ZipFile(BytesIO(document.to_docx_bytes())) as package:
        document_xml = package.read("word/document.xml").decode("utf-8")

    assert "<wp:anchor" not in document_xml
    assert "<w:pict>" not in document_xml


@pytest.mark.condition("FLOW-DOCUMENT-DRAWINGML-P3")
def test_flow_document_docx_drawingml_rejects_negative_shape_extents() -> None:
    """FLOW-DOCUMENT-DRAWINGML-P3: DrawingML extent helpers reject negative values."""
    assert _nonnegative_artifact_number(0.0, name="RectangleDrawing width") == 0.0
    assert _nonnegative_artifact_number(0.5, name="RectangleDrawing width") == 0.5
    with pytest.raises(ValueError, match="RectangleDrawing width must be nonnegative"):
        _nonnegative_artifact_number(-0.01, name="RectangleDrawing width")


@pytest.mark.condition("FLOW-DOCUMENT-DRAWINGML-P3")
def test_flow_document_docx_drawingml_helper_fragments_cover_branches() -> None:
    """FLOW-DOCUMENT-DRAWINGML-P3: DrawingML helper fragments preserve branch contracts."""
    style = DrawingStyle(
        f"drawingml_helper_{uuid4().hex}",
        stroke="#112233",
        stroke_width=0.5,
        fill="#445566",
        stroke_opacity=0.75,
        fill_opacity=0.25,
    )
    no_paint = DrawingStyle(f"drawingml_none_{uuid4().hex}", stroke="none", stroke_width=0.0, fill="none")
    no_stroke_with_width = DrawingStyle(f"drawingml_no_stroke_{uuid4().hex}", stroke="none", stroke_width=0.5, fill="none")
    zero_width_stroke = DrawingStyle(f"drawingml_zero_stroke_{uuid4().hex}", stroke="#112233", stroke_width=0.0, fill="none")
    fractional_alpha = DrawingStyle(
        f"drawingml_alpha_{uuid4().hex}",
        stroke="#112233",
        fill="#445566",
        fill_opacity=0.50001,
    )
    stroke_alpha = DrawingStyle(f"drawingml_stroke_alpha_{uuid4().hex}", stroke="#112233", stroke_opacity=0.50001)
    text_style = TextStyle(f"drawingml_helper_text_{uuid4().hex}", Font(size=12.0))
    text_style.color = "#abcdef"
    small_text_style = TextStyle(f"drawingml_small_text_{uuid4().hex}", Font(size=3.75))
    large_text_style = TextStyle(f"drawingml_large_text_{uuid4().hex}", Font(size=25.491))

    assert _drawingml_fill(None) == "<a:noFill/>"
    assert _drawingml_fill(no_paint) == "<a:noFill/>"
    assert '<a:srgbClr val="445566"><a:alpha val="25000"/></a:srgbClr>' in _drawingml_fill(style)
    assert '<a:srgbClr val="445566"><a:alpha val="50001"/></a:srgbClr>' in _drawingml_fill(fractional_alpha)
    assert _drawingml_line(no_paint) == "<a:ln><a:noFill/></a:ln>"
    assert _drawingml_line(no_stroke_with_width) == "<a:ln><a:noFill/></a:ln>"
    assert _drawingml_line(zero_width_stroke) == "<a:ln><a:noFill/></a:ln>"
    assert '<a:ln w="18000">' in _drawingml_line(style)
    assert '<a:alpha val="75000"/>' in _drawingml_line(style)
    assert '<a:alpha val="50001"/>' in _drawingml_line(stroke_alpha)
    assert '<w:sz w:val="24"/>' in _drawingml_text_body("Sized", text_style)
    assert '<w:sz w:val="8"/>' in _drawingml_text_body("Small", small_text_style)
    assert '<w:sz w:val="51"/>' in _drawingml_text_body("Large", large_text_style)
    assert '<w:sz w:val="20"/>' in _drawingml_text_body("Default", None)
    assert '<w:sz w:val="20"/>' in _drawingml_text_body("Fallback", type("StyleWithoutFont", (), {"color": "#000000"})())
    assert "<w:t>Sized</w:t>" in _drawingml_text_body("Sized", text_style)
    assert _drawingml_text_body(None, None) == "<wps:bodyPr/>"


@pytest.mark.condition("FLOW-DOCUMENT-DRAWINGML-P3")
def test_flow_document_docx_drawingml_component_helpers_preserve_offsets_and_extents() -> None:
    """FLOW-DOCUMENT-DRAWINGML-P3: Component helpers keep exact offsets, extents, and flips."""
    media_registry = _DocxMediaRegistry()
    style = DrawingStyle(f"drawingml_component_{uuid4().hex}", stroke="#112233", fill="#445566", stroke_width=0.5)
    text_style = TextStyle(f"drawingml_component_text_{uuid4().hex}", Font(size=12.0))

    zero_rect = _component_drawingml(RectangleDrawing((5.0, 7.0), 0.0, 0.0, 0.0, style), 5.0, 7.0, media_registry)
    assert 'cx="360" cy="360"' in zero_rect
    assert 'flipH="1"' not in zero_rect
    assert 'flipV="1"' not in zero_rect

    circle = _component_drawingml(CircleDrawing((5.0, 6.0), 2.0, style), 1.0, 1.0, media_registry)
    assert '<wp:positionH relativeFrom="column"><wp:posOffset>72000</wp:posOffset></wp:positionH>' in circle
    assert '<wp:positionV relativeFrom="paragraph"><wp:posOffset>108000</wp:posOffset></wp:positionV>' in circle
    assert 'cx="144000" cy="144000"' in circle

    text = _component_drawingml(TextDrawing("Placed", (4.0, 5.0), text_style), 1.0, 2.0, media_registry)
    assert '<wp:positionH relativeFrom="column"><wp:posOffset>108000</wp:posOffset></wp:positionH>' in text
    assert '<wp:positionV relativeFrom="paragraph"><wp:posOffset>108000</wp:posOffset></wp:positionV>' in text
    assert 'cx="2880000" cy="360000"' in text
    assert '<w:sz w:val="24"/>' in text

    forward = "".join(_drawingml_segments_docx([(0.0, 0.0), (2.0, 0.0)], 0.0, 0.0, style, media_registry))
    assert 'flipH="1"' not in forward
    assert 'flipV="1"' not in forward
    assert 'cx="72000" cy="360"' in forward

    offset_forward = "".join(_drawingml_segments_docx([(1.0, 1.0), (3.0, 1.0)], 0.0, 0.0, style, media_registry))
    assert '<wp:positionH relativeFrom="column"><wp:posOffset>36000</wp:posOffset></wp:positionH>' in offset_forward
    assert '<wp:positionV relativeFrom="paragraph"><wp:posOffset>36000</wp:posOffset></wp:positionV>' in offset_forward
    assert 'cx="72000" cy="360"' in offset_forward

    vertical = "".join(_drawingml_segments_docx([(1.0, 1.0), (1.0, 3.0)], 1.0, 1.0, style, media_registry))
    assert 'flipH="1"' not in vertical
    assert 'flipV="1"' not in vertical
    assert 'cx="360" cy="72000"' in vertical

    offset_vertical = "".join(_drawingml_segments_docx([(1.0, 1.0), (1.0, 3.0)], 0.0, 0.0, style, media_registry))
    assert '<wp:positionH relativeFrom="column"><wp:posOffset>36000</wp:posOffset></wp:positionH>' in offset_vertical
    assert '<wp:positionV relativeFrom="paragraph"><wp:posOffset>36000</wp:posOffset></wp:positionV>' in offset_vertical
    assert 'cx="360" cy="72000"' in offset_vertical

    default_style_line = "".join(_drawingml_segments_docx([(0.0, 0.0), (0.0, 2.0)], 0.0, 0.0, object(), media_registry))
    assert '<a:ln w="7200">' in default_style_line


@pytest.mark.condition("FLOW-DOCUMENT-DRAWINGML-P3")
def test_flow_document_docx_drawingml_shape_helper_preserves_explicit_flip_flags() -> None:
    """FLOW-DOCUMENT-DRAWINGML-P3: Shape helper emits only requested flip flags."""
    media_registry = _DocxMediaRegistry()

    no_flip = _drawingml_shape_docx(x=0.0, y=0.0, width=1.0, height=1.0, preset="rect", style=None, media_registry=media_registry)
    horizontal = _drawingml_shape_docx(
        x=0.0,
        y=0.0,
        width=1.0,
        height=1.0,
        preset="line",
        style=None,
        media_registry=media_registry,
        flip_horizontal=True,
    )
    vertical = _drawingml_shape_docx(
        x=0.0,
        y=0.0,
        width=1.0,
        height=1.0,
        preset="line",
        style=None,
        media_registry=media_registry,
        flip_vertical=True,
    )

    assert 'flipH="1"' not in no_flip
    assert 'flipV="1"' not in no_flip
    assert 'flipH="1"' in horizontal
    assert 'flipV="1"' not in horizontal
    assert 'flipH="1"' not in vertical
    assert 'flipV="1"' in vertical


@pytest.mark.condition("FLOW-DOCUMENT-DRAWINGML-P3")
def test_flow_document_docx_drawingml_markup_is_well_formed() -> None:
    """FLOW-DOCUMENT-DRAWINGML-P3: DOCX DrawingML emits parseable XML."""
    document = FlowDocument()
    group = _all_supported_drawing_group()
    document.add_drawing_group(group)

    with zipfile.ZipFile(BytesIO(document.to_docx_bytes())) as package:
        document_xml = package.read("word/document.xml")
        relationships_xml = package.read("word/_rels/document.xml.rels")

    ElementTree.fromstring(document_xml)
    ElementTree.fromstring(relationships_xml)


@pytest.mark.condition("FLOW-DOCUMENT-P1")
def test_flow_document_text_writers_create_requested_files(tmp_path) -> None:
    """FLOW-DOCUMENT-P1: HTML, Markdown, RTF, and text writers persist generated payloads."""
    document = FlowDocument(title="Files")
    document.add_paragraph(_paragraph("Persisted"))
    html_path = tmp_path / "document.html"
    markdown_path = tmp_path / "document.md"
    rtf_path = tmp_path / "document.rtf"
    text_path = tmp_path / "document.txt"

    document.create_html(str(html_path))
    document.create_markdown(str(markdown_path))
    document.create_rtf(str(rtf_path))
    document.create_text(str(text_path))

    assert html_path.read_text(encoding="utf-8") == document.to_html()
    assert markdown_path.read_text(encoding="utf-8") == document.to_markdown()
    assert rtf_path.read_text(encoding="utf-8") == document.to_rtf()
    assert text_path.read_text(encoding="utf-8") == "Persisted"


@pytest.mark.condition("FLOW-DOCUMENT-P1")
def test_flow_document_file_writers_accept_pathlike_outputs(tmp_path) -> None:
    """FLOW-DOCUMENT-P1: File writers accept path-like output locations."""
    document = FlowDocument(title="Pathlike")
    document.add_paragraph(_paragraph("Persisted"))
    docx_path = tmp_path / "document.docx"
    html_path = tmp_path / "document.html"
    markdown_path = tmp_path / "document.md"
    rtf_path = tmp_path / "document.rtf"
    text_path = tmp_path / "document.txt"

    document.create_docx(docx_path)
    document.create_html(html_path)
    document.create_markdown(markdown_path)
    document.create_rtf(rtf_path)
    document.create_text(text_path)

    assert docx_path.read_bytes() == document.to_docx_bytes()
    assert html_path.read_text(encoding="utf-8") == document.to_html()
    assert markdown_path.read_text(encoding="utf-8") == document.to_markdown()
    assert rtf_path.read_text(encoding="utf-8") == document.to_rtf()
    assert text_path.read_text(encoding="utf-8") == "Persisted"


@pytest.mark.condition("FLOW-DOCUMENT-P1")
@pytest.mark.parametrize(
    ("filepath", "exception_type", "message"),
    [
        (object(), TypeError, "file path must be a string or path-like object"),
        (123, TypeError, "file path must be a string or path-like object"),
        (b"document.html", TypeError, "file path must be a string or path-like object"),
        ("", ValueError, "file path must not be empty"),
    ],
)
def test_flow_document_file_writers_reject_malformed_paths(
    filepath: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """FLOW-DOCUMENT-P1: File writers reject malformed paths at the boundary."""
    document = FlowDocument(title="Bad Paths")
    document.add_paragraph(_paragraph("Persisted"))
    writers = (
        document.create_docx,
        document.create_html,
        document.create_markdown,
        document.create_rtf,
        document.create_text,
    )

    for writer in writers:
        with pytest.raises(exception_type, match=message):
            writer(filepath)  # type: ignore[arg-type]
