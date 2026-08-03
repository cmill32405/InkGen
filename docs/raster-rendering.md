# Raster Rendering

InkGen can render a closed set of renderer-neutral drawing primitives directly
to an in-memory RGBA PNG without creating or rereading a PDF. The backend uses
Pillow, which is already an InkGen runtime dependency.

```python
from InkGen import Canvas, DrawingComponentGroup, RasterRenderResult
from InkGen import RectangleDrawing, DrawingStyle, render_drawing_group

style = DrawingStyle("box", stroke="#000000", fill="#ffffff", stroke_width=0.2)
group = DrawingComponentGroup("fixture", [RectangleDrawing((10, 10), 40, 20, 0, style)])
result: RasterRenderResult = render_drawing_group(
    group,
    Canvas(210, 297, "mm"),
    dpi=300,
    supersample=2,
)
asset = result.asset
```

The canvas keeps InkGen's top-left, y-down coordinate system. Inch canvases
use `dpi` pixels per unit. Millimeter canvases use `dpi / 25.4` pixels per
unit. Output dimensions are rounded once after physical conversion.

## P1 Rendering Domain

P1 renders these neutral primitives:

- `RectangleDrawing` with square corners and no gradient;
- `LineDrawing` with a solid stroke;
- `CircleDrawing`;
- `PolygonalDrawing`;
- `RegularPolygonDrawing` without rounded corners; and
- `ImageDrawing`, including source alpha.

P2 additionally renders open `QuadraticBezierDrawing` and
`CubicBezierDrawing` strokes. Both consume InkGen's established 33-point curve
samples and are painted as supersampled polylines. Visible fills on these open
curves fail explicitly rather than silently closing the geometry.

Fill and stroke colors, widths, and independent opacity values are preserved.
P1 supports solid strokes with butt caps, miter joins, the default miter limit,
and zero dash offset. Other cap, join, miter-limit, dash, or dash-offset values
fail explicitly rather than being approximated. Components paint in group order
with source-over alpha compositing. The output remains RGBA even when a fully
opaque background is supplied.

The default output is transparent. Supply `background_rgba=(r, g, b, a)` only
when a specific substrate is part of the fixture contract. InkGen does not
silently flatten transparent drawings to white.

## Determinism And Limits

Identical supported inputs under the same Pillow version produce identical PNG
bytes. The result manifest records canvas geometry, units, DPI, supersampling,
background, output dimensions, and component count.

The supersampled working surface is limited to 64,000,000 pixels and the
supersampling factor is limited to 1 through 8. Invalid or unsupported inputs
fail before surface allocation.

The renderer deliberately rejects text, arcs, paths, zoning overlays, rounded
corners, gradients, dashed strokes, and unsupported stroke controls.
Later slices will add these features without weakening the closed-domain
behavior. The Baird composition API below consumes `RasterRenderResult.asset`
without a PDF or SVG intermediary.

## Baird Composition

`render_and_degrade_drawing_group()` returns both the clean transparent render
and its Baird-degraded opaque scan:

```python
from InkGen import BairdParams, render_and_degrade_drawing_group

scan = render_and_degrade_drawing_group(
    group,
    Canvas(210, 297, "mm"),
    BairdParams.sample(rng),
    seed=42,
    background_rgb=(245, 248, 250),
    dpi=300,
)
clean_asset = scan.clean.asset
degraded_asset = scan.degraded.asset
```

`background_rgb` is required and has no implicit white default. It is the
physical substrate used when Baird converts the clean RGBA asset to its opaque
scan domain. `RasterBairdResult.manifest` nests the complete render and
degradation manifests so the output can be reproduced.
