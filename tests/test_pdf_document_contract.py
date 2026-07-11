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


def _pdf_objects(pdf_bytes: bytes) -> dict[int, bytes]:
    return {
        int(match.group("id")): match.group("payload")
        for match in re.finditer(rb"(?P<id>\d+) 0 obj\n(?P<payload>.*?)\nendobj", pdf_bytes, re.S)
    }


def _page_object_ids(pdf_bytes: bytes) -> list[int]:
    objects = _pdf_objects(pdf_bytes)
    return [object_id for object_id, payload in sorted(objects.items()) if b"/Type /Page /Parent" in payload]


def _annotation_refs_by_page(pdf_bytes: bytes) -> list[list[int]]:
    return [
        [int(object_id) for object_id in re.findall(rb"(\d+) 0 R", match.group("ids"))]
        for match in re.finditer(rb"/Annots \[(?P<ids>(?:\d+ 0 R ?)+)\]", pdf_bytes)
    ]


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


@pytest.mark.condition("PDF-DOC-TEXT-ANNOTATION-P3")
def test_document_pdf_emits_text_annotations_and_round_trips() -> None:
    """PDF-DOC-TEXT-ANNOTATION-P3: Text annotations render and round-trip."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_page()
    document.add_text_annotation(
        1,
        [5.0, 6.0, 20.0, 25.0],
        "Check this (A)",
        title=r"Reviewer\One",
        open=True,
    )
    document.add_text_annotation(page_number=1, rect=[30.0, 6.0, 45.0, 25.0], contents="Closed note")
    document.add_text_annotation(2, [0.0, 0.0, 100.0, 80.0], "Page 2 note")

    payload = document.to_pdf_bytes()
    recreated = DocumentPDF.create_from_dict(document.parameters)
    objects = _pdf_objects(payload)
    annotation_refs = _annotation_refs_by_page(payload)
    annotation_ids = [annotation_id for page_refs in annotation_refs for annotation_id in page_refs]

    assert payload == document.to_pdf_bytes()
    assert [len(page_refs) for page_refs in annotation_refs] == [2, 1]
    assert b"/Subtype /Text" in objects[annotation_ids[0]]
    assert b"/Rect [5 6 20 25]" in objects[annotation_ids[0]]
    assert b"/T (Reviewer\\\\One)" in objects[annotation_ids[0]]
    assert b"/Contents (Check this \\(A\\))" in objects[annotation_ids[0]]
    assert b"/Open true" in objects[annotation_ids[0]]
    assert b"/Rect [30 6 45 25]" in objects[annotation_ids[1]]
    assert b"/Contents (Closed note)" in objects[annotation_ids[1]]
    assert b"/Open" not in objects[annotation_ids[1]]
    assert b"/Rect [0 0 100 80]" in objects[annotation_ids[2]]
    assert b"/Contents (Page 2 note)" in objects[annotation_ids[2]]
    assert sorted(objects) == list(range(1, max(objects) + 1))
    assert document.text_annotations() == (
        {
            "page_number": 1,
            "rect": [5.0, 6.0, 20.0, 25.0],
            "contents": "Check this (A)",
            "title": r"Reviewer\One",
            "open": True,
        },
        {"page_number": 1, "rect": [30.0, 6.0, 45.0, 25.0], "contents": "Closed note"},
        {"page_number": 2, "rect": [0.0, 0.0, 100.0, 80.0], "contents": "Page 2 note"},
    )
    assert recreated.parameters == document.parameters
    assert recreated.to_pdf_bytes() == payload


@pytest.mark.condition("PDF-DOC-TEXT-ANNOTATION-P3")
def test_document_pdf_rejects_invalid_text_annotation_metadata() -> None:
    """PDF-DOC-TEXT-ANNOTATION-P3: Text annotation metadata fails at explicit boundaries."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()

    with pytest.raises(ValueError, match="Position must correlate"):
        document.add_text_annotation(2, [0.0, 0.0, 1.0, 1.0], "note")

    for contents in [object(), "", "not latin \u0100"]:
        with pytest.raises((TypeError, ValueError)):
            document.add_text_annotation(1, [0.0, 0.0, 1.0, 1.0], contents)  # type: ignore[arg-type]
        assert document.text_annotations() == ()

    for title in [object(), "", "not latin \u0100"]:
        with pytest.raises((TypeError, ValueError)):
            document.add_text_annotation(1, [0.0, 0.0, 1.0, 1.0], "note", title=title)  # type: ignore[arg-type]
        assert document.text_annotations() == ()

    for open_state in [0, 1, "true", object()]:
        with pytest.raises(TypeError):
            document.add_text_annotation(1, [0.0, 0.0, 1.0, 1.0], "note", open=open_state)  # type: ignore[arg-type]
        assert document.text_annotations() == ()

    invalid_rectangles = [
        "0 0 1 1",
        [0.0, 0.0, 1.0],
        [True, 0.0, 1.0, 1.0],
        [0.0, 0.0, float("nan"), 1.0],
        [0.0, 0.0, 0.0, 1.0],
        [-1.0, 0.0, 1.0, 1.0],
        [0.0, 0.0, 101.0, 1.0],
    ]
    for rect in invalid_rectangles:
        with pytest.raises((TypeError, ValueError)):
            document.add_text_annotation(1, rect, "note")  # type: ignore[arg-type]
        assert document.text_annotations() == ()

    document.add_text_annotation(1, [0.0, 0.0, 1.0, 1.0], "note")
    document.clear_text_annotations()

    assert document.text_annotations() == ()
    assert "text_annotations" not in document.parameters["DocumentPDF"]
    assert b"/Annots" not in document.to_pdf_bytes()


@pytest.mark.condition("PDF-DOC-TEXT-ANNOTATION-P3")
def test_document_pdf_text_annotations_track_page_insertions_and_removals() -> None:
    """PDF-DOC-TEXT-ANNOTATION-P3: Text annotations stay aligned with page mutations."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_page()
    document.add_page()
    document.add_text_annotation(1, [1.0, 1.0, 10.0, 10.0], "front")
    document.add_text_annotation(2, [2.0, 2.0, 20.0, 20.0], "middle")
    document.add_text_annotation(3, [3.0, 3.0, 30.0, 30.0], "tail", title="Tail", open=True)

    document.add_page(position=2)

    assert document.text_annotations() == (
        {"page_number": 1, "rect": [1.0, 1.0, 10.0, 10.0], "contents": "front"},
        {"page_number": 3, "rect": [2.0, 2.0, 20.0, 20.0], "contents": "middle"},
        {
            "page_number": 4,
            "rect": [3.0, 3.0, 30.0, 30.0],
            "contents": "tail",
            "title": "Tail",
            "open": True,
        },
    )

    document.remove_page(3)

    assert document.text_annotations() == (
        {"page_number": 1, "rect": [1.0, 1.0, 10.0, 10.0], "contents": "front"},
        {
            "page_number": 3,
            "rect": [3.0, 3.0, 30.0, 30.0],
            "contents": "tail",
            "title": "Tail",
            "open": True,
        },
    )

    document.remove_page(1)

    assert document.text_annotations() == (
        {
            "page_number": 2,
            "rect": [3.0, 3.0, 30.0, 30.0],
            "contents": "tail",
            "title": "Tail",
            "open": True,
        },
    )


@pytest.mark.condition("PDF-DOC-TEXT-ANNOTATION-P3")
def test_document_pdf_text_annotations_use_value_equality_for_large_page_removal() -> None:
    """PDF-DOC-TEXT-ANNOTATION-P3: Text annotation removal uses page-number value equality."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    for _ in range(260):
        document.add_page()
    document.add_text_annotation(1, [1.0, 1.0, 10.0, 10.0], "front")
    document.add_text_annotation(int("260"), [2.0, 2.0, 20.0, 20.0], "tail")

    document.remove_page(int("260"))

    assert document.pages == 259
    assert document.text_annotations() == ({"page_number": 1, "rect": [1.0, 1.0, 10.0, 10.0], "contents": "front"},)


@pytest.mark.condition("PDF-DOC-HIGHLIGHT-ANNOTATION-P3")
def test_document_pdf_emits_highlight_annotations_and_round_trips() -> None:
    """PDF-DOC-HIGHLIGHT-ANNOTATION-P3: Highlight annotations render and round-trip."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_page()
    document.add_text_annotation(1, [0.0, 0.0, 4.0, 4.0], "note")
    document.add_highlight_annotation(1, [5.0, 6.0, 20.0, 25.0], color="#336699", contents="Clause (A)")
    document.add_highlight_annotation(2, [0.0, 0.0, 100.0, 80.0])
    document.add_highlight_annotation(2, [10.0, 10.0, 20.0, 20.0], color=[0.1234564, 0.2, 0.3])

    payload = document.to_pdf_bytes()
    recreated = DocumentPDF.create_from_dict(document.parameters)
    objects = _pdf_objects(payload)
    annotation_refs = _annotation_refs_by_page(payload)
    annotation_ids = [annotation_id for page_refs in annotation_refs for annotation_id in page_refs]

    assert payload == document.to_pdf_bytes()
    assert [len(page_refs) for page_refs in annotation_refs] == [2, 2]
    assert b"/Subtype /Text" in objects[annotation_ids[0]]
    assert b"/Subtype /Highlight" in objects[annotation_ids[1]]
    assert b"/Rect [5 6 20 25]" in objects[annotation_ids[1]]
    assert b"/QuadPoints [5 25 20 25 5 6 20 6]" in objects[annotation_ids[1]]
    assert b"/C [0.2 0.4 0.6]" in objects[annotation_ids[1]]
    assert b"/Contents (Clause \\(A\\))" in objects[annotation_ids[1]]
    assert b"/Subtype /Highlight" in objects[annotation_ids[2]]
    assert b"/Rect [0 0 100 80]" in objects[annotation_ids[2]]
    assert b"/C [1 1 0]" in objects[annotation_ids[2]]
    assert b"/Subtype /Highlight" in objects[annotation_ids[3]]
    assert b"/Rect [10 10 20 20]" in objects[annotation_ids[3]]
    assert b"/C [0.123456 0.2 0.3]" in objects[annotation_ids[3]]
    assert document.highlight_annotations() == (
        {
            "page_number": 1,
            "rect": [5.0, 6.0, 20.0, 25.0],
            "color": [0.2, 0.4, 0.6],
            "contents": "Clause (A)",
        },
        {"page_number": 2, "rect": [0.0, 0.0, 100.0, 80.0], "color": [1.0, 1.0, 0.0]},
        {"page_number": 2, "rect": [10.0, 10.0, 20.0, 20.0], "color": [0.123456, 0.2, 0.3]},
    )
    assert recreated.parameters == document.parameters
    assert recreated.to_pdf_bytes() == payload


@pytest.mark.condition("PDF-DOC-HIGHLIGHT-ANNOTATION-P3")
def test_document_pdf_rejects_invalid_highlight_annotation_metadata() -> None:
    """PDF-DOC-HIGHLIGHT-ANNOTATION-P3: Highlight metadata fails at explicit boundaries."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()

    with pytest.raises(ValueError, match="Position must correlate"):
        document.add_highlight_annotation(2, [0.0, 0.0, 1.0, 1.0])
    with pytest.raises(TypeError):
        document.add_highlight_annotation(1, [0.0, 0.0, 1.0, 1.0], "#ff0000")  # type: ignore[misc]

    invalid_rectangles = [
        "0 0 1 1",
        [0.0, 0.0, 1.0],
        [True, 0.0, 1.0, 1.0],
        [0.0, 0.0, float("nan"), 1.0],
        [0.0, 0.0, 0.0, 1.0],
        [-1.0, 0.0, 1.0, 1.0],
        [0.0, 0.0, 101.0, 1.0],
    ]
    for rect in invalid_rectangles:
        with pytest.raises((TypeError, ValueError)):
            document.add_highlight_annotation(1, rect)  # type: ignore[arg-type]
        assert document.highlight_annotations() == ()

    invalid_colors = [
        "",
        "yellow",
        "#12345",
        "#12345g",
        "#3366990",
        None,
        object(),
        [1.0, 0.0],
        [1.0, 0.0, 0.0, 0.0],
        [1.0, True, 0.0],
        [-0.1, 0.0, 0.0],
        [1.1, 0.0, 0.0],
        [float("nan"), 0.0, 0.0],
    ]
    for color in invalid_colors:
        with pytest.raises((TypeError, ValueError)):
            document.add_highlight_annotation(1, [0.0, 0.0, 1.0, 1.0], color=color)  # type: ignore[arg-type]
        assert document.highlight_annotations() == ()

    for contents in [object(), "", "not latin \u0100"]:
        with pytest.raises((TypeError, ValueError)):
            document.add_highlight_annotation(1, [0.0, 0.0, 1.0, 1.0], contents=contents)  # type: ignore[arg-type]
        assert document.highlight_annotations() == ()

    document.add_highlight_annotation(1, [0.0, 0.0, 1.0, 1.0])
    document.clear_highlight_annotations()

    assert document.highlight_annotations() == ()
    assert "highlight_annotations" not in document.parameters["DocumentPDF"]
    assert b"/Annots" not in document.to_pdf_bytes()


@pytest.mark.condition("PDF-DOC-HIGHLIGHT-ANNOTATION-P3")
def test_document_pdf_highlight_annotations_track_page_insertions_and_removals() -> None:
    """PDF-DOC-HIGHLIGHT-ANNOTATION-P3: Highlight annotations stay aligned with page mutations."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_page()
    document.add_page()
    document.add_highlight_annotation(1, [1.0, 1.0, 10.0, 10.0], color="#ff0000")
    document.add_highlight_annotation(2, [2.0, 2.0, 20.0, 20.0], color="#00ff00", contents="middle")
    document.add_highlight_annotation(3, [3.0, 3.0, 30.0, 30.0], color="#0000ff")

    document.add_page(position=2)

    assert document.highlight_annotations() == (
        {"page_number": 1, "rect": [1.0, 1.0, 10.0, 10.0], "color": [1.0, 0.0, 0.0]},
        {
            "page_number": 3,
            "rect": [2.0, 2.0, 20.0, 20.0],
            "color": [0.0, 1.0, 0.0],
            "contents": "middle",
        },
        {"page_number": 4, "rect": [3.0, 3.0, 30.0, 30.0], "color": [0.0, 0.0, 1.0]},
    )

    document.remove_page(3)

    assert document.highlight_annotations() == (
        {"page_number": 1, "rect": [1.0, 1.0, 10.0, 10.0], "color": [1.0, 0.0, 0.0]},
        {"page_number": 3, "rect": [3.0, 3.0, 30.0, 30.0], "color": [0.0, 0.0, 1.0]},
    )

    document.remove_page(1)

    assert document.highlight_annotations() == ({"page_number": 2, "rect": [3.0, 3.0, 30.0, 30.0], "color": [0.0, 0.0, 1.0]},)


@pytest.mark.condition("PDF-DOC-HIGHLIGHT-ANNOTATION-P3")
def test_document_pdf_highlight_annotations_use_value_equality_for_large_page_removal() -> None:
    """PDF-DOC-HIGHLIGHT-ANNOTATION-P3: Highlight removal uses page-number value equality."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    for _ in range(260):
        document.add_page()
    document.add_highlight_annotation(1, [1.0, 1.0, 10.0, 10.0])
    document.add_highlight_annotation(int("260"), [2.0, 2.0, 20.0, 20.0])

    document.remove_page(int("260"))

    assert document.pages == 259
    assert document.highlight_annotations() == ({"page_number": 1, "rect": [1.0, 1.0, 10.0, 10.0], "color": [1.0, 1.0, 0.0]},)


@pytest.mark.condition("PDF-DOC-HIGHLIGHT-ANNOTATION-P3")
def test_document_pdf_rejects_invalid_serialized_highlight_annotation_metadata() -> None:
    """PDF-DOC-HIGHLIGHT-ANNOTATION-P3: Serialized highlights validate before rendering."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_highlight_annotation(1, [1.0, 2.0, 30.0, 40.0], color="#336699", contents="note")

    invalid_payloads = []
    for mutator in [
        lambda data: data["DocumentPDF"].__setitem__("highlight_annotations", "bad"),
        lambda data: data["DocumentPDF"].__setitem__("highlight_annotations", [object()]),
        lambda data: data["DocumentPDF"]["highlight_annotations"][0].pop("page_number"),
        lambda data: data["DocumentPDF"]["highlight_annotations"][0].pop("rect"),
        lambda data: data["DocumentPDF"]["highlight_annotations"][0].pop("color"),
        lambda data: data["DocumentPDF"]["highlight_annotations"][0].__setitem__("page_number", 2),
        lambda data: data["DocumentPDF"]["highlight_annotations"][0].__setitem__("rect", [0.0, 0.0, 0.0, 1.0]),
        lambda data: data["DocumentPDF"]["highlight_annotations"][0].__setitem__("color", [2.0, 0.0, 0.0]),
        lambda data: data["DocumentPDF"]["highlight_annotations"][0].__setitem__("contents", ""),
    ]:
        payload = deepcopy(document.parameters)
        mutator(payload)
        invalid_payloads.append(payload)

    for payload in invalid_payloads:
        with pytest.raises((TypeError, ValueError)):
            DocumentPDF.create_from_dict(payload)

    missing_optional_payload = deepcopy(document.parameters)
    missing_optional_payload["DocumentPDF"]["highlight_annotations"][0].pop("contents")
    recreated = DocumentPDF.create_from_dict(missing_optional_payload)

    assert recreated.highlight_annotations() == ({"page_number": 1, "rect": [1.0, 2.0, 30.0, 40.0], "color": [0.2, 0.4, 0.6]},)


@pytest.mark.condition("PDF-DOC-SQUARE-ANNOTATION-P3")
def test_document_pdf_emits_square_annotations_and_round_trips() -> None:
    """PDF-DOC-SQUARE-ANNOTATION-P3: Square annotations render and round-trip."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_page()
    document.add_highlight_annotation(1, [0.0, 0.0, 4.0, 4.0])
    document.add_square_annotation(1, [5.0, 6.0, 20.0, 25.0], color="#336699", contents="Box (A)")
    document.add_square_annotation(2, [0.0, 0.0, 100.0, 80.0])
    document.add_square_annotation(2, [10.0, 10.0, 20.0, 20.0], color=[0.1234564, 0.2, 0.3])

    payload = document.to_pdf_bytes()
    recreated = DocumentPDF.create_from_dict(document.parameters)
    objects = _pdf_objects(payload)
    annotation_refs = _annotation_refs_by_page(payload)
    annotation_ids = [annotation_id for page_refs in annotation_refs for annotation_id in page_refs]

    assert payload == document.to_pdf_bytes()
    assert [len(page_refs) for page_refs in annotation_refs] == [2, 2]
    assert b"/Subtype /Highlight" in objects[annotation_ids[0]]
    assert b"/Subtype /Square" in objects[annotation_ids[1]]
    assert b"/Rect [5 6 20 25]" in objects[annotation_ids[1]]
    assert b"/C [0.2 0.4 0.6]" in objects[annotation_ids[1]]
    assert b"/Border [0 0 1]" in objects[annotation_ids[1]]
    assert b"/Contents (Box \\(A\\))" in objects[annotation_ids[1]]
    assert b"/Subtype /Square" in objects[annotation_ids[2]]
    assert b"/Rect [0 0 100 80]" in objects[annotation_ids[2]]
    assert b"/C [1 0 0]" in objects[annotation_ids[2]]
    assert b"/Subtype /Square" in objects[annotation_ids[3]]
    assert b"/C [0.123456 0.2 0.3]" in objects[annotation_ids[3]]
    assert sorted(objects) == list(range(1, max(objects) + 1))
    assert document.square_annotations() == (
        {"page_number": 1, "rect": [5.0, 6.0, 20.0, 25.0], "color": [0.2, 0.4, 0.6], "contents": "Box (A)"},
        {"page_number": 2, "rect": [0.0, 0.0, 100.0, 80.0], "color": [1.0, 0.0, 0.0]},
        {"page_number": 2, "rect": [10.0, 10.0, 20.0, 20.0], "color": [0.123456, 0.2, 0.3]},
    )
    assert recreated.parameters == document.parameters
    assert recreated.to_pdf_bytes() == payload


@pytest.mark.condition("PDF-DOC-SQUARE-ANNOTATION-P3")
def test_document_pdf_rejects_invalid_square_annotation_metadata() -> None:
    """PDF-DOC-SQUARE-ANNOTATION-P3: Square metadata fails at explicit boundaries."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()

    with pytest.raises(ValueError, match="Position must correlate"):
        document.add_square_annotation(2, [0.0, 0.0, 1.0, 1.0])
    with pytest.raises(TypeError):
        document.add_square_annotation(1, [0.0, 0.0, 1.0, 1.0], "#ff0000")  # type: ignore[misc]

    invalid_rectangles = [
        "0 0 1 1",
        [0.0, 0.0, 1.0],
        [True, 0.0, 1.0, 1.0],
        [0.0, 0.0, float("nan"), 1.0],
        [0.0, 0.0, 0.0, 1.0],
        [-1.0, 0.0, 1.0, 1.0],
        [0.0, 0.0, 101.0, 1.0],
    ]
    for rect in invalid_rectangles:
        with pytest.raises((TypeError, ValueError)):
            document.add_square_annotation(1, rect)  # type: ignore[arg-type]
        assert document.square_annotations() == ()

    invalid_colors = [
        "",
        "red",
        "#12345",
        "#12345g",
        "#3366990",
        None,
        object(),
        [1.0, 0.0],
        [1.0, 0.0, 0.0, 0.0],
        [1.0, True, 0.0],
        [-0.1, 0.0, 0.0],
        [1.1, 0.0, 0.0],
        [float("nan"), 0.0, 0.0],
    ]
    for color in invalid_colors:
        with pytest.raises((TypeError, ValueError)):
            document.add_square_annotation(1, [0.0, 0.0, 1.0, 1.0], color=color)  # type: ignore[arg-type]
        assert document.square_annotations() == ()

    for contents in [object(), "", "not latin \u0100"]:
        with pytest.raises((TypeError, ValueError)):
            document.add_square_annotation(1, [0.0, 0.0, 1.0, 1.0], contents=contents)  # type: ignore[arg-type]
        assert document.square_annotations() == ()

    document.add_square_annotation(1, [0.0, 0.0, 1.0, 1.0])
    document.clear_square_annotations()

    assert document.square_annotations() == ()
    assert "square_annotations" not in document.parameters["DocumentPDF"]
    assert b"/Annots" not in document.to_pdf_bytes()


@pytest.mark.condition("PDF-DOC-SQUARE-ANNOTATION-P3")
def test_document_pdf_square_annotations_track_page_insertions_and_removals() -> None:
    """PDF-DOC-SQUARE-ANNOTATION-P3: Square annotations stay aligned with page mutations."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_page()
    document.add_page()
    document.add_square_annotation(1, [1.0, 1.0, 10.0, 10.0], color="#ff0000")
    document.add_square_annotation(2, [2.0, 2.0, 20.0, 20.0], color="#00ff00", contents="middle")
    document.add_square_annotation(3, [3.0, 3.0, 30.0, 30.0], color="#0000ff")

    document.add_page(position=2)

    assert document.square_annotations() == (
        {"page_number": 1, "rect": [1.0, 1.0, 10.0, 10.0], "color": [1.0, 0.0, 0.0]},
        {
            "page_number": 3,
            "rect": [2.0, 2.0, 20.0, 20.0],
            "color": [0.0, 1.0, 0.0],
            "contents": "middle",
        },
        {"page_number": 4, "rect": [3.0, 3.0, 30.0, 30.0], "color": [0.0, 0.0, 1.0]},
    )

    document.remove_page(3)

    assert document.square_annotations() == (
        {"page_number": 1, "rect": [1.0, 1.0, 10.0, 10.0], "color": [1.0, 0.0, 0.0]},
        {"page_number": 3, "rect": [3.0, 3.0, 30.0, 30.0], "color": [0.0, 0.0, 1.0]},
    )

    document.remove_page(1)

    assert document.square_annotations() == ({"page_number": 2, "rect": [3.0, 3.0, 30.0, 30.0], "color": [0.0, 0.0, 1.0]},)


@pytest.mark.condition("PDF-DOC-SQUARE-ANNOTATION-P3")
def test_document_pdf_square_annotations_use_value_equality_for_large_page_removal() -> None:
    """PDF-DOC-SQUARE-ANNOTATION-P3: Square removal uses page-number value equality."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    for _ in range(260):
        document.add_page()
    document.add_square_annotation(1, [1.0, 1.0, 10.0, 10.0])
    document.add_square_annotation(int("260"), [2.0, 2.0, 20.0, 20.0])

    document.remove_page(int("260"))

    assert document.pages == 259
    assert document.square_annotations() == ({"page_number": 1, "rect": [1.0, 1.0, 10.0, 10.0], "color": [1.0, 0.0, 0.0]},)


@pytest.mark.condition("PDF-DOC-SQUARE-ANNOTATION-P3")
def test_document_pdf_rejects_invalid_serialized_square_annotation_metadata() -> None:
    """PDF-DOC-SQUARE-ANNOTATION-P3: Serialized squares validate before rendering."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_square_annotation(1, [1.0, 2.0, 30.0, 40.0], color="#336699", contents="note")

    invalid_payloads = []
    for mutator in [
        lambda data: data["DocumentPDF"].__setitem__("square_annotations", "bad"),
        lambda data: data["DocumentPDF"].__setitem__("square_annotations", [object()]),
        lambda data: data["DocumentPDF"]["square_annotations"][0].pop("page_number"),
        lambda data: data["DocumentPDF"]["square_annotations"][0].pop("rect"),
        lambda data: data["DocumentPDF"]["square_annotations"][0].pop("color"),
        lambda data: data["DocumentPDF"]["square_annotations"][0].__setitem__("page_number", 2),
        lambda data: data["DocumentPDF"]["square_annotations"][0].__setitem__("rect", [0.0, 0.0, 0.0, 1.0]),
        lambda data: data["DocumentPDF"]["square_annotations"][0].__setitem__("color", [2.0, 0.0, 0.0]),
        lambda data: data["DocumentPDF"]["square_annotations"][0].__setitem__("contents", ""),
    ]:
        payload = deepcopy(document.parameters)
        mutator(payload)
        invalid_payloads.append(payload)

    for payload in invalid_payloads:
        with pytest.raises((TypeError, ValueError)):
            DocumentPDF.create_from_dict(payload)

    missing_optional_payload = deepcopy(document.parameters)
    missing_optional_payload["DocumentPDF"]["square_annotations"][0].pop("contents")
    recreated = DocumentPDF.create_from_dict(missing_optional_payload)

    assert recreated.square_annotations() == ({"page_number": 1, "rect": [1.0, 2.0, 30.0, 40.0], "color": [0.2, 0.4, 0.6]},)


@pytest.mark.condition("PDF-DOC-CIRCLE-ANNOTATION-P3")
def test_document_pdf_emits_circle_annotations_and_round_trips() -> None:
    """PDF-DOC-CIRCLE-ANNOTATION-P3: Circle annotations render and round-trip."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_page()
    document.add_square_annotation(1, [0.0, 0.0, 4.0, 4.0])
    document.add_circle_annotation(1, [5.0, 6.0, 20.0, 25.0], color="#336699", contents="Oval (A)")
    document.add_circle_annotation(2, [0.0, 0.0, 100.0, 80.0])
    document.add_circle_annotation(2, [10.0, 10.0, 20.0, 20.0], color=[0.1234564, 0.2, 0.3])

    payload = document.to_pdf_bytes()
    recreated = DocumentPDF.create_from_dict(document.parameters)
    objects = _pdf_objects(payload)
    annotation_refs = _annotation_refs_by_page(payload)
    annotation_ids = [annotation_id for page_refs in annotation_refs for annotation_id in page_refs]

    assert payload == document.to_pdf_bytes()
    assert [len(page_refs) for page_refs in annotation_refs] == [2, 2]
    assert b"/Subtype /Square" in objects[annotation_ids[0]]
    assert b"/Subtype /Circle" in objects[annotation_ids[1]]
    assert b"/Rect [5 6 20 25]" in objects[annotation_ids[1]]
    assert b"/C [0.2 0.4 0.6]" in objects[annotation_ids[1]]
    assert b"/Border [0 0 1]" in objects[annotation_ids[1]]
    assert b"/Contents (Oval \\(A\\))" in objects[annotation_ids[1]]
    assert b"/Subtype /Circle" in objects[annotation_ids[2]]
    assert b"/Rect [0 0 100 80]" in objects[annotation_ids[2]]
    assert b"/C [1 0 0]" in objects[annotation_ids[2]]
    assert b"/Subtype /Circle" in objects[annotation_ids[3]]
    assert b"/C [0.123456 0.2 0.3]" in objects[annotation_ids[3]]
    assert sorted(objects) == list(range(1, max(objects) + 1))
    assert document.circle_annotations() == (
        {"page_number": 1, "rect": [5.0, 6.0, 20.0, 25.0], "color": [0.2, 0.4, 0.6], "contents": "Oval (A)"},
        {"page_number": 2, "rect": [0.0, 0.0, 100.0, 80.0], "color": [1.0, 0.0, 0.0]},
        {"page_number": 2, "rect": [10.0, 10.0, 20.0, 20.0], "color": [0.123456, 0.2, 0.3]},
    )
    assert recreated.parameters == document.parameters
    assert recreated.to_pdf_bytes() == payload


@pytest.mark.condition("PDF-DOC-CIRCLE-ANNOTATION-P3")
def test_document_pdf_rejects_invalid_circle_annotation_metadata() -> None:
    """PDF-DOC-CIRCLE-ANNOTATION-P3: Circle metadata fails at explicit boundaries."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()

    with pytest.raises(ValueError, match="Position must correlate"):
        document.add_circle_annotation(2, [0.0, 0.0, 1.0, 1.0])
    with pytest.raises(TypeError):
        document.add_circle_annotation(1, [0.0, 0.0, 1.0, 1.0], "#ff0000")  # type: ignore[misc]

    invalid_rectangles = [
        "0 0 1 1",
        [0.0, 0.0, 1.0],
        [True, 0.0, 1.0, 1.0],
        [0.0, 0.0, float("nan"), 1.0],
        [0.0, 0.0, 0.0, 1.0],
        [-1.0, 0.0, 1.0, 1.0],
        [0.0, 0.0, 101.0, 1.0],
    ]
    for rect in invalid_rectangles:
        with pytest.raises((TypeError, ValueError)):
            document.add_circle_annotation(1, rect)  # type: ignore[arg-type]
        assert document.circle_annotations() == ()

    invalid_colors = [
        "",
        "red",
        "#12345",
        "#12345g",
        "#3366990",
        None,
        object(),
        [1.0, 0.0],
        [1.0, 0.0, 0.0, 0.0],
        [1.0, True, 0.0],
        [-0.1, 0.0, 0.0],
        [1.1, 0.0, 0.0],
        [float("nan"), 0.0, 0.0],
    ]
    for color in invalid_colors:
        with pytest.raises((TypeError, ValueError)):
            document.add_circle_annotation(1, [0.0, 0.0, 1.0, 1.0], color=color)  # type: ignore[arg-type]
        assert document.circle_annotations() == ()

    for contents in [object(), "", "not latin \u0100"]:
        with pytest.raises((TypeError, ValueError)):
            document.add_circle_annotation(1, [0.0, 0.0, 1.0, 1.0], contents=contents)  # type: ignore[arg-type]
        assert document.circle_annotations() == ()

    document.add_circle_annotation(1, [0.0, 0.0, 1.0, 1.0])
    document.clear_circle_annotations()

    assert document.circle_annotations() == ()
    assert "circle_annotations" not in document.parameters["DocumentPDF"]
    assert b"/Annots" not in document.to_pdf_bytes()


@pytest.mark.condition("PDF-DOC-CIRCLE-ANNOTATION-P3")
def test_document_pdf_circle_annotations_track_page_insertions_and_removals() -> None:
    """PDF-DOC-CIRCLE-ANNOTATION-P3: Circle annotations stay aligned with page mutations."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_page()
    document.add_page()
    document.add_circle_annotation(1, [1.0, 1.0, 10.0, 10.0], color="#ff0000")
    document.add_circle_annotation(2, [2.0, 2.0, 20.0, 20.0], color="#00ff00", contents="middle")
    document.add_circle_annotation(3, [3.0, 3.0, 30.0, 30.0], color="#0000ff")

    document.add_page(position=2)

    assert document.circle_annotations() == (
        {"page_number": 1, "rect": [1.0, 1.0, 10.0, 10.0], "color": [1.0, 0.0, 0.0]},
        {
            "page_number": 3,
            "rect": [2.0, 2.0, 20.0, 20.0],
            "color": [0.0, 1.0, 0.0],
            "contents": "middle",
        },
        {"page_number": 4, "rect": [3.0, 3.0, 30.0, 30.0], "color": [0.0, 0.0, 1.0]},
    )

    document.remove_page(3)

    assert document.circle_annotations() == (
        {"page_number": 1, "rect": [1.0, 1.0, 10.0, 10.0], "color": [1.0, 0.0, 0.0]},
        {"page_number": 3, "rect": [3.0, 3.0, 30.0, 30.0], "color": [0.0, 0.0, 1.0]},
    )

    document.remove_page(1)

    assert document.circle_annotations() == ({"page_number": 2, "rect": [3.0, 3.0, 30.0, 30.0], "color": [0.0, 0.0, 1.0]},)


@pytest.mark.condition("PDF-DOC-CIRCLE-ANNOTATION-P3")
def test_document_pdf_circle_annotations_use_value_equality_for_large_page_removal() -> None:
    """PDF-DOC-CIRCLE-ANNOTATION-P3: Circle removal uses page-number value equality."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    for _ in range(260):
        document.add_page()
    document.add_circle_annotation(1, [1.0, 1.0, 10.0, 10.0])
    document.add_circle_annotation(int("260"), [2.0, 2.0, 20.0, 20.0])

    document.remove_page(int("260"))

    assert document.pages == 259
    assert document.circle_annotations() == ({"page_number": 1, "rect": [1.0, 1.0, 10.0, 10.0], "color": [1.0, 0.0, 0.0]},)


@pytest.mark.condition("PDF-DOC-CIRCLE-ANNOTATION-P3")
def test_document_pdf_rejects_invalid_serialized_circle_annotation_metadata() -> None:
    """PDF-DOC-CIRCLE-ANNOTATION-P3: Serialized circles validate before rendering."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_circle_annotation(1, [1.0, 2.0, 30.0, 40.0], color="#336699", contents="note")

    invalid_payloads = []
    for mutator in [
        lambda data: data["DocumentPDF"].__setitem__("circle_annotations", "bad"),
        lambda data: data["DocumentPDF"].__setitem__("circle_annotations", [object()]),
        lambda data: data["DocumentPDF"]["circle_annotations"][0].pop("page_number"),
        lambda data: data["DocumentPDF"]["circle_annotations"][0].pop("rect"),
        lambda data: data["DocumentPDF"]["circle_annotations"][0].pop("color"),
        lambda data: data["DocumentPDF"]["circle_annotations"][0].__setitem__("page_number", 2),
        lambda data: data["DocumentPDF"]["circle_annotations"][0].__setitem__("rect", [0.0, 0.0, 0.0, 1.0]),
        lambda data: data["DocumentPDF"]["circle_annotations"][0].__setitem__("color", [2.0, 0.0, 0.0]),
        lambda data: data["DocumentPDF"]["circle_annotations"][0].__setitem__("contents", ""),
    ]:
        payload = deepcopy(document.parameters)
        mutator(payload)
        invalid_payloads.append(payload)

    for payload in invalid_payloads:
        with pytest.raises((TypeError, ValueError)):
            DocumentPDF.create_from_dict(payload)

    missing_optional_payload = deepcopy(document.parameters)
    missing_optional_payload["DocumentPDF"]["circle_annotations"][0].pop("contents")
    recreated = DocumentPDF.create_from_dict(missing_optional_payload)

    assert recreated.circle_annotations() == ({"page_number": 1, "rect": [1.0, 2.0, 30.0, 40.0], "color": [0.2, 0.4, 0.6]},)


@pytest.mark.condition("PDF-DOC-LINE-ANNOTATION-P3")
def test_document_pdf_emits_line_annotations_and_round_trips() -> None:
    """PDF-DOC-LINE-ANNOTATION-P3: Line annotations render and round-trip."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_page()
    document.add_circle_annotation(1, [0.0, 0.0, 4.0, 4.0])
    document.add_line_annotation(1, [5.0, 6.0], [20.0, 25.0], color="#336699", contents="Leader (A)")
    document.add_line_annotation(1, [20.0, 25.0], [5.0, 6.0], color="#663399")
    document.add_line_annotation(2, [0.0, 0.0], [100.0, 0.0])
    document.add_line_annotation(2, [100.0, 0.0], [100.0, 80.0], color="#00ff00")
    document.add_line_annotation(2, [0.0, 80.0], [100.0, 80.0], color="#0000ff")
    document.add_line_annotation(2, [10.0, 10.0], [20.0, 20.0], color=[0.1234564, 0.2, 0.3])

    payload = document.to_pdf_bytes()
    recreated = DocumentPDF.create_from_dict(document.parameters)
    objects = _pdf_objects(payload)
    annotation_refs = _annotation_refs_by_page(payload)
    annotation_ids = [annotation_id for page_refs in annotation_refs for annotation_id in page_refs]

    assert payload == document.to_pdf_bytes()
    assert [len(page_refs) for page_refs in annotation_refs] == [3, 4]
    assert b"/Subtype /Circle" in objects[annotation_ids[0]]
    assert b"/Subtype /Line" in objects[annotation_ids[1]]
    assert b"/Rect [4 5 21 26]" in objects[annotation_ids[1]]
    assert b"/L [5 6 20 25]" in objects[annotation_ids[1]]
    assert b"/C [0.2 0.4 0.6]" in objects[annotation_ids[1]]
    assert b"/Border [0 0 1]" in objects[annotation_ids[1]]
    assert b"/Contents (Leader \\(A\\))" in objects[annotation_ids[1]]
    assert b"/Subtype /Line" in objects[annotation_ids[2]]
    assert b"/Rect [4 5 21 26]" in objects[annotation_ids[2]]
    assert b"/L [20 25 5 6]" in objects[annotation_ids[2]]
    assert b"/Subtype /Line" in objects[annotation_ids[3]]
    assert b"/Rect [0 0 100 1]" in objects[annotation_ids[3]]
    assert b"/L [0 0 100 0]" in objects[annotation_ids[3]]
    assert b"/C [1 0 0]" in objects[annotation_ids[3]]
    assert b"/Subtype /Line" in objects[annotation_ids[3]]
    assert b"/Subtype /Line" in objects[annotation_ids[4]]
    assert b"/Rect [99 0 100 80]" in objects[annotation_ids[4]]
    assert b"/L [100 0 100 80]" in objects[annotation_ids[4]]
    assert b"/Subtype /Line" in objects[annotation_ids[5]]
    assert b"/Rect [0 79 100 80]" in objects[annotation_ids[5]]
    assert b"/L [0 80 100 80]" in objects[annotation_ids[5]]
    assert b"/Subtype /Line" in objects[annotation_ids[6]]
    assert b"/C [0.123456 0.2 0.3]" in objects[annotation_ids[6]]
    assert sorted(objects) == list(range(1, max(objects) + 1))
    assert document.line_annotations() == (
        {"page_number": 1, "start": [5.0, 6.0], "end": [20.0, 25.0], "color": [0.2, 0.4, 0.6], "contents": "Leader (A)"},
        {"page_number": 1, "start": [20.0, 25.0], "end": [5.0, 6.0], "color": [0.4, 0.2, 0.6]},
        {"page_number": 2, "start": [0.0, 0.0], "end": [100.0, 0.0], "color": [1.0, 0.0, 0.0]},
        {"page_number": 2, "start": [100.0, 0.0], "end": [100.0, 80.0], "color": [0.0, 1.0, 0.0]},
        {"page_number": 2, "start": [0.0, 80.0], "end": [100.0, 80.0], "color": [0.0, 0.0, 1.0]},
        {"page_number": 2, "start": [10.0, 10.0], "end": [20.0, 20.0], "color": [0.123456, 0.2, 0.3]},
    )
    assert recreated.parameters == document.parameters
    assert recreated.to_pdf_bytes() == payload


@pytest.mark.condition("PDF-DOC-LINE-ANNOTATION-P3")
def test_document_pdf_rejects_invalid_line_annotation_metadata() -> None:
    """PDF-DOC-LINE-ANNOTATION-P3: Line metadata fails at explicit boundaries."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()

    with pytest.raises(ValueError, match="Position must correlate"):
        document.add_line_annotation(2, [0.0, 0.0], [1.0, 1.0])
    with pytest.raises(TypeError):
        document.add_line_annotation(1, [0.0, 0.0], [1.0, 1.0], "#ff0000")  # type: ignore[misc]
    for point in [object(), "ab", b"ab", [0.0], [0.0, 1.0, 2.0]]:
        with pytest.raises(TypeError, match="two-number sequence"):
            document.add_line_annotation(1, point, [1.0, 1.0])  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="two-number sequence"):
            document.add_line_annotation(1, [1.0, 1.0], point)  # type: ignore[arg-type]

    invalid_points = [
        "0 0",
        [0.0],
        [True, 0.0],
        [0.0, float("nan")],
        [-1.0, 0.0],
        [0.0, -0.5],
        [101.0, 0.0],
        [0.0, 81.0],
    ]
    for point in invalid_points:
        with pytest.raises((TypeError, ValueError)):
            document.add_line_annotation(1, point, [1.0, 1.0])  # type: ignore[arg-type]
        assert document.line_annotations() == ()
        with pytest.raises((TypeError, ValueError)):
            document.add_line_annotation(1, [1.0, 1.0], point)  # type: ignore[arg-type]
        assert document.line_annotations() == ()

    with pytest.raises(ValueError, match="endpoints must be distinct"):
        document.add_line_annotation(1, [1.0, 1.0], [1.0, 1.0])
    assert document.line_annotations() == ()

    invalid_colors = [
        "",
        "red",
        "#12345",
        "#12345g",
        "#3366990",
        None,
        object(),
        [1.0, 0.0],
        [1.0, 0.0, 0.0, 0.0],
        [1.0, True, 0.0],
        [-0.1, 0.0, 0.0],
        [1.1, 0.0, 0.0],
        [float("nan"), 0.0, 0.0],
    ]
    for color in invalid_colors:
        with pytest.raises((TypeError, ValueError)):
            document.add_line_annotation(1, [0.0, 0.0], [1.0, 1.0], color=color)  # type: ignore[arg-type]
        assert document.line_annotations() == ()

    for contents in [object(), "", "not latin \u0100"]:
        with pytest.raises((TypeError, ValueError)):
            document.add_line_annotation(1, [0.0, 0.0], [1.0, 1.0], contents=contents)  # type: ignore[arg-type]
        assert document.line_annotations() == ()

    document.add_line_annotation(1, [0.0, 0.0], [1.0, 1.0])
    document.clear_line_annotations()

    assert document.line_annotations() == ()
    assert "line_annotations" not in document.parameters["DocumentPDF"]
    assert b"/Annots" not in document.to_pdf_bytes()


@pytest.mark.condition("PDF-DOC-LINE-ANNOTATION-P3")
def test_document_pdf_line_annotations_track_page_insertions_and_removals() -> None:
    """PDF-DOC-LINE-ANNOTATION-P3: Line annotations stay aligned with page mutations."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_page()
    document.add_page()
    document.add_line_annotation(1, [1.0, 1.0], [10.0, 10.0], color="#ff0000")
    document.add_line_annotation(2, [2.0, 2.0], [20.0, 20.0], color="#00ff00", contents="middle")
    document.add_line_annotation(3, [3.0, 3.0], [30.0, 30.0], color="#0000ff")

    document.add_page(position=2)

    assert document.line_annotations() == (
        {"page_number": 1, "start": [1.0, 1.0], "end": [10.0, 10.0], "color": [1.0, 0.0, 0.0]},
        {
            "page_number": 3,
            "start": [2.0, 2.0],
            "end": [20.0, 20.0],
            "color": [0.0, 1.0, 0.0],
            "contents": "middle",
        },
        {"page_number": 4, "start": [3.0, 3.0], "end": [30.0, 30.0], "color": [0.0, 0.0, 1.0]},
    )

    document.remove_page(3)

    assert document.line_annotations() == (
        {"page_number": 1, "start": [1.0, 1.0], "end": [10.0, 10.0], "color": [1.0, 0.0, 0.0]},
        {"page_number": 3, "start": [3.0, 3.0], "end": [30.0, 30.0], "color": [0.0, 0.0, 1.0]},
    )

    document.remove_page(1)

    assert document.line_annotations() == ({"page_number": 2, "start": [3.0, 3.0], "end": [30.0, 30.0], "color": [0.0, 0.0, 1.0]},)


@pytest.mark.condition("PDF-DOC-LINE-ANNOTATION-P3")
def test_document_pdf_line_annotations_use_value_equality_for_large_page_removal() -> None:
    """PDF-DOC-LINE-ANNOTATION-P3: Line removal uses page-number value equality."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    for _ in range(260):
        document.add_page()
    document.add_line_annotation(1, [1.0, 1.0], [10.0, 10.0])
    document.add_line_annotation(int("260"), [2.0, 2.0], [20.0, 20.0])

    document.remove_page(int("260"))

    assert document.pages == 259
    assert document.line_annotations() == ({"page_number": 1, "start": [1.0, 1.0], "end": [10.0, 10.0], "color": [1.0, 0.0, 0.0]},)


@pytest.mark.condition("PDF-DOC-LINE-ANNOTATION-P3")
def test_document_pdf_rejects_invalid_serialized_line_annotation_metadata() -> None:
    """PDF-DOC-LINE-ANNOTATION-P3: Serialized lines validate before rendering."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_line_annotation(1, [1.0, 2.0], [30.0, 40.0], color="#336699", contents="note")

    invalid_payloads = []
    for mutator in [
        lambda data: data["DocumentPDF"].__setitem__("line_annotations", "bad"),
        lambda data: data["DocumentPDF"].__setitem__("line_annotations", [object()]),
        lambda data: data["DocumentPDF"]["line_annotations"][0].pop("page_number"),
        lambda data: data["DocumentPDF"]["line_annotations"][0].pop("start"),
        lambda data: data["DocumentPDF"]["line_annotations"][0].pop("end"),
        lambda data: data["DocumentPDF"]["line_annotations"][0].pop("color"),
        lambda data: data["DocumentPDF"]["line_annotations"][0].__setitem__("page_number", 2),
        lambda data: data["DocumentPDF"]["line_annotations"][0].__setitem__("start", [0.0]),
        lambda data: data["DocumentPDF"]["line_annotations"][0].__setitem__("end", [1.0, 2.0]),
        lambda data: data["DocumentPDF"]["line_annotations"][0].__setitem__("color", [2.0, 0.0, 0.0]),
        lambda data: data["DocumentPDF"]["line_annotations"][0].__setitem__("contents", ""),
    ]:
        payload = deepcopy(document.parameters)
        mutator(payload)
        invalid_payloads.append(payload)

    for payload in invalid_payloads:
        with pytest.raises((TypeError, ValueError)):
            DocumentPDF.create_from_dict(payload)

    missing_optional_payload = deepcopy(document.parameters)
    missing_optional_payload["DocumentPDF"]["line_annotations"][0].pop("contents")
    recreated = DocumentPDF.create_from_dict(missing_optional_payload)

    assert recreated.line_annotations() == ({"page_number": 1, "start": [1.0, 2.0], "end": [30.0, 40.0], "color": [0.2, 0.4, 0.6]},)


@pytest.mark.condition("PDF-DOC-TEXT-ANNOTATION-P3")
def test_document_pdf_rejects_invalid_serialized_text_annotation_metadata() -> None:
    """PDF-DOC-TEXT-ANNOTATION-P3: Serialized text annotations validate before rendering."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_text_annotation(1, [1.0, 2.0, 30.0, 40.0], "note", title="Reviewer", open=True)

    invalid_payloads = []
    for mutator in [
        lambda data: data["DocumentPDF"].__setitem__("text_annotations", "bad"),
        lambda data: data["DocumentPDF"].__setitem__("text_annotations", [object()]),
        lambda data: data["DocumentPDF"]["text_annotations"][0].pop("page_number"),
        lambda data: data["DocumentPDF"]["text_annotations"][0].pop("rect"),
        lambda data: data["DocumentPDF"]["text_annotations"][0].pop("contents"),
        lambda data: data["DocumentPDF"]["text_annotations"][0].__setitem__("page_number", 2),
        lambda data: data["DocumentPDF"]["text_annotations"][0].__setitem__("rect", [0.0, 0.0, 0.0, 1.0]),
        lambda data: data["DocumentPDF"]["text_annotations"][0].__setitem__("contents", ""),
        lambda data: data["DocumentPDF"]["text_annotations"][0].__setitem__("title", object()),
        lambda data: data["DocumentPDF"]["text_annotations"][0].__setitem__("open", 1),
    ]:
        payload = deepcopy(document.parameters)
        mutator(payload)
        invalid_payloads.append(payload)

    for payload in invalid_payloads:
        with pytest.raises((TypeError, ValueError)):
            DocumentPDF.create_from_dict(payload)

    missing_optional_payload = deepcopy(document.parameters)
    missing_optional_payload["DocumentPDF"]["text_annotations"][0].pop("title")
    missing_optional_payload["DocumentPDF"]["text_annotations"][0].pop("open")
    recreated = DocumentPDF.create_from_dict(missing_optional_payload)

    assert recreated.text_annotations() == ({"page_number": 1, "rect": [1.0, 2.0, 30.0, 40.0], "contents": "note"},)


@pytest.mark.condition("PDF-DOC-PAGE-LINK-P3")
def test_document_pdf_emits_internal_page_link_annotations_and_round_trips() -> None:
    """PDF-DOC-PAGE-LINK-P3: Internal page link annotations render and round-trip."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_page()
    document.add_page()
    document.add_page_link(1, [5.0, 6.0, 20.0, 25.0], 3, left=12.0)
    document.add_page_link(1, [30.0, 6.0, 45.0, 25.0], 2, left=2.0, top=70.0, zoom=1.5)

    payload = document.to_pdf_bytes()
    recreated = DocumentPDF.create_from_dict(document.parameters)
    objects = _pdf_objects(payload)
    page_ids = _page_object_ids(payload)
    annotation_refs = _annotation_refs_by_page(payload)
    annotation_ids = [annotation_id for page_refs in annotation_refs for annotation_id in page_refs]

    assert payload == document.to_pdf_bytes()
    assert [len(page_refs) for page_refs in annotation_refs] == [2]
    assert b"/Subtype /Link" in objects[annotation_ids[0]]
    assert b"/Rect [5 6 20 25]" in objects[annotation_ids[0]]
    assert b"/Border [0 0 0]" in objects[annotation_ids[0]]
    assert f"/Dest [{page_ids[2]} 0 R /XYZ 12 null null]".encode("ascii") in objects[annotation_ids[0]]
    assert b"/Rect [30 6 45 25]" in objects[annotation_ids[1]]
    assert f"/Dest [{page_ids[1]} 0 R /XYZ 2 70 1.5]".encode("ascii") in objects[annotation_ids[1]]
    assert sorted(objects) == list(range(1, max(objects) + 1))
    assert document.page_links() == (
        {"page_number": 1, "rect": [5.0, 6.0, 20.0, 25.0], "target_page_number": 3, "left": 12.0},
        {"page_number": 1, "rect": [30.0, 6.0, 45.0, 25.0], "target_page_number": 2, "left": 2.0, "top": 70.0, "zoom": 1.5},
    )
    assert recreated.parameters == document.parameters
    assert recreated.to_pdf_bytes() == payload


@pytest.mark.condition("PDF-DOC-PAGE-LINK-P3")
def test_document_pdf_rejects_invalid_internal_page_link_metadata() -> None:
    """PDF-DOC-PAGE-LINK-P3: Internal page link metadata fails at explicit boundaries."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_page()

    with pytest.raises(ValueError, match="Position must correlate"):
        document.add_page_link(3, [0.0, 0.0, 1.0, 1.0], 1)
    with pytest.raises(ValueError, match="Position must correlate"):
        document.add_page_link(1, [0.0, 0.0, 1.0, 1.0], 3)

    invalid_rectangles = [
        "0 0 1 1",
        [0.0, 0.0, 1.0],
        [True, 0.0, 1.0, 1.0],
        [0.0, 0.0, float("nan"), 1.0],
        [0.0, 0.0, 0.0, 1.0],
        [-1.0, 0.0, 1.0, 1.0],
        [0.0, 0.0, 101.0, 1.0],
    ]
    for rect in invalid_rectangles:
        with pytest.raises((TypeError, ValueError)):
            document.add_page_link(1, rect, 2)  # type: ignore[arg-type]
        assert document.page_links() == ()

    invalid_destinations = [
        {"left": True},
        {"left": float("nan")},
        {"top": object()},
        {"top": float("inf")},
        {"zoom": "bad"},
        {"zoom": float("-inf")},
    ]
    for kwargs in invalid_destinations:
        with pytest.raises((TypeError, ValueError), match="page link"):
            document.add_page_link(1, [0.0, 0.0, 1.0, 1.0], 2, **kwargs)  # type: ignore[arg-type]
        assert document.page_links() == ()

    document.add_page_link(1, [0.0, 0.0, 1.0, 1.0], 2)
    document.clear_page_links()

    assert document.page_links() == ()
    assert "page_links" not in document.parameters["DocumentPDF"]
    assert b"/Annots" not in document.to_pdf_bytes()


@pytest.mark.condition("PDF-DOC-PAGE-LINK-P3")
def test_document_pdf_internal_page_links_track_page_insertions_and_removals() -> None:
    """PDF-DOC-PAGE-LINK-P3: Internal page links stay aligned with page mutations."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_page()
    document.add_page()
    document.add_page_link(1, [1.0, 1.0, 10.0, 10.0], 3, left=1.0)
    document.add_page_link(2, [2.0, 2.0, 20.0, 20.0], 1, left=2.0)
    document.add_page_link(3, [3.0, 3.0, 30.0, 30.0], 2, left=3.0)
    document.add_page_link(3, [4.0, 4.0, 40.0, 40.0], 1, left=4.0)

    document.add_page(position=2)

    assert document.page_links() == (
        {"page_number": 1, "rect": [1.0, 1.0, 10.0, 10.0], "target_page_number": 4, "left": 1.0},
        {"page_number": 3, "rect": [2.0, 2.0, 20.0, 20.0], "target_page_number": 1, "left": 2.0},
        {"page_number": 4, "rect": [3.0, 3.0, 30.0, 30.0], "target_page_number": 3, "left": 3.0},
        {"page_number": 4, "rect": [4.0, 4.0, 40.0, 40.0], "target_page_number": 1, "left": 4.0},
    )

    document.remove_page(3)

    assert document.page_links() == (
        {"page_number": 1, "rect": [1.0, 1.0, 10.0, 10.0], "target_page_number": 3, "left": 1.0},
        {"page_number": 3, "rect": [4.0, 4.0, 40.0, 40.0], "target_page_number": 1, "left": 4.0},
    )

    document.remove_page(1)

    assert document.page_links() == ()


@pytest.mark.condition("PDF-DOC-PAGE-LINK-P3")
def test_document_pdf_internal_page_links_use_value_equality_for_large_page_removal() -> None:
    """PDF-DOC-PAGE-LINK-P3: Internal page link removal uses page-number value equality."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    for _ in range(260):
        document.add_page()
    document.add_page_link(1, [1.0, 1.0, 10.0, 10.0], 2)
    document.add_page_link(1, [2.0, 2.0, 20.0, 20.0], int("260"))
    document.add_page_link(int("260"), [3.0, 3.0, 30.0, 30.0], 1)

    document.remove_page(int("260"))

    assert document.pages == 259
    assert document.page_links() == ({"page_number": 1, "rect": [1.0, 1.0, 10.0, 10.0], "target_page_number": 2, "left": 0.0},)


@pytest.mark.condition("PDF-DOC-PAGE-LINK-P3")
def test_document_pdf_rejects_invalid_serialized_internal_page_link_metadata() -> None:
    """PDF-DOC-PAGE-LINK-P3: Serialized internal page links validate before rendering."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_page()
    document.add_page_link(1, [1.0, 2.0, 30.0, 40.0], 2, left=5.0, top=6.0, zoom=1.25)

    invalid_payloads = []
    for mutator in [
        lambda data: data["DocumentPDF"].__setitem__("page_links", "bad"),
        lambda data: data["DocumentPDF"].__setitem__("page_links", [object()]),
        lambda data: data["DocumentPDF"]["page_links"][0].pop("page_number"),
        lambda data: data["DocumentPDF"]["page_links"][0].pop("rect"),
        lambda data: data["DocumentPDF"]["page_links"][0].pop("target_page_number"),
        lambda data: data["DocumentPDF"]["page_links"][0].__setitem__("page_number", 3),
        lambda data: data["DocumentPDF"]["page_links"][0].__setitem__("target_page_number", 3),
        lambda data: data["DocumentPDF"]["page_links"][0].__setitem__("rect", [0.0, 0.0, 0.0, 1.0]),
        lambda data: data["DocumentPDF"]["page_links"][0].__setitem__("left", float("nan")),
        lambda data: data["DocumentPDF"]["page_links"][0].__setitem__("top", "bad"),
        lambda data: data["DocumentPDF"]["page_links"][0].__setitem__("zoom", True),
    ]:
        payload = deepcopy(document.parameters)
        mutator(payload)
        invalid_payloads.append(payload)

    for payload in invalid_payloads:
        with pytest.raises((TypeError, ValueError)):
            DocumentPDF.create_from_dict(payload)

    missing_left_payload = deepcopy(document.parameters)
    missing_left_payload["DocumentPDF"]["page_links"][0].pop("left")
    recreated = DocumentPDF.create_from_dict(missing_left_payload)

    assert recreated.page_links() == (
        {"page_number": 1, "rect": [1.0, 2.0, 30.0, 40.0], "target_page_number": 2, "left": 0.0, "top": 6.0, "zoom": 1.25},
    )


@pytest.mark.condition("PDF-DOC-NAMED-DEST-P3")
def test_document_pdf_emits_named_destinations_and_links_round_trips() -> None:
    """PDF-DOC-NAMED-DEST-P3: Named destinations and links render and round-trip."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_page()
    document.add_page()
    document.add_named_destination(r"A\1", 3, left=9.0)
    document.add_named_destination("B (2)", 2, left=5.0, top=70.0, zoom=1.25)
    document.add_named_destination_link(1, [5.0, 6.0, 20.0, 25.0], "B (2)")
    document.add_named_destination_link(1, [30.0, 6.0, 45.0, 25.0], r"A\1")

    payload = document.to_pdf_bytes()
    recreated = DocumentPDF.create_from_dict(document.parameters)
    objects = _pdf_objects(payload)
    page_ids = _page_object_ids(payload)
    annotation_refs = _annotation_refs_by_page(payload)
    annotation_ids = [annotation_id for page_refs in annotation_refs for annotation_id in page_refs]

    assert payload == document.to_pdf_bytes()
    assert [len(page_refs) for page_refs in annotation_refs] == [2]
    assert b"/Names << /Dests << /Names [" in objects[1]
    assert f"(A\\\\1) [{page_ids[2]} 0 R /XYZ 9 null null]".encode("ascii") in objects[1]
    assert f"(B \\(2\\)) [{page_ids[1]} 0 R /XYZ 5 70 1.25]".encode("ascii") in objects[1]
    assert objects[1].index(b"(A\\\\1)") < objects[1].index(b"(B \\(2\\))")
    assert b"/Subtype /Link" in objects[annotation_ids[0]]
    assert b"/Dest (B \\(2\\))" in objects[annotation_ids[0]]
    assert b"/Rect [5 6 20 25]" in objects[annotation_ids[0]]
    assert b"/Dest (A\\\\1)" in objects[annotation_ids[1]]
    assert b"/Rect [30 6 45 25]" in objects[annotation_ids[1]]
    assert sorted(objects) == list(range(1, max(objects) + 1))
    assert document.named_destinations() == (
        {"name": r"A\1", "page_number": 3, "left": 9.0},
        {"name": "B (2)", "page_number": 2, "left": 5.0, "top": 70.0, "zoom": 1.25},
    )
    assert document.named_destination_links() == (
        {"page_number": 1, "rect": [5.0, 6.0, 20.0, 25.0], "destination_name": "B (2)"},
        {"page_number": 1, "rect": [30.0, 6.0, 45.0, 25.0], "destination_name": r"A\1"},
    )
    assert recreated.parameters == document.parameters
    assert recreated.to_pdf_bytes() == payload


@pytest.mark.condition("PDF-DOC-NAMED-DEST-P3")
def test_document_pdf_rejects_invalid_named_destination_metadata() -> None:
    """PDF-DOC-NAMED-DEST-P3: Named destination metadata fails explicitly."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_page()

    for name in [object(), "", "not latin \u0100"]:
        with pytest.raises((TypeError, ValueError)):
            document.add_named_destination(name, 1)  # type: ignore[arg-type]
        assert document.named_destinations() == ()

    with pytest.raises(ValueError, match="Position must correlate"):
        document.add_named_destination("missing", 3)

    invalid_destinations = [
        {"left": True},
        {"left": float("nan")},
        {"top": object()},
        {"top": float("inf")},
        {"zoom": "bad"},
        {"zoom": float("-inf")},
    ]
    for kwargs in invalid_destinations:
        with pytest.raises((TypeError, ValueError), match="named destination"):
            document.add_named_destination("bad", 1, **kwargs)  # type: ignore[arg-type]
        assert document.named_destinations() == ()

    document.add_named_destination("target", 2)
    with pytest.raises(ValueError, match="Position must correlate"):
        document.add_named_destination_link(3, [0.0, 0.0, 1.0, 1.0], "target")
    for name in [object(), "", "not latin \u0100", "missing"]:
        with pytest.raises((TypeError, ValueError)):
            document.add_named_destination_link(1, [0.0, 0.0, 1.0, 1.0], name)  # type: ignore[arg-type]
        assert document.named_destination_links() == ()
    for rect in ["0 0 1 1", [0.0, 0.0, 1.0], [True, 0.0, 1.0, 1.0], [0.0, 0.0, 0.0, 1.0]]:
        with pytest.raises((TypeError, ValueError)):
            document.add_named_destination_link(1, rect, "target")  # type: ignore[arg-type]
        assert document.named_destination_links() == ()

    document.add_named_destination_link(1, [0.0, 0.0, 1.0, 1.0], "target")
    document.clear_named_destination_links()
    assert document.named_destination_links() == ()
    document.add_named_destination_link(1, [0.0, 0.0, 1.0, 1.0], "target")
    document.clear_named_destinations()

    assert document.named_destinations() == ()
    assert document.named_destination_links() == ()
    assert "named_destinations" not in document.parameters["DocumentPDF"]
    assert "named_destination_links" not in document.parameters["DocumentPDF"]
    assert b"/Names" not in document.to_pdf_bytes()
    assert b"/Annots" not in document.to_pdf_bytes()


@pytest.mark.condition("PDF-DOC-NAMED-DEST-P3")
def test_document_pdf_named_destinations_track_page_insertions_and_removals() -> None:
    """PDF-DOC-NAMED-DEST-P3: Named destination targets and links track page mutations."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_page()
    document.add_page()
    document.add_named_destination("front", 1, left=1.0)
    document.add_named_destination("middle", 2, left=2.0)
    document.add_named_destination("tail", 3, left=3.0)
    document.add_named_destination_link(1, [1.0, 1.0, 10.0, 10.0], "tail")
    document.add_named_destination_link(2, [4.0, 4.0, 40.0, 40.0], "tail")
    document.add_named_destination_link(3, [2.0, 2.0, 20.0, 20.0], "front")
    document.add_named_destination_link(3, [3.0, 3.0, 30.0, 30.0], "middle")

    document.add_page(position=2)

    assert document.named_destinations() == (
        {"name": "front", "page_number": 1, "left": 1.0},
        {"name": "middle", "page_number": 3, "left": 2.0},
        {"name": "tail", "page_number": 4, "left": 3.0},
    )
    assert document.named_destination_links() == (
        {"page_number": 1, "rect": [1.0, 1.0, 10.0, 10.0], "destination_name": "tail"},
        {"page_number": 3, "rect": [4.0, 4.0, 40.0, 40.0], "destination_name": "tail"},
        {"page_number": 4, "rect": [2.0, 2.0, 20.0, 20.0], "destination_name": "front"},
        {"page_number": 4, "rect": [3.0, 3.0, 30.0, 30.0], "destination_name": "middle"},
    )

    document.remove_page(3)

    assert document.named_destinations() == (
        {"name": "front", "page_number": 1, "left": 1.0},
        {"name": "tail", "page_number": 3, "left": 3.0},
    )
    assert document.named_destination_links() == (
        {"page_number": 1, "rect": [1.0, 1.0, 10.0, 10.0], "destination_name": "tail"},
        {"page_number": 3, "rect": [2.0, 2.0, 20.0, 20.0], "destination_name": "front"},
    )

    document.remove_page(1)

    assert document.named_destinations() == ({"name": "tail", "page_number": 2, "left": 3.0},)
    assert document.named_destination_links() == ()


@pytest.mark.condition("PDF-DOC-NAMED-DEST-P3")
def test_document_pdf_named_destinations_use_value_equality_for_large_page_removal() -> None:
    """PDF-DOC-NAMED-DEST-P3: Named destination removal uses page-number value equality."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    for _ in range(260):
        document.add_page()
    document.add_named_destination("front", 1)
    document.add_named_destination("tail", int("260"))
    document.add_named_destination_link(1, [1.0, 1.0, 10.0, 10.0], "tail")
    document.add_named_destination_link(int("260"), [2.0, 2.0, 20.0, 20.0], "front")

    document.remove_page(int("260"))

    assert document.pages == 259
    assert document.named_destinations() == ({"name": "front", "page_number": 1, "left": 0.0},)
    assert document.named_destination_links() == ()


@pytest.mark.condition("PDF-DOC-NAMED-DEST-P3")
def test_document_pdf_rejects_invalid_serialized_named_destination_metadata() -> None:
    """PDF-DOC-NAMED-DEST-P3: Serialized named destinations validate before rendering."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_page()
    document.add_named_destination("target", 2, left=5.0, top=6.0, zoom=1.25)
    document.add_named_destination_link(1, [1.0, 2.0, 30.0, 40.0], "target")

    invalid_payloads = []
    for mutator in [
        lambda data: data["DocumentPDF"].__setitem__("named_destinations", "bad"),
        lambda data: data["DocumentPDF"].__setitem__("named_destinations", [object()]),
        lambda data: data["DocumentPDF"]["named_destinations"][0].pop("name"),
        lambda data: data["DocumentPDF"]["named_destinations"][0].pop("page_number"),
        lambda data: data["DocumentPDF"]["named_destinations"][0].__setitem__("name", ""),
        lambda data: data["DocumentPDF"]["named_destinations"][0].__setitem__("page_number", 3),
        lambda data: data["DocumentPDF"]["named_destinations"][0].__setitem__("left", float("nan")),
        lambda data: data["DocumentPDF"]["named_destinations"][0].__setitem__("top", "bad"),
        lambda data: data["DocumentPDF"]["named_destinations"][0].__setitem__("zoom", True),
        lambda data: data["DocumentPDF"].__setitem__("named_destination_links", "bad"),
        lambda data: data["DocumentPDF"].__setitem__("named_destination_links", [object()]),
        lambda data: data["DocumentPDF"]["named_destination_links"][0].pop("page_number"),
        lambda data: data["DocumentPDF"]["named_destination_links"][0].pop("rect"),
        lambda data: data["DocumentPDF"]["named_destination_links"][0].pop("destination_name"),
        lambda data: data["DocumentPDF"]["named_destination_links"][0].__setitem__("page_number", 3),
        lambda data: data["DocumentPDF"]["named_destination_links"][0].__setitem__("rect", [0.0, 0.0, 0.0, 1.0]),
        lambda data: data["DocumentPDF"]["named_destination_links"][0].__setitem__("destination_name", "missing"),
    ]:
        payload = deepcopy(document.parameters)
        mutator(payload)
        invalid_payloads.append(payload)

    for payload in invalid_payloads:
        with pytest.raises((TypeError, ValueError)):
            DocumentPDF.create_from_dict(payload)

    missing_left_payload = deepcopy(document.parameters)
    missing_left_payload["DocumentPDF"]["named_destinations"][0].pop("left")
    recreated = DocumentPDF.create_from_dict(missing_left_payload)

    assert recreated.named_destinations() == ({"name": "target", "page_number": 2, "left": 0.0, "top": 6.0, "zoom": 1.25},)
    assert recreated.named_destination_links() == ({"page_number": 1, "rect": [1.0, 2.0, 30.0, 40.0], "destination_name": "target"},)


@pytest.mark.condition("PDF-DOC-OUTLINE-P3")
def test_document_pdf_emits_flat_outlines_and_round_trips() -> None:
    """PDF-DOC-OUTLINE-P3: Flat PDF outlines render, link, and round-trip."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_page()
    document.add_outline("Cover (A)", 1)
    document.add_outline(r"Details\B", 2, left=12.5, top=70.0, zoom=1.25)
    document.add_outline(title="Appendix", page_number=2, left=20.0)

    payload = document.to_pdf_bytes()
    recreated = DocumentPDF.create_from_dict(document.parameters)
    objects = _pdf_objects(payload)

    outline_root_match = re.search(rb"/Outlines (?P<id>\d+) 0 R", payload)
    assert outline_root_match is not None
    outline_root_id = int(outline_root_match.group("id"))
    outline_root = objects[outline_root_id]
    first_match = re.search(rb"/First (?P<id>\d+) 0 R", outline_root)
    last_match = re.search(rb"/Last (?P<id>\d+) 0 R", outline_root)
    assert first_match is not None
    assert last_match is not None
    first_id = int(first_match.group("id"))
    last_id = int(last_match.group("id"))
    middle_id = first_id + 1

    assert payload == document.to_pdf_bytes()
    assert b"/PageMode /UseOutlines" in payload
    assert b"/Type /Outlines" in outline_root
    assert b"/Count 3" in outline_root
    assert b"/Title (Cover \\(A\\))" in objects[first_id]
    assert b"/Title (Appendix)" in objects[last_id]
    assert b"/Title (Details\\\\B)" in payload
    assert f"/Parent {outline_root_id} 0 R".encode("ascii") in objects[first_id]
    assert b"/Prev" not in objects[first_id]
    assert f"/Next {middle_id} 0 R".encode("ascii") in objects[first_id]
    assert f"/Prev {first_id} 0 R".encode("ascii") in objects[middle_id]
    assert f"/Next {last_id} 0 R".encode("ascii") in objects[middle_id]
    assert f"/Prev {middle_id} 0 R".encode("ascii") in objects[last_id]
    assert b"/Next" not in objects[last_id]
    assert b"/XYZ 0 null null]" in objects[first_id]
    assert b"/XYZ 12.5 70 1.25]" in objects[middle_id]
    assert b"/XYZ 20 null null]" in objects[last_id]
    assert sorted(objects) == list(range(1, max(objects) + 1))
    assert document.outlines() == (
        {"title": "Cover (A)", "page_number": 1, "left": 0.0},
        {"title": r"Details\B", "page_number": 2, "left": 12.5, "top": 70.0, "zoom": 1.25},
        {"title": "Appendix", "page_number": 2, "left": 20.0},
    )
    assert recreated.parameters == document.parameters
    assert recreated.to_pdf_bytes() == payload


@pytest.mark.condition("PDF-DOC-NESTED-OUTLINE-P3")
def test_document_pdf_emits_nested_outlines_and_round_trips() -> None:
    """PDF-DOC-NESTED-OUTLINE-P3: One-level nested PDF outlines render and round-trip."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_page()
    document.add_page()
    document.add_outline("Chapter 1", 1)
    document.add_outline("Section 1.1", 2, left=10.0, parent="Chapter 1")
    document.add_outline("Section 1.2", 3, left=20.0, top=70.0, zoom=1.25, parent="Chapter 1")
    document.add_outline("Section 1.3", 3, left=25.0, parent="Chapter 1")
    document.add_outline("Chapter 2", 3, left=30.0)

    payload = document.to_pdf_bytes()
    recreated = DocumentPDF.create_from_dict(document.parameters)
    objects = _pdf_objects(payload)
    outline_root_id = int(re.search(rb"/Outlines (?P<id>\d+) 0 R", payload).group("id"))  # type: ignore[union-attr]
    outline_root = objects[outline_root_id]
    first_id = int(re.search(rb"/First (?P<id>\d+) 0 R", outline_root).group("id"))  # type: ignore[union-attr]
    child_1_id = first_id + 1
    child_2_id = first_id + 2
    child_3_id = first_id + 3
    second_top_id = first_id + 4

    assert payload == document.to_pdf_bytes()
    assert b"/Count 5" in outline_root
    assert f"/First {first_id} 0 R".encode("ascii") in outline_root
    assert f"/Last {second_top_id} 0 R".encode("ascii") in outline_root
    assert f"/Parent {outline_root_id} 0 R".encode("ascii") in objects[first_id]
    assert f"/Next {second_top_id} 0 R".encode("ascii") in objects[first_id]
    assert f"/First {child_1_id} 0 R".encode("ascii") in objects[first_id]
    assert f"/Last {child_3_id} 0 R".encode("ascii") in objects[first_id]
    assert b"/Count 3" in objects[first_id]
    assert f"/Parent {first_id} 0 R".encode("ascii") in objects[child_1_id]
    assert b"/Prev" not in objects[child_1_id]
    assert f"/Next {child_2_id} 0 R".encode("ascii") in objects[child_1_id]
    assert f"/Parent {first_id} 0 R".encode("ascii") in objects[child_2_id]
    assert f"/Prev {child_1_id} 0 R".encode("ascii") in objects[child_2_id]
    assert f"/Next {child_3_id} 0 R".encode("ascii") in objects[child_2_id]
    assert f"/Parent {first_id} 0 R".encode("ascii") in objects[child_3_id]
    assert f"/Prev {child_2_id} 0 R".encode("ascii") in objects[child_3_id]
    assert b"/Next" not in objects[child_3_id]
    assert f"/Prev {first_id} 0 R".encode("ascii") in objects[second_top_id]
    assert b"/Next" not in objects[second_top_id]
    assert b"/Title (Section 1.2)" in objects[child_2_id]
    assert b"/XYZ 20 70 1.25]" in objects[child_2_id]
    assert document.outlines() == (
        {"title": "Chapter 1", "page_number": 1, "left": 0.0},
        {"title": "Section 1.1", "page_number": 2, "left": 10.0, "parent": "Chapter 1"},
        {"title": "Section 1.2", "page_number": 3, "left": 20.0, "top": 70.0, "zoom": 1.25, "parent": "Chapter 1"},
        {"title": "Section 1.3", "page_number": 3, "left": 25.0, "parent": "Chapter 1"},
        {"title": "Chapter 2", "page_number": 3, "left": 30.0},
    )
    assert recreated.parameters == document.parameters
    assert recreated.to_pdf_bytes() == payload


@pytest.mark.condition("PDF-DOC-DEEP-OUTLINE-P3")
def test_document_pdf_emits_deep_outline_trees_and_round_trips() -> None:
    """PDF-DOC-DEEP-OUTLINE-P3: Deep PDF outline trees render recursively."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_page()
    document.add_page()
    document.add_outline("Root", 1)
    document.add_outline("Section", 2, parent="Root")
    document.add_outline("Topic", 3, parent="Section", expanded=False)
    document.add_outline("Leaf", 3, parent="Topic")
    document.add_outline("Sibling", 2, parent="Root")
    document.add_outline("Appendix", 3)

    payload = document.to_pdf_bytes()
    recreated = DocumentPDF.create_from_dict(document.parameters)
    objects = _pdf_objects(payload)
    outline_root_id = int(re.search(rb"/Outlines (?P<id>\d+) 0 R", payload).group("id"))  # type: ignore[union-attr]
    outline_root = objects[outline_root_id]
    root_id = int(re.search(rb"/First (?P<id>\d+) 0 R", outline_root).group("id"))  # type: ignore[union-attr]
    section_id = root_id + 1
    topic_id = root_id + 2
    leaf_id = root_id + 3
    sibling_id = root_id + 4
    appendix_id = root_id + 5

    assert payload == document.to_pdf_bytes()
    assert f"/Last {appendix_id} 0 R".encode("ascii") in outline_root
    assert b"/Count 6" in outline_root
    assert f"/Parent {outline_root_id} 0 R".encode("ascii") in objects[root_id]
    assert f"/Next {appendix_id} 0 R".encode("ascii") in objects[root_id]
    assert f"/First {section_id} 0 R".encode("ascii") in objects[root_id]
    assert f"/Last {sibling_id} 0 R".encode("ascii") in objects[root_id]
    assert b"/Count 4" in objects[root_id]
    assert f"/Parent {root_id} 0 R".encode("ascii") in objects[section_id]
    assert f"/Next {sibling_id} 0 R".encode("ascii") in objects[section_id]
    assert f"/First {topic_id} 0 R".encode("ascii") in objects[section_id]
    assert f"/Last {topic_id} 0 R".encode("ascii") in objects[section_id]
    assert b"/Count 2" in objects[section_id]
    assert f"/Parent {section_id} 0 R".encode("ascii") in objects[topic_id]
    assert f"/First {leaf_id} 0 R".encode("ascii") in objects[topic_id]
    assert f"/Last {leaf_id} 0 R".encode("ascii") in objects[topic_id]
    assert b"/Count -1" in objects[topic_id]
    assert f"/Parent {topic_id} 0 R".encode("ascii") in objects[leaf_id]
    assert b"/First" not in objects[leaf_id]
    assert f"/Parent {root_id} 0 R".encode("ascii") in objects[sibling_id]
    assert f"/Prev {section_id} 0 R".encode("ascii") in objects[sibling_id]
    assert b"/Next" not in objects[sibling_id]
    assert f"/Prev {root_id} 0 R".encode("ascii") in objects[appendix_id]
    assert b"/Next" not in objects[appendix_id]
    assert document.outlines() == (
        {"title": "Root", "page_number": 1, "left": 0.0},
        {"title": "Section", "page_number": 2, "left": 0.0, "parent": "Root"},
        {"title": "Topic", "page_number": 3, "left": 0.0, "parent": "Section", "expanded": False},
        {"title": "Leaf", "page_number": 3, "left": 0.0, "parent": "Topic"},
        {"title": "Sibling", "page_number": 2, "left": 0.0, "parent": "Root"},
        {"title": "Appendix", "page_number": 3, "left": 0.0},
    )
    assert recreated.parameters == document.parameters
    assert recreated.to_pdf_bytes() == payload


@pytest.mark.condition("PDF-DOC-OUTLINE-STATE-P3")
def test_document_pdf_emits_collapsed_outline_state_and_round_trips() -> None:
    """PDF-DOC-OUTLINE-STATE-P3: Collapsed outline parents emit negative child counts."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_page()
    document.add_outline("Collapsed", 1, expanded=False)
    document.add_outline("Child A", 2, parent="Collapsed")
    document.add_outline("Child B", 2, parent="Collapsed")
    document.add_outline("Expanded", 2)
    document.add_outline("Child C", 2, parent="Expanded")

    payload = document.to_pdf_bytes()
    recreated = DocumentPDF.create_from_dict(document.parameters)
    objects = _pdf_objects(payload)
    outline_root_id = int(re.search(rb"/Outlines (?P<id>\d+) 0 R", payload).group("id"))  # type: ignore[union-attr]
    first_id = int(re.search(rb"/First (?P<id>\d+) 0 R", objects[outline_root_id]).group("id"))  # type: ignore[union-attr]
    expanded_id = first_id + 3

    assert b"/Title (Collapsed)" in objects[first_id]
    assert b"/Count -2" in objects[first_id]
    assert b"/Title (Expanded)" in objects[expanded_id]
    assert b"/Count 1" in objects[expanded_id]
    assert document.outlines() == (
        {"title": "Collapsed", "page_number": 1, "left": 0.0, "expanded": False},
        {"title": "Child A", "page_number": 2, "left": 0.0, "parent": "Collapsed"},
        {"title": "Child B", "page_number": 2, "left": 0.0, "parent": "Collapsed"},
        {"title": "Expanded", "page_number": 2, "left": 0.0},
        {"title": "Child C", "page_number": 2, "left": 0.0, "parent": "Expanded"},
    )
    assert recreated.parameters == document.parameters
    assert recreated.to_pdf_bytes() == payload


@pytest.mark.condition("PDF-DOC-OUTLINE-P3")
def test_document_pdf_rejects_invalid_outline_metadata() -> None:
    """PDF-DOC-OUTLINE-P3: Outline metadata fails at explicit boundaries."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()

    for title in [object(), "", "not latin \u0100"]:
        with pytest.raises((TypeError, ValueError)):
            document.add_outline(title, 1)  # type: ignore[arg-type]
        assert document.outlines() == ()

    with pytest.raises(ValueError, match="Position must correlate"):
        document.add_outline("missing", 2)
    for expanded in [0, 1, "true", object()]:
        with pytest.raises(TypeError):
            document.add_outline("bad expanded", 1, expanded=expanded)  # type: ignore[arg-type]
        assert document.outlines() == ()

    with pytest.raises(ValueError, match="outline parent"):
        document.add_outline("orphan", 1, parent="missing")
    document.add_outline("parent", 1)
    document.add_outline("value child", 1, parent="".join(["par", "ent"]))
    with pytest.raises(ValueError, match="conflicts"):
        document.add_outline("parent", 1)
    document.add_outline("duplicate", 1)
    document.add_outline("duplicate", 1)
    with pytest.raises(ValueError, match="outline parent"):
        document.add_outline("ambiguous", 1, parent="duplicate")
    document.clear_outlines()
    document.add_outline("root", 1)
    document.add_outline("branch", 1, parent="root")
    document.add_outline("branch", 1)
    with pytest.raises(ValueError, match="outline parent"):
        document.add_outline("leaf", 1, parent="branch")
    document.clear_outlines()
    document.add_outline("root", 1)
    document.add_outline("branch", 1, parent="root")
    document.add_outline("leaf", 1, parent="branch")
    with pytest.raises(ValueError, match="conflicts"):
        document.add_outline("branch", 1)
    with pytest.raises((TypeError, ValueError)):
        document.add_outline("bad parent", 1, parent=object())  # type: ignore[arg-type]
    document.clear_outlines()

    invalid_destinations = [
        {"left": True},
        {"left": float("nan")},
        {"top": object()},
        {"top": float("inf")},
        {"zoom": "bad"},
        {"zoom": float("-inf")},
    ]
    for kwargs in invalid_destinations:
        with pytest.raises((TypeError, ValueError), match="outline"):
            document.add_outline("bad destination", 1, **kwargs)  # type: ignore[arg-type]
        assert document.outlines() == ()

    document.add_outline("valid", 1)
    document.clear_outlines()

    assert document.outlines() == ()
    assert "outlines" not in document.parameters["DocumentPDF"]
    assert b"/Outlines" not in document.to_pdf_bytes()


@pytest.mark.condition("PDF-DOC-OUTLINE-P3")
def test_document_pdf_outline_metadata_tracks_page_insertions_and_removals() -> None:
    """PDF-DOC-OUTLINE-P3: Outlines stay aligned with page mutations."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_page()
    document.add_page()
    document.add_outline("front", 1)
    document.add_outline("middle", 2, expanded=False)
    document.add_outline("tail", 3)
    document.add_outline("front child", 2, parent="front")
    document.add_outline("middle child", 1, parent="middle")
    document.add_outline("tail child", 3, parent="tail")

    document.add_page(position=2)

    assert document.outlines() == (
        {"title": "front", "page_number": 1, "left": 0.0},
        {"title": "middle", "page_number": 3, "left": 0.0, "expanded": False},
        {"title": "tail", "page_number": 4, "left": 0.0},
        {"title": "front child", "page_number": 3, "left": 0.0, "parent": "front"},
        {"title": "middle child", "page_number": 1, "left": 0.0, "parent": "middle"},
        {"title": "tail child", "page_number": 4, "left": 0.0, "parent": "tail"},
    )

    document.remove_page(3)

    assert document.outlines() == (
        {"title": "front", "page_number": 1, "left": 0.0},
        {"title": "tail", "page_number": 3, "left": 0.0},
        {"title": "tail child", "page_number": 3, "left": 0.0, "parent": "tail"},
    )

    document.remove_page(1)

    assert document.outlines() == (
        {"title": "tail", "page_number": 2, "left": 0.0},
        {"title": "tail child", "page_number": 2, "left": 0.0, "parent": "tail"},
    )


@pytest.mark.condition("PDF-DOC-DEEP-OUTLINE-P3")
def test_document_pdf_deep_outline_page_removal_prunes_descendants() -> None:
    """PDF-DOC-DEEP-OUTLINE-P3: Removing a nested parent prunes its descendants."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_page()
    document.add_page()
    document.add_outline("root", 1)
    document.add_outline("branch", 2, parent="root")
    document.add_outline("leaf", 3, parent="branch")
    document.add_outline("sibling", 3, parent="root")

    document.remove_page(2)

    assert document.outlines() == (
        {"title": "root", "page_number": 1, "left": 0.0},
        {"title": "sibling", "page_number": 2, "left": 0.0, "parent": "root"},
    )


@pytest.mark.condition("PDF-DOC-OUTLINE-P3")
def test_document_pdf_outline_metadata_uses_value_equality_for_large_page_removal() -> None:
    """PDF-DOC-OUTLINE-P3: Outline removal uses page-number value equality."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    for _ in range(260):
        document.add_page()
    document.add_outline("front", 1)
    document.add_outline("tail", int("260"))

    document.remove_page(int("260"))

    assert document.pages == 259
    assert document.outlines() == ({"title": "front", "page_number": 1, "left": 0.0},)


@pytest.mark.condition("PDF-DOC-OUTLINE-P3")
def test_document_pdf_outlines_render_large_flat_lists_without_terminal_next_link() -> None:
    """PDF-DOC-OUTLINE-P3: Large flat outline lists terminate the Next chain."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    for index in range(260):
        document.add_outline(f"bookmark {index}", 1)

    payload = document.to_pdf_bytes()

    assert b"/Count 260" in payload
    assert b"/Title (bookmark 259)" in payload
    assert b"/Title (bookmark 260)" not in payload


@pytest.mark.condition("PDF-DOC-OUTLINE-P3")
def test_document_pdf_rejects_invalid_serialized_outline_metadata() -> None:
    """PDF-DOC-OUTLINE-P3: Serialized outlines validate before rendering."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_outline("valid", 1, left=1.0, top=2.0, zoom=1.0)

    invalid_payloads = []
    for mutator in [
        lambda data: data["DocumentPDF"].__setitem__("outlines", "bad"),
        lambda data: data["DocumentPDF"].__setitem__("outlines", [object()]),
        lambda data: data["DocumentPDF"]["outlines"][0].pop("title"),
        lambda data: data["DocumentPDF"]["outlines"][0].pop("page_number"),
        lambda data: data["DocumentPDF"]["outlines"][0].__setitem__("title", ""),
        lambda data: data["DocumentPDF"]["outlines"][0].__setitem__("page_number", 2),
        lambda data: data["DocumentPDF"]["outlines"][0].__setitem__("left", float("nan")),
        lambda data: data["DocumentPDF"]["outlines"][0].__setitem__("top", "bad"),
        lambda data: data["DocumentPDF"]["outlines"][0].__setitem__("zoom", True),
        lambda data: data["DocumentPDF"]["outlines"][0].__setitem__("parent", "missing"),
        lambda data: data["DocumentPDF"]["outlines"][0].__setitem__("parent", object()),
        lambda data: data["DocumentPDF"]["outlines"][0].__setitem__("expanded", 1),
        lambda data: data["DocumentPDF"]["outlines"].extend(
            [
                {"title": "child", "page_number": 1, "parent": "valid"},
                {"title": "valid", "page_number": 1},
            ],
        ),
    ]:
        payload = deepcopy(document.parameters)
        mutator(payload)
        invalid_payloads.append(payload)

    for payload in invalid_payloads:
        with pytest.raises((TypeError, ValueError)):
            DocumentPDF.create_from_dict(payload)

    non_sequence_payload = deepcopy(document.parameters)
    non_sequence_payload["DocumentPDF"]["outlines"] = object()
    with pytest.raises(TypeError, match="DocumentPDF outlines must be a sequence"):
        DocumentPDF.create_from_dict(non_sequence_payload)

    missing_left_payload = deepcopy(document.parameters)
    missing_left_payload["DocumentPDF"]["outlines"][0].pop("left")
    missing_left_payload["DocumentPDF"]["outlines"][0]["expanded"] = False
    recreated = DocumentPDF.create_from_dict(missing_left_payload)

    assert recreated.outlines() == ({"title": "valid", "page_number": 1, "left": 0.0, "top": 2.0, "zoom": 1.0, "expanded": False},)


@pytest.mark.condition("PDF-DOC-LINK-P3")
def test_document_pdf_emits_uri_link_annotations_and_round_trips() -> None:
    """PDF-DOC-LINK-P3: URI link annotations render and round-trip."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_page()
    document.add_uri_link(1, [5.0, 6.0, 20.0, 25.0], "https://example.com/a?x=(1)")
    document.add_uri_link(1, [30.0, 6.0, 45.0, 25.0], "https://example.com/b")
    document.add_uri_link(2, [0.0, 0.0, 100.0, 80.0], r"mailto:test\user@example.com")

    payload = document.to_pdf_bytes()
    recreated = DocumentPDF.create_from_dict(document.parameters)
    objects = _pdf_objects(payload)
    annotation_refs = _annotation_refs_by_page(payload)
    annotation_ids = [annotation_id for page_refs in annotation_refs for annotation_id in page_refs]

    assert payload == document.to_pdf_bytes()
    assert [len(page_refs) for page_refs in annotation_refs] == [2, 1]
    assert b"/Subtype /Link" in objects[annotation_ids[0]]
    assert b"/Rect [5 6 20 25]" in objects[annotation_ids[0]]
    assert b"/Border [0 0 0]" in objects[annotation_ids[0]]
    assert b"/A << /S /URI /URI (https://example.com/a?x=\\(1\\)) >>" in objects[annotation_ids[0]]
    assert b"/Rect [30 6 45 25]" in objects[annotation_ids[1]]
    assert b"/URI (https://example.com/b)" in objects[annotation_ids[1]]
    assert b"/Rect [0 0 100 80]" in objects[annotation_ids[2]]
    assert b"/URI (mailto:test\\\\user@example.com)" in objects[annotation_ids[2]]
    assert sorted(objects) == list(range(1, max(objects) + 1))
    assert document.uri_links() == (
        {"page_number": 1, "rect": [5.0, 6.0, 20.0, 25.0], "uri": "https://example.com/a?x=(1)"},
        {"page_number": 1, "rect": [30.0, 6.0, 45.0, 25.0], "uri": "https://example.com/b"},
        {"page_number": 2, "rect": [0.0, 0.0, 100.0, 80.0], "uri": r"mailto:test\user@example.com"},
    )
    assert recreated.parameters == document.parameters
    assert recreated.to_pdf_bytes() == payload


@pytest.mark.condition("PDF-DOC-LINK-P3")
def test_document_pdf_rejects_invalid_uri_link_metadata() -> None:
    """PDF-DOC-LINK-P3: URI link metadata fails at explicit boundaries."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()

    with pytest.raises(ValueError, match="Position must correlate"):
        document.add_uri_link(2, [0.0, 0.0, 1.0, 1.0], "https://example.com")

    for uri in [object(), "", "not latin \u0100"]:
        with pytest.raises((TypeError, ValueError)):
            document.add_uri_link(1, [0.0, 0.0, 1.0, 1.0], uri)  # type: ignore[arg-type]
        assert document.uri_links() == ()

    invalid_rectangles = [
        "0 0 1 1",
        [0.0, 0.0, 1.0],
        [True, 0.0, 1.0, 1.0],
        [0.0, 0.0, float("nan"), 1.0],
        [0.0, 0.0, 0.0, 1.0],
        [-1.0, 0.0, 1.0, 1.0],
        [0.0, 0.0, 101.0, 1.0],
    ]
    for rect in invalid_rectangles:
        with pytest.raises((TypeError, ValueError)):
            document.add_uri_link(1, rect, "https://example.com")  # type: ignore[arg-type]
        assert document.uri_links() == ()

    document.add_uri_link(1, [0.0, 0.0, 1.0, 1.0], "https://example.com")
    document.clear_uri_links()

    assert document.uri_links() == ()
    assert "uri_links" not in document.parameters["DocumentPDF"]
    assert b"/Annots" not in document.to_pdf_bytes()


@pytest.mark.condition("PDF-DOC-LINK-P3")
def test_document_pdf_uri_links_track_page_insertions_and_removals() -> None:
    """PDF-DOC-LINK-P3: URI link annotations stay aligned with page mutations."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_page()
    document.add_page()
    document.add_uri_link(1, [1.0, 1.0, 10.0, 10.0], "https://front.example")
    document.add_uri_link(2, [2.0, 2.0, 20.0, 20.0], "https://middle.example")
    document.add_uri_link(3, [3.0, 3.0, 30.0, 30.0], "https://tail.example")

    document.add_page(position=2)

    assert document.uri_links() == (
        {"page_number": 1, "rect": [1.0, 1.0, 10.0, 10.0], "uri": "https://front.example"},
        {"page_number": 3, "rect": [2.0, 2.0, 20.0, 20.0], "uri": "https://middle.example"},
        {"page_number": 4, "rect": [3.0, 3.0, 30.0, 30.0], "uri": "https://tail.example"},
    )

    document.remove_page(3)

    assert document.uri_links() == (
        {"page_number": 1, "rect": [1.0, 1.0, 10.0, 10.0], "uri": "https://front.example"},
        {"page_number": 3, "rect": [3.0, 3.0, 30.0, 30.0], "uri": "https://tail.example"},
    )

    document.remove_page(1)

    assert document.uri_links() == ({"page_number": 2, "rect": [3.0, 3.0, 30.0, 30.0], "uri": "https://tail.example"},)


@pytest.mark.condition("PDF-DOC-LINK-P3")
def test_document_pdf_uri_links_use_value_equality_for_large_page_removal() -> None:
    """PDF-DOC-LINK-P3: URI link removal uses page-number value equality."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    for _ in range(260):
        document.add_page()
    document.add_uri_link(1, [1.0, 1.0, 10.0, 10.0], "https://front.example")
    document.add_uri_link(int("260"), [2.0, 2.0, 20.0, 20.0], "https://tail.example")

    document.remove_page(int("260"))

    assert document.pages == 259
    assert document.uri_links() == ({"page_number": 1, "rect": [1.0, 1.0, 10.0, 10.0], "uri": "https://front.example"},)


@pytest.mark.condition("PDF-DOC-LINK-P3")
def test_document_pdf_rejects_invalid_serialized_uri_link_metadata() -> None:
    """PDF-DOC-LINK-P3: Serialized URI links validate before rendering."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.add_uri_link(1, [1.0, 2.0, 30.0, 40.0], "https://example.com")

    invalid_payloads = []
    for mutator in [
        lambda data: data["DocumentPDF"].__setitem__("uri_links", "bad"),
        lambda data: data["DocumentPDF"].__setitem__("uri_links", [object()]),
        lambda data: data["DocumentPDF"]["uri_links"][0].pop("page_number"),
        lambda data: data["DocumentPDF"]["uri_links"][0].pop("rect"),
        lambda data: data["DocumentPDF"]["uri_links"][0].pop("uri"),
        lambda data: data["DocumentPDF"]["uri_links"][0].__setitem__("page_number", 2),
        lambda data: data["DocumentPDF"]["uri_links"][0].__setitem__("rect", [0.0, 0.0, 0.0, 1.0]),
        lambda data: data["DocumentPDF"]["uri_links"][0].__setitem__("uri", ""),
    ]:
        payload = deepcopy(document.parameters)
        mutator(payload)
        invalid_payloads.append(payload)

    for payload in invalid_payloads:
        with pytest.raises((TypeError, ValueError)):
            DocumentPDF.create_from_dict(payload)
