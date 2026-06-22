"""Behavioral tests for width/height component geometry."""

from __future__ import annotations

from uuid import uuid4

import pytest

from InkGen.component import WidthHeightDrawingComponent
from InkGen.pdf_generator import RectanglePDF
from InkGen.style import DrawingStyle
from InkGen.svg_generator import RectangleSVG


def _style() -> DrawingStyle:
    """Return a unique drawing style for width/height contract tests."""
    return DrawingStyle(f"width_height_contract_{uuid4().hex}", stroke="#000000", fill="none")


@pytest.mark.condition("WIDTH-HEIGHT-P1")
def test_width_height_component_preserves_positive_and_zero_dimensions() -> None:
    """WIDTH-HEIGHT-P1: Width/height geometry preserves nonnegative dimensions."""
    component = WidthHeightDrawingComponent((5.0, 2.0), 0.0, 3.5, _style())

    assert component.position == (5.0, 2.0)
    assert component.width == 0.0
    assert component.height == 3.5
    assert component.points == [(5.0, 2.0), (5.0, 2.0), (5.0, 5.5), (5.0, 5.5)]
    assert component.bbox == [(5.0, 2.0), (5.0, 5.5)]

    component.width = 7.25
    component.height = 0.0

    assert component.width == 7.25
    assert component.height == 0.0
    assert component.point_2 == (12.25, 2.0)


@pytest.mark.condition("WIDTH-HEIGHT-P1")
def test_width_height_component_rejects_invalid_constructor_dimensions() -> None:
    """WIDTH-HEIGHT-P1: Invalid dimensions fail at construction."""
    invalid_values = [-1.0, float("nan"), float("inf"), True, object(), "wide"]

    for value in invalid_values:
        with pytest.raises((TypeError, ValueError)):
            WidthHeightDrawingComponent((10.0, 10.0), value, 2.0, _style())  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            WidthHeightDrawingComponent((10.0, 10.0), 2.0, value, _style())  # type: ignore[arg-type]


@pytest.mark.condition("WIDTH-HEIGHT-P1")
def test_width_height_setters_reject_invalid_dimensions_without_mutating() -> None:
    """WIDTH-HEIGHT-P1: Invalid width/height setter calls preserve prior geometry."""
    component = WidthHeightDrawingComponent((10.0, 10.0), 4.0, 5.0, _style())
    before = component.parameters

    for value in [-0.5, float("nan"), float("inf"), False, object(), "wide"]:
        with pytest.raises((TypeError, ValueError)):
            component.width = value  # type: ignore[assignment]
        assert component.parameters == before

        with pytest.raises((TypeError, ValueError)):
            component.height = value  # type: ignore[assignment]
        assert component.parameters == before


@pytest.mark.condition("WIDTH-HEIGHT-P1")
def test_width_height_position_mutation_preserves_dimensions() -> None:
    """WIDTH-HEIGHT-P1: Position mutation preserves validated dimensions."""
    component = WidthHeightDrawingComponent((5.0, 2.0), 4.0, 6.0, _style())

    component.position = (8.0, 3.0)

    assert component.position == (8.0, 3.0)
    assert component.width == 4.0
    assert component.height == 6.0
    assert component.point_2 == (12.0, 9.0)


@pytest.mark.condition("WIDTH-HEIGHT-P1")
def test_rectangle_renderers_consume_width_height_dimension_contract() -> None:
    """WIDTH-HEIGHT-P1: Rectangle renderers reject invalid inherited dimensions."""
    for rectangle_type in (RectangleSVG, RectanglePDF):
        with pytest.raises(ValueError):
            rectangle_type((10.0, 10.0), -1.0, 2.0, 0.0, _style())
        with pytest.raises(ValueError):
            rectangle_type((10.0, 10.0), 2.0, float("inf"), 0.0, _style())
