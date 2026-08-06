# Raster Path Dash Contract Proof

Condition: `RASTER-PATH-DASH-P18`.

## Claim

For every valid dashed `PathDrawing` in the established P5-P7 and P17
domains, the standalone raster renderer applies one logical dash phase per
subpath, measures dashes over the sampled path body without inventing source
joins, applies caps and joins according to SVG/PDF stroke semantics, and
bounds all derived dash and miter work before raster surface allocation.

## Domain

- Path commands satisfy the P5 linear, P6 Bezier, and P7 endpoint-arc
  cardinality, ordering, and finite-coordinate contracts.
- Dash arrays satisfy the P13 neutral style contract: nonnegative finite
  entries, at least one positive entry, and odd arrays repeated to even length.
- Dash offset is finite. It is reduced modulo the positive pattern period.
- Caps are `butt`, `round`, or `square`; joins are `miter`, `round`, or
  `bevel`; miter limits are positive and finite.
- Stroke, fill, canvas, DPI, supersampling, and background satisfy the existing
  raster contracts.

## Dependency And Contract Review

- Incoming: public raster rendering and Baird composition consume neutral
  `PathDrawing` recipes and `DrawingStyle` dash/cap/join selectors.
- Outgoing: `raster_renderer.py` consumes P5-P7 sampled path geometry, P17
  source endpoint topology, P13 dash normalization, and P14-P16 cap/join
  geometry. It adds no dependency or serialized renderer intermediary.
- Cross-backend contract: SVG 2 and PDF apply the configured dash phase anew
  to each subpath. Both cap each open dash and join corners contained inside a
  dash. PDF 2 joins the first and last on-portions of a closed subpath only
  when the initial dash begins on and the final dash ends within an on-slot.
- ADR consistency: ADR-0034 requires neutral input, explicit unsupported
  domains, independent alpha, bounded work before allocation, and no PDF/SVG
  rasterizer. P18 preserves each constraint. No contradictory ADR was found.

## Mathematical Proof

For one sampled subpath with ordered points `p_0, ..., p_n`, define cumulative
distance

```text
d_0 = 0
d_i = sum(j=1..i) ||p_j - p_(j-1)||.
```

Every term is nonnegative. The implementation rejects a non-finite partial
sum, so `0 = d_0 <= ... <= d_n = L` is a finite monotone metric. Duplicate
samples have zero metric width and are skipped when selecting an incident
tangent. Interpolation at distance `x` selects a positive-width edge containing
or nearest to `x`, clamps its affine fraction to `[0, 1]`, and therefore
returns a point on the sampled body.

Let the normalized even dash pattern be `a_0, ..., a_(m-1)` with

```text
a_i >= 0
P = sum(a_i) > 0.
```

The phase is `o mod P`. The established P13 cursor returns one slot and the
remaining distance in that slot. Each positive walker iteration consumes

```text
s = min(remaining, L - position).
```

The implementation requires `position + s > position`; otherwise it rejects
floating-point stagnation. Thus every accepted iteration advances and no
iteration passes `L`. At most the configured global operation budget is
consumed. Every emitted positive interval consequently satisfies

```text
0 <= start < end <= L,
```

and cursor order makes intervals ordered and nonoverlapping. Zero-length
on-slots are enumerated separately at arithmetic-progression positions modulo
`P`, deduplicated, and charged to the same global budget.

Each source join has a retained sample index `e` from P17 and therefore a
distance `d_e`. A join belongs to a positive dash interval `(u, v)` exactly
when

```text
u < d_e < v.
```

Strict inequalities exclude dash boundaries, which receive independent caps.
Bezier and arc tessellation points outside the retained endpoint set can
advance `d` and supply local tangents but cannot become joins. A linear scan of
ordered joins and ordered intervals is bounded by their combined cardinality.

For a closed subpath, let the cursor begin in an on-slot and let the final
walker step end strictly inside an on-slot. Exactly in that case, the final and
initial intervals are two representations of one dash crossing the `Z` seam;
they are merged and receive one seam join rather than two caps. If one on-slot
covers the entire closed path, the run is a closed cycle and receives joins at
all source vertices and no caps. Exact slot boundaries do not satisfy the
strict final condition and remain separate.

For each positive open run, P14 supplies exactly one start and one end cap from
the local measured tangents. Each zero-length on-dash supplies one bounded
round or square mark; butt contributes no pixels. Painted source joins use the
P15/P16 geometry and pre-allocation miter-coordinate check. Fill is composited
under P12 before the dashed stroke layer, preserving independent source-over
alpha.

Multiple `M` subpaths independently repeat this construction from the same
normalized phase. Their operation counts are subtracted from one shared
100,000-operation budget, so splitting an adversarial path cannot evade the
bound.

## Comprehensiveness Matrix

| Domain class | Handling | Evidence |
|---|---|---|
| Multiple source segments | one continuous distance cursor | exact run/section test |
| Multiple `M` subpaths | phase reset per subpath | two-subpath test |
| Bezier/arc samples | advance distance, never invent joins | curve topology test |
| Dash endpoint at source vertex | caps, no join | exact-boundary test |
| Open positive dash | two configured caps | operation-trace tests |
| Zero-length on-dash | local-tangent bounded mark | round/square tests |
| Move-only subpath | transparent no-op | pixel test |
| Zero-length drawing segment | initial dash state controls mark | pixel test |
| Closed seam crossing | one wrapped run and seam join | topology/call test |
| Closed exact boundary | no false seam join | boundary test |
| Whole closed cycle | joins and no caps | topology/call test |
| Nondefault miter | painted joins only, pre-allocation bound | failure-mode test |
| Fill plus dashed stroke | P12 fill before P18 stroke | exact RGBA test |
| DPI/supersampling | logical dash metric scales once | pixel test |
| Large pattern count | shared exact operation ceiling | boundary tests |
| Floating-point stagnation | reject before allocation | adversarial test |
| Other primitive dashes | retain P13/P18 closed-domain rejection | failure test |
| Empty dash array | retain exact P17 dispatch | regression test |
| Arbitrary valid patterns | ordered, bounded, nonoverlapping intervals | property test |

## Verification Status

- Focused P13/P17/P18 and raster mutation-evidence gate: 78 passed.
- Retained Cosmic Ray campaign: 7,220 generated candidates, 736 selected
  work items, 670 killed, 66 mathematically equivalent survivors, zero worker
  errors/timeouts, 91.0% raw and 100% effective mutation coverage.
- Full regression gate: 2,390 passed.
- Full coverage gate: 2,390 passed, 98% package coverage, and 99% coverage for
  `raster_renderer.py`.
- Ruff default, format, and strict `ANN,D,S,C90` checks passed for the six
  touched Python files; the strict complexity ceiling was 15.
- Python bytecode compilation and MkDocs strict build passed.
- The implementation adds no package, runtime, schema, or network dependency.

## Standards References

- W3C, *SVG 2, Painting: Stroke Properties*.
- ISO 32000-1:2008, section 8.4.3.6, line dash pattern.
- ISO 32000-2:2020, section 8.4.3.6, closed dashed-subpath seam behavior.
