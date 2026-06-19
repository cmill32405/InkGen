"""Tests for Font proof obligations."""

from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest

from InkGen.document_outputs import FlowDocument
from InkGen.drawing_components import DrawingComponentGroup, TextDrawing
from InkGen.dxf_generator import DXFDocument
from InkGen.paragraph import Paragraph
from InkGen.pdf_generator import TextPDF
from InkGen.style import Font, TextStyle
from InkGen.svg_generator import TextSVG


def _style_name(prefix: str = "font_contract") -> str:
    """Return a test-unique style name."""
    return f"{prefix}_{uuid4().hex}"


def _text_style(font: Font) -> TextStyle:
    """Return a test-unique text style for a font."""
    return TextStyle(_style_name("font_text"), font)


@pytest.mark.condition("FONT-P1")
def test_font_constructor_and_setters_share_valid_contract() -> None:
    """FONT-P1: Constructor and setters preserve the same valid font domain."""
    font = Font(
        family=["DejaVu Sans", "sans-serif"],
        style="italic",
        variant="small-caps",
        stretch=500,
        weight=700,
        size=12,
    )

    assert font.style == "italic"
    assert font.variant == "small-caps"
    assert font.stretch == 500
    assert font.weight == 700
    assert font.size == 12.0

    font.family = "sans-serif"
    font.style = "oblique"
    font.variant = "normal"
    font.stretch = "expanded"
    font.weight = "bold"
    font.size = "x-large"

    assert font.style == "oblique"
    assert font.variant == "normal"
    assert font.stretch == "expanded"
    assert font.weight == "bold"
    assert font.size == pytest.approx(14.4, rel=1e-6)

    font.size = 9
    assert font.parameters["Font"]["size"] == 9.0

    font.size = 1.0
    assert font.size == 1.0
    font.size = 240.0
    assert font.size == 240.0

    font.stretch = 0
    assert font.stretch == 0
    font.stretch = 1000
    assert font.stretch == 1000

    font.weight = 0
    assert font.weight == 0
    font.weight = 1000
    assert font.weight == 1000


@pytest.mark.condition("FONT-P1")
def test_font_rejects_invalid_size_boundaries() -> None:
    """FONT-P1: Font size must be named or finite, positive, and bounded."""
    for value in [True, False, 0, -0.1, 240.1, float("nan"), float("inf"), "bad", object()]:
        with pytest.raises((TypeError, ValueError)):
            Font(size=value)  # type: ignore[arg-type]

    font = Font(size=10.0)
    for value in [True, False, 0, -0.1, 240.1, float("nan"), float("inf"), "bad", object()]:
        with pytest.raises((TypeError, ValueError)):
            font.size = value  # type: ignore[assignment]
        assert font.size == 10.0


@pytest.mark.condition("FONT-P1")
def test_font_rejects_invalid_weight_stretch_and_family_boundaries() -> None:
    """FONT-P1: Font family, weight, and stretch fail at public boundaries."""
    for value in [True, False, 1.5, object()]:
        with pytest.raises((TypeError, ValueError)):
            Font(weight=value)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            Font(stretch=value)  # type: ignore[arg-type]

    for field in ["weight", "stretch"]:
        for value in [-1, 1001, "bad"]:
            with pytest.raises(ValueError, match=f"Invalid {field} value"):
                Font(**{field: value})  # type: ignore[arg-type]

    for value in ["", [], ["valid", ""], [object()], object(), True]:
        with pytest.raises(TypeError):
            Font(family=value)  # type: ignore[arg-type]

    font = Font()
    for value in [True, False, 1.5, object()]:
        with pytest.raises((TypeError, ValueError)):
            font.weight = value  # type: ignore[assignment]
        with pytest.raises((TypeError, ValueError)):
            font.stretch = value  # type: ignore[assignment]
        assert font.weight == "normal"
        assert font.stretch == "normal"

    for value in [-1, 1001, "bad"]:
        with pytest.raises(ValueError, match="Invalid weight value"):
            font.weight = value  # type: ignore[assignment]
        with pytest.raises(ValueError, match="Invalid stretch value"):
            font.stretch = value  # type: ignore[assignment]


@pytest.mark.condition("FONT-P1")
def test_font_custom_paths_are_validated_and_copied(tmp_path: Path) -> None:
    """FONT-P1: Custom font paths validate type/existence without caller mutation."""
    custom_paths = [str(tmp_path)]

    font = Font(custom_font_paths=custom_paths)

    assert custom_paths == [str(tmp_path)]
    assert font.parameters["Font"]["custom_font_paths"] == [str(tmp_path).replace("\\", "/") + "/"]

    with pytest.raises(TypeError):
        Font(custom_font_paths=object())  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        Font(custom_font_paths=[str(tmp_path), object()])  # type: ignore[list-item]
    with pytest.raises(ValueError):
        Font(custom_font_paths=str(tmp_path / "missing"))


@pytest.mark.condition("FONT-P1")
def test_font_hydration_uses_public_validation_boundaries() -> None:
    """FONT-P1: Serialized Font payloads cannot bypass public validation."""
    font = Font(style="italic", variant="normal", stretch="condensed", weight="bold", size=11)
    payload = font.parameters

    clone = Font.create_from_dict(payload)

    assert clone.style == "italic"
    assert clone.variant == "normal"
    assert clone.stretch == "condensed"
    assert clone.weight == "bold"
    assert clone.size == 11.0

    invalid_payloads = []
    for field, value in [
        ("family", ""),
        ("style", "diagonal"),
        ("variant", "caps"),
        ("stretch", True),
        ("weight", True),
        ("size", float("nan")),
        ("custom_font_paths", object()),
    ]:
        invalid = {"Font": payload["Font"].copy()}
        invalid["Font"][field] = value
        invalid_payloads.append(invalid)

    for invalid in invalid_payloads:
        with pytest.raises((TypeError, ValueError)):
            Font.create_from_dict(invalid)  # type: ignore[arg-type]


@pytest.mark.condition("FONT-P1")
def test_font_contract_remains_live_in_output_paths() -> None:
    """FONT-P1: SVG, PDF, DXF, and DOCX paths consume validated font size/style."""
    font = Font(style="italic", weight="bold", size=14)
    style = _text_style(font)
    style.color = "#112233"

    svg = TextSVG("Font", (1.0, 2.0), style).generate_svg()
    pdf = TextPDF("Font", (1.0, 2.0), style).generate_pdf()

    group = DrawingComponentGroup("font-live")
    group.add_component(TextDrawing("Font", (1.0, 2.0), style))
    dxf_document = DXFDocument(canvas_height=20.0)
    dxf_document.add_group(group)
    dxf = dxf_document.to_dxf_string()

    document = FlowDocument(title="Font Contract")
    document.add_paragraph(Paragraph("Font", position=(0.0, 0.0), width=50.0, style=style))
    with zipfile.ZipFile(BytesIO(document.to_docx_bytes())) as package:
        document_xml = package.read("word/document.xml").decode("utf-8")

    assert "font-style:italic" in svg
    assert "font-size:18.666667px" in svg
    assert "/F1 14 Tf" in pdf
    assert "\n40\n4.938889\n" in dxf
    assert '<w:sz w:val="28"/>' in document_xml
    assert "<w:b/>" in document_xml
    assert "<w:i/>" in document_xml
