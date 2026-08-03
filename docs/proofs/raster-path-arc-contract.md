# Raster Path Arc Contract Proof

Condition: `RASTER-PATH-ARC-P7`.

## Claim

For every valid stroke-only path in the declared P7 domain, an absolute SVG
endpoint-arc `A` command selects the ellipse, center, direction, and angular
span defined by its radii, rotation, large-arc flag, sweep flag, current point,
and last endpoint. Raster sampling preserves exact path endpoints and uses the
canonical neutral `Arc.points` sequence without materializing SVG or PDF.

## Domain

- The path satisfies the `RASTER-PATH-P5` sequence and style domain.
- `A` contains at least one finite `PathCommand` point; its last point is the
  endpoint, matching existing SVG and PDF behavior.
- Missing arc flags default to radii `(0, 0)`, rotation `0`, large-arc `0`, and
  sweep `0`.
- An explicit `flags` value is a mapping. `radii` is a two-value sequence of
  finite numeric values, `rotation` is finite numeric, and `large_arc` and
  `sweep` are booleans or integer `0`/`1` values.
- Negative radii are normalized to absolute values.
- Inputs whose finite values produce non-finite or underflowed center
  calculations are rejected before allocation.
- Relative path commands, visible path fills, hostile custom mappings, and
  private mutation beyond the tested live command fields are outside scope.

## Dependency And Contract Review

- Incoming: public raster rendering and Baird composition consume neutral
  `PathDrawing` recipes in group order.
- Outgoing: `raster_renderer.py` consumes `PathCommand` points and flags,
  `DrawingStyle`, and the canonical `component.Arc.points` sampler.
- Cross-backend contract: `PathSVG` and PDF path handling already use the last
  `A` point as the endpoint and reset smooth controls. P7 preserves that path
  contract while replacing PDF's current line approximation with true sampled
  geometry only in the raster backend.
- Architecture: endpoint-to-center conversion remains renderer-owned; no
  neutral component, serializer, format enum, import direction, or dependency
  manifest changes.
- ADR consistency: ADR-0034 requires direct neutral rendering, no serialized
  intermediary, and no new rasterizer dependency. P7 follows that decision.

## Mathematical Proof

Let the current point be `P0`, the endpoint be `P1`, the absolute radii be
`rx, ry > 0`, and the axis rotation be `phi`. Translate by the midpoint and
rotate by `-phi`:

```text
(x', y') = R(-phi) * ((P0 - P1) / 2)
u = x' / rx
v = y' / ry
lambda = u^2 + v^2
```

If `lambda > 1`, P7 multiplies both radii by `sqrt(lambda)`. The corrected
normalized value is therefore exactly `1` in real arithmetic; otherwise the
radii remain unchanged and `0 < lambda <= 1`.

Let `sigma` be `-1` when the large-arc and sweep flags are equal and `+1`
otherwise, and define

```text
k = sigma * sqrt((1 - lambda) / lambda)
C' = (k * rx * v, -k * ry * u).
```

The normalized vector from `C'` to the transformed start is

```text
(u - k*v, v + k*u).
```

Its squared length is

```text
(u - k*v)^2 + (v + k*u)^2
= (u^2 + v^2) * (1 + k^2)
= lambda * (1 + (1 - lambda) / lambda)
= 1.
```

The transformed endpoint has the negated midpoint coordinates and yields the
same unit result. Thus both endpoints lie on the ellipse centered at `C'`.
Rotating `C'` by `phi` and restoring the midpoint preserves those incidences in
the path coordinate frame. The sign rule selects the two possible centers.

The normalized half-chord length is `sqrt(lambda)`. If `alpha` is the small
central angle, the chord identity gives

```text
sin(alpha / 2) = sqrt(lambda)
alpha = 2 * asin(sqrt(lambda)).
```

P7 therefore chooses magnitude `alpha` for a small arc and `2*pi - alpha` for
a large arc, then applies a positive sign for sweep one and a negative sign for
sweep zero. This computes the required span without subtracting two nearly
equal reconstructed unit vectors. At an exact semicircle the two magnitudes
are both `pi`, as required.

The derived center, corrected radii, start angle, end angle, and rotation are
passed to `Arc.points`. Its ordinary output has 33 points. P7 replaces its
first and last samples with `P0` and `P1`, so finite reconstruction error cannot
break current-point continuity. If the canonical sampler intentionally
collapses a sub-resolution small span to one point, P7 returns `[P0, P1]`
instead; appending from index one still advances the path current point. `A`
then clears both smooth-control histories.

For degeneracies, `rx = 0` or `ry = 0` returns `[P0, P1]`, which is the SVG
line rule. `P0 = P1` returns `[P0]`, so appending from index one adds no
segment. These cases avoid division and are exhaustive before center
conversion.

## Comprehensiveness Matrix

| Domain class | Handling | Evidence |
|---|---|---|
| Four large-arc/sweep combinations | choose center and signed span | exact unit-circle midpoint matrix |
| Rotated unequal radii | derive center form and reuse `Arc.points` | canonical rotated-ellipse comparison |
| Undersized radii | scale both radii by SVG correction | exact corrected semicircle witness |
| Negative radii | normalize with absolute value | rotated canonical comparison |
| Multiple stored points | consume the established last endpoint | rotated comparison with ignored prefix point |
| Missing flags or zero radius | emit a line | degenerate-rule test |
| Equal endpoints | add no segment | degenerate-rule test |
| Arc followed by `S` or `T` | clear both control histories | exact reset test |
| Malformed live flags | reject before allocation | type/value failure matrix |
| Finite inputs with unstable derived values | reject before allocation | overflow/underflow failure matrix |
| Subnormal normalized chord | preserve small/large choice and current point | four-flag huge-radius witness |
| Empty `A` or corrupted tag | reject before allocation | live-boundary tests |
| Public clean-to-Baird path | emit clean and degraded assets | integration test |
| Visible path fill | remain rejected | retained P5 boundary test |

## Test Applicability

| Test class | Status | Reason |
|---|---|---|
| Unit and condition | Applicable | validation and coordinate formulas changed |
| Failure mode | Applicable | malformed flags and unstable arithmetic reject early |
| Integration/live path | Applicable | public raster-to-Baird path is exercised |
| Contract/regression | Applicable | P5/P6 path tests remain in the gate |
| Property/partition | Applicable | all four binary flag combinations and numeric partitions are enumerated |
| Mutation | Applicable | validation, dispatch, and geometry formulas are proof-critical |
| Security/adversarial | Not applicable | no files, active content, subprocess input, or external data access is added |
| Performance/resource | Applicable | each `A` produces either 33 canonical samples or the two-point sub-resolution fallback |
| Golden/visual | Not applicable | exact geometry and live raster evidence cover this non-layout slice |
| Concurrency | Not applicable | conversion is pure and owns no shared mutable state |

## Verification Status

The exact source snapshot is SHA-256
`9A370C3EAC0C115FF5ABDE127351300059B6EC114BA574058FD3DCDDE41BB582`.
The focused P5/P6/P7 path gate passes 76 tests. Cosmic Ray generated 2,167
candidates and the checked-in filter selected 450 proof-critical work items:
437 were killed in the initial campaign, one more was killed by the finite
rounding witness, and 12 are proven equivalent in the validated domain. There
were no worker errors or timeouts, giving 97.33% raw and 100% effective mutation
coverage. Exact hashes and survivor proofs are recorded in
`tests/mutation/raster_path_arc_p7_evidence.json`.

- Complete raster-family gate: 182 passed; `raster_renderer.py` has 100%
  statement and branch coverage (422 statements and 218 branches).
- Standalone Baird degradation gate: 41 passed in a fresh process.
- Exact staged-index regression: 2,134 passed.
- Dirty working-snapshot regression: 2,148 passed, including unrelated pending
  InkGen slices.
- Full package branch-coverage gate: 2,148 passed; aggregate coverage is 97%.
- Ruff lint and format, source compilation, strict MkDocs, evidence-hash
  correlation, and scoped diff hygiene passed.
- Dependency manifest: unchanged; P7 reuses `component.Arc` and Pillow.
- Environment advisory: the combined raster-family process emits the existing
  NumPy module-reload warning. The standalone Baird gate passes without it.
