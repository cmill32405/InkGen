"""Behavioral tests for SVG component-group factory payload envelopes."""

from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

import pytest

from InkGen.boundary import Canvas
from InkGen.style import DrawingStyle, Font, Style, TextStyle
from InkGen.svg_generator import ComponentGroupSVG, DocumentSVG, RectangleSVG, TextSVG


def _drawing_style() -> DrawingStyle:
    """Return a unique drawing style for SVG group factory contract tests."""
    return DrawingStyle(f"svg_group_draw_{uuid4().hex}", stroke="#000000", fill="none")


def _text_style() -> TextStyle:
    """Return a unique text style for SVG group factory contract tests."""
    return TextStyle(f"svg_group_text_{uuid4().hex}", Font(size=11.0))


def _group() -> tuple[ComponentGroupSVG, DrawingStyle, TextStyle]:
    """Return a valid SVG group with drawing and text children."""
    drawing_style = _drawing_style()
    text_style = _text_style()
    group = ComponentGroupSVG("payload")
    group.add_component(RectangleSVG((0.0, 0.0), 2.0, 3.0, 0.0, drawing_style))
    group.add_component(TextSVG("label", (1.0, 2.0), text_style))
    return group, drawing_style, text_style


@pytest.mark.condition("SVG-GROUP-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("payload", "exception_type", "message"),
    [
        (object(), TypeError, "ComponentGroupSVG data must be a mapping"),
        ({}, ValueError, "ComponentGroupSVG data must include ComponentGroupSVG"),
        ({"ComponentGroupSVG": object()}, TypeError, "ComponentGroupSVG payload must be a mapping"),
        ({"ComponentGroupSVG": {"components": []}}, ValueError, "ComponentGroupSVG payload must include group_label"),
        ({"ComponentGroupSVG": {"group_label": "payload"}}, ValueError, "ComponentGroupSVG payload must include components"),
        (
            {"ComponentGroupSVG": {"group_label": "payload", "components": "RectangleSVG"}},
            TypeError,
            "ComponentGroupSVG components must be a sequence",
        ),
    ],
)
def test_component_group_svg_factory_rejects_malformed_group_payloads(
    payload: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """SVG-GROUP-FACTORY-PAYLOAD-P2: Group roots and component collections fail explicitly."""
    with pytest.raises(exception_type, match=message):
        ComponentGroupSVG.create_from_dict(payload)


@pytest.mark.condition("SVG-GROUP-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("component_entry", "exception_type", "message"),
    [
        (object(), TypeError, "SVG component entry must be a mapping"),
        ({}, ValueError, "SVG component entry must contain one type"),
        (
            {
                "RectangleSVG": {"position": (0.0, 0.0), "width": 1.0, "height": 1.0, "corner_radii": 0.0},
                "TextSVG": {"text": "x", "position": (0.0, 0.0)},
            },
            ValueError,
            "SVG component entry must contain one type",
        ),
        ({1: {}}, TypeError, "SVG component type must be a string"),
        ({"RectangleSVG": object()}, TypeError, "SVG component payload must be a mapping"),
        ({"NotSVG": {}}, ValueError, "Unsupported SVG component payload type: NotSVG"),
        ({"DocumentSVG": {}}, ValueError, "Unsupported SVG component payload type: DocumentSVG"),
    ],
)
def test_component_group_svg_factory_rejects_malformed_component_entries(
    component_entry: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """SVG-GROUP-FACTORY-PAYLOAD-P2: Child component entries fail before dynamic dispatch."""
    payload = {"ComponentGroupSVG": {"group_label": "payload", "components": [component_entry]}}

    with pytest.raises(exception_type, match=message):
        ComponentGroupSVG.create_from_dict(payload)


@pytest.mark.condition("SVG-GROUP-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("style_payload", "exception_type", "message"),
    [
        (object(), TypeError, "SVG component style entry must be a mapping"),
        ({}, ValueError, "SVG component style entry must contain one type"),
        (
            {"DrawingStyle": {"name": "a"}, "TextStyle": {"name": "b"}},
            ValueError,
            "SVG component style entry must contain one type",
        ),
        ({1: {"name": "bad"}}, TypeError, "SVG component style type must be a string"),
        ({"DrawingStyle": object()}, TypeError, "SVG component style payload must be a mapping"),
        ({"DrawingStyle": {"stroke": "#000000"}}, TypeError, "SVG component style name must be a string"),
        ({"ComponentGroupSVG": {"name": "not_style"}}, ValueError, "Unsupported SVG component style payload type: ComponentGroupSVG"),
    ],
)
def test_component_group_svg_factory_rejects_malformed_style_envelopes(
    style_payload: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """SVG-GROUP-FACTORY-PAYLOAD-P2: Child style envelopes fail before style hydration."""
    component = {
        "RectangleSVG": {
            "position": (0.0, 0.0),
            "width": 1.0,
            "height": 1.0,
            "corner_radii": 0.0,
            "style": style_payload,
        }
    }
    payload = {"ComponentGroupSVG": {"group_label": "payload", "components": [component]}}

    with pytest.raises(exception_type, match=message):
        ComponentGroupSVG.create_from_dict(payload)


@pytest.mark.condition("SVG-GROUP-FACTORY-PAYLOAD-P2")
def test_component_group_svg_factory_preserves_valid_group_hydration_and_style_cache() -> None:
    """SVG-GROUP-FACTORY-PAYLOAD-P2: Valid SVG group payloads hydrate and reuse cached styles."""
    group, drawing_style, text_style = _group()
    for name in (drawing_style.name, text_style.name):
        if name in Style.style_names:
            Style.style_names.remove(name)

    style_cache: dict[str, object] = {}
    recreated = ComponentGroupSVG.create_from_dict(group.parameters, style_cache)
    recreated_again = ComponentGroupSVG.create_from_dict(group.parameters, style_cache)

    assert recreated.parameters == group.parameters
    assert recreated.generate_label() == {"payload": recreated.bbox}
    assert recreated.generate_segmentation_mask() == {"payload": recreated.convex_hull}
    recreated_text = next(component for component in recreated.components() if type(component) is TextSVG)
    recreated_text_again = next(component for component in recreated_again.components() if type(component) is TextSVG)
    assert (
        style_cache[drawing_style.name] is next(component for component in recreated.components() if type(component) is RectangleSVG).style
    )
    assert recreated_text.style is style_cache[text_style.name]
    assert recreated_text_again.style is style_cache[text_style.name]


@pytest.mark.condition("SVG-GROUP-FACTORY-PAYLOAD-P2")
def test_component_group_svg_factory_contract_remains_live_in_document_hydration() -> None:
    """SVG-GROUP-FACTORY-PAYLOAD-P2: DocumentSVG routes nested groups through the group factory."""
    drawing_style = _drawing_style()
    group = ComponentGroupSVG("payload")
    group.add_component(RectangleSVG((10.0, 10.0), 2.0, 3.0, 0.0, drawing_style))
    document = DocumentSVG(Canvas(100.0, 100.0))
    document.add_page()
    document.page(1).layer("base").add_component_group(group)
    styles = {drawing_style.name: drawing_style}

    recreated = DocumentSVG.create_from_dict(document.parameters, styles)

    assert recreated.parameters == document.parameters

    broken = deepcopy(document.parameters)
    broken["DocumentSVG"]["pages"][0]["Layers"]["layers"]["base"]["Layer"]["component_groups"][0]["ComponentGroupSVG"]["components"] = "bad"
    with pytest.raises(TypeError, match="ComponentGroupSVG components must be a sequence"):
        DocumentSVG.create_from_dict(broken, styles)
