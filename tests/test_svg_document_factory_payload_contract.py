"""Behavioral tests for SVG document factory payload envelopes."""

from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

import pytest

from InkGen.boundary import Canvas
from InkGen.component import ComponentGroup, WidthHeightDrawingComponent
from InkGen.style import DrawingStyle, Style
from InkGen.svg_generator import ComponentGroupSVG, DocumentSVG, RectangleSVG


def _drawing_style() -> DrawingStyle:
    """Return a unique drawing style for SVG document factory contract tests."""
    return DrawingStyle(f"svg_document_factory_{uuid4().hex}", stroke="#000000", fill="none")


def _document() -> tuple[DocumentSVG, DrawingStyle]:
    """Return a valid one-page SVG document with one layer and one group."""
    style = _drawing_style()
    document = DocumentSVG(Canvas(100.0, 100.0))
    document.add_page()
    group = ComponentGroupSVG("payload")
    group.add_component(RectangleSVG((10.0, 10.0), 2.0, 3.0, 0.0, style))
    document.page(1).layer("base").add_component_group(group)
    return document, style


def _document_with_custom_layer() -> tuple[DocumentSVG, DrawingStyle]:
    """Return a valid SVG document whose only serialized layer is not base."""
    style = _drawing_style()
    document = DocumentSVG(Canvas(100.0, 100.0))
    document.add_page()
    page = document.page(1)
    page.add_layer("drawing")
    page.remove_layer("base")
    group = ComponentGroupSVG("payload")
    group.add_component(RectangleSVG((10.0, 10.0), 2.0, 3.0, 0.0, style))
    page.layer("drawing").add_component_group(group)
    return document, style


@pytest.mark.condition("SVG-DOCUMENT-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("payload", "exception_type", "message"),
    [
        (object(), TypeError, "DocumentSVG data must be a mapping"),
        ({}, ValueError, "DocumentSVG data must include DocumentSVG"),
        ({"DocumentSVG": object()}, TypeError, "DocumentSVG payload must be a mapping"),
        ({"DocumentSVG": {"pages": []}}, ValueError, "DocumentSVG payload must include canvas"),
        ({"DocumentSVG": {"canvas": Canvas(100.0, 100.0).parameters}}, ValueError, "DocumentSVG payload must include pages"),
        (
            {"DocumentSVG": {"canvas": Canvas(100.0, 100.0).parameters, "pages": "bad"}},
            TypeError,
            "DocumentSVG pages must be a sequence",
        ),
    ],
)
def test_document_svg_factory_rejects_malformed_document_payloads(
    payload: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """SVG-DOCUMENT-FACTORY-PAYLOAD-P2: Document roots and pages fail explicitly."""
    with pytest.raises(exception_type, match=message):
        DocumentSVG.create_from_dict(payload)


@pytest.mark.condition("SVG-DOCUMENT-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("mutator", "exception_type", "message"),
    [
        (lambda data: data["DocumentSVG"]["pages"].__setitem__(0, object()), TypeError, "Layers data must be a mapping"),
        (
            lambda data: data["DocumentSVG"]["pages"].__setitem__(0, {}),
            ValueError,
            "Layers data must include Layers",
        ),
        (
            lambda data: data["DocumentSVG"]["pages"][0].__setitem__("Layers", object()),
            TypeError,
            "Layers payload must be a mapping",
        ),
        (
            lambda data: data["DocumentSVG"]["pages"][0]["Layers"].pop("canvas"),
            ValueError,
            "Layers payload must include canvas",
        ),
        (
            lambda data: data["DocumentSVG"]["pages"][0]["Layers"].__setitem__("layers", []),
            TypeError,
            "Layers layers must be a mapping",
        ),
    ],
)
def test_document_svg_factory_rejects_malformed_page_payloads(
    mutator: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """SVG-DOCUMENT-FACTORY-PAYLOAD-P2: Page-level Layers envelopes fail explicitly."""
    document, style = _document()
    payload = deepcopy(document.parameters)
    mutator(payload)

    with pytest.raises(exception_type, match=message):
        DocumentSVG.create_from_dict(payload, {style.name: style})


@pytest.mark.condition("SVG-DOCUMENT-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("mutator", "exception_type", "message"),
    [
        (
            lambda data: data["DocumentSVG"]["pages"][0]["Layers"]["layers"].__setitem__("base", object()),
            TypeError,
            "Layer data must be a mapping",
        ),
        (
            lambda data: data["DocumentSVG"]["pages"][0]["Layers"]["layers"].__setitem__("base", {}),
            ValueError,
            "Layer data must include Layer",
        ),
        (
            lambda data: data["DocumentSVG"]["pages"][0]["Layers"]["layers"]["base"].__setitem__("Layer", object()),
            TypeError,
            "Layer payload must be a mapping",
        ),
        (
            lambda data: data["DocumentSVG"]["pages"][0]["Layers"]["layers"]["base"]["Layer"].pop("layer_name"),
            ValueError,
            "Layer payload must include layer_name",
        ),
        (
            lambda data: data["DocumentSVG"]["pages"][0]["Layers"]["layers"]["base"]["Layer"].__setitem__("component_groups", "bad"),
            TypeError,
            "Layer component_groups must be a sequence",
        ),
        (
            lambda data: data["DocumentSVG"]["pages"][0]["Layers"]["layers"]["base"]["Layer"].__setitem__("group_collision_settings", []),
            TypeError,
            "Layer group_collision_settings must be a mapping",
        ),
        (
            lambda data: data["DocumentSVG"]["pages"][0]["Layers"]["layers"]["base"]["Layer"]["component_groups"].__setitem__(
                0,
                object(),
            ),
            TypeError,
            "Layer component group entries must be mappings",
        ),
        (
            lambda data: data["DocumentSVG"]["pages"][0]["Layers"]["layers"]["base"]["Layer"]["group_collision_settings"].__setitem__(
                "payload",
                "bad",
            ),
            TypeError,
            "Layer group collision setting entries must be mappings",
        ),
        (
            lambda data: data["DocumentSVG"]["pages"][0]["Layers"]["layers"]["base"]["Layer"]["group_collision_settings"]["payload"].pop(
                "allow_collision"
            ),
            ValueError,
            "Layer group collision settings payload must include allow_collision",
        ),
        (
            lambda data: data["DocumentSVG"]["pages"][0]["Layers"]["layers"]["base"]["Layer"]["group_collision_settings"]["payload"].pop(
                "strict"
            ),
            ValueError,
            "Layer group collision settings payload must include strict",
        ),
    ],
)
def test_document_svg_factory_rejects_malformed_layer_payloads(
    mutator: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """SVG-DOCUMENT-FACTORY-PAYLOAD-P2: Layer envelopes fail before group hydration."""
    document, style = _document()
    payload = deepcopy(document.parameters)
    mutator(payload)

    with pytest.raises(exception_type, match=message):
        DocumentSVG.create_from_dict(payload, {style.name: style})


@pytest.mark.condition("SVG-DOCUMENT-FACTORY-PAYLOAD-P2")
def test_document_svg_factory_preserves_valid_document_hydration() -> None:
    """SVG-DOCUMENT-FACTORY-PAYLOAD-P2: Valid document payloads still hydrate."""
    document, style = _document()

    recreated = DocumentSVG.create_from_dict(document.parameters, {style.name: style})
    svg = recreated._assemble_page_svg(recreated.page(1), [])

    assert recreated.parameters == document.parameters
    assert "<rect" in svg
    assert 'width="2.0"' in svg
    assert 'height="3.0"' in svg
    assert list(recreated.page(1).layers) == ["base"]


@pytest.mark.condition("SVG-DOCUMENT-FACTORY-PAYLOAD-P2")
def test_document_svg_factory_removes_constructor_default_layer() -> None:
    """SVG-DOCUMENT-FACTORY-PAYLOAD-P2: Hydration does not leak the default layer."""
    document, style = _document_with_custom_layer()

    recreated = DocumentSVG.create_from_dict(document.parameters, {style.name: style})

    assert recreated.parameters == document.parameters
    assert list(recreated.page(1).layers) == ["drawing"]


@pytest.mark.condition("SVG-DOCUMENT-FACTORY-PAYLOAD-P2")
def test_document_svg_factory_preserves_generic_group_compatibility() -> None:
    """SVG-DOCUMENT-FACTORY-PAYLOAD-P2: Legacy generic groups still hydrate."""
    style = _drawing_style()
    document = DocumentSVG(Canvas(100.0, 100.0))
    document.add_page()
    group = ComponentGroup("generic")
    group.add_component(WidthHeightDrawingComponent((1.0, 2.0), 3.0, 4.0, style))
    document.page(1).layer("base").add_component_group(group)
    if style.name in Style.style_names:
        Style.style_names.remove(style.name)

    recreated = DocumentSVG.create_from_dict(document.parameters, {style.name: style})

    assert recreated.parameters == document.parameters
    assert list(recreated.page(1).layers) == ["base"]


@pytest.mark.condition("SVG-DOCUMENT-FACTORY-PAYLOAD-P2")
def test_document_svg_factory_contract_remains_live_in_group_hydration() -> None:
    """SVG-DOCUMENT-FACTORY-PAYLOAD-P2: Nested SVG groups still use the SVG group factory."""
    document, style = _document()
    payload = deepcopy(document.parameters)
    group_payload = payload["DocumentSVG"]["pages"][0]["Layers"]["layers"]["base"]["Layer"]["component_groups"][0]
    group_payload["ComponentGroupSVG"]["components"] = "bad"

    with pytest.raises(TypeError, match="ComponentGroupSVG components must be a sequence"):
        DocumentSVG.create_from_dict(payload, {style.name: style})
