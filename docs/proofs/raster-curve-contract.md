# Raster Curve Contract Proof

Condition: `RASTER-CURVE-P2`.

## Claim

For valid open neutral quadratic or cubic Bezier geometry with a supported
stroke style, the raster renderer consumes InkGen's established 33-point curve
sequence, applies the renderer's deterministic physical pixel transform, and
produces the same clean and Baird-composable RGBA asset for equal inputs.

## Domain

- `QuadraticBezierDrawing` and `CubicBezierDrawing` have finite validated
  geometry.
- Stroke controls satisfy the existing closed raster style domain.
- A visible fill is absent because the neutral curves are open.
- Canvas, DPI, supersampling, background, and runtime satisfy
  `RASTER-RENDERER-P1`.
- Deterministic-byte claims remain scoped to the same Pillow runtime.

## Structural Proof

Let `S(c) = (p0, ..., p32)` be the established sample sequence returned by
InkGen's neutral quadratic or cubic component for curve `c`. The raster backend
does not implement a second Bezier formula. It constructs the corresponding
neutral sampler and reads `S(c)`.

For physical pixel scale `k`, each point is mapped independently by:

```text
T_k(x, y) = (round(k*x), round(k*y))
```

The emitted Pillow polyline is exactly:

```text
(T_k(p0), ..., T_k(p32))
```

Therefore equal curve geometry and equal scale produce equal raster polyline
arguments. `RASTER-RENDERER-P1` proves deterministic ordered compositing and
PNG encoding for those fixed arguments. `RASTER-BAIRD-P1` then proves that the
clean asset remains valid deterministic input to the explicit-substrate Baird
composition.

## Comprehensiveness Matrix

| Domain class | Handling | Evidence |
|---|---|---|
| Valid quadratic stroke | render shared samples | exact dependency-contract test |
| Valid cubic stroke | render shared samples | exact dependency-contract test |
| Clean-to-degraded live path | preserve curve pixels through composition | public scan-path test |
| No visible stroke | transparent no-op | boundary test |
| Painted fill with zero opacity | accept as non-visible | boundary test |
| Visible open-curve fill | reject before allocation | failure-mode test |
| Unsupported dash/cap/join/miter | existing closed-domain rejection | raster P1 tests |
| Malformed/non-finite geometry | neutral constructor rejection | existing Bezier contract tests |
| PDF/SVG intermediary | excluded | source imports and ADR-0034 |

## Verification Status

- Curve condition tests: 6 passed.
- Raster/curve/composition focused gate: 44 passed.
- Standalone Baird degradation gate: 41 passed.
- `raster_renderer.py` statement and branch coverage: 100%.
- Mutation testing: 897 generated candidates, 23 contract-relevant work items,
  21 killed, and 2 formally documented equivalent survivors. Effective
  non-equivalent mutation coverage is 100%.
- Exact staged-snapshot regression: 2,033 passed.
- Working-tree regression, including unrelated pending slices: 2,047 passed.
- Ruff check/format and strict MkDocs build: passed against the exact staged
  snapshot.

The two focused gates remain separate because collecting the Baird degradation
module after the raster modules in one Windows test process reloads NumPy and
invalidates NumPy's private `_NoValue` sentinel identity. The isolated Baird
gate passes; this test-order limitation is outside `RASTER-CURVE-P2` and does
not alter the renderer or degradation contracts.
