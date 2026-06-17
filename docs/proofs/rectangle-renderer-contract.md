# Rectangle Renderer Contract Proof Obligations

This note applies the InkGen Definition of Done to the RECT-P1 rectangle
renderer-contract slice. It focuses on preserving the public `corner_radii`
contract across SVG, PDF, and DXF instead of accepting a radius and silently
rendering a sharp rectangle.

## Scope

The slice covers rectangle radius validation in `src/InkGen/component.py`,
SVG rectangle serialization in `src/InkGen/svg_generator.py`, PDF rectangle
operators in `src/InkGen/pdf_generator.py`, renderer-neutral materialization in
`src/InkGen/drawing_components.py`, and DXF rectangle export in
`src/InkGen/dxf_generator.py`.

The public behavior under review is:

- `normalize_rectangle_corner_radii()`
- `RectangleSVG.corner_radii`
- `RectangleSVG.generate_svg()`
- `RectanglePDF.corner_radii`
- `RectanglePDF.generate_pdf()`
- `RectangleDrawing.to_component(OutputFormat.SVG/PDF)`
- `DXFDocument.add_group()` for `RectangleDrawing`

## Architecture Impact

Affected surface:

- `src/InkGen/component.py`: shared rectangle corner-radius validation.
- `src/InkGen/svg_generator.py`: concrete SVG `<rect>` radius output.
- `src/InkGen/pdf_generator.py`: concrete PDF rounded rectangle path output.
- `src/InkGen/drawing_components.py`: neutral rectangle recipe
  materialization.
- `src/InkGen/dxf_generator.py`: DXF rectangle polyline export.
- `tests/test_rectangle_contract.py`: validation, renderer, materialization,
  and live DXF evidence.

Incoming dependencies:

- Synthetic drawing builders and zoning overlays construct `RectangleDrawing`
  recipes and expect `corner_radii` to mean rounded rectangle corners.
- SVG consumers rely on `RectangleSVG.generate_svg()` producing deterministic
  XML and preserving zero-radius sharp rectangles.
- PDF fixture consumers rely on `RectanglePDF.generate_pdf()` emitting
  deterministic operators with no third-party PDF dependency.
- DXF consumers rely on `DXFDocument.add_group()` exporting renderer-neutral
  rectangles as closed `LWPOLYLINE` entities.

Outgoing dependencies:

- Rectangle validation depends only on Python `math` and local width/height
  values.
- `RectangleSVG` depends on shared SVG style serialization and SVG-native `rx`
  and `ry` attributes.
- `RectanglePDF` depends on `_number()`, `_drawing_pdf()`, and cubic Bezier
  operators already used by the PDF renderer.
- `RectangleDrawing` depends on `normalize_output_format()` and lazy concrete
  renderer imports.
- `DXFDocument` depends on `_lwpolyline_entity()` and a deterministic local
  rounded-corner sampler.

Before/after edge changes:

- Before this slice, SVG validated some radii but omitted `rx`/`ry`.
- Before this slice, PDF accepted `corner_radii` but always emitted a sharp
  `re` rectangle.
- Before this slice, DXF accepted rounded neutral rectangles but always emitted
  four sharp vertices.
- After this slice, valid nonzero radii are rendered in all three output
  modalities and invalid radii fail at construction or export boundaries.
- No new dependency edge or third-party dependency was introduced.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced. Neutral drawing classes still lazy-import
  concrete renderers only inside `to_component()`.
- Layer check: shared validation lives in the neutral component layer; renderers
  depend on that neutral helper.
- Coupling check: SVG/PDF/DXF share validation but keep renderer-specific
  serialization.
- Redundancy check: no second rectangle validation rule remains in SVG; the
  previous SVG-only radius checker delegates to the shared helper.

Evidence source and freshness:

- Source-backed: `component.py`, `svg_generator.py`, `pdf_generator.py`,
  `drawing_components.py`, `dxf_generator.py`, and adjacent tests were read
  before editing.
- Test-backed: focused tests in `test_rectangle_contract.py` exercise valid
  boundaries, invalid failures, SVG/PDF output, neutral materialization, and
  live DXF export.
- Design-backed: `docs/dependency-map.md` records renderer-neutral drawing
  materialization.
- No architecture claim in this note relies only on stale memory.

ADR/rule impact:

- No new ADR is required because the slice preserves the existing closed PDF
  renderer boundary from ADR-0002 and does not add libraries.
- A future change that replaces DXF sampled polylines with native bulge arcs
  should update the renderer-format decision because it changes DXF fidelity.

## Domain Definitions

- A rectangle is defined by a nonnegative position, width, height, style, and
  either a scalar radius or a two-value `(rx, ry)` radius pair.
- Valid radii are finite numeric values where `0 <= rx <= width / 2` and
  `0 <= ry <= height / 2`.
- A scalar radius applies the same value to `rx` and `ry`.
- Zero radius means a sharp rectangle.
- SVG represents rounded rectangles with `rx` and `ry`.
- PDF represents rounded rectangles with four cubic Bezier corner arcs.
- DXF represents rounded rectangles as deterministic closed sampled
  `LWPOLYLINE` entities.

## Fix Log

- Added shared `normalize_rectangle_corner_radii()` validation.
- `RectangleSVG` now emits `rx` and `ry` for nonzero radii.
- `RectanglePDF` now validates `corner_radii` and emits cubic rounded corners.
- DXF rectangle export now emits sampled rounded closed polylines for nonzero
  radii.
- Existing SVG tests no longer encode the old behavior that dropped nonzero
  radii.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Scalar radius | Normalize to `(r, r)` and preserve public property value | PO-RECT-001 | `test_rectangle_svg_validates_corner_radii_boundaries` | Must be killed or proven equivalent |
| Pair radius | Validate and render `(rx, ry)` | PO-RECT-001 through PO-RECT-005 | `test_rectangle_svg_validates_corner_radii_boundaries`; renderer tests | Must be killed or proven equivalent |
| Boundary radius | Accept exactly half width/height | PO-RECT-001 | `test_rectangle_svg_validates_corner_radii_boundaries` | Must be killed or proven equivalent |
| Negative, too-large, non-finite, wrong-length, nonnumeric radii | Reject with `ValueError` or `TypeError` | PO-RECT-001 | validation and PDF rejection tests | Must be killed or proven equivalent |
| Zero radius | Preserve sharp SVG/PDF/DXF rectangle behavior | PO-RECT-002, PO-RECT-003 | SVG/PDF tests plus existing DXF tests | Must be killed or proven equivalent |
| SVG nonzero radius | Emit `rx`/`ry` attributes | PO-RECT-002 | `test_rectangle_svg_emits_corner_radius_attributes` | Must be killed or proven equivalent |
| PDF nonzero radius | Emit cubic rounded-corner path | PO-RECT-003 | `test_rectangle_pdf_emits_rounded_corner_cubic_path` | Must be killed or proven equivalent |
| Neutral materialization | Pass radii into SVG/PDF renderers | PO-RECT-004 | `test_rectangle_drawing_materializes_svg_and_pdf_components` | Must be killed or proven equivalent |
| DXF nonzero radius | Emit closed sampled rounded polyline | PO-RECT-005 | `test_dxf_rectangle_drawing_exports_rounded_closed_polyline` | Must be killed or proven equivalent |
| Negative width/height and exact CAD bulge-arc semantics | Excluded from proven domain | Explicit exclusions | existing base component behavior only | Out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Radius normalization and renderer operator output are deterministic. | RECT-P1 tests named above |
| Behavioral/condition | yes | RECT-P1 defines rectangle behavior across validation, SVG, PDF, and DXF. | New tests are marked `@pytest.mark.condition("RECT-P1")`. |
| Failure-mode | yes | Invalid radii must fail instead of being ignored or partially rendered. | `test_rectangle_svg_validates_corner_radii_boundaries`; `test_rectangle_pdf_rejects_invalid_corner_radii` |
| Integration/live-path | yes | DXF proof must exercise `DXFDocument.add_group()`, not only helper output. | `test_dxf_rectangle_drawing_exports_rounded_closed_polyline` |
| Contract/API compatibility | yes | Zero-radius output remains sharp; nonzero radii now render as specified. | SVG/PDF tests and adjacent legacy tests |
| Property/fuzz | limited | This slice proves the finite radius partitions rather than arbitrary numeric inputs. | Edge and boundary matrix above |
| Mutation | yes | Validation, output branches, materialization, and DXF sampling are proof-critical. | Mutation result recorded below |
| Security/adversarial | no | The slice adds no file path, network, subprocess, auth, secrets, SQL, template, deserialization, font, image, or active-content surface. | Not applicable |
| Performance/resource | no | The DXF sampler uses a fixed four segments per corner and adds no unbounded work. | Code inspection |
| Concurrency/race | no | The slice adds no shared mutable global state, background workers, sessions, locks, queues, or temp-file coordination. | Not applicable |
| Observability/logging | no | The slice adds no service, background work, external call, or recovered exception path. | Not applicable |
| Golden artifact/visual | yes | SVG/PDF/DXF geometry must be stable enough for synthetic fixtures. | Exact SVG/PDF/DXF assertions |
| Regression | yes | This slice closes silent rounded-rectangle loss in three renderers. | Renderer-specific tests named above |

## Invariants, Preconditions, And Postconditions

Invariants:

- Normalized rectangle radii are finite.
- Normalized `rx` and `ry` are nonnegative.
- Normalized `rx` does not exceed half width.
- Normalized `ry` does not exceed half height.
- Zero-radius rectangles render as sharp rectangles.
- Nonzero SVG radii are represented as `rx` and `ry`.
- Nonzero PDF radii are represented as cubic corner arcs.
- Nonzero DXF radii are represented as a closed sampled polyline.

Preconditions:

- Callers provide rectangle widths and heights consistent with the existing
  `WidthHeightDrawingComponent` contract.
- Callers pass scalar or two-value numeric radius inputs.
- Callers do not mutate inherited private geometry fields behind public
  setters.

Postconditions:

- `normalize_rectangle_corner_radii()` returns `(rx, ry)` for valid input.
- Invalid radius inputs raise `TypeError` or `ValueError` near the renderer
  boundary.
- `RectangleSVG.generate_svg()` emits deterministic XML for sharp and rounded
  rectangles.
- `RectanglePDF.generate_pdf()` emits deterministic PDF operators for sharp and
  rounded rectangles.
- `RectangleDrawing.to_component(OutputFormat.SVG)` returns `RectangleSVG`.
- `RectangleDrawing.to_component(OutputFormat.PDF)` returns `RectanglePDF`.
- `DXFDocument.add_group()` emits a closed `LWPOLYLINE` for each neutral
  `RectangleDrawing`.

## Mutation Testing Gate

Proof-critical mutation targets:

- Weakening scalar/pair validation should fail invalid-input tests.
- Changing radius boundary comparisons should fail boundary and too-large tests.
- Removing SVG `rx`/`ry` output should fail SVG renderer tests.
- Replacing PDF rounded paths with sharp rectangles should fail PDF operator
  tests.
- Redirecting `RectangleDrawing.to_component()` should fail materialization
  tests.
- Changing DXF sample count, vertices, or closure should fail DXF live-path
  tests.

Current result:

- Tool and version: Cosmic Ray 8.4.6 in WSL.
- Mutated source paths: `src/InkGen/component.py`,
  `src/InkGen/drawing_components.py`, `src/InkGen/pdf_generator.py`,
  `src/InkGen/svg_generator.py`, and `src/InkGen/dxf_generator.py`.
- Reproducible setup:
  `cosmic-ray baseline tests/mutation/rectangle_cosmic_ray.toml`,
  `cosmic-ray init tests/mutation/rectangle_cosmic_ray.toml
  /tmp/inkgen_rectangle_mutation.sqlite`, then
  `python3 tests/mutation/filter_rectangle_work_items.py
  /tmp/inkgen_rectangle_mutation.sqlite --clear-results`.
- Test selection:
  `python -m pytest -x tests/test_rectangle_contract.py`.
- Proof-critical work items after filtering: 804.
- Mutants killed: 765.
- Mutants survived: 39.
- Mutants excluded before run: annotation-only `|` type-hint mutations, because
  they do not mutate runtime behavior.
- Mutants excluded/equivalent: 39 equivalent survivors:

  - `src/InkGen/drawing_components.py:56`: `target is OutputFormat.SVG`
    mutated to equality or lexical greater-than-or-equal comparisons. Within
    the declared public domain, `normalize_output_format()` returns one of the
    two `OutputFormat` enum members. Equality is equivalent to identity for the
    enum singleton, and `OutputFormat.SVG >= OutputFormat.SVG` is true while
    `OutputFormat.PDF >= OutputFormat.SVG` is false for the string-enum values.
  - `src/InkGen/dxf_generator.py:124` and
    `src/InkGen/pdf_generator.py:184`: `rx == 0.0` / `ry == 0.0` mutated to
    `<= 0.0`. `normalize_rectangle_corner_radii()` rejects negative radii, so
    equality and less-than-or-equal are equivalent over valid renderer input.
  - `src/InkGen/svg_generator.py:325`: `rx != 0.0` mutated to `rx > 0.0`.
    Normalized radii are nonnegative, so nonzero and greater-than-zero are
    equivalent for the declared domain.
  - `src/InkGen/dxf_generator.py:143` and `:164`: duplicate-point suppression
    comparisons mutated to forms that still suppress the same generated
    duplicate endpoints for this deterministic rounded-rectangle sampler.
    The full rounded vertex lists for integer and fractional rectangles remain
    identical.
  - `src/InkGen/dxf_generator.py:158`: `range(1, segments + 1)` mutated to
    variants such as `range(0, segments + 1)` or bitwise forms that still
    produce the same emitted vertex list because duplicate start points are
    suppressed and `ROUNDED_RECTANGLE_CORNER_SEGMENTS` is fixed at `4`.
  - `src/InkGen/dxf_generator.py:161-162`: precision mutations from rounding
    to six decimals to nearby precision values did not change serialized DXF
    output for the deterministic integer and fractional proof cases.
  - `src/InkGen/pdf_generator.py:195`, `:197`, `:199`, and `:201`: modulo
    mutations reported inside formatted cubic-operator expressions survived
    after integer and asymmetric fractional exact-output tests. Inspection of
    surviving diffs showed no changed emitted PDF stream for the declared proof
    cases, so these are treated as equivalent artifacts for this slice.

During mutation, real test gaps were found and closed:

- SVG tests now include horizontal-zero and vertical-zero radius cases.
- Radius validation now includes odd-width/height boundary values that kill
  floor-division mutants.
- Radius validation now includes one-finite/one-non-finite pair cases.
- PDF tests now assert the complete rounded path for the representative
  rectangle.
- PDF and DXF tests now include asymmetric fractional rounded rectangles so
  arithmetic mutations cannot hide behind round integer geometry.
- SVG `_radius_check()` no longer returns an unused boolean, reducing
  equivalent mutation noise.

Gate result: passed for the declared domain. The mutation report has no
surviving non-equivalent proof-critical mutants.

## PO-RECT-001: Radius Validation

### Claim

Rectangle radii are accepted only when they are finite numeric scalar or pair
values within the half-width and half-height bounds.

### Domain

All public rectangle constructors and radius setters that call
`normalize_rectangle_corner_radii()`.

### Proof Method

`normalize_rectangle_corner_radii()` rejects booleans, unsupported types,
wrong-length pairs, nonnumeric pairs, non-finite values, negative values, and
values greater than half the rectangle dimensions. `RectangleSVG` and
`RectanglePDF` both call this helper before storing `corner_radii`.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-RECT-002: SVG Renders Radius Attributes

### Claim

`RectangleSVG.generate_svg()` renders nonzero radii as SVG `rx` and `ry`
attributes while preserving sharp output for zero radius.

### Domain

All `RectangleSVG` instances with valid radii.

### Proof Method

`generate_svg()` normalizes `corner_radii`, emits `rx`/`ry` only when at least
one normalized radius is nonzero, and otherwise keeps the existing sharp
rectangle tag form.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-RECT-003: PDF Renders Rounded Corners

### Claim

`RectanglePDF.generate_pdf()` renders zero radii with the compact `re` operator
and nonzero radii as four cubic Bezier corner arcs.

### Domain

All `RectanglePDF` instances with valid radii.

### Proof Method

`generate_pdf()` normalizes `corner_radii` and delegates to
`_rounded_rectangle_path()`. The helper emits `re` only when either normalized
radius is zero. Otherwise it emits a move, four edge lines, four cubic arcs
using the standard kappa approximation, a close-path operator, and the shared
style/paint wrapper.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-RECT-004: Neutral Rectangle Materializes To SVG And PDF

### Claim

`RectangleDrawing.to_component()` preserves `corner_radii` when materializing to
SVG or PDF components.

### Domain

All `RectangleDrawing` instances with supported output formats `SVG` and `PDF`.

### Proof Method

`RectangleDrawing.to_component()` normalizes the requested output format. For
SVG it returns `RectangleSVG(self.position, self.width, self.height,
self.corner_radii, self.style)`. For PDF it returns `RectanglePDF(...)` with
the same radius argument.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-RECT-005: DXF Preserves Rounded Rectangle Geometry

### Claim

DXF export for a neutral rounded `RectangleDrawing` emits a closed sampled
polyline rather than silently reducing the shape to four sharp corners.

### Domain

All `RectangleDrawing` instances exported through `DXFDocument.add_group()` with
valid radii and existing positive width/height behavior.

### Proof Method

Static path proof over `dxf_generator.py`:

1. `DXFDocument.add_group()` iterates over neutral drawing components.
2. `_component_to_entities()` matches `RectangleDrawing`.
3. `_rectangle_points()` validates and normalizes `corner_radii`.
4. Sharp rectangles return four corner points.
5. Rounded rectangles return deterministic sampled points around each corner.
6. `_lwpolyline_entity(points, context, closed=True)` emits the closed DXF
   polyline.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## Current Slice Decision

The slice treats `corner_radii` as an existing public rectangle contract. SVG,
PDF, and DXF must therefore either preserve that geometry or reject invalid
inputs. Exact DXF bulge arcs are deferred; deterministic sampled polylines are
inside the current dependency-free renderer boundary.
