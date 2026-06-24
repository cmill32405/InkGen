"""Behavioral tests for flow-document output contracts."""

from __future__ import annotations

import zipfile
from io import BytesIO
from uuid import uuid4

import pytest

from InkGen.component import PathCommand
from InkGen.document_outputs import DOCX_FIXED_TIMESTAMP, FlowDocument
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
def test_flow_document_hydrates_direct_payload_mapping() -> None:
    """FLOW-DOCUMENT-P1: Direct FlowDocument payloads remain supported."""
    document = FlowDocument(title="Direct")
    paragraph = _paragraph("Direct payload")
    document.add_paragraph(paragraph)
    payload = document.parameters["FlowDocument"]

    clone = FlowDocument.create_from_dict(payload, {paragraph.style.name: paragraph.style})

    assert clone.parameters == document.parameters
    assert clone.to_plain_text() == "Direct payload"


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


@pytest.mark.condition("FLOW-DOCUMENT-P1")
def test_flow_document_file_writers_accept_pathlike_outputs(tmp_path) -> None:
    """FLOW-DOCUMENT-P1: File writers accept path-like output locations."""
    document = FlowDocument(title="Pathlike")
    document.add_paragraph(_paragraph("Persisted"))
    docx_path = tmp_path / "document.docx"
    html_path = tmp_path / "document.html"
    rtf_path = tmp_path / "document.rtf"
    text_path = tmp_path / "document.txt"

    document.create_docx(docx_path)
    document.create_html(html_path)
    document.create_rtf(rtf_path)
    document.create_text(text_path)

    assert docx_path.read_bytes() == document.to_docx_bytes()
    assert html_path.read_text(encoding="utf-8") == document.to_html()
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
        document.create_rtf,
        document.create_text,
    )

    for writer in writers:
        with pytest.raises(exception_type, match=message):
            writer(filepath)  # type: ignore[arg-type]
