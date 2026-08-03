# ADR-0034: Dependency-Free Raster Renderer

## Status

Accepted for `RASTER-RENDERER-P1`.

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

## Dependencies And Contracts

| Dependency | Consumed contract | Failure if changed |
|---|---|---|
| `drawing_components.py` | Neutral primitive geometry, style ownership, and group order | Geometry or ordering renders incorrectly |
| `boundary.py` | Positive canvas dimensions and normalized `mm`/`in` units | Physical pixel dimensions become incorrect |
| `style.py` | Normalized RGB colors, opacity, and stroke width | Paint differs from SVG/PDF semantics |
| `image_assets.py` | EXIF-normalized decoded pixels and alpha metadata | Embedded image orientation or transparency changes |
| Pillow | RGBA source-over compositing, supersampled drawing, LANCZOS reduction, deterministic PNG encoding | Pixel evidence changes across backend versions |

The dependency direction is one-way: `raster_renderer.py` consumes neutral
recipes and image assets. Neutral primitives, PDF, SVG, DXF, and document
outputs do not depend on the raster renderer.

## Consequences

- InkGen can produce clean in-memory raster fixtures without PDF round-trips.
- Transparent and colored-background fixtures are explicit and testable.
- Physical resolution is tied to canvas units and DPI.
- Unsupported rendering cannot silently approximate the source drawing.
- Later text, curve, path, clipping, and Baird-composition slices can extend a
  proven boundary without changing existing output-format dispatch.

## Alternatives Rejected

- **Render PDF with PyMuPDF:** violates standalone ownership and adds a PDF
  reader to a generation path.
- **Render SVG with CairoSVG or a browser:** adds a dependency and makes SVG a
  runtime intermediary.
- **Add `RASTER` to `OutputFormat` immediately:** changes every neutral
  primitive contract before a complete raster domain exists.
- **Flatten to white:** destroys source alpha and prevents colored-substrate
  fixtures.
