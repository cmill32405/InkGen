# PDF Generation

InkGen includes a dependency-free PDF backend that parallels the SVG primitive
renderer over the same geometry, style, document, and component-group model.

The PDF backend lives in `InkGen.pdf_generator` and provides:

- `PDFGeneratorInterface`
- `RectanglePDF`, `LinePDF`, `ArcPDF`, `QuadraticBezierPDF`, `CubicBezierPDF`
- `PathPDF`, `RegularPolygonPDF`, `PolygonalPDF`, `CirclePDF`, `TextPDF`
- `ImagePDF`
- `ComponentGroupPDF`
- `DocumentPDF`

`DocumentPDF` writes one PDF page per InkGen document page. It applies the
SVG-style top-left/y-down to PDF bottom-left/y-up coordinate transform once at
the page content-stream level, and text rendering counter-flips glyphs so text
stays upright. PDF metadata dates and object ordering are fixed so repeated
renders of the same document produce deterministic bytes.

PDF text uses `TextStyle.font` to choose deterministic font resources. Generic
families keep the built-in PDF Standard behavior: Helvetica/sans-serif,
Times/serif, and Courier/monospace map to Standard 14 resources, including bold
and italic/oblique variants. Named installed TrueType/OpenType fonts resolve
through InkGen's existing `Font.font_file` discovery and are embedded in the PDF
with WinAnsi widths and a font descriptor. This covers common OS fonts on
Windows, macOS, and Linux when the font is installed or provided through
`custom_font_paths`.

The dependency-free backend still emits simple WinAnsi text strings. Full
Unicode/CID text encoding, glyph subsetting, shaping in PDF text operators, and
complex-script extraction maps are not implemented in this slice.

## PDF Capability Roadmap

InkGen's PDF target is a deterministic synthetic drawing and document-fixture
backend, not a full Acrobat replacement. The current backend is useful for
parser-facing technical drawings because it supports pages, vector primitives,
closed renderer domains, deterministic bytes, extraction/grammar truth, raster
images with alpha, JPEG pass-through, ICC profile emission, Standard 14 fonts,
and named TrueType/OpenType font embedding.

The remaining gaps that keep the backend from being a fully featured PDF
creation system are:

| Area | Current status | Needed for full-feature parity |
|---|---|---|
| Text encoding | WinAnsi literal strings and installed-font embedding | Unicode/CID fonts, `/ToUnicode` CMaps, glyph subsetting, and text extraction maps |
| Text layout | Single positioned text components | Multi-line wrapping, alignment, tabs, columns, kerning, and complex-script shaping |
| Graphics state | Basic stroke/fill primitives | Clipping paths, dash arrays, line caps/joins, miter limits, opacity groups, blend modes, gradients, and patterns |
| Document structure | Pages and deterministic metadata | Outlines/bookmarks, links, annotations, tagged PDF structure, page labels, and additional page boxes |
| Color/profile support | Device RGB/CMYK and JPEG ICC profile objects | Broader calibrated color spaces and selectable PDF/A-style archival constraints |
| Import/conversion | SVG input remains SVG-only | Arbitrary SVG-to-PDF conversion and external PDF embedding are out of scope until explicitly approved |
| Optimization/security | Classic xref table and plain objects | Object streams, font/image subsetting, encryption, and signatures if those become product requirements |
| Parser stress fixtures | Core truth records and current synthetic drawings | Purpose-built fixtures for CID encodings, missing/odd CMaps, rotated pages, transparency, scans, tables, title blocks, and BOM drawings |

The highest-value PDF hardening target for Document Intelligence remains
Unicode/CID/`ToUnicode` support because parser extraction quality depends on
recoverable text, especially for hostile or unusual font encodings.

PDF raster images use `RasterImageAsset` and `ImagePDF`. InkGen accepts
Pillow-decodable raster inputs at the asset boundary, applies EXIF orientation
before exposing decoded pixels, decodes them to RGB image XObjects, and emits an
alpha soft mask (`/SMask`) when the source image contains transparency. Alpha is
not flattened against white or any other background color. Identity-orientation
RGB and CMYK JPEG sources are passed through as `/DCTDecode` streams so the PDF
can reuse the original encoded bytes; embedded JPEG ICC profiles are emitted as
compressed ICCBased color-space objects with DeviceRGB or DeviceCMYK alternates.
JPEGs that require EXIF rotation or unsupported color modes fall back to
normalized RGB samples. SVG output uses the same `RasterImageAsset` through
`ImageSVG`, normalized to an embedded PNG data URI.

The PDF render path is intentionally closed. `DocumentPDF` renders exact
`ComponentGroupPDF` groups, and `ComponentGroupPDF` accepts/renders only the
built-in PDF primitive/image component classes listed above. Custom dynamic
`generate_pdf()` components and custom `ComponentGroupPDF` subclasses are
outside the supported and proven PDF renderer contract. This constraint keeps
rendered bytes deterministic and supports the grammar-truth noninterference
proof in `docs/proofs/grammar-truth.md`.

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
Markdown, RTF, or plain-text fixtures need embedded diagrams.

Semantic extraction-truth annotations can be attached through
`InkGen.extraction_truth` and emitted with `DocumentPDF.extraction_truth()`. Those
records use rendered PDF point coordinates (`pdf_points_bottom_left`) so they can
be compared directly with parser output.

Grammar truth annotations can be attached through `InkGen.grammar_truth` and
emitted with `DocumentPDF.grammar_truth()`. The emit is registry-agnostic: InkGen
validates only a non-empty `condition_id` and `kind` values of `cue`,
`construct`, `link`, or `assessment`. Doc-level assessments such as OOD safety or
form orientation use `page: 0` and `bbox: None`; body records reuse the same
rendered PDF point coordinate frame as extraction truth.

## Example

```python
from InkGen.boundary import Canvas
from InkGen.grammar_truth import annotate_grammar_truth
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
annotate_grammar_truth(group, "B1", "cue", value="heading_level")
document.page(1).layer("base").add_component_group(group)

document.create_pdf("examples/output/seed.pdf")
truth = document.grammar_truth()
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
- Grammar truth records for cues, constructs, links, and assessments
- Visual spot-check artifact generation
