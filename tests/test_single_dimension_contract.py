"""Behavioral tests for single-dimension component geometry."""

from __future__ import annotations

from uuid import uuid4

import pytest

from InkGen.component import SingleDimensionDrawingComponent
from InkGen.style import DrawingStyle
from InkGen.svg_generator import CircleSVG


def _style() -> DrawingStyle:
    """Return a unique drawing style for single-dimension contract tests."""
    return DrawingStyle(f"single_dimension_contract_{uuid4().hex}", stroke="#000000", fill="none")


@pytest.mark.condition("SINGLE-DIM-P1")
def test_single_dimension_size_updates_asymmetric_position_diagonal() -> None:
    """SINGLE-DIM-P1: Size mutation preserves x+size and y+size diagonal geometry."""
    component = SingleDimensionDrawingComponent((5.0, 2.0), 10.0, _style())

    component.size = 7.5

    assert component.position == (5.0, 2.0)
    assert component.size == 7.5
    assert component.point_1 == (5.0, 2.0)
    assert component.point_2 == (12.5, 9.5)
    assert component.points == [(5.0, 2.0), (12.5, 9.5)]
    assert component.bbox == [(5.0, 2.0), (12.5, 9.5)]
    assert component.convex_hull == [(5.0, 2.0), (12.5, 9.5)]


@pytest.mark.condition("SINGLE-DIM-P1")
def test_single_dimension_position_updates_preserve_size_on_asymmetric_coordinates() -> None:
    """SINGLE-DIM-P1: Position mutation preserves size without square-axis drift."""
    component = SingleDimensionDrawingComponent((5.0, 2.0), 10.0, _style())

    component.position = (8.0, 3.0)

    assert component.size == 10.0
    assert component.point_1 == (8.0, 3.0)
    assert component.point_2 == (18.0, 13.0)


@pytest.mark.condition("SINGLE-DIM-P1")
def test_single_dimension_parameters_round_trip_after_size_mutation() -> None:
    """SINGLE-DIM-P1: Serialized size remains deterministic after mutation."""
    style = _style()
    component = SingleDimensionDrawingComponent((5.0, 2.0), 10.0, style)
    component.size = 7.5

    clone = SingleDimensionDrawingComponent.create_from_dict(component.parameters, style)

    assert clone.parameters == component.parameters
    assert clone.point_2 == (12.5, 9.5)


@pytest.mark.condition("SINGLE-DIM-P1")
def test_circle_radius_setter_preserves_hidden_single_dimension_diagonal() -> None:
    """SINGLE-DIM-P1: Circle radius mutation keeps inherited point geometry coherent."""
    circle = CircleSVG((5.0, 2.0), 10.0, _style())

    circle.radius = 7.5

    assert circle.radius == 7.5
    assert circle.position == (5.0, 2.0)
    assert circle.point_2 == (12.5, 9.5)
