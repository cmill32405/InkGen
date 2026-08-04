# ADR-0034: Dependency-Free Raster Renderer

## Status

Accepted for `RASTER-RENDERER-P1`, `RASTER-BAIRD-P1`,
`RASTER-CURVE-P2`, `RASTER-TEXT-P3`, `RASTER-ARC-P4`, and
`RASTER-PATH-P5`, `RASTER-PATH-CURVE-P6`, `RASTER-PATH-ARC-P7`, and
`RASTER-ROUNDED-RECT-P8`, `RASTER-ROUNDED-POLYGON-P9`, and
`RASTER-GRADIENT-P10`, `RASTER-TEXT-MULTILINE-P11`, and
`RASTER-PATH-FILL-P12`, and `RASTER-LINE-DASH-P13`.

## Context

InkGen's standalone Baird implementation accepts a clean raster asset, but the
library could not create that asset from its own neutral drawings without
passing through an external PDF or SVG rasterizer. That prevented a standalone
clean-drawing-to-degraded-scan workflow and encouraged use of PyMuPDF outside
InkGen.

Adding a raster member to `OutputFormat` would expand every neutral primitive's
materialization contract at once. Rendering a concrete SVG or PDF would also
make those serialized formats runtime dependencies of the raster path.

## Decision

Add `raster_renderer.py` as a consumer of neutral `DrawingComponentGroup`
recipes. It accepts an explicit `Canvas`, DPI, supersampling factor, and
optional RGBA background, and returns `RasterRenderResult` containing a
`RasterImageAsset` and deterministic manifest.

P1 is a closed renderer domain. It supports basic rectangles, lines, circles,
polygons, regular polygons, and raster images. Solid strokes use butt caps,
miter joins, the default miter limit, and zero dash offset. Unsupported
primitives or style features fail before allocation. Alpha remains explicit
through the complete render path.

Use Pillow, an existing dependency, for pixel surfaces, compositing, geometric
drawing, image resizing, and PNG encoding. Do not add PyMuPDF, OpenCV, Cairo,
or another rendering library.

Add `render_and_degrade_drawing_group()` as a thin composition of the clean
renderer and `baird_degrade_asset()`. The clean result remains transparent
RGBA. The caller must name the RGB substrate used for the opaque Baird scan;
there is no implicit white background. `RasterBairdResult` retains both result
objects and nests their manifests without duplicating either algorithm.

P2 admits open `QuadraticBezierDrawing` and `CubicBezierDrawing` strokes. The
raster backend consumes the same deterministic 33-point samples already owned
by the neutral component layer and paints them as supersampled polylines.
Visible curve fills remain outside the closed domain and fail explicitly;
silently closing an open curve would change its geometry.

P3 admits visible, single-line `TextDrawing` values with zero character
spacing and no super/subscript transformation. The neutral baseline position
is mapped to Pillow's left, middle, or right baseline anchor. Font points are
converted independently from canvas units with `dpi * supersample / 72`, and
the existing `Font.font_file` resolver supplies the exact installed font file.
Unsupported presentation and font-load failures remain explicit.

P4 admits open `ArcDrawing` strokes. The raster backend consumes the same
deterministic `Arc.points` samples used by PDF and DXF, including rotation and
reverse spans. Visible fills fail explicitly because filling would close the
arc with an implicit chord. Zero-span arcs remain transparent move-only paths.

P5 admits stroke-only `PathDrawing` values containing the linear `M`, `L`,
`H`, `V`, and `Z` commands. Commands are revalidated from the live mutable
collection before surface allocation, expanded into independent subpaths, and
painted through the established open-polyline operation. `Z` contributes the
explicit segment back to the current subpath's starting point. Visible fills
and nonlinear commands fail explicitly until their geometry and fill-rule
semantics are separately owned.

P6 admits the sampled Bezier path commands `C`, `S`, `Q`, and `T`. Cubic and
quadratic segments reuse the established 33-point neutral component samplers.
Smooth commands reflect the previous applicable control around the current
point and reset that state after linear commands, opposite curve families,
closure, or a new subpath. Complete grouped commands may contain multiple
segments; empty `C`, `S`, and `Q` groups are no-ops.

P7 admits absolute SVG endpoint-arc `A` commands. The raster backend validates
the live flag mapping, converts the last command point from SVG endpoint form
to center form, and then reuses the established `Arc` sampler. Ordinary spans
produce its 33-point sequence; sub-resolution small spans use an exact
two-point fallback so the path current point still advances.
Negative radii are normalized to their absolute values, undersized radii are
scaled by the SVG correction rule, a zero radius produces a line, and equal
endpoints produce no segment. Exact path endpoints replace the reconstructed
sampler endpoints after conversion. `A` clears both smooth-control histories.
Visible path fills remain outside the closed renderer domain.

P8 admits `RectangleDrawing` values with validated horizontal and vertical
corner radii. The renderer maps the logical box and radii to the supersampled
pixel domain, paints the fill as two interior rectangles plus four elliptical
quarter-disks, and paints the boundary as four cardinal line segments plus
four quarter-ellipse arcs. If either logical radius is zero, or the rounded
corner cannot occupy a positive pixel radius after scaling, the established
sharp rectangle path is used. Live radii are revalidated before allocation.

P9 admits rounded `RegularPolygonDrawing` values and closes a pre-existing
cross-backend defect: SVG, PDF, and DXF previously validated and serialized
`corner_radius` but emitted sharp vertices. Shared component geometry now owns
the tangent entry/exit points, circle centers, signed corner sweeps, and bounded
arc samples. SVG emits native circular arcs, PDF emits tangent cubic arc
approximations, and DXF and raster consume the same at-most-22.5-degree sampled
outline. A zero radius retains every established sharp backend path. Raster
revalidates live polygon geometry before allocating a surface.

P10 admits `LinearGradientFill` on rectangles. The raster backend consumes the
same neutral full-coverage axis and extended-stop contract as SVG and PDF. It
projects supersampled pixel centers onto that axis and performs piecewise
linear sRGB interpolation in bounded two-dimensional NumPy tiles. Pillow owns
the established sharp or elliptical-rounded mask and source-over composition.
The rectangle's style continues to own fill opacity and its separately painted
stroke. Clipping to the canvas never changes the source axis.

This does not reverse ADR-0029's rejection of rasterizing a gradient as a
substitute for parametric SVG/PDF output. P10 is used only when a caller
explicitly asks the standalone raster renderer for pixels; SVG and PDF retain
their native gradient resources and no renderer uses raster output as an
intermediary.

P11 admits normalized multiline `TextDrawing` values under ADR-0035. The
renderer preserves CRLF/CR/LF line boundaries, empty lines, per-line baseline
alignment, and point-scaled `TextStyle.line_spacing`. Live text and spacing are
validated before surface allocation.

P12 admits solid `PathDrawing` fills under the nonzero winding rule already
used by InkGen's SVG and PDF paths. Every sampled subpath is implicitly closed
for fill without changing its stroke geometry. A bounded scanline active-edge
table evaluates supersampled pixel centers over the path's canvas-clipped
bounding box. Half-open edge intervals prevent shared vertices from being
counted twice; upward and downward crossings contribute opposite winding
deltas. Fill pixels are selected exactly when the accumulated winding is
nonzero. The fill is source-over composited before a separately painted stroke,
so independent fill and stroke opacity remain meaningful. No dependency or
renderer intermediary is added.

P13 admits dash arrays and dash phase for `LineDrawing` only. The raster
backend expands odd arrays once, wraps phase by the positive pattern period,
and partitions the finite neutral segment in logical canvas units before pixel
scaling. Zero-length entries advance without paint. An explicit 100,000-step
operation bound is checked before Pillow allocation. Other primitives retain
the established dash rejection until their closed-outline and subpath phase
continuity contracts are separately proven.

## Dependencies And Contracts

| Dependency | Consumed contract | Failure if changed |
|---|---|---|
| `drawing_components.py` | Neutral primitive geometry, style ownership, and group order | Geometry or ordering renders incorrectly |
| `component.py` | Established curve samples, normalized path commands, rectangle radii, and regular-polygon tangent-circle geometry | Raster curves, paths, or rounded shapes diverge from neutral/PDF/SVG/DXF geometry |
| `style.py` | Validated nonnegative dash arrays, phase, stroke width, opacity, and butt-cap default | Raster line cadence or paint differs from SVG/PDF intent |
| `gradients.py` | Full-coverage axis, ordered extended stops, and normalized sRGB colors | Raster direction, endpoint extension, or interpolation diverges from SVG/PDF intent |
| `boundary.py` | Positive canvas dimensions and normalized `mm`/`in` units | Physical pixel dimensions become incorrect |
| `style.py` | Normalized drawing colors, text colors, font-file resolution, point size, visibility, and alignment | Paint, glyph source, or baseline alignment differs from SVG/PDF semantics |
| `image_assets.py` | EXIF-normalized decoded pixels and alpha metadata | Embedded image orientation or transparency changes |
| `baird.py` | Seeded degradation, explicit alpha substrate, and result provenance | Scan appearance or reproducibility changes |
| Pillow | RGBA source-over compositing, supersampled drawing, LANCZOS reduction, deterministic PNG encoding | Pixel evidence changes across backend versions |
| NumPy | Bounded projection grids and piecewise channel interpolation | Large gradient fixtures become slow or produce different channel rounding |

The dependency direction is one-way: `raster_renderer.py` consumes neutral
recipes, image assets, and Baird's public asset bridge. Neutral primitives,
PDF, SVG, DXF, and document outputs do not depend on the raster renderer.

## Consequences

- InkGen can produce clean in-memory raster fixtures without PDF round-trips.
- Transparent and colored-background fixtures are explicit and testable.
- Physical resolution is tied to canvas units and DPI.
- Unsupported rendering cannot silently approximate the source drawing.
- Clean and Baird-degraded assets can be produced in one standalone call.
- Quadratic and cubic curves reuse established neutral samples without a
  serialized renderer intermediary.
- Single-line text uses the resolved font file and physical point size without
  changing neutral component or output-format dispatch.
- Elliptical arcs preserve shared rotation, direction, and endpoint samples
  without materializing PDF or SVG.
- Linear paths preserve subpath boundaries, axis commands, and explicit
  closure without changing existing output-format dispatch.
- Bezier paths preserve canonical sampling and smooth-control reflection
  without duplicating curve equations in the raster backend.
- Endpoint arcs preserve SVG radius correction, flag-selected sweep, rotation,
  and exact endpoints while reusing the canonical center-arc sampler.
- Rounded rectangles preserve the established elliptical `rx`/`ry` contract
  without routing through SVG, PDF, or DXF.
- Rectangle gradients preserve the neutral axis, N-stop colors, fill opacity,
  rounded clipping, and explicit alpha without using SVG or PDF as an
  intermediary.
- Path fills preserve implicit closure, nested-hole orientation,
  self-intersections, clipping, and independent fill/stroke alpha under the
  SVG/PDF nonzero rule.
- Dashed lines preserve neutral logical lengths, odd-pattern repetition,
  modulo phase, alpha, and deterministic resource bounds.
- Later clipping slices can extend a proven boundary without weakening
  existing rejection contracts.

## Alternatives Rejected

- **Render PDF with PyMuPDF:** violates standalone ownership and adds a PDF
  reader to a generation path.
- **Render SVG with CairoSVG or a browser:** adds a dependency and makes SVG a
  runtime intermediary.
- **Add `RASTER` to `OutputFormat` immediately:** changes every neutral
  primitive contract before a complete raster domain exists.
- **Flatten to white:** destroys source alpha and prevents colored-substrate
  fixtures.
