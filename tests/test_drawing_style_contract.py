"""Tests for drawing style proof obligations."""

from __future__ import annotations

from uuid import uuid4

import pytest

from InkGen.pdf_generator import RectanglePDF
from InkGen.style import DrawingStyle
from InkGen.svg_generator import RectangleSVG


def _style_name(prefix: str = "drawing_style_contract") -> str:
    """Return a test-unique style name."""
    return f"{prefix}_{uuid4().hex}"


@pytest.mark.condition("STYLE-DRAWING-P1")
def test_drawing_style_normalizes_colors_and_preserves_valid_numeric_contract() -> None:
    """STYLE-DRAWING-P1: Valid drawing styles normalize colors and finite numbers."""
    default_style = DrawingStyle(name=_style_name())
    style = DrawingStyle(
        name=_style_name(),
        stroke="BLACK",
        stroke_width=0,
        fill="#AABBCC",
        stroke_opacity=0,
        fill_opacity=1,
    )

    assert default_style.stroke == "#000000"
    assert default_style.stroke_width == 0.2
    assert default_style.fill == "none"
    assert default_style.stroke_opacity == 1.0
    assert default_style.fill_opacity == 1.0
    assert style.stroke == "#000000"
    assert style.stroke_width == 0.0
    assert style.fill == "#aabbcc"
    assert style.stroke_opacity == 0.0
    assert style.fill_opacity == 1.0

    style.stroke_width = 0.75
    style.stroke_opacity = 0.5
    style.fill_opacity = 0.25

    assert style.parameters["DrawingStyle"] == {
        "name": style.name,
        "stroke": "#000000",
        "stroke_width": 0.75,
        "fill": "#aabbcc",
        "stroke_opacity": 0.5,
        "fill_opacity": 0.25,
    }


@pytest.mark.condition("STYLE-DRAWING-P1")
def test_drawing_style_rejects_malformed_colors_without_incidental_errors() -> None:
    """STYLE-DRAWING-P1: Colors must be supported strings, hex values, or none."""
    invalid_colors = ["", "#", "#12345", "#g12345", "#12345g", "!123456", "001122", None, object(), 1, True]

    for color in invalid_colors:
        with pytest.raises(ValueError):
            DrawingStyle(_style_name(), stroke=color)  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            DrawingStyle(_style_name(), fill=color)  # type: ignore[arg-type]

    style = DrawingStyle(_style_name(), stroke="none", fill="none")
    assert style.stroke == "none"
    assert style.fill == "none"

    for color in invalid_colors:
        with pytest.raises(ValueError):
            style.stroke = color  # type: ignore[assignment]
        with pytest.raises(ValueError):
            style.fill = color  # type: ignore[assignment]

    assert style.stroke == "none"
    assert style.fill == "none"


@pytest.mark.condition("STYLE-DRAWING-P1")
def test_drawing_style_rejects_invalid_stroke_width_and_opacity_boundaries() -> None:
    """STYLE-DRAWING-P1: Stroke width and opacity values must be finite bounded numbers."""
    invalid_stroke_widths = [True, False, -0.001, float("nan"), float("inf"), "1", object()]
    invalid_opacities = [True, False, -0.001, 1.001, float("nan"), float("inf"), "1", object()]

    for stroke_width in invalid_stroke_widths:
        with pytest.raises((TypeError, ValueError)):
            DrawingStyle(_style_name(), stroke_width=stroke_width)  # type: ignore[arg-type]

    for opacity in invalid_opacities:
        with pytest.raises((TypeError, ValueError)):
            DrawingStyle(_style_name(), stroke_opacity=opacity)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            DrawingStyle(_style_name(), fill_opacity=opacity)  # type: ignore[arg-type]

    style = DrawingStyle(_style_name(), stroke_width=0.2, stroke_opacity=0.8, fill_opacity=0.7)

    for stroke_width in invalid_stroke_widths:
        with pytest.raises((TypeError, ValueError)):
            style.stroke_width = stroke_width  # type: ignore[assignment]
        assert style.stroke_width == 0.2

    for opacity in invalid_opacities:
        with pytest.raises((TypeError, ValueError)):
            style.stroke_opacity = opacity  # type: ignore[assignment]
        with pytest.raises((TypeError, ValueError)):
            style.fill_opacity = opacity  # type: ignore[assignment]
        assert style.stroke_opacity == 0.8
        assert style.fill_opacity == 0.7


@pytest.mark.condition("STYLE-DRAWING-P1")
def test_drawing_style_hydration_uses_public_validation_boundaries() -> None:
    """STYLE-DRAWING-P1: Serialized drawing styles cannot bypass validation."""
    valid_payload = {
        "DrawingStyle": {
            "name": _style_name(),
            "stroke": "#336699",
            "stroke_width": 0.75,
            "fill": "orange",
            "stroke_opacity": 0.5,
            "fill_opacity": 0.25,
        }
    }
    style = DrawingStyle.create_from_dict(valid_payload)

    assert style.stroke == "#336699"
    assert style.stroke_width == 0.75
    assert style.fill == "#f58231"
    assert style.stroke_opacity == 0.5
    assert style.fill_opacity == 0.25

    invalid_payloads = []
    for field, value in [
        ("stroke", ""),
        ("fill", object()),
        ("stroke_width", -1.0),
        ("stroke_opacity", True),
        ("fill_opacity", float("nan")),
    ]:
        payload = {"DrawingStyle": valid_payload["DrawingStyle"].copy()}
        payload["DrawingStyle"]["name"] = _style_name()
        payload["DrawingStyle"][field] = value
        invalid_payloads.append(payload)

    for payload in invalid_payloads:
        with pytest.raises((TypeError, ValueError)):
            DrawingStyle.create_from_dict(payload)  # type: ignore[arg-type]


@pytest.mark.condition("STYLE-DRAWING-P1")
def test_drawing_style_contract_remains_live_in_svg_and_pdf_output() -> None:
    """STYLE-DRAWING-P1: SVG and PDF drawing paths consume validated style values."""
    style = DrawingStyle(
        _style_name(),
        stroke="#336699",
        stroke_width=0.75,
        fill="#cc0000",
        stroke_opacity=0.5,
        fill_opacity=0.25,
    )

    svg = RectangleSVG((1.0, 2.0), 3.0, 4.0, 0.0, style).generate_svg()
    pdf = RectanglePDF((1.0, 2.0), 3.0, 4.0, 0.0, style).generate_pdf()

    assert "fill:#cc0000" in svg
    assert "fill-opacity:0.25" in svg
    assert "stroke:#336699" in svg
    assert "stroke-width:0.75" in svg
    assert "stroke-opacity:0.5" in svg
    assert "0.2 0.4 0.6 RG" in pdf
    assert "0.75 w" in pdf
    assert "0.8 0 0 rg" in pdf
    assert pdf.endswith("\nB\nQ")
