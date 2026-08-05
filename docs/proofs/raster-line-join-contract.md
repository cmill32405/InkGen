# Raster Line Join Contract Proof

Condition: `RASTER-LINE-JOIN-P15`.

## Claim

For every finite sharp rectangle or polygon in the declared P15 domain,
InkGen paints `miter`, `round`, and `bevel` raster stroke joins from the
neutral `DrawingStyle` selector without a serialized renderer intermediary.
The default miter route remains unchanged, selectors on geometry without
sharp vertices are neutral, and unsupported sampled geometry fails before
surface allocation.

## Domain And Dependencies

| Direction | Dependency | Contract |
|---|---|---|
| Incoming | `render_drawing_group()` and Baird composition | Closed-domain validation precedes allocation; RGBA order and scaling remain unchanged |
| Incoming | `DrawingStyle` | Join is `miter`, `round`, or `bevel`; stroke width and opacity are validated |
| Incoming | Rectangle and polygon recipes | Straight-edge vertices are finite and ordered; regular-polygon rounding is already canonical |
| Outgoing | Pillow `line`, `ellipse`, and `polygon` | Receives finite supersampled pixel geometry and established RGBA paint |
| Sibling | SVG/PDF join operators | The same half-width outer-corner semantics are selected |

The dependency direction remains `raster_renderer.py -> neutral recipes`.
No dependency, output-format member, or renderer intermediary is added.

P15 applies visible join geometry to sharp `RectangleDrawing`,
`PolygonalDrawing`, and zero-corner-radius `RegularPolygonDrawing` values.
`LineDrawing` and `CircleDrawing` have no join vertex. Rounded rectangles and
rounded regular polygons have smooth canonical outlines, so the selector is a
neutral no-op. Sampled arcs, Beziers, and paths remain outside P15 because
their tessellation vertices are not source path-segment boundaries.

## Mathematical Proof

For consecutive nonzero pixel-space segments `A -> V` and `V -> B`, let

```text
u = (V - A) / ||V - A||
w = (B - V) / ||B - V||
n_u = (-u_y, u_x)
n_w = (-w_y, w_x)
r = raster_stroke_width / 2
c = cross(u, w)
s = -1 when c > 0, otherwise +1
```

The sign `s` selects the side opposite the turn, which is the convex outer
corner. The outer incident-stroke offsets are therefore

```text
P = V + s*r*n_u
Q = V + s*r*n_w
```

Both satisfy `||P - V|| = ||Q - V|| = r` because `n_u` and `n_w` are unit
normals. The bevel join adds triangle `(V, P, Q)` to the two centered stroke
bodies. Its new outer boundary is exactly segment `P -> Q`, the neutral bevel
definition.

The round join adds the radius-`r` disk centered at `V` to those incident
stroke bodies. The bodies already occupy the disk sectors adjacent to each
segment; their union with the disk leaves the circular outer arc between `P`
and `Q`. This is the neutral round-join support. Reversing path direction
negates the cross product and swaps `P` and `Q`, preserving the same geometric
set.

When either incident segment is zero-length or the cross product is zero, no
positive-area outer wedge exists and the bevel helper emits no polygon. Closed
outlines evaluate every vertex exactly once, including the first/last seam.
Open line and circle primitives have no semantic join and therefore retain
identical pixels for all three selectors.

The default miter route is dispatched through the pre-P15 drawing path, so P15
and the later P16 extension introduce no changed operation for default styles.
P16 separately owns bounded nondefault miter construction and bevel fallback.

## Comprehensiveness

| Partition | Evidence |
|---|---|
| Bevel orientation | Exact clockwise and counterclockwise outer triangles |
| Bevel invariant | Property test proves both offsets remain half a stroke width from the vertex |
| Degenerate geometry | Repeated, forward-collinear, and reverse-collinear vertices add no bevel polygon |
| Helper cardinality | Empty, one-point, open, duplicate-point, and closed-collinear paths add no spurious paint |
| Round versus bevel | Public PNG alpha planes are distinct at an acute corner |
| Closed seam | Closed helper and all three public corner-bearing primitives exercise every vertex |
| Gradient interaction | Gradient rectangle retains fill and explicit non-miter stroke |
| No-vertex primitives | Line and circle PNG bytes are equal for miter, round, and bevel |
| Smooth outlines | Existing rounded rectangle/polygon paths remain canonical and selector-neutral |
| Sampled geometry | Path and Bezier non-miter joins fail before Pillow allocation |
| Mutable corruption | Invalid join type and value fail before allocation |
| Miter limit | Nondefault values are neutral for the P15 round/bevel selectors; P16 separately proves miter behavior |
| Invisible stroke | Join geometry cannot create paint when stroke opacity is zero |
| Legacy miter | Dynamic equal selector produces byte-identical established output |

## Verification Status

- **PASS: condition tests.** The focused P15 suite has 23 passing tests,
  including exact geometry, public PNG materialization, invalid-domain failure,
  and degenerate helper branches.
- **PASS: mutation testing.** Cosmic Ray generated 5,360 candidates and
  selected 333 proof-critical P15 work items. All 333 completed: 327 were
  killed and six were proven equivalent, for 98.20% raw and 100% effective
  mutation coverage. Retained execution artifacts are `9655` and `9656`.
- **PASS: regression testing.** Three deterministic disjoint shards ran the
  2,307-test repository inventory successfully (`994 + 602 + 711`). After the
  final helper-edge test was added, its complete 23-test condition file passed,
  covering the current 2,308-test inventory without changing production code.
- **PASS: branch coverage.** Repository coverage is 98%; appending the focused
  P15 suite gives `raster_renderer.py` 100% statement and branch coverage.
- **PASS: complexity.** `_render_component` is 15 after extracting rectangle
  and polygon policy helpers; every new P15 helper is below Ruff's stricter
  complexity-10 reporting threshold. The pre-existing
  `_sampled_path_subpaths` complexity of 31 remains the sole result above the
  slice threshold and was not changed by P15.
- **PASS: static analysis.** Ruff lint, formatter, `ANN`/`S`/`D` checks, and
  Python bytecode compilation pass for every touched Python file.
- **PASS: evidence freshness.** The P10-P15 retained mutation manifests all
  match the final renderer source; the P15 certificate also matches its
  condition tests, checker, filter, configuration, and retained database.

## Residual Boundaries

- Non-miter joins at true command boundaries inside `PathDrawing` require a
  path sampler that preserves semantic segment boundaries separately from
  curve tessellation points.
- Nondefault miter limits are proven by `RASTER-MITER-LIMIT-P16`; this P15
  condition continues to own round and bevel behavior only.
- Dashed strokes remain `LineDrawing`-only under P13, so dash continuity around
  closed corners remains outside this condition.

## Primary Specifications

- [SVG 2 stroke-linejoin](https://www.w3.org/TR/SVG/painting.html#LineJoin)
  defines miter, round, and bevel outer-corner geometry.
- [PDF 1.7 / ISO 32000-1](https://developer.adobe.com/document-services/docs/assets/35e4369068f86065372c18787171a17e/PDF_ISO_32000-1.pdf)
  defines the line-join and miter-limit graphics-state operators.
- [Pillow ImageDraw](https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html)
  defines the line, ellipse, and polygon raster primitives consumed here.
