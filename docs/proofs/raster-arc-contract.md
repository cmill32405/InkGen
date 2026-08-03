# Raster Arc Contract Proof

Condition: `RASTER-ARC-P4`.

## Claim

For every valid neutral elliptical arc in the declared P4 presentation domain,
the standalone raster renderer paints the same ordered sampled points owned by
`Arc.points`, after applying the established physical coordinate transform,
without closing or filling the path.

## Domain

- The component is a valid `ArcDrawing` with finite center, angles, rotation,
  and strictly positive radii.
- The style has no visible fill and uses the solid-stroke controls admitted by
  `RASTER-RENDERER-P1`.
- Canvas, DPI, supersampling, background, and runtime satisfy P1.
- A zero-span arc contains one canonical point and represents a move-only,
  transparent path.

## Dependency And Contract Review

- Incoming: public raster rendering and Baird composition consume neutral
  `DrawingComponentGroup` order and `ArcDrawing` geometry.
- Outgoing: `raster_renderer.py` depends on `component.Arc.points` for sampling,
  `DrawingStyle` for normalized paint values, and Pillow for the final open
  polyline. It does not materialize PDF or SVG.
- Generated-artifact contract: PDF and DXF already use the same canonical arc
  points as an open stroke-only path. P4 preserves that point sequence and
  openness in raster output.
- ADR consistency: ADR-0034 requires the standalone renderer to consume neutral
  recipes and shared geometry without adding a serialized renderer
  intermediary. P4 follows that decision and adds no new dependency edge.

## Mathematical Proof

Let canonical arc points be the finite sequence

```text
A = [a_0, a_1, ..., a_n]
```

returned by `Arc(center, rx, ry, start, end, style, rotation).points`. The
existing `ARC-P1` proof establishes that these points apply ellipse sampling,
rotation, direction, and endpoint inclusion correctly. Let the P1 physical
pixel transform be

```text
T(x, y) = (round(x * p * s), round(y * p * s))
```

for validated physical scale `p` and supersampling factor `s`. P4 passes
exactly `[T(a_0), ..., T(a_n)]` to one Pillow line operation. Therefore point
order, direction, rotation, and endpoint identity are preserved under the
deterministic coordinate transform.

When `n = 0`, an open path has only a move point and no line segment. The
renderer returns before painting, matching the PDF/DXF move-only semantics.
When stroke paint is absent, no operation is emitted. A visible fill is
rejected before surface allocation because filling would add an implicit chord
and change the open-arc geometry.

## Comprehensiveness Matrix

| Domain class | Handling | Evidence |
|---|---|---|
| Forward unrotated span | canonical 33-point open polyline | exact call test |
| Reverse span | preserve canonical reverse order | parameterized exact call test |
| Rotated ellipse | preserve canonical rotation | parameterized exact call test |
| Public clean-to-Baird path | emit clean and degraded assets | live-path test |
| Zero-span arc | transparent move-only no-op | exact no-call test |
| Minimal two-point helper input | paint one open segment | helper boundary test |
| Visible fill | reject before allocation | failure-mode test |
| Transparent fill | admit as non-painting fill | boundary test |
| Missing stroke | transparent no-op | boundary test |
| Invalid geometry | reject in `ArcDrawing` before rendering | existing ARC-FINITE-P2 proof |

## Verification Status

- Arc condition tests: 9 passed.
- Combined raster/arc/curve/text/composition focused gate: 69 passed.
- `raster_renderer.py` statement and branch coverage: 100%.
- Exact-index mutation: 1,031 generated candidates, 27 relevant work items,
  25 killed, and two rigorously equivalent normalized-domain survivors; zero
  worker errors or timeouts.
- Exact staged-snapshot regression: 2,058 passed.
- Ruff lint and format checks, standalone Baird regression, strict MkDocs,
  mutation-evidence hash correlation, and cached-diff hygiene passed.
