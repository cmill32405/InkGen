"""Tests for InkGen's semantic extraction-truth emit."""

from __future__ import annotations

import uuid
from dataclasses import FrozenInstanceError

import pytest

from InkGen.boundary import Canvas
from InkGen.extraction_truth import (
    ExtractionTruthAnnotation,
    ExtractionTruthRecord,
    annotate_extraction_truth,
    extraction_truth_json,
    normalize_bbox,
    records_for_annotated_target,
    restore_extraction_truth_annotations,
    sort_extraction_truth_records,
)
from InkGen.pdf_generator import ComponentGroupPDF, DocumentPDF, RectanglePDF
from InkGen.style import DrawingStyle


@pytest.fixture
def drawing_style() -> DrawingStyle:
    """Return a drawing style for extraction-truth tests."""
    return DrawingStyle(
        f"truth_border_{uuid.uuid4().hex}",
        stroke="#000000",
        stroke_width=0.2,
        fill="none",
    )


def _document_with_group(group: ComponentGroupPDF) -> DocumentPDF:
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    document.page(1).layer("base").add_component_group(group)
    return document


class _TargetWithBBox:
    def __init__(self, bbox: object) -> None:
        self.bbox = bbox


@pytest.mark.condition("PDF-P2")
def test_document_pdf_emits_group_truth_in_pdf_coordinates(drawing_style: DrawingStyle) -> None:
    """PDF-P2: Group truth bboxes emit in rendered PDF bottom-left coordinates."""
    group = ComponentGroupPDF("invoice_total")
    group.add_component(RectanglePDF((10.0, 5.0), 30.0, 20.0, 0.0, drawing_style))
    annotate_extraction_truth(group, "invoice_total", "123.45", instance_id="body-total")
    document = _document_with_group(group)

    mm_to_points = 72.0 / 25.4
    assert document.extraction_truth() == [
        {
            "field": "invoice_total",
            "value": "123.45",
            "role": "value",
            "page": 1,
            "bbox": [10.0 * mm_to_points, 55.0 * mm_to_points, 40.0 * mm_to_points, 75.0 * mm_to_points],
            "source_channel": "body",
            "is_truth": True,
            "instance_id": "body-total",
            "coordinate_frame": "pdf_points_bottom_left",
        }
    ]


@pytest.mark.condition("PDF-P2")
def test_document_pdf_emits_component_and_out_of_band_truth(
    drawing_style: DrawingStyle,
) -> None:
    """PDF-P2: Truth emit supports component-level and out-of-band channels."""
    group = ComponentGroupPDF("contract_number_group")
    label = RectanglePDF((10.0, 10.0), 5.0, 5.0, 0.0, drawing_style)
    value_box = RectanglePDF((20.0, 30.0), 40.0, 10.0, 0.0, drawing_style)
    group.add_component(label)
    group.add_component(value_box)
    annotate_extraction_truth(
        label,
        "contract_number",
        "Contract:",
        role="label",
        instance_id="label",
    )
    annotate_extraction_truth(
        value_box,
        "contract_number",
        "W91QVN-26-C-0001",
        instance_id="body",
    )
    document = _document_with_group(group)
    annotate_extraction_truth(
        document,
        "contract_number",
        "W91QVN-26-C-0001",
        source_channel="filename",
        instance_id="filename",
    )
    annotate_extraction_truth(
        document,
        "contract_number",
        "sibling-corroboration",
        source_channel="sibling",
        instance_id="sibling",
    )

    truth = document.extraction_truth()

    assert truth[0]["source_channel"] == "filename"
    assert truth[0]["page"] == 0
    assert truth[0]["bbox"] is None
    sibling_record = next(record for record in truth if record["source_channel"] == "sibling")
    assert sibling_record["page"] == 0
    assert sibling_record["bbox"] is None
    value_record = next(record for record in truth if record["role"] == "value" and record["source_channel"] == "body")
    label_record = next(record for record in truth if record["role"] == "label")
    mm_to_points = 72.0 / 25.4
    assert value_record["bbox"] == [
        20.0 * mm_to_points,
        40.0 * mm_to_points,
        60.0 * mm_to_points,
        50.0 * mm_to_points,
    ]
    assert label_record["bbox"] == [
        10.0 * mm_to_points,
        65.0 * mm_to_points,
        15.0 * mm_to_points,
        70.0 * mm_to_points,
    ]
    assert truth == document.extraction_truth()


@pytest.mark.condition("PDF-P2")
def test_extraction_truth_round_trips_with_document_pdf_parameters(
    drawing_style: DrawingStyle,
) -> None:
    """PDF-P2: Extraction-truth annotations round-trip with PDF parameters."""
    group = ComponentGroupPDF("ambiguous_total")
    decoy = RectanglePDF((10.0, 10.0), 20.0, 5.0, 0.0, drawing_style)
    truth = RectanglePDF((10.0, 25.0), 20.0, 5.0, 0.0, drawing_style)
    group.add_component(decoy)
    group.add_component(truth)
    annotate_extraction_truth(group, "invoice_total", "200.00", instance_id="group-truth")
    annotate_extraction_truth(decoy, "invoice_total", "20.00", is_truth=False, instance_id="decoy")
    annotate_extraction_truth(truth, "invoice_total", "200.00", is_truth=True, instance_id="truth")
    document = _document_with_group(group)
    annotate_extraction_truth(
        document,
        "invoice_total",
        "200.00",
        source_channel="metadata",
        instance_id="meta",
    )

    recreated = DocumentPDF.create_from_dict(document.parameters, {drawing_style.name: drawing_style})

    assert recreated.parameters == document.parameters
    assert recreated.extraction_truth() == document.extraction_truth()
    assert recreated.extraction_truth_json() == document.extraction_truth_json()
    assert recreated.to_pdf_bytes() == document.to_pdf_bytes()


@pytest.mark.condition("PDF-P2")
def test_extraction_truth_annotations_do_not_change_pdf_bytes(drawing_style: DrawingStyle) -> None:
    """PDF-P2: Adding semantic truth does not alter rendered PDF bytes."""
    group = ComponentGroupPDF("stable_render")
    group.add_component(RectanglePDF((10.0, 10.0), 20.0, 5.0, 0.0, drawing_style))
    document = _document_with_group(group)

    before = document.to_pdf_bytes()
    annotate_extraction_truth(group, "stable_render", "same bytes")
    after = document.to_pdf_bytes()

    assert after == before


@pytest.mark.condition("PDF-P2")
def test_unannotated_pdf_parameters_do_not_gain_extraction_truth_keys(
    drawing_style: DrawingStyle,
) -> None:
    """PDF-P2: Unannotated PDF parameter serialization stays legacy-compatible."""
    group = ComponentGroupPDF("legacy_shape")
    group.add_component(RectanglePDF((10.0, 10.0), 20.0, 5.0, 0.0, drawing_style))
    document = _document_with_group(group)

    group_payload = group.parameters["ComponentGroupPDF"]
    document_payload = document.parameters["DocumentPDF"]

    assert "extraction_truth" not in group_payload
    assert "component_extraction_truth" not in group_payload
    assert "extraction_truth" not in document_payload


@pytest.mark.condition("PDF-P2")
def test_extraction_truth_rejects_empty_required_fields(drawing_style: DrawingStyle) -> None:
    """PDF-P2: Semantic annotations fail loudly when required fields are empty."""
    group = ComponentGroupPDF("bad_truth")
    group.add_component(RectanglePDF((10.0, 10.0), 20.0, 5.0, 0.0, drawing_style))

    with pytest.raises(ValueError, match="field_name must be a non-empty string"):
        annotate_extraction_truth(group, "", "value")


@pytest.mark.condition("PDF-P2")
def test_extraction_truth_rejects_invalid_optional_fields() -> None:
    """PDF-P2: Semantic annotations fail loudly for invalid optional fields."""
    empty_subclass = type("EmptySubclass", (str,), {})("")

    with pytest.raises(ValueError, match="field_name must be a non-empty string"):
        ExtractionTruthAnnotation(empty_subclass, "value")
    with pytest.raises(ValueError, match="source_channel must be a non-empty string"):
        ExtractionTruthAnnotation("field", "value", source_channel="")
    with pytest.raises(TypeError, match="is_truth must be a bool"):
        ExtractionTruthAnnotation("field", "value", is_truth="yes")
    with pytest.raises(TypeError, match="instance_id must be a string or None"):
        ExtractionTruthAnnotation("field", "value", instance_id=object())


@pytest.mark.condition("TRUTH-ANNOTATION-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("payload", "exception_type", "message"),
    [
        (object(), TypeError, "extraction truth annotation data must be a mapping"),
        ({"value": "v"}, ValueError, "field_name is required"),
        ({"field_name": "field"}, ValueError, "value is required"),
        ({"field_name": object(), "value": "v"}, TypeError, "field_name must be a string"),
        ({"field_name": "field", "value": object()}, TypeError, "value must be a string"),
        ({"field_name": "field", "value": "v", "role": object()}, TypeError, "role must be a string"),
        (
            {"field_name": "field", "value": "v", "source_channel": object()},
            TypeError,
            "source_channel must be a string",
        ),
        (
            {"field_name": "field", "value": "v", "instance_id": object()},
            TypeError,
            "instance_id must be a string or None",
        ),
    ],
)
def test_extraction_truth_from_dict_rejects_malformed_serialized_fields(
    payload: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """TRUTH-ANNOTATION-PAYLOAD-P2: Serialized extraction truth cannot stringify malformed fields."""
    with pytest.raises(exception_type, match=message):
        ExtractionTruthAnnotation.from_dict(payload)


@pytest.mark.condition("TRUTH-ANNOTATION-PAYLOAD-P2")
def test_restore_extraction_truth_rejects_malformed_serialized_annotations() -> None:
    """TRUTH-ANNOTATION-PAYLOAD-P2: Restore path uses the same annotation payload boundary."""
    target = _TargetWithBBox(None)

    with pytest.raises(TypeError, match="field_name must be a string"):
        restore_extraction_truth_annotations(target, [{"field_name": object(), "value": "v"}])


@pytest.mark.condition("TRUTH-ANNOTATION-PAYLOAD-P2")
def test_extraction_truth_from_dict_preserves_default_truth_flag() -> None:
    """TRUTH-ANNOTATION-PAYLOAD-P2: Missing is_truth defaults to a true annotation."""
    annotation = ExtractionTruthAnnotation.from_dict({"field_name": "field", "value": "v"})

    assert annotation.is_truth is True


@pytest.mark.condition("PDF-P2")
def test_body_annotation_without_bbox_emits_none_bbox() -> None:
    """PDF-P2: Body extraction truth without usable geometry keeps a null bbox."""

    class TargetWithoutBBox:
        pass

    target = TargetWithoutBBox()
    annotate_extraction_truth(target, "unlocated", "value")

    records = records_for_annotated_target(target, page=3, canvas_height=80.0)

    assert len(records) == 1
    assert records[0].page == 3
    assert records[0].bbox is None


@pytest.mark.condition("PDF-P2")
def test_body_source_channel_uses_value_equality_not_identity(drawing_style: DrawingStyle) -> None:
    """PDF-P2: Dynamically built body source strings still emit body records."""
    group = ComponentGroupPDF("dynamic_body")
    group.add_component(RectanglePDF((10.0, 5.0), 30.0, 20.0, 0.0, drawing_style))
    dynamic_body = b"body".decode()
    body_literal = "body"
    assert dynamic_body == "body"
    assert dynamic_body is not body_literal

    annotate_extraction_truth(group, "field", "value", source_channel=dynamic_body)
    records = records_for_annotated_target(group, page=2, canvas_height=80.0)

    assert records[0].page == 2
    assert records[0].bbox == [10.0, 55.0, 40.0, 75.0]


@pytest.mark.condition("PDF-P2")
def test_non_body_source_channels_suppress_page_and_bbox_regardless_of_sort_order(drawing_style: DrawingStyle) -> None:
    """PDF-P2: Non-body channels on geometric targets never emit body geometry."""
    group_before_body = ComponentGroupPDF("before_body")
    group_before_body.add_component(RectanglePDF((10.0, 5.0), 30.0, 20.0, 0.0, drawing_style))
    annotate_extraction_truth(group_before_body, "field", "before", source_channel="aa")

    group_after_body = ComponentGroupPDF("after_body")
    group_after_body.add_component(RectanglePDF((10.0, 5.0), 30.0, 20.0, 0.0, drawing_style))
    annotate_extraction_truth(group_after_body, "field", "after", source_channel="metadata")

    for group in (group_before_body, group_after_body):
        records = records_for_annotated_target(group, page=3, canvas_height=80.0)
        assert records[0].page == 0
        assert records[0].bbox is None


@pytest.mark.condition("PDF-P2")
def test_extraction_truth_public_helpers_keep_keyword_only_contracts() -> None:
    """PDF-P2: Extraction helpers reject positional values for keyword-only options."""
    target = _TargetWithBBox((1.0, 2.0, 3.0, 4.0))
    annotation = ExtractionTruthAnnotation("field", "value")

    with pytest.raises(TypeError):
        annotate_extraction_truth(target, "field", "value", "label")
    with pytest.raises(TypeError):
        records_for_annotated_target(target, 1, 80.0)
    with pytest.raises(TypeError):
        ExtractionTruthRecord.from_annotation(annotation, 1, None)


@pytest.mark.condition("PDF-P2")
def test_extraction_truth_records_are_immutable() -> None:
    """PDF-P2: Extraction annotation and emitted record dataclasses are frozen."""
    annotation = ExtractionTruthAnnotation("field", "value")
    record = ExtractionTruthRecord.from_annotation(annotation, page=1, bbox=None)

    with pytest.raises(FrozenInstanceError):
        annotation.role = "label"
    with pytest.raises(FrozenInstanceError):
        record.page = 2


@pytest.mark.condition("PDF-P2")
def test_extraction_truth_json_sorts_dictionary_keys() -> None:
    """PDF-P2: Extraction truth JSON is deterministic for dictionary key order."""
    assert extraction_truth_json([{"b": 2, "a": 1}]) == '[{"a":1,"b":2}]'


@pytest.mark.condition("PDF-P2")
def test_extraction_truth_sorting_handles_none_and_bbox_values_deterministically() -> None:
    """PDF-P2: Extraction truth sorting handles optional identifiers and bboxes."""
    records = [
        ExtractionTruthRecord("field", "value", "value", 1, None, "body", True, None),
        ExtractionTruthRecord("field", "value", "value", 1, [1.0, 2.0, 3.0, 4.0], "body", True, "next"),
    ]

    sorted_records = sort_extraction_truth_records(records)

    assert sorted_records == records


@pytest.mark.condition("PDF-P2")
def test_extraction_truth_bbox_property_cases_emit_pdf_coordinates() -> None:
    """PDF-P2: Bounded bbox partitions obey the PDF coordinate theorem."""
    cases = [
        ((10, 5, 40, 25), 80.0, [10.0, 55.0, 40.0, 75.0]),
        ((40, 25, 10, 5), 80.0, [10.0, 55.0, 40.0, 75.0]),
        ([(-5, 2), (15, 10), (8, 20)], 30.0, [-5.0, 10.0, 15.0, 28.0]),
        ([(1.25, 2.5, "ignored"), (4.75, 8.5, "ignored")], 10.0, [1.25, 1.5, 4.75, 7.5]),
        ((0, 0, 0, 0), 12.0, [0.0, 12.0, 0.0, 12.0]),
    ]

    for index, (bbox, canvas_height, expected) in enumerate(cases):
        target = _TargetWithBBox(bbox)
        annotate_extraction_truth(target, f"field-{index}", "value")

        records = records_for_annotated_target(target, page=2, canvas_height=canvas_height)

        assert records[0].page == 2
        assert records[0].bbox == expected


@pytest.mark.condition("PDF-P2")
def test_extraction_truth_bbox_normalization_rejects_malformed_shapes() -> None:
    """PDF-P2: Bbox normalization ignores malformed shapes without partial coercion."""
    assert normalize_bbox([]) is None
    assert normalize_bbox([1, 2, 3]) is None
    assert normalize_bbox([1, 2, 3, 4, 5]) is None
    assert normalize_bbox([(1.0, "bad"), (3.0, 4.0)]) == (3.0, 4.0, 3.0, 4.0)
    assert normalize_bbox([("bad", 2.0), (3.0, 4.0)]) == (3.0, 4.0, 3.0, 4.0)
    assert normalize_bbox([(1.0,), (3.0, 4.0)]) == (3.0, 4.0, 3.0, 4.0)
    assert normalize_bbox([object(), (3.0, 4.0)]) == (3.0, 4.0, 3.0, 4.0)


@pytest.mark.condition("TRUTH-BBOX-FINITE-P2")
@pytest.mark.parametrize(
    ("bbox", "expected_bbox"),
    [
        ((True, 2.0, 3.0, 4.0), None),
        ((1.0, False, 3.0, 4.0), None),
        ((1.0, 2.0, float("nan"), 4.0), None),
        ((1.0, 2.0, 3.0, float("inf")), None),
        ([(True, 2.0), (3.0, 4.0)], [3.0, 76.0, 3.0, 76.0]),
        ([(1.0, float("nan")), (3.0, 4.0)], [3.0, 76.0, 3.0, 76.0]),
        ([(1.0, 2.0), (float("-inf"), 4.0)], [1.0, 78.0, 1.0, 78.0]),
    ],
)
def test_extraction_truth_bbox_normalization_rejects_bool_and_nonfinite_coordinates(
    bbox: object,
    expected_bbox: list[float] | None,
) -> None:
    """TRUTH-BBOX-FINITE-P2: Bool and non-finite bbox coordinates are not numeric truth geometry."""
    target = _TargetWithBBox(bbox)
    annotate_extraction_truth(target, "field", "value")

    records = records_for_annotated_target(target, page=2, canvas_height=80.0)

    assert records[0].bbox == expected_bbox


@pytest.mark.condition("PDF-P2")
def test_extraction_truth_annotation_property_cases_round_trip_and_sort_deterministically() -> None:
    """PDF-P2: Bounded valid annotation partitions round-trip and sort deterministically."""
    roles = ("label", "value")
    channels = ("body", "metadata")
    truth_values = (True, False)
    records: list[ExtractionTruthRecord] = []

    for index, (role, source_channel, is_truth) in enumerate(
        (role, source_channel, is_truth) for role in roles for source_channel in channels for is_truth in truth_values
    ):
        annotation = ExtractionTruthAnnotation(
            f"field-{index}",
            f"value-{index}",
            role=role,
            source_channel=source_channel,
            is_truth=is_truth,
            instance_id=f"instance-{index}" if index % 2 else None,
        )

        assert ExtractionTruthAnnotation.from_dict(annotation.to_dict()) == annotation

        page = 7 if source_channel == "body" else 0
        bbox = [1.0, 2.0, 3.0, 4.0] if source_channel == "body" else None
        records.append(ExtractionTruthRecord.from_annotation(annotation, page=page, bbox=bbox))

    sorted_once = sort_extraction_truth_records(records)
    sorted_twice = sort_extraction_truth_records(reversed(records))

    assert sorted_once == sorted_twice
    assert extraction_truth_json(sorted_once) == extraction_truth_json(sorted_twice)
