"""Parser stress fixture contract tests."""

from __future__ import annotations

import json

import pytest

from InkGen.parser_stress_fixtures import (
    ParserStressBOMRow,
    ParserStressFixtureSpec,
    ScannedParserStressFixtureSpec,
    _coerce_fixture_page_rotation,
    _unique_style_name,
    build_parser_stress_pdf,
    build_scanned_parser_stress_pdf,
)
from InkGen.pdf_generator import ComponentGroupPDF, DocumentPDF, ImagePDF
from InkGen.style import DrawingStyle


def _groups_by_label(document: DocumentPDF) -> dict[str, ComponentGroupPDF]:
    return {group.group_label: group for group in document.page(1).layer("base").groups()}


def _document_canvas_dimensions(document: DocumentPDF) -> tuple[float, float]:
    canvas = document.parameters["DocumentPDF"]["canvas"]["Canvas"]
    return canvas["width"], canvas["height"]


@pytest.mark.condition("PDF-PARSER-STRESS-FIXTURE-P3")
def test_parser_stress_pdf_builds_rotated_transparent_truth_labeled_fixture() -> None:
    """PDF-PARSER-STRESS-FIXTURE-P3: The fixture builder emits parser-facing PDF stress cues."""
    spec = ParserStressFixtureSpec(
        drawing_number="PSF-0100",
        revision="B",
        title="PARSER STRESS TEST",
        style_namespace="parser_stress_contract",
    )

    document = build_parser_stress_pdf(spec)
    payload = document.to_pdf_bytes()
    extraction_truth = document.extraction_truth()
    grammar_truth = document.grammar_truth()

    assert isinstance(document, DocumentPDF)
    assert _document_canvas_dimensions(document) == (340.0, 200.0)
    assert document.page_rotation(1) == 90
    groups = _groups_by_label(document)
    assert set(groups) == {"title_block", "bom_table", "transparent_overlay", "zone_markers"}
    assert len(tuple(groups["title_block"].components())) == 8
    assert len(tuple(groups["bom_table"].components())) == 24
    assert len(tuple(groups["transparent_overlay"].components())) == 2
    assert len(tuple(groups["zone_markers"].components())) == 8
    assert b"/Rotate 90" in payload
    assert b"/TrimBox [0 0 340 200]" in payload
    assert b"/ExtGState" in payload
    assert b"PARSER STRESS TEST" in payload
    assert b"PSF-1001" in payload
    assert {record["field"] for record in extraction_truth} >= {
        "drawing_number",
        "revision",
        "drawing_title",
        "part_number",
        "quantity",
        "bom_table",
    }
    assert any(record["condition_id"] == "BOM-TABLE" and record["kind"] == "construct" for record in grammar_truth)
    assert any(record["condition_id"] == "TRANSPARENCY-CUE" for record in grammar_truth)
    assert any(record["page"] == 0 and record["bbox"] is None and record["value"]["known_fixture"] is True for record in grammar_truth)
    assert any(record["condition_id"] == "PARSER-STRESS-DOCUMENT" and record["value"]["known_fixture"] is True for record in grammar_truth)
    assert json.loads(document.extraction_truth_json()) == extraction_truth
    assert json.loads(document.grammar_truth_json()) == grammar_truth


@pytest.mark.condition("PDF-PARSER-STRESS-FIXTURE-P3")
def test_parser_stress_pdf_can_disable_optional_rotation_and_transparency() -> None:
    """PDF-PARSER-STRESS-FIXTURE-P3: Optional stress cues can be omitted deliberately."""
    document = build_parser_stress_pdf(
        ParserStressFixtureSpec(
            drawing_number="PSF-0101",
            page_rotation=None,
            include_transparency=False,
            style_namespace="parser_stress_no_optional",
        )
    )
    payload = document.to_pdf_bytes()

    assert document.page_rotation(1) is None
    assert b"/Rotate" not in payload
    assert b"/ExtGState" not in payload
    assert "transparent_overlay" not in _groups_by_label(document)


@pytest.mark.condition("PDF-PARSER-STRESS-FIXTURE-P3")
def test_parser_stress_spec_normalizes_rotations() -> None:
    """PDF-PARSER-STRESS-FIXTURE-P3: Rotation metadata is normalized before rendering."""
    positive = ParserStressFixtureSpec(page_rotation=450, style_namespace="parser_stress_rotation_positive")
    negative = ParserStressFixtureSpec(page_rotation=-90, style_namespace="parser_stress_rotation_negative")

    assert _coerce_fixture_page_rotation(0) == 0
    assert _coerce_fixture_page_rotation(90) == 90
    assert positive.page_rotation == 90
    assert negative.page_rotation == 270
    assert build_parser_stress_pdf(positive).page_rotation(1) == 90
    assert build_parser_stress_pdf(negative).page_rotation(1) == 270
    with pytest.raises(TypeError, match="page_rotation"):
        _coerce_fixture_page_rotation(True)
    with pytest.raises(ValueError, match="page_rotation"):
        _coerce_fixture_page_rotation(1)


@pytest.mark.condition("PDF-PARSER-STRESS-FIXTURE-P3")
def test_parser_stress_unique_style_names_advance_through_collisions() -> None:
    """PDF-PARSER-STRESS-FIXTURE-P3: Style names advance deterministically on collisions."""
    namespace = "parser_stress_unique_contract"

    assert _unique_style_name(namespace, "outline") == f"{namespace}_outline"
    DrawingStyle(f"{namespace}_outline")
    assert _unique_style_name(namespace, "outline") == f"{namespace}_outline_1"
    DrawingStyle(f"{namespace}_outline_1")
    assert _unique_style_name(namespace, "outline") == f"{namespace}_outline_2"


@pytest.mark.condition("PDF-PARSER-STRESS-FIXTURE-P3")
def test_parser_stress_pdf_default_builds_do_not_collide_on_style_names() -> None:
    """PDF-PARSER-STRESS-FIXTURE-P3: Repeated default builds keep working despite Style name uniqueness."""
    first = build_parser_stress_pdf()
    second = build_parser_stress_pdf()

    assert first.to_pdf_bytes() == second.to_pdf_bytes()
    assert first.extraction_truth_json() == second.extraction_truth_json()
    assert first.grammar_truth_json() == second.grammar_truth_json()


@pytest.mark.condition("PDF-PARSER-STRESS-FIXTURE-P3")
def test_parser_stress_spec_rejects_empty_or_invalid_inputs() -> None:
    """PDF-PARSER-STRESS-FIXTURE-P3: Invalid fixture specs fail before rendering."""
    with pytest.raises(ValueError, match="drawing_number"):
        ParserStressFixtureSpec(drawing_number="")
    with pytest.raises(TypeError, match="page_rotation"):
        ParserStressFixtureSpec(page_rotation=True)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="page_rotation"):
        ParserStressFixtureSpec(page_rotation=45)
    with pytest.raises(TypeError, match="include_transparency"):
        ParserStressFixtureSpec(include_transparency="yes")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="bom_rows"):
        ParserStressFixtureSpec(bom_rows=())
    with pytest.raises(TypeError, match="bom_rows"):
        ParserStressFixtureSpec(bom_rows=(object(),))  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="spec"):
        build_parser_stress_pdf(object())  # type: ignore[arg-type]


@pytest.mark.condition("PDF-PARSER-STRESS-FIXTURE-P3")
def test_parser_stress_bom_row_rejects_empty_fields() -> None:
    """PDF-PARSER-STRESS-FIXTURE-P3: BOM row fields are non-empty strings."""
    with pytest.raises(ValueError, match="part_number"):
        ParserStressBOMRow("1", "", "DESCRIPTION", "1")
    with pytest.raises(ValueError, match="quantity"):
        ParserStressBOMRow("1", "PN-1", "DESCRIPTION", 1)  # type: ignore[arg-type]


@pytest.mark.condition("PDF-PARSER-STRESS-SCAN-P3")
def test_scanned_parser_stress_pdf_builds_image_only_truth_labeled_fixture() -> None:
    """PDF-PARSER-STRESS-SCAN-P3: The scanned fixture emits an image-only PDF page."""
    spec = ScannedParserStressFixtureSpec(scan_id="SCAN-0100", page_label="SCAN-A-", source_name="scan-a.png")

    document = build_scanned_parser_stress_pdf(spec)
    payload = document.to_pdf_bytes()
    extraction_truth = document.extraction_truth()
    grammar_truth = document.grammar_truth()
    groups = _groups_by_label(document)
    components = tuple(groups["scanned_page"].components())

    assert isinstance(document, DocumentPDF)
    assert _document_canvas_dimensions(document) == (340.0, 200.0)
    assert set(groups) == {"scanned_page"}
    assert len(components) == 1
    assert type(components[0]) is ImagePDF
    assert components[0].position == (0.1, 0.1)
    assert components[0].width == 339.8
    assert components[0].height == 199.8
    assert components[0].image.width == 680
    assert components[0].image.height == 400
    image = components[0].image.image()
    pixels = image.load()
    assert pixels[72, 60] == (0, 0, 0)
    assert pixels[168, 60] == (0, 0, 0)
    assert pixels[398, 60] == (0, 0, 0)
    assert pixels[50, 68] == (0, 0, 0)
    assert pixels[50, 88] == (0, 0, 0)
    grid_x = {36, 37, 72, 73, 168, 169, 398, 399, 438, 439}
    grid_y = {48, 49, 68, 69, 88, 89, 108, 109, 128, 129}
    header_dark_pixels = sum(
        1 for y in range(54, 72) for x in range(42, 430) if pixels[x, y][0] < 100 and x not in grid_x and y not in grid_y
    )
    row_dark_pixels = sum(
        1 for y in range(70, 115) for x in range(42, 430) if pixels[x, y][0] < 100 and x not in grid_x and y not in grid_y
    )
    assert header_dark_pixels > 500
    assert row_dark_pixels > 500
    assert document.page_rotation(1) is None
    assert b"/TrimBox [0 0 340 200]" in payload
    assert b"/Subtype /Image" in payload
    assert b"/XObject << /Im1" in payload
    assert "339.8 0 0 -199.8 0.1 199.9 cm\n/Im1 Do" in payload.decode("latin-1")
    assert b"BT" not in payload
    assert b" Tj" not in payload
    assert b"SCAN-0100" not in payload
    assert {(record["field"], record["role"], record["source_channel"], record["instance_id"]) for record in extraction_truth} >= {
        ("scanned_page_image", "image", "image", "SCAN-0100"),
        ("scanned_page", "region", "body", "SCAN-0100"),
    }
    assert any(
        record["condition_id"] == "PARSER-STRESS-SCANNED-DOCUMENT"
        and record["kind"] == "assessment"
        and record["bbox"] is None
        and record["value"]["known_fixture"] is True
        and record["value"]["extractable_text"] is False
        for record in grammar_truth
    )
    assert any(
        record["condition_id"] == "SCANNED-PAGE-IMAGE"
        and record["kind"] == "cue"
        and record["source_channel"] == "image"
        and record["value"]["image_format"] == "PNG"
        for record in grammar_truth
    )
    assert any(record["condition_id"] == "IMAGE-ONLY-PAGE" and record["kind"] == "construct" for record in grammar_truth)
    assert json.loads(document.extraction_truth_json()) == extraction_truth
    assert json.loads(document.grammar_truth_json()) == grammar_truth


@pytest.mark.condition("PDF-PARSER-STRESS-SCAN-P3")
def test_scanned_parser_stress_pdf_default_builds_are_deterministic() -> None:
    """PDF-PARSER-STRESS-SCAN-P3: Repeated scanned fixture builds are deterministic."""
    first = build_scanned_parser_stress_pdf()
    second = build_scanned_parser_stress_pdf()

    assert first.to_pdf_bytes() == second.to_pdf_bytes()
    assert first.extraction_truth_json() == second.extraction_truth_json()
    assert first.grammar_truth_json() == second.grammar_truth_json()


@pytest.mark.condition("PDF-PARSER-STRESS-SCAN-P3")
def test_scanned_parser_stress_spec_rejects_empty_or_invalid_inputs() -> None:
    """PDF-PARSER-STRESS-SCAN-P3: Invalid scanned fixture specs fail before rendering."""
    with pytest.raises(ValueError, match="scan_id"):
        ScannedParserStressFixtureSpec(scan_id="")
    with pytest.raises(ValueError, match="page_label"):
        ScannedParserStressFixtureSpec(page_label="")
    with pytest.raises(ValueError, match="source_name"):
        ScannedParserStressFixtureSpec(source_name="")
    with pytest.raises(ValueError, match="scan_id"):
        ScannedParserStressFixtureSpec(scan_id=10)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="spec"):
        build_scanned_parser_stress_pdf(object())  # type: ignore[arg-type]
