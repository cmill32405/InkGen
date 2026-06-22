# Quadratic Bezier Renderer Contract Proof Obligations

This note applies the InkGen Definition of Done to the CURVE-P1 quadratic
Bezier renderer-contract slice. It focuses on mathematical curve semantics and
the dependency path from renderer-neutral drawing recipes into PDF and DXF
output.

## Scope

The slice covers quadratic Bezier geometry owned by
`src/InkGen/component.py`, PDF quadratic-to-cubic rendering in
`src/InkGen/pdf_generator.py`, renderer-neutral materialization in
`src/InkGen/drawing_components.py`, and DXF curve export in
`src/InkGen/dxf_generator.py`.

The public behavior under review is:

- `QuadraticBezier.points`
- `QuadraticBezierPDF.generate_pdf()`
- `QuadraticBezierDrawing.to_component(OutputFormat.PDF)`
- `DXFDocument.add_group()` for `QuadraticBezierDrawing`

## Architecture Impact

Affected surface:

- `src/InkGen/component.py`: source of quadratic Bezier sampled point geometry.
- `src/InkGen/pdf_generator.py`: conversion of quadratic Bezier controls into
  cubic PDF operators.
- `src/InkGen/drawing_components.py`: neutral curve recipe materialization to
  concrete renderers.
- `src/InkGen/dxf_generator.py`: DXF polyline output that intentionally reuses
  PDF-materialized sampled points for curves.
- `tests/test_curve_contract.py`, `tests/test_component.py`,
  `tests/test_pdf_generator.py`, and `tests/test_dxf_generator.py`: math,
  renderer, and dependency-path evidence.

Incoming dependencies:

- Labels, masks, truth emitters, generated fixtures, and DXF export rely on
  stable component `points`, `bbox`, and `convex_hull` semantics.
- PDF fixture consumers rely on `QuadraticBezierPDF.generate_pdf()` emitting a
  curve that matches the neutral quadratic geometry.
- DXF export relies on `QuadraticBezierDrawing.to_component(OutputFormat.PDF)`
  returning a concrete component whose sampled `points` represent the neutral
  curve.

Outgoing dependencies:

- `QuadraticBezier` depends only on numeric point inputs, `DrawingStyle`, and
  the shared `PRECISION` / `DEFAULT_CURVE_SAMPLES` constants.
- `QuadraticBezierPDF` depends on the shared component geometry contract and the
  private `_quadratic_to_cubic()` helper for PDF's cubic curve operator.
- `DXFDocument` depends on renderer-neutral drawing recipes and intentionally
  materializes curves through the PDF path for sampled geometry.

Before/after edge changes:

- No new production dependency edge was added in this slice.
- The existing edge
  `dxf_generator.py -> component.to_component(OutputFormat.PDF)` for sampled
  geometry is now explicitly tested for `QuadraticBezierDrawing`.
- The PDF quadratic-to-cubic helper remains local to `pdf_generator.py`.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced. Components do not import PDF or DXF.
- Layer check: concrete renderers depend on component geometry and neutral
  recipes according to `docs/dependency-map.md`.
- Coupling check: DXF's reuse of PDF sampled points is explicit and tested,
  rather than hidden as an unverified side effect.
- Redundancy check: the slice avoids introducing a second quadratic sampling
  implementation for DXF.

Evidence source and freshness:

- Source-backed: `component.py`, `pdf_generator.py`, `drawing_components.py`,
  and `dxf_generator.py` were read before adding tests.
- Test-backed: focused tests in `test_curve_contract.py`,
  `test_component.py`, `test_pdf_generator.py`, and `test_dxf_generator.py`
  exercise the math and live dependency path.
- Design-backed: `docs/dependency-map.md` already records the DXF-to-PDF sampled
  geometry edge as intentional.
- No architecture claim in this section relies only on stale memory.

ADR/rule impact:

- No new ADR is required because no new architecture decision was made.
- A future change that replaces DXF's PDF-materialized curve sampling with a
  native DXF curve strategy should add or update an ADR because it changes the
  accepted dependency and generated-artifact contract.

## Domain Definitions

- A quadratic Bezier is defined by numeric points `S`, `C`, and `E`.
- `S` is the start point, `C` is the control point, and `E` is the end point.
- `DEFAULT_CURVE_SAMPLES` is the positive integer number of sample intervals.
- `PRECISION` is the number of decimal places used by InkGen component point
  output.
- `QuadraticBezier.points` returns sample points for
  `t = i / DEFAULT_CURVE_SAMPLES`, for integer `i` from `0` through
  `DEFAULT_CURVE_SAMPLES`, rounded to `PRECISION`.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid numeric start/control/end points | Emit sampled points from the quadratic formula, rounded to `PRECISION` | PO-QB-001 | `tests/test_curve_contract.py::test_quadratic_bezier_samples_follow_formula_and_control_bounds` | Must be killed or proven equivalent |
| `t == 0` and `t == 1` endpoints | Preserve start and end points exactly after rounding | PO-QB-001 | `test_quadratic_bezier_points`; `test_quadratic_bezier_samples_follow_formula_and_control_bounds` | Must be killed or proven equivalent |
| PDF quadratic rendering | Convert quadratic controls to an equivalent cubic PDF curve | PO-QB-002 | `test_pdf_quadratic_to_cubic_conversion_is_curve_equivalent`; `test_quadratic_bezier_pdf_emits_equivalent_cubic_operator` | Must be killed or proven equivalent |
| Renderer-neutral quadratic drawing exported to DXF | Materialize to PDF and emit DXF polyline vertices from the same sampled points | PO-QB-003 | `test_dxf_quadratic_bezier_reuses_pdf_sample_points` | Must be killed or proven equivalent |
| Parameter round trip | Preserve quadratic geometry parameters | Compatibility invariant | `test_quadratic_bezier_points`; `test_pdf_primitives_round_trip_parameters` | Must be killed or proven equivalent |
| Hostile mutation of private fields, monkey-patched renderers, non-default sample counts, and native DXF curve entities | Excluded from proven domain | Explicit exclusions in PO-QB-001 through PO-QB-003 | none | Out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Quadratic sampling and PDF control conversion are small deterministic math units. | `test_quadratic_bezier_samples_follow_formula_and_control_bounds`; `test_pdf_quadratic_to_cubic_conversion_is_curve_equivalent` |
| Behavioral/condition | yes | CURVE-P1 defines expected quadratic curve behavior across component, PDF, and DXF paths. | New tests are marked `@pytest.mark.condition("CURVE-P1")`. |
| Failure-mode | limited no | This slice did not change input validation or error paths. Existing invalid radius/path tests cover adjacent curve-family failures. | Not applicable for this geometry-equivalence slice. |
| Integration/live-path | yes | DXF must exercise the public neutral group path, not just a helper. | `test_dxf_quadratic_bezier_reuses_pdf_sample_points` calls `DXFDocument.add_group()`. |
| Contract/API compatibility | yes | Existing point and parameter contracts must remain stable. | Existing quadratic parameter tests and PDF primitive round-trip tests. |
| Property/fuzz | yes | Curve equivalence is an invariant over sampled `t` values and representative control-point partitions. | Deterministic bounded property-style tests plus algebraic proof below. |
| Mutation | yes | `_quadratic_to_cubic()` and `QuadraticBezier.points` are proof-critical math logic. | Mutation run result recorded below. |
| Security/adversarial | no | The slice adds no file path, network, subprocess, auth, secrets, SQL, template, deserialization, font, image, or active-content surface. | Not applicable. |
| Performance/resource | no | The slice uses fixed `DEFAULT_CURVE_SAMPLES` and adds no unbounded loop or cache. | Not applicable. |
| Concurrency/race | no | The slice adds no shared mutable global state, background workers, sessions, locks, queues, or temp-file coordination. | Not applicable. |
| Golden artifact/visual | yes | PDF and DXF generated geometry must be stable enough for synthetic fixtures. | PDF operator test and DXF vertex test. |
| Regression | yes | The tests guard against future drift in sampled geometry, PDF conversion, and DXF dependency behavior. | CURVE-P1 tests named above. |

## Invariants, Preconditions, And Postconditions

Invariants:

- Quadratic sampled points are computed from the quadratic Bezier formula and
  rounded to `PRECISION`.
- The first sampled point is the start point and the last sampled point is the
  end point.
- Every sampled point is a convex combination of start, control, and end, so it
  lies inside the convex hull of those control points.
- The PDF cubic controls produced by `_quadratic_to_cubic()` define the same
  curve as the quadratic for every `t` in `[0, 1]`.
- DXF curve output uses the same sampled points as the neutral curve's PDF
  materialization path.

Preconditions:

- Start, control, and end points are two-item numeric tuples/lists accepted by
  `QuadraticBezier`.
- `DEFAULT_CURVE_SAMPLES` is positive.
- Callers do not monkey-patch curve classes or mutate private fields.

Postconditions:

- `QuadraticBezier.points` returns `DEFAULT_CURVE_SAMPLES + 1` sampled points.
- `QuadraticBezierPDF.generate_pdf()` emits one PDF move operator and one cubic
  curve operator for the quadratic.
- `DXFDocument.add_group()` emits an open `LWPOLYLINE` whose vertices match the
  PDF-materialized quadratic sample points.

## Mutation Testing Gate

Proof-critical mutation targets:

- Changing any quadratic basis coefficient in `QuadraticBezier.points` should
  fail the formula and endpoint tests.
- Changing the `2/3` conversion factor in `_quadratic_to_cubic()` should fail
  the curve-equivalence test and PDF operator test.
- Redirecting DXF curve export away from `component.to_component(OutputFormat.PDF).points`
  without preserving vertices should fail the DXF dependency-path test.

Current result:

- Tool and version: Cosmic Ray 8.4.6 in WSL.
- Mutated source paths: `src/InkGen/component.py`,
  `src/InkGen/pdf_generator.py`, and `src/InkGen/dxf_generator.py`.
- Reproducible setup:
  `cosmic-ray baseline tests/mutation/quadratic_bezier_cosmic_ray.toml`,
  `cosmic-ray init tests/mutation/quadratic_bezier_cosmic_ray.toml
  /tmp/inkgen_curve_mutation.sqlite`, then
  `python tests/mutation/filter_quadratic_bezier_work_items.py
  /tmp/inkgen_curve_mutation.sqlite --clear-results`.
- Test selection:
  `python -m pytest -x tests/test_curve_contract.py tests/test_component.py
  tests/test_pdf_generator.py tests/test_dxf_generator.py`.
- Proof-critical work items after filtering: 513.
- Mutants killed: 511.
- Mutants survived: 2.
- Mutants excluded/equivalent: 2 equivalent mutants at
  `src/InkGen/component.py:1454`:
  `range(self._samples | 1)` and `range(self._samples ^ 1)`.
  Within the declared public domain, `QuadraticBezier.__init__()` assigns
  `_samples = max(1, DEFAULT_CURVE_SAMPLES)` and
  `DEFAULT_CURVE_SAMPLES == 32`, so:

  ```text
  _samples + 1 == 33
  _samples | 1 == 33
  _samples ^ 1 == 33
  ```

  Direct mutation of `_samples` or non-default sample counts are excluded from
  PO-QB-001.
- Gate result: passed for the declared domain. The mutation report has no
  surviving non-equivalent proof-critical mutants.

During the first broader mutation pass, a real test gap was found in
`QuadraticBezierPDF.generate_pdf()`: the operator test used a curve whose
second cubic control point had `x == y`, so coordinate-index mutations survived.
The test now uses an asymmetric second cubic control point and the refined gate
kills those mutants.

The companion BEZIER-FINITE-P2 slice closes the former non-finite public point
input exclusion for quadratic and cubic Bezier components.

## PO-QB-001: Quadratic Sample Formula

### Claim

`QuadraticBezier.points` emits points from the quadratic Bezier formula rounded
to InkGen `PRECISION`.

### Domain

All quadratic Bezier components with numeric points `S`, `C`, and `E`, using
the default positive sample interval count.

### Assumptions

- Python arithmetic and exponentiation have their standard meanings for finite
  numeric values.
- `round(value, PRECISION)` is the public point precision contract for InkGen
  components.

### Theorem

For every sample index `i` where `0 <= i <= DEFAULT_CURVE_SAMPLES`, with
`t = i / DEFAULT_CURVE_SAMPLES`, the emitted point is:

```text
round((1 - t)^2*S + 2*(1 - t)*t*C + t^2*E, PRECISION)
```

applied independently to x and y coordinates.

### Proof Method

Static/algebraic reasoning over `QuadraticBezier.points`:

1. The method iterates `step` from `0` through `_samples`.
2. It assigns `t = step / _samples`.
3. It assigns `one_minus_t = 1.0 - t`.
4. It computes x and y using the exact quadratic Bezier basis:
   `(1-t)^2*S + 2*(1-t)*t*C + t^2*E`.
5. It appends each coordinate rounded to `PRECISION`.
6. Therefore every emitted point matches the theorem.

At `t = 0`, the basis weights are `1, 0, 0`, so the point is `S`. At `t = 1`,
the basis weights are `0, 0, 1`, so the point is `E`.

The basis weights are non-negative and sum to 1 for every `t` in `[0, 1]`, so
each unrounded sample is a convex combination of `S`, `C`, and `E`.

### Counterexamples And Exclusions

- Direct mutation of `_samples` to a non-positive value is outside the public
  construction contract.
- Rounding can move a value by up to the precision unit; exact unrounded curve
  membership is not claimed for serialized points.

### Conclusion

Proven for the stated domain.

## PO-QB-002: PDF Quadratic-To-Cubic Equivalence

### Claim

The PDF cubic control points produced from a quadratic Bezier define the same
curve as the original quadratic.

### Domain

All finite numeric start, control, and end points.

### Assumptions

- PDF represents quadratic Beziers through cubic Bezier operators.
- The cubic Bezier formula has its standard Bernstein-basis meaning.

### Theorem

For quadratic points `S`, `Q`, and `E`, let:

```text
C1 = S + 2/3 * (Q - S)
C2 = E + 2/3 * (Q - E)
```

Then for every `t` in `[0, 1]`, the cubic Bezier `(S, C1, C2, E)` evaluates to
the same point as the quadratic Bezier `(S, Q, E)`.

### Proof Method

Algebraic substitution.

The cubic formula is:

```text
(1-t)^3*S + 3(1-t)^2*t*C1 + 3(1-t)*t^2*C2 + t^3*E
```

Substitute `C1 = S + 2/3(Q-S)` and `C2 = E + 2/3(Q-E)`.

The coefficient of `S` becomes:

```text
(1-t)^3 + (1-t)^2*t = (1-t)^2
```

The coefficient of `Q` becomes:

```text
2(1-t)^2*t + 2(1-t)*t^2 = 2(1-t)t
```

The coefficient of `E` becomes:

```text
(1-t)*t^2 + t^3 = t^2
```

Therefore the cubic reduces to:

```text
(1-t)^2*S + 2(1-t)t*Q + t^2*E
```

which is the quadratic Bezier formula.

### Counterexamples And Exclusions

- This proof does not claim anything about PDF viewer rendering bugs.
- This proof does not cover arbitrary private monkey-patching of
  `_quadratic_to_cubic()`.

### Conclusion

Proven for the stated domain.

## PO-QB-003: DXF Reuses PDF-Sampled Neutral Curve Geometry

### Claim

DXF export for a neutral `QuadraticBezierDrawing` emits vertices from the same
sampled points as the neutral curve's PDF materialization.

### Domain

All `QuadraticBezierDrawing` instances exported through `DXFDocument.add_group()`.

### Assumptions

- `QuadraticBezierDrawing.to_component(OutputFormat.PDF)` returns the concrete
  `QuadraticBezierPDF` object used for sampled geometry.
- `DXFDocument.add_group()` is the public DXF group export path.

### Theorem

For every neutral quadratic drawing in the domain, the generated DXF
`LWPOLYLINE` vertices equal:

```text
QuadraticBezierDrawing.to_component(OutputFormat.PDF).points
```

after the optional DXF coordinate-frame conversion.

### Proof Method

Static path proof over `dxf_generator.py`:

1. `DXFDocument.add_group()` iterates over `group.components`.
2. `_component_to_entities()` matches `QuadraticBezierDrawing` in the curve
   branch.
3. That branch assigns `concrete = component.to_component(OutputFormat.PDF)`.
4. It returns `_lwpolyline_entity(concrete.points, context, closed=False)`.
5. `_lwpolyline_entity()` emits one vertex for each supplied point.
6. Therefore the generated vertices are the PDF-materialized sampled points,
   transformed only by `DXFRenderContext.point()`.

### Counterexamples And Exclusions

- Native DXF spline/entity output is not part of the current contract.
- If DXF changes to a native curve representation, this proof must be replaced
  and an ADR should record the new dependency direction.

### Conclusion

Proven for the stated domain.

## Current Slice Decision

The slice has mathematical proof for the quadratic sampling formula and the PDF
quadratic-to-cubic conversion, plus live-path evidence for DXF dependency
propagation.

The main design constraint is that DXF curve export intentionally depends on
PDF-materialized sampled points for quadratic curves. That edge is now explicit
and tested.
