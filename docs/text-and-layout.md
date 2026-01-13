# Text & Layout

InkGen provides utilities for laying out text, zoning drawings, and managing tabular data. These features sit atop the primitives described earlier and are primarily implemented in the following modules:

- `src/InkGen/text_fitter.py`
- `src/InkGen/text_outline.py`
- `src/InkGen/cad_component_groups.py`
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

## Zoning and CAD Layouts

`cad_component_groups.Zoning` builds grid-based zoning overlays commonly seen on engineering drawings. The zoning component exposes margins, zone width, and label configuration options:

```python
from InkGen.cad_component_groups import Zoning
from InkGen.style import DrawingStyle, TextStyle, Font

zoning_style = DrawingStyle("ZoneLines", stroke="#999", stroke_width=0.2)
zoning_text = TextStyle("ZoneLabels", Font("Arial", weight="bold", size=6))
zoning = Zoning(
    canvas,
    line_style=zoning_style,
    text_style=zoning_text,
    margins=5,
    horizontal_zones=10,
    vertical_zones=8,
)
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

1. Use `Zoning` to draw grid overlays and annotation callouts.
2. Fit descriptive text into complex components with `TextFitter`.
3. Add revision tables or bills of materials using the `Table` API.
4. Render everything through `DocumentSVG`, optionally exporting masks and labels for machine learning pipelines.

See the [Examples](examples.md) section for end-to-end walkthroughs.
