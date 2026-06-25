# Radial Scalar Boundary Contract Proof Obligations

This note applies the InkGen Definition of Done to the RADIAL-SCALAR-P2 radial
scalar hardening slice.

## Scope

The slice covers finite non-boolean scalar validation for polar length/angle,
regular polygon radius/corner radius, SVG/PDF circle radius, and neutral radial
drawing materialization paths.
It now also covers neutral `CircleDrawing` and `RegularPolygonDrawing`
construction and `FlowDocument` hydration of serialized neutral radial payloads.

## Architecture Impact

Affected surface:

- `src/InkGen/component.py`: polar and regular-polygon scalar validation.
- `src/InkGen/svg_generator.py`: SVG circle radius validation.
- `src/InkGen/pdf_generator.py`: PDF circle radius validation.
- `src/InkGen/drawing_components.py`: renderer-neutral circle and regular
  polygon recipe validation.
- `tests/test_radial_scalar_contract.py`: RADIAL-SCALAR-P2 behavioral,
  failure-mode, state-preservation, neutral RADIAL-DRAWING-GEOMETRY-P2, and
  dependent path tests.
- `tests/test_flow_document_contract.py`: dependent flow-document drawing
  hydration path coverage.
- `tests/mutation/radial_scalar_cosmic_ray.toml`: scoped mutation gate.
- `tests/mutation/filter_radial_scalar_work_items.py`: proof-critical mutation
  filter.
- `tests/mutation/radial_drawing_geometry_cosmic_ray.toml`: neutral radial
  mutation gate.
- `tests/mutation/filter_radial_drawing_geometry_work_items.py`: neutral radial
  geometry mutation filter.

Before/after edge changes:

- Before this slice, `True` could be accepted as a circle radius or regular
  polygon corner radius.
- Before this slice, non-finite regular-polygon values could reach downstream
  point validation after NumPy warnings rather than failing at the scalar
  boundary.
- After this slice, radial scalar values must be finite numeric non-booleans;
  circle and regular-polygon radii remain strictly positive.
- Before the neutral slice, `CircleDrawing` and `RegularPolygonDrawing` could
  store malformed geometry until SVG/PDF/DXF materialization or flow-document
  output.
- After the neutral slice, direct neutral construction and `FlowDocument`
  hydration reject malformed radial geometry before public neutral state is
  exposed.

## Domain Definitions

- Polar length and angle are finite numeric non-boolean values.
- Circle radius is a finite numeric non-boolean value greater than zero.
- Regular polygon radius is a finite numeric non-boolean value greater than
  zero.
- Regular polygon corner radius is a finite numeric non-boolean value between
  zero and half the current radius.
- Rejected scalar setters must not mutate prior valid state.
- Neutral radial drawing positions are finite nonnegative point pairs.
- Neutral regular polygon side counts are non-boolean integers greater than or
  equal to three.
- Serialized neutral radial payloads hydrated through `FlowDocument` must
  satisfy the same constructor boundaries.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Circle radius | Reject boolean, nonnumeric, non-finite, zero, and negative values | PO-RAD-001 | `test_circle_radius_rejects_boolean_and_nonfinite_values` | mutation target |
| Polar length/angle | Reject boolean, nonnumeric, and non-finite values | PO-RAD-002 | `test_polar_length_angle_reject_boolean_and_nonfinite_values` | mutation target |
| Regular polygon scalar values | Reject invalid radius, angle, and corner radius values | PO-RAD-003 | `test_regular_polygon_radius_corner_and_angle_reject_invalid_scalars` | mutation target |
| Neutral radial drawings | Reject invalid scalar values before output | PO-RAD-004 | `test_neutral_radial_drawings_consume_scalar_boundaries` | focused test |
| Valid finite scalars | Preserve existing geometry behavior | PO-RAD-005 | `test_valid_radial_scalars_remain_supported` | focused test |
| Neutral radial drawing construction | Normalize valid circle and regular polygon geometry and reject malformed positions, sides, radii, angles, and corner radii before materialization | PO-RAD-006 | `test_neutral_radial_drawings_normalize_geometry_before_materialization`; `test_neutral_radial_drawings_reject_malformed_geometry_payloads` | mutation target |
| Serialized neutral radial hydration | Reject malformed serialized circle and regular polygon payloads before flow-document public state is exposed | PO-RAD-007 | `test_flow_document_hydration_rejects_malformed_radial_geometry_payloads` | mutation target |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Scalar validation is deterministic. | RADIAL-SCALAR-P2 tests |
| Behavioral/condition | yes | The slice defines public radial scalar boundaries. | Tests marked `@pytest.mark.condition("RADIAL-SCALAR-P2")` |
| Failure-mode | yes | Invalid scalars must fail and preserve state. | Constructor and setter rejection tests |
| Integration/live-path | yes | Neutral radial drawings materialize through concrete renderers/DXF. | Dependent path test |
| Integration/live-path | yes | Flow-document drawing hydration dispatches to neutral radial constructors. | `test_flow_document_hydration_rejects_malformed_radial_geometry_payloads` |
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
- PASS for the neutral authoring extension. Cosmic Ray generated 1,695 raw
  drawing-component mutants. The `RADIAL-DRAWING-GEOMETRY-P2` filter reduced
  this to 151 proof-critical work items. Result: 146 killed, 5 survived. The 5
  survivors are equivalent signature-only mutants that replace helper
  keyword-only markers `*` with `/` on `_coerce_point_pair()`,
  `_coerce_non_negative_point_pair()`, `_coerce_finite_float()`,
  `_coerce_finite_positive_float()`, and
  `_coerce_finite_non_negative_float()`. All current proof-domain calls pass
  `value` positionally and `name` by keyword, so the mutated signatures are
  behaviorally identical for the declared domain.

During the first mutation pass, the filter was too broad and selected existing
polar endpoint arithmetic. After narrowing to changed validation rows, mutation
found a real CircleSVG setter gap around `numeric <= 0`; the test now covers a
negative radius setter call with state preservation and kills that mutant.

## PO-RAD-006: Neutral RadialDrawing Geometry Boundary

### Claim

`CircleDrawing` and `RegularPolygonDrawing` normalize valid geometry at
construction and reject malformed position, side-count, radius, angle, and
corner-radius payloads before SVG/PDF/DXF materialization.

### Domain

Direct neutral radial drawing construction with finite nonnegative positions,
strictly positive finite radii, finite regular-polygon angles, valid integer
side counts, and valid regular-polygon corner radii. Malformed partitions
include strings, wrong-length point sequences, booleans, nonnumeric objects,
non-finite numbers, negative positions, non-integer side counts, too-few sides,
non-positive radii, negative corner radii, and corner radii above half the
radius.

### Proof Method

The neutral radial constructors validate and store normalized values before the
objects can be observed. Positions use `_coerce_non_negative_point_pair()`;
radii use `_coerce_finite_positive_float()`; angles use
`_coerce_finite_float()`; side counts use `_coerce_regular_polygon_sides()`;
and corner radii use `_coerce_finite_non_negative_float()` plus the half-radius
bound. Focused tests cover valid normalization, SVG/PDF materialization, DXF
materialization, and malformed partitions.

### Conclusion

Proven for the stated public construction domain after focused tests and
mutation pass, with only equivalent signature-only survivors.

## PO-RAD-007: FlowDocument RadialDrawing Hydration Boundary

### Claim

Serialized neutral radial drawing payloads hydrated through
`FlowDocument.create_from_dict()` cannot expose malformed circle or regular
polygon geometry.

### Domain

Flow-document drawing blocks containing serialized `CircleDrawing` or
`RegularPolygonDrawing` payloads and style overrides for the malformed geometry
partitions named in PO-RAD-006.

### Proof Method

`document_outputs._drawing_component_from_parameters()` dispatches exact
component type names to `DRAWING_COMPONENT_CONSTRUCTORS[component_type]` with
`style=style, **payload`. Therefore serialized neutral radial payloads must
pass their constructors before the hydrated group is returned. Focused tests
mutate serialized payload fields and assert hydration raises.

### Conclusion

Proven for the stated flow-document hydration domain after focused tests and
mutation pass, with only equivalent signature-only survivors.
