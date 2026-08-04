# Raster Line Cap Contract Proof

Condition: `RASTER-LINE-CAP-P14`.

## Claim

For every finite raster `LineDrawing` in the declared domain, InkGen paints
the neutral `butt`, `round`, or `square` cap support at both ends of every
solid or dashed on-segment, including zero-length on-dashes, with bounded work
and no serialized renderer intermediary.

## Domain And Dependencies

| Direction | Dependency | Contract |
|---|---|---|
| Incoming | `render_drawing_group()` and Baird composition | Closed-domain validation precedes allocation; RGBA order and scaling remain unchanged |
| Incoming | `LineDrawing` and serialized `DrawingStyle` | Endpoints are finite; cap is `butt`, `round`, or `square`; stroke width and opacity are validated |
| Outgoing | P13 dash partition | Positive on-segments retain logical cadence and phase before pixel scaling |
| Outgoing | Pillow `line`, `ellipse`, and `polygon` | Receives finite bounded pixel geometry and the established RGBA stroke |
| Sibling | SVG/PDF cap operators | Nondegenerate round and square support has the same half-width construction |

The dependency direction remains `raster_renderer.py -> neutral recipes`.
No package or renderer intermediary is added. Non-butt caps remain rejected
for rectangles, circles, arcs, paths, curves, and polygons.

## Mathematical Proof

For a nonzero pixel-space segment from `A` to `B`, let

```text
u = (B - A) / ||B - A||
n = (-u_y, u_x)
r = raster_stroke_width / 2
```

The established butt path paints the stroke body without extending its source
endpoints. The round path paints that body and disks centered at `A` and `B`
with radius `r`. Their union therefore adds exactly one outward half-disk at
each endpoint.

The square path paints the quadrilateral with corners

```text
A - r*u + r*n    B + r*u + r*n
B + r*u - r*n    A - r*u - r*n
```

Projection onto `u` gives the closed interval
`[dot(A,u)-r, dot(B,u)+r]`; projection onto `n` gives
`[dot(A,n)-r, dot(A,n)+r]`. The polygon is therefore exactly the stroke-width
rectangle extended one half-width beyond both endpoints.

For a zero-length solid line, butt emits no paint, round emits one disk, and
square emits one centered square. A zero-length square has no geometric
tangent, so InkGen uses the deterministic neutral fallback `u=(1,0)`. This
matches SVG's centered-square outcome; PDF specifies no output for a
degenerate projecting-square path because its orientation is indeterminate.
The backend difference is explicit rather than treated as equivalence.

P13 returns every positive on-segment. For each zero-length even dash entry at
pattern prefix `q_i`, P14 solves

```text
d = q_i - (offset mod period) + k*period,  0 <= d <= line_length
```

and paints a cap centered at `A + d*u`. Thus positive and zero-length dashes
share one cadence. Duplicate centers are painted once. The number of positive
segments plus unique zero centers may not exceed 100,000; validation computes
the same geometry before surface allocation.

## Comprehensiveness

| Partition | Evidence |
|---|---|
| Solid round and square | Exact public RGBA endpoint and corner pixels |
| Butt compatibility | P1/P13 regression and zero-length transparent test |
| Horizontal and diagonal square geometry | Exact corners plus property-based support projections |
| Positive dashed segments | Public square-cap cadence test |
| Zero-length on-dashes | Exact center/phase tests and public dotted-line pixels |
| Zero-length source line | Butt, round, square, on-phase, and gap-phase tests |
| Alpha and clipping | Exact translucent public pixels and Pillow canvas clipping |
| Closed-domain rejection | Non-line cap tests before allocation |
| Mutable corruption | Invalid type/value tests before allocation |
| Resource bound | Exact combined positive-segment/zero-cap boundary tests |
| Aggregate numeric overflow | Non-finite dash-period rejection before allocation |
| Live public path | `render_drawing_group()` tests over solid and dashed lines |

## Verification Status

- Focused P14/P13/renderer plus certificate suite: 72 passed (artifact 9603).
- P10-P13 dependency refresh: both fast mutation witnesses and 299 focused
  tests passed (artifact 9606); all seven retained evidence modules then
  passed 16 tests (artifact 9607).
- Cosmic Ray 8.4.6: 4,834 generated candidates, 431 retained P14 work items,
  415 killed, and 16 equivalent survivors with exact job-ID proofs. Raw
  mutation coverage is 96.2877%; effective mutation coverage is 100%.
  The complete SQLite campaign and freshness verifier are retained in
  `tests/mutation/raster_line_cap_p14.sqlite` and
  `tests/test_raster_line_cap_mutation_evidence.py`.
- Full regression: 2,284 tests passed across three deterministic disjoint
  branch-coverage shards (artifacts 9611, 9612, and 9613).
- Combined branch coverage: 96.96% repository-wide and 100.00% for
  `raster_renderer.py` (778 statements and 366 branches; artifact 9615).
- Ruff lint, ANN/S/D checks, Ruff format, Python compilation, strict MkDocs,
  and `git diff --check` passed for the P14 snapshot (artifact 9616).
- P14 reduced `_validate_render_domain` from complexity 18 to 11; every new
  P14 helper is at or below the project threshold of 12. The pre-existing
  `_render_component` (19) and `_sampled_path_subpaths` (31) exceptions are
  unchanged and remain outside this slice.

## Primary Specifications

- [SVG 2 stroke-linecap](https://www.w3.org/TR/SVG/painting.html#LineCaps)
  defines butt, half-circle round, half-width square, and zero-length shapes.
- [PDF 1.7 / ISO 32000-1](https://developer.adobe.com/document-services/docs/assets/35e4369068f86065372c18787171a17e/PDF_ISO_32000-1.pdf)
  defines line-cap operators and the degenerate projecting-square exception.
- [Pillow ImageDraw](https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html)
  defines the inclusive line, ellipse, and polygon raster primitives consumed
  by this backend.
