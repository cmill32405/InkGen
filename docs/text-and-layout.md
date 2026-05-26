# Text & Layout

InkGen provides utilities for laying out text, zoning drawings, and managing tabular data. These features sit atop the primitives described earlier and are primarily implemented in the following modules:

- `src/InkGen/text_fitter.py`
- `src/InkGen/text_outline.py`
- `src/InkGen/paragraph.py`
- `src/InkGen/cad_component_groups.py`
- `src/InkGen/drawing_components.py`
- `src/InkGen/table.py`

## Text Fitting Workflow

`TextFitter` wraps HarfBuzz, fontTools, and shapely to render text within arbitrary polygons. It automatically adjusts font size and word wrapping to fit text into complex shapes.

### Basic Text Fitting

```python
from InkGen.text_fitter import TextBlock, TextFitter
from InkGen.style import TextStyle, Font
from shapely.geometry import Polygon as ShapelyPolygon

# Define text block parameters
text_block = TextBlock(
    text="Engineering Systems Division",
    font_path="C:/Windows/Fonts/arial.ttf",
    min_font_size_px=8,
    font_size_range=(10, 24),
    max_line_width=120,
)

# Create target shape
outer_shape = ShapelyPolygon([(0, 0), (140, 0), (140, 60), (0, 60)])

# Fit text
fitter = TextFitter()
result = fitter.fit(text_block, fitter_shape=fitter.component_to_fitter_shape(outer_shape))

# Check if fitting succeeded
if result.success:
    # Convert fitted lines to TextSVG components
    style = TextStyle("Body", Font("Arial", size=result.font_size))
    for line in result.lines:
        text_svg = TextSVG(
            text=line.text,
            position=(line.x, line.y),
            style=style
        )
        # Add to component group...
```

### Fitting Parameters

The `TextBlock` constructor accepts:
- `text`: The text string to fit
- `font_path`: Path to the TrueType/OpenType font file
- `min_font_size_px`: Minimum font size to try (in pixels)
- `font_size_range`: Tuple of (min, max) font sizes to search
- `max_line_width`: Maximum width for a single line (in document units)

The fitter performs binary search over font size, adaptive word wrapping, and geometric jittering to ensure text stays within the boundary. When `TextFitter.fit()` returns a `FittingResult`, you can convert the text lines into `TextSVG` components.

## Text Outlines

`text_outline.py` can vectorize text for debugging or mask production:

```python
from InkGen.text_outline import outline_for_text

outline = outline_for_text(
    text="InkGen",
    font_path="C:/Windows/Fonts/arial.ttf",
    size_px=24,
    x=0,
    y=0,
    add_one_pixel_margin=True,
)
svg_path = outline["svg_path"]
convex_hull = outline["convex_hull"]
```

This data is useful for collision checking and annotation overlays.

## Paragraphs

`Paragraph` stores Word-like paragraph settings separately from any renderer.
It supports alignment, first-line and hanging indents, left/right indents,
before/after spacing, line spacing rules, tab stops, and pagination flags such
as keep-with-next and page-break-before.

```python
from InkGen.paragraph import LineSpacingRule, Paragraph, ParagraphAlignment
from InkGen.style import TextStyle, Font

body_style = TextStyle("Body", Font("Arial", size=10))
paragraph = Paragraph(
    "This paragraph can be materialized as SVG or PDF text lines.",
    position=(20, 40),
    width=120,
    style=body_style,
    alignment=ParagraphAlignment.LEFT,
    first_line_indent=6,
    space_before=2,
    space_after=3,
    line_spacing=1.15,
    line_spacing_rule=LineSpacingRule.MULTIPLE,
    keep_with_next=True,
)
paragraph.add_tab_stop(30)

drawing_group = paragraph.to_drawing_group("BodyParagraph")
pdf_group = drawing_group.to_group("pdf")
svg_group = drawing_group.to_group("svg")
```

## Flow Documents

`FlowDocument` collects ordered paragraph, table, and drawing primitive blocks
and exports dependency-free document files. DOCX is the primary bridge for Word
and Google Docs workflows. HTML, RTF, and plain text are also supported for
lighter interchange. Google Docs itself is a hosted editor rather than a local
file format, so the portable paths are the formats it can import/export.

```python
from InkGen.document_outputs import FlowDocument

flow_doc = FlowDocument(title="Inspection Notes")
flow_doc.add_paragraph(paragraph)
flow_doc.add_table(table)
flow_doc.add_drawing_group(drawing_group)

flow_doc.create_docx("examples/output/inspection_notes.docx")
flow_doc.create_html("examples/output/inspection_notes.html")
flow_doc.create_rtf("examples/output/inspection_notes.rtf")
flow_doc.create_text("examples/output/inspection_notes.txt")
```

## Zoning and CAD Layouts

`cad_component_groups.Zoning` is the legacy SVG-oriented zoning helper. New
multi-format synthetic drawings should use `drawing_components.ZoningDrawing`,
which builds the same kind of grid overlay from renderer-neutral primitives and
then emits SVG or PDF component groups. The same primitive groups can be exported
as DXF through `DXFDocument`.

```python
from InkGen.drawing_components import OutputFormat, ZoningDrawing
from InkGen.style import DrawingStyle, TextStyle, Font

zoning_style = DrawingStyle("ZoneLines", stroke="#999", stroke_width=0.2)
zoning_text = TextStyle("ZoneLabels", Font("Arial", weight="bold", size=6))
zoning = ZoningDrawing(
    canvas,
    line_style=zoning_style,
    text_style=zoning_text,
    margins=5,
    horizontal_zones=10,
    vertical_zones=8,
)
pdf_group = zoning.to_group(OutputFormat.PDF)
svg_group = zoning.to_group(OutputFormat.SVG)
```

## Tables

The `Table` API lets you build spreadsheet-like layouts and convert them into SVG using `TableSVG`.

```python
from InkGen.table import Table, AutoFitRule
from InkGen.style import TextStyle, Font, DrawingStyle
from InkGen.svg_generator import TableSVG

table = Table(position=(10, 10))
table.add_column(width=40.0)
table.add_column(width=80.0)
table.add_row(height=12.0)

header_style = TextStyle("Header", Font("Arial", weight="bold", size=12))
body_style = TextStyle("Body", Font("Arial", size=10))

table.cell(0, 0).add_paragraph("Item", style_id=header_style.name)
table.cell(0, 1).add_paragraph("Description", style_id=header_style.name)
table.cell(1, 0).add_paragraph("001", style_id=body_style.name)
table.cell(1, 1).add_paragraph("Hydraulic Pump", style_id=body_style.name)

border_style = DrawingStyle("TableBorder", stroke="#222", stroke_width=0.2, fill="none")
table_group = TableSVG.from_table(
    table,
    group_label="BillOfMaterials",
    border_style=border_style,
    text_styles={
        header_style.name: header_style,
        body_style.name: body_style,
    },
)
```

Set `table.autofit = True` to enable auto-fit rules. Per-row and per-column rules can be set via `row.height_rule = AutoFitRule.EXPAND` and `column.width_rule = AutoFitRule.FIT`.

## Putting It Together

Most practical documents combine these layout utilities:

1. Use `ZoningDrawing` to draw grid overlays and annotation callouts across SVG/PDF/DXF outputs.
2. Fit descriptive text into complex components with `TextFitter`.
3. Add revision tables or bills of materials using the `Table` API.
4. Render drawings through `DocumentSVG`, `DocumentPDF`, or `DXFDocument`, and render flow documents through `FlowDocument`.

See the [Examples](examples.md) section for end-to-end walkthroughs.
