"""Behavioral tests for finite arc input boundaries."""

from __future__ import annotations

from uuid import uuid4

import pytest

from InkGen.component import Arc
from InkGen.drawing_components import ArcDrawing, DrawingComponentGroup
from InkGen.dxf_generator import DXFDocument
from InkGen.pdf_generator import ArcPDF
from InkGen.style import DrawingStyle


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


@pytest.mark.condition("ARC-FINITE-P2")
def test_arc_dependent_pdf_and_dxf_paths_reject_nonfinite_geometry() -> None:
    """ARC-FINITE-P2: PDF and neutral-DXF arc paths consume finite boundaries."""
    with pytest.raises(ValueError):
        ArcPDF((0.0, 0.0), 1.0, 1.0, float("nan"), 90.0, _style())

    group = DrawingComponentGroup("arc_finite")
    group.add_component(ArcDrawing((0.0, 0.0), 1.0, float("inf"), 0.0, 90.0, _style()))
    document = DXFDocument()

    with pytest.raises(ValueError):
        document.add_group(group)
