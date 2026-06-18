"""Tests for paragraph proof obligations."""

from __future__ import annotations

from uuid import uuid4

import pytest

from InkGen.document_outputs import FlowDocument
from InkGen.paragraph import LineSpacingRule, Paragraph, ParagraphAlignment, TabStop
from InkGen.pdf_generator import ComponentGroupPDF
from InkGen.style import Font, TextStyle
from InkGen.svg_generator import ComponentGroupSVG


def _style() -> TextStyle:
    """Return a unique text style for paragraph contract tests."""
    return TextStyle(f"paragraph_contract_{uuid4().hex}", Font(size=10.0))


def _paragraph(text: str = "Alpha beta gamma") -> Paragraph:
    """Return a valid paragraph for live-path tests."""
    return Paragraph(text, position=(4.0, 6.0), width=32.0, style=_style(), line_spacing=1.2)


@pytest.mark.condition("PARAGRAPH-P1")
def test_paragraph_rejects_nonfinite_boolean_and_malformed_positions() -> None:
    """PARAGRAPH-P1: Paragraph origins must be finite numeric coordinates."""
    style = _style()
    invalid_positions = [
        (float("nan"), 0.0),
        (0.0, float("inf")),
        (True, 0.0),
        (0.0, False),
        (0.0,),
        (0.0, 1.0, 2.0),
    ]

    for position in invalid_positions:
        with pytest.raises((TypeError, ValueError)):
            Paragraph("bad", position=position, style=style)  # type: ignore[arg-type]

    paragraph = Paragraph("ok", position=(0.0, 0.0), style=style)
    paragraph.position = (-2.5, 3.5)
    assert paragraph.position == (-2.5, 3.5)


@pytest.mark.condition("PARAGRAPH-P1")
def test_paragraph_rejects_invalid_numeric_measurements() -> None:
    """PARAGRAPH-P1: Paragraph measurements must be finite and respect field bounds."""
    style = _style()

    for field in ("width", "hanging_indent", "left_indent", "right_indent", "space_before", "space_after"):
        with pytest.raises(ValueError, match="at least"):
            Paragraph("bad", style=style, **{field: -0.1})
        with pytest.raises(ValueError, match="finite"):
            Paragraph("bad", style=style, **{field: float("nan")})
        with pytest.raises(TypeError, match="numeric"):
            Paragraph("bad", style=style, **{field: True})
    with pytest.raises(TypeError, match="numeric"):
        Paragraph("bad", style=style, width=object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="numeric"):
        Paragraph("bad", style=style, width="wide")  # type: ignore[arg-type]

    for value in (float("nan"), float("inf")):
        with pytest.raises(ValueError, match="finite"):
            Paragraph("bad", style=style, first_line_indent=value)
    with pytest.raises(TypeError, match="numeric"):
        Paragraph("bad", style=style, first_line_indent=False)

    paragraph = Paragraph("ok", style=style, first_line_indent=-3.0, width=0.0)
    assert paragraph.first_line_indent == pytest.approx(-3.0)
    assert paragraph.width == pytest.approx(0.0)


@pytest.mark.condition("PARAGRAPH-P1")
def test_paragraph_rejects_invalid_line_spacing_and_outline_level() -> None:
    """PARAGRAPH-P1: Line spacing is finite positive and outline level is an integer level."""
    style = _style()

    for value in (0.0, -1.0):
        with pytest.raises(ValueError, match="greater than"):
            Paragraph("bad", style=style, line_spacing=value)
    for value in (float("nan"), float("inf")):
        with pytest.raises(ValueError, match="finite"):
            Paragraph("bad", style=style, line_spacing=value)
    with pytest.raises(TypeError, match="numeric"):
        Paragraph("bad", style=style, line_spacing=True)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="integer"):
        Paragraph("bad", style=style, outline_level=-1)
    with pytest.raises(ValueError, match="integer"):
        Paragraph("bad", style=style, outline_level=True)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="integer"):
        Paragraph("bad", style=style, outline_level=10)
    assert Paragraph("ok", style=style, outline_level=0).outline_level == 0
    assert Paragraph("ok", style=style, outline_level=9).outline_level == 9


@pytest.mark.condition("PARAGRAPH-P1")
def test_tab_stops_reject_invalid_positions() -> None:
    """PARAGRAPH-P1: Tab stops must be finite non-negative positions."""
    for value in (-0.1, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            TabStop(value)
    with pytest.raises(TypeError, match="numeric"):
        TabStop(True)  # type: ignore[arg-type]

    assert TabStop(0.0).position == pytest.approx(0.0)
    assert TabStop(2.0, "right").alignment is ParagraphAlignment.RIGHT  # type: ignore[arg-type]

    paragraph = _paragraph()
    with pytest.raises(ValueError, match="finite"):
        paragraph.add_tab_stop(float("nan"))
    stop = paragraph.add_tab_stop(8.0, alignment="right")
    assert stop == TabStop(8.0, ParagraphAlignment.RIGHT)


@pytest.mark.condition("PARAGRAPH-P1")
def test_paragraph_hydration_uses_public_validation_boundaries() -> None:
    """PARAGRAPH-P1: Serialized payloads cannot bypass paragraph validation."""
    paragraph = _paragraph("Persisted")
    payload = paragraph.parameters
    payload["Paragraph"]["text"] = 123
    with pytest.raises(TypeError, match="text"):
        Paragraph.create_from_dict(payload, {paragraph.style.name: paragraph.style})

    payload = paragraph.parameters
    payload["Paragraph"]["keep_together"] = "yes"
    with pytest.raises(TypeError, match="bool"):
        Paragraph.create_from_dict(payload, {paragraph.style.name: paragraph.style})

    payload = paragraph.parameters
    payload["Paragraph"]["outline_level"] = True
    with pytest.raises(ValueError, match="integer"):
        Paragraph.create_from_dict(payload, {paragraph.style.name: paragraph.style})

    payload = paragraph.parameters
    payload["Paragraph"]["tab_stops"] = [{"position": float("inf"), "alignment": "left", "leader": None}]
    with pytest.raises(ValueError, match="finite"):
        Paragraph.create_from_dict(payload, {paragraph.style.name: paragraph.style})


@pytest.mark.condition("PARAGRAPH-P1")
def test_paragraph_contract_remains_live_through_render_and_document_paths() -> None:
    """PARAGRAPH-P1: Valid paragraphs still materialize and export through dependent paths."""
    paragraph = Paragraph(
        "Alpha beta gamma delta",
        position=(4.0, 6.0),
        width=28.0,
        style=_style(),
        alignment="right",
        line_spacing_rule=LineSpacingRule.EXACTLY,
        line_spacing=5.0,
    )

    lines = paragraph.layout_lines()
    assert len(lines) >= 1
    assert all(line.position[0] >= paragraph.position[0] for line in lines)

    drawing_group = paragraph.to_drawing_group("paragraph_contract")
    assert isinstance(drawing_group.to_group("svg"), ComponentGroupSVG)
    assert isinstance(drawing_group.to_group("pdf"), ComponentGroupPDF)

    document = FlowDocument(title="Paragraph contract")
    document.add_paragraph(paragraph)
    assert "Alpha beta" in document.to_plain_text()
    assert "Alpha beta" in document.to_html()
