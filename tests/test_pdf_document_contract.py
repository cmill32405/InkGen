"""PDF document renderer contract tests."""

from __future__ import annotations

import re
from uuid import uuid4

import pytest

from InkGen.boundary import Canvas
from InkGen.extraction_truth import annotate_extraction_truth
from InkGen.grammar_truth import annotate_grammar_truth
from InkGen.pdf_generator import ComponentGroupPDF, DocumentPDF, RectanglePDF
from InkGen.style import DrawingStyle


def _drawing_style() -> DrawingStyle:
    return DrawingStyle(f"pdf_doc_{uuid4().hex}", stroke="#000000", stroke_width=0.2, fill="none")


def _stream(pdf_bytes: bytes) -> str:
    match = re.search(rb"stream\n(?P<content>.*?)\nendstream", pdf_bytes, re.S)
    assert match is not None
    return match.group("content").decode("latin-1")


def _document_with_duplicate_label_groups() -> tuple[DocumentPDF, ComponentGroupPDF, ComponentGroupPDF]:
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    first = ComponentGroupPDF("Repeat")
    first.add_component(RectanglePDF((10.0, 10.0), 8.0, 6.0, 0.0, _drawing_style()))
    second = ComponentGroupPDF("Repeat")
    second.add_component(RectanglePDF((40.0, 10.0), 9.0, 7.0, 0.0, _drawing_style()))
    layer = document.page(1).layer("base")
    layer.add_component_group(first)
    layer.add_component_group(second)
    return document, first, second


@pytest.mark.condition("PDF-DOC-P2")
def test_document_pdf_renders_duplicate_label_groups() -> None:
    """PDF-DOC-P2: PDF rendering traverses every stored group, not only label lookup entries."""
    document, _, _ = _document_with_duplicate_label_groups()

    content = _stream(document.to_pdf_bytes())

    assert "10 10 8 6 re" in content
    assert "40 10 9 7 re" in content


@pytest.mark.condition("PDF-DOC-P2")
def test_document_pdf_rendering_preserves_group_insertion_order() -> None:
    """PDF-DOC-P2: PDF content follows layer group insertion order, not label sort order."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    z_group = ComponentGroupPDF("z-last-alphabetically")
    z_group.add_component(RectanglePDF((70.0, 10.0), 8.0, 6.0, 0.0, _drawing_style()))
    a_group = ComponentGroupPDF("a-first-alphabetically")
    a_group.add_component(RectanglePDF((10.0, 10.0), 8.0, 6.0, 0.0, _drawing_style()))
    document.page(1).layer("base").add_component_group(z_group)
    document.page(1).layer("base").add_component_group(a_group)

    content = _stream(document.to_pdf_bytes())

    assert content.index("70 10 8 6 re") < content.index("10 10 8 6 re")


@pytest.mark.condition("PDF-DOC-P2")
def test_document_pdf_extraction_truth_includes_duplicate_label_groups() -> None:
    """PDF-DOC-P2: Extraction truth includes repeated semantic labels as distinct groups."""
    document, first, second = _document_with_duplicate_label_groups()
    annotate_extraction_truth(first, "repeat_group", "first", instance_id="first")
    annotate_extraction_truth(second, "repeat_group", "second", instance_id="second")

    records = document.extraction_truth()

    assert {record["instance_id"] for record in records} == {"first", "second"}
    assert {record["value"] for record in records} == {"first", "second"}


@pytest.mark.condition("PDF-DOC-P2")
def test_document_pdf_grammar_truth_includes_duplicate_label_groups() -> None:
    """PDF-DOC-P2: Grammar truth includes repeated semantic labels as distinct groups."""
    document, first, second = _document_with_duplicate_label_groups()
    annotate_grammar_truth(first, "B-REPEAT", "cue", value="first", instance_id="first")
    annotate_grammar_truth(second, "B-REPEAT", "cue", value="second", instance_id="second")

    records = document.grammar_truth()

    assert {record["instance_id"] for record in records} == {"first", "second"}
    assert {record["value"] for record in records} == {"first", "second"}
