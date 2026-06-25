"""Behavioral tests for SVG curve primitive factory payload envelopes."""

from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

import pytest

from InkGen.style import DrawingStyle
from InkGen.svg_generator import ArcSVG, CubicBezierSVG, QuadraticBezierSVG


def _style() -> DrawingStyle:
    """Return a unique drawing style for SVG curve factory tests."""
    return DrawingStyle(f"svg_curve_{uuid4().hex}", stroke="#000000", fill="none")


@pytest.mark.condition("SVG-CURVE-FACTORY-PAYLOAD-P2")
def test_svg_curve_factories_preserve_explicit_style_compact_payloads() -> None:
    """SVG-CURVE-FACTORY-PAYLOAD-P2: Valid compact curve payloads still hydrate."""
    style = _style()

    arc = ArcSVG.create_from_dict(
        {
            "ArcSVG": {
                "center": (1.0, 2.0),
                "radius_x": 3.0,
                "radius_y": 4.0,
                "start_angle": 15.0,
                "end_angle": 90.0,
                "rotation": 10.0,
            }
        },
        style,
    )
    quadratic = QuadraticBezierSVG.create_from_dict(
        {"QuadraticBezierSVG": {"start_point": (0.0, 0.0), "control_point": (1.0, 2.0), "end_point": (3.0, 0.0)}},
        style,
    )
    cubic = CubicBezierSVG.create_from_dict(
        {
            "CubicBezierSVG": {
                "start_point": (0.0, 0.0),
                "control_point1": (1.0, 2.0),
                "control_point2": (2.0, 2.0),
                "end_point": (3.0, 0.0),
            }
        },
        style,
    )

    assert arc.center == (1.0, 2.0)
    assert arc.radius_x == 3.0
    assert arc.rotation == 10.0
    assert quadratic.control_point == (1.0, 2.0)
    assert cubic.control_point2 == (2.0, 2.0)


@pytest.mark.condition("SVG-CURVE-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("factory", "key"),
    [
        (ArcSVG.create_from_dict, "ArcSVG"),
        (QuadraticBezierSVG.create_from_dict, "QuadraticBezierSVG"),
        (CubicBezierSVG.create_from_dict, "CubicBezierSVG"),
    ],
)
def test_svg_curve_factories_reject_malformed_payload_roots(
    factory: Callable[..., object],
    key: str,
) -> None:
    """SVG-CURVE-FACTORY-PAYLOAD-P2: Curve factory roots fail explicitly."""
    style = _style()
    cases = [
        (object(), TypeError, f"{key} data must be a mapping"),
        ({}, ValueError, f"{key} data must include {key}"),
        ({key: object()}, TypeError, f"{key} payload must be a mapping"),
    ]

    for payload, exception_type, message in cases:
        with pytest.raises(exception_type, match=message):
            factory(payload, style)


@pytest.mark.condition("SVG-CURVE-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("factory", "payload"),
    [
        (ArcSVG.create_from_dict, {"ArcSVG": {}}),
        (QuadraticBezierSVG.create_from_dict, {"QuadraticBezierSVG": {}}),
        (CubicBezierSVG.create_from_dict, {"CubicBezierSVG": {}}),
    ],
)
def test_svg_curve_factories_require_style_when_not_explicit(
    factory: Callable[..., object],
    payload: object,
) -> None:
    """SVG-CURVE-FACTORY-PAYLOAD-P2: Style fields are required without explicit style."""
    with pytest.raises(ValueError, match="style"):
        factory(payload)


@pytest.mark.condition("SVG-CURVE-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("factory", "payload", "message"),
    [
        (ArcSVG.create_from_dict, {"ArcSVG": {"radius_x": 1.0, "radius_y": 1.0, "start_angle": 0.0, "end_angle": 90.0}}, "center"),
        (ArcSVG.create_from_dict, {"ArcSVG": {"center": (0.0, 0.0), "radius_y": 1.0, "start_angle": 0.0, "end_angle": 90.0}}, "radius_x"),
        (ArcSVG.create_from_dict, {"ArcSVG": {"center": (0.0, 0.0), "radius_x": 1.0, "start_angle": 0.0, "end_angle": 90.0}}, "radius_y"),
        (ArcSVG.create_from_dict, {"ArcSVG": {"center": (0.0, 0.0), "radius_x": 1.0, "radius_y": 1.0, "end_angle": 90.0}}, "start_angle"),
        (ArcSVG.create_from_dict, {"ArcSVG": {"center": (0.0, 0.0), "radius_x": 1.0, "radius_y": 1.0, "start_angle": 0.0}}, "end_angle"),
        (
            QuadraticBezierSVG.create_from_dict,
            {"QuadraticBezierSVG": {"control_point": (1.0, 1.0), "end_point": (2.0, 0.0)}},
            "start_point",
        ),
        (
            QuadraticBezierSVG.create_from_dict,
            {"QuadraticBezierSVG": {"start_point": (0.0, 0.0), "end_point": (2.0, 0.0)}},
            "control_point",
        ),
        (
            QuadraticBezierSVG.create_from_dict,
            {"QuadraticBezierSVG": {"start_point": (0.0, 0.0), "control_point": (1.0, 1.0)}},
            "end_point",
        ),
        (
            CubicBezierSVG.create_from_dict,
            {"CubicBezierSVG": {"control_point1": (1.0, 1.0), "control_point2": (2.0, 1.0), "end_point": (3.0, 0.0)}},
            "start_point",
        ),
        (
            CubicBezierSVG.create_from_dict,
            {"CubicBezierSVG": {"start_point": (0.0, 0.0), "control_point2": (2.0, 1.0), "end_point": (3.0, 0.0)}},
            "control_point1",
        ),
        (
            CubicBezierSVG.create_from_dict,
            {"CubicBezierSVG": {"start_point": (0.0, 0.0), "control_point1": (1.0, 1.0), "end_point": (3.0, 0.0)}},
            "control_point2",
        ),
        (
            CubicBezierSVG.create_from_dict,
            {"CubicBezierSVG": {"start_point": (0.0, 0.0), "control_point1": (1.0, 1.0), "control_point2": (2.0, 1.0)}},
            "end_point",
        ),
    ],
)
def test_svg_curve_factories_reject_missing_required_fields(
    factory: Callable[..., object],
    payload: object,
    message: str,
) -> None:
    """SVG-CURVE-FACTORY-PAYLOAD-P2: Required curve fields fail explicitly."""
    with pytest.raises(ValueError, match=message):
        factory(payload, _style())
