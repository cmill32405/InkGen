"""Tests for Word-like renderer-neutral paragraph layout."""

from __future__ import annotations

from uuid import uuid4

import pytest

from InkGen.boundary import Canvas
from InkGen.paragraph import LineSpacingRule, Paragraph, ParagraphAlignment, TabStop
from InkGen.pdf_generator import ComponentGroupPDF, DocumentPDF
from InkGen.style import Font, TextStyle
from InkGen.svg_generator import ComponentGroupSVG


def _style() -> TextStyle:
    return TextStyle(f"paragraph_style_{uuid4().hex}", Font(size=10.0))


@pytest.mark.condition("PDF-P3")
def test_paragraph_tracks_word_like_parameters_and_geometry() -> None:
    """PDF-P3: Paragraph stores Word-like spacing, indentation, and pagination settings."""
    paragraph = Paragraph(
        "First line wraps into a second line",
        position=(10.0, 20.0),
        width=38.0,
        style=_style(),
        alignment=ParagraphAlignment.CENTER,
        first_line_indent=4.0,
        hanging_indent=2.0,
        left_indent=3.0,
        right_indent=5.0,
        space_before=2.0,
        space_after=3.0,
        line_spacing=1.5,
        line_spacing_rule=LineSpacingRule.MULTIPLE,
        keep_together=True,
        keep_with_next=True,
        page_break_before=True,
        widow_control=False,
        outline_level=2,
    )
    paragraph.add_tab_stop(12.0, alignment="right", leader=".")

    assert paragraph.position == (10.0, 20.0)
    assert paragraph.content_width == pytest.approx(30.0)
    assert paragraph.keep_together is True
    assert paragraph.keep_with_next is True
    assert paragraph.page_break_before is True
    assert paragraph.widow_control is False
    assert paragraph.outline_level == 2
    assert paragraph.tab_stops == (TabStop(12.0, ParagraphAlignment.RIGHT, "."),)
    assert paragraph.bbox[0] == (10.0, 20.0)
    assert paragraph.bbox[1][0] == pytest.approx(48.0)
    assert paragraph.height > paragraph.space_before + paragraph.space_after


@pytest.mark.condition("PDF-P3")
def test_paragraph_layout_wraps_and_applies_alignment() -> None:
    """PDF-P3: Paragraph line layout wraps text and positions baselines deterministically."""
    style = _style()
    paragraph = Paragraph(
        "Alpha beta gamma delta",
        position=(5.0, 7.0),
        width=32.0,
        style=style,
        alignment="right",
        left_indent=2.0,
        right_indent=2.0,
        space_before=1.0,
        line_spacing_rule=LineSpacingRule.EXACTLY,
        line_spacing=6.0,
    )

    lines = paragraph.layout_lines()

    assert len(lines) > 1
    assert lines[0].line_index == 0
    assert lines[1].position[1] - lines[0].position[1] == pytest.approx(6.0)
    assert lines[0].position[0] >= paragraph.position[0] + paragraph.left_indent
    assert all(line.width <= paragraph.content_width for line in lines)


@pytest.mark.condition("PDF-P3")
def test_paragraph_materializes_to_svg_and_pdf_groups() -> None:
    """PDF-P3: Paragraph emits renderer-neutral text lines that materialize as SVG or PDF."""
    paragraph = Paragraph("A short paragraph", position=(10.0, 10.0), width=80.0, style=_style())
    drawing_group = paragraph.to_drawing_group("paragraph_group")

    svg_group = drawing_group.to_group("svg")
    pdf_group = drawing_group.to_group("pdf")
    document = DocumentPDF(Canvas(200.0, 120.0))
    document.add_page()
    document.page(1).layer("base").add_component_group(pdf_group)

    assert isinstance(svg_group, ComponentGroupSVG)
    assert isinstance(pdf_group, ComponentGroupPDF)
    assert {type(component).__name__ for component in svg_group.components()} == {"TextSVG"}
    assert {type(component).__name__ for component in pdf_group.components()} == {"TextPDF"}
    assert document.to_pdf_bytes().startswith(b"%PDF-1.4\n")


@pytest.mark.condition("PDF-P3")
def test_paragraph_parameters_round_trip() -> None:
    """PDF-P3: Paragraph serializes and recreates all layout parameters."""
    style = _style()
    paragraph = Paragraph(
        "Round trip",
        position=(1.0, 2.0),
        width=44.0,
        style=style,
        alignment="justify",
        first_line_indent=3.0,
        space_before=1.0,
        space_after=2.0,
        line_spacing=12.0,
        line_spacing_rule="at_least",
        outline_level=1,
    )
    paragraph.add_tab_stop(8.0)

    clone = Paragraph.create_from_dict(paragraph.parameters, {style.name: style})

    assert clone.parameters == paragraph.parameters
    assert clone.layout_lines() == paragraph.layout_lines()


@pytest.mark.condition("PDF-P3")
def test_paragraph_rejects_invalid_settings() -> None:
    """PDF-P3: Paragraph fails loudly for invalid Word-like settings."""
    style = _style()

    with pytest.raises(TypeError):
        Paragraph(123, style=style)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        Paragraph("bad", width=-1.0, style=style)
    with pytest.raises(ValueError):
        Paragraph("bad", style=style, alignment="diagonal")
    with pytest.raises(ValueError):
        Paragraph("bad", style=style, line_spacing=0.0)
    with pytest.raises(TypeError):
        Paragraph("bad", style=style, keep_together="yes")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        Paragraph("bad", style=style, outline_level=10)
    with pytest.raises(ValueError):
        TabStop(-1.0)
