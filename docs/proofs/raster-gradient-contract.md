# Raster Linear-Gradient Contract Proof

Condition: `RASTER-GRADIENT-P10`.

## Claim

For every valid rectangle `LinearGradientFill`, the standalone raster renderer
samples the same neutral full-coverage axis and extended stops as SVG/PDF,
preserves fill opacity and explicit alpha, clips to sharp or
elliptical-rounded rectangle geometry, paints the stroke separately, and keeps
temporary interpolation grids bounded independently of canvas aspect ratio.

## Pre-Change Dependency And Contract Review

- Incoming: `RectangleDrawing.fill_gradient` stores a mutable canonical payload;
  public raster rendering and Baird composition consume the neutral recipe.
- Outgoing: `raster_renderer.py` consumes `LinearGradientFill.axis_for_box()`
  and `extended_stops()`, NumPy array interpolation, Pillow masks, and Pillow
  source-over composition.
- Dependents: direct raster fixtures and `render_and_degrade_drawing_group()`.
- Serialized SVG/PDF/DXF/document outputs are unchanged. DXF continues to
  reject gradients, and SVG/PDF retain native parametric paint resources.
- No package dependency or public API is added. NumPy and Pillow are existing
  required InkGen dependencies.
- ADR review found no contradiction: ADR-0029 rejects replacing parametric
  SVG/PDF gradients with raster bands; P10 samples pixels only when raster
  output is explicitly requested.

## Mathematical Proof

Let the neutral axis be `a -> b`, with `d = b - a`. The established gradient
proof establishes `||d|| > 0` and that every rectangle point projects between
the axis endpoints. For a supersampled pixel center `p`, P10 computes

```text
t(p) = clamp(((p - a) dot d) / (d dot d), 0, 1).
```

This is the scalar coefficient of the orthogonal projection onto the axis.
At `p = a`, `t = 0`; at `p = b`, `t = 1`. Linearity of the dot product makes
`t` monotone along the requested direction. Canvas clipping only changes the
set of evaluated points, not `a`, `b`, or `t`, so an off-canvas rectangle
cannot be renormalized.

Let consecutive extended stops be `(u0, c0)` and `(u1, c1)` with
`u0 <= t <= u1`. Stop validation proves `u1 > u0`. Each sRGB byte channel is

```text
c(t) = round(c0 + (c1 - c0) * (t - u0) / (u1 - u0)).
```

`numpy.interp` implements that piecewise linear expression and endpoint
extension, after which `numpy.rint` applies the declared nearest-byte
quantization. The alpha channel is independently `round(fill_opacity * 255)`.
Therefore solid style RGB cannot leak into gradient pixels, while the style's
fill opacity remains authoritative.

The P8 sharp/rounded mask is `1` exactly on the rectangle fill domain and `0`
outside it. Assigning the gradient alpha through that mask clips paint without
changing RGB interpolation. Stroke painting occurs after the clipped gradient,
using the established rectangle boundary. Thus fill clipping and stroke
geometry remain independent.

The image intersection is partitioned into tiles with width at most
`_GRADIENT_TILE_PIXELS` and height
`max(1, floor(_GRADIENT_TILE_PIXELS / width))`. Every non-final tile therefore
contains at most the configured number of pixels, and final tiles contain no
more. Pixel coordinates are global, so changing tile boundaries cannot change
`t(p)` or output bytes.

## Comprehensiveness Matrix

| Domain class | Required result | Evidence |
|---|---|---|
| 0/90/180/270 degrees | visual CCW direction | cardinal parameter test |
| Oblique axis | monotone projected interpolation | tile/determinism test |
| Two and N stops | piecewise sRGB interpolation | cardinal and N-stop tests |
| Missing endpoint stops | extend first/last colors | N-stop endpoint test |
| Style solid fill present | gradient RGB overrides it | opacity test |
| Partial fill opacity | preserve unflattened alpha | opacity test |
| Elliptical rounded corners | clip fill, retain stroke | rounded mask test |
| Off-canvas rectangle | retain full source axis | clipping test |
| Small tile limit | identical PNG and bounded tile size | partition test |
| Mutable malformed payload | fail before allocation | hostile live-mutation test |
| Derived axis overflow | fail before allocation | finite-length failure test |
| Baird composition | clean alpha uses explicit substrate | integration test |

## Test Applicability

Unit, condition, failure-mode, property-partition, integration, live-path,
pixel, determinism, resource-bound, coverage, and mutation checks apply.
Concurrency, network, active-content, and external-I/O checks do not apply.

## Mutation Gate

Cosmic Ray 8.4.6 generated 3,186 candidates from the final raster module. The
proof-critical filter retained 311 work items covering live validation, the
gradient rectangle render branch, finite-axis guards, projection,
interpolation, clipping, tiling, masking, opacity, and composition. Isolated
WSL execution completed every item without worker errors or timeouts: 298 were
killed and 13 survived.

All 13 survivors are equivalent in the validated domain:

- nonnegative logical and pixel radii make `> 0`/`!= 0` and `== 0`/`<= 0`
  identical;
- a finite sum of squares is nonnegative, so `<= 0` and `== 0` are identical;
- the alpha byte is in `[0, 255]`, making `== 0` and `<= 0` identical;
- `numpy.interp` already extends endpoint colors, so wider preceding clip
  limits do not change interpolation;
- Pillow mode `L` maps both zero and minus one constructor fills to byte zero;
  and
- rounded-mask calls with `stroke=None` never read `stroke_width`.

The job IDs, exact source/test/config/filter/database hashes, late-kill
witnesses, and individual proofs are recorded in
`tests/mutation/raster_gradient_p10_evidence.json`. Raw mutation coverage is
95.82%; effective coverage after equivalent-mutant proofs is 100%. A final
public docstring correction was outside the mutation filter; the evidence
records identical pre/post AST hashes for all four mutation-scoped definitions
and the final module byte hash.

## Verification Status

- Focused P10 plus dependent raster/gradient contracts: 195 passed.
- Full exact-index regression: 2,213 passed in deterministic shards of 895,
  483, and 835 tests (Clarvis artifacts 9347, 9348, and 9349).
- Raster-family coverage: 338 passed; `raster_renderer.py` has 100% statement
  and 100% branch coverage (Clarvis artifact 9363).
- Mutation: 311/311 work items completed without worker errors or timeouts;
  298 killed and 13 proven equivalent, for 100% effective coverage.
- Mutation evidence certificate and manifest-hash test: passed as part of the
  focused and full suites; the JSON campaign record also parsed successfully.
- Ruff lint and format checks for all changed Python files: passed.
- Python bytecode compilation for the source and new evidence tests: passed.
- MkDocs strict build: passed.
- Exact staged patch whitespace check: passed.
- Dependency manifests: unchanged; the implementation uses the existing
  Pillow and NumPy dependencies.
