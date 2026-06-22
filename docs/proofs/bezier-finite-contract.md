# Bezier Finite Boundary Contract Proof Obligations

This note applies the InkGen Definition of Done to the BEZIER-FINITE-P2
quadratic/cubic Bezier finite-boundary hardening slice.

## Scope

The slice covers public construction and point setter boundaries for:

- `QuadraticBezier.start_point`
- `QuadraticBezier.control_point`
- `QuadraticBezier.end_point`
- `CubicBezier.start_point`
- `CubicBezier.control_point1`
- `CubicBezier.control_point2`
- `CubicBezier.end_point`
- Dependent `QuadraticBezierPDF` and `CubicBezierPDF` construction
- Dependent neutral `QuadraticBezierDrawing` and `CubicBezierDrawing` export
  through `DXFDocument.add_group()`

## Architecture Impact

Affected surface:

- `src/InkGen/component.py`: finite numeric Bezier point validation.
- `tests/test_bezier_finite_contract.py`: BEZIER-FINITE-P2 behavioral,
  failure-mode, state-preservation, and dependent PDF/DXF tests.
- `tests/mutation/bezier_finite_cosmic_ray.toml`: scoped mutation gate.
- `tests/mutation/filter_bezier_finite_work_items.py`: proof-critical mutation
  filter.
- `docs/proofs/bezier-finite-contract.md`: proof note.

Incoming dependencies:

- Quadratic/cubic PDF renderers inherit the base Bezier component contracts.
- Neutral Bezier drawings materialize to PDF components for DXF sampled-curve
  export.
- Labels, masks, truth emitters, generated fixtures, and synthetic drawing
  consumers rely on Bezier `points`, `bbox`, and `convex_hull` semantics.

Outgoing dependencies:

- The finite validators depend only on `math.isfinite()`.
- No dependency or package was added.

Before/after edge changes:

- Before this slice, `NaN`, `inf`, and boolean coordinates could be stored and
  later emitted as Bezier sampled points.
- After this slice, all public quadratic/cubic Bezier point boundaries require
  finite numeric non-boolean coordinates.
- Existing finite Bezier sampling semantics are preserved.

Cycle/layer/coupling/redundancy result:

- Cycle check: no dependency edge was added.
- Layer check: shared Bezier geometry validation remains in `component.py`.
- Coupling check: PDF and DXF behavior still depends on the base component
  geometry contract.
- Redundancy check: validation stays local to the Bezier component classes.

ADR/rule impact:

- No ADR is required. This closes an invalid public input gap in existing
  component contracts.

## Domain Definitions

- A Bezier point is a two-coordinate tuple/list whose coordinates are finite
  numeric non-boolean values.
- Rejected setter inputs must not mutate prior valid Bezier state.

## Fix Log

- Added finite numeric coordinate validation to `QuadraticBezier._coerce_point()`.
- Added finite numeric coordinate validation to `CubicBezier._coerce_point()`.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid finite quadratic points | Preserve public geometry and sampled points | PO-BFIN-001 | `test_quadratic_bezier_preserves_valid_finite_points_and_setters` | mutation target |
| Valid finite cubic points | Preserve public geometry and sampled points | PO-BFIN-001 | `test_cubic_bezier_preserves_valid_finite_points_and_setters` | mutation target |
| Invalid quadratic points | Reject non-finite, nonnumeric, boolean, and malformed point values | PO-BFIN-002 | `test_quadratic_bezier_rejects_invalid_constructor_and_setter_points` | mutation target |
| Invalid cubic points | Reject non-finite, nonnumeric, boolean, and malformed point values | PO-BFIN-002 | `test_cubic_bezier_rejects_invalid_constructor_and_setter_points` | mutation target |
| Dependent PDF/DXF paths | Reject non-finite geometry before renderer output | PO-BFIN-003 | `test_dependent_pdf_and_dxf_paths_reject_nonfinite_bezier_geometry` | focused test |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Finite numeric point validation is deterministic. | BEZIER-FINITE-P2 tests |
| Behavioral/condition | yes | The slice defines public Bezier point boundaries. | Tests marked `@pytest.mark.condition("BEZIER-FINITE-P2")` |
| Failure-mode | yes | Invalid points must fail and preserve state. | Constructor and setter rejection tests |
| Integration/live-path | yes | PDF and neutral-DXF paths consume the base Bezier boundary. | Dependent path test |
| Contract/API compatibility | yes | Existing CURVE-P1 behavior must continue passing. | Focused gate includes `tests/test_curve_contract.py` |
| Property/fuzz | no | Partitions are finite numeric type/range classes. | Not applicable |
| Mutation | yes | The validators and public point setter calls are proof-critical. | Result recorded below |
| Security/adversarial | no | No path, network, subprocess, archive, SQL, template, or active-content surface changed. | Not applicable |
| Performance/resource | no | Constant-time validation only. | Not applicable |
| Concurrency/race | no | No shared state, workers, locks, or temp files changed. | Not applicable |
| Regression | yes | Prevents non-finite Bezier samples from reaching renderers. | Invalid geometry tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Weakening boolean, numeric, finite, or arity checks must fail invalid
  constructor or setter tests.
- Removing setter validation calls must fail invalid-input or
  state-preservation tests.

Current result:

- PASS. Cosmic Ray generated 2,848 raw component mutants. The
  `BEZIER-FINITE-P2` filter reduced this to 34 proof-critical work items. All
  34 were killed and 0 survived.

## PO-BFIN-001: Valid Finite Bezier Inputs Preserve Geometry

### Claim

Finite numeric Bezier inputs preserve public point properties and sampled point
generation.

### Domain

Quadratic and cubic Bezier components with finite numeric point coordinates.

### Proof Method

Construction and setters pass public values through finite coercion and then
store floats. Focused tests assert public properties and sampled point count
before and after setter calls.

### Conclusion

Proven for the stated domain after focused tests and mutation pass.

## PO-BFIN-002: Invalid Bezier Inputs Fail Without Mutation

### Claim

Invalid Bezier point values are rejected before construction or setter calls
store invalid geometry.

### Domain

`NaN`, positive/negative infinity, booleans, nonnumeric objects, nonnumeric
strings, one-coordinate points, and three-coordinate points.

### Proof Method

The constructors and point setters call `_coerce_point()`, which checks arity
and validates each coordinate with finite numeric coercion. Focused tests cover
all invalid partitions for quadratic and cubic Beziers and compare serialized
state after rejected setter calls.

### Conclusion

Proven for the stated domain after focused tests and mutation pass.

## PO-BFIN-003: Dependent Render Paths Consume Finite Boundary

### Claim

PDF Bezier construction and neutral Bezier DXF export reject non-finite geometry
before producing renderer output.

### Domain

`QuadraticBezierPDF`, `CubicBezierPDF`, and `DXFDocument.add_group()` with
neutral Bezier drawings that would materialize to invalid geometry.

### Proof Method

PDF Bezier components inherit the base Bezier validators, and
`DXFDocument.add_group()` materializes neutral Bezier drawings through
`to_component(OutputFormat.PDF)`. Focused tests assert both dependent paths
reject invalid non-finite input.

### Conclusion

Proven for the stated representative dependent paths after focused tests pass.
