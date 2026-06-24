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


@pytest.mark.condition("COMPONENT-GROUP-PAYLOAD-P2")
def test_component_group_round_trip_preserves_base_components() -> None:
    """COMPONENT-GROUP-PAYLOAD-P2: Base Component payloads hydrate without a style argument."""
    group = ComponentGroup("base")
    group.add_component(Component())

    clone = ComponentGroup.create_from_dict(group.parameters)

    assert clone.group_label == "base"
    assert [component.component_type for component in clone.components()] == ["Component"]
    assert clone.parameters == group.parameters


@pytest.mark.condition("COMPONENT-GROUP-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("payload", "exception_type", "message"),
    [
        (object(), TypeError, "ComponentGroup data must be a mapping"),
        ({}, ValueError, "ComponentGroup data must include ComponentGroup"),
        ({"ComponentGroup": object()}, TypeError, "ComponentGroup payload must be a mapping"),
        ({"ComponentGroup": {"components": []}}, ValueError, "ComponentGroup payload must include group_label"),
        ({"ComponentGroup": {"group_label": "parts"}}, ValueError, "ComponentGroup payload must include components"),
        (
            {"ComponentGroup": {"group_label": "parts", "components": "bad"}},
            TypeError,
            "ComponentGroup components must be a sequence",
        ),
        (
            {"ComponentGroup": {"group_label": "parts", "components": [object()]}},
            TypeError,
            "component group component entry must be a mapping",
        ),
        (
            {"ComponentGroup": {"group_label": "parts", "components": [{}]}},
            ValueError,
            "component group component entry must contain one component type",
        ),
        (
            {"ComponentGroup": {"group_label": "parts", "components": [{"Component": {}, "DrawingComponent": {}}]}},
            ValueError,
            "component group component entry must contain one component type",
        ),
        (
            {"ComponentGroup": {"group_label": "parts", "components": [{123: {}}]}},
            TypeError,
            "component group component type must be a string",
        ),
        (
            {"ComponentGroup": {"group_label": "parts", "components": [{"Component": object()}]}},
            TypeError,
            "component group component payload must be a mapping",
        ),
        (
            {"ComponentGroup": {"group_label": "parts", "components": [{"NotAComponent": {}}]}},
            ValueError,
            "Unsupported component group payload type",
        ),
        (
            {"ComponentGroup": {"group_label": "parts", "components": [{"PRECISION": {}}]}},
            ValueError,
            "Unsupported component group payload type",
        ),
        (
            {"ComponentGroup": {"group_label": "parts", "components": [{"Style": {}}]}},
            ValueError,
            "Unsupported component group payload type",
        ),
    ],
)
def test_component_group_hydration_rejects_malformed_payload_envelopes(
    payload: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """COMPONENT-GROUP-PAYLOAD-P2: Serialized group envelopes fail before dynamic dispatch."""
    with pytest.raises(exception_type, match=message):
        ComponentGroup.create_from_dict(payload, {})


@pytest.mark.condition("COMPONENT-GROUP-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("style_payload", "exception_type", "message"),
    [
        (object(), TypeError, "component group style payload must be a mapping"),
        ({}, ValueError, "component group style payload must contain one style type"),
        ({"DrawingStyle": {}, "TextStyle": {}}, ValueError, "component group style payload must contain one style type"),
        ({123: {}}, TypeError, "component group style type must be a string"),
        ({"DrawingStyle": object()}, TypeError, "component group style entry must be a mapping"),
        ({"DrawingStyle": {"name": object()}}, TypeError, "component group style name must be a string"),
        ({"NotAStyle": {"name": "style"}}, ValueError, "Unsupported component group payload type"),
    ],
)
def test_component_group_hydration_rejects_malformed_style_envelopes(
    style_payload: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """COMPONENT-GROUP-PAYLOAD-P2: Serialized style envelopes fail before style construction."""
    payload = {
        "ComponentGroup": {
            "group_label": "parts",
            "components": [
                {
                    "StandardDrawingComponent": {
                        "point_1": (1.0, 2.0),
                        "point_2": (3.0, 4.0),
                        "style": style_payload,
                    }
                }
            ],
        }
    }

    with pytest.raises(exception_type, match=message):
        ComponentGroup.create_from_dict(payload, {})
