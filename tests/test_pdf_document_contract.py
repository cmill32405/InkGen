"""PDF document renderer contract tests."""

from __future__ import annotations

import re
from copy import deepcopy
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


@pytest.mark.condition("PDF-DOC-STRUCT-P3")
def test_document_pdf_emits_page_labels_and_page_boxes() -> None:
    """PDF-DOC-STRUCT-P3: PDF document structure metadata renders and round-trips."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_page()
    document.set_page_label(1, "Cover (A)")
    document.set_page_label(2, r"B\2")
    document.set_page_box(1, "CropBox", [5.0, 6.0, 95.0, 74.0])
    document.set_page_box(1, "/TrimBox", (10.0, 12.0, 90.0, 70.0))
    document.set_page_box(2, "ArtBox", [0.0, 0.0, 100.0, 80.0])

    payload = document.to_pdf_bytes()
    recreated = DocumentPDF.create_from_dict(document.parameters)
    object_ids = re.findall(rb"(?m)^(\d+) 0 obj$", payload)
    trailer_size = re.search(rb"/Size (?P<size>\d+)", payload)

    assert payload == document.to_pdf_bytes()
    assert b"/PageLabels << /Nums [0 << /P (Cover \\(A\\)) >> 1 << /P (B\\\\2) >>] >>" in payload
    assert b"/CropBox [5 6 95 74]" in payload
    assert b"/TrimBox [10 12 90 70]" in payload
    assert b"/ArtBox [0 0 100 80]" in payload
    assert b"/Count 2" in payload
    assert payload.count(b"/CropBox") == 1
    assert len(object_ids) == len(set(object_ids))
    assert trailer_size is not None
    assert int(trailer_size.group("size")) == max(int(object_id) for object_id in object_ids) + 1
    assert recreated.parameters == document.parameters
    assert recreated.to_pdf_bytes() == payload
    assert recreated.page_label(1) == "Cover (A)"
    assert recreated.page_box(1, "trim") == (10.0, 12.0, 90.0, 70.0)


@pytest.mark.condition("PDF-DOC-STRUCT-P3")
def test_document_pdf_rejects_invalid_page_structure_metadata() -> None:
    """PDF-DOC-STRUCT-P3: Page labels and page boxes fail at explicit boundaries."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()

    for label in [object(), "", "not latin \u0100"]:
        with pytest.raises((TypeError, ValueError)):
            document.set_page_label(1, label)  # type: ignore[arg-type]
        assert document.page_label(1) is None

    for box_name in [object(), "", "MediaBox"]:
        with pytest.raises((TypeError, ValueError)):
            document.set_page_box(1, box_name, [0.0, 0.0, 10.0, 10.0])  # type: ignore[arg-type]
        assert document.page_box(1, "CropBox") is None

    invalid_boxes: list[tuple[object, type[Exception], str]] = [
        ("0 0 1 1", TypeError, "four-number sequence"),
        (b"\x00\x00\x01\x01", TypeError, "four-number sequence"),
        ([0.0, 0.0, 1.0], TypeError, "four-number sequence"),
        ([0.0, 0.0, 1.0, 1.0, 1.0], TypeError, "four-number sequence"),
        ([True, 0.0, 1.0, 1.0], TypeError, "finite numbers"),
        ([0.0, 0.0, float("nan"), 1.0], ValueError, "finite numbers"),
        ([0.0, 0.0, 0.0, 1.0], ValueError, "positive area"),
        ([0.0, 1.0, 1.0, 1.0], ValueError, "positive area"),
        ([2.0, 0.0, 1.0, 1.0], ValueError, "positive area"),
        ([0.0, 2.0, 1.0, 1.0], ValueError, "positive area"),
        ([-1.0, 0.0, 1.0, 1.0], ValueError, "inside the page MediaBox"),
        ([0.0, -0.5, 1.0, 1.0], ValueError, "inside the page MediaBox"),
        ([0.0, 0.0, 101.0, 1.0], ValueError, "inside the page MediaBox"),
        ([0.0, 0.0, 1.0, 81.0], ValueError, "inside the page MediaBox"),
    ]
    for box, exception_type, message in invalid_boxes:
        with pytest.raises(exception_type, match=message):
            document.set_page_box(1, "CropBox", box)  # type: ignore[arg-type]
        assert document.page_box(1, "CropBox") is None

    with pytest.raises(ValueError, match="Position must correlate"):
        document.set_page_label(2, "missing")
    with pytest.raises(ValueError, match="Position must correlate"):
        document.set_page_box(2, "CropBox", [0.0, 0.0, 1.0, 1.0])

    document.set_page_label(1, "P1")
    document.set_page_box(1, "CropBox", [0.0, 0.0, 1.0, 1.0])
    document.set_page_label(1, None)
    document.set_page_box(1, "CropBox", None)

    assert document.page_label(1) is None
    assert document.page_box(1, "CropBox") is None
    assert "page_labels" not in document.parameters["DocumentPDF"]
    assert "page_boxes" not in document.parameters["DocumentPDF"]


@pytest.mark.condition("PDF-DOC-STRUCT-P3")
def test_document_pdf_page_structure_metadata_tracks_page_insertions_and_removals() -> None:
    """PDF-DOC-STRUCT-P3: Page-specific PDF metadata follows page index mutations."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_page()
    document.add_page()
    document.set_page_label(2, "middle")
    document.set_page_box(2, "BleedBox", [2.0, 3.0, 80.0, 60.0])
    document.set_page_label(3, "tail")
    document.set_page_box(3, "ArtBox", [1.0, 2.0, 90.0, 70.0])

    document.add_page()

    assert document.page_label(2) == "middle"
    assert document.page_box(2, "BleedBox") == (2.0, 3.0, 80.0, 60.0)
    assert document.page_label(3) == "tail"

    document.add_page(position=2)

    assert document.page_label(3) == "middle"
    assert document.page_box(3, "BleedBox") == (2.0, 3.0, 80.0, 60.0)
    assert document.page_label(4) == "tail"
    assert document.page_box(4, "ArtBox") == (1.0, 2.0, 90.0, 70.0)
    assert document.page_label(2) is None

    document.remove_page(2)

    assert document.page_label(2) == "middle"
    assert document.page_box(2, "BleedBox") == (2.0, 3.0, 80.0, 60.0)
    assert document.page_label(3) == "tail"
    assert document.page_box(3, "ArtBox") == (1.0, 2.0, 90.0, 70.0)

    document.remove_page(1)

    assert document.page_label(1) == "middle"
    assert document.page_box(1, "BleedBox") == (2.0, 3.0, 80.0, 60.0)
    assert document.page_label(2) == "tail"

    document.remove_page(2)

    assert document.pages == 2
    assert document.page_label(1) == "middle"
    assert document.page_box(1, "BleedBox") == (2.0, 3.0, 80.0, 60.0)
    assert "2" not in document.parameters["DocumentPDF"].get("page_labels", {})


@pytest.mark.condition("PDF-DOC-STRUCT-P3")
def test_document_pdf_page_structure_metadata_tracks_front_insert_and_noninterned_removal() -> None:
    """PDF-DOC-STRUCT-P3: Page metadata uses value equality for page index mutations."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    for _ in range(260):
        document.add_page()
    first_page = 1
    last_page = int("260")
    document.set_page_label(first_page, "front")
    document.set_page_box(first_page, "CropBox", [1.0, 1.0, 90.0, 70.0])
    document.set_page_label(last_page, "tail")
    document.set_page_box(last_page, "TrimBox", [2.0, 2.0, 80.0, 60.0])

    document.add_page(position=1)

    assert document.page_label(2) == "front"
    assert document.page_box(2, "CropBox") == (1.0, 1.0, 90.0, 70.0)
    assert document.page_label(261) == "tail"
    assert document.page_box(261, "TrimBox") == (2.0, 2.0, 80.0, 60.0)

    document.remove_page(int("261"))

    assert document.pages == 260
    assert "261" not in document.parameters["DocumentPDF"].get("page_labels", {})
    assert "261" not in document.parameters["DocumentPDF"].get("page_boxes", {})


@pytest.mark.condition("PDF-DOC-STRUCT-P3")
def test_document_pdf_rejects_invalid_serialized_page_structure_metadata() -> None:
    """PDF-DOC-STRUCT-P3: Serialized page labels and boxes validate before rendering."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.set_page_label(1, "P1")
    document.set_page_box(1, "BleedBox", [1.0, 1.0, 99.0, 79.0])

    invalid_payloads = []
    for mutator in [
        lambda data: data["DocumentPDF"].__setitem__("page_labels", "bad"),
        lambda data: data["DocumentPDF"].__setitem__("page_labels", {"0": "bad"}),
        lambda data: data["DocumentPDF"].__setitem__("page_labels", {"1.0": "bad"}),
        lambda data: data["DocumentPDF"].__setitem__("page_labels", {"-1": "bad"}),
        lambda data: data["DocumentPDF"].__setitem__("page_labels", {"1": ""}),
        lambda data: data["DocumentPDF"].__setitem__("page_boxes", "bad"),
        lambda data: data["DocumentPDF"].__setitem__("page_boxes", {"1": "bad"}),
        lambda data: data["DocumentPDF"].__setitem__("page_boxes", {"1": {"MediaBox": [0.0, 0.0, 1.0, 1.0]}}),
        lambda data: data["DocumentPDF"].__setitem__("page_boxes", {"1": {"CropBox": [0.0, 0.0, 0.0, 1.0]}}),
    ]:
        payload = deepcopy(document.parameters)
        mutator(payload)
        invalid_payloads.append(payload)

    for payload in invalid_payloads:
        with pytest.raises((TypeError, ValueError)):
            DocumentPDF.create_from_dict(payload)

    zero_page_payload = deepcopy(document.parameters)
    zero_page_payload["DocumentPDF"]["page_labels"] = {"0": "bad"}
    with pytest.raises(ValueError, match="page number keys"):
        DocumentPDF.create_from_dict(zero_page_payload)

    decimal_page_payload = deepcopy(document.parameters)
    decimal_page_payload["DocumentPDF"]["page_labels"] = {"1.0": "bad"}
    with pytest.raises(TypeError, match="page number keys"):
        DocumentPDF.create_from_dict(decimal_page_payload)
