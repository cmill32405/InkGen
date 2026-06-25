"""Behavioral tests for finite arc input boundaries."""

from __future__ import annotations

from uuid import uuid4

import pytest

from InkGen.component import Arc
from InkGen.document_outputs import FlowDocument
from InkGen.drawing_components import ArcDrawing, DrawingComponentGroup, OutputFormat
from InkGen.dxf_generator import DXFDocument
from InkGen.pdf_generator import ArcPDF
from InkGen.style import DrawingStyle
from InkGen.svg_generator import ArcSVG


def _style() -> DrawingStyle:
    """Return a unique drawing style for arc finite-boundary tests."""
    return DrawingStyle(f"arc_finite_contract_{uuid4().hex}", stroke="#000000", fill="none")


@pytest.mark.condition("ARC-FINITE-P2")
def test_arc_preserves_valid_finite_geometry_and_setters() -> None:
    """ARC-FINITE-P2: Finite arc inputs preserve public geometry."""
    arc = Arc((1.25, -2.5), 3.5, 4.25, -30.0, 120.0, _style(), rotation=15.0)

    assert arc.center == (1.25, -2.5)
    assert arc.radius_x == 3.5
    assert arc.radius_y == 4.25
    assert arc.start_angle == -30.0
    assert arc.end_angle == 120.0
    assert arc.rotation == 15.0
    assert len(arc.points) == 33

    arc.center = (-4.0, 5.0)
    arc.radius_x = 6.0
    arc.radius_y = 2.0
    arc.start_angle = 10.0
    arc.end_angle = 20.0
    arc.rotation = -45.0

    assert arc.center == (-4.0, 5.0)
    assert arc.radius_x == 6.0
    assert arc.radius_y == 2.0
    assert arc.start_angle == 10.0
    assert arc.end_angle == 20.0
    assert arc.rotation == -45.0


@pytest.mark.condition("ARC-FINITE-P2")
def test_arc_rejects_invalid_constructor_boundaries() -> None:
    """ARC-FINITE-P2: Non-finite and nonnumeric arc constructor inputs fail."""
    style = _style()
    invalid_values = [float("nan"), float("inf"), -float("inf"), True, object(), "angle"]

    for value in invalid_values:
        with pytest.raises((TypeError, ValueError)):
            Arc((value, 0.0), 1.0, 1.0, 0.0, 90.0, style)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            Arc((0.0, value), 1.0, 1.0, 0.0, 90.0, style)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            Arc((0.0, 0.0), value, 1.0, 0.0, 90.0, style)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            Arc((0.0, 0.0), 1.0, value, 0.0, 90.0, style)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            Arc((0.0, 0.0), 1.0, 1.0, value, 90.0, style)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            Arc((0.0, 0.0), 1.0, 1.0, 0.0, value, style)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            Arc((0.0, 0.0), 1.0, 1.0, 0.0, 90.0, style, rotation=value)  # type: ignore[arg-type]

    with pytest.raises(ValueError):
        Arc((0.0, 0.0), 0.0, 1.0, 0.0, 90.0, style)
    with pytest.raises(ValueError):
        Arc((0.0, 0.0), 1.0, -0.5, 0.0, 90.0, style)
    with pytest.raises(ValueError, match="Point must contain two numeric values."):
        Arc((0.0,), 1.0, 1.0, 0.0, 90.0, style)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="Point must contain two numeric values."):
        Arc((0.0, 1.0, 2.0), 1.0, 1.0, 0.0, 90.0, style)  # type: ignore[arg-type]


@pytest.mark.condition("ARC-FINITE-P2")
def test_arc_setters_reject_invalid_inputs_without_mutating() -> None:
    """ARC-FINITE-P2: Rejected arc setter inputs preserve prior state."""
    arc = Arc((0.0, 0.0), 2.0, 3.0, 0.0, 90.0, _style(), rotation=5.0)
    before = arc.parameters
    invalid_values = [float("nan"), float("inf"), -float("inf"), False, object(), "bad"]

    for value in invalid_values:
        with pytest.raises((TypeError, ValueError)):
            arc.center = (value, 0.0)  # type: ignore[assignment]
        assert arc.parameters == before

        with pytest.raises((TypeError, ValueError)):
            arc.radius_x = value  # type: ignore[assignment]
        assert arc.parameters == before

        with pytest.raises((TypeError, ValueError)):
            arc.radius_y = value  # type: ignore[assignment]
        assert arc.parameters == before

        with pytest.raises((TypeError, ValueError)):
            arc.start_angle = value  # type: ignore[assignment]
        assert arc.parameters == before

        with pytest.raises((TypeError, ValueError)):
            arc.end_angle = value  # type: ignore[assignment]
        assert arc.parameters == before

        with pytest.raises((TypeError, ValueError)):
            arc.rotation = value  # type: ignore[assignment]
        assert arc.parameters == before

    with pytest.raises(ValueError, match="Point must contain two numeric values."):
        arc.center = (0.0,)  # type: ignore[assignment]
    assert arc.parameters == before

    with pytest.raises(ValueError, match="Point must contain two numeric values."):
        arc.center = (0.0, 1.0, 2.0)  # type: ignore[assignment]
    assert arc.parameters == before


@pytest.mark.condition("ARC-DRAWING-GEOMETRY-P2")
def test_arc_drawing_normalizes_geometry_before_materialization() -> None:
    """ARC-DRAWING-GEOMETRY-P2: Neutral arc geometry normalizes at construction."""
    style = _style()
    drawing = ArcDrawing([1, -2], 3, 4, -30, 120, style, rotation=15)  # type: ignore[arg-type]

    assert drawing.center == (1.0, -2.0)
    assert drawing.radius_x == 3.0
    assert drawing.radius_y == 4.0
    assert drawing.start_angle == -30.0
    assert drawing.end_angle == 120.0
    assert drawing.rotation == 15.0
    assert isinstance(drawing.to_component(OutputFormat.SVG), ArcSVG)
    assert isinstance(drawing.to_component(OutputFormat.PDF), ArcPDF)


@pytest.mark.condition("ARC-DRAWING-GEOMETRY-P2")
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("center", "12"),
        ("center", [1.0]),
        ("center", [1.0, 2.0, 3.0]),
        ("center", {"x": 1.0, "y": 2.0}),
        ("center", (object(), 1.0)),
        ("center", ("x", 1.0)),
        ("center", (True, 1.0)),
        ("center", (float("nan"), 1.0)),
        ("radius_x", True),
        ("radius_y", False),
        ("radius_x", object()),
        ("radius_y", "wide"),
        ("radius_x", float("inf")),
        ("radius_y", float("nan")),
        ("radius_x", 0.0),
        ("radius_y", -0.1),
        ("start_angle", True),
        ("end_angle", object()),
        ("rotation", "spin"),
        ("start_angle", float("inf")),
        ("end_angle", float("nan")),
        ("rotation", -float("inf")),
    ],
)
def test_arc_drawing_rejects_malformed_geometry_payloads(field: str, value: object) -> None:
    """ARC-DRAWING-GEOMETRY-P2: Neutral arcs reject malformed geometry payloads."""
    kwargs = {
        "center": (1.0, -2.0),
        "radius_x": 3.0,
        "radius_y": 4.0,
        "start_angle": -30.0,
        "end_angle": 120.0,
        "rotation": 15.0,
    }
    kwargs[field] = value

    with pytest.raises((TypeError, ValueError)):
        ArcDrawing(style=_style(), **kwargs)  # type: ignore[arg-type]


@pytest.mark.condition("ARC-DRAWING-GEOMETRY-P2")
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("center", "12"),
        ("center", [1.0]),
        ("center", [1.0, 2.0, 3.0]),
        ("center", {"x": 1.0, "y": 2.0}),
        ("center", (object(), 1.0)),
        ("center", ("x", 1.0)),
        ("center", (True, 1.0)),
        ("center", (float("nan"), 1.0)),
        ("radius_x", True),
        ("radius_y", False),
        ("radius_x", object()),
        ("radius_y", "wide"),
        ("radius_x", float("inf")),
        ("radius_y", float("nan")),
        ("radius_x", 0.0),
        ("radius_y", -0.1),
        ("start_angle", True),
        ("end_angle", object()),
        ("rotation", "spin"),
        ("start_angle", float("inf")),
        ("end_angle", float("nan")),
        ("rotation", -float("inf")),
    ],
)
def test_flow_document_hydration_rejects_malformed_arc_geometry_payloads(field: str, value: object) -> None:
    """ARC-DRAWING-GEOMETRY-P2: Flow documents cannot hydrate bad arc geometry."""
    style = _style()
    group = DrawingComponentGroup("arc-flow")
    group.add_component(ArcDrawing((1.0, -2.0), 3.0, 4.0, -30.0, 120.0, style, rotation=15.0))
    document = FlowDocument(title="Bad Arc")
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


@pytest.mark.condition("ARC-FINITE-P2")
def test_arc_dependent_pdf_and_dxf_paths_reject_nonfinite_geometry() -> None:
    """ARC-FINITE-P2: PDF and neutral-DXF arc paths consume finite boundaries."""
    with pytest.raises(ValueError):
        ArcPDF((0.0, 0.0), 1.0, 1.0, float("nan"), 90.0, _style())

    group = DrawingComponentGroup("arc_finite")
    with pytest.raises(ValueError):
        group.add_component(ArcDrawing((0.0, 0.0), 1.0, float("inf"), 0.0, 90.0, _style()))

    group.add_component(ArcDrawing((0.0, 0.0), 1.0, 1.0, 0.0, 90.0, _style()))
    document = DXFDocument()
    document.add_group(group)
    assert "LWPOLYLINE" in document.to_dxf_string()
