# Linear-Gradient Rectangle Contract Proof

## Scope

Condition `LINEAR-GRADIENT-P1` covers:

- validated and deterministic linear-gradient values;
- renderer-neutral rectangle materialization;
- SVG user-space gradient emission;
- PDF axial shading, clipping, opacity, stroke, and N-stop functions;
- extraction-truth parameter emission;
- legacy solid rectangle compatibility; and
- explicit DXF rejection.

## Dependency Map

Incoming dependencies:

- callers construct `LinearGradientFill`;
- `RectangleDrawing`, `RectangleSVG`, and `RectanglePDF` consume it;
- `FlowDocument` serializes the neutral rectangle payload;
- `DocumentSVG` consumes generated SVG fragments;
- `DocumentPDF` registers shading resources while rendering pages;
- extraction truth reads renderer-provided truth parameters;
- DXF dispatch inspects neutral rectangles.

Outgoing dependencies:

- `gradients.py` uses only Python standard-library math, mappings, sequences,
  and dataclasses;
- SVG emission depends on the rectangle geometry and existing style emitter;
- PDF emission depends on the existing content-transform, clip-path,
  ExtGState, object-writer, and resource-dictionary contracts;
- truth emission depends on the existing annotated-target traversal.

The new dependency direction is:

```text
RectangleDrawing/SVG/PDF -> LinearGradientFill
DocumentPDF -> PDF shading registry -> LinearGradientFill
extraction_truth -> optional target parameter provider
DXF -> RectangleDrawing gradient rejection
```

`DrawingStyle` does not depend on gradients, and `gradients.py` does not depend
on a renderer. No cycle or package dependency is introduced.

## Proof Obligation PO-GRAD-001: Axis Coverage

Claim:

- The computed gradient axis spans the minimum and maximum projection of every
  point in the rectangle along the requested direction.

Domain:

- finite rectangle origin `(x, y)`;
- finite positive width `w` and height `h`;
- finite angle `theta`, normalized modulo 360 degrees.

Assumptions:

- the rectangle is the convex hull of its four corners;
- SVG and PDF linear gradients interpolate along their declared axis and pad
  endpoint colors outside the stop interval.

Theorem:

- For every point `p` in the rectangle, its projection on direction
  `d = (cos(theta), -sin(theta))` lies between the projections of the emitted
  endpoints.

Proof method:

- Let the rectangle center be `c`. Every corner is
  `c + (sx*w/2, sy*h/2)` for `sx, sy` in `{-1, 1}`.
- Its centered projection is
  `sx*cos(theta)*w/2 + sy*(-sin(theta))*h/2`.
- The triangle inequality bounds the absolute projection by
  `h = |cos(theta)|*w/2 + |sin(theta)|*h/2`.
- Choosing `sx` and `sy` to match the signs of the direction components
  achieves both `-h` and `+h`, so the bound is exact.
- The emitted endpoints are `c - h*d` and `c + h*d`.
- Projection is linear, and a rectangle is convex, so every interior point's
  projection also lies inside that interval.

Counterexamples and exclusions:

- zero or negative dimensions are rejected for gradient rectangles;
- non-finite geometry and angles are rejected;
- the theorem covers axis geometry, not conformance bugs in an external SVG or
  PDF renderer.

Conclusion:

- Proven algebraically for the stated domain. Parameterized tests search
  cardinal, oblique, square, wide, tall, and fractional cases for
  implementation/model disagreement.

## Proof Obligation PO-GRAD-002: Visual Angle

Claim:

- The visual direction of the emitted axis is `theta` counter-clockwise from
  horizontal.

Domain and assumptions:

- Same as PO-GRAD-001; InkGen canvas y increases downward.

Proof method:

- The axis direction is `(cos(theta), -sin(theta))`.
- Converting from canvas to visual Cartesian coordinates negates y, yielding
  `(cos(theta), sin(theta))`.
- By the definitions of sine and cosine, this vector has angle `theta`.

Conclusion:

- Proven algebraically. Cardinal and oblique parameterized tests guard the
  implementation.

## Evidence Matrix

| Domain class | Handling | Evidence |
|---|---|---|
| Two valid stops | normalize and emit | value, SVG, PDF, render tests |
| N valid stops | stitch adjacent PDF functions | N-stop PDF test |
| Stops inside `(0, 1)` | pad endpoint colors | N-stop PDF test |
| Negative/large angle | normalize modulo 360 | value test |
| Cardinal/oblique angle | preserve visual direction | axis property tests |
| Square/wide/tall/fractional box | span corner projections | axis property tests |
| Rounded rectangle | clip shading and repaint stroke | PDF operator test |
| Fill opacity | apply existing ExtGState | PDF operator test |
| Annotated panel | emit bbox plus parameters | extraction-truth test |
| Solid legacy rectangle | omit gradient key | compatibility test |
| Malformed kind/stops/color/angle | reject at boundary | failure matrix |
| Zero-area gradient rectangle | reject before output | failure test |
| DXF gradient | reject, never flatten | DXF failure test |
| External consumer rendering | smooth directional samples | PyMuPDF raster test |

## Mutation Evidence

Cosmic Ray generated 587 proof-scope mutants after excluding unchanged
neighboring behavior. The dedicated `LINEAR-GRADIENT-P1` suite killed 580.
Seven survivors are equivalent over the validated runtime domain:

| Survivor | Equivalence argument |
|---|---|
| `target is OutputFormat.SVG` to `target == OutputFormat.SVG` | `normalize_output_format()` returns members of one `Enum`; members are singletons and enum equality is identity equality. |
| `target is OutputFormat.SVG` to `target >= OutputFormat.SVG` | The current normalized domain is exactly string-enum values `pdf` and `svg`; only `svg >= svg` is true, matching the original branch. |
| `LinearGradientFill.angle_deg` dataclass field default `0.0` to `-1.0` | The explicit `__init__` owns the callable default and always assigns the instance field; the dataclass metadata default is not used to construct an instance. |
| `LinearGradientFill.angle_deg` dataclass field default `0.0` to `1.0` | Same constructor-override argument as the preceding mutant. |
| first stop `offset != 0.0` to `offset > 0.0` | Stop validation proves every offset is in `[0, 1]`; on that domain, not equal to zero is equivalent to greater than zero. |
| last stop `offset != 1.0` to `offset < 1.0` | Stop validation proves every offset is in `[0, 1]`; on that domain, not equal to one is equivalent to less than one. |
| `len(stops) == 2` to `len(stops) <= 2` | Construction proves at least two stops and endpoint extension never removes stops; therefore both predicates are true exactly when the length is two. |

The mutation suite includes independent checks for malformed first and last
hex digits, endpoint extension, default angles, two/even/N-stop PDF functions,
multiple shading resources, SVG solid/gradient/none fill opacity, and canonical
truth-parameter sorting.

## Functional Wiring

- `RectangleDrawing.to_component()` reaches both concrete renderers.
- `DocumentSVG.create_svg()` writes a parseable gradient SVG.
- `DocumentPDF.to_pdf_bytes()` registers `/Shading`, invokes `/Sh* sh`, and
  renders a directional transition in PyMuPDF.
- `DocumentPDF.extraction_truth()` emits physical-point bboxes and gradient
  parameters, including after parameter round trip.

## Residual Risk

- SVG/PDF conformance is supported by emitted-operator inspection and PyMuPDF
  evidence, not mathematically proven for every external viewer.
- DOCX does not yet have a native gradient DrawingML contract.
- Radial gradients, patterns, meshes, per-stop opacity, and non-rectangle
  gradient fills are outside this condition.
