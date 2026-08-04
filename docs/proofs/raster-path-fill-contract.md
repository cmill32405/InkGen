# Raster Path Fill Contract

Condition: `RASTER-PATH-FILL-P12`

## Claim

InkGen rasterizes every admitted `PathDrawing` fill with the same default
nonzero winding semantics used by its SVG and PDF paths. Open subpaths are
implicitly closed for fill, nested contours cancel only when their directions
oppose, self-intersections are classified by winding, clipping does not alter
the source contour, and fill/stroke alpha compose in paint order.

## Scope And Dependencies

P12 consumes these established contracts without adding a dependency:

| Dependency | Consumed contract | Failure if changed |
|---|---|---|
| `PathDrawing` and `PathCommand` | Live command collection and style ownership | Fill could accept malformed or stale path state |
| `_sampled_path_subpaths()` | Ordered linear, Bezier, and endpoint-arc samples with independent subpaths | Fill boundary could diverge from raster stroke geometry |
| `DrawingStyle` | Normalized color plus independent fill/stroke opacity | Paint or alpha could change silently |
| Pillow | RGBA masks, source-over composition, and final supersample reduction | Pixel and alpha evidence could change by backend version |
| `Canvas` renderer limits | Finite scale and at most 64,000,000 working pixels | Mask work or memory could become unbounded by canvas size |

The dependency direction remains `raster_renderer.py -> neutral recipes`; SVG,
PDF, DXF, document output, and neutral classes do not depend on raster output.
ADR-0034 owns this extension. No contradictory ADR was found.

P10 and P11 retain whole-file freshness hashes for this shared renderer. P12
changes only the `PathDrawing` branches and adds path-fill helpers outside the
mutation expressions selected by those campaigns. Their manifests therefore
record a scoped-diff re-attestation to the P12 source hash, backed by rerun
focused suites and certificate checks; their mutation outcomes are not
silently treated as evidence for P12.

## Proof Obligations

- `PO-RPF-001`: every admitted sampled coordinate remains finite after pixel
  scaling, before a surface is allocated.
- `PO-RPF-002`: every non-horizontal edge contributes exactly one signed
  crossing on each scanline in its half-open vertical interval.
- `PO-RPF-003`: a working pixel is filled if and only if its center has nonzero
  accumulated winding.
- `PO-RPF-004`: open and explicitly closed versions of the same subpath have
  identical fill geometry.
- `PO-RPF-005`: canvas clipping restricts work and output pixels without
  replacing or renormalizing source edges.
- `PO-RPF-006`: degenerate subpaths create no fill pixels.
- `PO-RPF-007`: fill alpha is applied once, then stroke alpha is source-over
  composited, then the component layer is source-over composited in group
  order.
- `PO-RPF-008`: the public clean-to-Baird path consumes the filled raster asset.

## Mathematical Argument

For a supersampled pixel row `r`, evaluate the horizontal ray through
`y = r + 1/2`. For every directed non-horizontal edge from `(x1, y1)` to
`(x2, y2)`, P12 admits the edge exactly when

```text
min(y1, y2) <= y < max(y1, y2).
```

The half-open upper boundary means a shared vertex belongs to exactly one of
its two incident non-horizontal edges. The intersection is

```text
x(y) = x1 + (y - y1) * (x2 - x1) / (y2 - y1),
```

with winding delta `+1` when `y1 < y2` and `-1` otherwise. Sorting active
intersections partitions the row into intervals. The running sum is constant
inside each interval and changes only by the crossing delta at an edge. This is
the standard nonzero winding number up to a global sign caused by the y-down
canvas; testing `winding != 0` is invariant under that sign. Therefore a pixel
center is selected exactly when its source path winding is nonzero.

Each subpath appends its first point only to the fill edge sequence when it is
not already closed. Thus implicit and explicit closure produce the same edge
multiset while stroke sampling remains unchanged. Horizontal edges contribute
no ray crossing. Subpaths with fewer than three sampled points, collinear
contours, and opposite crossings with zero accumulated winding produce no fill.

The evaluated row and column ranges are the intersection of the source path's
supersampled bounding box and the finite canvas. Intersections still use the
original off-canvas endpoints, so clipping cannot change winding. The mask is
allocated only for that clipped box and cannot exceed the already bounded
working surface.

Finally, the mask contains either zero or the normalized fill alpha. Pillow
source-over composites that tile onto the component layer. A separate stroke
layer is then source-over composited onto the fill, and the renderer composites
the completed component layer in group order. This establishes `PO-RPF-007`.

The path-specific paint dispatch is isolated in `_render_path_component`.
Explicit McCabe analysis places every P12 helper at or below 12, under the
project maximum of 15, while reducing the pre-existing `_render_component`
score from 22 to 20. No dependency or public API was added by the extraction.

## Comprehensiveness Matrix

| Domain class | Required handling | Evidence |
|---|---|---|
| Open and `Z`-closed contour | identical implicit fill closure | parameterized exact-pixel test |
| Same-orientation nested contours | retain filled interior | nonzero-vs-even-odd discriminator |
| Opposite-orientation nested contours | create transparent hole | cancellation test |
| Self-intersection | fill only nonzero lobes | bow-tie discriminator |
| Curved commands | use established sampled boundary | quadratic live-path test plus P6/P7 suites |
| Off-canvas contour | clip output, retain source winding | full-canvas enclosure test |
| Collinear or move-only contour | transparent no-op | degenerate test plus P5 no-op tests |
| Vertically separated contours | inactive intervening scanlines stay transparent | disjoint-contour branch test |
| Fill and translucent stroke | source-over in fill-then-stroke order | exact RGBA test |
| Pixel-space overflow | reject before allocation | allocation-guard failure test |
| Public Baird composition | emit clean and degraded assets | public integration test |
| Existing stroke-only paths | preserve behavior | complete P5/P6/P7 regression suites |
| Retained mutation evidence | fail closed on source, test, config, filter, database, count, outcome, or survivor drift | certificate test over the committed manifest and SQLite campaign |

## Residual Risk

P12 proves the default nonzero rule. InkGen's neutral `DrawingStyle` has no
path-specific even-odd selector, so even-odd path fills remain outside the
public model rather than being silently approximated. Pixel bytes remain tied
to the installed Pillow version, as stated by ADR-0034.

## Verification Status

The retained Cosmic Ray campaign generated 3,747 candidates and selected 292
proof-critical mutations across validation, paint-order wiring, and scanline
fill helpers. It killed 279; the 13 survivors are proven equivalent in
`tests/mutation/raster_path_fill_p12_evidence.json`, for effective mutation
coverage of 100%. Focused condition, changed-line/branch coverage, exact-index
regression, lint, strict-documentation, and diff-hygiene gates complete the
verification record.
