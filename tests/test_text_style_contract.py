"""Tests for text style proof obligations."""

from __future__ import annotations

from uuid import uuid4

import pytest

from InkGen.pdf_generator import TextPDF
from InkGen.style import Font, Style, TextStyle
from InkGen.svg_generator import TextSVG


def _style_name(prefix: str = "text_style_contract") -> str:
    """Return a test-unique style name."""
    return f"{prefix}_{uuid4().hex}"


def _font() -> Font:
    """Return a deterministic default font object for text style tests."""
    return Font(size=12.0)


@pytest.mark.condition("TEXT-STYLE-P1")
def test_text_style_defaults_and_valid_updates_are_serialized() -> None:
    """TEXT-STYLE-P1: TextStyle defaults and valid public updates are deterministic."""
    style = TextStyle(_style_name(), _font())

    assert style.color == "#000000"
    assert style.superscript is False
    assert style.subscript is False
    assert style.text_align == "start"
    assert style.text_anchor == "start"
    assert style.line_spacing == 1.0

    style.color = "Blue"
    style.superscript = True
    style.subscript = True
    style.text_align = "right"
    style.line_spacing = 0.0

    assert style.parameters["TextStyle"]["color"] == "#0000ff"
    assert style.parameters["TextStyle"]["superscript"] is True
    assert style.parameters["TextStyle"]["subscript"] is True
    assert style.parameters["TextStyle"]["text_align"] == "end"
    assert style.text_anchor == "end"
    assert style.parameters["TextStyle"]["line_spacing"] == 0.0


@pytest.mark.condition("TEXT-STYLE-P1")
def test_text_style_rejects_invalid_font_without_registering_name() -> None:
    """TEXT-STYLE-P1: Invalid font values fail before style names are reserved."""
    name = _style_name("bad_font")

    with pytest.raises(TypeError):
        TextStyle(name, object())  # type: ignore[arg-type]

    assert name not in Style.style_names

    style = TextStyle(name, _font())
    assert style.name == name


@pytest.mark.condition("TEXT-STYLE-P1")
def test_text_style_rejects_invalid_color_align_and_script_boundaries() -> None:
    """TEXT-STYLE-P1: Color, alignment, and script flags fail at public boundaries."""
    style = TextStyle(_style_name(), _font())

    for color in ["", "#12345", "#12345g", "001122", None, object(), True]:
        with pytest.raises(ValueError):
            style.color = color  # type: ignore[assignment]
        assert style.color == "#000000"

    alignments = {
        "left": ("start", "start"),
        "start": ("start", "start"),
        "right": ("end", "end"),
        "end": ("end", "end"),
        "middle": ("center", "middle"),
        "center": ("center", "middle"),
    }
    for value, expected in alignments.items():
        style.text_align = value
        assert (style.text_align, style.text_anchor) == expected

    before = (style.text_align, style.text_anchor)
    for value in ["diagonal", "", None, 1, True]:
        with pytest.raises((TypeError, ValueError)):
            style.text_align = value  # type: ignore[assignment]
        assert (style.text_align, style.text_anchor) == before

    for value in [1, 0, "true", None, object()]:
        with pytest.raises(TypeError):
            style.superscript = value  # type: ignore[assignment]
        with pytest.raises(TypeError):
            style.subscript = value  # type: ignore[assignment]
        assert style.superscript is False
        assert style.subscript is False


@pytest.mark.condition("TEXT-STYLE-P1")
def test_text_style_rejects_invalid_line_spacing_boundaries() -> None:
    """TEXT-STYLE-P1: Line spacing must be finite, non-negative, and non-boolean."""
    style = TextStyle(_style_name(), _font())
    style.line_spacing = 0
    assert style.line_spacing == 0.0
    style.line_spacing = 1.25
    assert style.line_spacing == 1.25

    for value in [True, False, -0.001, float("nan"), float("inf"), "1", None, object()]:
        with pytest.raises((TypeError, ValueError)):
            style.line_spacing = value  # type: ignore[assignment]
        assert style.line_spacing == 1.25


@pytest.mark.condition("TEXT-STYLE-P1")
def test_text_style_hydration_uses_public_validation_boundaries() -> None:
    """TEXT-STYLE-P1: Serialized TextStyle payloads cannot bypass validation."""
    style = TextStyle(_style_name(), _font())
    style.color = "#112233"
    style.superscript = True
    style.text_align = "center"
    style.line_spacing = 1.5

    payload = style.parameters
    payload["TextStyle"]["name"] = _style_name("clone")
    clone = TextStyle.create_from_dict(payload)

    assert clone.color == "#112233"
    assert clone.superscript is True
    assert clone.subscript is False
    assert clone.text_align == "center"
    assert clone.text_anchor == "middle"
    assert clone.line_spacing == 1.5

    invalid_payloads = []
    for field, value in [
        ("color", object()),
        ("superscript", "true"),
        ("subscript", 1),
        ("text_align", "diagonal"),
        ("line_spacing", True),
    ]:
        invalid = {"TextStyle": payload["TextStyle"].copy()}
        invalid["TextStyle"]["font"] = payload["TextStyle"]["font"]
        invalid["TextStyle"]["name"] = _style_name("invalid")
        invalid["TextStyle"][field] = value
        invalid_payloads.append(invalid)

    for invalid in invalid_payloads:
        with pytest.raises((TypeError, ValueError)):
            TextStyle.create_from_dict(invalid)  # type: ignore[arg-type]


@pytest.mark.condition("TEXT-STYLE-P1")
def test_text_style_contract_remains_live_in_svg_and_pdf_output() -> None:
    """TEXT-STYLE-P1: SVG and PDF text paths consume validated text style values."""
    style = TextStyle(_style_name(), _font())
    style.color = "#112233"
    style.text_align = "center"
    style.line_spacing = 1.25

    svg = TextSVG("Hello <PDF>", (4.0, 5.0), style).generate_svg()
    pdf = TextPDF("Hello (PDF)\nNext", (4.0, 5.0), style).generate_pdf()

    assert "fill:#112233" in svg
    assert "line-height:1.25" in svg
    assert "text-anchor:middle" in svg
    assert "text-align:center" in svg
    assert "Hello &lt;PDF&gt;" in svg
    assert "0.066667 0.133333 0.2 rg" in pdf
    assert "/F1 12 Tf" in pdf
    assert "1 0 0 -1 -35.6 5 Tm" in pdf
    assert "(Hello \\(PDF\\)) Tj" in pdf
    assert "1 0 0 -1 -10.4 20 Tm" in pdf
    assert "(Next) Tj" in pdf
