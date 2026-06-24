"""Behavioral tests for primitive component factory payload envelopes."""

from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

import pytest

from InkGen.component import (
    Component,
    DrawingComponent,
    SingleDimensionDrawingComponent,
    StandardDrawingComponent,
    TextComponent,
    WidthHeightDrawingComponent,
)
from InkGen.style import DrawingStyle, Font, TextStyle


def _drawing_style() -> DrawingStyle:
    """Return a unique drawing style for component-factory contract tests."""
    return DrawingStyle(f"component_factory_draw_{uuid4().hex}", stroke="#000000", fill="none")


def _text_style() -> TextStyle:
    """Return a unique text style for component-factory contract tests."""
    return TextStyle(f"component_factory_text_{uuid4().hex}", Font(size=11.0))


@pytest.mark.condition("COMPONENT-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("factory", "key", "style"),
    [
        (Component.create_from_dict, "Component", None),
        (DrawingComponent.create_from_dict, "DrawingComponent", _drawing_style()),
        (StandardDrawingComponent.create_from_dict, "StandardDrawingComponent", _drawing_style()),
        (SingleDimensionDrawingComponent.create_from_dict, "SingleDimensionDrawingComponent", _drawing_style()),
        (WidthHeightDrawingComponent.create_from_dict, "WidthHeightDrawingComponent", _drawing_style()),
        (TextComponent.create_from_dict, "TextComponent", _text_style()),
    ],
)
def test_component_factories_reject_malformed_payload_roots(
    factory: Callable[..., object],
    key: str,
    style: object | None,
) -> None:
    """COMPONENT-FACTORY-PAYLOAD-P2: Factory roots fail before incidental subscription errors."""
    cases = [
        (object(), TypeError, f"{key} data must be a mapping"),
        ({}, ValueError, f"{key} data must include {key}"),
        ({key: object()}, TypeError, f"{key} payload must be a mapping"),
    ]

    for payload, exception_type, message in cases:
        with pytest.raises(exception_type, match=message):
            if style is None:
                factory(payload)
            else:
                factory(payload, style)


@pytest.mark.condition("COMPONENT-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("factory", "payload", "style", "message"),
    [
        (DrawingComponent.create_from_dict, {"DrawingComponent": {}}, None, "DrawingComponent payload must include style"),
        (
            StandardDrawingComponent.create_from_dict,
            {"StandardDrawingComponent": {"point_2": (1.0, 1.0)}},
            _drawing_style(),
            "StandardDrawingComponent payload must include point_1",
        ),
        (
            StandardDrawingComponent.create_from_dict,
            {"StandardDrawingComponent": {"point_1": (0.0, 0.0)}},
            _drawing_style(),
            "StandardDrawingComponent payload must include point_2",
        ),
        (
            SingleDimensionDrawingComponent.create_from_dict,
            {"SingleDimensionDrawingComponent": {"size": 1.0}},
            _drawing_style(),
            "SingleDimensionDrawingComponent payload must include position",
        ),
        (
            SingleDimensionDrawingComponent.create_from_dict,
            {"SingleDimensionDrawingComponent": {"position": (0.0, 0.0)}},
            _drawing_style(),
            "SingleDimensionDrawingComponent payload must include size",
        ),
        (
            WidthHeightDrawingComponent.create_from_dict,
            {"WidthHeightDrawingComponent": {"width": 1.0, "height": 1.0}},
            _drawing_style(),
            "WidthHeightDrawingComponent payload must include position",
        ),
        (
            WidthHeightDrawingComponent.create_from_dict,
            {"WidthHeightDrawingComponent": {"position": (0.0, 0.0), "height": 1.0}},
            _drawing_style(),
            "WidthHeightDrawingComponent payload must include width",
        ),
        (
            WidthHeightDrawingComponent.create_from_dict,
            {"WidthHeightDrawingComponent": {"position": (0.0, 0.0), "width": 1.0}},
            _drawing_style(),
            "WidthHeightDrawingComponent payload must include height",
        ),
        (
            TextComponent.create_from_dict,
            {"TextComponent": {"position": (0.0, 0.0)}},
            _text_style(),
            "TextComponent payload must include text",
        ),
        (
            TextComponent.create_from_dict,
            {"TextComponent": {"text": "label"}},
            _text_style(),
            "TextComponent payload must include position",
        ),
    ],
)
def test_component_factories_reject_missing_required_payload_fields(
    factory: Callable[..., object],
    payload: object,
    style: object | None,
    message: str,
) -> None:
    """COMPONENT-FACTORY-PAYLOAD-P2: Required fields fail at the factory boundary."""
    with pytest.raises(ValueError, match=message):
        if style is None:
            factory(payload)
        else:
            factory(payload, style)


@pytest.mark.condition("COMPONENT-FACTORY-PAYLOAD-P2")
def test_component_factories_preserve_explicit_style_payload_compatibility() -> None:
    """COMPONENT-FACTORY-PAYLOAD-P2: Explicit styles still allow compact geometry payloads."""
    drawing_style = _drawing_style()
    text_style = _text_style()

    drawing = DrawingComponent.create_from_dict({"DrawingComponent": {}}, drawing_style)
    standard = StandardDrawingComponent.create_from_dict(
        {"StandardDrawingComponent": {"point_1": (0.0, 0.0), "point_2": (1.0, 1.0)}},
        drawing_style,
    )
    single = SingleDimensionDrawingComponent.create_from_dict(
        {"SingleDimensionDrawingComponent": {"position": (2.0, 3.0), "size": 4.0}},
        drawing_style,
    )
    width_height = WidthHeightDrawingComponent.create_from_dict(
        {"WidthHeightDrawingComponent": {"position": (5.0, 6.0), "width": 7.0, "height": 8.0}},
        drawing_style,
    )
    text = TextComponent.create_from_dict(
        {"TextComponent": {"text": "label", "position": (9.0, 10.0)}},
        text_style,
    )

    assert drawing.parameters["DrawingComponent"]["style"] == drawing_style.parameters
    assert standard.point_1 == (0.0, 0.0)
    assert single.size == 4.0
    assert width_height.width == 7.0
    assert text.text == "label"
