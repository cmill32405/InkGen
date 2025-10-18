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

## Suggested Experiments

- Modify the margins, zone counts, and callouts in `run_inkgen.py` to match your house style.
- Replace the example font paths with custom fonts and verify text layout.
- Integrate additional component types (e.g., arcs, bezier curves) into the base example to extend coverage.

## Automation

Consider scripting the examples as integration tests to ensure regressions are caught automatically. For instance:

```bash
pytest examples --maxfail=1 --disable-warnings -q
```

This keeps the example output in sync with the code and acts as smoke testing for the rendering pipeline.
