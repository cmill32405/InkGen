"""Tests for InkGen's grammar cue and construct truth emit."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from InkGen.boundary import Canvas
from InkGen.drawing_components import DrawingComponentGroup, RectangleDrawing, TextDrawing
from InkGen.grammar_truth import (
    GrammarTruthAnnotation,
    GrammarTruthRecord,
    annotate_grammar_truth,
    grammar_truth_json,
    records_for_annotated_target,
    restore_grammar_truth_annotations,
    sort_grammar_truth_records,
)
from InkGen.pdf_generator import ComponentGroupPDF, DocumentPDF, RectanglePDF
from InkGen.style import DrawingStyle, Font, TextStyle


def _drawing_style() -> DrawingStyle:
    return DrawingStyle(f"grammar_line_{uuid4().hex}", stroke="#000000", stroke_width=0.2, fill="none")


def _text_style() -> TextStyle:
    return TextStyle(f"grammar_text_{uuid4().hex}", Font(size=8.0))


def _document_with_group(group: ComponentGroupPDF) -> DocumentPDF:
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.page(1).layer("base").add_component_group(group)
    return document


class _TargetWithBBox:
    def __init__(self, bbox: object) -> None:
        self.bbox = bbox


@pytest.mark.condition("PDF-P3")
def test_document_pdf_emits_grammar_truth_in_pdf_coordinates() -> None:
    """PDF-P3: Grammar-truth bboxes emit in rendered PDF bottom-left coordinates."""
    group = ComponentGroupPDF("bold-heading")
    group.add_component(RectanglePDF((10.0, 5.0), 30.0, 20.0, 0.0, _drawing_style()))
    annotate_grammar_truth(group, "B1", "cue", value="heading_level", instance_id="heading")
    document = _document_with_group(group)

    assert document.grammar_truth() == [
        {
            "condition_id": "B1",
            "kind": "cue",
            "page": 1,
            "bbox": [10.0, 55.0, 40.0, 75.0],
            "value": "heading_level",
            "links_to": None,
            "source_channel": "body",
            "instance_id": "heading",
            "coordinate_frame": "pdf_points_bottom_left",
        }
    ]


@pytest.mark.condition("PDF-P3")
def test_document_pdf_emits_assessment_and_link_truth() -> None:
    """PDF-P3: Grammar truth supports doc-level assessments and link records."""
    group = ComponentGroupPDF("toc-link")
    link_box = RectanglePDF((10.0, 10.0), 30.0, 10.0, 0.0, _drawing_style())
    group.add_component(link_box)
    annotate_grammar_truth(link_box, "LINK", "link", value="toc_entry", links_to="section-1")
    document = _document_with_group(group)
    annotate_grammar_truth(
        document,
        "OOD-SAFE",
        "assessment",
        value={"familiar": True, "abstain": False},
        source_channel="metadata",
        instance_id="ood",
    )

    truth = document.grammar_truth()

    assessment = truth[0]
    link = truth[1]
    assert assessment["kind"] == "assessment"
    assert assessment["page"] == 0
    assert assessment["bbox"] is None
    assert assessment["value"] == {"familiar": True, "abstain": False}
    assert link["condition_id"] == "LINK"
    assert link["kind"] == "link"
    assert link["links_to"] == "section-1"
    assert link["bbox"] == [10.0, 60.0, 40.0, 70.0]


@pytest.mark.condition("PDF-P3")
def test_grammar_truth_round_trips_with_document_pdf_parameters() -> None:
    """PDF-P3: Grammar annotations round-trip with PDF document parameters."""
    style = _drawing_style()
    group = ComponentGroupPDF("dimension")
    dimension_box = RectanglePDF((20.0, 30.0), 40.0, 10.0, 0.0, style)
    group.add_component(dimension_box)
    annotate_grammar_truth(group, "K17", "construct", value="dimension_cluster")
    annotate_grammar_truth(dimension_box, "G10", "cue", value="wireframe")
    document = _document_with_group(group)
    annotate_grammar_truth(document, "D5", "assessment", value="portrait")

    recreated = DocumentPDF.create_from_dict(document.parameters, {style.name: style})

    assert recreated.parameters == document.parameters
    assert recreated.grammar_truth() == document.grammar_truth()
    assert recreated.grammar_truth_json() == document.grammar_truth_json()
    assert recreated.to_pdf_bytes() == document.to_pdf_bytes()


@pytest.mark.condition("PDF-P3")
def test_grammar_truth_annotations_do_not_change_pdf_bytes() -> None:
    """PDF-P3: Adding grammar truth does not alter rendered PDF bytes."""
    group = ComponentGroupPDF("stable")
    group.add_component(RectanglePDF((10.0, 10.0), 20.0, 5.0, 0.0, _drawing_style()))
    document = _document_with_group(group)

    before = document.to_pdf_bytes()
    annotate_grammar_truth(group, "E3", "cue", value="section_divider")
    after = document.to_pdf_bytes()

    assert after == before


@pytest.mark.condition("PDF-P3")
def test_unannotated_pdf_parameters_do_not_gain_grammar_truth_keys() -> None:
    """PDF-P3: Unannotated PDF parameter serialization stays legacy-compatible."""
    group = ComponentGroupPDF("legacy_shape")
    group.add_component(RectanglePDF((10.0, 10.0), 20.0, 5.0, 0.0, _drawing_style()))
    document = _document_with_group(group)

    group_payload = group.parameters["ComponentGroupPDF"]
    document_payload = document.parameters["DocumentPDF"]

    assert "grammar_truth" not in group_payload
    assert "component_grammar_truth" not in group_payload
    assert "grammar_truth" not in document_payload


@pytest.mark.condition("PDF-P3")
def test_body_annotation_without_bbox_emits_none_bbox() -> None:
    """PDF-P3: Body grammar truth without usable geometry keeps a null bbox."""

    class TargetWithoutBBox:
        pass

    target = TargetWithoutBBox()
    annotate_grammar_truth(target, "B-NONE", "cue", value="unlocated")

    records = records_for_annotated_target(target, page=3, canvas_height=80.0)

    assert len(records) == 1
    assert records[0].page == 3
    assert records[0].bbox is None


@pytest.mark.condition("PDF-P3")
def test_body_source_channel_uses_value_equality_not_identity() -> None:
    """PDF-P3: Dynamically built body source strings still emit body records."""
    group = ComponentGroupPDF("dynamic-body")
    group.add_component(RectanglePDF((10.0, 5.0), 30.0, 20.0, 0.0, _drawing_style()))
    dynamic_body = b"body".decode()
    body_literal = "body"
    assert dynamic_body == "body"
    assert dynamic_body is not body_literal

    annotate_grammar_truth(group, "B-DYNAMIC", "cue", source_channel=dynamic_body)
    records = records_for_annotated_target(group, page=2, canvas_height=80.0)

    assert records[0].page == 2
    assert records[0].bbox == [10.0, 55.0, 40.0, 75.0]


@pytest.mark.condition("PDF-P3")
def test_non_body_source_channels_suppress_page_and_bbox_regardless_of_sort_order() -> None:
    """PDF-P3: Non-body channels on geometric targets never emit body geometry."""
    group_before_body = ComponentGroupPDF("before-body")
    group_before_body.add_component(RectanglePDF((10.0, 5.0), 30.0, 20.0, 0.0, _drawing_style()))
    annotate_grammar_truth(group_before_body, "B-LESS", "assessment", source_channel="aa")

    group_after_body = ComponentGroupPDF("after-body")
    group_after_body.add_component(RectanglePDF((10.0, 5.0), 30.0, 20.0, 0.0, _drawing_style()))
    annotate_grammar_truth(group_after_body, "B-GREATER", "assessment", source_channel="metadata")

    for group in (group_before_body, group_after_body):
        records = records_for_annotated_target(group, page=3, canvas_height=80.0)
        assert records[0].page == 0
        assert records[0].bbox is None


@pytest.mark.condition("PDF-P3")
def test_neutral_drawing_annotations_materialize_to_pdf_grammar_truth() -> None:
    """PDF-P3: Renderer-neutral grammar labels propagate to concrete PDF components."""
    recipe = DrawingComponentGroup("title-band")
    box = RectangleDrawing((5.0, 5.0), 50.0, 10.0, 0.0, _drawing_style())
    title = TextDrawing("SECTION 1", (7.0, 12.0), _text_style())
    recipe.add_component(box)
    recipe.add_component(title)
    annotate_grammar_truth(recipe, "K1", "construct", value="title_band")
    annotate_grammar_truth(box, "E2", "cue", value="shaded_band")
    annotate_grammar_truth(title, "B2", "cue", value="all_caps")
    document = _document_with_group(recipe.to_group("pdf"))

    truth = document.grammar_truth()
    records = {str(record["condition_id"]): record for record in truth}

    assert sorted(records) == ["B2", "E2", "K1"]
    assert records["B2"]["bbox"] is not None
    assert records["E2"]["bbox"] == [5.0, 65.0, 55.0, 75.0]
    assert records["K1"]["bbox"] is not None


@pytest.mark.condition("PDF-P3")
def test_grammar_truth_rejects_empty_condition_and_invalid_kind() -> None:
    """PDF-P3: Grammar labels fail loudly for invalid schema fields."""
    group = ComponentGroupPDF("bad-label")

    with pytest.raises(ValueError, match="condition_id must be a non-empty string"):
        annotate_grammar_truth(group, "", "cue")
    with pytest.raises(ValueError, match="kind must be one of"):
        annotate_grammar_truth(group, "B1", "derived")


@pytest.mark.condition("PDF-P3")
def test_grammar_truth_rejects_invalid_optional_fields() -> None:
    """PDF-P3: Grammar truth rejects invalid optional reference fields."""
    with pytest.raises(ValueError, match="source_channel must be a non-empty string"):
        GrammarTruthAnnotation("B1", "cue", source_channel="")
    with pytest.raises(TypeError, match="links_to must be a string or None"):
        GrammarTruthAnnotation("B1", "link", links_to=object())
    with pytest.raises(TypeError, match="instance_id must be a string or None"):
        GrammarTruthAnnotation("B1", "cue", instance_id=object())


@pytest.mark.condition("TRUTH-ANNOTATION-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("payload", "exception_type", "message"),
    [
        (object(), TypeError, "grammar truth annotation data must be a mapping"),
        ({"kind": "cue"}, ValueError, "condition_id is required"),
        ({"condition_id": "B1"}, ValueError, "kind is required"),
        ({"condition_id": object(), "kind": "cue"}, TypeError, "condition_id must be a string"),
        ({"condition_id": "B1", "kind": object()}, TypeError, "kind must be a string"),
        ({"condition_id": "B1", "kind": "cue", "links_to": object()}, TypeError, "links_to must be a string or None"),
        (
            {"condition_id": "B1", "kind": "cue", "source_channel": object()},
            TypeError,
            "source_channel must be a string",
        ),
        (
            {"condition_id": "B1", "kind": "cue", "instance_id": object()},
            TypeError,
            "instance_id must be a string or None",
        ),
    ],
)
def test_grammar_truth_from_dict_rejects_malformed_serialized_fields(
    payload: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """TRUTH-ANNOTATION-PAYLOAD-P2: Serialized grammar truth cannot stringify malformed fields."""
    with pytest.raises(exception_type, match=message):
        GrammarTruthAnnotation.from_dict(payload)


@pytest.mark.condition("TRUTH-ANNOTATION-PAYLOAD-P2")
def test_restore_grammar_truth_rejects_malformed_serialized_annotations() -> None:
    """TRUTH-ANNOTATION-PAYLOAD-P2: Restore path uses the same annotation payload boundary."""
    target = _TargetWithBBox(None)

    with pytest.raises(TypeError, match="condition_id must be a string"):
        restore_grammar_truth_annotations(target, [{"condition_id": object(), "kind": "cue"}])


@pytest.mark.condition("PDF-P3")
def test_grammar_truth_public_helpers_keep_keyword_only_contracts() -> None:
    """PDF-P3: Grammar helpers reject positional values for keyword-only options."""
    group = ComponentGroupPDF("keyword-only")
    annotation = GrammarTruthAnnotation("B1", "cue")

    with pytest.raises(TypeError):
        annotate_grammar_truth(group, "B1", "cue", "positional-value")
    with pytest.raises(TypeError):
        records_for_annotated_target(group, 1, 80.0)
    with pytest.raises(TypeError):
        GrammarTruthRecord.from_annotation(annotation, 1, None)


@pytest.mark.condition("PDF-P3")
def test_grammar_truth_records_are_immutable() -> None:
    """PDF-P3: Grammar annotation and emitted record dataclasses are frozen."""
    annotation = GrammarTruthAnnotation("B1", "cue")
    record = GrammarTruthRecord.from_annotation(annotation, page=1, bbox=None)

    with pytest.raises(FrozenInstanceError):
        annotation.kind = "construct"
    with pytest.raises(FrozenInstanceError):
        record.page = 2


@pytest.mark.condition("PDF-P3")
def test_grammar_truth_json_sorts_dictionary_keys() -> None:
    """PDF-P3: Grammar truth JSON is deterministic for dictionary key order."""
    assert grammar_truth_json([{"b": 2, "a": 1}]) == '[{"a":1,"b":2}]'


@pytest.mark.condition("PDF-P3")
def test_grammar_truth_sorting_handles_none_and_dictionary_values_deterministically() -> None:
    """PDF-P3: Grammar truth sorting handles optional identifiers and dict values."""
    first_value = {"b": 1, "a": 2}
    second_value = {"a": 2, "b": 1}
    records = [
        GrammarTruthRecord("B", "cue", 1, None, first_value, "same", "body", "same", "first"),
        GrammarTruthRecord("B", "cue", 1, None, second_value, "same", "body", "same", "second"),
    ]

    sorted_records = sort_grammar_truth_records(records)

    assert sorted_records == records


@pytest.mark.condition("PDF-P3")
def test_grammar_truth_sorting_handles_none_links_to() -> None:
    """PDF-P3: Grammar truth sorting treats missing links as an empty key."""
    records = [
        GrammarTruthRecord("B", "cue", 1, None, "value", None, "body", "same"),
        GrammarTruthRecord("B", "cue", 1, None, "value", "next", "body", "same"),
    ]

    sorted_records = sort_grammar_truth_records(records)

    assert sorted_records == records


@pytest.mark.condition("PDF-P3")
def test_grammar_truth_sorting_handles_none_instance_id() -> None:
    """PDF-P3: Grammar truth sorting treats missing instance IDs as an empty key."""
    records = [
        GrammarTruthRecord("B", "cue", 1, None, "value", "same", "body", None),
        GrammarTruthRecord("B", "cue", 1, None, "value", "same", "body", "next"),
    ]

    sorted_records = sort_grammar_truth_records(records)

    assert sorted_records == records


@pytest.mark.condition("PDF-P3")
def test_grammar_truth_bbox_property_cases_emit_pdf_coordinates() -> None:
    """PDF-P3: Bounded bbox partitions obey the PDF coordinate theorem."""
    cases = [
        ((10, 5, 40, 25), 80.0, [10.0, 55.0, 40.0, 75.0]),
        ((40, 25, 10, 5), 80.0, [10.0, 55.0, 40.0, 75.0]),
        ([(-5, 2), (15, 10), (8, 20)], 30.0, [-5.0, 10.0, 15.0, 28.0]),
        ([(1.25, 2.5, "ignored"), (4.75, 8.5, "ignored")], 10.0, [1.25, 1.5, 4.75, 7.5]),
        ((0, 0, 0, 0), 12.0, [0.0, 12.0, 0.0, 12.0]),
    ]

    for index, (bbox, canvas_height, expected) in enumerate(cases):
        target = _TargetWithBBox(bbox)
        annotate_grammar_truth(target, f"BBOX-{index}", "cue")

        records = records_for_annotated_target(target, page=2, canvas_height=canvas_height)

        assert records[0].page == 2
        assert records[0].bbox == expected


@pytest.mark.condition("PDF-P3")
def test_grammar_truth_annotation_property_cases_round_trip_and_sort_deterministically() -> None:
    """PDF-P3: Bounded valid annotation partitions round-trip and sort deterministically."""
    kinds = ("cue", "construct", "link", "assessment")
    channels = ("body", "metadata")
    values = (None, "text", {"b": 2, "a": [1, 3]})
    records: list[GrammarTruthRecord] = []

    for index, (kind, source_channel, value) in enumerate(
        (kind, source_channel, value) for kind in kinds for source_channel in channels for value in values
    ):
        annotation = GrammarTruthAnnotation(
            f"COND-{index}",
            kind,
            value=value,
            links_to="target" if kind == "link" else None,
            source_channel=source_channel,
            instance_id=f"instance-{index}" if index % 2 else None,
        )

        assert GrammarTruthAnnotation.from_dict(annotation.to_dict()) == annotation

        page = 7 if source_channel == "body" else 0
        bbox = [1.0, 2.0, 3.0, 4.0] if source_channel == "body" else None
        records.append(GrammarTruthRecord.from_annotation(annotation, page=page, bbox=bbox))

    sorted_once = sort_grammar_truth_records(records)
    sorted_twice = sort_grammar_truth_records(reversed(records))

    assert sorted_once == sorted_twice
    assert grammar_truth_json(sorted_once) == grammar_truth_json(sorted_twice)
