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

P3 additionally renders visible, single-line `TextDrawing` values. The text
position is a baseline anchor: `start`, `center`, and `end` alignment map to
left, middle, and right baseline anchors. Font size is interpreted in points
and converted with `dpi * supersample / 72`, independently of whether canvas
coordinates use inches or millimeters. The existing cross-platform
`Font.font_file` resolver supplies the exact installed font file. Empty,
invisible, and `none`-colored text are transparent no-ops.

P3 rejects multiline text, nonzero character spacing, superscript, and
subscript rather than silently dropping those semantics. Font-load failures
raise a raster-specific `ValueError`. Glyph shape and byte determinism are
scoped to the same resolved font file and Pillow runtime; cross-platform font
substitution and complex-script equivalence are not claimed.

P4 additionally renders open `ArcDrawing` strokes by reusing the canonical
`Arc.points` sequence already consumed by PDF and DXF. Forward, reverse, and
rotated elliptical spans preserve sample order. Visible fills fail explicitly
because they would close the open arc with an implicit chord. Transparent
fills remain valid, and zero-span or unpainted arcs are transparent no-ops.

P5 additionally renders stroke-only `PathDrawing` values containing `M`, `L`,
`H`, `V`, and `Z` commands. Multiple subpaths remain independent, `H` and `V`
inherit the current orthogonal coordinate, and `Z` paints an explicit segment
to the current subpath's starting point. Empty and move-only paths are
transparent no-ops. A command after `Z` must begin a new subpath with `M`.
Visible path fills and nonlinear `C`, `S`, `Q`, `T`, and `A` commands fail
before surface allocation rather than receiving approximate semantics.

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

The renderer deliberately rejects nonlinear path commands, visible path fills,
zoning overlays, rounded corners, gradients, dashed strokes, unsupported
stroke controls, and text presentation outside the P3 domain. Later slices can
add these features without weakening the closed-domain behavior. The Baird
composition API below consumes `RasterRenderResult.asset` without a PDF or SVG
intermediary.

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
