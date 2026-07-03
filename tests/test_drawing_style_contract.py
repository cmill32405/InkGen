"""Tests for drawing style proof obligations."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

import InkGen.pdf_generator as pdf_module
import InkGen.svg_generator as svg_module
from InkGen.pdf_generator import RectanglePDF
from InkGen.style import DrawingStyle
from InkGen.svg_generator import RectangleSVG


def _style_name(prefix: str = "drawing_style_contract") -> str:
    """Return a test-unique style name."""
    return f"{prefix}_{uuid4().hex}"


def _new_string(value: str) -> str:
    """Return an equal string through a runtime conversion path."""
    return bytes(value, "ascii").decode("ascii")


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
    assert default_style.stroke_dasharray == ()
    assert default_style.stroke_dash_offset == 0.0
    assert default_style.stroke_linecap == "butt"
    assert default_style.stroke_linejoin == "miter"
    assert default_style.stroke_miterlimit == 10.0
    assert style.stroke == "#000000"
    assert style.stroke_width == 0.0
    assert style.fill == "#aabbcc"
    assert style.stroke_opacity == 0.0
    assert style.fill_opacity == 1.0

    style.stroke_width = 0.75
    style.stroke_opacity = 0.5
    style.fill_opacity = 0.25
    style.stroke_dasharray = [1.5, 0.5]
    style.stroke_dash_offset = 0.25
    style.stroke_linecap = "round"
    style.stroke_linejoin = "bevel"
    style.stroke_miterlimit = 3.5

    assert style.parameters["DrawingStyle"] == {
        "name": style.name,
        "stroke": "#000000",
        "stroke_width": 0.75,
        "fill": "#aabbcc",
        "stroke_opacity": 0.5,
        "fill_opacity": 0.25,
        "stroke_dasharray": [1.5, 0.5],
        "stroke_dash_offset": 0.25,
        "stroke_linecap": "round",
        "stroke_linejoin": "bevel",
        "stroke_miterlimit": 3.5,
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


@pytest.mark.condition("STYLE-DRAWING-STROKE-P2")
def test_drawing_style_rejects_invalid_stroke_presentation_boundaries() -> None:
    """STYLE-DRAWING-STROKE-P2: Stroke presentation fields validate explicit domains."""
    invalid_dasharrays = [[0, 0], [-1.0], [float("nan")], [True], "1,2", b"\x01\x02", object()]
    invalid_offsets = [True, -0.001, float("nan"), float("inf"), "1", object()]
    invalid_caps = ["", "flat", "ROUND", 1, object()]
    invalid_joins = ["", "arcs", "MITER", 1, object()]
    invalid_miters = [True, 0.0, -0.001, float("nan"), float("inf"), "1", object()]

    for dasharray in invalid_dasharrays:
        with pytest.raises((TypeError, ValueError)):
            DrawingStyle(_style_name(), stroke_dasharray=dasharray)  # type: ignore[arg-type]
    for offset in invalid_offsets:
        with pytest.raises((TypeError, ValueError)):
            DrawingStyle(_style_name(), stroke_dash_offset=offset)  # type: ignore[arg-type]
    for linecap in invalid_caps:
        with pytest.raises(ValueError):
            DrawingStyle(_style_name(), stroke_linecap=linecap)  # type: ignore[arg-type]
    for linejoin in invalid_joins:
        with pytest.raises(ValueError):
            DrawingStyle(_style_name(), stroke_linejoin=linejoin)  # type: ignore[arg-type]
    for miterlimit in invalid_miters:
        with pytest.raises((TypeError, ValueError)):
            DrawingStyle(_style_name(), stroke_miterlimit=miterlimit)  # type: ignore[arg-type]

    style = DrawingStyle(_style_name(), stroke_dasharray=[2.0], stroke_dash_offset=0.5, stroke_linecap="square", stroke_linejoin="round")
    for dasharray in invalid_dasharrays:
        with pytest.raises((TypeError, ValueError)):
            style.stroke_dasharray = dasharray  # type: ignore[assignment]
        assert style.stroke_dasharray == (2.0,)
    for offset in invalid_offsets:
        with pytest.raises((TypeError, ValueError)):
            style.stroke_dash_offset = offset  # type: ignore[assignment]
        assert style.stroke_dash_offset == 0.5
    for linecap in invalid_caps:
        with pytest.raises(ValueError):
            style.stroke_linecap = linecap  # type: ignore[assignment]
        assert style.stroke_linecap == "square"
    for linejoin in invalid_joins:
        with pytest.raises(ValueError):
            style.stroke_linejoin = linejoin  # type: ignore[assignment]
        assert style.stroke_linejoin == "round"
    for miterlimit in invalid_miters:
        with pytest.raises((TypeError, ValueError)):
            style.stroke_miterlimit = miterlimit  # type: ignore[assignment]
        assert style.stroke_miterlimit == 10.0


@pytest.mark.condition("STYLE-DRAWING-STROKE-P2")
def test_stroke_presentation_maps_each_renderer_operator_domain() -> None:
    """STYLE-DRAWING-STROKE-P2: SVG and PDF map every stroke presentation token deterministically."""
    default_style = DrawingStyle(_style_name())
    default_svg_tokens = svg_module._style_properties(default_style).split(";")  # noqa: SLF001
    default_pdf_operators = pdf_module._style_operators(default_style)  # noqa: SLF001

    assert "stroke-dasharray:" not in ";".join(default_svg_tokens)
    assert "stroke-dashoffset:" not in ";".join(default_svg_tokens)
    assert "stroke-linecap:" not in ";".join(default_svg_tokens)
    assert "stroke-linejoin:" not in ";".join(default_svg_tokens)
    assert "stroke-miterlimit:" not in ";".join(default_svg_tokens)
    assert not any(operator.endswith(" d") for operator in default_pdf_operators)
    assert "0.2 w" in default_pdf_operators
    assert "0 0 0 RG" in default_pdf_operators
    assert not any(operator.endswith(" J") for operator in default_pdf_operators)
    assert not any(operator.endswith(" j") for operator in default_pdf_operators)
    assert not any(operator.endswith(" M") for operator in default_pdf_operators)
    with pytest.raises(TypeError):
        pdf_module._style_operators(default_style, False)  # noqa: SLF001
    with pytest.raises(TypeError):
        svg_module._style_properties(default_style, False)  # noqa: SLF001

    fill_style = DrawingStyle(_style_name(), fill="#ffffff")
    fill_pdf_operators = pdf_module._style_operators(fill_style)  # noqa: SLF001

    assert "1 1 1 rg" in fill_pdf_operators

    legacy_dash_style = SimpleNamespace(stroke="#000000", fill="none", stroke_dasharray=(2.0,))
    legacy_dash_svg_tokens = svg_module._style_properties(legacy_dash_style).split(";")  # type: ignore[arg-type]  # noqa: SLF001
    legacy_dash_pdf_operators = pdf_module._style_operators(legacy_dash_style)  # type: ignore[arg-type]  # noqa: SLF001

    assert "stroke-dasharray:2.0" in legacy_dash_svg_tokens
    assert "stroke-dashoffset:" not in ";".join(legacy_dash_svg_tokens)
    assert "stroke-linecap:" not in ";".join(legacy_dash_svg_tokens)
    assert "stroke-linejoin:" not in ";".join(legacy_dash_svg_tokens)
    assert "stroke-miterlimit:" not in ";".join(legacy_dash_svg_tokens)
    assert "[2] 0 d" in legacy_dash_pdf_operators
    assert "0 w" in legacy_dash_pdf_operators
    assert not any(operator.endswith(" M") for operator in legacy_dash_pdf_operators)

    context = pdf_module.PDFRenderContext(
        canvas_height=10.0,
        graphics_state_registry=pdf_module._PDFGraphicsStateRegistry(),  # noqa: SLF001
    )
    legacy_opaque_operators = pdf_module._style_operators(legacy_dash_style, context=context)  # type: ignore[arg-type]  # noqa: SLF001

    assert not any(operator.endswith(" gs") for operator in legacy_opaque_operators)

    stroke_disabled_style = DrawingStyle(_style_name(), stroke_opacity=0.25, fill_opacity=1.0)
    stroke_disabled_operators = pdf_module._style_operators(stroke_disabled_style, stroke=False, context=context)  # noqa: SLF001

    assert not any(operator.endswith(" gs") for operator in stroke_disabled_operators)

    runtime_default_style = DrawingStyle(
        _style_name(),
        stroke_linecap=_new_string("butt"),
        stroke_linejoin=_new_string("miter"),
    )
    runtime_default_svg_tokens = svg_module._style_properties(runtime_default_style).split(";")  # noqa: SLF001
    runtime_default_pdf_operators = pdf_module._style_operators(runtime_default_style)  # noqa: SLF001

    assert "stroke-linecap:" not in ";".join(runtime_default_svg_tokens)
    assert "stroke-linejoin:" not in ";".join(runtime_default_svg_tokens)
    assert not any(operator.endswith(" J") for operator in runtime_default_pdf_operators)
    assert not any(operator.endswith(" j") for operator in runtime_default_pdf_operators)

    square_round_style = DrawingStyle(
        _style_name(),
        stroke_dasharray=[2.0, 3.0],
        stroke_dash_offset=0.0,
        stroke_linecap="square",
        stroke_linejoin="round",
        stroke_miterlimit=1.0,
    )
    square_round_svg_tokens = svg_module._style_properties(square_round_style).split(";")  # noqa: SLF001
    square_round_pdf_operators = pdf_module._style_operators(square_round_style)  # noqa: SLF001

    assert "stroke-dasharray:2.0,3.0" in square_round_svg_tokens
    assert "stroke-dashoffset:" not in ";".join(square_round_svg_tokens)
    assert "stroke-linecap:square" in square_round_svg_tokens
    assert "stroke-linejoin:round" in square_round_svg_tokens
    assert "stroke-miterlimit:1.0" in square_round_svg_tokens
    assert "[2 3] 0 d" in square_round_pdf_operators
    assert "2 J" in square_round_pdf_operators
    assert "1 j" in square_round_pdf_operators
    assert "1 M" in square_round_pdf_operators

    high_miter_style = DrawingStyle(_style_name(), stroke_miterlimit=11.0)
    high_miter_svg_tokens = svg_module._style_properties(high_miter_style).split(";")  # noqa: SLF001
    high_miter_pdf_operators = pdf_module._style_operators(high_miter_style)  # noqa: SLF001

    assert "stroke-miterlimit:11.0" in high_miter_svg_tokens
    assert "11 M" in high_miter_pdf_operators


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
            "stroke_dasharray": [1.0, 2.0],
            "stroke_dash_offset": 0.5,
            "stroke_linecap": "round",
            "stroke_linejoin": "bevel",
            "stroke_miterlimit": 4.0,
        }
    }
    style = DrawingStyle.create_from_dict(valid_payload)

    assert style.stroke == "#336699"
    assert style.stroke_width == 0.75
    assert style.fill == "#f58231"
    assert style.stroke_opacity == 0.5
    assert style.fill_opacity == 0.25
    assert style.stroke_dasharray == (1.0, 2.0)
    assert style.stroke_dash_offset == 0.5
    assert style.stroke_linecap == "round"
    assert style.stroke_linejoin == "bevel"
    assert style.stroke_miterlimit == 4.0

    invalid_payloads = []
    for field, value in [
        ("stroke", ""),
        ("fill", object()),
        ("stroke_width", -1.0),
        ("stroke_opacity", True),
        ("fill_opacity", float("nan")),
        ("stroke_dasharray", [0.0, 0.0]),
        ("stroke_dash_offset", -1.0),
        ("stroke_linecap", "flat"),
        ("stroke_linejoin", "arcs"),
        ("stroke_miterlimit", 0.0),
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
        stroke_dasharray=[1.5, 0.75],
        stroke_dash_offset=0.25,
        stroke_linecap="round",
        stroke_linejoin="bevel",
        stroke_miterlimit=4.0,
    )

    svg = RectangleSVG((1.0, 2.0), 3.0, 4.0, 0.0, style).generate_svg()
    pdf = RectanglePDF((1.0, 2.0), 3.0, 4.0, 0.0, style).generate_pdf()

    assert "fill:#cc0000" in svg
    assert "fill-opacity:0.25" in svg
    assert "stroke:#336699" in svg
    assert "stroke-width:0.75" in svg
    assert "stroke-opacity:0.5" in svg
    assert "stroke-dasharray:1.5,0.75" in svg
    assert "stroke-dashoffset:0.25" in svg
    assert "stroke-linecap:round" in svg
    assert "stroke-linejoin:bevel" in svg
    assert "stroke-miterlimit:4.0" in svg
    assert "0.2 0.4 0.6 RG" in pdf
    assert "0.75 w" in pdf
    assert "[1.5 0.75] 0.25 d" in pdf
    assert "1 J" in pdf
    assert "2 j" in pdf
    assert "4 M" in pdf
    assert "0.8 0 0 rg" in pdf
    assert pdf.endswith("\nB\nQ")
