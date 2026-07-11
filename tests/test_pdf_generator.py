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


@pytest.mark.condition("PDF-GRAPHICS-STATE-P3")
def test_document_pdf_emits_extgstate_for_drawing_opacity() -> None:
    """PDF-GRAPHICS-STATE-P3: DocumentPDF maps drawing opacity to ExtGState resources."""
    style = DrawingStyle(
        f"transparent_{uuid.uuid4().hex}",
        stroke="#112233",
        fill="#445566",
        stroke_width=0.5,
        stroke_opacity=0.25,
        fill_opacity=0.75,
    )
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    group = ComponentGroupPDF("opacity")
    group.add_component(RectanglePDF((1.0, 2.0), 3.0, 4.0, 0.0, style))
    document.page(1).layer("base").add_component_group(group)

    payload = document.to_pdf_bytes()
    content = _stream(payload)

    assert b"/ExtGState << /GS1" in payload
    assert b"<< /Type /ExtGState /CA 0.25 /ca 0.75 >>" in payload
    _assert_contiguous_object_ids(payload)
    objects = _pdf_objects(payload)
    resource_match = re.search(rb"/ExtGState << /GS1 (?P<id>\d+) 0 R", payload)
    assert resource_match is not None
    assert objects[int(resource_match.group("id"))] == b"<< /Type /ExtGState /CA 0.25 /ca 0.75 >>"
    assert "/GS1 gs\n0.066667 0.133333 0.2 RG" in content
    assert "0.266667 0.333333 0.4 rg" in content


@pytest.mark.condition("PDF-GRAPHICS-STATE-P3")
def test_document_pdf_reuses_opacity_extgstate_resources() -> None:
    """PDF-GRAPHICS-STATE-P3: Equal opacity tuples share one ExtGState resource."""
    style = DrawingStyle(
        f"transparent_reuse_{uuid.uuid4().hex}",
        stroke="#000000",
        fill="#ffffff",
        stroke_opacity=0.5,
        fill_opacity=0.25,
    )
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    group = ComponentGroupPDF("opacity-reuse")
    group.add_component(RectanglePDF((1.0, 2.0), 3.0, 4.0, 0.0, style))
    group.add_component(CirclePDF((10.0, 10.0), 2.0, style))
    document.page(1).layer("base").add_component_group(group)

    payload = document.to_pdf_bytes()
    content = _stream(payload)

    assert payload.count(b"/Type /ExtGState") == 1
    assert content.count("/GS1 gs") == 2


@pytest.mark.condition("PDF-GRAPHICS-STATE-P3")
def test_document_pdf_separates_stroke_and_fill_opacity_domains() -> None:
    """PDF-GRAPHICS-STATE-P3: Stroke-only and fill-only paths ignore unused opacity channels."""
    style = DrawingStyle(
        f"transparent_channels_{uuid.uuid4().hex}",
        stroke="#000000",
        fill="#ffffff",
        stroke_opacity=0.25,
        fill_opacity=0.5,
    )
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    group = ComponentGroupPDF("opacity-channels")
    group.add_component(LinePDF((1.0, 2.0), (3.0, 4.0), style))
    group.add_component(RectanglePDF((5.0, 6.0), 7.0, 8.0, 0.0, style))
    document.page(1).layer("base").add_component_group(group)

    payload = document.to_pdf_bytes()
    content = _stream(payload)

    assert b"/GS1" in payload
    assert b"/GS2" in payload
    assert b"<< /Type /ExtGState /CA 0.25 /ca 1 >>" in payload
    assert b"<< /Type /ExtGState /CA 0.25 /ca 0.5 >>" in payload
    assert "/GS1 gs\n0 0 0 RG" in content
    assert "/GS2 gs\n0 0 0 RG" in content


@pytest.mark.condition("PDF-GRAPHICS-STATE-P3")
def test_document_pdf_omits_extgstate_for_opaque_drawings(drawing_style: DrawingStyle) -> None:
    """PDF-GRAPHICS-STATE-P3: Opaque drawing styles do not create ExtGState resources."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    group = ComponentGroupPDF("opaque")
    group.add_component(RectanglePDF((1.0, 2.0), 3.0, 4.0, 0.0, drawing_style))
    document.page(1).layer("base").add_component_group(group)

    payload = document.to_pdf_bytes()

    assert b"/ExtGState" not in payload
    assert " gs" not in _stream(payload)


@pytest.mark.condition("PDF-GRAPHICS-STATE-P3")
def test_pdf_opacity_helpers_validate_boundaries_and_reuse_resources() -> None:
    """PDF-GRAPHICS-STATE-P3: Opacity helper boundaries and resource reuse are explicit."""
    registry = pdf_generator_module._PDFGraphicsStateRegistry()  # noqa: SLF001

    assert pdf_generator_module._opacity_value(0.0, "alpha") == 0.0  # noqa: SLF001
    assert pdf_generator_module._opacity_value(1.0, "alpha") == 1.0  # noqa: SLF001
    assert registry.resource_name_for_opacity(stroke_opacity=1.0, fill_opacity=1.0) is None
    assert registry.resource_name_for_opacity(stroke_opacity=0.5, fill_opacity=1.0) == "GS1"
    assert registry.resource_name_for_opacity(stroke_opacity=1.0, fill_opacity=0.25) == "GS2"
    assert registry.resource_name_for_opacity(stroke_opacity=0.5, fill_opacity=1.0) == "GS1"
    assert registry.resources() == (("GS1", 0.5, 1.0), ("GS2", 1.0, 0.25))
    assert pdf_generator_module._pdf_extgstate_object(stroke_opacity=0.5, fill_opacity=1.0) == (  # noqa: SLF001
        "<< /Type /ExtGState /CA 0.5 /ca 1 >>"
    )
    for value in (True, -0.001, 1.001, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="alpha"):
            pdf_generator_module._opacity_value(value, "alpha")  # noqa: SLF001


@pytest.mark.condition("PDF-GROUP-BLEND-P3")
def test_document_pdf_emits_group_blend_mode_extgstate(drawing_style: DrawingStyle) -> None:
    """PDF-GROUP-BLEND-P3: DocumentPDF maps group blend modes to ExtGState resources."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    group = ComponentGroupPDF("blend")
    group.set_blend_mode("Multiply")
    group.add_component(RectanglePDF((1.0, 2.0), 3.0, 4.0, 0.0, drawing_style))
    document.page(1).layer("base").add_component_group(group)

    payload = document.to_pdf_bytes()
    content = _stream(payload)
    objects = _pdf_objects(payload)
    resource_match = re.search(rb"/ExtGState << /GS1 (?P<id>\d+) 0 R", payload)

    _assert_contiguous_object_ids(payload)
    assert resource_match is not None
    assert objects[int(resource_match.group("id"))] == b"<< /Type /ExtGState /BM /Multiply >>"
    assert "q\n1 0 0 -1 0 80 cm\nq\n/GS1 gs\nq\n0 0 0 RG" in content


@pytest.mark.condition("PDF-GROUP-BLEND-P3")
def test_document_pdf_combines_group_blend_and_clip_controls(drawing_style: DrawingStyle) -> None:
    """PDF-GROUP-BLEND-P3: Group blend and clip controls share one group graphics-state wrapper."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    group = ComponentGroupPDF("blend-clip")
    group.set_blend_mode("Screen")
    group.set_clip_rect((1.0, 2.0, 30.0, 40.0))
    group.add_component(RectanglePDF((10.0, 20.0), 3.0, 4.0, 0.0, drawing_style))
    document.page(1).layer("base").add_component_group(group)

    content = _stream(document.to_pdf_bytes())

    assert "q\n1 0 0 -1 0 80 cm\nq\n/GS1 gs\n1 2 30 40 re\nW\nn\nq\n0 0 0 RG" in content


@pytest.mark.condition("PDF-GROUP-BLEND-P3")
def test_pdf_blend_mode_helpers_validate_normalize_and_reuse_resources() -> None:
    """PDF-GROUP-BLEND-P3: Blend mode helpers normalize standard modes and reuse resources."""
    registry = pdf_generator_module._PDFGraphicsStateRegistry()  # noqa: SLF001

    assert pdf_generator_module._coerce_pdf_blend_mode(None) is None  # noqa: SLF001
    assert pdf_generator_module._coerce_pdf_blend_mode("Normal") is None  # noqa: SLF001
    assert pdf_generator_module._coerce_pdf_blend_mode("color-dodge") == "ColorDodge"  # noqa: SLF001
    assert registry.resource_name_for_blend_mode("screen") == "GS1"
    assert registry.resource_name_for_blend_mode("Screen") == "GS1"
    assert registry.resource_name_for_blend_mode("hard light") == "GS2"
    assert registry.resource_name_for_opacity(stroke_opacity=0.5, fill_opacity=1.0) == "GS3"
    assert registry.blend_mode_resources() == (("GS1", "Screen"), ("GS2", "HardLight"))
    assert pdf_generator_module._pdf_blend_mode_extgstate_object("soft_light") == "<< /Type /ExtGState /BM /SoftLight >>"  # noqa: SLF001


@pytest.mark.condition("PDF-GROUP-BLEND-P3")
def test_component_group_pdf_blend_mode_round_trips(drawing_style: DrawingStyle) -> None:
    """PDF-GROUP-BLEND-P3: Group blend modes serialize and hydrate deterministically."""
    group = ComponentGroupPDF("blend-roundtrip")
    group.set_blend_mode("soft-light")
    group.add_component(RectanglePDF((1.0, 2.0), 3.0, 4.0, 0.0, drawing_style))

    recreated = ComponentGroupPDF.create_from_dict(group.parameters, {drawing_style.name: drawing_style})

    assert group.parameters["ComponentGroupPDF"]["blend_mode"] == "SoftLight"
    assert recreated.blend_mode() == "SoftLight"
    assert recreated.parameters == group.parameters

    group.set_blend_mode("Normal")
    assert group.blend_mode() is None
    assert "blend_mode" not in group.parameters["ComponentGroupPDF"]


@pytest.mark.condition("PDF-GROUP-BLEND-P3")
@pytest.mark.parametrize("blend_mode", [object(), "", "not-a-mode"])
def test_component_group_pdf_rejects_malformed_blend_modes(blend_mode: object) -> None:
    """PDF-GROUP-BLEND-P3: Malformed blend modes fail before group state mutation."""
    group = ComponentGroupPDF("bad-blend")
    group.set_blend_mode("Multiply")

    with pytest.raises((TypeError, ValueError), match="PDF blend mode"):
        group.set_blend_mode(blend_mode)

    assert group.blend_mode() == "Multiply"


@pytest.mark.condition("PDF-GROUP-BLEND-P3")
def test_component_group_pdf_factory_rejects_malformed_blend_modes() -> None:
    """PDF-GROUP-BLEND-P3: Group hydration rejects malformed serialized blend modes."""
    payload = {"ComponentGroupPDF": {"group_label": "bad-blend", "components": [], "blend_mode": "not-a-mode"}}

    with pytest.raises(ValueError, match="PDF blend mode must be a standard PDF blend mode"):
        ComponentGroupPDF.create_from_dict(payload)


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
    assert payload.count(b"100 beginbfchar") == 4
    assert payload.count(b"18 beginbfchar") == 2
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
    assert payload.count(b"100 beginbfchar") == 2
    assert b"18 beginbfchar" in payload
    assert b"<20> <0020>" in payload
    assert b"<41> <0041>" in payload
    assert b"<7E> <007E>" in payload
    assert b"<7F> <007F>" not in payload
    assert b"<80> <20AC>" in payload
    assert b"<81>" not in payload
    assert b"<E9> <00E9>" in payload


@pytest.mark.condition("PDF-FONT-EMBED-P3")
def test_document_pdf_embeds_named_installed_font_resources() -> None:
    """PDF-FONT-EMBED-P3: Named installed fonts embed with widths and descriptors."""
    font = Font(family="DejaVu Sans", size=10.0)
    style = TextStyle(f"embedded_{uuid.uuid4().hex}", font)

    payload = _pdf_bytes_for_single_text_style(style)

    assert b"/Subtype /TrueType" in payload
    assert b"/FontDescriptor" in payload
    assert b"/FontFile2" in payload
    assert b"/FirstChar 32 /LastChar 255" in payload
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
    assert pdf_generator_module._pdf_glyph_width(0x7F, {0x7F: "DEL"}, {"DEL": (500, 0)}, 1000) == 0  # noqa: SLF001
    assert pdf_generator_module._pdf_glyph_width(65, {65: "A"}, {}, 1000) == 0  # noqa: SLF001
    assert pdf_generator_module._pdf_name("A B") == "A#20B"  # noqa: SLF001
    assert pdf_generator_module._pdf_name("é") == "EmbeddedFont"  # noqa: SLF001
    assert pdf_generator_module._escape_pdf_string("Café € –") == r"Caf\351 \200 \226"  # noqa: SLF001
    assert pdf_generator_module._escape_pdf_string("\b\t\n\f\r()\\ ~") == r"\b\t\n\f\r\(\)\\ ~"  # noqa: SLF001
    assert pdf_generator_module._escape_pdf_string("\x1f") == r"\037"  # noqa: SLF001
    assert pdf_generator_module._escape_pdf_string("\x7f") == r"\177"  # noqa: SLF001
    with pytest.raises(ValueError, match="WinAnsi"):
        pdf_generator_module._coerce_pdf_literal_string("\n\t", "test field")  # noqa: SLF001
    assert pdf_generator_module._escape_pdf_text_string("\x1f") == r"\037"  # noqa: SLF001
    assert pdf_generator_module._escape_pdf_text_string("\x7f") == r"\177"  # noqa: SLF001

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


@pytest.mark.condition("PDF-GROUP-CLIP-P3")
def test_component_group_pdf_emits_rectangular_clip_path(drawing_style: DrawingStyle) -> None:
    """PDF-GROUP-CLIP-P3: ComponentGroupPDF wraps children in a rectangular clip path."""
    group = ComponentGroupPDF("clip")
    group.set_clip_rect((1.0, 2.0, 30.0, 40.0))
    group.add_component(RectanglePDF((10.0, 20.0), 3.0, 4.0, 0.0, drawing_style))

    content = group.generate_pdf()

    assert content.startswith("q\n1 2 30 40 re\nW\nn\n")
    assert content.endswith("\nQ")
    assert content.index("W\nn") < content.index("10 20 3 4 re")


@pytest.mark.condition("PDF-GROUP-CLIP-P3")
def test_document_pdf_consumes_group_clip_path_live(drawing_style: DrawingStyle) -> None:
    """PDF-GROUP-CLIP-P3: DocumentPDF emits configured group clipping in page content."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    group = ComponentGroupPDF("clip-live")
    group.set_clip_rect((1.0, 2.0, 30.0, 40.0))
    group.add_component(RectanglePDF((10.0, 20.0), 3.0, 4.0, 0.0, drawing_style))
    document.page(1).layer("base").add_component_group(group)

    content = _stream(document.to_pdf_bytes())

    assert "1 0 0 -1 0 80 cm\nq\n1 2 30 40 re\nW\nn" in content
    assert content.index("W\nn") < content.index("10 20 3 4 re")


@pytest.mark.condition("PDF-GROUP-CLIP-P3")
def test_component_group_pdf_clip_rect_round_trips(drawing_style: DrawingStyle) -> None:
    """PDF-GROUP-CLIP-P3: Group clip rectangles serialize and hydrate deterministically."""
    group = ComponentGroupPDF("clip-roundtrip")
    group.set_clip_rect((1.0, 2.0, 30.0, 40.0))
    group.add_component(RectanglePDF((10.0, 20.0), 3.0, 4.0, 0.0, drawing_style))

    recreated = ComponentGroupPDF.create_from_dict(group.parameters, {drawing_style.name: drawing_style})

    assert group.parameters["ComponentGroupPDF"]["clip_rect"] == [1.0, 2.0, 30.0, 40.0]
    assert recreated.clip_rect() == (1.0, 2.0, 30.0, 40.0)
    assert recreated.parameters == group.parameters
    assert recreated.generate_pdf() == group.generate_pdf()


@pytest.mark.condition("PDF-GROUP-CLIP-P3")
def test_component_group_pdf_emits_arbitrary_clip_path(drawing_style: DrawingStyle) -> None:
    """PDF-GROUP-CLIP-P3: ComponentGroupPDF emits a closed path clipping operator."""
    group = ComponentGroupPDF("clip-path")
    group.set_clip_path(
        [
            PathCommand("M", [(1.0, 2.0)]),
            PathCommand("L", [(31.0, 2.0), (16.0, 42.0)]),
            PathCommand("Z", []),
        ]
    )
    group.add_component(RectanglePDF((10.0, 20.0), 3.0, 4.0, 0.0, drawing_style))

    content = group.generate_pdf()

    assert content.startswith("q\n1 2 m\n31 2 l\n16 42 l\nh\nW\nn\n")
    assert content.endswith("\nQ")
    assert content.index("W\nn") < content.index("10 20 3 4 re")


@pytest.mark.condition("PDF-GROUP-CLIP-P3")
def test_document_pdf_consumes_group_clip_path_with_rect_and_blend_live(drawing_style: DrawingStyle) -> None:
    """PDF-GROUP-CLIP-P3: Path clipping composes with rectangle clipping and blend state."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    group = ComponentGroupPDF("clip-path-live")
    group.set_blend_mode("Screen")
    group.set_clip_rect((1.0, 2.0, 30.0, 40.0))
    group.set_clip_path(
        [
            PathCommand("M", [(2.0, 3.0)]),
            PathCommand("L", [(20.0, 3.0), (20.0, 30.0)]),
            PathCommand("Z", []),
        ]
    )
    group.add_component(RectanglePDF((10.0, 20.0), 3.0, 4.0, 0.0, drawing_style))
    document.page(1).layer("base").add_component_group(group)

    content = _stream(document.to_pdf_bytes())

    expected = "q\n1 0 0 -1 0 80 cm\nq\n/GS1 gs\n1 2 30 40 re\nW\nn\n2 3 m\n20 3 l\n20 30 l\nh\nW\nn"
    assert expected in content
    assert content.index("/GS1 gs") < content.index("1 2 30 40 re")
    assert content.index("1 2 30 40 re") < content.index("2 3 m")
    assert content.index("2 3 m") < content.index("10 20 3 4 re")


@pytest.mark.condition("PDF-GROUP-CLIP-P3")
def test_component_group_pdf_evenodd_clip_rule_applies_to_rect_and_path(drawing_style: DrawingStyle) -> None:
    """PDF-GROUP-CLIP-P3: Even-odd clip rules emit W* for every group clip."""
    group = ComponentGroupPDF("clip-rule")
    group.set_clip_rule("even-odd")
    group.set_clip_rect((1.0, 2.0, 30.0, 40.0))
    group.set_clip_path(
        [
            PathCommand("M", [(2.0, 3.0)]),
            PathCommand("L", [(20.0, 3.0), (20.0, 30.0)]),
            PathCommand("Z", []),
        ]
    )
    group.add_component(RectanglePDF((10.0, 20.0), 3.0, 4.0, 0.0, drawing_style))

    content = group.generate_pdf()

    assert "1 2 30 40 re\nW*\nn\n2 3 m\n20 3 l\n20 30 l\nh\nW*\nn\n" in content
    assert "\nW\n" not in content
    assert content.index("W*\nn") < content.index("10 20 3 4 re")


@pytest.mark.condition("PDF-GROUP-CLIP-P3")
def test_component_group_pdf_clip_path_round_trips_and_returns_detached_commands(drawing_style: DrawingStyle) -> None:
    """PDF-GROUP-CLIP-P3: Group clip paths serialize, hydrate, and avoid aliasing."""
    commands = [
        PathCommand("M", [(1.0, 2.0)]),
        PathCommand("Q", [(5.0, 8.0), (9.0, 2.0)]),
        PathCommand("Z", []),
    ]
    group = ComponentGroupPDF("clip-path-roundtrip")
    group.set_clip_path(commands)
    group.add_component(RectanglePDF((10.0, 20.0), 3.0, 4.0, 0.0, drawing_style))
    commands[0].add_point((99.0, 99.0))

    recreated = ComponentGroupPDF.create_from_dict(group.parameters, {drawing_style.name: drawing_style})
    returned = group.clip_path()
    assert returned is not None
    returned[0].add_point((50.0, 50.0))

    assert group.parameters["ComponentGroupPDF"]["clip_path"] == [
        {"type": "M", "points": [(1.0, 2.0)]},
        {"type": "Q", "points": [(5.0, 8.0), (9.0, 2.0)]},
        {"type": "Z", "points": []},
    ]
    assert [command.parameters for command in recreated.clip_path() or ()] == group.parameters["ComponentGroupPDF"]["clip_path"]
    assert recreated.parameters == group.parameters
    assert recreated.generate_pdf() == group.generate_pdf()

    group.set_clip_path(None)
    assert group.clip_path() is None
    assert "clip_path" not in group.parameters["ComponentGroupPDF"]


@pytest.mark.condition("PDF-GROUP-CLIP-P3")
def test_component_group_pdf_clip_rule_round_trips_and_clears(drawing_style: DrawingStyle) -> None:
    """PDF-GROUP-CLIP-P3: Clip rules serialize only when non-default."""
    group = ComponentGroupPDF("clip-rule-roundtrip")
    group.set_clip_rule("even odd")
    group.set_clip_rect((1.0, 2.0, 30.0, 40.0))
    group.add_component(RectanglePDF((10.0, 20.0), 3.0, 4.0, 0.0, drawing_style))

    recreated = ComponentGroupPDF.create_from_dict(group.parameters, {drawing_style.name: drawing_style})

    assert group.clip_rule() == "evenodd"
    assert group.parameters["ComponentGroupPDF"]["clip_rule"] == "evenodd"
    assert recreated.clip_rule() == "evenodd"
    assert recreated.generate_pdf() == group.generate_pdf()

    group.clear_clip_rule()
    assert group.clip_rule() == "nonzero"
    assert "clip_rule" not in group.parameters["ComponentGroupPDF"]


@pytest.mark.condition("PDF-GROUP-CLIP-P3")
def test_component_group_pdf_clip_path_preserves_command_flags(drawing_style: DrawingStyle) -> None:
    """PDF-GROUP-CLIP-P3: Clip path command cloning preserves serialized flags."""
    arc = PathCommand("A", [(10.0, 20.0)])
    arc.flags = {"large_arc": False, "sweep": True}
    group = ComponentGroupPDF("clip-path-flags")
    group.set_clip_path([PathCommand("M", [(1.0, 2.0)]), arc, PathCommand("Z", [])])
    arc.flags = {"large_arc": True, "sweep": False}

    returned = group.clip_path()
    assert returned is not None
    returned[1].flags = {"large_arc": True}

    assert group.parameters["ComponentGroupPDF"]["clip_path"] == [
        {"type": "M", "points": [(1.0, 2.0)]},
        {"type": "A", "points": [(10.0, 20.0)], "flags": {"large_arc": False, "sweep": True}},
        {"type": "Z", "points": []},
    ]


@pytest.mark.condition("PDF-GROUP-CLIP-P3")
def test_component_group_pdf_accepts_fractional_positive_clip_dimensions() -> None:
    """PDF-GROUP-CLIP-P3: Clip rectangles accept any finite positive dimensions."""
    group = ComponentGroupPDF("clip-small")

    group.set_clip_rect((0.0, 0.0, 0.5, 0.25))

    assert group.clip_rect() == (0.0, 0.0, 0.5, 0.25)


@pytest.mark.condition("PDF-GROUP-CLIP-P3")
@pytest.mark.parametrize(
    "clip_rect",
    [
        "1 2 3 4",
        [1.0, 2.0, 3.0],
        [1.0, 2.0, 3.0, 4.0, 5.0],
        [True, 2.0, 3.0, 4.0],
        [1.0, 2.0, float("nan"), 4.0],
        [1.0, 2.0, 0.0, 4.0],
        [1.0, 2.0, -0.5, 4.0],
        [1.0, 2.0, 3.0, 0.0],
        [1.0, 2.0, 3.0, -0.5],
        [1.0, 2.0, 3.0, -1.0],
        object(),
    ],
)
def test_component_group_pdf_rejects_malformed_clip_rectangles(clip_rect: object) -> None:
    """PDF-GROUP-CLIP-P3: Malformed PDF group clip rectangles fail before state mutation."""
    group = ComponentGroupPDF("clip-invalid")

    with pytest.raises((TypeError, ValueError), match="PDF clip rectangle"):
        group.set_clip_rect(clip_rect)

    assert group.clip_rect() is None


@pytest.mark.condition("PDF-GROUP-CLIP-P3")
def test_component_group_pdf_factory_rejects_malformed_clip_rectangles() -> None:
    """PDF-GROUP-CLIP-P3: Group hydration rejects malformed serialized clip rectangles."""
    payload = {"ComponentGroupPDF": {"group_label": "clip-invalid", "components": [], "clip_rect": [1.0, 2.0, 0.0, 4.0]}}

    with pytest.raises(ValueError, match="PDF clip rectangle width and height must be positive"):
        ComponentGroupPDF.create_from_dict(payload)


@pytest.mark.condition("PDF-GROUP-CLIP-P3")
@pytest.mark.parametrize(
    "clip_path",
    [
        "M 0 0",
        [],
        [object()],
        [PathCommand("L", [(1.0, 2.0)]), PathCommand("Z", [])],
        [PathCommand("M", [(1.0, 2.0)]), PathCommand("L", [(3.0, 4.0)])],
        [PathCommand("M", [(1.0, 2.0)]), PathCommand("C", [(3.0, 4.0)]), PathCommand("Z", [])],
        [{"points": [(1.0, 2.0)]}, {"type": "Z", "points": []}],
        [{"type": "M", "points": [(1.0, 2.0)]}, {"type": "Z", "points": object()}],
    ],
)
def test_component_group_pdf_rejects_malformed_clip_paths(clip_path: object) -> None:
    """PDF-GROUP-CLIP-P3: Malformed PDF group clip paths fail before state mutation."""
    group = ComponentGroupPDF("clip-path-invalid")
    group.set_clip_path([PathCommand("M", [(0.0, 0.0)]), PathCommand("L", [(1.0, 0.0)]), PathCommand("Z", [])])

    with pytest.raises((TypeError, ValueError), match="PDF clip path|PathPDF command"):
        group.set_clip_path(clip_path)  # type: ignore[arg-type]

    assert group.parameters["ComponentGroupPDF"]["clip_path"] == [
        {"type": "M", "points": [(0.0, 0.0)]},
        {"type": "L", "points": [(1.0, 0.0)]},
        {"type": "Z", "points": []},
    ]


@pytest.mark.condition("PDF-GROUP-CLIP-P3")
def test_component_group_pdf_rejects_string_clip_path_with_boundary_error() -> None:
    """PDF-GROUP-CLIP-P3: String clip paths fail at the clip-path boundary."""
    group = ComponentGroupPDF("clip-path-string")

    with pytest.raises(TypeError, match="PDF clip path commands must be a non-empty sequence"):
        group.set_clip_path("M 0 0")  # type: ignore[arg-type]


@pytest.mark.condition("PDF-GROUP-CLIP-P3")
def test_component_group_pdf_rejects_clip_path_start_after_m_command() -> None:
    """PDF-GROUP-CLIP-P3: Non-M starts fail regardless of command sort order."""
    group = ComponentGroupPDF("clip-path-start")

    with pytest.raises(ValueError, match="PDF clip path must start with an M command"):
        group.set_clip_path([PathCommand("Q", [(1.0, 2.0), (3.0, 4.0)]), PathCommand("Z", [])])


@pytest.mark.condition("PDF-GROUP-CLIP-P3")
def test_component_group_pdf_factory_rejects_malformed_clip_paths() -> None:
    """PDF-GROUP-CLIP-P3: Group hydration rejects malformed serialized clip paths."""
    payload = {"ComponentGroupPDF": {"group_label": "clip-path-invalid", "components": [], "clip_path": [{"type": "L", "points": []}]}}

    with pytest.raises(ValueError, match="PDF clip path must start with an M command"):
        ComponentGroupPDF.create_from_dict(payload)


@pytest.mark.condition("PDF-GROUP-CLIP-P3")
@pytest.mark.parametrize("clip_rule", [object(), "", "not-a-rule"])
def test_component_group_pdf_rejects_malformed_clip_rules(clip_rule: object) -> None:
    """PDF-GROUP-CLIP-P3: Malformed PDF clip rules fail before state mutation."""
    group = ComponentGroupPDF("clip-rule-invalid")
    group.set_clip_rule("evenodd")

    with pytest.raises((TypeError, ValueError), match="PDF clip rule"):
        group.set_clip_rule(clip_rule)  # type: ignore[arg-type]

    assert group.clip_rule() == "evenodd"


@pytest.mark.condition("PDF-GROUP-CLIP-P3")
def test_component_group_pdf_factory_rejects_malformed_clip_rules() -> None:
    """PDF-GROUP-CLIP-P3: Group hydration rejects malformed serialized clip rules."""
    payload = {"ComponentGroupPDF": {"group_label": "clip-rule-invalid", "components": [], "clip_rule": "not-a-rule"}}

    with pytest.raises(ValueError, match="PDF clip rule must be nonzero or evenodd"):
        ComponentGroupPDF.create_from_dict(payload)


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

    assert r"(A\\B\(C\)) Tj" in content
    assert "(D) Tj" in content
    assert r"\r\n" not in content


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
