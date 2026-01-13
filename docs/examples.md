# Examples

This section complements the runnable scripts in the `examples/` directory with annotated walkthroughs. Each example generates SVG output in `examples/output/`.

## 1. `run_inkgen.py`

This script demonstrates a full drawing assembly that includes:

- Core shapes (`RectangleSVG`, `CircleSVG`, `RegularPolygonSVG`)
- Text-fitting examples with `TextFitter`
- Embedded SVG artwork via `SVGComponent`
- Zoning overlays, callouts, and annotation polygons
- Table generation with `TableSVG`

### Key Steps

1. Create a `DocumentSVG` bound to a canvas.
2. Instantiate drawing components and add them to `ComponentGroupSVG` instances.
3. Use helper functions to fit text into complex shapes.
4. Add zoning and annotation layers.
5. Save the document as both YAML (`test_document.yaml`) and SVG (`test1.svg`).

### Preview

```bash
python examples/run_inkgen.py
python -m webbrowser examples/output/test1.svg  # Opens the SVG in your default browser
```

> Tip: check `examples/output/` after running the script to inspect the generated YAML recipe and SVG assets.

## 2. `run_inkgen_primitives.py`

Produces a primitives showcase that highlights each drawing component together with a label describing key parameters.

- Demonstrates `RectangleSVG`, `CircleSVG`, `LineSVG`, `PolygonalSVG`, `RegularPolygonSVG`, `ArcSVG`, `QuadraticBezierSVG`, `CubicBezierSVG`, and `PathSVG`.
- Exports a base SVG plus a mask SVG for segmentation tasks.

```bash
python examples/run_inkgen_primitives.py
```

Outputs:

- `examples/output/inkgen_primitives_showcase_base.svg`
- `examples/output/inkgen_primitives_showcase_mask.svg`

## 3. `test_svg_drawing.py`

Illustrates a structured drawing complete with revision tables, bill of materials, callouts, and free text blocks.

- Demonstrates programmatic layer management with `DocumentSVG`.
- Shows how to reuse helper functions for text style and baseline calculations.

```bash
python examples/test_svg_drawing.py
```

Output: `examples/output/test_svg_draw.svg`

## Understanding the Output

Each example script generates multiple artifacts:

1. **SVG Files**: The primary output, viewable in browsers or vector editors
2. **YAML Files**: Serialized document recipes that can be reloaded and modified
3. **Mask SVGs**: Segmentation masks for machine learning workflows (when applicable)

### Inspecting Generated SVGs

Open SVG files in:
- **Web browsers**: For quick previews
- **Inkscape**: For detailed inspection and editing
- **Vector editors**: Adobe Illustrator, Affinity Designer, etc.

### Working with YAML Recipes

YAML files contain the complete document structure:

```yaml
Document:
  canvas:
    width: 210
    height: 297
    units: mm
  pages:
    - Layers:
        layers:
          base:
            Layer:
              name: base
              canvas: ...
              component_groups: ...
```

You can:
- Edit YAML files to modify document structure
- Load YAML files programmatically to recreate documents
- Version control document templates
- Generate variations of drawings from templates

## Suggested Experiments

### Customizing Styles

Modify the margins, zone counts, and callouts in `run_inkgen.py` to match your house style:

```python
# Change zoning parameters
zoning = Zoning(
    canvas,
    line_style=zoning_style,
    text_style=zoning_text,
    margins=10,  # Increase margins
    horizontal_zones=12,  # More zones
    vertical_zones=10,
)
```

### Using Custom Fonts

Replace the example font paths with custom fonts and verify text layout:

```python
# Use a custom font
font = Font(
    family="MyCustomFont",
    size=12,
    custom_font_paths=["/path/to/my/font.ttf"]
)
```

### Extending Component Coverage

Integrate additional component types (e.g., arcs, bezier curves) into the base example:

```python
# Add an arc
arc = ArcSVG(
    point_1=(0, 0),
    point_2=(100, 50),
    radius=60,
    large_arc=False,
    sweep=True,
    style=style
)
group.add_component(arc)
```

### Creating Multi-Page Documents

Build documents with multiple pages:

```python
document = Document(canvas)
document.add_page()  # Page 1
document.add_page()  # Page 2

# Add different content to each page
document.page(0).add_layer("title", title_layer)
document.page(1).add_layer("content", content_layer)
```

## Automation and Testing

The examples can serve as integration tests to ensure regressions are caught automatically. While the examples are primarily for demonstration, you can:

1. Run examples and verify output files exist
2. Compare generated SVG structure against expected patterns
3. Validate YAML serialization/deserialization round-trips

This keeps the example output in sync with the code and acts as smoke testing for the rendering pipeline.
