# Raster Path Contract Proof

Condition: `RASTER-PATH-P5`.

## Claim

For every valid neutral path in the declared P5 linear-command domain, the
standalone raster renderer preserves command order, axis inheritance, subpath
boundaries, and explicit closure under the established physical coordinate
transform without inventing fill or nonlinear geometry.

## Domain

- The component is a `PathDrawing` whose live command collection is `None` or
  a sequence containing only `PathCommand` objects.
- Every non-empty subpath begins with exactly one-point `M`.
- `L`, `H`, and `V` contain at least one point; `Z` contains no points.
- Only `M`, `L`, `H`, `V`, and `Z` occur.
- The style has no visible fill and uses the solid-stroke controls admitted by
  `RASTER-RENDERER-P1`.
- Canvas, DPI, supersampling, background, and runtime satisfy P1.

## Dependency And Contract Review

- Incoming: public raster rendering and Baird composition consume neutral
  `DrawingComponentGroup` order and `PathDrawing` geometry.
- Outgoing: `raster_renderer.py` depends on `component.PathCommand` for
  normalized command types and points, `DrawingStyle` for normalized paint,
  and Pillow for the final independent polylines.
- Generated-artifact contract: SVG and PDF already serialize neutral path
  commands. P5 consumes the neutral commands directly and does not parse either
  output format.
- ADR consistency: ADR-0034 requires the standalone renderer to consume
  neutral recipes without a serialized intermediary or new rasterizer
  dependency. P5 follows that decision and adds no dependency edge.

## Mathematical Proof

Let one valid subpath begin at `p_0 = (x_0, y_0)` and let the current point
after expansion be `p_i = (x_i, y_i)`. The linear commands define the next
ordered points as follows:

```text
L(x, y) -> (x, y)
H(x, _) -> (x, y_i)
V(_, y) -> (x_i, y)
Z       -> p_0 when the subpath contains at least one segment
```

Induction over the command sequence establishes that each expanded point is
the point defined by the neutral command and the immediately preceding current
point. `M` ends the preceding open subpath and starts a new sequence, while
`Z` appends only the starting point of the current sequence and then ends it.
Therefore no segment can cross an `M` or `Z` subpath boundary.

Let the established P1 pixel transform be

```text
T(x, y) = (round(x * p * s), round(y * p * s))
```

for validated physical scale `p` and supersampling factor `s`. P5 submits each
expanded subpath `[p_0, ..., p_n]` independently as
`[T(p_0), ..., T(p_n)]`. Consequently, command order, axis inheritance,
closure endpoints, and subpath independence are preserved under the same
deterministic transform already proven for P1.

## Comprehensiveness Matrix

| Domain class | Handling | Evidence |
|---|---|---|
| `M` and multi-point `L` | preserve ordered points | exact line-call test |
| `H` and `V` | inherit the current orthogonal coordinate | exact line-call test |
| `Z` | append the subpath start for every segmented subpath | exact expansion tests |
| Multiple subpaths | paint independent polylines | exact line-call test |
| Public clean-to-Baird path | emit clean and degraded assets | live-path test |
| Empty and move-only paths | transparent no-op | parameterized tests |
| Missing stroke | transparent no-op | boundary test |
| Visible fill | reject before allocation | failure-mode test |
| `C`, `S`, `Q`, `T`, `A` | reject before allocation | parameterized tests |
| Malformed order or cardinality | reject before allocation | failure-mode matrix |
| Mutated command container | revalidate and reject before allocation | live-boundary tests |

## Verification Status

- Path condition tests: 28 passed.
- Combined raster renderer, curve, text, arc, path, and Baird-composition gate:
  97 passed.
- `raster_renderer.py` statement and branch coverage: 100% (287 statements and
  160 branches).
- Exact-index mutation: 1,154 generated candidates, 112 relevant work items,
  106 killed, and six rigorously equivalent validated-domain survivors; zero
  worker errors or timeouts. Two non-equivalent survivors were killed after
  adding the transparent-fill boundary condition.
- Standalone Baird regression: 41 passed.
- Exact staged-snapshot regression: 2,086 passed.
- Ruff lint and format checks, strict MkDocs, mutation-evidence hash
  correlation, and cached-diff hygiene passed.
- Dependency manifest: unchanged by this slice; P5 uses existing neutral
  component contracts and Pillow without adding a package.
- Environment advisory: the focused renderer-family process reports the
  pre-existing NumPy module-reload warning. Running Baird after that reload in
  the same process produced six NumPy failures; the fresh-process Baird gate
  passed all 41 conditions, and the full repository order passed all 2,086.
