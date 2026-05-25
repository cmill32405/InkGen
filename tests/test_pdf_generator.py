"""Tests for InkGen's dependency-free PDF backend."""

from __future__ import annotations

import re
import uuid

import pytest

from InkGen.boundary import Canvas
from InkGen.component import ComponentGroup, PathCommand
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


@pytest.mark.condition("PDF-P1")
def test_pdf_primitives_round_trip_parameters(drawing_style: DrawingStyle, text_style: TextStyle) -> None:
    """PDF-P1: PDF primitives recreate from their own serialized parameters."""
    commands = [
        PathCommand("M", [(1.0, 2.0)]),
        PathCommand("L", [(3.0, 4.0)]),
        PathCommand("Z", []),
    ]
    primitives = [
        (RectanglePDF((10.0, 20.0), 30.0, 40.0, 0.0, drawing_style), drawing_style),
        (LinePDF((1.0, 1.0), (2.0, 2.0), drawing_style), drawing_style),
        (ArcPDF((10.0, 10.0), 5.0, 3.0, 0.0, 90.0, drawing_style), drawing_style),
        (QuadraticBezierPDF((0.0, 0.0), (1.0, 1.0), (2.0, 0.0), drawing_style), drawing_style),
        (CubicBezierPDF((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0), drawing_style), drawing_style),
        (PathPDF(drawing_style, commands=commands), drawing_style),
        (RegularPolygonPDF((10.0, 10.0), 3, 5.0, drawing_style), drawing_style),
        (PolygonalPDF([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)], drawing_style), drawing_style),
        (CirclePDF((10.0, 10.0), 5.0, drawing_style), drawing_style),
        (TextPDF("Seed", (15.0, 25.0), text_style), text_style),
    ]

    for primitive, style in primitives:
        recreated = primitive.__class__.create_from_dict(primitive.parameters, style)
        assert recreated.parameters == primitive.parameters
        assert recreated.generate_pdf() == primitive.generate_pdf()


@pytest.mark.condition("PDF-P1")
def test_component_group_pdf_round_trips_pdf_children(drawing_style: DrawingStyle, text_style: TextStyle) -> None:
    """PDF-P1: ComponentGroupPDF recreates child PDF components from parameters."""
    group = ComponentGroupPDF("roundtrip")
    group.add_component(RectanglePDF((10.0, 20.0), 30.0, 40.0, 0.0, drawing_style))
    group.add_component(TextPDF("Seed", (15.0, 25.0), text_style))

    styles = {drawing_style.name: drawing_style, text_style.name: text_style}
    recreated = ComponentGroupPDF.create_from_dict(group.parameters, styles)

    assert recreated.parameters == group.parameters
    assert recreated.generate_pdf() == group.generate_pdf()


@pytest.mark.condition("PDF-P1")
def test_document_pdf_round_trips_parameters_and_bytes(drawing_style: DrawingStyle, text_style: TextStyle) -> None:
    """PDF-P1: DocumentPDF recreates pages/layers/groups and preserves deterministic bytes."""
    canvas = Canvas(100.0, 80.0)
    document = DocumentPDF(canvas)
    document.add_page()
    group = ComponentGroupPDF("roundtrip")
    group.add_component(RectanglePDF((10.0, 20.0), 30.0, 40.0, 0.0, drawing_style))
    group.add_component(TextPDF("Seed", (15.0, 25.0), text_style))
    document.page(1).layer("base").add_component_group(group)

    styles = {drawing_style.name: drawing_style, text_style.name: text_style}
    recreated = DocumentPDF.create_from_dict(document.parameters, styles)

    assert recreated.parameters == document.parameters
    assert recreated.to_pdf_bytes() == document.to_pdf_bytes()


@pytest.mark.condition("PDF-P1")
def test_document_pdf_outputs_one_pdf_page_per_inkgen_page(drawing_style: DrawingStyle) -> None:
    """PDF-P1: DocumentPDF assembles one PDF page for each InkGen page."""
    canvas = Canvas(100.0, 80.0)
    document = DocumentPDF(canvas)

    for page_index in range(2):
        document.add_page()
        group = ComponentGroupPDF(f"page_{page_index + 1}")
        group.add_component(RectanglePDF((10.0 + page_index, 20.0), 30.0, 40.0, 0.0, drawing_style))
        document.page(page_index + 1).layer("base").add_component_group(group)

    payload = document.to_pdf_bytes()

    assert payload.count(b"/Type /Page ") == 2
    assert b"/Type /Pages" in payload
    assert b"/Count 2" in payload
    assert payload.count(b"/MediaBox [0 0 100 80]") == 2
    assert payload.count(b"1 0 0 -1 0 80 cm") == 2


@pytest.mark.condition("PDF-P1")
def test_document_pdf_create_pdf_writes_bytes_and_rejects_missing_directory(
    tmp_path,
    drawing_style: DrawingStyle,
) -> None:
    """PDF-P1: create_pdf writes deterministic bytes and fails loudly on bad paths."""
    canvas = Canvas(100.0, 80.0)
    document = DocumentPDF(canvas)
    document.add_page()
    group = ComponentGroupPDF("base")
    group.add_component(RectanglePDF((10.0, 20.0), 30.0, 40.0, 0.0, drawing_style))
    document.page(1).layer("base").add_component_group(group)

    target = tmp_path / "seed.pdf"
    document.create_pdf(str(target))

    assert target.read_bytes() == document.to_pdf_bytes()
    with pytest.raises(ValueError, match="file path does not exist"):
        document.create_pdf(str(tmp_path / "missing" / "seed.pdf"))


@pytest.mark.condition("PDF-P1")
def test_text_pdf_escapes_literal_string_control_characters(text_style: TextStyle) -> None:
    """PDF-P1: TextPDF escapes literal-string delimiter and control characters."""
    content = TextPDF("A\\B(C)\r\nD", (1.0, 2.0), text_style).generate_pdf()

    assert r"(A\\B\(C\)\r\nD) Tj" in content


@pytest.mark.condition("PDF-P1")
def test_drawing_style_without_visible_paint_emits_noop_path(drawing_style: DrawingStyle) -> None:
    """PDF-P1: Invisible drawing styles emit a no-op paint operator."""
    drawing_style.stroke = "none"
    drawing_style.fill = "none"

    content = RectanglePDF((10.0, 20.0), 30.0, 40.0, 0.0, drawing_style).generate_pdf()

    assert content.endswith("\nn\nQ")


@pytest.mark.condition("PDF-P1")
def test_document_pdf_rejects_non_pdf_child_in_standard_group(drawing_style: DrawingStyle) -> None:
    """PDF-P1: DocumentPDF fails loudly when the live page path contains a non-PDF child."""

    class NonPdfComponent:
        id = 12345

    canvas = Canvas(100.0, 80.0)
    document = DocumentPDF(canvas)
    document.add_page()
    group = ComponentGroup("mixed")
    group.add_component(RectanglePDF((10.0, 20.0), 30.0, 40.0, 0.0, drawing_style))
    document.page(1).layer("base").add_component_group(group)
    group._components[NonPdfComponent.id] = NonPdfComponent()

    with pytest.raises(TypeError, match="does not implement generate_pdf"):
        document.to_pdf_bytes()
