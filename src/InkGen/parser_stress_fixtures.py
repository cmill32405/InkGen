"""Parser-facing PDF fixture builders for Document Intelligence stress tests."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from InkGen.boundary import Canvas
from InkGen.extraction_truth import annotate_extraction_truth
from InkGen.grammar_truth import annotate_grammar_truth
from InkGen.pdf_generator import ComponentGroupPDF, DocumentPDF, LinePDF, RectanglePDF, TextPDF
from InkGen.style import DrawingStyle, Font, Style, TextStyle


@dataclass(frozen=True)
class ParserStressBOMRow:
    """One deterministic BOM row for a parser stress PDF fixture."""

    item: str
    part_number: str
    description: str
    quantity: str

    def __post_init__(self) -> None:
        """Validate the BOM row fields at the fixture boundary."""
        for field_name, value in (
            ("item", self.item),
            ("part_number", self.part_number),
            ("description", self.description),
            ("quantity", self.quantity),
        ):
            _require_non_empty_string(value, field_name)


@dataclass(frozen=True)
class ParserStressFixtureSpec:
    """Configuration for a deterministic technical-drawing parser stress PDF."""

    drawing_number: str = "PSF-0001"
    revision: str = "A"
    title: str = "PARSER STRESS FIXTURE"
    page_rotation: int | None = 90
    page_label: str = "PSF-"
    style_namespace: str = "parser_stress_pdf"
    bom_rows: Sequence[ParserStressBOMRow] = field(default_factory=lambda: DEFAULT_PARSER_STRESS_BOM_ROWS)
    include_transparency: bool = True

    def __post_init__(self) -> None:
        """Validate and normalize the fixture spec."""
        for field_name, value in (
            ("drawing_number", self.drawing_number),
            ("revision", self.revision),
            ("title", self.title),
            ("page_label", self.page_label),
            ("style_namespace", self.style_namespace),
        ):
            _require_non_empty_string(value, field_name)
        if not isinstance(self.include_transparency, bool):
            raise TypeError("include_transparency must be a bool.")
        if self.page_rotation is not None:
            object.__setattr__(self, "page_rotation", _coerce_fixture_page_rotation(self.page_rotation))
        rows = tuple(self.bom_rows)
        if not rows:
            raise ValueError("bom_rows must contain at least one row.")
        if not all(isinstance(row, ParserStressBOMRow) for row in rows):
            raise TypeError("bom_rows must contain ParserStressBOMRow instances.")
        object.__setattr__(self, "bom_rows", rows)


@dataclass(frozen=True)
class _FixtureStyles:
    outline: DrawingStyle
    grid: DrawingStyle
    shaded: DrawingStyle
    transparent: DrawingStyle
    title_text: TextStyle
    body_text: TextStyle
    small_text: TextStyle


def build_parser_stress_pdf(spec: ParserStressFixtureSpec | None = None) -> DocumentPDF:
    """Build a deterministic parser-facing PDF with truth labels and stress cues."""
    if spec is None:
        spec = ParserStressFixtureSpec()
    if not isinstance(spec, ParserStressFixtureSpec):
        raise TypeError("spec must be a ParserStressFixtureSpec or None.")

    canvas = Canvas(340.0, 200.0)
    document = DocumentPDF(canvas)
    document.add_page()
    document.set_page_label(1, spec.page_label)
    document.set_page_box(1, "TrimBox", (0.0, 0.0, canvas.width, canvas.height))
    if spec.page_rotation is not None:
        document.set_page_rotation(1, spec.page_rotation)

    annotate_grammar_truth(
        document,
        "PARSER-STRESS-DOCUMENT",
        "assessment",
        value={"fixture_family": "technical_drawing", "known_fixture": True},
        source_channel="metadata",
        instance_id=spec.drawing_number,
    )

    styles = _fixture_styles(spec.style_namespace)
    layer = document.page(1).layer("base")
    layer.add_component_group(_title_block_group(spec, styles))
    layer.add_component_group(_bom_group(spec, styles))
    if spec.include_transparency:
        layer.add_component_group(_transparent_overlay_group(styles))
    layer.add_component_group(_zone_marker_group(styles))
    return document


def _fixture_styles(namespace: str) -> _FixtureStyles:
    outline = DrawingStyle(_unique_style_name(namespace, "outline"), stroke="#111111", stroke_width=0.35, fill="none")
    grid = DrawingStyle(_unique_style_name(namespace, "grid"), stroke="#555555", stroke_width=0.18, fill="none")
    shaded = DrawingStyle(_unique_style_name(namespace, "shaded"), stroke="#111111", stroke_width=0.25, fill="#eeeeee")
    transparent = DrawingStyle(
        _unique_style_name(namespace, "transparent"),
        stroke="#006699",
        stroke_width=0.2,
        fill="#66ccff",
        fill_opacity=0.35,
    )
    title_font = Font(family="sans-serif", weight="bold", size=9.0)
    body_font = Font(family="sans-serif", size=6.5)
    small_font = Font(family="monospace", size=5.5)
    title_text = TextStyle(_unique_style_name(namespace, "title_text"), title_font)
    body_text = TextStyle(_unique_style_name(namespace, "body_text"), body_font)
    small_text = TextStyle(_unique_style_name(namespace, "small_text"), small_font)
    return _FixtureStyles(outline, grid, shaded, transparent, title_text, body_text, small_text)


def _title_block_group(spec: ParserStressFixtureSpec, styles: _FixtureStyles) -> ComponentGroupPDF:
    group = ComponentGroupPDF("title_block")
    group.add_component(RectanglePDF((155.0, 146.0), 110.0, 38.0, 0.0, styles.outline))
    group.add_component(RectanglePDF((155.0, 146.0), 110.0, 9.0, 0.0, styles.shaded))
    _add_labeled_text(group, "DRAWING TITLE", (158.0, 152.0), styles.small_text, "title_block_header", "label")
    _add_labeled_text(group, spec.title, (158.0, 164.0), styles.title_text, "drawing_title", "value")
    _add_labeled_text(group, "DWG NO.", (158.0, 176.0), styles.small_text, "drawing_number_label", "label")
    _add_labeled_text(group, spec.drawing_number, (181.0, 176.0), styles.body_text, "drawing_number", "value")
    _add_labeled_text(group, "REV", (230.0, 176.0), styles.small_text, "revision_label", "label")
    _add_labeled_text(group, spec.revision, (246.0, 176.0), styles.body_text, "revision", "value")
    annotate_extraction_truth(group, "title_block", spec.drawing_number, role="region", instance_id=spec.drawing_number)
    annotate_grammar_truth(group, "TITLE-BLOCK", "construct", value="technical_drawing_title_block", instance_id=spec.drawing_number)
    return group


def _bom_group(spec: ParserStressFixtureSpec, styles: _FixtureStyles) -> ComponentGroupPDF:
    group = ComponentGroupPDF("bom_table")
    x = 18.0
    y = 24.0
    row_height = 10.0
    column_widths = (18.0, 48.0, 115.0, 20.0)
    table_width = sum(column_widths)
    table_height = row_height * (len(spec.bom_rows) + 1)
    group.add_component(RectanglePDF((x, y), table_width, table_height, 0.0, styles.outline))
    group.add_component(RectanglePDF((x, y), table_width, row_height, 0.0, styles.shaded))

    current_x = x
    for width in column_widths[:-1]:
        current_x += width
        group.add_component(LinePDF((current_x, y), (current_x, y + table_height), styles.grid))
    for index in range(1, len(spec.bom_rows) + 1):
        line_y = y + row_height * index
        group.add_component(LinePDF((x, line_y), (x + table_width, line_y), styles.grid))

    headers = ("ITEM", "PART NUMBER", "DESCRIPTION", "QTY")
    text_x = x + 3.0
    for header, width in zip(headers, column_widths, strict=True):
        _add_labeled_text(group, header, (text_x, y + 7.0), styles.small_text, f"bom_{header.lower().replace(' ', '_')}_header", "label")
        text_x += width

    for row_index, row in enumerate(spec.bom_rows, start=1):
        baseline = y + row_height * row_index + 7.0
        values = (row.item, row.part_number, row.description, row.quantity)
        text_x = x + 3.0
        for header, value, width in zip(("item", "part_number", "description", "quantity"), values, column_widths, strict=True):
            _add_labeled_text(group, value, (text_x, baseline), styles.body_text, header, "value", instance_id=row.item)
            text_x += width

    annotate_extraction_truth(group, "bom_table", spec.drawing_number, role="region", instance_id=spec.drawing_number)
    annotate_grammar_truth(group, "BOM-TABLE", "construct", value={"rows": len(spec.bom_rows)}, instance_id=spec.drawing_number)
    annotate_grammar_truth(group, "TABLE-GRID", "cue", value={"columns": len(column_widths), "rows": len(spec.bom_rows) + 1})
    return group


def _transparent_overlay_group(styles: _FixtureStyles) -> ComponentGroupPDF:
    group = ComponentGroupPDF("transparent_overlay")
    group.add_component(RectanglePDF((55.0, 72.0), 145.0, 32.0, 0.0, styles.transparent))
    _add_labeled_text(group, "ALPHA OVER BODY TEXT", (63.0, 91.0), styles.body_text, "transparent_overlay_note", "note")
    annotate_grammar_truth(group, "TRANSPARENCY-CUE", "cue", value="semi_transparent_region")
    return group


def _zone_marker_group(styles: _FixtureStyles) -> ComponentGroupPDF:
    group = ComponentGroupPDF("zone_markers")
    for index, label in enumerate(("1", "2", "3", "4"), start=0):
        x = 30.0 + index * 52.0
        group.add_component(RectanglePDF((x, 4.0), 16.0, 8.0, 0.0, styles.outline))
        _add_labeled_text(group, label, (x + 5.5, 10.0), styles.small_text, "zone_marker", "label", instance_id=label)
    annotate_grammar_truth(group, "ZONE-MARKERS", "cue", value={"top_edge_digits": 4})
    return group


def _add_labeled_text(
    group: ComponentGroupPDF,
    text: str,
    position: tuple[float, float],
    style: TextStyle,
    field_name: str,
    role: str,
    *,
    instance_id: str | None = None,
) -> TextPDF:
    component = TextPDF(text, position, style)
    annotate_extraction_truth(component, field_name, text, role=role, instance_id=instance_id)
    group.add_component(component)
    return component


def _coerce_fixture_page_rotation(rotation: object) -> int:
    if isinstance(rotation, bool) or not isinstance(rotation, int):
        raise TypeError("page_rotation must be an integer multiple of 90 or None.")
    if rotation % 90 != 0:
        raise ValueError("page_rotation must be a multiple of 90.")
    return rotation % 360


def _require_non_empty_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string.")
    return value


def _unique_style_name(namespace: str, suffix: str) -> str:
    base = f"{namespace}_{suffix}"
    if base not in Style.style_names:
        return base
    index = 1
    while f"{base}_{index}" in Style.style_names:
        index += 1
    return f"{base}_{index}"


DEFAULT_PARSER_STRESS_BOM_ROWS = (
    ParserStressBOMRow("1", "PSF-1001", "ROTATED PAGE BRACKET", "2"),
    ParserStressBOMRow("2", "PSF-1002", "TRANSPARENT COVER PLATE", "1"),
    ParserStressBOMRow("3", "PSF-1003", "TITLE BLOCK FASTENER", "8"),
)
