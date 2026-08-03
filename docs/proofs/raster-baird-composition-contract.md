# Raster Baird Composition Contract Proof

Condition: `RASTER-BAIRD-P1`.

## Claim

For the declared renderer P1 domain, fixed Baird parameters, a fixed seed, and
an explicit RGB substrate, `render_and_degrade_drawing_group()` deterministically
returns the clean transparent RGBA render and its opaque Baird-degraded scan
without a PDF or SVG intermediary.

## Domain And Assumptions

- The group, canvas, DPI, and render supersampling satisfy
  `RASTER-RENDERER-P1`.
- `params` is a valid immutable `BairdParams` value.
- `seed` is in Baird's unsigned 64-bit seed domain.
- `background_rgb` is an explicit three-channel integer substrate.
- Deterministic-byte claims are scoped to the same Pillow and NumPy runtime.

## Composition Proof

Let `R(x)` be `render_drawing_group()` for fixed render inputs `x`. P1 proves
that `R` is deterministic and returns a transparent `RasterRenderResult`.

Let `B(a, p, s, c)` be `baird_degrade_asset()` for raster asset `a`, parameters
`p`, seed `s`, and substrate `c`. `BAIRD-P2` proves that `B` is deterministic
for those fixed inputs, requires `c` for alpha input, and returns a
`BairdDegradationResult`.

The composition is exactly:

```text
F(x, p, s, c) = (R(x), B(R(x).asset, p, s, c))
```

For two equal input tuples, determinism of `R` gives equal clean results.
Substitution into deterministic `B` gives equal degraded results. Therefore
both members and the nested manifest returned by `F` are equal. The source
contains no PDF or SVG import or call; the only new internal edge is
`raster_renderer -> baird`.

## Comprehensiveness Matrix

| Domain class | Handling | Evidence |
|---|---|---|
| Valid drawing and Baird inputs | return clean and degraded assets | deterministic live-path test |
| Transparent clean result | preserve RGBA clean asset | pixel and mode assertions |
| Colored substrate | affect opaque scan explicitly | black/white substrate test |
| Reproducibility | nest both manifests and preserve source | repeated byte/manifest test |
| Missing or invalid substrate | reject | failure-mode test |
| Invalid params or seed | delegate Baird rejection | failure-mode test |
| Invalid result envelope | reject unrelated result types | constructor test |
| Public defaults and keyword-only controls | pin 300 DPI, 2x, and keyword-only inputs | signature/default test |
| PDF/SVG input or intermediary | excluded | ADR-0034 and import graph |

## Verification Status

- Focused composition conditions: 5 passed.
- Combined raster P1/P2 statement and branch coverage: 100%.
- Mutation: 13 selected composition mutants, 13 killed, zero survivors,
  errors, or timeouts; evidence is retained in
  `tests/mutation/raster_baird_composition_p1_evidence.json`.
- Exact staged-snapshot regression: 2,027 passed.
- Ruff lint and format checks, Python compilation, strict MkDocs build, and
  `git diff --cached --check`: passed.
- No dependency manifest changed. The shared Python environment retains its
  pre-existing `sse-starlette`/`starlette` version conflict; it is outside this
  slice and was not modified.
