"""Layer component-group contract tests."""

from __future__ import annotations

from uuid import uuid4

import pytest

from InkGen.boundary import Canvas
from InkGen.component import ComponentGroup, WidthHeightDrawingComponent
from InkGen.document import Layer
from InkGen.errors import InvalidComponentGroupID
from InkGen.pdf_generator import DocumentPDF
from InkGen.style import DrawingStyle, Style
from InkGen.svg_generator import DocumentSVG


def _style() -> DrawingStyle:
    """Return a unique drawing style for layer group tests."""
    return DrawingStyle(name=f"layer_group_{uuid4().hex}", stroke="#000000", fill="none")


def _group(label: str, x: float) -> ComponentGroup:
    """Return a component group inside the layer contract canvas."""
    group = ComponentGroup(label)
    group.add_component(WidthHeightDrawingComponent((x, 10.0), 6.0, 4.0, _style()))
    return group


def _distinct_label(label: str) -> str:
    """Return an equal but non-identical label string."""
    return ("_" + label)[1:]


def _release_group_style_names(layer: Layer) -> None:
    """Remove this test layer's generated style names before hydration."""
    for group in layer.groups():
        for component in group.components():
            style_name = component.style.name
            if style_name in Style.style_names:
                Style.style_names.remove(style_name)


@pytest.mark.condition("LAYER-GROUP-P2")
def test_layer_groups_returns_all_groups_in_insertion_order() -> None:
    """LAYER-GROUP-P2: Complete traversal preserves repeated labels and insertion order."""
    layer = Layer("base", Canvas(100.0, 80.0))
    first_label = _distinct_label("Repeat")
    second_label = _distinct_label("Repeat")
    first = _group(first_label, 10.0)
    second = _group(second_label, 30.0)

    layer.add_component_group(first)
    layer.add_component_group(second)

    assert first.group_label == second.group_label
    assert first.group_label is not second.group_label
    assert layer.groups() == (first, second)
    assert layer.group(first.group_id) is first
    assert layer.group(second.group_id) is second
    assert layer.component_groups == {"Repeat": second.group_id}


@pytest.mark.condition("LAYER-GROUP-P2")
def test_layer_remove_by_id_keeps_duplicate_label_lookup_live() -> None:
    """LAYER-GROUP-P2: Removing one duplicate by id keeps the remaining label addressable."""
    layer = Layer("base", Canvas(100.0, 80.0))
    first = _group(_distinct_label("Repeat"), 10.0)
    second = _group(_distinct_label("Repeat"), 30.0)
    layer.add_component_group(first)
    layer.add_component_group(second)

    layer.remove_component_group(first.group_id)

    assert layer.groups() == (second,)
    assert layer.component_groups == {"Repeat": second.group_id}
    assert layer.group(layer.component_groups["Repeat"]) is second


@pytest.mark.condition("LAYER-GROUP-P2")
def test_layer_remove_by_label_restores_previous_duplicate_lookup() -> None:
    """LAYER-GROUP-P2: Label removal deletes the current lookup target and restores a prior duplicate."""
    layer = Layer("base", Canvas(100.0, 80.0))
    first = _group(_distinct_label("Repeat"), 10.0)
    second = _group(_distinct_label("Repeat"), 30.0)
    layer.add_component_group(first)
    layer.add_component_group(second)

    layer.remove_component_group("Repeat")

    assert layer.groups() == (first,)
    assert layer.component_groups == {"Repeat": first.group_id}
    assert layer.group(layer.component_groups["Repeat"]) is first


@pytest.mark.condition("LAYER-GROUP-P2")
def test_layer_remove_last_duplicate_deletes_label_lookup() -> None:
    """LAYER-GROUP-P2: Removing the last duplicate clears the label lookup and rejects stale labels."""
    layer = Layer("base", Canvas(100.0, 80.0))
    alpha = _group("Alpha", 30.0)
    group = _group("Repeat", 10.0)
    zeta = _group("Zeta", 50.0)
    layer.add_component_group(alpha)
    layer.add_component_group(group)
    layer.add_component_group(zeta)

    layer.remove_component_group("Repeat")

    assert layer.groups() == (alpha, zeta)
    assert "Repeat" not in layer.component_groups
    assert layer.component_groups == {"Alpha": alpha.group_id, "Zeta": zeta.group_id}
    with pytest.raises(InvalidComponentGroupID):
        layer.remove_component_group("Repeat")


@pytest.mark.condition("LAYER-GROUP-P2")
def test_layer_remove_rejects_invalid_integer_id_without_mutating_groups() -> None:
    """LAYER-GROUP-P2: Unknown integer ids fail at the layer boundary without changing stored groups."""
    layer = Layer("base", Canvas(100.0, 80.0))
    group = _group("Known", 10.0)
    layer.add_component_group(group)

    with pytest.raises(InvalidComponentGroupID):
        layer.remove_component_group(group.group_id + 999)

    assert layer.groups() == (group,)
    assert layer.component_groups == {"Known": group.group_id}


@pytest.mark.condition("LAYER-GROUP-LOOKUP-P2")
def test_layer_component_groups_returns_lookup_snapshot() -> None:
    """LAYER-GROUP-LOOKUP-P2: Returned label lookups cannot mutate layer state."""
    layer = Layer("base", Canvas(100.0, 80.0))
    first = _group("Known", 10.0)
    second = _group("Other", 30.0)
    layer.add_component_group(first)
    layer.add_component_group(second)

    lookup = layer.component_groups
    lookup.clear()
    lookup["Injected"] = first.group_id + 999

    assert layer.component_groups == {"Known": first.group_id, "Other": second.group_id}
    assert layer.groups() == (first, second)
    assert layer.group(first.group_id) is first

    layer.remove_component_group("Known")
    assert layer.component_groups == {"Other": second.group_id}
    assert layer.groups() == (second,)


@pytest.mark.condition("LAYER-GROUP-P2")
def test_layer_serialization_preserves_repeated_label_groups() -> None:
    """LAYER-GROUP-P2: Layer parameters round trip repeated label groups as distinct entries."""
    layer = Layer("base", Canvas(100.0, 80.0))
    layer.add_component_group(_group("Repeat", 10.0))
    layer.add_component_group(_group("Repeat", 30.0))

    _release_group_style_names(layer)
    clone = Layer.create_from_dict(layer.parameters, {})

    assert [group.group_label for group in clone.groups()] == ["Repeat", "Repeat"]
    assert len(clone.groups()) == 2
    assert clone.component_groups["Repeat"] == clone.groups()[-1].group_id


@pytest.mark.condition("LAYER-GROUP-P2")
def test_document_renderers_use_public_layer_group_contract() -> None:
    """LAYER-GROUP-P2: SVG and PDF document helpers consume the complete public group traversal contract."""
    layer = Layer("base", Canvas(100.0, 80.0))
    first = _group("Repeat", 10.0)
    second = _group("Repeat", 30.0)
    layer.add_component_group(first)
    layer.add_component_group(second)

    assert tuple(DocumentSVG._iter_layer_groups(layer)) == layer.groups()
    assert DocumentPDF._iter_layer_groups(layer) == layer.groups()
    assert DocumentPDF._iter_layer_groups(layer, sort=True) == tuple(
        sorted(layer.groups(), key=lambda group: (group.group_label, group.group_id))
    )
