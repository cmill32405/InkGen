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
- Neutral `ArcDrawing` construction
- `FlowDocument.create_from_dict()` hydration of serialized `ArcDrawing`
  payloads
- Dependent neutral `ArcDrawing` export through `DXFDocument.add_group()`

## Architecture Impact

Affected surface:

- `src/InkGen/component.py`: finite numeric arc validation.
- `src/InkGen/drawing_components.py`: renderer-neutral arc recipe validation.
- `tests/test_arc_finite_contract.py`: ARC-FINITE-P2 behavioral,
  failure-mode, state-preservation, neutral ARC-DRAWING-GEOMETRY-P2, and
  dependent PDF/DXF tests.
- `tests/test_flow_document_contract.py`: dependent flow-document drawing
  hydration path coverage.
- `tests/mutation/arc_finite_cosmic_ray.toml`: scoped mutation gate.
- `tests/mutation/filter_arc_finite_work_items.py`: proof-critical mutation
  filter.
- `tests/mutation/arc_drawing_geometry_cosmic_ray.toml`: neutral arc mutation
  gate.
- `tests/mutation/filter_arc_drawing_geometry_work_items.py`: neutral arc
  geometry mutation filter.
- `docs/proofs/arc-finite-contract.md`: proof note.

Incoming dependencies:

- `ArcPDF` inherits `Arc` and consumes the same public geometry boundary.
- `ArcDrawing` materializes to `ArcPDF` for DXF sampled-curve export.
- `FlowDocument.create_from_dict()` hydrates serialized drawing payloads by
  dispatching to `ArcDrawing(style=style, **payload)`.
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
- Before the neutral slice, `ArcDrawing` stored malformed center, radius, angle,
  or rotation payloads until SVG/PDF/DXF materialization.
- After the neutral slice, direct `ArcDrawing` construction and
  `FlowDocument` hydration reject malformed arc geometry before public neutral
  drawing state is exposed.

Cycle/layer/coupling/redundancy result:

- Cycle check: no dependency edge was added.
- Layer check: shared arc geometry validation remains in `component.py`.
- Coupling check: PDF and DXF behavior still depends on the base arc geometry
  contract.
- Redundancy check: one local validator is reused by point, radius, angle, and
  rotation paths.
- Redundancy check for the neutral boundary: `ArcDrawing` uses the existing
  neutral point-pair helper and one shared finite scalar helper rather than
  duplicating renderer logic.

ADR/rule impact:

- No ADR is required. This closes an invalid public input gap in an existing
  component contract.

## Domain Definitions

- Arc center coordinates are finite numeric non-boolean values.
- Arc radii are finite numeric non-boolean values greater than zero.
- Arc start angle, end angle, and rotation are finite numeric non-boolean
  values in degrees.
- Rejected setter inputs must not mutate prior valid arc state.
- `ArcDrawing` mirrors the concrete arc authoring domain: finite center
  coordinates, strictly positive finite radii, and finite start/end/rotation
  values. Negative center coordinates remain valid because concrete `Arc`
  accepts them.
- Serialized `ArcDrawing` payloads hydrated through `FlowDocument` must satisfy
  the same neutral authoring boundary.

## Fix Log

- Added `Arc._coerce_finite_number()` to reject booleans, nonnumeric values,
  and non-finite values.
- Routed center coordinates, radii, constructor angles, and angle setters
  through the finite validator.
- Added neutral finite scalar validation for `ArcDrawing` radii, angles, and
  rotation.
- Routed `ArcDrawing` center through the neutral finite point-pair helper and
  normalized all public neutral arc geometry before materialization.
- Added direct neutral and `FlowDocument` hydration tests for malformed
  `ArcDrawing` geometry payloads.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid finite arc geometry | Preserve public arc geometry and sampled points | PO-AFIN-001 | `test_arc_preserves_valid_finite_geometry_and_setters` | mutation target |
| Invalid constructor inputs | Reject non-finite, nonnumeric, boolean, zero-radius, and negative-radius values | PO-AFIN-002 | `test_arc_rejects_invalid_constructor_boundaries` | mutation target |
| Invalid setter inputs | Reject and preserve prior state | PO-AFIN-003 | `test_arc_setters_reject_invalid_inputs_without_mutating` | mutation target |
| Dependent PDF/DXF paths | Reject non-finite geometry before renderer output | PO-AFIN-004 | `test_arc_dependent_pdf_and_dxf_paths_reject_nonfinite_geometry` | focused test |
| Neutral `ArcDrawing` construction | Normalize valid geometry and reject malformed center, radius, angle, and rotation payloads before materialization | PO-AFIN-005 | `test_arc_drawing_normalizes_geometry_before_materialization`; `test_arc_drawing_rejects_malformed_geometry_payloads` | mutation target |
| Serialized neutral `ArcDrawing` hydration | Reject malformed serialized arc payloads before flow-document public state is exposed | PO-AFIN-006 | `test_flow_document_hydration_rejects_malformed_arc_geometry_payloads` | mutation target |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Finite numeric validation is deterministic. | ARC-FINITE-P2 tests |
| Behavioral/condition | yes | The slice defines public arc input boundaries. | Tests marked `@pytest.mark.condition("ARC-FINITE-P2")` |
| Failure-mode | yes | Invalid values must fail and preserve state. | Constructor and setter rejection tests |
| Integration/live-path | yes | PDF and neutral-DXF paths consume the base arc boundary. | Dependent path test |
| Integration/live-path | yes | Flow-document drawing hydration dispatches to the neutral arc constructor. | `test_flow_document_hydration_rejects_malformed_arc_geometry_payloads` |
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
- PASS for the neutral authoring extension. Cosmic Ray generated 1,663 raw
  drawing-component mutants. The `ARC-DRAWING-GEOMETRY-P2` filter reduced this
  to 68 proof-critical work items. Result: 65 killed, 3 survived. The 3
  survivors are equivalent signature-only mutants that replace the helper
  keyword-only marker `*` with `/` on `_coerce_point_pair()`,
  `_coerce_finite_float()`, and `_coerce_finite_positive_float()`. All current
  proof-domain calls pass `value` positionally and `name` by keyword, so the
  mutated signatures are behaviorally identical for the declared domain.

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

`ArcPDF` construction and `DXFDocument.add_group()` with valid `ArcDrawing`
geometry. Invalid neutral arc geometry is now rejected before it can be added to
a group or reach DXF materialization.

### Proof Method

`ArcPDF` inherits `Arc`, and `DXFDocument.add_group()` materializes valid
`ArcDrawing` instances through `ArcDrawing.to_component(OutputFormat.PDF)`.
Focused tests assert `ArcPDF` rejects invalid non-finite input, invalid neutral
arc construction fails before group insertion, and valid neutral arc geometry
still exports through DXF.

### Conclusion

Proven for the stated representative dependent paths after focused tests pass.

## PO-AFIN-005: Neutral ArcDrawing Geometry Boundary

### Claim

`ArcDrawing` normalizes valid geometry at construction and rejects malformed
center, radius, angle, and rotation payloads before SVG/PDF materialization.

### Domain

Direct `ArcDrawing` construction with finite center coordinates, positive
finite radii, finite start/end angles, finite rotation, and malformed
partitions including strings, mappings, wrong-length point sequences,
non-numeric objects, booleans, non-finite numbers, zero radii, and negative
radii.

### Proof Method

`ArcDrawing.__post_init__()` validates and stores normalized geometry before
the object can be observed. The center uses `_coerce_point_pair()`. Radii use a
strictly positive finite scalar helper. Angles and rotation use a finite scalar
helper. Focused tests cover valid normalization, SVG/PDF materialization, and
all declared malformed partitions. Mutation testing targets the helper branches
and constructor wiring.

### Conclusion

Proven for the stated public construction domain after focused tests and
mutation pass, with only equivalent signature-only survivors.

## PO-AFIN-006: FlowDocument ArcDrawing Hydration Boundary

### Claim

Serialized `ArcDrawing` payloads hydrated through `FlowDocument.create_from_dict()`
cannot expose malformed neutral arc geometry.

### Domain

Flow-document drawing blocks containing serialized `ArcDrawing` payloads and
style overrides for the same malformed geometry partitions named in
PO-AFIN-005.

### Proof Method

`document_outputs._drawing_component_from_parameters()` dispatches exact
component type names to `DRAWING_COMPONENT_CONSTRUCTORS[component_type]` with
`style=style, **payload`. Therefore serialized `ArcDrawing` payloads must pass
`ArcDrawing.__post_init__()` before the hydrated group is returned. Focused
tests mutate serialized payload fields and assert hydration raises.

### Conclusion

Proven for the stated flow-document hydration domain after focused tests and
mutation pass, with only equivalent signature-only survivors.
