# PDF Generation

InkGen includes a dependency-free PDF backend that parallels the SVG primitive
renderer over the same geometry, style, document, and component-group model.

The PDF backend lives in `InkGen.pdf_generator` and provides:

- `PDFGeneratorInterface`
- `RectanglePDF`, `LinePDF`, `ArcPDF`, `QuadraticBezierPDF`, `CubicBezierPDF`
- `PathPDF`, `RegularPolygonPDF`, `PolygonalPDF`, `CirclePDF`, `TextPDF`
- `ComponentGroupPDF`
- `DocumentPDF`

`DocumentPDF` writes one PDF page per InkGen document page. It applies the
SVG-style top-left/y-down to PDF bottom-left/y-up coordinate transform once at
the page content-stream level, and text rendering counter-flips glyphs so text
stays upright. PDF metadata dates and object ordering are fixed so repeated
renders of the same document produce deterministic bytes.

Higher-level synthetic drawing helpers should use `InkGen.drawing_components`
when they need to target multiple formats. For example, `ZoningDrawing` stores a
renderer-neutral zoning recipe and can materialize either `ComponentGroupSVG` or
`ComponentGroupPDF` from the same geometry.

`SVGComponent` remains SVG-only. The PDF backend does not currently embed or
convert arbitrary external SVG files into PDF operators.

For CAD-oriented interchange, use `InkGen.dxf_generator.DXFDocument` with
renderer-neutral drawing groups. DXF is separate from PDF because it represents
drawing entities, not paged document graphics.

The renderer-neutral drawing class system is scoped to SVG, PDF, and DXF. Flow
documents use those same primitive groups as document blocks when DOCX, HTML,
RTF, or plain-text fixtures need embedded diagrams.

Semantic extraction-truth annotations can be attached through
`InkGen.extraction_truth` and emitted with `DocumentPDF.extraction_truth()`. Those
records use rendered PDF point coordinates (`pdf_points_bottom_left`) so they can
be compared directly with parser output.

## Example

```python
from InkGen.boundary import Canvas
from InkGen.pdf_generator import ComponentGroupPDF, DocumentPDF, RectanglePDF, TextPDF
from InkGen.style import DrawingStyle, Font, TextStyle

canvas = Canvas(100.0, 80.0)
document = DocumentPDF(canvas)
document.add_page()

drawing_style = DrawingStyle("pdf_border", stroke="#000000", stroke_width=0.2, fill="none")
text_style = TextStyle("pdf_text", font=Font(size=12.0))

group = ComponentGroupPDF("panel")
group.add_component(RectanglePDF((10.0, 20.0), 30.0, 40.0, 0.0, drawing_style))
group.add_component(TextPDF("Seed", (15.0, 25.0), text_style))
document.page(1).layer("base").add_component_group(group)

document.create_pdf("examples/output/seed.pdf")
```

## Renderer-Neutral Synthetic Drawings

```python
from InkGen.boundary import Canvas
from InkGen.drawing_components import OutputFormat, ZoningDrawing
from InkGen.pdf_generator import DocumentPDF
from InkGen.style import DrawingStyle, Font, TextStyle

canvas = Canvas(210.0, 297.0, "mm")
zoning = ZoningDrawing(
    canvas,
    line_style=DrawingStyle("zone_lines", stroke="#999999", fill="none", stroke_width=0.2),
    text_style=TextStyle("zone_text", Font(size=6.0)),
    horizontal_zones=10,
    vertical_zones=8,
)

document = DocumentPDF(canvas)
document.add_page()
document.page(1).layer("base").add_component_group(zoning.to_group(OutputFormat.PDF))
document.create_pdf("examples/output/zoning.pdf")
```

## Visual Spot Check

Run the matched SVG/PDF spot-check generator:

```bash
python examples/pdf_visual_spotcheck.py
```

It writes:

- `examples/output/pdf_visual_spotcheck.svg`
- `examples/output/pdf_visual_spotcheck.pdf`

Open both files in local viewers and compare the rectangle, line, circle, and
text placement. The generator builds matched SVG and PDF documents from the same
coordinates and styles without adding a PDF library dependency.

## Verification Status

The PDF backend is covered by PDF-P1 tests for:

- Primitive surface parity against the SVG primitive backend
- PDF content-stream operators for supported primitive types
- SVG-style path command variants (`H`, `V`, `Q`, `C`, `A`, `Z`)
- Deterministic document bytes and page-level coordinate flipping
- Multi-page document assembly
- `create_pdf()` file output and missing-directory failure behavior
- Serialization round trips for primitives, component groups, and documents
- Literal PDF string escaping
- Invisible style no-op painting
- Live-path rejection of non-PDF children
- Renderer-agnostic group truth geometry via labels and segmentation masks
- Renderer-neutral zoning recipes that emit PDF-safe component groups
- Visual spot-check artifact generation
