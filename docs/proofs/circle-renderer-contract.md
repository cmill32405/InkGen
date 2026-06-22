# Circle Renderer Contract Proof Obligations

This note applies the InkGen Definition of Done to the CIRCLE-P1 circle
renderer-contract slice. It focuses on radius validation, PDF cubic-circle
serialization, renderer-neutral materialization, and native DXF circle export.

## Scope

The slice covers circle PDF rendering in `src/InkGen/pdf_generator.py`,
renderer-neutral materialization in `src/InkGen/drawing_components.py`, and DXF
circle export in `src/InkGen/dxf_generator.py`.

The public behavior under review is:

- `CirclePDF.__init__()`
- `CirclePDF.generate_pdf()`
- `CircleDrawing.to_component(OutputFormat.SVG/PDF)`
- `DXFDocument.add_group()` for `CircleDrawing`
- `_circle_entity()`

## Architecture Impact

Affected surface:

- `src/InkGen/pdf_generator.py`: PDF circle rendering using four cubic Bezier
  segments.
- `src/InkGen/drawing_components.py`: neutral circle recipe materialization to
  concrete renderers.
- `src/InkGen/dxf_generator.py`: native DXF `CIRCLE` entity output.
- `tests/test_circle_contract.py`: validation, renderer, and dependency-path
  evidence.

Incoming dependencies:

- PDF fixture consumers rely on `CirclePDF.generate_pdf()` emitting a closed
  circle path with deterministic cubic control points.
- SVG/PDF drawing recipe consumers rely on `CircleDrawing.to_component()`
  preserving circle position, radius, and style.
- DXF consumers rely on `CircleDrawing` being exported as a native `CIRCLE`
  entity rather than a sampled polyline.

Outgoing dependencies:

- `CirclePDF` depends on the shared `SingleDimensionDrawingComponent` radius and
  point contract, local `_number()` serialization, and `_drawing_pdf()`.
- `CircleDrawing` depends on `normalize_output_format()` and materializes to
  `CircleSVG` or `CirclePDF`.
- `DXFDocument` depends on `CircleDrawing` and `DXFRenderContext.point()` for
  native circle center coordinates.

Before/after edge changes:

- No production code or dependency edge was changed in this slice.
- The existing neutral recipe edge `CircleDrawing -> CircleSVG/CirclePDF` is now
  explicitly tested.
- The existing DXF edge `CircleDrawing -> _circle_entity()` is now explicitly
  tested as native entity output.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced. Components do not import PDF or DXF.
- Layer check: concrete renderers and DXF output depend on neutral recipes
  according to `docs/dependency-map.md`.
- Coupling check: DXF intentionally does not reuse PDF circle Bezier geometry;
  it emits a native `CIRCLE` entity.
- Redundancy check: the slice avoids introducing another circle geometry
  implementation.

Evidence source and freshness:

- Source-backed: `pdf_generator.py`, `drawing_components.py`, `dxf_generator.py`,
  and `svg_generator.py` were read before adding tests.
- Test-backed: focused tests in `test_circle_contract.py` exercise validation,
  PDF operators, neutral recipe materialization, and live DXF export.
- Design-backed: `docs/dependency-map.md` records renderer-neutral materializing
  into concrete drawing components.
- No architecture claim in this section relies only on stale memory.

ADR/rule impact:

- No new ADR is required because no new architecture decision was made.
- A future change that converts DXF circles into sampled polylines should add or
  update an ADR because it changes the generated-artifact contract.

## Domain Definitions

- A PDF circle is defined by a position accepted by
  `SingleDimensionDrawingComponent`, a numeric `radius > 0`, and a
  `DrawingStyle`.
- The PDF circle approximation uses the standard four-cubic kappa constant:

```text
k = 0.5522847498307936
control = radius * k
```

- The native DXF circle contract emits group codes:

```text
0 CIRCLE
8 layer
10 center.x
20 center.y
30 0
40 radius
```

## Fix Log

- No production fixes were required in this slice.
- Test hardening fixed the local DXF test parser so it reads code/value pairs
  inside the `CIRCLE` entity block rather than scanning all header/entity lines.
- Mutation testing forced stricter PDF assertions so expected operators are
  matched as complete lines, not substrings.
- Mutation testing forced a stricter DXF assertion that `CIRCLE` is paired with
  group code `0`.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid numeric radius | Construct a PDF circle and preserve the radius | PO-CIRCLE-001 | `test_circle_pdf_rejects_invalid_radius_boundaries` | Must be killed or proven equivalent |
| Zero, negative, and non-numeric radius | Reject at construction with `ValueError` | PO-CIRCLE-001 | `test_circle_pdf_rejects_invalid_radius_boundaries` | Must be killed or proven equivalent |
| PDF circle rendering | Emit one move-to, four cubic operators using kappa control distance, close path, and paint | PO-CIRCLE-002 | `test_circle_pdf_emits_four_cubic_bezier_segments` | Must be killed or proven equivalent |
| Renderer-neutral circle materialization | Materialize to `CircleSVG` or `CirclePDF` with matching position/radius | PO-CIRCLE-003 | `test_circle_drawing_materializes_svg_and_pdf_components` | Must be killed or proven equivalent |
| DXF circle output | Emit one native `CIRCLE` entity with layer, center, z=0, and radius | PO-CIRCLE-004 | `test_dxf_circle_drawing_emits_native_circle_entity` | Must be killed or proven equivalent |
| Mutation of inherited `size`, negative base coordinates, style paint semantics, and SVG circle internals | Excluded from proven domain | Explicit exclusions in PO-CIRCLE-001 through PO-CIRCLE-004 | existing tests only | Out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Radius validation and PDF operator generation are deterministic. | `test_circle_pdf_rejects_invalid_radius_boundaries`; `test_circle_pdf_emits_four_cubic_bezier_segments` |
| Behavioral/condition | yes | CIRCLE-P1 defines expected circle behavior across PDF, neutral recipe, and DXF paths. | New tests are marked `@pytest.mark.condition("CIRCLE-P1")`. |
| Failure-mode | yes | Invalid radius values must fail at construction. | `test_circle_pdf_rejects_invalid_radius_boundaries` |
| Integration/live-path | yes | DXF must exercise the public neutral group path, not just `_circle_entity()`. | `test_dxf_circle_drawing_emits_native_circle_entity` calls `DXFDocument.add_group()`. |
| Contract/API compatibility | yes | Existing circle serialization and renderer-neutral materialization must remain stable. | Existing SVG/PDF tests plus CIRCLE-P1 tests. |
| Property/fuzz | limited | The PDF approximation is a fixed deterministic operator sequence rather than a broad input relation. | Exact operator tests over one representative circle. |
| Mutation | yes | Radius validation, PDF kappa/path terms, materialization, and DXF entity generation are proof-critical. | Mutation run result recorded below. |
| Security/adversarial | no | The slice adds no file path, network, subprocess, auth, secrets, SQL, template, deserialization, font, image, or active-content surface. | Not applicable. |
| Performance/resource | no | The slice adds no unbounded loop or cache. | Not applicable. |
| Concurrency/race | no | The slice adds no shared mutable global state, background workers, sessions, locks, queues, or temp-file coordination. | Not applicable. |
| Observability/logging | no | The slice adds no state-changing service, background work, external call, or recovery path. | Not applicable. |
| Golden artifact/visual | yes | PDF and DXF generated geometry must be stable enough for synthetic fixtures. | PDF operator test and DXF entity test. |
| Regression | yes | This slice extends the renderer proof pattern to circle output before a reported defect. | CIRCLE-P1 tests named above. |

## Invariants, Preconditions, And Postconditions

Invariants:

- PDF circle radius is numeric and strictly positive after public construction.
- PDF circle output uses four cubic Bezier segments with the standard kappa
  control distance.
- PDF circle output is closed.
- Neutral circle recipes preserve position and radius across SVG and PDF
  materialization.
- DXF circle output uses a native `CIRCLE` entity with center z-coordinate `0`.

Preconditions:

- Position is accepted by `SingleDimensionDrawingComponent`.
- Radius is finite, numeric, and greater than zero.
- Callers do not monkey-patch renderer classes or mutate inherited private
  fields.

Postconditions:

- `CirclePDF.generate_pdf()` emits a deterministic closed PDF path.
- `CircleDrawing.to_component(OutputFormat.SVG)` returns `CircleSVG`.
- `CircleDrawing.to_component(OutputFormat.PDF)` returns `CirclePDF`.
- `DXFDocument.add_group()` emits one native `CIRCLE` entity for each neutral
  `CircleDrawing`.

## Mutation Testing Gate

Proof-critical mutation targets:

- Weakening radius validation should fail invalid-radius tests.
- Changing kappa, radius, control-point signs, endpoint positions, close-path
  output, or paint output should fail PDF operator tests.
- Redirecting `CircleDrawing.to_component()` should fail materialization tests.
- Changing DXF entity type, layer, center, z, or radius group codes should fail
  DXF entity tests.

Current result:

- Tool and version: Cosmic Ray 8.4.6 in WSL.
- Mutated source paths: `src/InkGen/drawing_components.py`,
  `src/InkGen/pdf_generator.py`, and `src/InkGen/dxf_generator.py`.
- Reproducible setup:
  `cosmic-ray baseline tests/mutation/circle_cosmic_ray.toml`,
  `cosmic-ray init tests/mutation/circle_cosmic_ray.toml
  /tmp/inkgen_circle_mutation.sqlite`, then
  `python tests/mutation/filter_circle_work_items.py
  /tmp/inkgen_circle_mutation.sqlite --clear-results`.
- Test selection:
  `python -m pytest -x tests/test_circle_contract.py
  tests/test_drawing_components.py tests/test_pdf_generator.py
  tests/test_dxf_generator.py`.
- Proof-critical work items after filtering: 280.
- Mutants killed: 278.
- Mutants survived: 2.
- Mutants excluded/equivalent: 2 equivalent mutants:

  - `src/InkGen/drawing_components.py:244`: `target == OutputFormat.SVG` and
    `target >= OutputFormat.SVG`. Within the declared public domain,
    `normalize_output_format()` returns one of exactly two string-enum values:
    `OutputFormat.SVG == "svg"` or `OutputFormat.PDF == "pdf"`. Therefore:

    ```text
    OutputFormat.SVG is OutputFormat.SVG => true
    OutputFormat.SVG == OutputFormat.SVG => true
    OutputFormat.SVG >= OutputFormat.SVG => true
    OutputFormat.PDF is OutputFormat.SVG => false
    OutputFormat.PDF == OutputFormat.SVG => false
    OutputFormat.PDF >= OutputFormat.SVG => false, because "pdf" < "svg"
    ```

    If a future output format is added, this equivalence must be revisited.

During mutation, real test gaps were found and closed:

- PDF path assertions originally used substring checks, allowing `15 ...` to
  satisfy an expected `5 ...` operator fragment. Tests now compare complete
  content-stream lines.
- DXF tests originally asserted the `CIRCLE` value was present but did not
  require the preceding group code to be `0`. Tests now require the `0/CIRCLE`
  pair.

Gate result: passed for the declared domain. The mutation report has no
surviving non-equivalent proof-critical mutants.

The companion RADIAL-SCALAR-P2 slice closes the former boolean and non-finite
circle radius boundary gap for SVG/PDF circle components and neutral
materialization.

## PO-CIRCLE-001: Positive Radius Boundary

### Claim

`CirclePDF` construction accepts numeric positive radius values and rejects
zero, negative, and non-numeric radius values.

### Domain

All public `CirclePDF` constructor calls with ordinary finite radius-like
values.

### Proof Method

`CirclePDF.__init__()` checks `isinstance(radius, (float, int)) and radius > 0`
before delegating to `SingleDimensionDrawingComponent`. Otherwise it raises
`ValueError`. Therefore zero, negative, and non-numeric values do not construct
a `CirclePDF`.

### Conclusion

Proven for the stated domain.

## PO-CIRCLE-002: PDF Four-Cubic Circle Path

### Claim

`CirclePDF.generate_pdf()` emits a closed PDF path made from four cubic Bezier
segments using the standard kappa control distance.

### Domain

All `CirclePDF` instances in the stated circle domain.

### Proof Method

Static path proof over `CirclePDF.generate_pdf()`:

1. The method reads `x`, `y`, and `radius` from public properties.
2. It computes `control = radius * 0.5522847498307936`.
3. It emits a move-to at `(x + radius, y)`.
4. It emits four cubic `c` operators whose endpoints are the top, left, bottom,
   and right compass points and whose controls are offset by `control`.
5. It appends `h` and delegates to `_drawing_pdf()`.
6. Therefore the PDF path is the declared four-cubic approximation and is
   closed.

### Conclusion

Proven for the stated domain.

## PO-CIRCLE-003: Neutral Circle Materializes To SVG And PDF

### Claim

`CircleDrawing.to_component()` materializes neutral circle recipes into SVG and
PDF circle components without changing position or radius.

### Domain

All `CircleDrawing` instances with supported output formats `SVG` and `PDF`.

### Proof Method

`CircleDrawing.to_component()` normalizes the requested output format. For SVG
it returns `CircleSVG(self.position, self.radius, self.style)`. For PDF it
returns `CirclePDF(self.position, self.radius, self.style)`. Therefore position
and radius are preserved.

### Conclusion

Proven for the stated domain.

## PO-CIRCLE-004: DXF Uses Native Circle Entity

### Claim

DXF export for a neutral `CircleDrawing` emits a native `CIRCLE` entity with the
neutral circle's layer, center, z-coordinate, and radius.

### Domain

All `CircleDrawing` instances exported through `DXFDocument.add_group()`.

### Proof Method

Static path proof over `dxf_generator.py`:

1. `DXFDocument.add_group()` iterates over `group.components`.
2. `_component_to_entities()` matches `CircleDrawing`.
3. It returns `_circle_entity(component, context)`.
4. `_circle_entity()` emits DXF code/value pairs for `CIRCLE`, layer, center x,
   center y, z-coordinate `0.0`, and `component.radius`.
5. Therefore DXF output uses a native circle entity and preserves the neutral
   circle radius.

### Conclusion

Proven for the stated domain.

## Current Slice Decision

The slice has validation proof for PDF circle radius, deterministic PDF
four-cubic path proof, renderer-neutral SVG/PDF materialization evidence, and
live-path native DXF circle export evidence.

The main design constraint is that DXF circle export intentionally uses a native
`CIRCLE` entity instead of the PDF four-cubic approximation. That distinction is
now explicit and tested.
