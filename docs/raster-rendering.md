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

- `RectangleDrawing` without a gradient (rounded corners are added by P8);
- `LineDrawing` with a solid stroke;
- `CircleDrawing`;
- `PolygonalDrawing`;
- `RegularPolygonDrawing` (rounded corners are added by P9); and
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

P3 rejects nonzero character spacing, superscript, and subscript rather than
silently dropping those semantics. Font-load failures raise a raster-specific
`ValueError`. Glyph shape and byte determinism are scoped to the same resolved
font file and Pillow runtime; cross-platform font substitution and complex-
script equivalence are not claimed.

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
Visible path fills and nonlinear commands fail before surface allocation
rather than receiving approximate semantics.

P6 additionally renders `C`, `S`, `Q`, and `T` as sampled stroke segments.
Each cubic or quadratic segment reuses the same deterministic 33-point neutral
sampler as the standalone Bezier primitives. Multiple complete groups in one
command are supported. `S` and `T` reflect the previous applicable control;
linear commands, opposite curve families, closure, and a new subpath reset that
state. Empty `C`, `S`, and `Q` commands are no-ops, while incomplete groups and
an empty `T` fail before allocation.

P7 additionally renders absolute SVG endpoint-arc `A` commands. Arc parameters
come from the command's optional `flags` mapping: `radii`, `rotation`,
`large_arc`, and `sweep`. The last command point is the endpoint, matching the
existing SVG and PDF serialization contract. The renderer applies SVG radius
correction and a chord-derived, flag-selected sweep, then reuses the canonical
`Arc` sampler. Ordinary spans use 33 points; a sub-resolution small span uses
its exact two endpoints so the path current point is preserved. Negative radii
are treated as absolute values, either zero radius produces a line segment, and
equal endpoints add no segment. Malformed flags or non-finite derived geometry
fail before surface allocation.

P8 additionally renders `RectangleDrawing` values with scalar or asymmetric
elliptical corner radii. The existing neutral radius contract requires
nonnegative finite values no greater than half the rectangle width and height.
Each rounded corner is painted as a quarter ellipse joined to horizontal and
vertical cardinal edges. A zero horizontal or vertical radius preserves sharp
rectangle semantics. Positive logical radii that cannot occupy a positive
half-width and half-height in the target pixel grid also use the sharp pixel
path rather than constructing invalid Pillow boxes. Live radius mutation is
revalidated before surface allocation.

P9 additionally renders rounded `RegularPolygonDrawing` values. The shared
component geometry constructs a circle tangent to both incident edges at every
vertex, with the requested `corner_radius`. The legal half-circumradius bound
guarantees adjacent tangent points do not cross. Raster and DXF consume the
same deterministic outline whose circular samples are at most 22.5 degrees
apart; SVG emits native circular arcs and PDF emits tangent cubic segments from
the same corner records. Zero radius preserves the established sharp paths.
Malformed live polygon geometry fails before raster surface allocation.

P10 additionally renders rectangle `LinearGradientFill` values. Every
supersampled pixel center is projected onto the existing full-coverage neutral
axis, clamped to `[0, 1]`, and interpolated between the surrounding extended
stops in sRGB channel space. Gradient paint replaces the style's solid fill;
the existing `fill_opacity`, rounded-corner clip, and separately painted stroke
remain authoritative. Off-canvas clipping does not renormalize the gradient
axis. NumPy evaluates at most 1,000,000 pixels per tile, and Pillow performs
masking and source-over composition. Live mutable gradient payloads and
nonrepresentable derived axes fail before surface allocation.

P11 additionally renders multiline `TextDrawing` values. CRLF, CR, and LF are
normalized through the shared neutral line contract, including empty and
trailing lines. Every line uses the same baseline anchor and x coordinate; its
y coordinate advances by the requested font size, physical point scale, and
`TextStyle.line_spacing`. Live non-string text and nonnumeric, non-finite, or
negative spacing fail before surface allocation. Zero spacing intentionally
overlaps baselines.

P13 additionally renders dashed `LineDrawing` strokes. Dash lengths and phase
remain in logical canvas units, odd-length arrays repeat once to form an even
pattern, and phase wraps modulo the pattern period. Zero-length slots are
valid when another slot is positive. A zero-length dashed line is a transparent
butt-cap no-op. More than 100,000 positive pattern steps fails before
surface allocation. Dash arrays on other primitives and a phase without an
array remain outside the closed domain.

P18 additionally renders dashed `PathDrawing` strokes. Dash distance continues
across every source segment in one subpath, while each `M` subpath reapplies the
configured phase. Bezier and arc samples contribute measured length and local
tangents without becoming source joins. A source vertex strictly inside an
on-dash receives its configured join; a vertex at a dash boundary receives
separate dash caps. Closed paths join a dash across the `Z` seam only when the
first and final on-portions are continuous, and a dash covering the full closed
cycle receives joins without caps. Positive and zero-length dash work across
all subpaths shares the 100,000-operation pre-allocation bound.

Fill and stroke colors, widths, and independent opacity values are preserved.
Paths support solid fills under the SVG/PDF nonzero winding rule, including
implicit closure, nested holes, self-intersections, curves, and off-canvas
clipping. Filled-path strokes are source-over composited after their fill.
Raster `LineDrawing` supports `butt`, `round`, and `square` caps for solid and
dashed strokes. Round and square geometry is applied to every positive dash
and to zero-length on-dashes, so `(0, gap)` patterns produce bounded dotted
lines. A zero-length butt line is transparent, a round line is a centered
circle, and a square line is a centered square with a deterministic horizontal
tangent fallback. Sharp rectangles, irregular polygons, regular polygons, and
source-command path vertices support `miter`, `round`, and `bevel` stroke
joins. Join selectors are neutral for lines, circles, and already-rounded
outlines. `PathDrawing` retains source segment endpoints separately from
Bezier and arc tessellation points, so sampled points provide local tangent
directions but do not become joins. Open path subpaths support `butt`, `round`,
and `square` caps at the two subpath ends; `Z`-closed subpaths join their seam
and ignore cap selectors. Nondefault positive finite miter limits apply to
sharp rectangles, polygons, and semantic path vertices: a corner whose
miter-to-half-width ratio exceeds the limit falls back to a bevel. The default
limit of 10 preserves the established Pillow path, and limits are neutral for
round/bevel joins and geometry without sharp joins. Standalone sampled arc and
Bezier primitives still reject non-miter joins and nondefault miter limits.
Caps on other primitives also remain outside the closed domain. Components
paint in group order with source-over alpha compositing. The output remains
RGBA even when a fully opaque background is supplied.

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

The renderer deliberately rejects zoning overlays, dashed strokes outside the
line and path domains, non-butt caps outside line and path domains, non-miter
joins and nondefault miter limits on standalone sampled curves, and text
presentation outside the P3/P11 domain.
Later slices can add these features without weakening the closed-domain
behavior. The Baird composition API below consumes
`RasterRenderResult.asset` without a PDF or SVG intermediary.

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

## End-to-End PDF Fixture

`build_raster_baird_pdf_fixture()` provides a reusable integration fixture that
contains neutral text and vector geometry, partial alpha, canvas-edge clipping,
an explicit colored substrate, deterministic Baird degradation, and terminal
PDF image embedding:

```python
from InkGen import build_raster_baird_pdf_fixture

fixture = build_raster_baird_pdf_fixture(seed=19)
clean_png = fixture.scan.clean.asset.data
degraded_png = fixture.scan.degraded.asset.data
pdf_bytes = fixture.document.to_pdf_bytes()
manifest = fixture.manifest
```

The PDF contains one opaque image XObject and no live text. It is a terminal
container for the degraded asset, not an input or intermediary for rasterizing
the source drawing. Canvas clipping is exercised by the fixture; arbitrary
user-defined raster clip windows remain outside this contract.
