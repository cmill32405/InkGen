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
`custom_font_paths`. Used font resources include deterministic `/ToUnicode`
CMaps for InkGen's current printable ASCII text range, bytes 32 through 126, so
standard PDF text extractors can map generated ASCII bytes back to Unicode.
`TextPDF` rejects tabs, control characters, non-ASCII Latin-1, and Unicode
characters outside that mapped range before PDF bytes are emitted.

The dependency-free backend still emits simple single-byte text strings. Full
WinAnsi, Unicode/CID text encoding, glyph subsetting, shaping in PDF text
operators, and complex-script extraction maps beyond the current ASCII CMap are not
implemented in this slice.

## PDF Capability Roadmap

InkGen's PDF target is a deterministic synthetic drawing and document-fixture
backend, not a full Acrobat replacement. The current backend is useful for
parser-facing technical drawings because it supports pages, vector primitives,
closed renderer domains, deterministic bytes, extraction/grammar truth, raster
images with alpha, JPEG pass-through, ICC profile emission, Standard 14 fonts,
named TrueType/OpenType font embedding, page labels, page rotations,
Crop/Bleed/Trim/Art page boxes, flat and arbitrary-depth nested
outlines/bookmarks, URI links, internal page links, named destinations,
named-destination links, text annotations, FreeText annotations, highlight
annotations, square annotations, circle annotations, line annotations,
rectangular and closed path group clipping, stroke/fill opacity through PDF
ExtGState resources, group blend modes through PDF ExtGState resources, and
stroke dash/cap/join/miter operators.

The remaining gaps that keep the backend from being a fully featured PDF
creation system are:

| Area | Current status | Needed for full-feature parity |
|---|---|---|
| Text encoding | Single-byte literal strings over printable ASCII bytes 32-126, installed-font embedding, fail-fast text-domain validation, and printable ASCII `/ToUnicode` CMaps | Full WinAnsi, Unicode/CID fonts, glyph subsetting, and full complex-script text extraction maps |
| Text layout | Positioned text components with explicit line-break output using `TextStyle.line_spacing` and per-line `TextStyle.text_align` | Automatic wrapping, tabs, columns, kerning, and complex-script shaping |
| Graphics state | Basic stroke/fill primitives, rectangular and closed path group clipping with nonzero/even-odd clip rules, group blend modes, stroke/fill alpha ExtGState resources, and stroke dash/cap/join/miter operators | Opacity groups, gradients, and patterns |
| Document structure | Pages, deterministic metadata, page labels, page rotations, Crop/Bleed/Trim/Art boxes, flat and arbitrary-depth nested outlines/bookmarks, URI links, internal page links, named destinations, named-destination links, text annotations, FreeText annotations, highlight annotations, square annotations, circle annotations, and line annotations | Rich annotation appearances, replies/widgets, raw generic annotations, and tagged PDF structure |
| Color/profile support | Device RGB/CMYK and JPEG ICC profile objects | Broader calibrated color spaces and selectable PDF/A-style archival constraints |
| Import/conversion | SVG input remains SVG-only | Arbitrary SVG-to-PDF conversion and external PDF embedding are out of scope until explicitly approved |
| Optimization/security | Classic xref table and plain objects | Object streams, font/image subsetting, encryption, and signatures if those become product requirements |
| Parser stress fixtures | Purpose-built technical-drawing fixture builder for rotated pages, transparency, tables, title blocks, BOM rows, page boxes, and truth labels | Additional variants for CID encodings, missing/odd CMaps, scans, and other parser-hostile PDF producer behaviors |

The highest-value PDF hardening target for Document Intelligence remains full
Unicode/CID font support because parser extraction quality depends on
recoverable text, especially for hostile or unusual font encodings.

`ComponentGroupPDF` supports rectangular clipping paths through
`set_clip_rect((x, y, width, height))`. Clip rectangles use the same top-left
InkGen document coordinates as PDF primitives because `DocumentPDF` applies the
page-level coordinate flip before group operators are emitted. Clip rectangles
must be finite four-number sequences with positive width and height, are stored
in group parameters, round-trip through `ComponentGroupPDF.create_from_dict()`,
and render as `q`, `re`, `W`, `n`, child operators, and `Q`. Arbitrary path
clipping and style-owned clipping are intentionally outside the current closed
renderer contract.

`ComponentGroupPDF` also supports closed path clipping through
`set_clip_path(commands)`. Clip paths use the same `PathCommand` command model
as `PathPDF`, must be non-empty, must start with `M`, must end with `Z`, are
cloned before storage, and are validated before group state changes. They are
stored as `clip_path` in group parameters, hydrate through
`ComponentGroupPDF.create_from_dict()`, and render as path operators followed by
`W` or `W*` and `n`. Rectangular and path clips can be configured together; PDF
applies them as intersecting clipping paths inside the same group graphics-state
wrapper.

Clip rules can be selected with `ComponentGroupPDF.set_clip_rule()`. The default
`nonzero` rule emits `W` and is not serialized; `evenodd` emits `W*` for every
configured group clip and round-trips as `clip_rule`. Per-clip fill rules inside
one group, raw PDF clipping operators, open paths, text clipping, and
renderer-neutral clipping state remain intentionally out of scope.

`ComponentGroupPDF` also supports standard PDF blend modes through
`set_blend_mode(mode)`. Supported non-default modes are the standard PDF blend
mode names such as `Multiply`, `Screen`, `Overlay`, `Darken`, `Lighten`,
`ColorDodge`, `ColorBurn`, `HardLight`, `SoftLight`, `Difference`, `Exclusion`,
`Hue`, `Saturation`, `Color`, and `Luminosity`; `Normal` and `None` clear the
setting. Blend modes are stored in group parameters, hydrate through
`ComponentGroupPDF.create_from_dict()`, and render through deterministic
`/ExtGState` resources on the `DocumentPDF` live path. They remain group-local
PDF renderer state and do not change neutral drawing recipes or shared
`DrawingStyle`.

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

`DocumentPDF` supports explicit page labels through `set_page_label()`, page
rotations through `set_page_rotation()`, and additional page boxes through
`set_page_box()`. Page labels are emitted as a PDF `/PageLabels` number tree
with literal string prefixes. Page rotations are emitted as page dictionary
`/Rotate` entries normalized to `90`, `180`, or `270`. Page boxes are emitted on
the target page dictionary as `/CropBox`, `/BleedBox`, `/TrimBox`, or `/ArtBox`
entries in PDF bottom-left page coordinates. Labels, rotations, and boxes are
stored in document parameters, round-trip through `DocumentPDF.create_from_dict()`,
and follow page insertions and removals. Invalid page labels, rotations, page
numbers, box names, and box coordinates fail at the `DocumentPDF` boundary before
rendering. Page rotation is viewer metadata; it does not remap component
geometry or truth coordinates.

`DocumentPDF` also supports PDF outlines through `add_outline()`. Each outline
has a Latin-1 title, targets an existing page, and may set PDF `/XYZ`
destination `left`, `top`, and `zoom` values. Omitted `top` or `zoom` values are
emitted as PDF `null` destination entries. Omit `parent` for a top-level
outline. Use `parent="<title>"` for a child under an earlier outline whose title
matches exactly one existing outline. Duplicate flat titles remain valid until a
caller tries to use that title as a parent. Use `expanded=False` on a parent
outline to emit a collapsed bookmark state with a negative descendant `/Count`;
expanded outlines are the default and omit the serialized flag. Outlines are
stored in document parameters, round-trip through
`DocumentPDF.create_from_dict()`, follow page insertions and removals, prune
orphaned descendants when a parent outline is removed, and are emitted as
deterministic root, sibling, and recursive child outline objects.

URI link annotations can be added through `DocumentPDF.add_uri_link()`. Each
link targets an existing source page, stores a finite positive-area rectangle
inside that page's MediaBox, and emits a PDF `/Subtype /Link` annotation with a
URI action. Link target strings are non-empty Latin-1 values because the current
dependency-free backend emits literal PDF strings. URI links are stored in
document parameters, round-trip through `DocumentPDF.create_from_dict()`, follow
page insertions and removals, and are emitted in deterministic page/insertion
order.

Internal page link annotations can be added through
`DocumentPDF.add_page_link()`. Each link has an existing source page, an existing
target page, a finite positive-area rectangle on the source page, and a PDF
`/XYZ` destination with finite `left`, `top`, and `zoom` values when provided.
Omitted `top` or `zoom` values are emitted as PDF `null` destination entries.
Internal links are stored in document parameters, round-trip through
`DocumentPDF.create_from_dict()`, follow source and target page insertions and
removals, and are emitted as deterministic `/Subtype /Link` annotations with a
direct `/Dest` array.

Named destinations can be added through `DocumentPDF.add_named_destination()`,
and active regions that target them can be added through
`DocumentPDF.add_named_destination_link()`. Destination names are non-empty
Latin-1 PDF literal strings. Named destinations target existing pages with PDF
`/XYZ` destinations, are emitted through the catalog `/Names` dictionary, sort
deterministically by destination name, round-trip through
`DocumentPDF.create_from_dict()`, and follow page insertions and removals. Links
to named destinations are deterministic `/Subtype /Link` annotations with a
literal-string `/Dest`. Generic PDF annotation types beyond the explicit text,
FreeText, highlight, square, circle, and line APIs, rich annotation appearances,
and tagged PDF structure are intentionally out of scope.

Text annotations can be added through `DocumentPDF.add_text_annotation()`. Each
annotation has an existing source page, a finite positive-area rectangle inside
that page's MediaBox, non-empty Latin-1 contents, an optional non-empty Latin-1
title, and a strict boolean `open` state. Text annotations are stored in document
parameters, round-trip through `DocumentPDF.create_from_dict()`, follow page
insertions and removals, and are emitted as deterministic `/Subtype /Text`
annotation objects after URI, internal page, and named-destination links on each
page.

FreeText annotations can be added through
`DocumentPDF.add_free_text_annotation()`. Each annotation has an existing source
page, a finite positive-area rectangle inside that page's MediaBox, non-empty
Latin-1 contents, a strict RGB text color accepted as `#rrggbb` or serialized
0.0-1.0 channel triple, and a finite positive font size. FreeText annotations
emit deterministic `/Subtype /FreeText` objects with `/DA` and local `/DR`
Helvetica resources, are stored in document parameters, round-trip through
`DocumentPDF.create_from_dict()`, follow page insertions and removals, and are
emitted after sticky text annotations on each page. Rich text strings,
appearance streams, callouts, rotation, border styles, replies/widgets, tagged
PDF structure, and arbitrary raw annotation dictionaries remain intentionally
out of scope.

Highlight annotations can be added through
`DocumentPDF.add_highlight_annotation()`. Each annotation has an existing source
page, a finite positive-area rectangle inside that page's MediaBox, a strict RGB
color accepted as `#rrggbb` or serialized 0.0-1.0 channel triple, and optional
non-empty Latin-1 contents. Highlights emit deterministic `/Subtype /Highlight`
objects with rectangle-derived `/QuadPoints`, are stored in document parameters,
round-trip through `DocumentPDF.create_from_dict()`, follow page insertions and
removals, and are emitted after text annotations on each page. Rich annotation
appearance streams, comments/replies, file attachments, stamps, widgets, and
other annotation subtypes remain intentionally out of scope.

Square annotations can be added through
`DocumentPDF.add_square_annotation()`. Each annotation has an existing source
page, a finite positive-area rectangle inside that page's MediaBox, a strict RGB
border color accepted as `#rrggbb` or serialized 0.0-1.0 channel triple, and
optional non-empty Latin-1 contents. Squares emit deterministic
`/Subtype /Square` objects with `/Border [0 0 1]`, are stored in document
parameters, round-trip through `DocumentPDF.create_from_dict()`, follow page
insertions and removals, and are emitted after highlight annotations on each
page. Rich appearance streams, fill colors, comments/replies, file attachments,
stamps, widgets, tagged PDF structure, and arbitrary raw annotation dictionaries
remain intentionally out of scope.

Circle annotations can be added through
`DocumentPDF.add_circle_annotation()`. Each annotation has an existing source
page, a finite positive-area rectangle inside that page's MediaBox, a strict RGB
border color accepted as `#rrggbb` or serialized 0.0-1.0 channel triple, and
optional non-empty Latin-1 contents. Circles emit deterministic
`/Subtype /Circle` objects with `/Border [0 0 1]`, are stored in document
parameters, round-trip through `DocumentPDF.create_from_dict()`, follow page
insertions and removals, and are emitted after square annotations on each page.
Rich appearance streams, fill colors, comments/replies, file attachments,
stamps, widgets, tagged PDF structure, and arbitrary raw annotation dictionaries
remain intentionally out of scope.

Line annotations can be added through
`DocumentPDF.add_line_annotation()`. Each annotation has an existing source page,
distinct finite start/end points inside that page's MediaBox, a strict RGB
border color accepted as `#rrggbb` or serialized 0.0-1.0 channel triple, and
optional non-empty Latin-1 contents. Line endpoints use the same bottom-left
page coordinate frame as the existing annotation rectangle APIs. The generated
PDF derives a positive-area `/Rect` around the line segment and emits
deterministic `/Subtype /Line` objects with `/L`, `/C`, and `/Border [0 0 1]`.
Lines are stored in document parameters, round-trip through
`DocumentPDF.create_from_dict()`, follow page insertions and removals, and are
emitted after circle annotations on each page. Arrowheads, captions, rich
appearance streams, custom border styles, tagged PDF structure, and arbitrary
raw annotation dictionaries remain intentionally out of scope.

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
renderer-neutral drawing groups. DXF emits drawing entities, including
true-color stroke/lineweight group codes and solid-fill HATCH entities for
closed filled shapes. DXF is separate from PDF because it represents drawing
entities, not paged document graphics.

The renderer-neutral drawing class system is scoped to SVG, PDF, and DXF. Flow
documents use those same primitive groups as document blocks when DOCX, HTML,
Markdown, RTF, or plain-text fixtures need embedded diagrams.

Semantic extraction-truth annotations can be attached through
`InkGen.extraction_truth` and emitted with `DocumentPDF.extraction_truth()`. Those
records use rendered PDF point coordinates (`pdf_points_bottom_left`) so they can
be compared directly with parser output.

Parser stress PDFs can be built with `InkGen.parser_stress_fixtures`. The
default `build_parser_stress_pdf()` output is a single-page technical drawing
with a rotated PDF page dictionary, TrimBox metadata, a title block, a BOM table,
a semi-transparent overlay, zone markers, and extraction/grammar truth records.
The builder composes public PDF primitives and truth helpers; it does not own PDF
serialization and does not add dependencies.

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
- Page labels, page rotations, and Crop/Bleed/Trim/Art page boxes with
  serialization round trips, insertion/removal index shifts, and invalid
  metadata rejection
- Flat PDF outlines/bookmarks with serialization round trips, destination
  validation, insertion/removal index shifts, and invalid metadata rejection
- URI link annotations with serialization round trips, same-page annotation
  arrays, rectangle/URI validation, insertion/removal index shifts, and invalid
  metadata rejection
- Internal page link annotations with serialization round trips, same-page
  annotation arrays, source/target page validation, insertion/removal index
  shifts, and invalid metadata rejection
- Named destinations and named-destination link annotations with serialization
  round trips, deterministic name-tree ordering, source/target validation,
  insertion/removal index shifts, and invalid metadata rejection
- Text, FreeText, highlight, square, circle, and line annotations with
  serialization round trips, source-page validation, insertion/removal index
  shifts, deterministic page annotation ordering, and invalid metadata rejection
