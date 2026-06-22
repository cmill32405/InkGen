# API Reference

This section provides a high-level index of the primary modules and classes exposed by InkGen. For detailed signatures consult the source files under `src/InkGen/` or generated API docs when available.

## Boundary (`InkGen.boundary`)

- `Boundary`: Base class representing convex hull boundaries.
- `Canvas`: Specialised boundary used as the drawing surface.

## Components (`InkGen.component`)

- `Component`: Base class with identifiers and serialization.
- `DrawingComponent` and subclasses (`StandardDrawingComponent`, `SingleDimensionDrawingComponent`, `PolygonalDrawingComponent`, etc.).
- Geometry-specific classes such as `Arc`, `QuadraticBezier`, `CubicBezier`, `Path`.
- `ComponentGroup`: Collection of components with shared metadata.

## Document (`InkGen.document`)

- `Layer`: Container for component groups. Use `component_groups` for the
  backwards-compatible label-to-id lookup and `groups()` for complete traversal
  when repeated labels must be preserved.
- `Layers`: Layer stack with convenience helpers.
- `Document`: Multi-page document abstraction.

## SVG Generator (`InkGen.svg_generator`)

- `RectangleSVG`, `LineSVG`, `PolygonalSVG`, `RegularPolygonSVG`, `CircleSVG`, `PathSVG`, `TextSVG`.
- `ComponentGroupSVG`, `TableSVG`, `DocumentSVG`.
- `IncludeLayer`: Enum controlling which layers are exported.

## Tables (`InkGen.table`)

- `Table`, `Row`, `Column`, `Cell`.
- `AutoFitRule`: Column and row sizing strategies.

## Styling (`InkGen.style`)

- `Style`: Base style class.
- `DrawingStyle`, `TextStyle`, `Font`.

## Text Fitting (`InkGen.text_fitter`, `InkGen.text_outline`)

- `TextBlock`, `TextFitter`, `FittingResult`.
- Helper functions for outlining text (`outline_for_text`, `sample_path_points`).

## Paragraphs (`InkGen.paragraph`)

- `Paragraph`: Word-like paragraph layout model with alignment, indentation,
  spacing, tab stops, and pagination flags.
- `ParagraphAlignment`, `LineSpacingRule`, `TabStop`, `ParagraphLine`.

## Drawing Components (`InkGen.drawing_components`)

- `DrawingComponentGroup`: Renderer-neutral collection of drawing primitives.
- `RectangleDrawing`, `LineDrawing`, `TextDrawing`, `ArcDrawing`,
  `QuadraticBezierDrawing`, `CubicBezierDrawing`, `PathDrawing`,
  `RegularPolygonDrawing`, `PolygonalDrawing`, and `CircleDrawing`.
- Drawing groups materialize to SVG and PDF component groups directly, and to
  DXF through `DXFDocument`.
- `ZoningDrawing`: Renderer-neutral zoning overlay recipe.

## Document Outputs (`InkGen.document_outputs`)

- `FlowDocument`: Ordered flow document exporter for paragraphs, tables, and
  drawing primitive groups.
- `DocumentOutputFormat`: Supported document output labels.
- Formats currently implemented: DOCX, HTML, RTF, and plain text. DOCX uses
  native WordprocessingML tables and VML drawing groups so no additional document
  library dependency is required.

## Grammar Truth (`InkGen.grammar_truth`)

- `GrammarTruthAnnotation`: Registry-agnostic condition label attached to a
  document, component group, or component.
- `GrammarTruthRecord`: Emitted scorer record with rendered PDF coordinates.
- `annotate_grammar_truth()`: Adds condition truth for `cue`, `construct`,
  `link`, or `assessment` records.
- `DocumentPDF.grammar_truth()`: Emits deterministic records using
  `pdf_points_bottom_left` coordinates. Whole-document assessments use
  `page: 0` and `bbox: None`.

## DXF Output (`InkGen.dxf_generator`)

- `DXFDocument`: ASCII DXF exporter for renderer-neutral drawing groups.
- `DXFRenderContext`: Coordinate conversion settings for DXF output.
- Circles export as `CIRCLE`; other supported linework, curves, polygons, and
  paths export as `LINE`, `TEXT`, or sampled `LWPOLYLINE` entities.

## CAD Component Groups (`InkGen.cad_component_groups`)

- `Zoning`: Grid layout utility for engineering drawings.

## Utilities (`InkGen.svg_utils`)

- `FlattenedPath`: Dataclass representing flattened path results.
- `flatten_svg()`: Converts SVG files into flattened path data.

## Usage Patterns

### Creating a Simple Drawing

```python
from InkGen.boundary import Canvas
from InkGen.document import Document, Layer
from InkGen.style import DrawingStyle
from InkGen.svg_generator import DocumentSVG, RectangleSVG, ComponentGroupSVG

# Create a canvas (A4 size in millimeters)
canvas = Canvas(width=210, height=297, units="mm")

# Create a document
document = Document(canvas)

# Create a document page
document.add_page()
layer = document.page(1).layer("base")

# Create a style
style = DrawingStyle(
    name="outline",
    stroke="#000000",
    stroke_width=0.5,
    fill="none"
)

# Create a rectangle component
rect = RectangleSVG(
    position=(10, 10),
    width=100,
    height=50,
    corner_radii=0,
    style=style
)

# Group components
group = ComponentGroupSVG("MyGroup")
group.add_component(rect)

# Add to layer
layer.add_component_group(group)

# Generate SVG
doc_svg = DocumentSVG(canvas)
doc_svg.add_page()
doc_svg.page(1).layer("base").add_component_group(group)
doc_svg.create_svg("output.svg")
```

### Working with Text

```python
from InkGen.style import TextStyle, Font
from InkGen.svg_generator import TextSVG

# Create a text style
font = Font(family="Arial", size=12)
text_style = TextStyle(name="body", font=font)
text_style.color = "#000000"

# Create text component
text = TextSVG(
    text="Hello, InkGen!",
    position=(50, 50),
    style=text_style
)
```

### Building Tables

```python
from InkGen.table import Table, AutoFitRule
from InkGen.svg_generator import TableSVG

# Create a table
table = Table(position=(10, 10))
table.add_column(width=50.0)
table.add_column(width=100.0)
table.add_row(height=15.0)

# Add content
table.cell(0, 0).add_paragraph("Header 1")
table.cell(0, 1).add_paragraph("Header 2")

# Convert to SVG
border_style = DrawingStyle("border", stroke="#000", stroke_width=0.5, fill="none")
table_svg = TableSVG.from_table(
    table,
    border_style=border_style,
    text_styles={"default": text_style}
)
```

For more detailed examples, see the [Examples](examples.md) section.
