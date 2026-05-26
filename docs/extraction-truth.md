# Extraction Truth

InkGen can attach semantic extraction truth to PDF-rendered documents without
changing the rendered bytes. This is used for generated-document fixtures where
the document twin knows both what it depicts and where that value appears.

The API lives in `InkGen.extraction_truth`:

- `annotate_extraction_truth(target, field_name, value, role="value", source_channel="body")`
- `DocumentPDF.extraction_truth()`
- `DocumentPDF.extraction_truth_json()`

Targets may be a `ComponentGroupPDF`, an individual PDF component, or the
`DocumentPDF` itself for out-of-band channels.

## Record Schema

`DocumentPDF.extraction_truth()` returns a deterministic list of dictionaries:

```python
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
```

Body-channel bounding boxes are emitted in rendered PDF point space:
bottom-left origin, one unit per PDF point. This matches the PDF parser's native
frame. Out-of-band channels such as `filename` and `metadata` emit `page: 0` and
`bbox: None`.

## Example

```python
from InkGen.boundary import Canvas
from InkGen.extraction_truth import annotate_extraction_truth
from InkGen.pdf_generator import ComponentGroupPDF, DocumentPDF, RectanglePDF
from InkGen.style import DrawingStyle

canvas = Canvas(100.0, 80.0)
document = DocumentPDF(canvas)
document.add_page()

style = DrawingStyle("truth_border", stroke="#000000", stroke_width=0.2, fill="none")
group = ComponentGroupPDF("invoice_total")
group.add_component(RectanglePDF((10.0, 5.0), 30.0, 20.0, 0.0, style))
annotate_extraction_truth(group, "invoice_total", "123.45", instance_id="body-total")

document.page(1).layer("base").add_component_group(group)

truth = document.extraction_truth()
truth_json = document.extraction_truth_json()
```

Adding extraction-truth annotations does not alter `DocumentPDF.to_pdf_bytes()`.
The annotations serialize with `DocumentPDF.parameters` and restore through
`DocumentPDF.create_from_dict()`.
