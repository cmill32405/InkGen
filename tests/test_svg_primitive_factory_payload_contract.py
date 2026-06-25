"""Behavioral tests for SVG primitive factory payload envelopes."""

from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

import pytest

from InkGen.style import DrawingStyle, Font, TextStyle
from InkGen.svg_generator import CircleSVG, LineSVG, PolygonalSVG, RectangleSVG, RegularPolygonSVG, TextSVG


def _drawing_style() -> DrawingStyle:
    """Return a unique drawing style for SVG primitive factory tests."""
    return DrawingStyle(f"svg_primitive_{uuid4().hex}", stroke="#000000", fill="none")


def _text_style() -> TextStyle:
    """Return a unique text style for SVG primitive factory tests."""
    return TextStyle(f"svg_primitive_text_{uuid4().hex}", Font(size=11.0))


@pytest.mark.condition("SVG-PRIMITIVE-FACTORY-PAYLOAD-P2")
def test_svg_primitive_factories_preserve_explicit_style_compact_payloads() -> None:
    """SVG-PRIMITIVE-FACTORY-PAYLOAD-P2: Valid compact primitive payloads hydrate."""
    drawing_style = _drawing_style()
    text_style = _text_style()

    rectangle = RectangleSVG.create_from_dict(
        {"RectangleSVG": {"position": (0.0, 0.0), "width": 2.0, "height": 3.0, "corner_radii": 0.0}},
        drawing_style,
    )
    line = LineSVG.create_from_dict({"LineSVG": {"point_1": (0.0, 0.0), "point_2": (1.0, 1.0)}}, drawing_style)
    regular = RegularPolygonSVG.create_from_dict(
        {"RegularPolygonSVG": {"position": (0.0, 0.0), "sides": 3, "radius": 1.0, "angle": 0.0, "corner_radius": 0.0}},
        drawing_style,
    )
    polygonal = PolygonalSVG.create_from_dict(
        {"PolygonalSVG": {"points": [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]}},
        drawing_style,
    )
    circle = CircleSVG.create_from_dict({"CircleSVG": {"position": (0.0, 0.0), "radius": 1.0}}, drawing_style)
    text = TextSVG.create_from_dict({"TextSVG": {"text": "label", "position": (1.0, 2.0)}}, text_style)

    assert rectangle.width == 2.0
    assert line.point_2 == (1.0, 1.0)
    assert regular.sides == 3
    assert len(polygonal.points) == 3
    assert circle.radius == 1.0
    assert text.text == "label"


@pytest.mark.condition("SVG-PRIMITIVE-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("factory", "key", "style"),
    [
        (RectangleSVG.create_from_dict, "RectangleSVG", _drawing_style()),
        (LineSVG.create_from_dict, "LineSVG", _drawing_style()),
        (RegularPolygonSVG.create_from_dict, "RegularPolygonSVG", _drawing_style()),
        (PolygonalSVG.create_from_dict, "PolygonalSVG", _drawing_style()),
        (CircleSVG.create_from_dict, "CircleSVG", _drawing_style()),
        (TextSVG.create_from_dict, "TextSVG", _text_style()),
    ],
)
def test_svg_primitive_factories_reject_malformed_payload_roots(
    factory: Callable[..., object],
    key: str,
    style: object,
) -> None:
    """SVG-PRIMITIVE-FACTORY-PAYLOAD-P2: Primitive factory roots fail explicitly."""
    cases = [
        (object(), TypeError, f"{key} data must be a mapping"),
        ({}, ValueError, f"{key} data must include {key}"),
        ({key: object()}, TypeError, f"{key} payload must be a mapping"),
    ]

    for payload, exception_type, message in cases:
        with pytest.raises(exception_type, match=message):
            factory(payload, style)


@pytest.mark.condition("SVG-PRIMITIVE-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("factory", "payload"),
    [
        (RectangleSVG.create_from_dict, {"RectangleSVG": {}}),
        (LineSVG.create_from_dict, {"LineSVG": {}}),
        (RegularPolygonSVG.create_from_dict, {"RegularPolygonSVG": {}}),
        (PolygonalSVG.create_from_dict, {"PolygonalSVG": {}}),
        (CircleSVG.create_from_dict, {"CircleSVG": {}}),
        (TextSVG.create_from_dict, {"TextSVG": {}}),
    ],
)
def test_svg_primitive_factories_require_style_when_not_explicit(
    factory: Callable[..., object],
    payload: object,
) -> None:
    """SVG-PRIMITIVE-FACTORY-PAYLOAD-P2: Style fields are required without explicit style."""
    with pytest.raises(ValueError, match="style"):
        factory(payload)


@pytest.mark.condition("SVG-PRIMITIVE-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("factory", "payload", "style", "message"),
    [
        (RectangleSVG.create_from_dict, {"RectangleSVG": {"width": 1.0, "height": 1.0, "corner_radii": 0.0}}, _drawing_style(), "position"),
        (LineSVG.create_from_dict, {"LineSVG": {"point_1": (0.0, 0.0)}}, _drawing_style(), "point_2"),
        (RegularPolygonSVG.create_from_dict, {"RegularPolygonSVG": {"position": (0.0, 0.0), "sides": 3}}, _drawing_style(), "radius"),
        (
            RegularPolygonSVG.create_from_dict,
            {"RegularPolygonSVG": {"position": (0.0, 0.0), "sides": 3, "radius": 1.0, "corner_radius": 0.0}},
            _drawing_style(),
            "angle",
        ),
        (
            RegularPolygonSVG.create_from_dict,
            {"RegularPolygonSVG": {"position": (0.0, 0.0), "sides": 3, "radius": 1.0, "angle": 0.0}},
            _drawing_style(),
            "corner_radius",
        ),
        (PolygonalSVG.create_from_dict, {"PolygonalSVG": {}}, _drawing_style(), "points"),
        (CircleSVG.create_from_dict, {"CircleSVG": {"position": (0.0, 0.0)}}, _drawing_style(), "radius"),
        (TextSVG.create_from_dict, {"TextSVG": {"text": "label"}}, _text_style(), "position"),
    ],
)
def test_svg_primitive_factories_reject_missing_required_fields(
    factory: Callable[..., object],
    payload: object,
    style: object,
    message: str,
) -> None:
    """SVG-PRIMITIVE-FACTORY-PAYLOAD-P2: Required primitive fields fail explicitly."""
    with pytest.raises(ValueError, match=message):
        factory(payload, style)
