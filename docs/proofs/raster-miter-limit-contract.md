# Raster Miter Limit Contract Proof

Condition: `RASTER-MITER-LIMIT-P16`.

## Claim

For every sharp straight-edge raster primitive in the declared P16 domain,
InkGen either constructs the exact finite miter selected by
`DrawingStyle.stroke_miterlimit` or constructs the established bevel fallback.
The decision follows the half-angle ratio, generated coordinates are bounded
before surface allocation, and the default limit retains the exact legacy
rendering path.

## Domain And Dependencies

| Direction | Dependency | Contract |
|---|---|---|
| Incoming | `DrawingStyle` | Miter limit is numeric, finite, and greater than zero; join and visible-stroke state remain authoritative |
| Incoming | Rectangle and polygon recipes | Sharp semantic vertices are finite and ordered; rounded outlines are already canonical |
| Incoming | `render_drawing_group()` | Domain validation precedes the first Pillow surface allocation |
| Outgoing | Pillow `line` and `polygon` | Receives bounded supersampled pixel coordinates and established RGBA paint |
| Sibling | SVG/PDF stroke state | Uses the same miter-ratio threshold and bevel fallback meaning |

P16 applies nondefault limits to visible miter strokes on sharp
`RectangleDrawing`, `PolygonalDrawing`, and zero-corner-radius
`RegularPolygonDrawing` values. Limits are neutral for round and bevel joins,
lines, circles, rounded rectangles, rounded regular polygons, and invisible
strokes. Sampled arcs, Beziers, and paths remain outside the domain because
their sampled points are not semantic source joins.

## Mathematical Proof

For nonzero incident pixel-space segments `A -> V` and `V -> B`, define unit
tangents `u` and `w`, outer-side sign `s`, half stroke width `r`, and unit
left normals `n_u` and `n_w` as in the P15 join proof. The outer offsets are

```text
P = V + s*r*n_u
Q = V + s*r*n_w
```

Let `theta` be the angle between `u` and `w`. The distance from `V` to the
intersection of the two outer offset lines is

```text
rho = 1 / cos(theta / 2)
|V -> M| = r*rho
```

Because `cos(theta) = dot(u, w)` and the half-angle identity gives
`cos(theta / 2)^2 = (1 + dot(u, w)) / 2`, the implementation computes

```text
rho = sqrt(2 / (1 + dot(u, w)))
```

The vector `s*(n_u + n_w)` is the outer angle bisector. Normalizing it and
scaling by `r*rho` therefore yields the unique offset-line intersection `M`.
The emitted miter wedge `(V, P, M, Q)` contains exactly the area between the
two incident centered stroke bodies and that intersection.

The style contract retains a miter exactly when `rho <= miter_limit`. If the
ratio exceeds the limit, P16 emits `(V, P, Q)`, which is the P15 bevel proof.
Thus equality remains a miter and every over-limit corner has the specified
fallback. Repeated or collinear incident segments have no positive-area outer
wedge and emit no added polygon. A reversal makes `rho` unbounded; every
finite limit therefore selects the bevel before a miter tip is constructed.

Before allocation, every generated offset and admitted miter tip is checked
for finiteness and absolute value no greater than `2,147,483,647`. A scaled
stroke width above the same bound is rejected. Consequently no admitted P16
geometry can pass an unbounded generated coordinate to Pillow.

## Comprehensiveness

| Partition | Evidence |
|---|---|
| Threshold | A right angle bevels below `sqrt(2)` and miters at exact equality |
| Equation | Property tests prove both offsets have radius `r` and the tip has distance `r*rho` across angles and widths |
| Public dispatch | Sharp rectangle, irregular polygon, and regular polygon outputs differ for low and high limits |
| Legacy path | Equal default values produce byte-identical PNG output |
| Neutral joins | Round and bevel outputs are independent of the miter limit |
| Neutral geometry | Lines, circles, rounded rectangles, and rounded regular polygons are independent of the limit |
| Sampled geometry | Path and Bezier nondefault limits fail before allocation |
| Mutable corruption | Wrong type, NaN, infinity, zero, and negative live values fail before allocation |
| Reversal | A near-reversal with a finite low limit bevels without constructing a large tip |
| Resource bound | Unsafe admitted geometry fails before allocation |
| Mutation adequacy | 701 proof-critical Cosmic Ray mutants are killed by deterministic witnesses |

## Verification Status

- **PASS: condition tests.** Exact geometry, property, public output, neutral,
  corruption, unsupported-domain, reversal, and resource-bound cases pass.
- **PASS: mutation testing.** Cosmic Ray generated 5,870 renderer candidates,
  selected 701 P16 proof-critical work items, and killed all 701 with zero
  worker errors or timeouts. Retained execution artifacts are `9671` and
  `9674`.
- **PASS: regression testing.** Deterministic repository partitions passed
  `905 + 655 + 344 + 426 = 2,330` tests. The final expanded 30-test P16
  condition file also passed, covering the current 2,339-test inventory.
- **PASS: branch coverage.** Repository coverage is 98%; the touched
  `raster_renderer.py` has 100% statement and branch coverage after appending
  the focused P16 suite.
- **PASS: static and documentation gates.** Ruff lint, formatting,
  annotation/security/docstring checks, bytecode compilation, strict MkDocs,
  and diff hygiene pass for the final changed-file set.
- **PASS: evidence freshness.** Active P10-P16 mutation certificates match
  their current source, condition tests, witnesses, tools, and retained
  databases.

## Residual Boundaries

- Semantic path-command joins require a representation that distinguishes
  source joins from curve tessellation points.
- Dash phase continuity around closed outlines remains outside P16.
- Raster clipping and text-presentation parity remain separate bounded slices.

## Primary Specifications

- [SVG 2 stroke-miterlimit](https://www.w3.org/TR/SVG/painting.html#StrokeMiterlimitProperty)
  defines the miter ratio and bevel fallback.
- [PDF 1.7 / ISO 32000-1](https://developer.adobe.com/document-services/docs/assets/35e4369068f86065372c18787171a17e/PDF_ISO_32000-1.pdf)
  defines the graphics-state miter-limit operator.
- [Pillow ImageDraw](https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html)
  defines the bounded line and polygon operations consumed here.
