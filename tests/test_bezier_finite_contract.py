"""Behavioral tests for finite Bezier point boundaries."""

from __future__ import annotations

from uuid import uuid4

import pytest

from InkGen.component import CubicBezier, QuadraticBezier
from InkGen.document_outputs import FlowDocument
from InkGen.drawing_components import CubicBezierDrawing, DrawingComponentGroup, OutputFormat, QuadraticBezierDrawing
from InkGen.dxf_generator import DXFDocument
from InkGen.pdf_generator import CubicBezierPDF, QuadraticBezierPDF
from InkGen.style import DrawingStyle
from InkGen.svg_generator import CubicBezierSVG, QuadraticBezierSVG


def _style() -> DrawingStyle:
    """Return a unique drawing style for Bezier finite-boundary tests."""
    return DrawingStyle(f"bezier_finite_contract_{uuid4().hex}", stroke="#000000", fill="none")


@pytest.mark.condition("BEZIER-FINITE-P2")
def test_quadratic_bezier_preserves_valid_finite_points_and_setters() -> None:
    """BEZIER-FINITE-P2: Finite quadratic points preserve public geometry."""
    bezier = QuadraticBezier((1.25, -2.5), (3.5, 4.25), (7.0, -1.0), _style())

    assert bezier.start_point == (1.25, -2.5)
    assert bezier.control_point == (3.5, 4.25)
    assert bezier.end_point == (7.0, -1.0)
    assert len(bezier.points) == 33

    bezier.start_point = (-4.0, 5.0)
    bezier.control_point = (6.0, 2.0)
    bezier.end_point = (10.0, -3.0)

    assert bezier.start_point == (-4.0, 5.0)
    assert bezier.control_point == (6.0, 2.0)
    assert bezier.end_point == (10.0, -3.0)


@pytest.mark.condition("BEZIER-FINITE-P2")
def test_cubic_bezier_preserves_valid_finite_points_and_setters() -> None:
    """BEZIER-FINITE-P2: Finite cubic points preserve public geometry."""
    bezier = CubicBezier((1.25, -2.5), (3.5, 4.25), (6.5, 8.0), (7.0, -1.0), _style())

    assert bezier.start_point == (1.25, -2.5)
    assert bezier.control_point1 == (3.5, 4.25)
    assert bezier.control_point2 == (6.5, 8.0)
    assert bezier.end_point == (7.0, -1.0)
    assert len(bezier.points) == 33

    bezier.start_point = (-4.0, 5.0)
    bezier.control_point1 = (6.0, 2.0)
    bezier.control_point2 = (8.0, 9.0)
    bezier.end_point = (10.0, -3.0)

    assert bezier.start_point == (-4.0, 5.0)
    assert bezier.control_point1 == (6.0, 2.0)
    assert bezier.control_point2 == (8.0, 9.0)
    assert bezier.end_point == (10.0, -3.0)


@pytest.mark.condition("BEZIER-FINITE-P2")
def test_quadratic_bezier_rejects_invalid_constructor_and_setter_points() -> None:
    """BEZIER-FINITE-P2: Invalid quadratic points fail without mutation."""
    style = _style()
    invalid_values = [float("nan"), float("inf"), -float("inf"), True, object(), "bad"]

    for value in invalid_values:
        with pytest.raises((TypeError, ValueError)):
            QuadraticBezier((value, 0.0), (1.0, 1.0), (2.0, 0.0), style)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            QuadraticBezier((0.0, 0.0), (value, 1.0), (2.0, 0.0), style)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            QuadraticBezier((0.0, 0.0), (1.0, 1.0), (2.0, value), style)  # type: ignore[arg-type]

    for point in [(0.0,), (0.0, 1.0, 2.0)]:
        with pytest.raises(ValueError, match="Point must contain two numeric values."):
            QuadraticBezier(point, (1.0, 1.0), (2.0, 0.0), style)  # type: ignore[arg-type]

    bezier = QuadraticBezier((0.0, 0.0), (1.0, 1.0), (2.0, 0.0), style)
    before = bezier.parameters

    for value in invalid_values:
        with pytest.raises((TypeError, ValueError)):
            bezier.start_point = (value, 0.0)  # type: ignore[assignment]
        assert bezier.parameters == before

        with pytest.raises((TypeError, ValueError)):
            bezier.control_point = (1.0, value)  # type: ignore[assignment]
        assert bezier.parameters == before

        with pytest.raises((TypeError, ValueError)):
            bezier.end_point = (value, 0.0)  # type: ignore[assignment]
        assert bezier.parameters == before

    with pytest.raises(ValueError, match="Point must contain two numeric values."):
        bezier.control_point = (1.0,)  # type: ignore[assignment]
    assert bezier.parameters == before

    with pytest.raises(ValueError, match="Point must contain two numeric values."):
        bezier.end_point = (1.0, 2.0, 3.0)  # type: ignore[assignment]
    assert bezier.parameters == before


@pytest.mark.condition("BEZIER-FINITE-P2")
def test_cubic_bezier_rejects_invalid_constructor_and_setter_points() -> None:
    """BEZIER-FINITE-P2: Invalid cubic points fail without mutation."""
    style = _style()
    invalid_values = [float("nan"), float("inf"), -float("inf"), False, object(), "bad"]

    for value in invalid_values:
        with pytest.raises((TypeError, ValueError)):
            CubicBezier((value, 0.0), (1.0, 1.0), (2.0, 2.0), (3.0, 0.0), style)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            CubicBezier((0.0, 0.0), (value, 1.0), (2.0, 2.0), (3.0, 0.0), style)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            CubicBezier((0.0, 0.0), (1.0, 1.0), (2.0, value), (3.0, 0.0), style)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            CubicBezier((0.0, 0.0), (1.0, 1.0), (2.0, 2.0), (3.0, value), style)  # type: ignore[arg-type]

    for point in [(0.0,), (0.0, 1.0, 2.0)]:
        with pytest.raises(ValueError, match="Point must contain two numeric values."):
            CubicBezier(point, (1.0, 1.0), (2.0, 2.0), (3.0, 0.0), style)  # type: ignore[arg-type]

    bezier = CubicBezier((0.0, 0.0), (1.0, 1.0), (2.0, 2.0), (3.0, 0.0), style)
    before = bezier.parameters

    for value in invalid_values:
        with pytest.raises((TypeError, ValueError)):
            bezier.start_point = (value, 0.0)  # type: ignore[assignment]
        assert bezier.parameters == before

        with pytest.raises((TypeError, ValueError)):
            bezier.control_point1 = (1.0, value)  # type: ignore[assignment]
        assert bezier.parameters == before

        with pytest.raises((TypeError, ValueError)):
            bezier.control_point2 = (value, 2.0)  # type: ignore[assignment]
        assert bezier.parameters == before

        with pytest.raises((TypeError, ValueError)):
            bezier.end_point = (3.0, value)  # type: ignore[assignment]
        assert bezier.parameters == before

    with pytest.raises(ValueError, match="Point must contain two numeric values."):
        bezier.control_point1 = (1.0,)  # type: ignore[assignment]
    assert bezier.parameters == before

    with pytest.raises(ValueError, match="Point must contain two numeric values."):
        bezier.control_point2 = (1.0, 2.0, 3.0)  # type: ignore[assignment]
    assert bezier.parameters == before


@pytest.mark.condition("BEZIER-DRAWING-GEOMETRY-P2")
def test_bezier_drawings_normalize_geometry_before_materialization() -> None:
    """BEZIER-DRAWING-GEOMETRY-P2: Neutral Bezier points normalize at construction."""
    style = _style()
    quadratic = QuadraticBezierDrawing([1, -2], [3, 4], [5, -6], style)  # type: ignore[arg-type]
    cubic = CubicBezierDrawing([1, -2], [3, 4], [5, -6], [7, 8], style)  # type: ignore[arg-type]

    assert quadratic.start_point == (1.0, -2.0)
    assert quadratic.control_point == (3.0, 4.0)
    assert quadratic.end_point == (5.0, -6.0)
    assert isinstance(quadratic.to_component(OutputFormat.SVG), QuadraticBezierSVG)
    assert isinstance(quadratic.to_component(OutputFormat.PDF), QuadraticBezierPDF)

    assert cubic.start_point == (1.0, -2.0)
    assert cubic.control_point1 == (3.0, 4.0)
    assert cubic.control_point2 == (5.0, -6.0)
    assert cubic.end_point == (7.0, 8.0)
    assert isinstance(cubic.to_component(OutputFormat.SVG), CubicBezierSVG)
    assert isinstance(cubic.to_component(OutputFormat.PDF), CubicBezierPDF)


@pytest.mark.condition("BEZIER-DRAWING-GEOMETRY-P2")
@pytest.mark.parametrize(
    ("component_type", "field", "value"),
    [
        ("quadratic", "start_point", "12"),
        ("quadratic", "control_point", [1.0]),
        ("quadratic", "end_point", [1.0, 2.0, 3.0]),
        ("quadratic", "start_point", {"x": 1.0, "y": 2.0}),
        ("quadratic", "control_point", (object(), 1.0)),
        ("quadratic", "end_point", ("x", 1.0)),
        ("quadratic", "start_point", (True, 1.0)),
        ("quadratic", "control_point", (float("nan"), 1.0)),
        ("cubic", "start_point", "12"),
        ("cubic", "control_point1", [1.0]),
        ("cubic", "control_point2", [1.0, 2.0, 3.0]),
        ("cubic", "end_point", {"x": 1.0, "y": 2.0}),
        ("cubic", "control_point1", (object(), 1.0)),
        ("cubic", "control_point2", ("x", 1.0)),
        ("cubic", "start_point", (False, 1.0)),
        ("cubic", "end_point", (float("inf"), 1.0)),
    ],
)
def test_bezier_drawings_reject_malformed_geometry_payloads(
    component_type: str,
    field: str,
    value: object,
) -> None:
    """BEZIER-DRAWING-GEOMETRY-P2: Neutral Beziers reject malformed points."""
    if component_type == "quadratic":
        kwargs = {"start_point": (1.0, -2.0), "control_point": (3.0, 4.0), "end_point": (5.0, -6.0)}
        kwargs[field] = value
        with pytest.raises((TypeError, ValueError)):
            QuadraticBezierDrawing(style=_style(), **kwargs)  # type: ignore[arg-type]
    else:
        kwargs = {
            "start_point": (1.0, -2.0),
            "control_point1": (3.0, 4.0),
            "control_point2": (5.0, -6.0),
            "end_point": (7.0, 8.0),
        }
        kwargs[field] = value
        with pytest.raises((TypeError, ValueError)):
            CubicBezierDrawing(style=_style(), **kwargs)  # type: ignore[arg-type]


@pytest.mark.condition("BEZIER-DRAWING-GEOMETRY-P2")
@pytest.mark.parametrize(
    ("component_type", "field", "value"),
    [
        ("quadratic", "start_point", "12"),
        ("quadratic", "control_point", [1.0]),
        ("quadratic", "end_point", [1.0, 2.0, 3.0]),
        ("quadratic", "start_point", {"x": 1.0, "y": 2.0}),
        ("quadratic", "control_point", (object(), 1.0)),
        ("quadratic", "end_point", ("x", 1.0)),
        ("quadratic", "start_point", (True, 1.0)),
        ("quadratic", "control_point", (float("nan"), 1.0)),
        ("cubic", "start_point", "12"),
        ("cubic", "control_point1", [1.0]),
        ("cubic", "control_point2", [1.0, 2.0, 3.0]),
        ("cubic", "end_point", {"x": 1.0, "y": 2.0}),
        ("cubic", "control_point1", (object(), 1.0)),
        ("cubic", "control_point2", ("x", 1.0)),
        ("cubic", "start_point", (False, 1.0)),
        ("cubic", "end_point", (float("inf"), 1.0)),
    ],
)
def test_flow_document_hydration_rejects_malformed_bezier_geometry_payloads(
    component_type: str,
    field: str,
    value: object,
) -> None:
    """BEZIER-DRAWING-GEOMETRY-P2: Flow documents cannot hydrate bad Beziers."""
    style = _style()
    group = DrawingComponentGroup("bezier-flow")
    if component_type == "quadratic":
        group.add_component(QuadraticBezierDrawing((1.0, -2.0), (3.0, 4.0), (5.0, -6.0), style))
    else:
        group.add_component(CubicBezierDrawing((1.0, -2.0), (3.0, 4.0), (5.0, -6.0), (7.0, 8.0), style))
    document = FlowDocument(title="Bad Bezier")
    document.add_drawing_group(group)
    payload = document.parameters
    flow_payload = payload["FlowDocument"]
    assert isinstance(flow_payload, dict)
    blocks = flow_payload["blocks"]
    assert isinstance(blocks, list)
    block_payload = blocks[0]["payload"]
    assert isinstance(block_payload, dict)
    components = block_payload["components"]
    assert isinstance(components, list)
    component_payload = components[0]["payload"]
    assert isinstance(component_payload, dict)
    component_payload[field] = value

    with pytest.raises((TypeError, ValueError)):
        FlowDocument.create_from_dict(payload, {style.name: style})


@pytest.mark.condition("BEZIER-FINITE-P2")
def test_dependent_pdf_and_dxf_paths_reject_nonfinite_bezier_geometry() -> None:
    """BEZIER-FINITE-P2: PDF and neutral-DXF Bezier paths consume finite boundaries."""
    style = _style()

    with pytest.raises(ValueError):
        QuadraticBezierPDF((0.0, 0.0), (1.0, float("nan")), (2.0, 0.0), style)
    with pytest.raises(ValueError):
        CubicBezierPDF((0.0, 0.0), (1.0, 1.0), (float("inf"), 2.0), (3.0, 0.0), style)

    group = DrawingComponentGroup("bezier_finite")
    with pytest.raises(ValueError):
        group.add_component(QuadraticBezierDrawing((0.0, 0.0), (1.0, float("nan")), (2.0, 0.0), style))
    with pytest.raises(ValueError):
        group.add_component(CubicBezierDrawing((0.0, 0.0), (1.0, 1.0), (float("inf"), 2.0), (3.0, 0.0), style))

    group.add_component(QuadraticBezierDrawing((0.0, 0.0), (1.0, 1.0), (2.0, 0.0), style))
    group.add_component(CubicBezierDrawing((0.0, 0.0), (1.0, 1.0), (2.0, 2.0), (3.0, 0.0), style))
    document = DXFDocument()
    document.add_group(group)
    assert "LWPOLYLINE" in document.to_dxf_string()
