# Raster Line Dash Contract Proof

Condition: `RASTER-LINE-DASH-P13`.

## Claim

For every finite `LineDrawing` and valid nonempty `DrawingStyle` dash array,
the raster backend paints exactly the on-intervals selected by the neutral SVG
and PDF dash cadence, in logical canvas units, subject to a deterministic
100,000-step resource bound.

## Domain

- finite line endpoints accepted by `LineDrawing`;
- a nonempty finite, nonnegative dash array with at least one positive value;
- a finite, nonnegative phase;
- butt caps, a positive stroke width, and the existing raster canvas domain.

Odd arrays are repeated once. A zero-length source line emits no dash. A phase
without an array and dash styling on non-line primitives are excluded and fail
before surface allocation. Other cap, join, and miter-limit variants remain
outside the raster domain.

## Dependency And Contract Review

| Direction | Dependency | Consumed or preserved contract |
|---|---|---|
| Incoming | `render_drawing_group()` and Baird composition | Closed-domain validation precedes allocation; group order and RGBA source-over remain unchanged |
| Incoming | `LineDrawing` callers and serialized `DrawingStyle` | Dash lengths and phase are logical values, independent of DPI and supersampling |
| Outgoing | `DrawingStyle` | Arrays and phase are nonnegative finite values; odd arrays are legal; at least one array entry is positive |
| Outgoing | Pillow `ImageDraw.line()` | Receives only bounded, scaled on-segments and the existing RGBA stroke/width |
| Sibling | SVG and PDF renderers | Existing serialized dash array and phase semantics remain unchanged |

No dependency edge changes direction. Neutral drawings do not import raster
code, no renderer intermediary is introduced, and no dependency is added.

## Mathematical Proof

Let the source line be

```text
L(t) = A + t(B - A),  0 <= t <= 1
D = ||B - A||
```

Let the validated dash array be `a = (a0, ..., an-1)`. If `n` is odd, define
`q = a ++ a`; otherwise define `q = a`. Therefore `len(q)` is even. Since all
entries are nonnegative and at least one is positive,

```text
P = sum(q) > 0
phi = offset mod P,  0 <= phi < P
```

The cursor subtracts complete entries of `q` from `phi`, skipping zero entries,
until it reaches the unique half-open positive slot containing `phi`. Each loop
iteration then advances by the lesser of the remaining slot length and the
remaining source length. Even-index slots emit `[d0, d1]`; odd-index slots do
not. Thus a distance `d` is painted exactly when `(d + phi) mod P` lies in an
even-index interval of `q`, which is the established SVG/PDF cadence.

For every emitted endpoint `d`, the implementation returns `L(d / D)`. Because
`0 <= d <= D`, every endpoint lies on the closed source segment. Scaling occurs
only after this partition, so DPI and supersampling cannot change logical dash
cadence.

Zero entries cannot prevent termination: `_dash_cursor()` and
`_next_dash_slot()` skip them, and a positive entry must be reached because
`P > 0`. Every outer iteration advances by a positive distance. The renderer
counts each visited positive pattern slot and fails when that count exceeds
100,000. Domain validation runs the same partition before surface allocation,
so both loop work and the possible paint-operation list are bounded.

## Comprehensiveness

| Partition | Evidence |
|---|---|
| Even cadence | Exact unshifted interval test |
| Phase and wrapping | Exact shifted and modulo-equivalent interval tests |
| Odd cadence | Expansion and exact interval test |
| Zero slots | Zero-on and zero-gap cases terminate with exact output |
| Degenerate geometry | Zero-length butt-cap line is transparent |
| Public live path | Exact RGBA dash, gap, phase, and opacity pixels |
| Closed-domain failure | Non-line dash and orphan phase rejection |
| Mutable corruption | Type, boolean, negative, non-finite, and all-zero failures before allocation |
| Resource boundary | Pathological tiny cadence fails before allocation |
| Broad numeric domain | Hypothesis checks order, bounds, and collinearity |
| Legacy compatibility | Full InkGen regression suite |

## Verification Status

- Focused condition and retained-evidence suite: 52 passed.
- Focused P13 helper statement and branch coverage: 100%.
- Full regression: 2,263 tests passed across all 96 recursively discovered
  test files. Three disjoint file shards covered the 96-file set exactly, with
  no duplicate or omitted file.
- Combined full-suite branch coverage: 97% across InkGen and 100% for
  `raster_renderer.py`.
- Mutation: 4,109 generated candidates, 231 selected proof-critical work
  items, 218 killed, and 13 algebraically equivalent survivors. The effective
  mutation score is 100%; retained shard artifacts are `9535` through `9538`.
- Ruff lint and format, Python compilation, strict MkDocs, and diff-hygiene
  gates complete the static and documentation evidence.
- The remaining raster dash domain for rectangles, curves, polygons, circles,
  arcs, and paths is explicitly unproven and unsupported.
