"""Behavioral tests for PDF document factory payload envelopes."""

from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

import pytest

from InkGen.boundary import Canvas
from InkGen.pdf_generator import ComponentGroupPDF, DocumentPDF, RectanglePDF
from InkGen.style import DrawingStyle


def _drawing_style() -> DrawingStyle:
    """Return a unique drawing style for PDF document factory contract tests."""
    return DrawingStyle(f"pdf_document_factory_{uuid4().hex}", stroke="#000000", fill="none")


def _document() -> tuple[DocumentPDF, DrawingStyle]:
    """Return a valid one-page PDF document with one layer and one group."""
    style = _drawing_style()
    document = DocumentPDF(Canvas(100.0, 100.0))
    document.add_page()
    group = ComponentGroupPDF("payload")
    group.add_component(RectanglePDF((10.0, 10.0), 2.0, 3.0, 0.0, style))
    document.page(1).layer("base").add_component_group(group)
    return document, style


def _document_with_custom_layer() -> tuple[DocumentPDF, DrawingStyle]:
    """Return a valid PDF document whose only serialized layer is not base."""
    style = _drawing_style()
    document = DocumentPDF(Canvas(100.0, 100.0))
    document.add_page()
    page = document.page(1)
    page.add_layer("drawing")
    page.remove_layer("base")
    group = ComponentGroupPDF("payload")
    group.add_component(RectanglePDF((10.0, 10.0), 2.0, 3.0, 0.0, style))
    page.layer("drawing").add_component_group(group)
    return document, style


@pytest.mark.condition("PDF-DOCUMENT-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("payload", "exception_type", "message"),
    [
        (object(), TypeError, "DocumentPDF data must be a mapping"),
        ({}, ValueError, "DocumentPDF data must include DocumentPDF"),
        ({"DocumentPDF": object()}, TypeError, "DocumentPDF payload must be a mapping"),
        ({"DocumentPDF": {"pages": []}}, ValueError, "DocumentPDF payload must include canvas"),
        ({"DocumentPDF": {"canvas": Canvas(100.0, 100.0).parameters}}, ValueError, "DocumentPDF payload must include pages"),
        (
            {"DocumentPDF": {"canvas": Canvas(100.0, 100.0).parameters, "pages": "bad"}},
            TypeError,
            "DocumentPDF pages must be a sequence",
        ),
    ],
)
def test_document_pdf_factory_rejects_malformed_document_payloads(
    payload: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """PDF-DOCUMENT-FACTORY-PAYLOAD-P2: Document roots and pages fail explicitly."""
    with pytest.raises(exception_type, match=message):
        DocumentPDF.create_from_dict(payload)


@pytest.mark.condition("PDF-DOCUMENT-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("mutator", "exception_type", "message"),
    [
        (lambda data: data["DocumentPDF"]["pages"].__setitem__(0, object()), TypeError, "Layers data must be a mapping"),
        (
            lambda data: data["DocumentPDF"]["pages"].__setitem__(0, {}),
            ValueError,
            "Layers data must include Layers",
        ),
        (
            lambda data: data["DocumentPDF"]["pages"][0].__setitem__("Layers", object()),
            TypeError,
            "Layers payload must be a mapping",
        ),
        (
            lambda data: data["DocumentPDF"]["pages"][0]["Layers"].pop("canvas"),
            ValueError,
            "Layers payload must include canvas",
        ),
        (
            lambda data: data["DocumentPDF"]["pages"][0]["Layers"].__setitem__("layers", []),
            TypeError,
            "Layers layers must be a mapping",
        ),
    ],
)
def test_document_pdf_factory_rejects_malformed_page_payloads(
    mutator: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """PDF-DOCUMENT-FACTORY-PAYLOAD-P2: Page-level Layers envelopes fail explicitly."""
    document, style = _document()
    payload = deepcopy(document.parameters)
    mutator(payload)

    with pytest.raises(exception_type, match=message):
        DocumentPDF.create_from_dict(payload, {style.name: style})


@pytest.mark.condition("PDF-DOCUMENT-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("mutator", "exception_type", "message"),
    [
        (
            lambda data: data["DocumentPDF"]["pages"][0]["Layers"]["layers"].__setitem__("base", object()),
            TypeError,
            "Layer data must be a mapping",
        ),
        (
            lambda data: data["DocumentPDF"]["pages"][0]["Layers"]["layers"].__setitem__("base", {}),
            ValueError,
            "Layer data must include Layer",
        ),
        (
            lambda data: data["DocumentPDF"]["pages"][0]["Layers"]["layers"]["base"].__setitem__("Layer", object()),
            TypeError,
            "Layer payload must be a mapping",
        ),
        (
            lambda data: data["DocumentPDF"]["pages"][0]["Layers"]["layers"]["base"]["Layer"].pop("layer_name"),
            ValueError,
            "Layer payload must include layer_name",
        ),
        (
            lambda data: data["DocumentPDF"]["pages"][0]["Layers"]["layers"]["base"]["Layer"].__setitem__("component_groups", "bad"),
            TypeError,
            "Layer component_groups must be a sequence",
        ),
        (
            lambda data: data["DocumentPDF"]["pages"][0]["Layers"]["layers"]["base"]["Layer"].__setitem__("group_collision_settings", []),
            TypeError,
            "Layer group_collision_settings must be a mapping",
        ),
        (
            lambda data: data["DocumentPDF"]["pages"][0]["Layers"]["layers"]["base"]["Layer"]["group_collision_settings"].__setitem__(
                "payload",
                "bad",
            ),
            TypeError,
            "Layer group collision setting entries must be mappings",
        ),
        (
            lambda data: data["DocumentPDF"]["pages"][0]["Layers"]["layers"]["base"]["Layer"]["group_collision_settings"]["payload"].pop(
                "allow_collision"
            ),
            ValueError,
            "Layer group collision settings payload must include allow_collision",
        ),
        (
            lambda data: data["DocumentPDF"]["pages"][0]["Layers"]["layers"]["base"]["Layer"]["group_collision_settings"]["payload"].pop(
                "strict"
            ),
            ValueError,
            "Layer group collision settings payload must include strict",
        ),
    ],
)
def test_document_pdf_factory_rejects_malformed_layer_payloads(
    mutator: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """PDF-DOCUMENT-FACTORY-PAYLOAD-P2: Layer envelopes fail before group hydration."""
    document, style = _document()
    payload = deepcopy(document.parameters)
    mutator(payload)

    with pytest.raises(exception_type, match=message):
        DocumentPDF.create_from_dict(payload, {style.name: style})


@pytest.mark.condition("PDF-DOCUMENT-FACTORY-PAYLOAD-P2")
def test_document_pdf_factory_preserves_valid_document_hydration() -> None:
    """PDF-DOCUMENT-FACTORY-PAYLOAD-P2: Valid document payloads still hydrate."""
    document, style = _document()

    recreated = DocumentPDF.create_from_dict(document.parameters, {style.name: style})

    assert recreated.parameters == document.parameters
    assert recreated.to_pdf_bytes() == document.to_pdf_bytes()
    assert list(recreated.page(1).layers) == ["base"]


@pytest.mark.condition("PDF-DOCUMENT-FACTORY-PAYLOAD-P2")
def test_document_pdf_factory_removes_constructor_default_layer() -> None:
    """PDF-DOCUMENT-FACTORY-PAYLOAD-P2: Hydration does not leak the default layer."""
    document, style = _document_with_custom_layer()

    recreated = DocumentPDF.create_from_dict(document.parameters, {style.name: style})

    assert recreated.parameters == document.parameters
    assert recreated.to_pdf_bytes() == document.to_pdf_bytes()
    assert list(recreated.page(1).layers) == ["drawing"]


@pytest.mark.condition("PDF-DOCUMENT-FACTORY-PAYLOAD-P2")
def test_document_pdf_factory_contract_remains_live_in_group_hydration() -> None:
    """PDF-DOCUMENT-FACTORY-PAYLOAD-P2: Nested groups still use the PDF group factory."""
    document, style = _document()
    payload = deepcopy(document.parameters)
    group_payload = payload["DocumentPDF"]["pages"][0]["Layers"]["layers"]["base"]["Layer"]["component_groups"][0]
    group_payload["ComponentGroupPDF"]["components"] = "bad"

    with pytest.raises(TypeError, match="ComponentGroupPDF components must be a sequence"):
        DocumentPDF.create_from_dict(payload, {style.name: style})
