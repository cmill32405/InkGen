"""Behavioral tests for ZoningDrawing payload envelopes."""

from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

import pytest

from InkGen.boundary import Canvas
from InkGen.drawing_components import OutputFormat, ZoningDrawing
from InkGen.style import DrawingStyle, Font, TextStyle
from InkGen.svg_generator import ComponentGroupSVG


def _styles() -> tuple[DrawingStyle, TextStyle]:
    """Return unique styles for zoning payload contract tests."""
    line_style = DrawingStyle(f"zoning_payload_line_{uuid4().hex}", stroke="#111111", fill="none", stroke_width=0.2)
    text_style = TextStyle(f"zoning_payload_text_{uuid4().hex}", Font(size=6.0))
    return line_style, text_style


def _zoning() -> tuple[ZoningDrawing, DrawingStyle, TextStyle]:
    """Return a valid zoning recipe with explicit small zone counts."""
    line_style, text_style = _styles()
    zoning = ZoningDrawing(
        Canvas(210.0, 297.0, "mm"),
        line_style,
        text_style,
        margins=5.0,
        horizontal_zones=10,
        vertical_zones=8,
        first_horizontal_char=48,
    )
    return zoning, line_style, text_style


@pytest.mark.condition("ZONING-DRAWING-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("payload", "exception_type", "message"),
    [
        (object(), TypeError, "ZoningDrawing data must be a mapping"),
        ({}, ValueError, "ZoningDrawing data must include ZoningDrawing"),
        ({"ZoningDrawing": object()}, TypeError, "ZoningDrawing payload must be a mapping"),
    ],
)
def test_zoning_drawing_factory_rejects_malformed_roots(
    payload: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """ZONING-DRAWING-PAYLOAD-P2: Root zoning payloads fail explicitly."""
    with pytest.raises(exception_type, match=message):
        ZoningDrawing.create_from_dict(payload)


@pytest.mark.condition("ZONING-DRAWING-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("mutator", "exception_type", "message"),
    [
        (lambda data: data["ZoningDrawing"].pop("canvas"), ValueError, "ZoningDrawing payload must include canvas"),
        (lambda data: data["ZoningDrawing"].pop("line_style"), ValueError, "ZoningDrawing payload must include line_style"),
        (lambda data: data["ZoningDrawing"].pop("text_style"), ValueError, "ZoningDrawing payload must include text_style"),
        (lambda data: data["ZoningDrawing"].pop("parameters"), ValueError, "ZoningDrawing payload must include parameters"),
        (
            lambda data: data["ZoningDrawing"].__setitem__("parameters", []),
            TypeError,
            "ZoningDrawing parameters must be a mapping",
        ),
    ],
)
def test_zoning_drawing_factory_rejects_missing_or_malformed_fields(
    mutator: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """ZONING-DRAWING-PAYLOAD-P2: Required zoning fields fail explicitly."""
    zoning, line_style, text_style = _zoning()
    payload = deepcopy(zoning.parameters)
    mutator(payload)

    with pytest.raises(exception_type, match=message):
        ZoningDrawing.create_from_dict(payload, {line_style.name: line_style, text_style.name: text_style})


@pytest.mark.condition("ZONING-DRAWING-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("mutator", "exception_type", "message"),
    [
        (
            lambda data: data["ZoningDrawing"].__setitem__("line_style", object()),
            TypeError,
            "ZoningDrawing line_style must be a mapping",
        ),
        (
            lambda data: data["ZoningDrawing"]["line_style"].pop("DrawingStyle"),
            ValueError,
            "ZoningDrawing line_style must include DrawingStyle",
        ),
        (
            lambda data: data["ZoningDrawing"]["line_style"].__setitem__("DrawingStyle", object()),
            TypeError,
            "ZoningDrawing line_style entry must be a mapping",
        ),
        (
            lambda data: data["ZoningDrawing"]["line_style"]["DrawingStyle"].__setitem__("name", object()),
            TypeError,
            "ZoningDrawing line_style name must be a string",
        ),
        (
            lambda data: data["ZoningDrawing"].__setitem__("text_style", object()),
            TypeError,
            "ZoningDrawing text_style must be a mapping",
        ),
        (
            lambda data: data["ZoningDrawing"]["text_style"].pop("TextStyle"),
            ValueError,
            "ZoningDrawing text_style must include TextStyle",
        ),
        (
            lambda data: data["ZoningDrawing"]["text_style"].__setitem__("TextStyle", object()),
            TypeError,
            "ZoningDrawing text_style entry must be a mapping",
        ),
        (
            lambda data: data["ZoningDrawing"]["text_style"]["TextStyle"].__setitem__("name", object()),
            TypeError,
            "ZoningDrawing text_style name must be a string",
        ),
    ],
)
def test_zoning_drawing_factory_rejects_malformed_style_envelopes(
    mutator: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """ZONING-DRAWING-PAYLOAD-P2: Serialized style envelopes fail explicitly."""
    zoning, line_style, text_style = _zoning()
    payload = deepcopy(zoning.parameters)
    mutator(payload)

    with pytest.raises(exception_type, match=message):
        ZoningDrawing.create_from_dict(payload, {line_style.name: line_style, text_style.name: text_style})


@pytest.mark.condition("ZONING-DRAWING-PAYLOAD-P2")
def test_zoning_drawing_factory_rejects_malformed_style_registry() -> None:
    """ZONING-DRAWING-PAYLOAD-P2: Style registries must be mappings with matching kinds."""
    zoning, line_style, text_style = _zoning()

    with pytest.raises(TypeError, match="styles must be a mapping or None"):
        ZoningDrawing.create_from_dict(zoning.parameters, object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="must be a DrawingStyle"):
        ZoningDrawing.create_from_dict(zoning.parameters, {line_style.name: text_style, text_style.name: text_style})
    with pytest.raises(TypeError, match="must be a TextStyle"):
        ZoningDrawing.create_from_dict(zoning.parameters, {line_style.name: line_style, text_style.name: line_style})


@pytest.mark.condition("ZONING-DRAWING-PAYLOAD-P2")
def test_zoning_drawing_factory_preserves_valid_hydration_and_materialization() -> None:
    """ZONING-DRAWING-PAYLOAD-P2: Valid payloads still hydrate and materialize."""
    zoning, line_style, text_style = _zoning()

    recreated = ZoningDrawing.create_from_dict(zoning.parameters, {line_style.name: line_style, text_style.name: text_style})
    svg_group = recreated.to_group(OutputFormat.SVG)

    assert recreated.parameters == zoning.parameters
    assert isinstance(svg_group, ComponentGroupSVG)
    assert [component.parameters for component in svg_group.components()] == [
        component.parameters for component in zoning.to_group(OutputFormat.SVG).components()
    ]
