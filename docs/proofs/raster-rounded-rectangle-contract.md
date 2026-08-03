# Raster Rounded Rectangle Contract Proof

Condition: `RASTER-ROUNDED-RECT-P8`.

## Claim

For every validated `RectangleDrawing` in the P8 domain, the standalone raster
renderer paints the same sharp-or-elliptically-rounded geometry selected by the
neutral `corner_radii` contract, preserves fill and stroke paint independently,
and can pass the clean RGBA result directly to Baird without PDF or SVG.

## Domain

- The rectangle has finite nonnegative position, width, and height.
- `corner_radii` is a scalar or `(rx, ry)` pair accepted by
  `normalize_rectangle_corner_radii()`.
- `0 <= rx <= width / 2` and `0 <= ry <= height / 2`.
- The style is in the existing raster solid-stroke domain and the rectangle has
  no gradient.
- The canvas, DPI, supersampling, background, group, and memory bounds satisfy
  `RASTER-RENDERER-P1`.
- Rounded regular polygons, gradients, dashes, and unsupported stroke controls
  remain outside this slice.

## Dependency And Contract Review

- Incoming: `render_drawing_group()` and
  `render_and_degrade_drawing_group()` consume neutral rectangle recipes in
  group order.
- Outgoing: `raster_renderer.py` consumes the shared
  `normalize_rectangle_corner_radii()` contract, normalized `DrawingStyle`
  paint, Pillow drawing primitives, and the existing Baird public asset bridge.
- Cross-backend: SVG uses `rx` and `ry`, PDF uses four cubic elliptical corner
  approximations, and DXF uses sampled quarter ellipses. P8 preserves that
  horizontal/vertical radius meaning in pixels.
- Architecture: no neutral primitive, output-format enum, serializer, import
  direction, or dependency manifest changes.
- ADR consistency: ADR-0034 requires direct neutral rendering and prohibits a
  serialized intermediary or added rasterizer dependency. P8 follows it.

## Mathematical Proof

Let the scaled pixel box be `[l, r] x [t, b]`, with positive pixel radii `a`
and `c` satisfying

```text
0 < a <= (r - l) / 2
0 < c <= (b - t) / 2.
```

The four corner centers are

```text
(l + a, t + c), (r - a, t + c),
(r - a, b - c), (l + a, b - c).
```

At each center P8 paints the relevant quarter of

```text
((x - center_x) / a)^2 + ((y - center_y) / c)^2 <= 1.
```

It also paints the horizontal interior rectangle
`[l + a, r - a] x [t, b]` and the vertical interior rectangle
`[l, r] x [t + c, b - c]`. Their union with the four quarter-disks is exactly
the axis-aligned rectangle after each corner has been replaced by the stated
quarter ellipse: the interior strips cover every non-corner point, and each
remaining corner quadrant is included exactly when it satisfies the ellipse
inequality.

The stroked boundary is the union of four cardinal segments between adjacent
ellipse tangency points and four quarter-ellipse arcs. Every segment endpoint
is also an arc endpoint. The ellipse tangent is horizontal at its top and
bottom cardinal points and vertical at its left and right cardinal points, so
the joined boundary has no direction discontinuity.

Logical coordinates are mapped by the established supersampled scale. A
positive logical radius is rounded to at least one pixel and then bounded by
half the rounded pixel extent. This proves the four ellipse boxes stay inside
the scaled rectangle. If either logical radius is zero, or either rounded pixel
extent has no positive half-radius, P8 uses the existing sharp rectangle path.
No invalid or inverted corner box reaches Pillow.

Fill operations run before stroke operations on one transparent component
layer. That layer is then source-over composited by P1, so P8 does not change
the established group-order or alpha equations.

## Comprehensiveness Matrix

| Domain class | Handling | Evidence |
|---|---|---|
| Scalar radius | use equal horizontal and vertical radii | public pixel test |
| Asymmetric pair | use independent quarter-ellipse axes | exact Pillow-call test |
| Half-width/half-height boundary | produce a capsule/ellipse boundary | boundary pixel test |
| Either logical radius zero | use exact sharp rectangle path | exact fallback test |
| Positive subpixel radii | clamp only when a rounded pixel box is representable | subpixel fallback test |
| Thin positive radius on a representable box | preserve a one-pixel rounded radius | exact pixel-radius mapping test |
| Fill and stroke together | paint interior, edges, and arcs in order | exact call sequence |
| Stroke only | omit all fill operations | independent paint test |
| Fully unpainted | emit no rounded helper operations | independent paint test |
| Semi-transparent fill | preserve P1 source-over compositing | colored-background test |
| Malformed live radii | reject before surface allocation | live-mutation failure test |
| Public clean-to-Baird path | emit clean and degraded assets | integration test |
| Gradient or unsupported stroke | remain rejected | retained P1 conditions |

## Test Applicability

| Test class | Status | Reason |
|---|---|---|
| Unit and condition | Applicable | pixel mapping and paint dispatch changed |
| Failure mode | Applicable | malformed live radii reject before allocation |
| Integration/live path | Applicable | public clean-to-Baird composition is exercised |
| Contract/regression | Applicable | P1 and cross-renderer radius contracts remain in the gate |
| Property/partition | Applicable | scalar, pair, boundary, zero, and subpixel partitions are explicit |
| Mutation | Applicable | geometry arithmetic and paint branches are proof-critical |
| Security/adversarial | Not applicable | no files, active content, or external process input is added |
| Performance/resource | Applicable | each rounded rectangle emits a fixed fourteen Pillow operations at most |
| Golden/visual | Not applicable | exact calls and selected output pixels prove this primitive slice |
| Concurrency | Not applicable | painting owns a per-component layer and no shared mutable state |

## Verification Status

- PASS: the exact staged focused gate completed with `47 passed` across the P8,
  retained P1, and clean-to-Baird contract files.
- PASS: the complete raster-family gate completed with `190 passed`, and the
  standalone Baird family completed with `46 passed` in a fresh process.
- PASS: the exact staged full regression completed with `2143 passed`.
- PASS: the working-copy full regression completed with `2157 passed`; combined
  statement/branch coverage is `97%`, and `raster_renderer.py` has `100%`
  statement and branch coverage (`453` statements and `222` branches).
- PASS: the isolated Cosmic Ray campaign completed all `243` selected work
  items: `238` were killed and `5` were proved equivalent, for `97.94%` raw and
  `100%` effective mutation coverage, with no worker errors or timeouts.
- PASS: Ruff lint and format checks, Python bytecode compilation, strict MkDocs,
  the evidence-hash correlation check, and `git diff --cached --check` passed.
- PASS: the source SHA-256 is
  `CA5DA2D23C97BB9B0B349E4A6F922A24D05842B63BC0505DB60BC161BA591D64`;
  the mutation manifest records correlated source, test, configuration, and
  filter hashes.
- NOT APPLICABLE: InkGen has no `.pre-commit-config.yaml`, Clarvis structural
  checker, or Clarvis traceability script to run locally for this slice.
