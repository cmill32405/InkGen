"""Dependency-free document-output backends for paragraph-based content."""

from __future__ import annotations

import os
import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from html import escape as html_escape
from io import BytesIO
from math import isfinite
from xml.sax.saxutils import escape as xml_escape

from InkGen.component import Component, PathCommand
from InkGen.drawing_components import (
    ArcDrawing,
    CircleDrawing,
    CubicBezierDrawing,
    DrawingComponentGroup,
    ImageDrawing,
    LineDrawing,
    OutputFormat,
    PathDrawing,
    PolygonalDrawing,
    QuadraticBezierDrawing,
    RectangleDrawing,
    RegularPolygonDrawing,
    TextDrawing,
)
from InkGen.image_assets import RasterImageAsset
from InkGen.paragraph import LineSpacingRule, Paragraph, ParagraphAlignment
from InkGen.style import DrawingStyle, TextStyle
from InkGen.table import Table

DOCX_FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
DRAWING_COMPONENT_CONSTRUCTORS = {
    "ArcDrawing": ArcDrawing,
    "CircleDrawing": CircleDrawing,
    "CubicBezierDrawing": CubicBezierDrawing,
    "LineDrawing": LineDrawing,
    "PolygonalDrawing": PolygonalDrawing,
    "QuadraticBezierDrawing": QuadraticBezierDrawing,
    "RectangleDrawing": RectangleDrawing,
    "RegularPolygonDrawing": RegularPolygonDrawing,
    "TextDrawing": TextDrawing,
    "ImageDrawing": ImageDrawing,
}
DRAWING_COMPONENT_TYPES = frozenset((*DRAWING_COMPONENT_CONSTRUCTORS, "PathDrawing"))
DRAWING_COMPONENT_TYPE_NAMES = {
    **{component_class: component_name for component_name, component_class in DRAWING_COMPONENT_CONSTRUCTORS.items()},
    PathDrawing: "PathDrawing",
}
TEXT_DRAWING_COMPONENT_TYPES = frozenset({"TextDrawing"})
DOCX_IMAGE_RELATIONSHIP_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
DOCX_PICTURE_URI = "http://schemas.openxmlformats.org/drawingml/2006/picture"
EMU_PER_MM = 36000
DOCX_NATIVE_IMAGE_TYPES = {
    "BMP": ("bmp", "image/bmp"),
    "GIF": ("gif", "image/gif"),
    "JPEG": ("jpg", "image/jpeg"),
    "JPG": ("jpg", "image/jpeg"),
    "PNG": ("png", "image/png"),
    "TIFF": ("tif", "image/tiff"),
    "TIF": ("tif", "image/tiff"),
}


@dataclass(frozen=True)
class _DocxMediaPart:
    """Image media part registered for a DOCX package."""

    relationship_id: str
    target: str
    package_name: str
    data: bytes
    content_type: str


class _DocxMediaRegistry:
    """Deterministic registry for native DOCX media parts."""

    def __init__(self) -> None:
        self._part_by_digest: dict[str, _DocxMediaPart] = {}
        self._drawing_id = 0

    def register_image(self, image: RasterImageAsset) -> _DocxMediaPart:
        """Register a native or normalized DOCX media part and return its relationship."""
        data, extension, content_type = _docx_media_payload(image)
        digest = sha256(data + content_type.encode("ascii")).hexdigest()
        if digest not in self._part_by_digest:
            index = len(self._part_by_digest) + 1
            target = f"media/image{index}.{extension}"
            self._part_by_digest[digest] = _DocxMediaPart(
                relationship_id=f"rId{index}",
                target=target,
                package_name=f"word/{target}",
                data=data,
                content_type=content_type,
            )
        return self._part_by_digest[digest]

    def parts(self) -> tuple[_DocxMediaPart, ...]:
        """Return registered media parts in deterministic insertion order."""
        return tuple(self._part_by_digest.values())

    def next_drawing_id(self) -> int:
        """Return a unique DrawingML object id for the package."""
        self._drawing_id += 1
        return self._drawing_id


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
        self.title = _normalize_title(title)
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
    def create_from_dict(cls, data: object, styles: dict[str, object] | None = None) -> FlowDocument:
        """Recreate a flow document from serialized parameters."""
        styles = _normalize_style_overrides(styles)
        payload = _flow_document_payload(data)
        document = cls(title=_normalize_title(payload.get("title")))
        for block_payload in _payload_sequence(payload, "blocks"):
            document._blocks.append(_block_from_parameters(block_payload, styles))
        for paragraph_payload in _payload_sequence(payload, "paragraphs"):
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
        media_registry = _DocxMediaRegistry()
        document_xml = self._docx_document_xml(media_registry)
        styles_xml = self._docx_styles_xml()
        content_types = self._docx_content_types_xml(media_registry)
        package_relationships = self._docx_package_relationships_xml()
        document_relationships = self._docx_document_relationships_xml(media_registry)

        buffer = BytesIO()
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as package:
            _write_docx_part(package, "[Content_Types].xml", content_types)
            _write_docx_part(package, "_rels/.rels", package_relationships)
            _write_docx_part(package, "word/document.xml", document_xml)
            _write_docx_part(package, "word/styles.xml", styles_xml)
            _write_docx_part(package, "word/_rels/document.xml.rels", document_relationships)
            for part in media_registry.parts():
                _write_docx_binary_part(package, part.package_name, part.data)
        return buffer.getvalue()

    def create_docx(self, filepath: str | os.PathLike[str]) -> None:
        """Write a DOCX file."""
        _write_bytes(filepath, self.to_docx_bytes())

    def create_html(self, filepath: str | os.PathLike[str]) -> None:
        """Write an HTML file."""
        _write_text(filepath, self.to_html())

    def create_rtf(self, filepath: str | os.PathLike[str]) -> None:
        """Write an RTF file."""
        _write_text(filepath, self.to_rtf())

    def create_text(self, filepath: str | os.PathLike[str]) -> None:
        """Write a plain-text file."""
        _write_text(filepath, self.to_plain_text())

    def _docx_document_xml(self, media_registry: _DocxMediaRegistry) -> str:
        blocks = "\n".join(self._block_docx(block, media_registry) for block in self._blocks)
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
            'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
            'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture" '
            'xmlns:v="urn:schemas-microsoft-com:vml">\n'
            "<w:body>\n"
            f"{blocks}\n"
            '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr>\n'
            "</w:body>\n"
            "</w:document>\n"
        )

    def _block_docx(self, block: Paragraph | Table | DrawingComponentGroup, media_registry: _DocxMediaRegistry) -> str:
        if isinstance(block, Paragraph):
            return self._paragraph_docx(block)
        if isinstance(block, Table):
            return self._table_docx(block)
        return self._drawing_docx(block, media_registry)

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

    def _drawing_docx(self, group: DrawingComponentGroup, media_registry: _DocxMediaRegistry) -> str:
        min_x, min_y, max_x, max_y = _drawing_bounds(group)
        width = max(max_x - min_x, 1.0)
        height = max(max_y - min_y, 1.0)
        shapes = []
        image_paragraphs = []
        for component in group.components:
            if isinstance(component, ImageDrawing):
                image_paragraphs.append(_image_drawing_docx(component, media_registry))
            else:
                shapes.append(_component_vml(component, min_x, min_y))
        drawing_parts = []
        if shapes:
            drawing_parts.append(
                "<w:p><w:r><w:pict>"
                f'<v:group coordorigin="0 0" coordsize="{_vml_number(width)} {_vml_number(height)}" '
                f'style="width:{_vml_number(width)}mm;height:{_vml_number(height)}mm">'
                + "".join(shapes)
                + "</v:group></w:pict></w:r></w:p>"
            )
        drawing_parts.extend(image_paragraphs)
        return "".join(drawing_parts)

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
    def _docx_content_types_xml(media_registry: _DocxMediaRegistry) -> str:
        media_defaults = "".join(
            f'<Default Extension="{extension}" ContentType="{content_type}"/>\n'
            for extension, content_type in _docx_media_defaults(media_registry.parts())
        )
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
            '<Default Extension="xml" ContentType="application/xml"/>\n'
            f"{media_defaults}"
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
    def _docx_document_relationships_xml(media_registry: _DocxMediaRegistry) -> str:
        relationships = "".join(
            f'<Relationship Id="{part.relationship_id}" Type="{DOCX_IMAGE_RELATIONSHIP_TYPE}" Target="{part.target}"/>\n'
            for part in media_registry.parts()
        )
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
            f"{relationships}"
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


def _normalize_title(value: object) -> str:
    """Normalize a flow-document title without stringifying malformed data."""
    if value is None:
        return "InkGen Document"
    if not isinstance(value, str):
        raise TypeError("title must be a string or None")
    if not value:
        return "InkGen Document"
    return value


def _flow_document_payload(data: object) -> Mapping[str, object]:
    if not isinstance(data, Mapping):
        raise TypeError("flow document data must be a mapping")
    payload = data["FlowDocument"] if "FlowDocument" in data else data
    if not isinstance(payload, Mapping):
        raise TypeError("FlowDocument payload must be a mapping")
    return payload


def _payload_sequence(payload: Mapping[str, object], name: str) -> Sequence[object]:
    value = payload.get(name, [])
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"FlowDocument {name} must be a sequence")
    return value


def _normalize_style_overrides(styles: object) -> Mapping[str, object]:
    """Normalize serialized style overrides without accepting sequence lookups."""
    if styles is None:
        return {}
    if not isinstance(styles, Mapping):
        raise TypeError("styles must be a mapping or None")
    return styles


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


def _block_from_parameters(data: object, styles: dict[str, object] | None) -> Paragraph | Table | DrawingComponentGroup:
    if not isinstance(data, Mapping):
        raise TypeError("flow document block must be a mapping")
    if "type" not in data or "payload" not in data:
        raise ValueError("flow document block must include type and payload")
    block_type = data["type"]
    payload = data["payload"]
    if not isinstance(block_type, str):
        raise TypeError("flow document block type must be a string")
    if not isinstance(payload, Mapping):
        raise TypeError("flow document block payload must be a mapping")
    payload = dict(payload)
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
    for component in group.components:
        _validate_drawing_component_boundary(component)
    names = ", ".join(component.__class__.__name__ for component in group.components)
    return f"[Drawing: {group.group_label}; {names}]"


def _drawing_html(group: DrawingComponentGroup) -> str:
    min_x, min_y, max_x, max_y = _drawing_bounds(group)
    width = max(max_x - min_x, 1.0)
    height = max(max_y - min_y, 1.0)
    payload = []
    for component in group.components:
        payload.append(_svg_fragment(component))
    return (
        f'<svg width="{_vml_number(width)}mm" height="{_vml_number(height)}mm" '
        f'viewBox="{_vml_number(min_x)} {_vml_number(min_y)} {_vml_number(width)} {_vml_number(height)}">' + "".join(payload) + "</svg>"
    )


def _drawing_bounds(group: DrawingComponentGroup) -> tuple[float, float, float, float]:
    points: list[tuple[float, float]] = []
    for component in group.components:
        if isinstance(component, CircleDrawing):
            x, y = _artifact_point_pair(component.position, name="CircleDrawing position")
            radius = _positive_artifact_number(component.radius, name="CircleDrawing radius")
            points.extend([(x - radius, y - radius), (x + radius, y + radius)])
            continue
        concrete = _materialize_drawing_component(component, OutputFormat.PDF)
        points.extend(_materialized_points(concrete, allow_missing=True))
    if not points:
        return 0.0, 0.0, 1.0, 1.0
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def _component_vml(component: object, min_x: float, min_y: float) -> str:
    if isinstance(component, CircleDrawing):
        center_x, center_y = _artifact_point_pair(component.position, name="CircleDrawing position")
        radius = _positive_artifact_number(component.radius, name="CircleDrawing radius")
        x = center_x - radius - min_x
        y = center_y - radius - min_y
        diameter = radius * 2.0
        return (
            f'<v:oval style="position:absolute;left:{_vml_number(x)}mm;top:{_vml_number(y)}mm;'
            f'width:{_vml_number(diameter)}mm;height:{_vml_number(diameter)}mm"/>'
        )
    if isinstance(component, TextDrawing):
        position_x, position_y = _artifact_point_pair(component.position, name="TextDrawing position")
        x = position_x - min_x
        y = position_y - min_y
        return (
            f'<v:shape style="position:absolute;left:{_vml_number(x)}mm;top:{_vml_number(y)}mm;'
            f'width:80mm;height:10mm"><v:textbox><w:txbxContent><w:p><w:r><w:t>{xml_escape(component.text)}</w:t></w:r></w:p>'
            "</w:txbxContent></v:textbox></v:shape>"
        )
    concrete = _materialize_drawing_component(component, OutputFormat.PDF)
    points = _materialized_points(concrete, allow_missing=False)
    if not points:
        return ""
    point_text = " ".join(f"{_vml_number(point[0] - min_x)},{_vml_number(point[1] - min_y)}" for point in points)
    return f'<v:polyline points="{point_text}"/>'


def _image_drawing_docx(component: ImageDrawing, media_registry: _DocxMediaRegistry) -> str:
    """Return native DrawingML for a DOCX image drawing."""
    part = media_registry.register_image(component.image)
    width = _positive_artifact_number(component.width, name="ImageDrawing width")
    height = _positive_artifact_number(component.height, name="ImageDrawing height")
    width_emu = _mm_to_emu(width)
    height_emu = _mm_to_emu(height)
    doc_id = media_registry.next_drawing_id()
    name = xml_escape(f"Picture {doc_id}")
    return (
        "<w:p><w:r><w:drawing>"
        '<wp:inline distT="0" distB="0" distL="0" distR="0">'
        f'<wp:extent cx="{width_emu}" cy="{height_emu}"/>'
        f'<wp:docPr id="{doc_id}" name="{name}"/>'
        '<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
        "<a:graphic>"
        f'<a:graphicData uri="{DOCX_PICTURE_URI}">'
        "<pic:pic>"
        "<pic:nvPicPr>"
        f'<pic:cNvPr id="{doc_id}" name="{name}"/>'
        "<pic:cNvPicPr/>"
        "</pic:nvPicPr>"
        f'<pic:blipFill><a:blip r:embed="{part.relationship_id}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        "<pic:spPr>"
        f'<a:xfrm><a:off x="0" y="0"/><a:ext cx="{width_emu}" cy="{height_emu}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
        "</pic:spPr>"
        "</pic:pic>"
        "</a:graphicData>"
        "</a:graphic>"
        "</wp:inline>"
        "</w:drawing></w:r></w:p>"
    )


def _docx_media_payload(image: RasterImageAsset) -> tuple[bytes, str, str]:
    """Return media bytes, extension, and content type for DOCX image packaging."""
    native = DOCX_NATIVE_IMAGE_TYPES.get(image.format)
    if native is not None and image.orientation == 1 and _docx_native_preserves_alpha(image):
        extension, content_type = native
        return image.data, extension, content_type
    return image.png_bytes(), "png", "image/png"


def _docx_native_preserves_alpha(image: RasterImageAsset) -> bool:
    """Return whether native DOCX media can preserve this asset's alpha safely."""
    if not image.has_alpha:
        return True
    return image.format == "PNG"


def _docx_media_defaults(parts: tuple[_DocxMediaPart, ...]) -> tuple[tuple[str, str], ...]:
    """Return deterministic extension/content-type defaults for registered media."""
    defaults: dict[str, str] = {}
    for part in parts:
        extension = part.target.rsplit(".", maxsplit=1)[-1]
        defaults[extension] = part.content_type
    return tuple(sorted(defaults.items()))


def _materialized_points(component: object, *, allow_missing: bool) -> list[tuple[float, float]]:
    points = getattr(component, "points", None)
    if points is None:
        if allow_missing:
            return []
        raise TypeError("PDF materialization must expose points for DOCX drawing output")
    if isinstance(points, (str, bytes)) or not isinstance(points, Sequence):
        raise TypeError("materialized drawing points must be a sequence")
    return [_materialized_point(point) for point in points]


def _materialized_point(point: object) -> tuple[float, float]:
    if isinstance(point, (str, bytes)) or not isinstance(point, Sequence) or len(point) != 2:
        raise ValueError("materialized drawing points must contain two coordinates")
    return (
        _materialized_coordinate(point[0]),
        _materialized_coordinate(point[1]),
    )


def _materialized_coordinate(value: object) -> float:
    if isinstance(value, (bool, str, bytes)):
        raise ValueError("materialized drawing point coordinates must be finite numbers")
    try:
        coordinate = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("materialized drawing point coordinates must be finite numbers") from exc
    if not isfinite(coordinate):
        raise ValueError("materialized drawing point coordinates must be finite numbers")
    return coordinate


def _drawing_parameters(group: DrawingComponentGroup) -> dict[str, object]:
    return {
        "group_label": group.group_label,
        "components": [_drawing_component_parameters(component) for component in group.components],
    }


def _drawing_from_parameters(data: object, styles: dict[str, object] | None) -> DrawingComponentGroup:
    if not isinstance(data, Mapping):
        raise TypeError("flow document drawing payload must be a mapping")
    if "group_label" not in data or "components" not in data:
        raise ValueError("flow document drawing payload must include group_label and components")
    components = data["components"]
    if isinstance(components, (str, bytes)) or not isinstance(components, Sequence):
        raise TypeError("flow document drawing components must be a sequence")
    group = DrawingComponentGroup(data["group_label"])
    for component_data in components:
        group.add_component(_drawing_component_from_parameters(component_data, styles))
    return group


def _drawing_component_parameters(component: object) -> dict[str, object]:
    _validate_drawing_component_boundary(component)
    component_type = DRAWING_COMPONENT_TYPE_NAMES.get(type(component))
    if component_type is None:
        raise TypeError("flow document drawing components must be supported serializable drawing primitives")
    payload = dict(component.__dict__)
    style = payload.pop("style", None)
    if style is not None:
        payload["style"] = style.parameters
    if isinstance(component, PathDrawing):
        payload["commands"] = [command.parameters for command in component.commands or []]
    if isinstance(component, ImageDrawing):
        payload["image"] = component.image.parameters
    return {"type": component_type, "payload": payload}


def _validate_drawing_component_boundary(component: object) -> None:
    if not callable(getattr(component, "to_component", None)):
        raise TypeError("drawing components must implement to_component(output_format)")


def _drawing_component_from_parameters(data: object, styles: dict[str, object] | None) -> object:
    if not isinstance(data, Mapping):
        raise TypeError("flow document drawing component must be a mapping")
    if "type" not in data or "payload" not in data:
        raise ValueError("flow document drawing component must include type and payload")
    component_type = data["type"]
    if not isinstance(component_type, str):
        raise TypeError("flow document drawing component type must be a string")
    if component_type not in DRAWING_COMPONENT_TYPES:
        raise ValueError(f"Unsupported drawing component type: {component_type}")
    if not isinstance(data["payload"], Mapping):
        raise TypeError("flow document drawing component payload must be a mapping")
    payload = dict(data["payload"])
    if component_type == "ImageDrawing":
        if "image" not in payload:
            raise ValueError("flow document image drawing payload must include image")
        image = RasterImageAsset.create_from_dict(payload.pop("image"))
        return ImageDrawing(image=image, **payload)
    if "style" not in payload:
        raise ValueError("flow document drawing component payload must include style")
    style = _style_from_payload(payload.pop("style"), styles, text=component_type in TEXT_DRAWING_COMPONENT_TYPES)
    if component_type == "PathDrawing":
        return PathDrawing(style=style, commands=_path_commands_from_payload(payload))
    return DRAWING_COMPONENT_CONSTRUCTORS[component_type](style=style, **payload)


def _path_commands_from_payload(payload: Mapping[str, object]) -> list[PathCommand]:
    if "commands" not in payload:
        raise ValueError("flow document path payload must include commands")
    commands = payload["commands"]
    if isinstance(commands, (str, bytes)) or not isinstance(commands, Sequence):
        raise TypeError("flow document path commands must be a sequence")
    path_commands = []
    for command in commands:
        if not isinstance(command, Mapping):
            raise TypeError("flow document path command must be a mapping")
        if "type" not in command or "points" not in command:
            raise ValueError("flow document path command must include type and points")
        points = command["points"]
        if isinstance(points, (str, bytes)) or not isinstance(points, Sequence):
            raise TypeError("flow document path command points must be a sequence")
        path_commands.append(PathCommand(command["type"], points))
    return path_commands


def _style_from_payload(payload: object, styles: dict[str, object] | None, *, text: bool) -> DrawingStyle | TextStyle:
    if not isinstance(payload, Mapping):
        raise TypeError("flow document drawing style payload must be a mapping")
    styles = _normalize_style_overrides(styles)
    style_key = "TextStyle" if text else "DrawingStyle"
    expected_style_type = TextStyle if text else DrawingStyle
    if style_key not in payload:
        raise ValueError(f"flow document drawing style payload must include {style_key}")
    style_data = payload[style_key]
    if not isinstance(style_data, Mapping):
        raise TypeError("flow document drawing style entry must be a mapping")
    style_name = style_data.get("name")
    if not isinstance(style_name, str):
        raise TypeError("flow document drawing style name must be a string")
    if style_name in styles:
        style = styles[style_name]
        if not isinstance(style, expected_style_type):
            raise TypeError(f"style override for {style_name!r} must be a {expected_style_type.__name__}")
        return style
    return TextStyle.create_from_dict(payload) if text else DrawingStyle.create_from_dict(payload)


def _vml_number(value: float) -> str:
    numeric = _artifact_number(value, name="VML number")
    return f"{numeric:.3f}".rstrip("0").rstrip(".")


def _artifact_point_pair(value: object, *, name: str) -> tuple[float, float]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or len(value) != 2:
        raise ValueError(f"{name} must contain two finite numbers")
    return (
        _artifact_number(value[0], name=f"{name} x"),
        _artifact_number(value[1], name=f"{name} y"),
    )


def _artifact_number(value: object, *, name: str) -> float:
    if isinstance(value, (bool, str, bytes)):
        raise TypeError(f"{name} must be a finite number")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a finite number") from exc
    if not isfinite(numeric):
        raise ValueError(f"{name} must be a finite number")
    return numeric


def _positive_artifact_number(value: object, *, name: str) -> float:
    numeric = _artifact_number(value, name=name)
    if numeric <= 0.0:
        raise ValueError(f"{name} must be positive")
    return numeric


def _svg_fragment(component: object) -> str:
    """Materialize a neutral drawing primitive into an SVG fragment."""
    svg_component = _materialize_drawing_component(component, OutputFormat.SVG)
    generate_svg = getattr(svg_component, "generate_svg", None)
    if not callable(generate_svg):
        raise TypeError("SVG materialization must provide generate_svg()")
    fragment = generate_svg()
    if not isinstance(fragment, str):
        raise TypeError("generate_svg() must return a string")
    return fragment


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


def _write_docx_binary_part(package: zipfile.ZipFile, name: str, payload: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=DOCX_FIXED_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    package.writestr(info, payload)


def _mm_to_twips(value: float) -> int:
    return int(round(_artifact_number(value, name="twip value") * 1440.0 / 25.4))


def _mm_to_emu(value: float) -> int:
    return int(round(_artifact_number(value, name="EMU value") * EMU_PER_MM))


def _rtf_escape(value: str) -> str:
    parts = []
    for character in value:
        if character == "\\":
            parts.append(r"\\")
        elif character == "{":
            parts.append(r"\{")
        elif character == "}":
            parts.append(r"\}")
        elif ord(character) < 128:
            parts.append(character)
        else:
            encoded = character.encode("utf-16-le")
            for index in range(0, len(encoded), 2):
                code_unit = int.from_bytes(encoded[index : index + 2], "little")
                signed_code_unit = code_unit if code_unit < 0x8000 else code_unit - 0x10000
                parts.append(rf"\u{signed_code_unit}?")
    return "".join(parts)


def _normalize_output_filepath(filepath: object) -> str:
    try:
        path_value = os.fspath(filepath)
    except TypeError as exc:
        raise TypeError("file path must be a string or path-like object") from exc
    if not isinstance(path_value, str):
        raise TypeError("file path must be a string or path-like object")
    if not path_value:
        raise ValueError("file path must not be empty")
    path = os.path.abspath(path_value)
    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        raise ValueError("The file path does not exist.")
    return path


def _write_text(filepath: str | os.PathLike[str], payload: str) -> None:
    path = _normalize_output_filepath(filepath)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(payload)


def _write_bytes(filepath: str | os.PathLike[str], payload: bytes) -> None:
    path = _normalize_output_filepath(filepath)
    with open(path, "wb") as handle:
        handle.write(payload)
