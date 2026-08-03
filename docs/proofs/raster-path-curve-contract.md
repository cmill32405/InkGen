# Raster Path Curve Contract Proof

Condition: `RASTER-PATH-CURVE-P6`.

## Claim

For every valid stroke-only path in the declared P6 domain, raster `C`, `S`,
`Q`, and `T` commands preserve the canonical neutral Bezier samples, command
order, current-point continuity, and smooth-control reflection without
materializing SVG or PDF.

## Domain

- The path satisfies the `RASTER-PATH-P5` sequence and style domain.
- `C` points occur in groups of three `(control_1, control_2, end)`.
- `S` points occur in groups of two `(control_2, end)`.
- `Q` points occur in groups of two `(control, end)`.
- `T` contains at least one endpoint.
- Empty `C`, `S`, and `Q` commands are no-ops.
- Elliptical `A` commands and visible path fills remain outside the domain.

## Dependency And Contract Review

- Incoming: public raster rendering and Baird composition consume neutral
  `PathDrawing` recipes in group order.
- Outgoing: `raster_renderer.py` depends on `PathCommand` grouping and on the
  canonical `CubicBezier.points` and `QuadraticBezier.points` samplers. It does
  not duplicate either Bernstein equation.
- Cross-backend contract: PDF already owns absolute `C/S/Q/T` grouping,
  current-point updates, and reflected-control behavior. P6 preserves those
  semantics while producing sampled raster polylines instead of PDF operators.
- ADR consistency: ADR-0034 requires neutral geometry consumption, no
  serialized intermediary, and no new rasterizer dependency. P6 follows that
  decision and changes no dependency manifest.

## Mathematical Proof

Let the current endpoint be `P`, the previous applicable control be `K`, and
the smooth reflected control be

```text
R(K, P) = 2P - K.
```

For `S`, `R` is used as the first cubic control only when a preceding `C` or
`S` segment established a cubic control; otherwise the first control is `P`.
For `T`, `R` is used as the quadratic control only when a preceding `Q` or `T`
segment established a quadratic control; otherwise the control is `P`. Linear
commands, the opposite curve family, `M`, and `Z` clear the inapplicable state,
so a control cannot leak across a semantic boundary.

For each segment, let the canonical neutral sample sequence be

```text
B = [P, b_1, ..., b_32].
```

P6 appends `[b_1, ..., b_32]` to the current subpath. The repeated start is
omitted, but every sampled segment point and the endpoint remain unchanged.
Induction over complete command groups establishes a single ordered subpath
whose current endpoint after each segment equals that segment's canonical
endpoint. P5 independently proves subpath separation, closure, and the final
physical pixel transform.

## Comprehensiveness Matrix

| Domain class | Handling | Evidence |
|---|---|---|
| Multi-segment `C` | canonical cubic samples in order | exact sample test |
| Multi-segment `S` | reflected cubic controls | exact sample test |
| Multi-segment `Q` | canonical quadratic samples in order | exact sample test |
| Multi-segment `T` | reflected quadratic controls | exact sample test |
| Linear reset | clear smooth state before `S`/`T` | reset test |
| Opposite-family reset | prevent cubic/quadratic state leakage | cross-family test |
| New subpath and `Z` | reset state, preserve independent closure | cross-family test |
| Empty `C`/`S`/`Q` | transparent no-op | grouped no-op test |
| Incomplete groups or empty `T` | reject before allocation | failure-mode matrix |
| Elliptical `A` | reject before allocation | retained P5/P6 boundary test |
| Public clean-to-Baird path | emit clean and degraded assets | live-path test |

## Verification Status

- P6 condition tests: 11 passed; combined P5/P6 path conditions: 35 passed.
- Combined raster renderer, primitive-curve, text, arc, path, path-curve, and
  Baird-composition gate: 104 passed.
- `raster_renderer.py` statement and branch coverage: 100% (338 statements and
  184 branches).
- Exact-index mutation: 1,430 generated candidates, 267 relevant work items,
  262 killed, and five rigorously equivalent validated-domain survivors; zero
  worker errors or mutant timeouts. Two non-equivalent reflection mutants were
  killed after adding a nonzero two-axis witness.
- Standalone Baird regression: 41 passed.
- Exact staged-snapshot regression: 2,093 passed.
- Ruff lint and format checks, strict MkDocs, mutation-evidence hash
  correlation, and cached-diff hygiene passed.
- Dependency manifest: unchanged by this slice; P6 reuses neutral Bezier
  samplers and Pillow without adding a package.
- Environment advisory: the focused renderer-family process reports the
  pre-existing NumPy module-reload warning. The fresh-process Baird gate passed
  all 41 conditions, and the full repository order passed all 2,093.
