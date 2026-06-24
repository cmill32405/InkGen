"""Behavioral tests for specialized component factory payload envelopes."""

from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

import pytest

from InkGen.component import (
    Arc,
    CubicBezier,
    Path,
    PathCommand,
    PolarCoordinateDrawingComponent,
    PolygonalDrawingComponent,
    QuadraticBezier,
    RegularPolygonDrawingComponent,
)
from InkGen.style import DrawingStyle


def _style() -> DrawingStyle:
    """Return a unique drawing style for specialized factory contract tests."""
    return DrawingStyle(f"specialized_factory_{uuid4().hex}", stroke="#000000", fill="none")


@pytest.mark.condition("SPECIALIZED-COMPONENT-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("factory", "key"),
    [
        (PolarCoordinateDrawingComponent.create_from_dict, "PolarCoordinateDrawingComponent"),
        (PolygonalDrawingComponent.create_from_dict, "PolygonalDrawingComponent"),
        (RegularPolygonDrawingComponent.create_from_dict, "RegularPolygonDrawingComponent"),
        (Arc.create_from_dict, "Arc"),
        (QuadraticBezier.create_from_dict, "QuadraticBezier"),
        (CubicBezier.create_from_dict, "CubicBezier"),
        (Path.create_from_dict, "Path"),
    ],
)
def test_specialized_component_factories_reject_malformed_payload_roots(
    factory: Callable[..., object],
    key: str,
) -> None:
    """SPECIALIZED-COMPONENT-FACTORY-PAYLOAD-P2: Factory roots fail explicitly."""
    style = _style()
    cases = [
        (object(), TypeError, f"{key} data must be a mapping"),
        ({}, ValueError, f"{key} data must include {key}"),
        ({key: object()}, TypeError, f"{key} payload must be a mapping"),
    ]

    for payload, exception_type, message in cases:
        with pytest.raises(exception_type, match=message):
            factory(payload, style)


@pytest.mark.condition("SPECIALIZED-COMPONENT-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("factory", "payload", "message"),
    [
        (
            PolarCoordinateDrawingComponent.create_from_dict,
            {"PolarCoordinateDrawingComponent": {"position": (0.0, 0.0), "angle": 0.0}},
            "PolarCoordinateDrawingComponent payload must include length",
        ),
        (
            PolarCoordinateDrawingComponent.create_from_dict,
            {"PolarCoordinateDrawingComponent": {"position": (0.0, 0.0), "length": 1.0}},
            "PolarCoordinateDrawingComponent payload must include angle",
        ),
        (
            PolygonalDrawingComponent.create_from_dict,
            {"PolygonalDrawingComponent": {}},
            "PolygonalDrawingComponent payload must include points",
        ),
        (
            RegularPolygonDrawingComponent.create_from_dict,
            {"RegularPolygonDrawingComponent": {"position": (0.0, 0.0), "sides": 3, "radius": 1.0, "angle": 0.0}},
            "RegularPolygonDrawingComponent payload must include corner_radius",
        ),
        (
            Arc.create_from_dict,
            {"Arc": {"center": (0.0, 0.0), "radius_x": 1.0, "radius_y": 1.0, "start_angle": 0.0}},
            "Arc payload must include end_angle",
        ),
        (
            QuadraticBezier.create_from_dict,
            {"QuadraticBezier": {"start_point": (0.0, 0.0), "control_point": (1.0, 1.0)}},
            "QuadraticBezier payload must include end_point",
        ),
        (
            CubicBezier.create_from_dict,
            {
                "CubicBezier": {
                    "start_point": (0.0, 0.0),
                    "control_point1": (1.0, 1.0),
                    "end_point": (3.0, 0.0),
                }
            },
            "CubicBezier payload must include control_point2",
        ),
    ],
)
def test_specialized_component_factories_reject_missing_required_fields(
    factory: Callable[..., object],
    payload: object,
    message: str,
) -> None:
    """SPECIALIZED-COMPONENT-FACTORY-PAYLOAD-P2: Required fields fail at the factory boundary."""
    with pytest.raises(ValueError, match=message):
        factory(payload, _style())


@pytest.mark.condition("SPECIALIZED-COMPONENT-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("factory", "payload", "message"),
    [
        (PolarCoordinateDrawingComponent.create_from_dict, {"PolarCoordinateDrawingComponent": {}}, "style"),
        (PolygonalDrawingComponent.create_from_dict, {"PolygonalDrawingComponent": {}}, "style"),
        (RegularPolygonDrawingComponent.create_from_dict, {"RegularPolygonDrawingComponent": {}}, "style"),
        (Arc.create_from_dict, {"Arc": {}}, "style"),
        (QuadraticBezier.create_from_dict, {"QuadraticBezier": {}}, "style"),
        (CubicBezier.create_from_dict, {"CubicBezier": {}}, "style"),
        (Path.create_from_dict, {"Path": {}}, "style"),
    ],
)
def test_specialized_component_factories_require_style_when_not_explicit(
    factory: Callable[..., object],
    payload: object,
    message: str,
) -> None:
    """SPECIALIZED-COMPONENT-FACTORY-PAYLOAD-P2: Style fields are required without an explicit style."""
    with pytest.raises(ValueError, match=message):
        factory(payload)


@pytest.mark.condition("SPECIALIZED-COMPONENT-FACTORY-PAYLOAD-P2")
def test_specialized_component_factories_preserve_explicit_style_compact_payloads() -> None:
    """SPECIALIZED-COMPONENT-FACTORY-PAYLOAD-P2: Explicit styles still allow compact payloads."""
    style = _style()

    polar = PolarCoordinateDrawingComponent.create_from_dict(
        {"PolarCoordinateDrawingComponent": {"position": (0.0, 0.0), "length": 1.0, "angle": 0.0}},
        style,
    )
    polygonal = PolygonalDrawingComponent.create_from_dict(
        {"PolygonalDrawingComponent": {"points": [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]}},
        style,
    )
    regular = RegularPolygonDrawingComponent.create_from_dict(
        {"RegularPolygonDrawingComponent": {"position": (0.0, 0.0), "sides": 3, "radius": 1.0, "angle": 0.0, "corner_radius": 0.0}},
        style,
    )
    arc = Arc.create_from_dict(
        {"Arc": {"center": (0.0, 0.0), "radius_x": 1.0, "radius_y": 1.0, "start_angle": 0.0, "end_angle": 90.0}},
        style,
    )
    quadratic = QuadraticBezier.create_from_dict(
        {"QuadraticBezier": {"start_point": (0.0, 0.0), "control_point": (1.0, 1.0), "end_point": (2.0, 0.0)}},
        style,
    )
    cubic = CubicBezier.create_from_dict(
        {
            "CubicBezier": {
                "start_point": (0.0, 0.0),
                "control_point1": (1.0, 1.0),
                "control_point2": (2.0, 1.0),
                "end_point": (3.0, 0.0),
            }
        },
        style,
    )
    path = Path.create_from_dict(
        {"Path": {"commands": [PathCommand("M", [(0.0, 0.0)]).parameters]}},
        style,
    )

    assert polar.length == 1.0
    assert len(polygonal.points) == 3
    assert regular.sides == 3
    assert arc.radius_x == 1.0
    assert arc.rotation == 0.0
    assert quadratic.end_point == (2.0, 0.0)
    assert cubic.end_point == (3.0, 0.0)
    assert path.commands[0].type == "M"
