# Raster Renderer Contract Proof

Condition: `RASTER-RENDERER-P1`.

## Claim

For the declared P1 primitive domain, `render_drawing_group()` produces a
deterministic RGBA PNG with physically scaled geometry, group-order source-over
compositing, preserved image alpha, bounded memory demand, and explicit failure
for unsupported inputs.

## Domain

The domain is a valid `DrawingComponentGroup`, valid `Canvas`, positive finite
DPI, integer supersampling factor from 1 through 8, optional four-channel RGBA
background, and only the primitive/style combinations listed in
`docs/raster-rendering.md`.

## Proof Obligations

| Obligation | Evidence |
|---|---|
| Physical dimensions | Inch and millimeter condition tests |
| Deterministic PNG and manifest | Repeated empty-render byte comparison |
| Transparent default | Empty transparent-canvas pixel assertion |
| Explicit colored substrate | Semi-transparent fill over blue substrate assertion |
| Shape geometry | Rectangle, line, circle, irregular polygon, and regular polygon pixel assertions |
| Image alpha | Semi-transparent PNG remains semi-transparent without white flattening |
| Paint order | Overlapping opaque/transparent rectangles assert source-over result |
| Closed P1 domain | Unknown primitives, non-line dashes, orphan dash phases, caps, joins, and miter-limit variants fail loudly; rounded rectangles, rounded polygons, rectangle gradients, and line dashes are admitted only by their later proofs |
| Mutation-resistant live boundary | Invalid group, mutable component container, and post-construction list mutation tests |
| Resource bound | Excessive supersampled surface fails before allocation |

## Mathematical Proof

Let `d` be DPI and let canvas width `w` be in units `u`. Define

```text
p(u, d) = d              when u = inch
p(u, d) = d / 25.4       when u = millimeter
W = round(w * p(u, d))
```

`Canvas` proves `w > 0`, and the renderer proves `d > 0`, so `W >= 1` after
the explicit lower bound. Every logical coordinate `x` is mapped exactly once
to the supersampled coordinate `round(x * p * s)`, where `s` is the validated
supersampling factor. The final reduction returns exactly `W` pixels. No PDF
page-scale or SVG transform participates, so double scaling is impossible in
this path.

For source pixel `(Cs, As)` over destination `(Cd, Ad)`, Pillow's source-over
operation implements

```text
Ao = As + Ad * (1 - As)
Co * Ao = Cs * As + Cd * Ad * (1 - As)
```

The renderer composites components sequentially in list order. Induction over
the component list therefore establishes that each output pixel is the ordered
source-over composition of the explicit background and every painted
component covering that pixel. A transparent initial background has `Ad = 0`;
there is no white term to introduce implicit flattening.

## Counterexamples And Failure Modes

- Invalid canvas, DPI, supersampling, background, group, and mutable component
  containers fail before rendering.
- The supersampled surface is rejected above 64,000,000 pixels.
- The base P1 domain rejects unknown primitives, zoning, and
  unsupported stroke controls instead of producing a visually plausible
  approximation. Later slices add separately proven curve, text, arc, path,
  rounded-shape, rectangle-gradient, multiline-text, path-fill, and line-dash
  domains.
- Pixel-byte determinism is scoped to a fixed Pillow version and platform.
  Cross-version resampling kernels are not claimed bit-identical.

## Verification Status

- Focused conditions: 33 passed.
- Focused statement and branch coverage: 100%.
- Mutation: 473 selected final-source mutants; 447 killed and 26 exact
  equivalents documented in
  `tests/mutation/raster_renderer_p1_evidence.json`; zero unclassified
  survivors, worker errors, or worker timeouts.
- Full regression from the exact staged snapshot: 2,022 passed.
- Static gates: repository Ruff lint passed; all three touched Python files are
  Ruff-formatted; source compilation and scoped `git diff --check` passed.
- Documentation: source-backed consistency conditions passed and the strict
  MkDocs build completed in a temporary output directory.
- Dependency manifest: unchanged by this slice; the renderer uses the existing
  Pillow dependency and does not add PyMuPDF or another rasterizer.
- Environment advisories: the shared interpreter reports a pre-existing
  `sse-starlette`/`starlette` version mismatch, and optional package-build tools
  `build` and `wheel` are not installed. No dependency was installed or changed
  to mask those environment conditions.
