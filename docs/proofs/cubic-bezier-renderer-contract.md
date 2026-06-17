# Cubic Bezier Renderer Contract Proof Obligations

This note applies the InkGen Definition of Done to the CUBIC-P1 cubic Bezier
renderer-contract slice. It focuses on cubic Bezier sampling, point validation,
and the dependency path from renderer-neutral drawing recipes into PDF and DXF
output.

## Scope

The slice covers cubic Bezier geometry owned by `src/InkGen/component.py`, native
PDF cubic rendering in `src/InkGen/pdf_generator.py`, renderer-neutral
materialization in `src/InkGen/drawing_components.py`, and DXF curve export in
`src/InkGen/dxf_generator.py`.

The public behavior under review is:

- `CubicBezier._coerce_point()`
- `CubicBezier.points`
- `CubicBezierPDF.generate_pdf()`
- `CubicBezierDrawing.to_component(OutputFormat.PDF)`
- `DXFDocument.add_group()` for `CubicBezierDrawing`

## Architecture Impact

Affected surface:

- `src/InkGen/component.py`: source of sampled cubic Bezier geometry and point
  validation.
- `src/InkGen/pdf_generator.py`: PDF rendering using the native cubic `c`
  operator.
- `src/InkGen/drawing_components.py`: neutral cubic recipe materialization to
  concrete renderers.
- `src/InkGen/dxf_generator.py`: DXF polyline output that intentionally reuses
  PDF-materialized sampled points for curves.
- `tests/test_curve_contract.py`: math, validation, renderer, and
  dependency-path evidence.

Incoming dependencies:

- SVG/PDF/DXF renderers, labels, masks, truth emitters, generated fixtures, and
  synthetic drawing consumers rely on stable cubic `points`, `bbox`, and
  `convex_hull` semantics.
- PDF fixture consumers rely on `CubicBezierPDF.generate_pdf()` emitting a
  native open cubic path with the same control points supplied by callers.
- DXF export relies on `CubicBezierDrawing.to_component(OutputFormat.PDF)`
  returning a concrete component whose sampled `points` represent the neutral
  cubic curve.

Outgoing dependencies:

- `CubicBezier` depends only on numeric point inputs, `DrawingStyle`, and the
  shared `PRECISION` / `DEFAULT_CURVE_SAMPLES` constants.
- `CubicBezierPDF` depends on the shared component point/control contract and
  the local `_drawing_pdf()` helper.
- `DXFDocument` depends on renderer-neutral drawing recipes and intentionally
  materializes curve-like drawings through the PDF path for sampled geometry.

Before/after edge changes:

- No new production dependency edge was added in this slice.
- The existing edge
  `dxf_generator.py -> component.to_component(OutputFormat.PDF)` for sampled
  geometry is now explicitly tested for `CubicBezierDrawing`.
- The existing neutral recipe edge `CubicBezierDrawing -> CubicBezierPDF` is
  now explicitly tested for PDF output.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced. Components do not import PDF or DXF.
- Layer check: concrete renderers depend on component geometry and neutral
  recipes according to `docs/dependency-map.md`.
- Coupling check: DXF's reuse of PDF sampled points is explicit and tested.
- Redundancy check: the slice avoids introducing a second cubic sampling
  implementation for PDF or DXF.

Evidence source and freshness:

- Source-backed: `component.py`, `pdf_generator.py`, `drawing_components.py`,
  and `dxf_generator.py` were read before adding tests.
- Test-backed: focused tests in `test_curve_contract.py` exercise the math,
  validation, and live dependency paths.
- Design-backed: `docs/dependency-map.md` already records the DXF-to-PDF
  sampled geometry edge as intentional.
- No architecture claim in this section relies only on stale memory.

ADR/rule impact:

- No new ADR is required because no new architecture decision was made.
- A future change that replaces DXF sampled cubic rendering with a native curve
  entity should add or update an ADR because it changes the generated-artifact
  contract and dependency direction.

## Domain Definitions

- A cubic Bezier is defined by numeric `start_point`, `control_point1`,
  `control_point2`, and `end_point` coordinate pairs.
- `DEFAULT_CURVE_SAMPLES` is the positive integer number of sample intervals.
- `PRECISION` is the number of decimal places used by InkGen component point
  output.
- `CubicBezier.points` returns sample points for `t = i /
  DEFAULT_CURVE_SAMPLES`, for integer `i` from `0` through
  `DEFAULT_CURVE_SAMPLES`, rounded to `PRECISION`.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid numeric start/control/end points | Emit sampled points from the cubic Bernstein formula, rounded to `PRECISION` | PO-CUBIC-001 | `test_cubic_bezier_samples_follow_formula_and_control_bounds` | Must be killed or proven equivalent |
| Degenerate but valid coordinates, including vertical/tied x coordinates | Preserve formula output and endpoint identities | PO-CUBIC-001 | `test_cubic_bezier_samples_follow_formula_and_control_bounds` | Must be killed or proven equivalent |
| Malformed coordinate tuples | Reject at construction and setter boundaries with `ValueError` | PO-CUBIC-002 | `test_cubic_bezier_rejects_malformed_points` | Must be killed or proven equivalent |
| PDF cubic rendering | Emit one open native PDF cubic operator and use stroke-only painting | PO-CUBIC-003 | `test_cubic_bezier_pdf_emits_exact_cubic_operator` | Must be killed or proven equivalent |
| Renderer-neutral cubic drawing exported to DXF | Materialize to PDF and emit DXF polyline vertices from the same sampled points | PO-CUBIC-004 | `test_cubic_drawing_materializes_pdf_component`; `test_dxf_cubic_bezier_reuses_pdf_sample_points` | Must be killed or proven equivalent |
| Non-numeric points, non-finite values, hostile mutation of private fields, monkey-patched renderers, non-default sample counts, and native DXF cubic entities | Excluded from proven domain | Explicit exclusions in PO-CUBIC-001 through PO-CUBIC-004 | none | Out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Cubic sampling and point validation are deterministic math/validation units. | `test_cubic_bezier_samples_follow_formula_and_control_bounds`; `test_cubic_bezier_rejects_malformed_points` |
| Behavioral/condition | yes | CUBIC-P1 defines expected cubic behavior across component, PDF, neutral recipe, and DXF paths. | New tests are marked `@pytest.mark.condition("CUBIC-P1")`. |
| Failure-mode | yes | Malformed coordinate tuples are invalid construction/setter inputs. | `test_cubic_bezier_rejects_malformed_points` |
| Integration/live-path | yes | DXF must exercise the public neutral group path, not just a helper. | `test_dxf_cubic_bezier_reuses_pdf_sample_points` calls `DXFDocument.add_group()`. |
| Contract/API compatibility | yes | Existing point/control contracts must remain stable. | Existing cubic parameter tests plus CUBIC-P1 point tests. |
| Property/fuzz | yes | Cubic sampling has a deterministic formula over sampled `t` values. | Deterministic bounded property-style tests plus algebraic proof below. |
| Mutation | yes | Cubic sampling, point validation, renderer dispatch, and PDF/DXF path generation are proof-critical. | Mutation run result recorded below. |
| Security/adversarial | no | The slice adds no file path, network, subprocess, auth, secrets, SQL, template, deserialization, font, image, or active-content surface. | Not applicable. |
| Performance/resource | no | The slice uses fixed `DEFAULT_CURVE_SAMPLES` and adds no unbounded loop or cache. | Not applicable. |
| Concurrency/race | no | The slice adds no shared mutable global state, background workers, sessions, locks, queues, or temp-file coordination. | Not applicable. |
| Observability/logging | no | The slice adds no state-changing service, background work, external call, or recovery path. | Not applicable. |
| Golden artifact/visual | yes | PDF and DXF generated geometry must be stable enough for synthetic fixtures. | PDF operator/path test and DXF vertex test. |
| Regression | yes | This slice extends the prior curve-proof pattern to a similar renderer dependency path before a defect is reported. | CUBIC-P1 tests named above. |

## Invariants, Preconditions, And Postconditions

Invariants:

- Cubic sampled points are computed from the cubic Bernstein basis and rounded
  to `PRECISION`.
- The first sampled point is the start point and the last sampled point is the
  end point.
- Each sampled point is a convex combination of the four cubic controls and
  therefore lies inside the axis-aligned control-point bounds.
- Public point setters and construction preserve two-coordinate point shape.
- PDF output uses the supplied start/control/end points in one native cubic
  operator, while DXF output uses sampled component points.

Preconditions:

- Each point is a two-item numeric tuple/list accepted by `CubicBezier`.
- Callers do not monkey-patch curve classes or mutate private fields.

Postconditions:

- `CubicBezier.points` returns `DEFAULT_CURVE_SAMPLES + 1` sampled points.
- `CubicBezierPDF.generate_pdf()` emits an open PDF path with one `c` operator
  and stroke-only painting.
- `DXFDocument.add_group()` emits an open `LWPOLYLINE` whose vertices match the
  PDF-materialized cubic sample points.

## Mutation Testing Gate

Proof-critical mutation targets:

- Changing any Bernstein coefficient, power, interpolation, endpoint, or
  rounding term in `CubicBezier.points` should fail formula and endpoint tests.
- Weakening point tuple validation should fail invalid-point tests.
- Closing, filling, or changing the PDF cubic path should fail PDF operator
  tests.
- Redirecting DXF cubic export away from
  `component.to_component(OutputFormat.PDF).points` without preserving vertices
  should fail the DXF dependency-path test.

Current result:

- Tool and version: Cosmic Ray 8.4.6 in WSL.
- Mutated source paths: `src/InkGen/component.py`,
  `src/InkGen/drawing_components.py`, `src/InkGen/pdf_generator.py`, and
  `src/InkGen/dxf_generator.py`.
- Reproducible setup:
  `cosmic-ray baseline tests/mutation/cubic_bezier_cosmic_ray.toml`,
  `cosmic-ray init tests/mutation/cubic_bezier_cosmic_ray.toml
  /tmp/inkgen_cubic_mutation.sqlite`, then
  `python tests/mutation/filter_cubic_bezier_work_items.py
  /tmp/inkgen_cubic_mutation.sqlite --clear-results`.
- Test selection:
  `python -m pytest -x tests/test_curve_contract.py
  tests/test_drawing_components.py tests/test_pdf_generator.py
  tests/test_dxf_generator.py`.
- Proof-critical work items after filtering: 447.
- Mutants killed: 444.
- Mutants survived: 3.
- Mutants excluded/equivalent: 3 equivalent mutants:

  - `src/InkGen/component.py:1549`: `range(self._samples ^ 1)`. Within the
    declared public domain, `CubicBezier.__init__()` assigns
    `_samples = max(1, DEFAULT_CURVE_SAMPLES)` and
    `DEFAULT_CURVE_SAMPLES == 32`, so:

    ```text
    _samples + 1 == 33
    _samples ^ 1 == 33
    ```

  - `src/InkGen/drawing_components.py:163`: `target == OutputFormat.SVG` and
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

During the first mutation pass, a real test gap was found in the point-shape
boundary: a mutant changing `len(point) != 2` to `len(point) < 2` accepted
three-coordinate tuples. The `test_cubic_bezier_rejects_malformed_points`
regression now covers both too few and too many coordinates and kills that
mutant.

Gate result: passed for the declared domain. The mutation report has no
surviving non-equivalent proof-critical mutants.

## PO-CUBIC-001: Cubic Bernstein Sample Formula

### Claim

`CubicBezier.points` emits points from the cubic Bernstein formula rounded to
InkGen `PRECISION`.

### Domain

All cubic Bezier components with finite numeric start, control, and end points
and the default positive sample interval count.

### Assumptions

- `round(value, PRECISION)` is the public point precision contract for InkGen
  components.
- `DEFAULT_CURVE_SAMPLES` is positive in the constructed public component.

### Theorem

For every sample index `i` where `0 <= i <= DEFAULT_CURVE_SAMPLES`, with:

```text
t = i / DEFAULT_CURVE_SAMPLES
u = 1 - t
```

the emitted point is:

```text
round(u^3*S.x + 3*u^2*t*C1.x + 3*u*t^2*C2.x + t^3*E.x, PRECISION)
round(u^3*S.y + 3*u^2*t*C1.y + 3*u*t^2*C2.y + t^3*E.y, PRECISION)
```

### Proof Method

Static/algebraic reasoning over `CubicBezier.points`:

1. The method iterates `step` from `0` through `_samples`.
2. It assigns `t = step / _samples` and `one_minus_t = 1.0 - t`.
3. It computes x and y with the four cubic Bernstein terms.
4. It appends each coordinate rounded to `PRECISION`.
5. Therefore every emitted point matches the theorem.

The four Bernstein basis weights sum to:

```text
u^3 + 3*u^2*t + 3*u*t^2 + t^3 = (u + t)^3 = 1
```

Each weight is non-negative for `0 <= t <= 1`, so every unrounded sampled point
is inside the convex hull of the control points and therefore inside their
axis-aligned bounds.

### Counterexamples And Exclusions

- Non-finite numeric values are outside the proof.
- Direct mutation of `_samples` to a non-positive or non-default value is outside
  the public construction contract.
- Rounding can move a value by up to the precision unit; exact unrounded curve
  membership is not claimed for serialized points.

### Conclusion

Proven for the stated domain.

## PO-CUBIC-002: Point Shape Boundary

### Claim

Cubic Bezier point inputs have exactly two coordinates after construction and
after public setter calls.

### Domain

All public construction and setter calls for cubic start, control, and end
points.

### Proof Method

Construction calls `_coerce_point()` for all four point inputs, and every public
point setter calls the same helper. `_coerce_point()` raises `ValueError` when
the supplied point length is not exactly two and otherwise stores floats for the
two coordinates. Therefore no public construction or setter path can store a
malformed coordinate tuple.

### Conclusion

Proven for the stated domain.

## PO-CUBIC-003: PDF Cubic Uses Native Open Cubic Operator

### Claim

`CubicBezierPDF.generate_pdf()` emits an open, stroke-only PDF path containing
one native cubic `c` operator.

### Domain

All `CubicBezierPDF` instances in the stated cubic domain.

### Proof Method

`CubicBezierPDF.generate_pdf()` builds a path with one move-to operator from
`start_point` and one cubic operator from `control_point1`, `control_point2`,
and `end_point`. It passes that path to `_drawing_pdf(..., fill=False)`.
Therefore the path is open, uses the supplied cubic controls, and uses
stroke-only painting.

### Conclusion

Proven for the stated domain.

## PO-CUBIC-004: DXF Reuses PDF-Sampled Neutral Cubic Geometry

### Claim

DXF export for a neutral `CubicBezierDrawing` emits vertices from the same
sampled points as the neutral cubic's PDF materialization.

### Domain

All `CubicBezierDrawing` instances exported through `DXFDocument.add_group()`.

### Proof Method

Static path proof over `drawing_components.py` and `dxf_generator.py`:

1. `CubicBezierDrawing.to_component(OutputFormat.PDF)` returns a
   `CubicBezierPDF`.
2. `DXFDocument.add_group()` iterates over `group.components`.
3. `_component_to_entities()` matches `CubicBezierDrawing` in the curve branch.
4. That branch assigns `concrete = component.to_component(OutputFormat.PDF)`.
5. It returns `_lwpolyline_entity(concrete.points, context, closed=False)`.
6. `_lwpolyline_entity()` emits one vertex for each supplied point.
7. Therefore the generated vertices are the PDF-materialized sampled points,
   transformed only by `DXFRenderContext.point()`.

### Counterexamples And Exclusions

- Native DXF spline/entity output is not part of the current contract.
- If DXF changes to a native curve representation, this proof must be replaced
  and an ADR should record the new dependency direction.

### Conclusion

Proven for the stated domain.

## Current Slice Decision

The slice has mathematical proof for cubic Bernstein sampling, point shape
validation, and native open cubic PDF rendering, plus live-path evidence for
neutral recipe and DXF dependency propagation.

The main design constraint is that DXF cubic export intentionally depends on
sampled component points, not native DXF spline entities. That edge is now
explicit and tested.
