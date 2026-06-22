# Radial Scalar Boundary Contract Proof Obligations

This note applies the InkGen Definition of Done to the RADIAL-SCALAR-P2 radial
scalar hardening slice.

## Scope

The slice covers finite non-boolean scalar validation for polar length/angle,
regular polygon radius/corner radius, SVG/PDF circle radius, and neutral radial
drawing materialization paths.

## Architecture Impact

Affected surface:

- `src/InkGen/component.py`: polar and regular-polygon scalar validation.
- `src/InkGen/svg_generator.py`: SVG circle radius validation.
- `src/InkGen/pdf_generator.py`: PDF circle radius validation.
- `tests/test_radial_scalar_contract.py`: RADIAL-SCALAR-P2 behavioral,
  failure-mode, state-preservation, and dependent path tests.
- `tests/mutation/radial_scalar_cosmic_ray.toml`: scoped mutation gate.
- `tests/mutation/filter_radial_scalar_work_items.py`: proof-critical mutation
  filter.

Before/after edge changes:

- Before this slice, `True` could be accepted as a circle radius or regular
  polygon corner radius.
- Before this slice, non-finite regular-polygon values could reach downstream
  point validation after NumPy warnings rather than failing at the scalar
  boundary.
- After this slice, radial scalar values must be finite numeric non-booleans;
  circle and regular-polygon radii remain strictly positive.

## Domain Definitions

- Polar length and angle are finite numeric non-boolean values.
- Circle radius is a finite numeric non-boolean value greater than zero.
- Regular polygon radius is a finite numeric non-boolean value greater than
  zero.
- Regular polygon corner radius is a finite numeric non-boolean value between
  zero and half the current radius.
- Rejected scalar setters must not mutate prior valid state.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Circle radius | Reject boolean, nonnumeric, non-finite, zero, and negative values | PO-RAD-001 | `test_circle_radius_rejects_boolean_and_nonfinite_values` | mutation target |
| Polar length/angle | Reject boolean, nonnumeric, and non-finite values | PO-RAD-002 | `test_polar_length_angle_reject_boolean_and_nonfinite_values` | mutation target |
| Regular polygon scalar values | Reject invalid radius, angle, and corner radius values | PO-RAD-003 | `test_regular_polygon_radius_corner_and_angle_reject_invalid_scalars` | mutation target |
| Neutral radial drawings | Reject invalid scalar values before output | PO-RAD-004 | `test_neutral_radial_drawings_consume_scalar_boundaries` | focused test |
| Valid finite scalars | Preserve existing geometry behavior | PO-RAD-005 | `test_valid_radial_scalars_remain_supported` | focused test |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Scalar validation is deterministic. | RADIAL-SCALAR-P2 tests |
| Behavioral/condition | yes | The slice defines public radial scalar boundaries. | Tests marked `@pytest.mark.condition("RADIAL-SCALAR-P2")` |
| Failure-mode | yes | Invalid scalars must fail and preserve state. | Constructor and setter rejection tests |
| Integration/live-path | yes | Neutral radial drawings materialize through concrete renderers/DXF. | Dependent path test |
| Contract/API compatibility | yes | Existing CIRCLE-P1 and REGPOLY-P1 behavior must continue passing. | Focused gate includes both contract tests |
| Mutation | yes | Scalar validators and setter calls are proof-critical. | Result recorded below |
| Security/adversarial | no | No path, network, subprocess, archive, SQL, template, or active-content surface changed. | Not applicable |
| Performance/resource | no | Constant-time validation only. | Not applicable |
| Concurrency/race | no | No shared state, workers, locks, or temp files changed. | Not applicable |

## Mutation Testing Gate

Proof-critical mutation targets:

- Weakening boolean, numeric, finite, positivity, or half-radius checks must fail
  invalid scalar tests.
- Removing setter validation calls must fail invalid-input or
  state-preservation tests.

Current result:

- PASS. Cosmic Ray generated 7,174 raw radial-component mutants. The
  `RADIAL-SCALAR-P2` filter reduced this to 39 proof-critical work items. All
  39 were killed and 0 survived.

During the first mutation pass, the filter was too broad and selected existing
polar endpoint arithmetic. After narrowing to changed validation rows, mutation
found a real CircleSVG setter gap around `numeric <= 0`; the test now covers a
negative radius setter call with state preservation and kills that mutant.
