# Arc Finite Boundary Contract Proof Obligations

This note applies the InkGen Definition of Done to the ARC-FINITE-P2 arc
finite-boundary hardening slice.

## Scope

The slice covers public construction and setter boundaries for:

- `Arc.center`
- `Arc.radius_x`
- `Arc.radius_y`
- `Arc.start_angle`
- `Arc.end_angle`
- `Arc.rotation`
- Dependent `ArcPDF` construction
- Dependent neutral `ArcDrawing` export through `DXFDocument.add_group()`

## Architecture Impact

Affected surface:

- `src/InkGen/component.py`: finite numeric arc validation.
- `tests/test_arc_finite_contract.py`: ARC-FINITE-P2 behavioral,
  failure-mode, state-preservation, and dependent PDF/DXF tests.
- `tests/mutation/arc_finite_cosmic_ray.toml`: scoped mutation gate.
- `tests/mutation/filter_arc_finite_work_items.py`: proof-critical mutation
  filter.
- `docs/proofs/arc-finite-contract.md`: proof note.

Incoming dependencies:

- `ArcPDF` inherits `Arc` and consumes the same public geometry boundary.
- `ArcDrawing` materializes to `ArcPDF` for DXF sampled-curve export.
- Labels, masks, truth emitters, and generated fixtures consume arc `points`,
  `bbox`, and `convex_hull` semantics.

Outgoing dependencies:

- The finite validator depends only on `math.isfinite()`.
- No dependency or package was added.

Before/after edge changes:

- Before this slice, `NaN` and `inf` center, radius, and angle inputs could be
  stored and later emitted as non-finite sampled points.
- Before this slice, boolean values were accepted as numeric arc inputs through
  Python's `float()` conversion.
- After this slice, all public center, radius, and angle boundaries require
  finite numeric non-boolean values.
- Existing positive-radius semantics are preserved.

Cycle/layer/coupling/redundancy result:

- Cycle check: no dependency edge was added.
- Layer check: shared arc geometry validation remains in `component.py`.
- Coupling check: PDF and DXF behavior still depends on the base arc geometry
  contract.
- Redundancy check: one local validator is reused by point, radius, angle, and
  rotation paths.

ADR/rule impact:

- No ADR is required. This closes an invalid public input gap in an existing
  component contract.

## Domain Definitions

- Arc center coordinates are finite numeric non-boolean values.
- Arc radii are finite numeric non-boolean values greater than zero.
- Arc start angle, end angle, and rotation are finite numeric non-boolean
  values in degrees.
- Rejected setter inputs must not mutate prior valid arc state.

## Fix Log

- Added `Arc._coerce_finite_number()` to reject booleans, nonnumeric values,
  and non-finite values.
- Routed center coordinates, radii, constructor angles, and angle setters
  through the finite validator.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid finite arc geometry | Preserve public arc geometry and sampled points | PO-AFIN-001 | `test_arc_preserves_valid_finite_geometry_and_setters` | mutation target |
| Invalid constructor inputs | Reject non-finite, nonnumeric, boolean, zero-radius, and negative-radius values | PO-AFIN-002 | `test_arc_rejects_invalid_constructor_boundaries` | mutation target |
| Invalid setter inputs | Reject and preserve prior state | PO-AFIN-003 | `test_arc_setters_reject_invalid_inputs_without_mutating` | mutation target |
| Dependent PDF/DXF paths | Reject non-finite geometry before renderer output | PO-AFIN-004 | `test_arc_dependent_pdf_and_dxf_paths_reject_nonfinite_geometry` | focused test |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Finite numeric validation is deterministic. | ARC-FINITE-P2 tests |
| Behavioral/condition | yes | The slice defines public arc input boundaries. | Tests marked `@pytest.mark.condition("ARC-FINITE-P2")` |
| Failure-mode | yes | Invalid values must fail and preserve state. | Constructor and setter rejection tests |
| Integration/live-path | yes | PDF and neutral-DXF paths consume the base arc boundary. | Dependent path test |
| Contract/API compatibility | yes | Existing ARC-P1 behavior must continue passing. | Focused gate includes `tests/test_curve_contract.py` |
| Property/fuzz | no | Partitions are finite numeric type/range classes. | Not applicable |
| Mutation | yes | The validator and public boundary calls are proof-critical. | Result recorded below |
| Security/adversarial | no | No path, network, subprocess, archive, SQL, template, or active-content surface changed. | Not applicable |
| Performance/resource | no | Constant-time validation only. | Not applicable |
| Concurrency/race | no | No shared state, workers, locks, or temp files changed. | Not applicable |
| Regression | yes | Prevents non-finite arc samples from reaching renderers. | Invalid geometry tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Weakening boolean, numeric, finite, or positive-radius checks must fail
  invalid constructor or setter tests.
- Removing constructor or setter validation calls must fail invalid-input or
  state-preservation tests.

Current result:

- PASS. Cosmic Ray generated 2,836 raw component mutants. The
  `ARC-FINITE-P2` filter reduced this to 25 proof-critical work items. All 25
  were killed and 0 survived.

During the first mutation pass, a real test gap was found in center arity
coverage: weakening `len(point) != 2` to a one-sided comparison survived. The
constructor and setter tests now include one-coordinate and three-coordinate
center inputs and kill those mutants.

## PO-AFIN-001: Valid Finite Arc Inputs Preserve Geometry

### Claim

Finite numeric arc inputs preserve center, radii, angles, rotation, and sampled
point generation.

### Domain

Finite numeric center coordinates, positive radii, finite numeric angles, and
finite numeric rotation values.

### Proof Method

Construction and setters pass public values through finite coercion and then
store floats. Focused tests assert public properties and sampled point count
before and after setter calls.

### Conclusion

Proven for the stated domain after focused tests and mutation pass.

## PO-AFIN-002: Invalid Constructor Inputs Fail

### Claim

Invalid center, radius, angle, or rotation values are rejected before arc
construction stores invalid geometry.

### Domain

`NaN`, positive/negative infinity, booleans, nonnumeric objects, nonnumeric
strings, zero radii, and negative radii.

### Proof Method

The constructor calls `_coerce_point()`, `_validate_radius()`, and
`_coerce_finite_number()` before storing public fields. Focused tests cover all
invalid partitions at construction.

### Conclusion

Proven for the stated domain after focused tests and mutation pass.

## PO-AFIN-003: Invalid Setter Inputs Do Not Mutate State

### Claim

Rejected arc setter inputs leave existing valid arc state unchanged.

### Domain

Existing valid arcs and invalid center, radius, angle, or rotation setter
inputs.

### Proof Method

Each setter validates before assignment. Focused tests compare serialized
parameters before and after every rejected setter call.

### Conclusion

Proven for the stated domain after focused tests and mutation pass.

## PO-AFIN-004: Dependent Render Paths Consume Finite Boundary

### Claim

PDF arc construction and neutral arc DXF export reject non-finite geometry
before producing renderer output.

### Domain

`ArcPDF` construction and `DXFDocument.add_group()` with an `ArcDrawing` that
would materialize to invalid arc geometry.

### Proof Method

`ArcPDF` inherits `Arc`, and `DXFDocument.add_group()` materializes
`ArcDrawing` through `ArcDrawing.to_component(OutputFormat.PDF)`. Focused tests
assert both dependent paths reject invalid non-finite input.

### Conclusion

Proven for the stated representative dependent paths after focused tests pass.
