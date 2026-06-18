"""Dependency-free document-output backends for paragraph-based content."""

from __future__ import annotations

import os
import zipfile
from enum import Enum
from html import escape as html_escape
from io import BytesIO
from xml.sax.saxutils import escape as xml_escape

from InkGen.component import Component, PathCommand
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
from InkGen.paragraph import LineSpacingRule, Paragraph, ParagraphAlignment
from InkGen.style import DrawingStyle, TextStyle
from InkGen.table import Table

DOCX_FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


class DocumentOutputFormat(str, Enum):
    """Supported flow-document output formats."""

    DOCX = "docx"
    HTML = "html"
    RTF = "rtf"
    TEXT = "txt"


class FlowDocument:
    """Paragraph-based document that exports to common word-processing formats."""

    def __init__(self, *, title: str | None = None) -> None:
        """Create an empty flow document."""
        self.title = title or "InkGen Document"
        self._blocks: list[Paragraph | Table | DrawingComponentGroup] = []

    @property
    def paragraphs(self) -> tuple[Paragraph, ...]:
        """Paragraphs in document order."""
        return tuple(block for block in self._blocks if isinstance(block, Paragraph))

    @property
    def blocks(self) -> tuple[Paragraph | Table | DrawingComponentGroup, ...]:
        """All flow-document blocks in document order."""
        return tuple(self._blocks)

    def add_paragraph(self, paragraph: Paragraph) -> None:
        """Append a paragraph to the document."""
        if not isinstance(paragraph, Paragraph):
            raise TypeError("paragraph must be a Paragraph")
        self._blocks.append(paragraph)

    def add_table(self, table: Table) -> None:
        """Append a table to the document."""
        if not isinstance(table, Table):
            raise TypeError("table must be a Table")
        self._blocks.append(table)

    def add_drawing_group(self, group: DrawingComponentGroup) -> None:
        """Append a drawing group to the document."""
        if not isinstance(group, DrawingComponentGroup):
            raise TypeError("group must be a DrawingComponentGroup")
        self._blocks.append(group)

    @property
    def parameters(self) -> dict[str, object]:
        """Return serialization parameters for this flow document."""
        return {
            "FlowDocument": {
                "title": self.title,
                "blocks": [_block_parameters(block) for block in self._blocks],
            }
        }

    @classmethod
    def create_from_dict(cls, data: dict[str, object], styles: dict[str, object] | None = None) -> FlowDocument:
        """Recreate a flow document from serialized parameters."""
        payload = data["FlowDocument"] if "FlowDocument" in data else data
        document = cls(title=str(payload.get("title", "InkGen Document")))
        for block_payload in payload.get("blocks", []):
            document._blocks.append(_block_from_parameters(block_payload, styles))
        for paragraph_payload in payload.get("paragraphs", []):
            document.add_paragraph(Paragraph.create_from_dict(paragraph_payload, styles))
        return document

    def to_plain_text(self) -> str:
        """Serialize document text as plain text."""
        return "\n\n".join(_block_plain_text(block) for block in self._blocks)

    def to_html(self) -> str:
        """Serialize the document as standalone HTML."""
        body = [f"<h1>{html_escape(self.title)}</h1>"] if self.title else []
        for block in self._blocks:
            body.append(self._block_html(block))
        return (
            "<!doctype html>\n"
            "<html>\n"
            '<head><meta charset="utf-8"><title>'
            f"{html_escape(self.title)}</title></head>\n"
            "<body>\n" + "\n".join(body) + "\n</body>\n</html>\n"
        )

    def to_rtf(self) -> str:
        """Serialize the document as basic RTF."""
        chunks = [r"{\rtf1\ansi\deff0", r"{\fonttbl{\f0 Arial;}}"]
        if self.title:
            chunks.append(r"\b " + _rtf_escape(self.title) + r"\b0\par")
        for block in self._blocks:
            chunks.append(self._block_rtf(block))
        chunks.append("}")
        return "\n".join(chunks)

    def to_docx_bytes(self) -> bytes:
        """Serialize the document as a minimal DOCX package."""
        document_xml = self._docx_document_xml()
        styles_xml = self._docx_styles_xml()
        content_types = self._docx_content_types_xml()
        package_relationships = self._docx_package_relationships_xml()
        document_relationships = self._docx_document_relationships_xml()

        buffer = BytesIO()
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as package:
            _write_docx_part(package, "[Content_Types].xml", content_types)
            _write_docx_part(package, "_rels/.rels", package_relationships)
            _write_docx_part(package, "word/document.xml", document_xml)
            _write_docx_part(package, "word/styles.xml", styles_xml)
            _write_docx_part(package, "word/_rels/document.xml.rels", document_relationships)
        return buffer.getvalue()

    def create_docx(self, filepath: str) -> None:
        """Write a DOCX file."""
        _write_bytes(filepath, self.to_docx_bytes())

    def create_html(self, filepath: str) -> None:
        """Write an HTML file."""
        _write_text(filepath, self.to_html())

    def create_rtf(self, filepath: str) -> None:
        """Write an RTF file."""
        _write_text(filepath, self.to_rtf())

    def create_text(self, filepath: str) -> None:
        """Write a plain-text file."""
        _write_text(filepath, self.to_plain_text())

    def _docx_document_xml(self) -> str:
        blocks = "\n".join(self._block_docx(block) for block in self._blocks)
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
            'xmlns:v="urn:schemas-microsoft-com:vml">\n'
            "<w:body>\n"
            f"{blocks}\n"
            '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr>\n'
            "</w:body>\n"
            "</w:document>\n"
        )

    def _block_docx(self, block: Paragraph | Table | DrawingComponentGroup) -> str:
        if isinstance(block, Paragraph):
            return self._paragraph_docx(block)
        if isinstance(block, Table):
            return self._table_docx(block)
        return self._drawing_docx(block)

    def _block_html(self, block: Paragraph | Table | DrawingComponentGroup) -> str:
        if isinstance(block, Paragraph):
            style = self._paragraph_css(block)
            return f'<p style="{style}">{html_escape(block.text).replace(chr(10), "<br>")}</p>'
        if isinstance(block, Table):
            return _table_html(block)
        return _drawing_html(block)

    def _block_rtf(self, block: Paragraph | Table | DrawingComponentGroup) -> str:
        if isinstance(block, Paragraph):
            return self._paragraph_rtf(block)
        if isinstance(block, Table):
            return _table_plain_text(block).replace("\n", r"\par ") + r"\par"
        return _drawing_plain_text(block) + r"\par"

    def _paragraph_docx(self, paragraph: Paragraph) -> str:
        run_properties = self._run_properties_docx(paragraph)
        lines = []
        split_lines = paragraph.text.splitlines() or [""]
        for index, line in enumerate(split_lines):
            if index:
                lines.append("<w:br/>")
            lines.append(f'<w:t xml:space="preserve">{xml_escape(line)}</w:t>')
        return f"<w:p>{self._paragraph_properties_docx(paragraph)}<w:r>{run_properties}{''.join(lines)}</w:r></w:p>"

    def _table_docx(self, table: Table) -> str:
        rows = []
        for row_index in range(table.row_count):
            cells = []
            for column_index in range(table.column_count):
                cell = table.cell(row_index, column_index)
                text = xml_escape(cell.text)
                width = _mm_to_twips(table.columns[column_index].width)
                cells.append(f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/></w:tcPr><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:tc>')
            rows.append("<w:tr>" + "".join(cells) + "</w:tr>")
        return '<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/></w:tblPr>' + "".join(rows) + "</w:tbl>"

    def _drawing_docx(self, group: DrawingComponentGroup) -> str:
        min_x, min_y, max_x, max_y = _drawing_bounds(group)
        width = max(max_x - min_x, 1.0)
        height = max(max_y - min_y, 1.0)
        shapes = []
        for component in group.components:
            shapes.append(_component_vml(component, min_x, min_y))
        return (
            "<w:p><w:r><w:pict>"
            f'<v:group coordorigin="0 0" coordsize="{_vml_number(width)} {_vml_number(height)}" '
            f'style="width:{_vml_number(width)}mm;height:{_vml_number(height)}mm">' + "".join(shapes) + "</v:group></w:pict></w:r></w:p>"
        )

    def _paragraph_properties_docx(self, paragraph: Paragraph) -> str:
        alignment = "both" if paragraph.alignment is ParagraphAlignment.JUSTIFY else paragraph.alignment.value
        spacing_attrs = [
            f'w:before="{_mm_to_twips(paragraph.space_before)}"',
            f'w:after="{_mm_to_twips(paragraph.space_after)}"',
        ]
        line_value, line_rule = _docx_line_spacing(paragraph)
        spacing_attrs.append(f'w:line="{line_value}"')
        spacing_attrs.append(f'w:lineRule="{line_rule}"')
        indent_attrs = [
            f'w:left="{_mm_to_twips(paragraph.left_indent)}"',
            f'w:right="{_mm_to_twips(paragraph.right_indent)}"',
        ]
        if paragraph.first_line_indent:
            indent_attrs.append(f'w:firstLine="{_mm_to_twips(paragraph.first_line_indent)}"')
        if paragraph.hanging_indent:
            indent_attrs.append(f'w:hanging="{_mm_to_twips(paragraph.hanging_indent)}"')
        flags = []
        if paragraph.keep_together:
            flags.append("<w:keepLines/>")
        if paragraph.keep_with_next:
            flags.append("<w:keepNext/>")
        if paragraph.page_break_before:
            flags.append("<w:pageBreakBefore/>")
        if not paragraph.widow_control:
            flags.append('<w:widowControl w:val="0"/>')
        return (
            "<w:pPr>"
            f'<w:jc w:val="{alignment}"/>'
            f"<w:spacing {' '.join(spacing_attrs)}/>"
            f"<w:ind {' '.join(indent_attrs)}/>"
            f'<w:outlineLvl w:val="{paragraph.outline_level}"/>' + "".join(flags) + "</w:pPr>"
        )

    def _run_properties_docx(self, paragraph: Paragraph) -> str:
        style = paragraph.style
        size_half_points = int(round(float(style.font.size) * 2.0))
        color = getattr(style, "color", "#000000").lstrip("#")
        parts = [f'<w:color w:val="{color}"/>', f'<w:sz w:val="{size_half_points}"/>']
        if str(style.font.weight).lower() in {"bold", "heavy", "black"}:
            parts.append("<w:b/>")
        if str(style.font.style).lower() in {"italic", "oblique"}:
            parts.append("<w:i/>")
        return "<w:rPr>" + "".join(parts) + "</w:rPr>"

    def _paragraph_css(self, paragraph: Paragraph) -> str:
        alignment = "justify" if paragraph.alignment is ParagraphAlignment.JUSTIFY else paragraph.alignment.value
        line_height = paragraph._line_height()
        return "; ".join(
            [
                f"text-align: {alignment}",
                f"margin-top: {paragraph.space_before}mm",
                f"margin-bottom: {paragraph.space_after}mm",
                f"margin-left: {paragraph.left_indent}mm",
                f"margin-right: {paragraph.right_indent}mm",
                f"text-indent: {paragraph.first_line_indent - paragraph.hanging_indent}mm",
                f"line-height: {line_height}mm",
                f"font-size: {paragraph.style.font.size}pt",
                f"color: {paragraph.style.color}",
            ]
        )

    def _paragraph_rtf(self, paragraph: Paragraph) -> str:
        alignment = {
            ParagraphAlignment.LEFT: r"\ql",
            ParagraphAlignment.CENTER: r"\qc",
            ParagraphAlignment.RIGHT: r"\qr",
            ParagraphAlignment.JUSTIFY: r"\qj",
        }[paragraph.alignment]
        attrs = [
            alignment,
            rf"\li{_mm_to_twips(paragraph.left_indent)}",
            rf"\ri{_mm_to_twips(paragraph.right_indent)}",
            rf"\fi{_mm_to_twips(paragraph.first_line_indent - paragraph.hanging_indent)}",
            rf"\sb{_mm_to_twips(paragraph.space_before)}",
            rf"\sa{_mm_to_twips(paragraph.space_after)}",
            rf"\fs{int(round(float(paragraph.style.font.size) * 2.0))}",
        ]
        return " ".join(attrs) + " " + _rtf_escape(paragraph.text).replace("\n", r"\line ") + r"\par"

    @staticmethod
    def _docx_content_types_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
            '<Default Extension="xml" ContentType="application/xml"/>\n'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>\n'
            '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>\n'
            "</Types>\n"
        )

    @staticmethod
    def _docx_package_relationships_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>\n'
            "</Relationships>\n"
        )

    @staticmethod
    def _docx_document_relationships_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
            "</Relationships>\n"
        )

    @staticmethod
    def _docx_styles_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">\n'
            '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>\n'
            "</w:styles>\n"
        )


def _docx_line_spacing(paragraph: Paragraph) -> tuple[int, str]:
    if paragraph.line_spacing_rule is LineSpacingRule.SINGLE:
        return 240, "auto"
    if paragraph.line_spacing_rule is LineSpacingRule.ONE_AND_HALF:
        return 360, "auto"
    if paragraph.line_spacing_rule is LineSpacingRule.DOUBLE:
        return 480, "auto"
    if paragraph.line_spacing_rule is LineSpacingRule.MULTIPLE:
        return int(round(paragraph.line_spacing * 240)), "auto"
    if paragraph.line_spacing_rule is LineSpacingRule.EXACTLY:
        return _mm_to_twips(paragraph.line_spacing), "exact"
    return _mm_to_twips(paragraph.line_spacing), "atLeast"


def _block_parameters(block: Paragraph | Table | DrawingComponentGroup) -> dict[str, object]:
    if isinstance(block, Paragraph):
        return {"type": "paragraph", "payload": block.parameters}
    if isinstance(block, Table):
        return {"type": "table", "payload": block.parameters}
    return {"type": "drawing", "payload": _drawing_parameters(block)}


def _block_from_parameters(data: dict[str, object], styles: dict[str, object] | None) -> Paragraph | Table | DrawingComponentGroup:
    block_type = data["type"]
    payload = data["payload"]
    if block_type == "paragraph":
        return Paragraph.create_from_dict(payload, styles)
    if block_type == "table":
        return Table.create_from_dict(payload)
    if block_type == "drawing":
        return _drawing_from_parameters(payload, styles)
    raise ValueError(f"Unsupported flow document block type: {block_type}")


def _block_plain_text(block: Paragraph | Table | DrawingComponentGroup) -> str:
    if isinstance(block, Paragraph):
        return block.text
    if isinstance(block, Table):
        return _table_plain_text(block)
    return _drawing_plain_text(block)


def _table_plain_text(table: Table) -> str:
    rows = []
    for row_index in range(table.row_count):
        values = [table.cell(row_index, column_index).text for column_index in range(table.column_count)]
        rows.append("\t".join(values))
    return "\n".join(rows)


def _table_html(table: Table) -> str:
    rows = []
    for row_index in range(table.row_count):
        cells = []
        for column_index in range(table.column_count):
            cell = table.cell(row_index, column_index)
            cells.append(f"<td>{html_escape(cell.text).replace(chr(10), '<br>')}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return "<table>" + "".join(rows) + "</table>"


def _drawing_plain_text(group: DrawingComponentGroup) -> str:
    names = ", ".join(component.__class__.__name__ for component in group.components)
    return f"[Drawing: {group.group_label}; {names}]"


def _drawing_html(group: DrawingComponentGroup) -> str:
    min_x, min_y, max_x, max_y = _drawing_bounds(group)
    width = max(max_x - min_x, 1.0)
    height = max(max_y - min_y, 1.0)
    payload = []
    for component in group.components:
        svg_component = _materialize_drawing_component(component, OutputFormat.SVG)
        generate_svg = getattr(svg_component, "generate_svg", None)
        if generate_svg is not None:
            payload.append(generate_svg())
    return (
        f'<svg width="{_vml_number(width)}mm" height="{_vml_number(height)}mm" '
        f'viewBox="{_vml_number(min_x)} {_vml_number(min_y)} {_vml_number(width)} {_vml_number(height)}">' + "".join(payload) + "</svg>"
    )


def _drawing_bounds(group: DrawingComponentGroup) -> tuple[float, float, float, float]:
    points: list[tuple[float, float]] = []
    for component in group.components:
        if isinstance(component, CircleDrawing):
            x, y = component.position
            radius = component.radius
            points.extend([(x - radius, y - radius), (x + radius, y + radius)])
            continue
        concrete = _materialize_drawing_component(component, OutputFormat.PDF)
        points.extend(getattr(concrete, "points", []))
    if not points:
        return 0.0, 0.0, 1.0, 1.0
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def _component_vml(component: object, min_x: float, min_y: float) -> str:
    if isinstance(component, CircleDrawing):
        x = component.position[0] - component.radius - min_x
        y = component.position[1] - component.radius - min_y
        diameter = component.radius * 2.0
        return (
            f'<v:oval style="position:absolute;left:{_vml_number(x)}mm;top:{_vml_number(y)}mm;'
            f'width:{_vml_number(diameter)}mm;height:{_vml_number(diameter)}mm"/>'
        )
    if isinstance(component, TextDrawing):
        x = component.position[0] - min_x
        y = component.position[1] - min_y
        return (
            f'<v:shape style="position:absolute;left:{_vml_number(x)}mm;top:{_vml_number(y)}mm;'
            f'width:80mm;height:10mm"><v:textbox><w:txbxContent><w:p><w:r><w:t>{xml_escape(component.text)}</w:t></w:r></w:p>'
            "</w:txbxContent></v:textbox></v:shape>"
        )
    concrete = _materialize_drawing_component(component, OutputFormat.PDF)
    points = getattr(concrete, "points", [])
    if not points:
        return ""
    point_text = " ".join(f"{_vml_number(point[0] - min_x)},{_vml_number(point[1] - min_y)}" for point in points)
    return f'<v:polyline points="{point_text}"/>'


def _drawing_parameters(group: DrawingComponentGroup) -> dict[str, object]:
    return {
        "group_label": group.group_label,
        "components": [_drawing_component_parameters(component) for component in group.components],
    }


def _drawing_from_parameters(data: dict[str, object], styles: dict[str, object] | None) -> DrawingComponentGroup:
    group = DrawingComponentGroup(str(data["group_label"]))
    for component_data in data.get("components", []):
        group.add_component(_drawing_component_from_parameters(component_data, styles))
    return group


def _drawing_component_parameters(component: object) -> dict[str, object]:
    payload = dict(component.__dict__)
    style = payload.pop("style", None)
    if style is not None:
        payload["style"] = style.parameters
    if isinstance(component, TextDrawing):
        payload["style"] = component.style.parameters
    if isinstance(component, PathDrawing):
        payload["commands"] = [command.parameters for command in component.commands or []]
    return {"type": component.__class__.__name__, "payload": payload}


def _drawing_component_from_parameters(data: dict[str, object], styles: dict[str, object] | None) -> object:
    component_type = data["type"]
    payload = dict(data["payload"])
    style = _style_from_payload(payload.pop("style"), styles, text=component_type == "TextDrawing")
    if component_type == "RectangleDrawing":
        return RectangleDrawing(style=style, **payload)
    if component_type == "LineDrawing":
        return LineDrawing(style=style, **payload)
    if component_type == "TextDrawing":
        return TextDrawing(style=style, **payload)
    if component_type == "ArcDrawing":
        return ArcDrawing(style=style, **payload)
    if component_type == "QuadraticBezierDrawing":
        return QuadraticBezierDrawing(style=style, **payload)
    if component_type == "CubicBezierDrawing":
        return CubicBezierDrawing(style=style, **payload)
    if component_type == "PathDrawing":
        commands = [PathCommand(command["type"], command.get("points", [])) for command in payload.get("commands", [])]
        return PathDrawing(style=style, commands=commands)
    if component_type == "RegularPolygonDrawing":
        return RegularPolygonDrawing(style=style, **payload)
    if component_type == "PolygonalDrawing":
        return PolygonalDrawing(style=style, **payload)
    if component_type == "CircleDrawing":
        return CircleDrawing(style=style, **payload)
    raise ValueError(f"Unsupported drawing component type: {component_type}")


def _style_from_payload(payload: dict[str, object], styles: dict[str, object] | None, *, text: bool) -> DrawingStyle | TextStyle:
    styles = styles or {}
    style_key = "TextStyle" if text else "DrawingStyle"
    style_name = payload[style_key]["name"]
    if style_name in styles:
        return styles[style_name]
    return TextStyle.create_from_dict(payload) if text else DrawingStyle.create_from_dict(payload)


def _vml_number(value: float) -> str:
    numeric = float(value)
    if abs(numeric - round(numeric)) < 1e-9:
        return str(int(round(numeric)))
    return f"{numeric:.3f}".rstrip("0").rstrip(".")


def _materialize_drawing_component(component: object, output_format: OutputFormat) -> Component:
    materializer = getattr(component, "to_component", None)
    if not callable(materializer):
        raise TypeError("drawing components must implement to_component(output_format)")
    concrete = materializer(output_format)
    if not isinstance(concrete, Component):
        raise TypeError("to_component(output_format) must return an InkGen Component")
    return concrete


def _write_docx_part(package: zipfile.ZipFile, name: str, payload: str) -> None:
    info = zipfile.ZipInfo(name, date_time=DOCX_FIXED_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    package.writestr(info, payload)


def _mm_to_twips(value: float) -> int:
    return int(round(float(value) * 1440.0 / 25.4))


def _rtf_escape(value: str) -> str:
    return value.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")


def _write_text(filepath: str, payload: str) -> None:
    path = os.path.abspath(filepath)
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        raise ValueError("The file path does not exist.")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(payload)


def _write_bytes(filepath: str, payload: bytes) -> None:
    path = os.path.abspath(filepath)
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        raise ValueError("The file path does not exist.")
    with open(path, "wb") as handle:
        handle.write(payload)
