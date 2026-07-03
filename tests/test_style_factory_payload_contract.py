"""Behavioral tests for style factory payload envelopes."""

from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

import pytest

from InkGen.component import DrawingComponent, TextComponent
from InkGen.style import DrawingStyle, Font, Style, TextStyle


def _name(prefix: str = "style_factory_payload") -> str:
    """Return a unique style name for factory payload contract tests."""
    return f"{prefix}_{uuid4().hex}"


def _font_payload() -> dict[str, dict[str, object]]:
    """Return a valid serialized font payload."""
    return {
        "Font": {
            "family": "sans-serif",
            "style": "normal",
            "variant": "normal",
            "stretch": "normal",
            "weight": "normal",
            "size": 12.0,
            "custom_font_paths": None,
        }
    }


def _drawing_style_payload() -> dict[str, dict[str, object]]:
    """Return a valid serialized drawing-style payload."""
    return {
        "DrawingStyle": {
            "name": _name("drawing"),
            "stroke": "black",
            "stroke_width": 0.2,
            "fill": "none",
            "stroke_opacity": 1.0,
            "fill_opacity": 1.0,
            "stroke_dasharray": [],
            "stroke_dash_offset": 0.0,
            "stroke_linecap": "butt",
            "stroke_linejoin": "miter",
            "stroke_miterlimit": 10.0,
        }
    }


def _text_style_payload() -> dict[str, dict[str, object]]:
    """Return a valid serialized text-style payload."""
    return {
        "TextStyle": {
            "name": _name("text"),
            "color": "#000000",
            "superscript": False,
            "subscript": False,
            "text_align": "start",
            "line_spacing": 1.0,
            "font": _font_payload(),
        }
    }


@pytest.mark.condition("STYLE-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("factory", "key"),
    [
        (Style.create_from_dict, "Style"),
        (DrawingStyle.create_from_dict, "DrawingStyle"),
        (Font.create_from_dict, "Font"),
        (TextStyle.create_from_dict, "TextStyle"),
    ],
)
def test_style_factories_reject_malformed_payload_roots(
    factory: Callable[[object], object],
    key: str,
) -> None:
    """STYLE-FACTORY-PAYLOAD-P2: Style factory roots fail explicitly."""
    cases = [
        (object(), TypeError, f"{key} data must be a mapping"),
        ({}, ValueError, f"{key} data must include {key}"),
        ({key: object()}, TypeError, f"{key} payload must be a mapping"),
    ]

    for payload, exception_type, message in cases:
        with pytest.raises(exception_type, match=message):
            factory(payload)


@pytest.mark.condition("STYLE-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("factory", "payload", "message"),
    [
        (Style.create_from_dict, {"Style": {}}, "Style payload must include name"),
        (
            DrawingStyle.create_from_dict,
            {"DrawingStyle": {"name": _name("missing_stroke")}},
            "DrawingStyle payload must include stroke",
        ),
        (
            DrawingStyle.create_from_dict,
            {
                "DrawingStyle": {
                    "name": _name("missing_fill_opacity"),
                    "stroke": "black",
                    "stroke_width": 0.2,
                    "fill": "none",
                    "stroke_opacity": 1.0,
                }
            },
            "DrawingStyle payload must include fill_opacity",
        ),
        (
            Font.create_from_dict,
            {"Font": {"family": "sans-serif"}},
            "Font payload must include style",
        ),
        (
            Font.create_from_dict,
            {
                "Font": {
                    "family": "sans-serif",
                    "style": "normal",
                    "variant": "normal",
                    "stretch": "normal",
                    "weight": "normal",
                    "size": 12.0,
                }
            },
            "Font payload must include custom_font_paths",
        ),
        (
            TextStyle.create_from_dict,
            {"TextStyle": {"name": _name("missing_font")}},
            "TextStyle payload must include font",
        ),
        (
            TextStyle.create_from_dict,
            {
                "TextStyle": {
                    "name": _name("missing_line_spacing"),
                    "color": "#000000",
                    "superscript": False,
                    "subscript": False,
                    "text_align": "start",
                    "font": _font_payload(),
                }
            },
            "TextStyle payload must include line_spacing",
        ),
    ],
)
def test_style_factories_reject_missing_required_fields(
    factory: Callable[[object], object],
    payload: object,
    message: str,
) -> None:
    """STYLE-FACTORY-PAYLOAD-P2: Required style fields fail at the factory boundary."""
    with pytest.raises(ValueError, match=message):
        factory(payload)


@pytest.mark.condition("STYLE-FACTORY-PAYLOAD-P2")
def test_style_factories_preserve_valid_hydration() -> None:
    """STYLE-FACTORY-PAYLOAD-P2: Valid serialized style payloads still hydrate."""
    style = Style.create_from_dict({"Style": {"name": _name("base")}})
    drawing_style = DrawingStyle.create_from_dict(_drawing_style_payload())
    font = Font.create_from_dict(_font_payload())
    text_style = TextStyle.create_from_dict(_text_style_payload())

    assert style.name.startswith("base_")
    assert drawing_style.stroke == "#000000"
    assert font.size == 12.0
    assert text_style.color == "#000000"
    assert text_style.font.size == 12.0


@pytest.mark.condition("STYLE-FACTORY-PAYLOAD-P2")
def test_style_factory_payload_contract_remains_live_in_component_hydration() -> None:
    """STYLE-FACTORY-PAYLOAD-P2: Component factories consume validated style payloads."""
    drawing_component = DrawingComponent.create_from_dict(
        {"DrawingComponent": {"style": _drawing_style_payload()}},
    )
    text_component = TextComponent.create_from_dict(
        {
            "TextComponent": {
                "text": "Style",
                "position": (1.0, 2.0),
                "style": _text_style_payload(),
            }
        },
    )

    assert drawing_component.style.stroke == "#000000"
    assert text_component.style.color == "#000000"

    with pytest.raises(ValueError, match="DrawingStyle payload must include stroke"):
        DrawingComponent.create_from_dict(
            {"DrawingComponent": {"style": {"DrawingStyle": {"name": _name("bad_drawing")}}}},
        )
    with pytest.raises(ValueError, match="TextStyle payload must include font"):
        TextComponent.create_from_dict(
            {
                "TextComponent": {
                    "text": "Style",
                    "position": (1.0, 2.0),
                    "style": {"TextStyle": {"name": _name("bad_text")}},
                }
            },
        )
