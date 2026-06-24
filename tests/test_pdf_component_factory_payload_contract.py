"""Behavioral tests for PDF primitive factory payload envelopes."""

from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

import pytest

from InkGen.component import PathCommand
from InkGen.pdf_generator import (
    ArcPDF,
    CirclePDF,
    ComponentGroupPDF,
    CubicBezierPDF,
    LinePDF,
    PathPDF,
    PolygonalPDF,
    QuadraticBezierPDF,
    RectanglePDF,
    RegularPolygonPDF,
    TextPDF,
)
from InkGen.style import DrawingStyle, Font, TextStyle


def _drawing_style() -> DrawingStyle:
    """Return a unique drawing style for PDF factory contract tests."""
    return DrawingStyle(f"pdf_factory_draw_{uuid4().hex}", stroke="#000000", fill="none")


def _text_style() -> TextStyle:
    """Return a unique text style for PDF factory contract tests."""
    return TextStyle(f"pdf_factory_text_{uuid4().hex}", Font(size=11.0))


@pytest.mark.condition("PDF-COMPONENT-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("factory", "key", "style"),
    [
        (RectanglePDF.create_from_dict, "RectanglePDF", _drawing_style()),
        (LinePDF.create_from_dict, "LinePDF", _drawing_style()),
        (ArcPDF.create_from_dict, "ArcPDF", _drawing_style()),
        (QuadraticBezierPDF.create_from_dict, "QuadraticBezierPDF", _drawing_style()),
        (CubicBezierPDF.create_from_dict, "CubicBezierPDF", _drawing_style()),
        (PathPDF.create_from_dict, "PathPDF", _drawing_style()),
        (RegularPolygonPDF.create_from_dict, "RegularPolygonPDF", _drawing_style()),
        (PolygonalPDF.create_from_dict, "PolygonalPDF", _drawing_style()),
        (CirclePDF.create_from_dict, "CirclePDF", _drawing_style()),
        (TextPDF.create_from_dict, "TextPDF", _text_style()),
    ],
)
def test_pdf_component_factories_reject_malformed_payload_roots(
    factory: Callable[..., object],
    key: str,
    style: object,
) -> None:
    """PDF-COMPONENT-FACTORY-PAYLOAD-P2: PDF factory roots fail explicitly."""
    cases = [
        (object(), TypeError, f"{key} data must be a mapping"),
        ({}, ValueError, f"{key} data must include {key}"),
        ({key: object()}, TypeError, f"{key} payload must be a mapping"),
    ]

    for payload, exception_type, message in cases:
        with pytest.raises(exception_type, match=message):
            factory(payload, style)


@pytest.mark.condition("PDF-COMPONENT-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("factory", "payload", "style", "message"),
    [
        (RectanglePDF.create_from_dict, {"RectanglePDF": {"width": 1.0, "height": 1.0, "corner_radii": 0.0}}, _drawing_style(), "position"),
        (LinePDF.create_from_dict, {"LinePDF": {"point_1": (0.0, 0.0)}}, _drawing_style(), "point_2"),
        (
            ArcPDF.create_from_dict,
            {"ArcPDF": {"center": (0.0, 0.0), "radius_x": 1.0, "radius_y": 1.0, "start_angle": 0.0}},
            _drawing_style(),
            "end_angle",
        ),
        (
            QuadraticBezierPDF.create_from_dict,
            {"QuadraticBezierPDF": {"start_point": (0.0, 0.0), "control_point": (1.0, 1.0)}},
            _drawing_style(),
            "end_point",
        ),
        (
            CubicBezierPDF.create_from_dict,
            {"CubicBezierPDF": {"start_point": (0.0, 0.0), "control_point1": (1.0, 1.0), "end_point": (3.0, 0.0)}},
            _drawing_style(),
            "control_point2",
        ),
        (RegularPolygonPDF.create_from_dict, {"RegularPolygonPDF": {"position": (0.0, 0.0), "sides": 3}}, _drawing_style(), "radius"),
        (PolygonalPDF.create_from_dict, {"PolygonalPDF": {}}, _drawing_style(), "points"),
        (CirclePDF.create_from_dict, {"CirclePDF": {"position": (0.0, 0.0)}}, _drawing_style(), "radius"),
        (TextPDF.create_from_dict, {"TextPDF": {"text": "label"}}, _text_style(), "position"),
    ],
)
def test_pdf_component_factories_reject_missing_required_payload_fields(
    factory: Callable[..., object],
    payload: object,
    style: object,
    message: str,
) -> None:
    """PDF-COMPONENT-FACTORY-PAYLOAD-P2: Required fields fail at the factory boundary."""
    with pytest.raises(ValueError, match=message):
        factory(payload, style)


@pytest.mark.condition("PDF-COMPONENT-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("factory", "payload"),
    [
        (RectanglePDF.create_from_dict, {"RectanglePDF": {}}),
        (LinePDF.create_from_dict, {"LinePDF": {}}),
        (ArcPDF.create_from_dict, {"ArcPDF": {}}),
        (QuadraticBezierPDF.create_from_dict, {"QuadraticBezierPDF": {}}),
        (CubicBezierPDF.create_from_dict, {"CubicBezierPDF": {}}),
        (PathPDF.create_from_dict, {"PathPDF": {}}),
        (RegularPolygonPDF.create_from_dict, {"RegularPolygonPDF": {}}),
        (PolygonalPDF.create_from_dict, {"PolygonalPDF": {}}),
        (CirclePDF.create_from_dict, {"CirclePDF": {}}),
        (TextPDF.create_from_dict, {"TextPDF": {}}),
    ],
)
def test_pdf_component_factories_require_style_when_not_explicit(
    factory: Callable[..., object],
    payload: object,
) -> None:
    """PDF-COMPONENT-FACTORY-PAYLOAD-P2: Style fields are required without an explicit style."""
    with pytest.raises(ValueError, match="style"):
        factory(payload)


@pytest.mark.condition("PDF-COMPONENT-FACTORY-PAYLOAD-P2")
def test_pdf_component_factories_preserve_explicit_style_compact_payloads() -> None:
    """PDF-COMPONENT-FACTORY-PAYLOAD-P2: Explicit styles still allow compact PDF payloads."""
    drawing_style = _drawing_style()
    text_style = _text_style()

    rectangle = RectanglePDF.create_from_dict(
        {"RectanglePDF": {"position": (0.0, 0.0), "width": 2.0, "height": 3.0, "corner_radii": 0.0}},
        drawing_style,
    )
    line = LinePDF.create_from_dict({"LinePDF": {"point_1": (0.0, 0.0), "point_2": (1.0, 1.0)}}, drawing_style)
    arc = ArcPDF.create_from_dict(
        {"ArcPDF": {"center": (0.0, 0.0), "radius_x": 1.0, "radius_y": 2.0, "start_angle": 0.0, "end_angle": 90.0}},
        drawing_style,
    )
    quadratic = QuadraticBezierPDF.create_from_dict(
        {"QuadraticBezierPDF": {"start_point": (0.0, 0.0), "control_point": (1.0, 1.0), "end_point": (2.0, 0.0)}},
        drawing_style,
    )
    cubic = CubicBezierPDF.create_from_dict(
        {
            "CubicBezierPDF": {
                "start_point": (0.0, 0.0),
                "control_point1": (1.0, 1.0),
                "control_point2": (2.0, 1.0),
                "end_point": (3.0, 0.0),
            }
        },
        drawing_style,
    )
    path_command = PathCommand("A", [(2.0, 3.0)])
    path_command.flags = {"radii": (1.0, 1.5), "rotation": 0.0, "large_arc": 0, "sweep": 1}
    path = PathPDF.create_from_dict(
        {
            "PathPDF": {
                "commands": [
                    PathCommand("M", [(0.0, 0.0)]).parameters,
                    {**path_command.parameters, "flags": path_command.flags},
                ]
            }
        },
        drawing_style,
    )
    regular = RegularPolygonPDF.create_from_dict(
        {"RegularPolygonPDF": {"position": (0.0, 0.0), "sides": 3, "radius": 1.0}},
        drawing_style,
    )
    polygonal = PolygonalPDF.create_from_dict(
        {"PolygonalPDF": {"points": [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]}},
        drawing_style,
    )
    circle = CirclePDF.create_from_dict({"CirclePDF": {"position": (0.0, 0.0), "radius": 1.0}}, drawing_style)
    text = TextPDF.create_from_dict({"TextPDF": {"text": "label", "position": (1.0, 2.0)}}, text_style)

    assert rectangle.width == 2.0
    assert line.point_2 == (1.0, 1.0)
    assert arc.rotation == 0.0
    assert quadratic.end_point == (2.0, 0.0)
    assert cubic.end_point == (3.0, 0.0)
    assert path.commands[0].type == "M"
    assert path.commands[1].flags == path_command.flags
    assert regular.angle == 0.0
    assert regular.corner_radius == 0.0
    assert len(polygonal.points) == 3
    assert circle.radius == 1.0
    assert text.text == "label"


@pytest.mark.condition("PDF-COMPONENT-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("payload", "exception_type", "message"),
    [
        ({"PathPDF": {"commands": "M 0 0"}}, TypeError, "PathPDF commands must be a sequence"),
        ({"PathPDF": {"commands": [object()]}}, TypeError, "PathPDF command payload must be a mapping"),
        ({"PathPDF": {"commands": [{}]}}, ValueError, "PathPDF command payload must include type"),
    ],
)
def test_path_pdf_factory_rejects_malformed_command_payloads(
    payload: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """PDF-COMPONENT-FACTORY-PAYLOAD-P2: Path command envelopes fail before incidental errors."""
    with pytest.raises(exception_type, match=message):
        PathPDF.create_from_dict(payload, _drawing_style())


@pytest.mark.condition("PDF-COMPONENT-FACTORY-PAYLOAD-P2")
def test_pdf_component_factory_payload_contract_remains_live_in_group_hydration() -> None:
    """PDF-COMPONENT-FACTORY-PAYLOAD-P2: ComponentGroupPDF consumes validated child payloads."""
    style = _drawing_style()
    group = ComponentGroupPDF("payload")
    group.add_component(RectanglePDF((0.0, 0.0), 2.0, 3.0, 0.0, style))

    styles = {style.name: style}
    recreated = ComponentGroupPDF.create_from_dict(group.parameters, styles)

    assert recreated.generate_pdf() == group.generate_pdf()

    broken = group.parameters
    broken["ComponentGroupPDF"]["components"][0]["RectanglePDF"].pop("position")
    with pytest.raises(ValueError, match="RectanglePDF payload must include position"):
        ComponentGroupPDF.create_from_dict(broken, styles)
