"""Behavioral proofs for PDF text visibility and character spacing."""

from __future__ import annotations

from itertools import combinations
from uuid import uuid4

import pytest

import InkGen.component as component_module
import InkGen.pdf_generator as pdf_generator_module
from InkGen.boundary import Canvas
from InkGen.drawing_components import DrawingComponentGroup, OutputFormat, TextDrawing
from InkGen.pdf_generator import ComponentGroupPDF, DocumentPDF, TextPDF
from InkGen.style import Font, TextStyle

CONDITION = "PDF-TEXT-PRESENTATION-P3"


def _style(*, visible: bool = True, character_spacing: float = 0.0) -> TextStyle:
    """Return a unique text style with explicit presentation settings."""
    return TextStyle(
        name=f"pdf_text_presentation_{uuid4().hex}",
        font=Font(size=12.0),
        visible=visible,
        character_spacing=character_spacing,
    )


def _single_text_pdf(text: str, style: TextStyle) -> bytes:
    """Render one text run through the public document path."""
    document = DocumentPDF(Canvas(300.0, 60.0, "mm"))
    document.add_page()
    group = ComponentGroupPDF("text-presentation")
    group.add_component(TextPDF(text, (30.0, 25.0), style))
    document.page(1).layer("base").add_component_group(group)
    return document.to_pdf_bytes()


@pytest.mark.condition(CONDITION)
def test_text_presentation_defaults_round_trip_and_legacy_payloads() -> None:
    """PDF-TEXT-PRESENTATION-P3: New fields are stable and legacy payloads retain defaults."""
    style = TextStyle(name=f"direct_defaults_{uuid4().hex}", font=Font(size=12.0))

    assert style.visible is True
    assert style.character_spacing == 0.0
    assert style.parameters["TextStyle"]["visible"] is True
    assert style.parameters["TextStyle"]["character_spacing"] == 0.0

    payload = style.parameters
    payload["TextStyle"]["name"] = f"round_trip_{uuid4().hex}"
    payload["TextStyle"]["visible"] = False
    payload["TextStyle"]["character_spacing"] = -0.75
    clone = TextStyle.create_from_dict(payload)

    assert clone.visible is False
    assert clone.character_spacing == -0.75

    legacy_payload = style.parameters
    legacy_payload["TextStyle"]["name"] = f"legacy_{uuid4().hex}"
    del legacy_payload["TextStyle"]["visible"]
    del legacy_payload["TextStyle"]["character_spacing"]
    legacy = TextStyle.create_from_dict(legacy_payload)

    assert legacy.visible is True
    assert legacy.character_spacing == 0.0


@pytest.mark.condition(CONDITION)
def test_text_presentation_rejects_invalid_public_and_serialized_values() -> None:
    """PDF-TEXT-PRESENTATION-P3: Invalid settings fail before reaching PDF serialization."""
    style = _style()
    for value in (0, 1, "false", None, object()):
        with pytest.raises(TypeError, match="visible"):
            style.visible = value  # type: ignore[assignment]
        assert style.visible is True

    for value in (True, False, "1", None, object(), float("nan"), float("inf"), float("-inf")):
        with pytest.raises((TypeError, ValueError), match="character_spacing"):
            style.character_spacing = value  # type: ignore[assignment]
        assert style.character_spacing == 0.0

    for field, value in (("visible", "false"), ("character_spacing", float("nan"))):
        payload = style.parameters
        payload["TextStyle"]["name"] = f"invalid_{uuid4().hex}"
        payload["TextStyle"][field] = value
        with pytest.raises((TypeError, ValueError)):
            TextStyle.create_from_dict(payload)


@pytest.mark.condition(CONDITION)
def test_text_pdf_emits_only_nondefault_render_mode_and_character_spacing() -> None:
    """PDF-TEXT-PRESENTATION-P3: TextPDF maps presentation fields to scoped Tr and Tc operators."""
    default_pdf = TextPDF("ABC", (20.0, 5.0), _style()).generate_pdf()
    invisible_pdf = TextPDF("ABC", (20.0, 5.0), _style(visible=False)).generate_pdf()
    tracked_pdf = TextPDF("ABC", (20.0, 5.0), _style(character_spacing=1.25)).generate_pdf()

    assert " Tr" not in default_pdf
    assert " Tc" not in default_pdf
    assert invisible_pdf.splitlines()[4] == "3 Tr"
    assert tracked_pdf.splitlines()[4] == "1.25 Tc"
    assert invisible_pdf.endswith("ET\nQ")
    assert tracked_pdf.endswith("ET\nQ")


@pytest.mark.condition(CONDITION)
@pytest.mark.parametrize(
    ("alignment", "spacing", "expected_x"),
    [("center", 2.0, 7.2), ("end", 2.0, -5.6), ("center", -1.0, 10.2), ("end", -1.0, 0.4)],
)
def test_character_spacing_participates_in_pdf_alignment(
    alignment: str,
    spacing: float,
    expected_x: float,
) -> None:
    """PDF-TEXT-PRESENTATION-P3: Alignment includes every inter-character spacing interval."""
    style = _style(character_spacing=spacing)
    style.text_align = alignment

    operators = TextPDF("ABC", (20.0, 5.0), style).generate_pdf().splitlines()

    assert f"1 0 0 -1 {expected_x:g} 5 Tm" in operators


@pytest.mark.condition(CONDITION)
def test_pdf_text_width_and_alignment_helpers_use_exact_inter_character_intervals() -> None:
    """PDF-TEXT-PRESENTATION-P3: Width math applies spacing between, never after, glyphs."""
    assert pdf_generator_module._pdf_text_line_width("", 12.0, 2.0) == 0.0
    assert pdf_generator_module._pdf_text_line_width("A", 12.0, 2.0) == pytest.approx(7.2)
    assert pdf_generator_module._pdf_text_line_width("ABC", 12.0, 2.0) == pytest.approx(25.6)
    assert pdf_generator_module._pdf_text_line_width("ABC", 12.0, -1.0) == pytest.approx(19.6)

    dynamic_center = bytearray(b"center").decode("ascii")
    dynamic_end = bytearray(b"end").decode("ascii")
    assert pdf_generator_module._pdf_text_aligned_x(20.0, "ABC", 12.0, dynamic_center, 2.0) == pytest.approx(7.2)
    assert pdf_generator_module._pdf_text_aligned_x(20.0, "ABC", 12.0, dynamic_end, 2.0) == pytest.approx(-5.6)
    assert pdf_generator_module._pdf_text_aligned_x(20.0, "ABC", 12.0, "start", 2.0) == 20.0


@pytest.mark.condition(CONDITION)
def test_character_spacing_bounds_are_exact_for_fixed_outlines_and_multiline_text() -> None:
    """PDF-TEXT-PRESENTATION-P3: Conservative bounds include the largest tracked line."""
    style = _style(character_spacing=2.0)
    component = TextPDF("AB\nWXYZ", (10.0, 20.0), style)
    outline = {
        "points": [(10.0, 2.0), (20.0, 2.0), (20.0, 8.0), (10.0, 8.0)],
        "convex_hull": [(10.0, 2.0), (20.0, 2.0), (20.0, 8.0), (10.0, 8.0)],
        "bbox": [(10.0, 2.0), (20.0, 2.0), (20.0, 8.0), (10.0, 8.0)],
        "path_bbox": (10.0, 2.0, 20.0, 8.0),
    }

    positive = component._apply_character_spacing_bounds(outline)  # noqa: SLF001
    assert positive["bbox"] == [(10.0, 2.0), (26.0, 2.0), (26.0, 8.0), (10.0, 8.0)]
    assert positive["path_bbox"] == (10.0, 2.0, 26.0, 8.0)

    style.character_spacing = -2.0
    negative = component._apply_character_spacing_bounds(outline)  # noqa: SLF001
    assert negative["bbox"] == [(4.0, 2.0), (20.0, 2.0), (20.0, 8.0), (4.0, 8.0)]
    assert negative["path_bbox"] == (4.0, 2.0, 20.0, 8.0)

    component.text = "A"
    assert component._apply_character_spacing_bounds(outline) is outline  # noqa: SLF001
    component.text = ""
    assert component._apply_character_spacing_bounds(outline) is outline  # noqa: SLF001


@pytest.mark.condition(CONDITION)
@pytest.mark.parametrize(
    ("text", "expected"),
    [("", 0), ("A", 0), ("AB", 1), ("ABCD", 3), ("AB\r\nWXYZ\rQ", 3)],
)
def test_character_spacing_interval_count_is_line_local(text: str, expected: int) -> None:
    """PDF-TEXT-PRESENTATION-P3: Tracking counts gaps per normalized line."""
    component = TextPDF(text, (10.0, 20.0), _style(character_spacing=2.0))

    assert component._character_spacing_intervals() == expected  # noqa: SLF001


@pytest.mark.condition(CONDITION)
def test_character_spacing_outline_cache_tracks_style_mutation(monkeypatch: pytest.MonkeyPatch) -> None:
    """PDF-TEXT-PRESENTATION-P3: Mutating tracking invalidates cached collision geometry."""
    calls = 0

    def fixed_outline(**_kwargs: object) -> dict[str, object]:
        nonlocal calls
        calls += 1
        rect = [(10.0, 2.0), (20.0, 2.0), (20.0, 8.0), (10.0, 8.0)]
        return {"points": rect, "convex_hull": rect, "bbox": rect, "path_bbox": (10.0, 2.0, 20.0, 8.0)}

    monkeypatch.setattr(component_module, "outline_for_text", fixed_outline)
    style = _style()
    component = TextPDF("ABC", (10.0, 20.0), style)

    assert component.bbox == ((10.0, 2.0), (20.0, 8.0))
    assert component.bbox == ((10.0, 2.0), (20.0, 8.0))
    assert calls == 1

    style.character_spacing = 2.0
    assert component.bbox == ((10.0, 2.0), (24.0, 8.0))
    assert calls == 2


@pytest.mark.condition(CONDITION)
def test_character_spacing_fallback_bounds_preserve_positive_and_negative_offsets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PDF-TEXT-PRESENTATION-P3: Missing font tooling retains tracked conservative bounds."""
    monkeypatch.setattr(component_module, "outline_for_text", lambda **_kwargs: None)
    style = _style(character_spacing=2.0)
    component = TextPDF("ABC", (10.0, 20.0), style)

    assert component.bbox[0] == pytest.approx((10.0, 8.0))
    assert component.bbox[1] == pytest.approx((35.6, 20.0))

    style.character_spacing = -2.0
    assert component.bbox[0] == pytest.approx((6.0, 8.0))
    assert component.bbox[1] == pytest.approx((31.6, 20.0))

    component.text = "AB\nWXYZ"
    style.character_spacing = 0.25
    assert component.bbox[0] == pytest.approx((10.0, 8.0))
    assert component.bbox[1] == pytest.approx((39.55, 20.0))

    component.text = ""
    style.character_spacing = 2.0
    assert component.bbox[0] == pytest.approx((10.0, 8.0))
    assert component.bbox[1] == pytest.approx((16.0, 20.0))


@pytest.mark.condition(CONDITION)
@pytest.mark.parametrize(
    ("outline", "expected"),
    [
        ({"convex_hull": [(1.0, 5.0), (2.0, -3.0)]}, (-3.0, 5.0)),
        ({"bbox": [(1.0, 7.0), (2.0, 4.0)]}, (4.0, 7.0)),
        ({"points": [(1.0, 9.0), (2.0, 6.0)]}, (6.0, 9.0)),
        ({"path_bbox": (1.0, -2.0, 3.0, 8.0)}, (-2.0, 8.0)),
        ({}, None),
    ],
)
def test_outline_vertical_span_reads_every_supported_outline_surface(
    outline: dict[str, object],
    expected: tuple[float, float] | None,
) -> None:
    """PDF-TEXT-PRESENTATION-P3: Tracked bounds retain every outline representation."""
    assert TextPDF._outline_vertical_span(outline) == expected  # noqa: SLF001


@pytest.mark.condition(CONDITION)
def test_outline_span_absence_is_equivalent_for_horizontal_and_vertical_surfaces() -> None:
    """PDF-TEXT-PRESENTATION-P3: Every supported outline surface supplies both spans."""
    surfaces = {
        "convex_hull": [(1.0, 2.0), (3.0, 4.0)],
        "bbox": [(1.0, 2.0), (3.0, 4.0)],
        "points": [(1.0, 2.0), (3.0, 4.0)],
        "path_bbox": (1.0, 2.0, 3.0, 4.0),
    }
    keys = tuple(surfaces)
    outlines = [dict()] + [dict(combination) for size in range(1, len(keys) + 1) for combination in combinations(surfaces.items(), size)]

    for outline in outlines:
        horizontal_absent = TextPDF._outline_span(outline) is None  # noqa: SLF001
        vertical_absent = TextPDF._outline_vertical_span(outline) is None  # noqa: SLF001
        assert horizontal_absent == vertical_absent


@pytest.mark.condition(CONDITION)
def test_alignment_comparison_survivors_are_exact_over_validated_domain() -> None:
    """PDF-TEXT-PRESENTATION-P3: Surviving lexical comparisons equal live equality branches."""
    valid_alignments = ("start", "center", "end")
    for alignment in valid_alignments:
        assert (alignment == "center") == (alignment <= "center")
        if alignment != "center":
            assert (alignment == "end") == (alignment <= "end")


@pytest.mark.condition(CONDITION)
def test_character_spacing_updates_bounds_and_survives_neutral_materialization() -> None:
    """PDF-TEXT-PRESENTATION-P3: Tracking stays live in neutral output and collision geometry."""
    style = _style()
    drawing = TextDrawing("TRACK", (10.0, 20.0), style)
    pdf = drawing.to_component(OutputFormat.PDF)
    assert isinstance(pdf, TextPDF)

    default_width = pdf.bbox[1][0] - pdf.bbox[0][0]
    style.character_spacing = 1.5
    expanded_width = pdf.bbox[1][0] - pdf.bbox[0][0]
    assert expanded_width >= default_width + 6.0
    assert "1.5 Tc" in pdf.generate_pdf()

    style.character_spacing = -1.5
    negative_spacing_width = pdf.bbox[1][0] - pdf.bbox[0][0]
    assert negative_spacing_width >= default_width
    assert "-1.5 Tc" in pdf.generate_pdf()

    group = DrawingComponentGroup("tracked", [drawing])
    materialized = group.to_group(OutputFormat.PDF)
    assert "-1.5 Tc" in materialized.generate_pdf()


@pytest.mark.condition(CONDITION)
def test_invisible_text_is_extractable_without_painting_pixels() -> None:
    """PDF-TEXT-PRESENTATION-P3: Live PDF output preserves text extraction with zero glyph ink."""
    fitz = pytest.importorskip("fitz")
    phrase = "jan 2349 kWh usage comparison"
    invisible_payload = _single_text_pdf(phrase, _style(visible=False))
    visible_payload = _single_text_pdf(phrase, _style())

    with fitz.open(stream=invisible_payload, filetype="pdf") as invisible_document:
        page = invisible_document[0]
        assert phrase in page.get_text("text")
        invisible_samples = page.get_pixmap(alpha=False).samples

    with fitz.open(stream=visible_payload, filetype="pdf") as visible_document:
        visible_samples = visible_document[0].get_pixmap(alpha=False).samples

    assert min(invisible_samples) == 255
    assert min(visible_samples) < 255


@pytest.mark.condition(CONDITION)
def test_character_spacing_changes_live_extracted_span_width() -> None:
    """PDF-TEXT-PRESENTATION-P3: A real PDF consumer observes Tc as run-width control."""
    fitz = pytest.importorskip("fitz")
    widths = []
    for spacing in (0.0, 1.5, -1.5):
        payload = _single_text_pdf("TRACKING", _style(character_spacing=spacing))
        with fitz.open(stream=payload, filetype="pdf") as document:
            words = document[0].get_text("words")
        assert words
        widths.append(words[0][2] - words[0][0])

    default_width, expanded_width, contracted_width = widths
    assert expanded_width > default_width > contracted_width
