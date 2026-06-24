"""Behavioral tests for PDF component-group factory payload envelopes."""

from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

import pytest

from InkGen.boundary import Canvas
from InkGen.pdf_generator import ComponentGroupPDF, DocumentPDF, RectanglePDF, TextPDF
from InkGen.style import DrawingStyle, Font, TextStyle


def _drawing_style() -> DrawingStyle:
    """Return a unique drawing style for PDF group factory contract tests."""
    return DrawingStyle(f"pdf_group_draw_{uuid4().hex}", stroke="#000000", fill="none")


def _text_style() -> TextStyle:
    """Return a unique text style for PDF group factory contract tests."""
    return TextStyle(f"pdf_group_text_{uuid4().hex}", Font(size=11.0))


def _group() -> tuple[ComponentGroupPDF, DrawingStyle, TextStyle]:
    """Return a valid PDF group with drawing and text children."""
    drawing_style = _drawing_style()
    text_style = _text_style()
    group = ComponentGroupPDF("payload")
    group.add_component(RectanglePDF((0.0, 0.0), 2.0, 3.0, 0.0, drawing_style))
    group.add_component(TextPDF("label", (1.0, 2.0), text_style))
    return group, drawing_style, text_style


@pytest.mark.condition("PDF-GROUP-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("payload", "exception_type", "message"),
    [
        (object(), TypeError, "ComponentGroupPDF data must be a mapping"),
        ({}, ValueError, "ComponentGroupPDF data must include ComponentGroupPDF"),
        ({"ComponentGroupPDF": object()}, TypeError, "ComponentGroupPDF payload must be a mapping"),
        ({"ComponentGroupPDF": {"components": []}}, ValueError, "ComponentGroupPDF payload must include group_label"),
        ({"ComponentGroupPDF": {"group_label": "payload"}}, ValueError, "ComponentGroupPDF payload must include components"),
        (
            {"ComponentGroupPDF": {"group_label": "payload", "components": "RectanglePDF"}},
            TypeError,
            "ComponentGroupPDF components must be a sequence",
        ),
    ],
)
def test_component_group_pdf_factory_rejects_malformed_group_payloads(
    payload: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """PDF-GROUP-FACTORY-PAYLOAD-P2: Group roots and component collections fail explicitly."""
    with pytest.raises(exception_type, match=message):
        ComponentGroupPDF.create_from_dict(payload)


@pytest.mark.condition("PDF-GROUP-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("component_entry", "exception_type", "message"),
    [
        (object(), TypeError, "PDF component entry must be a mapping"),
        ({}, ValueError, "PDF component entry must contain one type"),
        (
            {
                "RectanglePDF": {"position": (0.0, 0.0), "width": 1.0, "height": 1.0, "corner_radii": 0.0},
                "TextPDF": {"text": "x", "position": (0.0, 0.0)},
            },
            ValueError,
            "PDF component entry must contain one type",
        ),
        ({1: {}}, TypeError, "PDF component type must be a string"),
        ({"RectanglePDF": object()}, TypeError, "PDF component payload must be a mapping"),
        ({"NotPDF": {}}, ValueError, "Unsupported PDF component payload type: NotPDF"),
        ({"DocumentPDF": {}}, ValueError, "Unsupported PDF component payload type: DocumentPDF"),
    ],
)
def test_component_group_pdf_factory_rejects_malformed_component_entries(
    component_entry: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """PDF-GROUP-FACTORY-PAYLOAD-P2: Child component entries fail before dynamic dispatch."""
    payload = {"ComponentGroupPDF": {"group_label": "payload", "components": [component_entry]}}

    with pytest.raises(exception_type, match=message):
        ComponentGroupPDF.create_from_dict(payload)


@pytest.mark.condition("PDF-GROUP-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("style_payload", "exception_type", "message"),
    [
        (object(), TypeError, "PDF component style entry must be a mapping"),
        ({}, ValueError, "PDF component style entry must contain one type"),
        (
            {"DrawingStyle": {"name": "a"}, "TextStyle": {"name": "b"}},
            ValueError,
            "PDF component style entry must contain one type",
        ),
        ({1: {"name": "bad"}}, TypeError, "PDF component style type must be a string"),
        ({"DrawingStyle": object()}, TypeError, "PDF component style payload must be a mapping"),
        ({"DrawingStyle": {"stroke": "#000000"}}, TypeError, "PDF component style name must be a string"),
        ({"ComponentGroupPDF": {"name": "not_style"}}, ValueError, "Unsupported PDF component style payload type: ComponentGroupPDF"),
    ],
)
def test_component_group_pdf_factory_rejects_malformed_style_envelopes(
    style_payload: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """PDF-GROUP-FACTORY-PAYLOAD-P2: Child style envelopes fail before style hydration."""
    component = {
        "RectanglePDF": {
            "position": (0.0, 0.0),
            "width": 1.0,
            "height": 1.0,
            "corner_radii": 0.0,
            "style": style_payload,
        }
    }
    payload = {"ComponentGroupPDF": {"group_label": "payload", "components": [component]}}

    with pytest.raises(exception_type, match=message):
        ComponentGroupPDF.create_from_dict(payload)


@pytest.mark.condition("PDF-GROUP-FACTORY-PAYLOAD-P2")
def test_component_group_pdf_factory_preserves_valid_group_hydration() -> None:
    """PDF-GROUP-FACTORY-PAYLOAD-P2: Valid PDF group payloads still hydrate."""
    group, drawing_style, text_style = _group()
    styles = {drawing_style.name: drawing_style, text_style.name: text_style}

    recreated = ComponentGroupPDF.create_from_dict(group.parameters, styles)

    assert recreated.parameters == group.parameters
    assert recreated.generate_pdf() == group.generate_pdf()


@pytest.mark.condition("PDF-GROUP-FACTORY-PAYLOAD-P2")
def test_component_group_pdf_factory_contract_remains_live_in_document_hydration() -> None:
    """PDF-GROUP-FACTORY-PAYLOAD-P2: DocumentPDF routes nested groups through the group factory."""
    drawing_style = _drawing_style()
    group = ComponentGroupPDF("payload")
    group.add_component(RectanglePDF((10.0, 10.0), 2.0, 3.0, 0.0, drawing_style))
    document = DocumentPDF(Canvas(100.0, 100.0))
    document.add_page()
    document.page(1).layer("base").add_component_group(group)
    styles = {drawing_style.name: drawing_style}

    recreated = DocumentPDF.create_from_dict(document.parameters, styles)

    assert recreated.to_pdf_bytes() == document.to_pdf_bytes()

    broken = deepcopy(document.parameters)
    broken["DocumentPDF"]["pages"][0]["Layers"]["layers"]["base"]["Layer"]["component_groups"][0]["ComponentGroupPDF"]["components"] = "bad"
    with pytest.raises(TypeError, match="ComponentGroupPDF components must be a sequence"):
        DocumentPDF.create_from_dict(broken, styles)
