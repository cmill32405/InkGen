"""Behavioral tests for radial scalar validation boundaries."""

from __future__ import annotations

from uuid import uuid4

import pytest

from InkGen.component import PolarCoordinateDrawingComponent, RegularPolygonDrawingComponent
from InkGen.document_outputs import FlowDocument
from InkGen.drawing_components import CircleDrawing, DrawingComponentGroup, OutputFormat, RegularPolygonDrawing
from InkGen.dxf_generator import DXFDocument
from InkGen.pdf_generator import CirclePDF, RegularPolygonPDF
from InkGen.style import DrawingStyle
from InkGen.svg_generator import CircleSVG, RegularPolygonSVG


def _style() -> DrawingStyle:
    """Return a unique drawing style for radial scalar tests."""
    return DrawingStyle(f"radial_scalar_contract_{uuid4().hex}", stroke="#000000", fill="none")


@pytest.mark.condition("RADIAL-SCALAR-P2")
def test_circle_radius_rejects_boolean_and_nonfinite_values() -> None:
    """RADIAL-SCALAR-P2: Circle radii must be finite positive non-booleans."""
    style = _style()

    for circle_type in (CirclePDF, CircleSVG):
        with pytest.raises(TypeError):
            circle_type((0.0, 0.0), True, style)  # type: ignore[arg-type]
        for value in [float("nan"), float("inf"), -float("inf"), 0.0, -1.0, object(), "bad"]:
            with pytest.raises(ValueError):
                circle_type((0.0, 0.0), value, style)  # type: ignore[arg-type]

    circle = CircleSVG((0.0, 0.0), 2.0, style)
    before = circle.parameters

    with pytest.raises(TypeError):
        circle.radius = False  # type: ignore[assignment]
    assert circle.parameters == before

    with pytest.raises(ValueError):
        circle.radius = float("nan")
    assert circle.parameters == before


@pytest.mark.condition("RADIAL-SCALAR-P2")
def test_polar_length_angle_reject_boolean_and_nonfinite_values() -> None:
    """RADIAL-SCALAR-P2: Polar length and angle reject invalid scalar values."""
    style = _style()

    for value in [float("nan"), float("inf"), -float("inf"), True, object(), "bad"]:
        with pytest.raises((TypeError, ValueError)):
            PolarCoordinateDrawingComponent((0.0, 0.0), value, 45.0, style)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            PolarCoordinateDrawingComponent((0.0, 0.0), 5.0, value, style)  # type: ignore[arg-type]

    polar = PolarCoordinateDrawingComponent((0.0, 0.0), 5.0, 45.0, style)
    before = polar.parameters

    for value in [float("nan"), float("inf"), -float("inf"), False, object(), "bad"]:
        with pytest.raises((TypeError, ValueError)):
            polar.length = value  # type: ignore[assignment]
        assert polar.parameters == before

        with pytest.raises((TypeError, ValueError)):
            polar.angle = value  # type: ignore[assignment]
        assert polar.parameters == before


@pytest.mark.condition("RADIAL-SCALAR-P2")
def test_regular_polygon_radius_corner_and_angle_reject_invalid_scalars() -> None:
    """RADIAL-SCALAR-P2: Regular polygon scalar boundaries reject invalid inputs."""
    style = _style()

    for value in [float("nan"), float("inf"), -float("inf"), True, object(), "bad"]:
        with pytest.raises((TypeError, ValueError)):
            RegularPolygonDrawingComponent((0.0, 0.0), 3, value, style)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            RegularPolygonDrawingComponent((0.0, 0.0), 3, 10.0, style, angle=value)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            RegularPolygonDrawingComponent((0.0, 0.0), 3, 10.0, style, corner_radius=value)  # type: ignore[arg-type]

    polygon = RegularPolygonDrawingComponent((0.0, 0.0), 3, 10.0, style, angle=15.0, corner_radius=2.0)
    before = polygon.parameters

    for value in [float("nan"), float("inf"), -float("inf"), False, object(), "bad"]:
        with pytest.raises((TypeError, ValueError)):
            polygon.radius = value  # type: ignore[assignment]
        assert polygon.parameters == before

        with pytest.raises((TypeError, ValueError)):
            polygon.angle = value  # type: ignore[assignment]
        assert polygon.parameters == before

        with pytest.raises((TypeError, ValueError)):
            polygon.corner_radius = value  # type: ignore[assignment]
        assert polygon.parameters == before


@pytest.mark.condition("RADIAL-DRAWING-GEOMETRY-P2")
def test_neutral_radial_drawings_normalize_geometry_before_materialization() -> None:
    """RADIAL-DRAWING-GEOMETRY-P2: Neutral radial geometry normalizes at construction."""
    style = _style()
    circle = CircleDrawing([4, 5], 2, style)  # type: ignore[arg-type]
    polygon = RegularPolygonDrawing([5, 6], 5, 4, style, angle=-30, corner_radius=1.5)  # type: ignore[arg-type]

    assert circle.position == (4.0, 5.0)
    assert circle.radius == 2.0
    assert isinstance(circle.to_component(OutputFormat.SVG), CircleSVG)
    assert isinstance(circle.to_component(OutputFormat.PDF), CirclePDF)

    assert polygon.position == (5.0, 6.0)
    assert polygon.sides == 5
    assert polygon.radius == 4.0
    assert polygon.angle == -30.0
    assert polygon.corner_radius == 1.5
    assert isinstance(polygon.to_component(OutputFormat.SVG), RegularPolygonSVG)
    assert isinstance(polygon.to_component(OutputFormat.PDF), RegularPolygonPDF)


@pytest.mark.condition("RADIAL-DRAWING-GEOMETRY-P2")
def test_neutral_radial_drawings_preserve_boundary_values() -> None:
    """RADIAL-DRAWING-GEOMETRY-P2: Zero positions and small positive radii are valid."""
    style = _style()

    circle = CircleDrawing((0.0, 0.0), 0.5, style)
    polygon = RegularPolygonDrawing((0.0, 0.0), 3, 0.5, style)
    exact_half_corner = RegularPolygonDrawing((5.0, 6.0), 5, 9.0, style, corner_radius=4.5)

    assert circle.position == (0.0, 0.0)
    assert circle.radius == 0.5
    assert polygon.position == (0.0, 0.0)
    assert polygon.radius == 0.5
    assert exact_half_corner.corner_radius == 4.5

    with pytest.raises(ValueError, match="must not exceed half"):
        RegularPolygonDrawing((5.0, 6.0), 5, 9.0, style, corner_radius=4.6)


@pytest.mark.condition("RADIAL-DRAWING-GEOMETRY-P2")
def test_neutral_radial_drawings_normalize_coordinate_conversion_errors() -> None:
    """RADIAL-DRAWING-GEOMETRY-P2: Coordinate conversion errors use boundary errors."""
    style = _style()

    with pytest.raises(ValueError, match="CircleDrawing position must contain two numeric values"):
        CircleDrawing((object(), 1.0), 1.0, style)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="RegularPolygonDrawing position must contain two numeric values"):
        RegularPolygonDrawing((object(), 1.0), 3, 1.0, style)  # type: ignore[arg-type]


@pytest.mark.condition("RADIAL-DRAWING-GEOMETRY-P2")
@pytest.mark.parametrize(
    ("component_type", "field", "value"),
    [
        ("circle", "position", "12"),
        ("circle", "position", [1.0]),
        ("circle", "position", [1.0, 2.0, 3.0]),
        ("circle", "position", (True, 1.0)),
        ("circle", "position", (float("nan"), 1.0)),
        ("circle", "position", (-0.1, 1.0)),
        ("circle", "position", (1.0, -0.1)),
        ("circle", "radius", True),
        ("circle", "radius", object()),
        ("circle", "radius", float("inf")),
        ("circle", "radius", 0.0),
        ("circle", "radius", -0.1),
        ("polygon", "position", "12"),
        ("polygon", "position", (True, 1.0)),
        ("polygon", "position", (float("nan"), 1.0)),
        ("polygon", "position", (-0.1, 1.0)),
        ("polygon", "position", (1.0, -0.1)),
        ("polygon", "sides", True),
        ("polygon", "sides", 3.5),
        ("polygon", "sides", 2),
        ("polygon", "radius", False),
        ("polygon", "radius", float("nan")),
        ("polygon", "radius", 0.0),
        ("polygon", "angle", True),
        ("polygon", "angle", object()),
        ("polygon", "angle", float("inf")),
        ("polygon", "corner_radius", False),
        ("polygon", "corner_radius", object()),
        ("polygon", "corner_radius", -0.1),
        ("polygon", "corner_radius", 5.1),
    ],
)
def test_neutral_radial_drawings_reject_malformed_geometry_payloads(
    component_type: str,
    field: str,
    value: object,
) -> None:
    """RADIAL-DRAWING-GEOMETRY-P2: Neutral radial drawings reject malformed geometry."""
    if component_type == "circle":
        kwargs = {"position": (4.0, 5.0), "radius": 2.0}
        kwargs[field] = value
        with pytest.raises((TypeError, ValueError)):
            CircleDrawing(style=_style(), **kwargs)  # type: ignore[arg-type]
    else:
        kwargs = {"position": (5.0, 6.0), "sides": 5, "radius": 10.0, "angle": -30.0, "corner_radius": 2.0}
        kwargs[field] = value
        with pytest.raises((TypeError, ValueError)):
            RegularPolygonDrawing(style=_style(), **kwargs)  # type: ignore[arg-type]


@pytest.mark.condition("RADIAL-DRAWING-GEOMETRY-P2")
@pytest.mark.parametrize(
    ("component_type", "field", "value"),
    [
        ("circle", "position", "12"),
        ("circle", "position", (True, 1.0)),
        ("circle", "position", (float("nan"), 1.0)),
        ("circle", "position", (-0.1, 1.0)),
        ("circle", "position", (1.0, -0.1)),
        ("circle", "radius", True),
        ("circle", "radius", object()),
        ("circle", "radius", float("inf")),
        ("circle", "radius", 0.0),
        ("polygon", "position", "12"),
        ("polygon", "position", (True, 1.0)),
        ("polygon", "position", (float("nan"), 1.0)),
        ("polygon", "position", (-0.1, 1.0)),
        ("polygon", "position", (1.0, -0.1)),
        ("polygon", "sides", True),
        ("polygon", "sides", 3.5),
        ("polygon", "sides", 2),
        ("polygon", "radius", False),
        ("polygon", "radius", float("nan")),
        ("polygon", "radius", 0.0),
        ("polygon", "angle", True),
        ("polygon", "angle", object()),
        ("polygon", "angle", float("inf")),
        ("polygon", "corner_radius", False),
        ("polygon", "corner_radius", object()),
        ("polygon", "corner_radius", -0.1),
        ("polygon", "corner_radius", 5.1),
    ],
)
def test_flow_document_hydration_rejects_malformed_radial_geometry_payloads(
    component_type: str,
    field: str,
    value: object,
) -> None:
    """RADIAL-DRAWING-GEOMETRY-P2: Flow documents cannot hydrate bad radial drawings."""
    style = _style()
    group = DrawingComponentGroup("radial-flow")
    if component_type == "circle":
        group.add_component(CircleDrawing((4.0, 5.0), 2.0, style))
    else:
        group.add_component(RegularPolygonDrawing((5.0, 6.0), 5, 10.0, style, angle=-30.0, corner_radius=2.0))
    document = FlowDocument(title="Bad Radial")
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


@pytest.mark.condition("RADIAL-SCALAR-P2")
def test_neutral_radial_drawings_consume_scalar_boundaries() -> None:
    """RADIAL-SCALAR-P2: Neutral radial drawings fail before renderer output."""
    style = _style()

    with pytest.raises(TypeError):
        CircleDrawing((0.0, 0.0), True, style)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        RegularPolygonDrawing((0.0, 0.0), 3, 10.0, style, corner_radius=float("nan"))

    group = DrawingComponentGroup("radial_scalar")
    with pytest.raises(TypeError):
        group.add_component(RegularPolygonDrawing((0.0, 0.0), 3, 10.0, style, corner_radius=True))  # type: ignore[arg-type]
    group.add_component(RegularPolygonDrawing((0.0, 0.0), 3, 10.0, style))
    document = DXFDocument()
    document.add_group(group)
    assert "LWPOLYLINE" in document.to_dxf_string()


@pytest.mark.condition("RADIAL-SCALAR-P2")
def test_valid_radial_scalars_remain_supported() -> None:
    """RADIAL-SCALAR-P2: Valid finite radial scalars preserve behavior."""
    style = _style()

    circle = CircleSVG((1.0, 2.0), 3.5, style)
    assert circle.radius == 3.5
    circle.radius = 4.25
    assert circle.radius == 4.25
    circle.radius = 0.5
    assert circle.radius == 0.5
    before = circle.parameters

    with pytest.raises(ValueError):
        circle.radius = -1.0
    assert circle.parameters == before

    polygon = RegularPolygonPDF((10.0, 10.0), 5, 8.0, style, angle=-30.0, corner_radius=2.5)
    assert polygon.sides == 5
    assert polygon.radius == pytest.approx(8.0, abs=1e-3)
    assert polygon.angle == pytest.approx(-30.0, abs=2e-3)
    assert polygon.corner_radius == 2.5
