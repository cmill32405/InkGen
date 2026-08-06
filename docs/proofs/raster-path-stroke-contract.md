# Raster Path Stroke Contract Proof

Condition: `RASTER-PATH-STROKE-P17`.

## Claim

For every valid solid-stroke `PathDrawing` in the established P5/P6/P7 path
domain, the standalone raster renderer applies caps only to open subpath ends,
applies joins only at source segment boundaries and closed seams, preserves the
established sampled stroke body, and bounds generated miter coordinates before
surface allocation.

## Domain

- Path commands satisfy the P5 linear, P6 Bezier, and P7 endpoint-arc
  cardinality and ordering contracts.
- The dash array is empty and dash phase is zero. Dashed path continuity is
  proven separately by `RASTER-PATH-DASH-P18`.
- The cap is `butt`, `round`, or `square`; the join is `miter`, `round`, or
  `bevel`; the miter limit is positive and finite.
- Stroke width, stroke opacity, canvas, DPI, supersampling, and background
  satisfy the existing raster contracts.
- Fill is absent or satisfies the P12 nonzero-winding contract.

## Dependency And Contract Review

- Incoming: public raster rendering and Baird composition consume neutral
  `PathDrawing` recipes and `DrawingStyle` stroke selectors.
- Outgoing: `raster_renderer.py` consumes normalized `PathCommand` values,
  canonical Bezier and arc samples, Pillow RGBA primitives, and the existing
  P14-P16 cap/join geometry. It adds no package or backend dependency.
- Cross-backend contract: SVG and PDF already distinguish source path segments
  from renderer approximation points. P17 retains that distinction in the
  raster path instead of parsing either serialized format.
- ADR consistency: ADR-0034 requires neutral input, explicit unsupported
  domains, independent alpha, bounded allocation, and no PDF/SVG rasterizer.
  P17 follows those constraints. No contradictory ADR was found.

## Mathematical Proof

Let source subpath segments be `S_1, ..., S_n`. For each segment, the canonical
sampler returns an ordered point sequence

```text
S_i = [p_i, q_i,1, ..., q_i,k_i, p_i+1].
```

The sampler concatenates `S_i[1:]` and records the resulting index `e_i` of
`p_i+1`. By induction over source segments, the concatenated point sequence is
identical to the established P5/P6/P7 sequence, while

```text
E = [0, e_1, ..., e_n]
```

contains exactly the source endpoints. Therefore the open join set is
`E[1:-1]`. For `Z`, the start point is appended as the closure body and the
join set is all non-duplicated members of `E`, including index zero exactly
once. Tessellation indices outside `E` cannot receive join geometry.

At endpoint index `e`, let `a` and `b` be the nearest distinct sampled points
before and after `e`. The incoming and outgoing unit tangents are

```text
u = (p_e - a) / ||p_e - a||
v = (b - p_e) / ||b - p_e||.
```

Round and bevel joins use the already proven P15 half-width constructions on
`(a, p_e, b)`. A miter uses the P16 ratio

```text
r = sqrt(2 / (1 + u dot v)).
```

The miter wedge is selected exactly when `r <= miter_limit`; otherwise the
bevel wedge is selected. Every generated miter coordinate is checked against
the signed 32-bit raster bound before Pillow surface allocation. Degenerate
incident geometry has no distinct tangent and contributes no join wedge.

For an open nondegenerate subpath, let forward endpoint tangent be `t`, unit
normal be `n = (-t_y, t_x)`, and half-width be `h`. A round cap is the disk of
radius `h` centered at the endpoint. A square cap is the polygon bounded by
`p +/- h*n` and `p +/- h*n +/- h*t`, with the sign directed away from the
stroke body. Thus each cap projects exactly one half-width beyond its subpath
end. A degenerate source segment uses the established horizontal tangent and
produces one centered disk or square. A move-only subpath has no source segment
and produces no cap.

Fill is composited first under P12. Stroke bodies, semantic joins, and caps are
painted on the stroke layer and source-over composited afterward. Therefore
P17 does not alter the established independent fill/stroke paint order.

## Comprehensiveness Matrix

| Domain class | Handling | Evidence |
|---|---|---|
| Linear and grouped segments | one endpoint index per source segment | topology and property tests |
| Bezier and arc samples | local tangent evidence, never extra joins | exact endpoint-index tests |
| Open subpaths | two endpoint caps, interior joins only | pixel and call-contract tests |
| Multiple open subpaths | independent caps and topology | multi-subpath test |
| `Z` closure | explicit closure body, seam joins, no caps | closed-path tests |
| Move-only and equal-endpoint arc | transparent no-op | degenerate tests |
| Zero-length source segment | one bounded round or square cap | cap tests |
| Round and bevel joins | explicit source-boundary geometry | public and call-contract tests |
| Nondefault miter limit | inclusive P16 threshold and bevel fallback | public and preflight tests |
| Fill plus custom stroke | P12 fill before P17 stroke | compositing test |
| Path dash array | delegated to the P18 measured-dash contract | P18 regression test |
| Standalone sampled curves | retain P15/P16 rejection | regression tests |
| Default butt/miter/10 | exact established `_draw_curve` dispatch | legacy-route test |

## Verification Status

- PASS: pre-change dependency, caller, contract, and ADR review.
- PASS: `RASTER-PATH-STROKE-P17` happy-path, failure-mode, edge-case,
  property, operation-trace, allocation-preflight, and compositing tests.
- PASS: default P5/P6/P7 sampled path sequences and default butt/miter/10
  rendering remain on the established legacy route.
- PASS: Cosmic Ray completed 579/579 selected mutations with 539 killed and 40
  mathematically documented equivalent survivors: 93.1% raw and 100%
  effective mutation coverage. The retained database and survivor proofs are
  checked by `test_raster_path_stroke_mutation_evidence.py`.
- PASS: all 2,365 repository tests passed in four deterministic shards
  (artifacts 9752, 9755, 9756, and 9759).
- PASS: package branch coverage is 97%; `raster_renderer.py` statement and
  branch coverage are both 100%.
- PASS: Ruff default lint and format; `ANN`, `D`, `S`, and `C90` with maximum
  complexity 15; and Python bytecode compilation for all touched Python files.
- PASS: strict MkDocs build (artifact 9761) and `git diff --check`.
- PASS: package dependencies are unchanged; P17 introduces no rasterizer,
  parser, network, or non-Pillow rendering dependency.
