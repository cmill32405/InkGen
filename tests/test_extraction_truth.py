"""Tests for InkGen's semantic extraction-truth emit."""

from __future__ import annotations

import uuid

import pytest

from InkGen.boundary import Canvas
from InkGen.extraction_truth import annotate_extraction_truth
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


@pytest.mark.condition("PDF-P2")
def test_document_pdf_emits_group_truth_in_pdf_coordinates(drawing_style: DrawingStyle) -> None:
    """PDF-P2: Group truth bboxes emit in rendered PDF bottom-left coordinates."""
    group = ComponentGroupPDF("invoice_total")
    group.add_component(RectanglePDF((10.0, 5.0), 30.0, 20.0, 0.0, drawing_style))
    annotate_extraction_truth(group, "invoice_total", "123.45", instance_id="body-total")
    document = _document_with_group(group)

    assert document.extraction_truth() == [
        {
            "field": "invoice_total",
            "value": "123.45",
            "role": "value",
            "page": 1,
            "bbox": [10.0, 55.0, 40.0, 75.0],
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
    assert value_record["bbox"] == [20.0, 40.0, 60.0, 50.0]
    assert label_record["bbox"] == [10.0, 65.0, 15.0, 70.0]
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
