"""Tests for InkGen's dependency-free PDF backend."""

from __future__ import annotations

import re
import uuid

import pytest

from InkGen.boundary import Canvas
from InkGen.component import PathCommand
from InkGen.pdf_generator import (
    ArcPDF,
    CirclePDF,
    ComponentGroupPDF,
    CubicBezierPDF,
    DocumentPDF,
    LinePDF,
    PathPDF,
    PDFGeneratorInterface,
    PolygonalPDF,
    QuadraticBezierPDF,
    RectanglePDF,
    RegularPolygonPDF,
    TextPDF,
)
from InkGen.style import DrawingStyle, Font, TextStyle


@pytest.fixture
def drawing_style() -> DrawingStyle:
    """Return a unique drawing style for PDF tests."""
    return DrawingStyle(name=f"pdf_style_{uuid.uuid4().hex}", stroke="#000000", stroke_width=0.2, fill="none")


@pytest.fixture
def text_style() -> TextStyle:
    """Return a unique text style for PDF tests."""
    return TextStyle(name=f"pdf_text_{uuid.uuid4().hex}", font=Font(size=12.0))


def _stream(pdf_bytes: bytes) -> str:
    match = re.search(rb"stream\n(?P<content>.*?)\nendstream", pdf_bytes, re.S)
    assert match is not None
    return match.group("content").decode("latin-1")


@pytest.mark.condition("PDF-P1")
def test_pdf_backend_has_parallel_primitive_mixins() -> None:
    """PDF-P1: Every Phase 1 SVG primitive has a parallel PDF primitive."""
    primitive_classes = [
        RectanglePDF,
        LinePDF,
        ArcPDF,
        QuadraticBezierPDF,
        CubicBezierPDF,
        PathPDF,
        RegularPolygonPDF,
        PolygonalPDF,
        CirclePDF,
        TextPDF,
    ]

    assert all(issubclass(primitive, PDFGeneratorInterface) for primitive in primitive_classes)


@pytest.mark.condition("PDF-P1")
def test_pdf_primitives_emit_content_stream_operators(drawing_style: DrawingStyle, text_style: TextStyle) -> None:
    """PDF-P1: Primitive renderers emit PDF operators without third-party libraries."""
    path = PathPDF(
        drawing_style,
        commands=[
            PathCommand("M", [(1.0, 2.0)]),
            PathCommand("L", [(3.0, 4.0)]),
            PathCommand("Z", []),
        ],
    )

    assert "10 20 30 40 re" in RectanglePDF((10.0, 20.0), 30.0, 40.0, 0.0, drawing_style).generate_pdf()
    assert "1 1 m\n2 2 l" in LinePDF((1.0, 1.0), (2.0, 2.0), drawing_style).generate_pdf()
    assert " c" in QuadraticBezierPDF((0.0, 0.0), (1.0, 1.0), (2.0, 0.0), drawing_style).generate_pdf()
    assert " c" in CubicBezierPDF((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0), drawing_style).generate_pdf()
    assert "1 2 m\n3 4 l\nh" in path.generate_pdf()
    assert "\nh\n" in RegularPolygonPDF((10.0, 10.0), 3, 5.0, drawing_style).generate_pdf()
    assert "0 0 m\n1 0 l\n1 1 l\nh" in PolygonalPDF([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)], drawing_style).generate_pdf()
    assert " c" in CirclePDF((10.0, 10.0), 5.0, drawing_style).generate_pdf()
    assert "(Hello \\(PDF\\)) Tj" in TextPDF("Hello (PDF)", (10.0, 20.0), text_style).generate_pdf()


@pytest.mark.condition("PDF-P1")
def test_document_pdf_is_deterministic_and_flips_page_coordinates_once(drawing_style: DrawingStyle, text_style: TextStyle) -> None:
    """PDF-P1: DocumentPDF emits stable bytes with a page-level SVG-to-PDF coordinate flip."""
    canvas = Canvas(100.0, 80.0)
    document = DocumentPDF(canvas)
    document.add_page()
    group = ComponentGroupPDF("base")
    group.add_component(RectanglePDF((10.0, 20.0), 30.0, 40.0, 0.0, drawing_style))
    group.add_component(TextPDF("Seed", (15.0, 25.0), text_style))
    document.page(1).layer("base").add_component_group(group)

    first = document.to_pdf_bytes()
    second = document.to_pdf_bytes()
    content = _stream(first)

    assert first == second
    assert first.startswith(b"%PDF-1.4\n")
    assert b"/CreationDate (D:20000101000000Z)" in first
    assert b"/MediaBox [0 0 100 80]" in first
    assert content.count("1 0 0 -1 0 80 cm") == 1
    assert "10 20 30 40 re" in content
    assert "1 0 0 -1 15 25 Tm" in content


@pytest.mark.condition("PDF-P1")
def test_component_group_pdf_rejects_non_pdf_components() -> None:
    """PDF-P1: ComponentGroupPDF rendering fails loudly when a component lacks generate_pdf."""

    class NonPdfComponent:
        id = 999

    group = ComponentGroupPDF("bad")
    group._components[999] = NonPdfComponent()

    with pytest.raises(TypeError, match="does not implement generate_pdf"):
        group.generate_pdf()
