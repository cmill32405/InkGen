"""Behavioral tests for legacy CAD zoning factory payload validation."""

from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

import pytest

from InkGen.boundary import Canvas
from InkGen.cad_component_groups import Zoning
from InkGen.style import DrawingStyle, Font, TextStyle


def _line_style() -> DrawingStyle:
    return DrawingStyle(f"cad_zoning_factory_line_{uuid4().hex}", stroke="#111111", fill="none")


def _text_style() -> TextStyle:
    return TextStyle(f"cad_zoning_factory_text_{uuid4().hex}", Font(size=6.0))


def _zoning_payload() -> dict[str, object]:
    zoning = Zoning(
        Canvas(210.0, 297.0, "mm"),
        _line_style(),
        _text_style(),
        margins=5.0,
        horizontal_zones=10,
        vertical_zones=8,
    )
    return deepcopy(zoning.parameters)


@pytest.mark.condition("CAD-ZONING-FACTORY-PAYLOAD-P2")
def test_legacy_zoning_factory_preserves_valid_payload_and_style_overrides() -> None:
    """CAD-ZONING-FACTORY-PAYLOAD-P2: Valid payloads round-trip through supplied styles."""
    original = Zoning(Canvas(210.0, 297.0, "mm"), _line_style(), _text_style(), horizontal_zones=10, vertical_zones=8)
    line_style = _line_style()
    text_style = _text_style()
    payload = deepcopy(original.parameters)
    payload["Zoning"]["line_style"] = line_style.parameters
    payload["Zoning"]["text_style"] = text_style.parameters

    recreated = Zoning.create_from_dict(payload, {line_style.name: line_style, text_style.name: text_style})

    assert recreated.parameters == payload
    assert recreated._line_style is line_style
    assert recreated._text_style is text_style
    assert [type(component) for component in recreated.component_group.components()] == [
        type(component) for component in original.component_group.components()
    ]
    assert len(list(recreated.component_group.components())) == len(list(original.component_group.components()))


@pytest.mark.condition("CAD-ZONING-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("payload", "error_type", "message"),
    [
        (object(), TypeError, "Zoning data must be a mapping"),
        ({}, ValueError, "Zoning data must include Zoning"),
        ({"Zoning": object()}, TypeError, "Zoning payload must be a mapping"),
    ],
)
def test_legacy_zoning_factory_rejects_malformed_root_payloads(
    payload: object,
    error_type: type[Exception],
    message: str,
) -> None:
    """CAD-ZONING-FACTORY-PAYLOAD-P2: Malformed root envelopes fail explicitly."""
    with pytest.raises(error_type, match=message):
        Zoning.create_from_dict(payload)


@pytest.mark.condition("CAD-ZONING-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("field", "replacement", "error_type", "message"),
    [
        ("line_style", None, ValueError, "Zoning payload must include line_style"),
        ("text_style", None, ValueError, "Zoning payload must include text_style"),
        ("canvas", None, ValueError, "Zoning payload must include canvas"),
        ("parameters", None, ValueError, "Zoning payload must include parameters"),
        ("line_style", object(), TypeError, "Zoning line_style must be a mapping"),
        ("text_style", object(), TypeError, "Zoning text_style must be a mapping"),
        ("parameters", object(), TypeError, "Zoning parameters must be a mapping"),
    ],
)
def test_legacy_zoning_factory_rejects_missing_and_malformed_payload_fields(
    field: str,
    replacement: object,
    error_type: type[Exception],
    message: str,
) -> None:
    """CAD-ZONING-FACTORY-PAYLOAD-P2: Required payload fields fail before raw indexing."""
    payload = _zoning_payload()
    if replacement is None:
        del payload["Zoning"][field]
    else:
        payload["Zoning"][field] = replacement

    with pytest.raises(error_type, match=message):
        Zoning.create_from_dict(payload)


@pytest.mark.condition("CAD-ZONING-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("field", "value", "error_type", "message"),
    [
        ("line_style", {}, ValueError, "Zoning line_style must include DrawingStyle"),
        ("line_style", {"DrawingStyle": object()}, TypeError, "Zoning line_style entry must be a mapping"),
        ("line_style", {"DrawingStyle": {"name": object()}}, TypeError, "Zoning line_style name must be a string"),
        ("text_style", {}, ValueError, "Zoning text_style must include TextStyle"),
        ("text_style", {"TextStyle": object()}, TypeError, "Zoning text_style entry must be a mapping"),
        ("text_style", {"TextStyle": {"name": object()}}, TypeError, "Zoning text_style name must be a string"),
    ],
)
def test_legacy_zoning_factory_rejects_malformed_style_envelopes(
    field: str,
    value: object,
    error_type: type[Exception],
    message: str,
) -> None:
    """CAD-ZONING-FACTORY-PAYLOAD-P2: Style envelopes fail before style constructors."""
    payload = _zoning_payload()
    payload["Zoning"][field] = value

    with pytest.raises(error_type, match=message):
        Zoning.create_from_dict(payload)


@pytest.mark.condition("CAD-ZONING-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("styles", "error_type", "message"),
    [
        (object(), TypeError, "styles must be a mapping or None"),
        ({"line": object(), "text": _text_style()}, TypeError, "style override for 'line' must be a DrawingStyle"),
        ({"line": _line_style(), "text": object()}, TypeError, "style override for 'text' must be a TextStyle"),
    ],
)
def test_legacy_zoning_factory_rejects_malformed_style_registry(
    styles: object,
    error_type: type[Exception],
    message: str,
) -> None:
    """CAD-ZONING-FACTORY-PAYLOAD-P2: Supplied style registries must match style kinds."""
    payload = _zoning_payload()
    payload["Zoning"]["line_style"]["DrawingStyle"]["name"] = "line"
    payload["Zoning"]["text_style"]["TextStyle"]["name"] = "text"

    with pytest.raises(error_type, match=message):
        Zoning.create_from_dict(payload, styles)


@pytest.mark.condition("CAD-ZONING-FACTORY-PAYLOAD-P2")
def test_legacy_zoning_factory_delegates_parameter_validation_to_constructor() -> None:
    """CAD-ZONING-FACTORY-PAYLOAD-P2: Serialized parameters still use zoning boundary validation."""
    line_style = _line_style()
    text_style = _text_style()
    payload = _zoning_payload()
    payload["Zoning"]["line_style"] = line_style.parameters
    payload["Zoning"]["text_style"] = text_style.parameters
    payload["Zoning"]["parameters"]["horizontal_zones"] = True

    with pytest.raises(ValueError):
        Zoning.create_from_dict(payload, {line_style.name: line_style, text_style.name: text_style})
