"""Tests for InkGen's dependency-free PDF backend."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

import pytest

import InkGen.pdf_generator as pdf_generator_module
import InkGen.svg_generator as svg_generator_module
from InkGen.boundary import Canvas
from InkGen.component import Component, ComponentGroup, PathCommand
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
from InkGen.pdf_render_contract import ensure_builtin_pdf_component, ensure_pdf_group
from InkGen.style import DrawingStyle, Font, TextStyle
from InkGen.svg_generator import LabelGenerator, SegmentGenerator


@pytest.fixture
def drawing_style() -> DrawingStyle:
    """Return a unique drawing style for PDF tests."""
    return DrawingStyle(name=f"pdf_style_{uuid.uuid4().hex}", stroke="#000000", stroke_width=0.2, fill="none")


@pytest.fixture
def text_style() -> TextStyle:
    """Return a unique text style for PDF tests."""
    return TextStyle(name=f"pdf_text_{uuid.uuid4().hex}", font=Font(size=12.0))


def _stream(pdf_bytes: bytes) -> str:
    matches = re.findall(rb"stream\n(?P<content>.*?)\nendstream", pdf_bytes, re.S)
    for match in matches:
        content = match.decode("latin-1")
        if " BT\n" in content or " cm\n" in content:
            return content
    raise AssertionError("PDF page content stream not found")


def _pdf_objects(pdf_bytes: bytes) -> dict[int, bytes]:
    return {
        int(match.group("id")): match.group("payload")
        for match in re.finditer(rb"(?P<id>\d+) 0 obj\n(?P<payload>.*?)\nendobj", pdf_bytes, re.S)
    }


def _assert_contiguous_object_ids(pdf_bytes: bytes) -> None:
    object_ids = sorted(_pdf_objects(pdf_bytes))
    assert object_ids == list(range(1, max(object_ids) + 1))


def _pdf_bytes_for_single_text_style(style: TextStyle) -> bytes:
    canvas = Canvas(100.0, 80.0)
    document = DocumentPDF(canvas)
    document.add_page()
    group = ComponentGroupPDF("font")
    group.add_component(TextPDF("Font", (10.0, 20.0), style))
    document.page(1).layer("base").add_component_group(group)
    return document.to_pdf_bytes()


def _quadratic_point(
    start: tuple[float, float],
    control: tuple[float, float],
    end: tuple[float, float],
    t: float,
) -> tuple[float, float]:
    one_minus_t = 1.0 - t
    return (
        one_minus_t**2 * start[0] + 2 * one_minus_t * t * control[0] + t**2 * end[0],
        one_minus_t**2 * start[1] + 2 * one_minus_t * t * control[1] + t**2 * end[1],
    )


def _cubic_point(
    start: tuple[float, float],
    control_1: tuple[float, float],
    control_2: tuple[float, float],
    end: tuple[float, float],
    t: float,
) -> tuple[float, float]:
    one_minus_t = 1.0 - t
    return (
        one_minus_t**3 * start[0] + 3 * one_minus_t**2 * t * control_1[0] + 3 * one_minus_t * t**2 * control_2[0] + t**3 * end[0],
        one_minus_t**3 * start[1] + 3 * one_minus_t**2 * t * control_1[1] + 3 * one_minus_t * t**2 * control_2[1] + t**3 * end[1],
    )


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
    assert issubclass(ComponentGroupPDF, LabelGenerator)
    assert issubclass(ComponentGroupPDF, SegmentGenerator)


@pytest.mark.condition("PDF-P1")
def test_pdf_backend_primitive_surface_matches_svg_backend() -> None:
    """PDF-P1: The PDF primitive surface stays paired with the SVG primitive surface."""
    non_primitive_stems = {"ComponentGroup", "Document", "SVGComponent", "Table"}
    svg_stems = {
        name.removesuffix("SVG") for name, value in vars(svg_generator_module).items() if isinstance(value, type) and name.endswith("SVG")
    } - non_primitive_stems
    pdf_stems = {
        name.removesuffix("PDF") for name, value in vars(pdf_generator_module).items() if isinstance(value, type) and name.endswith("PDF")
    } - non_primitive_stems

    assert pdf_stems == svg_stems


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
def test_path_pdf_emits_supported_svg_path_commands(drawing_style: DrawingStyle) -> None:
    """PDF-P1: PathPDF maps supported SVG-style path commands to PDF operators."""
    path = PathPDF(
        drawing_style,
        commands=[
            PathCommand("M", [(1.0, 2.0)]),
            PathCommand("H", [(5.0, 0.0)]),
            PathCommand("V", [(0.0, 6.0)]),
            PathCommand("Q", [(7.0, 8.0), (9.0, 10.0)]),
            PathCommand("C", [(11.0, 12.0), (13.0, 14.0), (15.0, 16.0)]),
            PathCommand("A", [(17.0, 18.0)]),
            PathCommand("Z", []),
        ],
    )

    content = path.generate_pdf()

    assert "1 2 m" in content
    assert "5 2 l" in content
    assert "5 6 l" in content
    assert "6.333333 7.333333 7.666667 8.666667 9 10 c" in content
    assert "11 12 13 14 15 16 c" in content
    assert "17 18 l" in content
    assert "\nh\n" in content


@pytest.mark.condition("CURVE-P1")
def test_pdf_quadratic_to_cubic_conversion_is_curve_equivalent() -> None:
    """CURVE-P1: PDF quadratic conversion preserves the quadratic Bezier curve."""
    cases = [
        ((0.0, 0.0), (1.0, 1.0), (2.0, 0.0)),
        ((-3.0, 4.0), (8.0, -2.0), (12.0, 6.0)),
        ((5.5, -1.25), (5.5, 8.75), (5.5, 3.5)),
    ]
    samples = (0.0, 0.125, 0.25, 0.5, 0.75, 0.875, 1.0)

    for start, control, end in cases:
        control_1, control_2 = pdf_generator_module._quadratic_to_cubic(start, control, end)

        assert control_1 == (
            pytest.approx(start[0] + (2.0 / 3.0) * (control[0] - start[0])),
            pytest.approx(start[1] + (2.0 / 3.0) * (control[1] - start[1])),
        )
        assert control_2 == (
            pytest.approx(end[0] + (2.0 / 3.0) * (control[0] - end[0])),
            pytest.approx(end[1] + (2.0 / 3.0) * (control[1] - end[1])),
        )
        for t in samples:
            quadratic = _quadratic_point(start, control, end, t)
            cubic = _cubic_point(start, control_1, control_2, end, t)
            assert cubic == (pytest.approx(quadratic[0]), pytest.approx(quadratic[1]))


@pytest.mark.condition("CURVE-P1")
def test_quadratic_bezier_pdf_emits_equivalent_cubic_operator(drawing_style: DrawingStyle) -> None:
    """CURVE-P1: QuadraticBezierPDF emits the mathematically equivalent cubic operator."""
    drawing_style.fill = "#ffffff"
    curve = QuadraticBezierPDF((1.0, 2.0), (4.0, 11.0), (10.0, 2.0), drawing_style)

    content = curve.generate_pdf()

    assert "1 2 m" in content
    assert "3 8 6 8 10 2 c" in content
    assert content.endswith("\nS\nQ")


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


@pytest.mark.condition("PDF-FONT-STANDARD-P2")
def test_document_pdf_maps_text_styles_to_standard_font_resources() -> None:
    """PDF-FONT-STANDARD-P2: PDF text uses built-in font resources from TextStyle."""
    canvas = Canvas(100.0, 80.0)
    document = DocumentPDF(canvas)
    document.add_page()
    times_style = TextStyle(f"times_{uuid.uuid4().hex}", Font(family="serif", style="italic", weight="bold", size=11.0))
    courier_style = TextStyle(f"mono_{uuid.uuid4().hex}", Font(family="monospace", size=9.0))
    group = ComponentGroupPDF("fonts")
    group.add_component(TextPDF("Times", (10.0, 20.0), times_style))
    group.add_component(TextPDF("Mono", (10.0, 35.0), courier_style))
    document.page(1).layer("base").add_component_group(group)

    payload = document.to_pdf_bytes()
    content = _stream(payload)

    assert b"/BaseFont /Times-BoldItalic" in payload
    assert b"/BaseFont /Courier" in payload
    assert payload.count(b"/ToUnicode ") == 2
    assert payload.count(b"/CMapName /InkGen-WinAnsi-UCS2") == 2
    assert payload.count(b"95 beginbfchar") == 2
    assert b"<7F> <007F>" not in payload
    assert "/F1 11 Tf" in content
    assert "/F2 9 Tf" in content


@pytest.mark.condition("PDF-FONT-STANDARD-P2")
@pytest.mark.parametrize(
    ("family", "font_style", "weight", "base_font"),
    [
        ("monospace", "normal", "normal", "Courier"),
        ("monospace", "normal", "bold", "Courier-Bold"),
        ("monospace", "oblique", "normal", "Courier-Oblique"),
        ("monospace", "italic", "bold", "Courier-BoldOblique"),
        ("serif", "normal", "normal", "Times-Roman"),
        ("serif", "normal", "semibold", "Times-Bold"),
        ("serif", "italic", "normal", "Times-Italic"),
        ("serif", "italic", "bold", "Times-BoldItalic"),
        ("sans-serif", "normal", 600, "Helvetica-Bold"),
        ("sans-serif", "normal", 700, "Helvetica-Bold"),
        ("sans-serif", "oblique", "normal", "Helvetica-Oblique"),
    ],
)
def test_document_pdf_maps_standard_font_variants(
    family: str,
    font_style: str,
    weight: str | int,
    base_font: str,
) -> None:
    """PDF-FONT-STANDARD-P2: Standard font mapping covers family/style/weight variants."""
    style = TextStyle(
        f"variant_{uuid.uuid4().hex}",
        Font(family=family, style=font_style, weight=weight, size=10.0),
    )

    payload = _pdf_bytes_for_single_text_style(style)

    assert f"/BaseFont /{base_font}".encode("latin-1") in payload
    assert "/F1 10 Tf" in _stream(payload)


@pytest.mark.condition("PDF-FONT-STANDARD-P2")
def test_document_pdf_numeric_weight_threshold_keeps_599_regular() -> None:
    """PDF-FONT-STANDARD-P2: Numeric weights below 600 stay regular."""
    style = TextStyle(
        f"regular_{uuid.uuid4().hex}",
        Font(family="sans-serif", weight=599, size=10.0),
    )

    payload = _pdf_bytes_for_single_text_style(style)

    assert b"/BaseFont /Helvetica /Encoding" in payload
    assert b"/BaseFont /Helvetica-Bold" not in payload


@pytest.mark.condition("PDF-FONT-TOUNICODE-P3")
def test_document_pdf_standard_fonts_emit_tounicode_cmaps() -> None:
    """PDF-FONT-TOUNICODE-P3: Standard PDF fonts include extraction CMaps."""
    payload = _pdf_bytes_for_single_text_style(TextStyle(f"unicode_{uuid.uuid4().hex}", Font(size=10.0)))

    assert b"/Subtype /Type1" in payload
    assert b"/ToUnicode " in payload
    assert b"/CMapName /InkGen-WinAnsi-UCS2" in payload
    assert b"95 beginbfchar" in payload
    assert b"<20> <0020>" in payload
    assert b"<41> <0041>" in payload
    assert b"<7E> <007E>" in payload
    assert b"<7F> <007F>" not in payload


@pytest.mark.condition("PDF-FONT-EMBED-P3")
def test_document_pdf_embeds_named_installed_font_resources() -> None:
    """PDF-FONT-EMBED-P3: Named installed fonts embed with widths and descriptors."""
    font = Font(family="DejaVu Sans", size=10.0)
    style = TextStyle(f"embedded_{uuid.uuid4().hex}", font)

    payload = _pdf_bytes_for_single_text_style(style)

    assert b"/Subtype /TrueType" in payload
    assert b"/FontDescriptor" in payload
    assert b"/FontFile2" in payload
    assert b"/FirstChar 32 /LastChar 126" in payload
    assert b"/Widths [" in payload
    assert b"/Encoding /WinAnsiEncoding" in payload
    assert b"/ToUnicode " in payload
    assert b"/CMapName /InkGen-WinAnsi-UCS2" in payload
    assert b"/BaseFont /Helvetica" not in payload
    assert b"/F1 10 Tf" in payload
    assert b"/Resources << /Font <<" in payload
    assert b"/XObject" not in payload
    _assert_contiguous_object_ids(payload)
    objects = _pdf_objects(payload)
    font_resource_match = re.search(rb"/Resources << /Font << /F1 (?P<id>\d+) 0 R", payload)
    assert font_resource_match is not None
    font_object = objects[int(font_resource_match.group("id"))]
    descriptor_match = re.search(rb"/FontDescriptor (?P<id>\d+) 0 R", font_object)
    tounicode_match = re.search(rb"/ToUnicode (?P<id>\d+) 0 R", font_object)
    assert descriptor_match is not None
    assert tounicode_match is not None
    assert b"/Type /FontDescriptor" in objects[int(descriptor_match.group("id"))]
    assert b"/CMapName /InkGen-WinAnsi-UCS2" in objects[int(tounicode_match.group("id"))]


@pytest.mark.condition("PDF-FONT-EMBED-P3")
def test_document_pdf_reuses_embedded_font_resources_across_sizes() -> None:
    """PDF-FONT-EMBED-P3: Same named font file shares one embedded PDF resource."""
    font = Font(family="DejaVu Sans", size=10.0)
    first_style = TextStyle(f"embedded_first_{uuid.uuid4().hex}", font)
    second_style = TextStyle(f"embedded_second_{uuid.uuid4().hex}", Font(family="DejaVu Sans", size=18.0))
    canvas = Canvas(100.0, 80.0)
    document = DocumentPDF(canvas)
    document.add_page()
    group = ComponentGroupPDF("embedded-fonts")
    group.add_component(TextPDF("Small", (10.0, 20.0), first_style))
    group.add_component(TextPDF("Large", (10.0, 40.0), second_style))
    document.page(1).layer("base").add_component_group(group)

    payload = document.to_pdf_bytes()

    assert payload.count(b"/FontFile2") == 1
    assert b"/F1 10 Tf" in payload
    assert b"/F1 18 Tf" in payload


@pytest.mark.condition("PDF-FONT-EMBED-P3")
def test_pdf_embedded_font_helpers_cover_missing_glyphs_and_open_type_streams() -> None:
    """PDF-FONT-EMBED-P3: Embedded-font helpers handle fallback boundaries."""
    assert pdf_generator_module._pdf_glyph_width(65, {}, {}, 1000) == 0  # noqa: SLF001
    assert pdf_generator_module._pdf_glyph_width(65, {65: "A"}, {"A": (500, 0)}, 1000) == 500  # noqa: SLF001
    assert pdf_generator_module._pdf_name("A B") == "A#20B"  # noqa: SLF001
    assert pdf_generator_module._pdf_name("é") == "EmbeddedFont"  # noqa: SLF001

    missing_data = pdf_generator_module._PDFFontResource(
        resource_name="F1",
        base_font="Bad",
        font_file="bad.otf",
        font_data=None,
        font_file_key="FontFile3",
    )
    with pytest.raises(ValueError, match="font data"):
        pdf_generator_module._pdf_font_file_object(missing_data)  # noqa: SLF001

    open_type = pdf_generator_module._PDFFontResource(
        resource_name="F1",
        base_font="OpenType",
        font_file="font.otf",
        font_data=b"font-data",
        font_file_key="FontFile3",
    )

    assert b"/Subtype /OpenType" in pdf_generator_module._pdf_font_file_object(open_type)  # noqa: SLF001

    true_type = pdf_generator_module._PDFFontResource(
        resource_name="F1",
        base_font="TrueType",
        font_file="font.ttf",
        font_data=b"font-data",
        font_file_key="FontFile2",
    )

    assert b"/Subtype /OpenType" not in pdf_generator_module._pdf_font_file_object(true_type)  # noqa: SLF001


@pytest.mark.condition("PDF-FONT-EMBED-P3")
def test_pdf_embedded_font_lookup_falls_back_for_missing_font_files() -> None:
    """PDF-FONT-EMBED-P3: Missing named font files fall back to Standard fonts."""

    class MissingFont:
        requested_family = "Missing Font"
        font_file = "C:/definitely/missing/font.ttf"

    class StyleWithMissingFont:
        font = MissingFont()

    assert pdf_generator_module._pdf_embedded_font_for_style(StyleWithMissingFont()) is None  # noqa: SLF001


@pytest.mark.condition("PDF-FONT-STANDARD-P2")
def test_document_pdf_empty_page_has_no_font_resource_dictionary() -> None:
    """PDF-FONT-STANDARD-P2: Empty pages do not emit unused font resources."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()

    payload = document.to_pdf_bytes()

    assert b"/Font <<" not in payload


@pytest.mark.condition("PDF-P1")
def test_component_group_pdf_rejects_non_pdf_components() -> None:
    """PDF-P1: ComponentGroupPDF rejects components outside the closed PDF set."""

    class CustomPDFComponent(Component):
        def generate_pdf(self, context: object | None = None) -> str:
            return "custom"

    group = ComponentGroupPDF("bad")
    custom = CustomPDFComponent()

    with pytest.raises(TypeError, match="only accepts built-in PDF components"):
        group.add_component(custom)

    group._components[custom.id] = custom
    with pytest.raises(TypeError, match="only renders built-in PDF components"):
        group.generate_pdf()


@pytest.mark.condition("PDF-P3")
def test_pdf_render_contract_helpers_keep_keyword_only_message() -> None:
    """PDF-P3: PDF render-contract guards keep diagnostic messages keyword-only."""
    with pytest.raises(TypeError, match="positional"):
        ensure_builtin_pdf_component(Component(), (), "message")
    with pytest.raises(TypeError, match="positional"):
        ensure_pdf_group(object(), object, "message")


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
def test_component_group_pdf_exposes_renderer_agnostic_truth(drawing_style: DrawingStyle) -> None:
    """PDF-P1: ComponentGroupPDF exposes labels and masks using shared geometry."""
    group = ComponentGroupPDF("truth")
    group.add_component(RectanglePDF((10.0, 20.0), 30.0, 40.0, 0.0, drawing_style))

    assert group.generate_label() == {"truth": group.bbox}
    assert group.generate_segmentation_mask() == {"truth": group.convex_hull}


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
    tmp_path: Path,
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
    pathlike_target = tmp_path / "pathlike.pdf"
    document.create_pdf(pathlike_target)
    assert pathlike_target.read_bytes() == document.to_pdf_bytes()
    with pytest.raises(ValueError, match="file path does not exist"):
        document.create_pdf(str(tmp_path / "missing" / "seed.pdf"))


@pytest.mark.condition("PDF-P1")
@pytest.mark.parametrize(
    ("filepath", "exception_type", "message"),
    [
        (object(), TypeError, "file path must be a string or path-like object"),
        (123, TypeError, "file path must be a string or path-like object"),
        (b"seed.pdf", TypeError, "file path must be a string or path-like object"),
        ("", ValueError, "file path must not be empty"),
    ],
)
def test_document_pdf_create_pdf_rejects_malformed_paths(
    filepath: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """PDF-P1: create_pdf rejects malformed paths at the writer boundary."""
    document = DocumentPDF(Canvas(100.0, 80.0))

    with pytest.raises(exception_type, match=message):
        document.create_pdf(filepath)  # type: ignore[arg-type]


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
    """PDF-P1: DocumentPDF fails loudly when a page contains a non-PDF group."""
    canvas = Canvas(100.0, 80.0)
    document = DocumentPDF(canvas)
    document.add_page()
    group = ComponentGroup("mixed")
    group.add_component(RectanglePDF((10.0, 20.0), 30.0, 40.0, 0.0, drawing_style))
    document.page(1).layer("base").add_component_group(group)

    with pytest.raises(TypeError, match="DocumentPDF pages must contain ComponentGroupPDF"):
        document.to_pdf_bytes()
