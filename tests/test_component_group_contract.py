"""Behavioral tests for base component-group contracts."""

from __future__ import annotations

from uuid import uuid4

import pytest

from InkGen.component import Component, ComponentGroup, DrawingComponent, StandardDrawingComponent, WidthHeightDrawingComponent
from InkGen.errors import InvalidComponentID
from InkGen.style import DrawingStyle


def _style() -> DrawingStyle:
    """Return a unique drawing style for component-group contract tests."""
    return DrawingStyle(f"component_group_contract_{uuid4().hex}", stroke="#000000", fill="none")


@pytest.mark.condition("COMPONENT-GROUP-P1")
def test_component_group_preserves_valid_components_in_insertion_order() -> None:
    """COMPONENT-GROUP-P1: Groups retain valid components by id and insertion order."""
    style = _style()
    base = Component()
    drawing = DrawingComponent(style)
    rectangle = WidthHeightDrawingComponent((1.0, 2.0), 3.0, 4.0, style)
    group = ComponentGroup("parts")

    group.add_component(base)
    group.add_component(drawing)
    group.add_component(rectangle)

    assert list(group.components()) == [base, drawing, rectangle]
    assert group.get_component(base.id) is base
    assert group.get_component(drawing.id) is drawing
    assert group.get_component(rectangle.id) is rectangle
    assert group.parameters == {
        "ComponentGroup": {
            "group_label": "parts",
            "components": [base.parameters, drawing.parameters, rectangle.parameters],
        }
    }


@pytest.mark.condition("COMPONENT-GROUP-P1")
def test_component_group_rejects_invalid_components_without_mutating_group() -> None:
    """COMPONENT-GROUP-P1: Invalid add attempts fail instead of silent omission."""
    group = ComponentGroup("parts")
    first = Component()
    group.add_component(first)

    for invalid_component in [object(), None, "not-a-component"]:
        with pytest.raises(TypeError, match="InkGen Component"):
            group.add_component(invalid_component)  # type: ignore[arg-type]

    assert list(group.components()) == [first]


@pytest.mark.condition("COMPONENT-GROUP-P1")
def test_component_group_lookup_and_removal_fail_loudly_for_missing_ids() -> None:
    """COMPONENT-GROUP-P1: Missing component ids raise project exceptions."""
    group = ComponentGroup("parts")
    component = Component()
    group.add_component(component)

    with pytest.raises(InvalidComponentID):
        group.get_component(component.id + 1000)

    group.remove_component(component.id)
    assert list(group.components()) == []

    with pytest.raises(InvalidComponentID):
        group.remove_component(component.id)


@pytest.mark.condition("COMPONENT-GROUP-P1")
def test_component_group_geometry_aggregates_only_component_points() -> None:
    """COMPONENT-GROUP-P1: Group geometry aggregates drawable component points."""
    style = _style()
    group = ComponentGroup("geometry")
    group.add_component(Component())
    group.add_component(StandardDrawingComponent((1.0, 2.0), (3.0, 4.0), style))
    group.add_component(WidthHeightDrawingComponent((5.0, 6.0), 2.0, 3.0, style))

    assert group.points == [
        (1.0, 2.0),
        (3.0, 4.0),
        (5.0, 6.0),
        (7.0, 6.0),
        (7.0, 9.0),
        (5.0, 9.0),
    ]
    assert group.bbox == ((1.0, 2.0), (7.0, 9.0))
    assert set(group.convex_hull) == {(1.0, 2.0), (7.0, 6.0), (7.0, 9.0), (5.0, 9.0)}


@pytest.mark.condition("COMPONENT-GROUP-P1")
def test_component_group_round_trip_preserves_label_order_and_styles() -> None:
    """COMPONENT-GROUP-P1: Serialized component groups hydrate deterministically."""
    style = _style()
    group = ComponentGroup("round_trip")
    group.add_component(StandardDrawingComponent((1.0, 2.0), (3.0, 4.0), style))
    group.add_component(WidthHeightDrawingComponent((5.0, 6.0), 2.0, 3.0, style))

    clone = ComponentGroup.create_from_dict(group.parameters, {style.name: style})

    assert clone.group_label == "round_trip"
    assert [component.component_type for component in clone.components()] == [
        "StandardDrawingComponent",
        "WidthHeightDrawingComponent",
    ]
    assert clone.parameters == group.parameters
