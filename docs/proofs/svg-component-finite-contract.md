# SVG Component Finite Boundary Contract

This note applies the InkGen Definition of Done to the
SVG-COMPONENT-FINITE-P2 embedded SVG boundary slice.

## Scope

The slice covers `SVGComponent` construction, deserialization, position
mutation, scale mutation, bbox coercion, bounds, points, and generated SVG
transform output.

## Architecture Impact

Affected surface:

- `src/InkGen/svg_generator.py`: added local finite scalar and bbox coercion to
  `SVGComponent`.
- `tests/test_svg_utils_contract.py`: added SVG-COMPONENT-FINITE-P2 condition
  tests.
- `tests/mutation/svg_component_finite_cosmic_ray.toml`: scoped mutation gate.
- `tests/mutation/filter_svg_component_finite_work_items.py`: proof-critical
  mutation filter.
- `docs/proofs/svg-component-finite-contract.md`: this proof note.

Incoming dependencies:

- SVG component round-trip tests use `SVGComponent.create_from_dict()`.
- External SVG embedding and synthetic drawing workflows consume
  `SVGComponent.points`, `bbox`, `parameters`, and `generate_svg()`.

Outgoing dependencies:

- `SVGComponent` still depends only on existing InkGen component interfaces and
  `flatten_svg()`.
- No dependency was added.

Before/after edge changes:

- No dependency edge changed.
- Before this slice, `SVGComponent` accepted `NaN`, infinity, and boolean values
  through direct `float()` coercion in bbox, position, and scale paths.
- After this slice, those values fail before state mutation or serialized
  payload rehydration.

Cycle/layer/coupling/redundancy result:

- Cycle check: no import was added, so no cycle is introduced.
- Layer check: validation remains inside the SVG renderer component boundary.
- Coupling check: no PDF, DXF, document, or external-library coupling was added.
- Redundancy check: `SVGComponent` now has one local finite scalar helper reused
  by bbox, position, and scale validation.

ADR/rule impact:

- No ADR change is required. This keeps `SVGComponent` SVG-only and does not add
  dependencies.

## Domain Definitions

- A valid embedded SVG position is exactly two finite numeric non-boolean
  coordinates.
- A valid embedded SVG scale is a finite numeric non-boolean scalar greater than
  zero.
- A valid embedded SVG bbox is exactly two coordinate pairs, each containing
  finite numeric non-boolean coordinates.
- Invalid constructor, setter, or deserialized values must fail before storing
  invalid component state.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid embedded SVG geometry | Preserve points, bbox, generated transform, and parameters | PO-SVGCOMP-001 | live path and deserialization tests | behavioral |
| Invalid position values | Reject malformed, boolean, and non-finite coordinates | PO-SVGCOMP-002 | position boundary test | behavioral |
| Invalid scale values | Reject boolean, non-finite, zero, and negative values | PO-SVGCOMP-003 | scale boundary test | killed |
| Invalid bbox values | Reject malformed, boolean, and non-finite coordinates | PO-SVGCOMP-004 | bbox boundary test | behavioral |
| Setter failure atomicity | Preserve prior parameters after rejected setter values | PO-SVGCOMP-005 | setter state-preservation test | killed |
| Deserialized invalid values | Route through the same constructor validation | PO-SVGCOMP-006 | `create_from_dict()` invalid scale test | behavioral |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Scalar and bbox validation is deterministic. | `tests/test_svg_utils_contract.py` |
| Behavioral/condition | yes | The slice defines SVG-COMPONENT-FINITE-P2 boundary behavior. | Tests are marked `@pytest.mark.condition("SVG-COMPONENT-FINITE-P2")`. |
| Failure-mode | yes | Invalid transform and bbox values must fail before rendering. | invalid constructor, setter, and deserialize tests |
| Integration/live-path | yes | Generated SVG and points consume the stored finite state. | live-path and generated transform assertions |
| Contract/API compatibility | yes | Valid persisted payloads still rehydrate. | `create_from_dict()` valid payload test |
| Property/fuzz | limited yes | Boundary partitions cover valid, malformed, boolean, and non-finite values. | finite boundary tests |
| Mutation | yes | Proof-critical finite and scale branches were mutated. | Cosmic Ray result below |
| Security/adversarial | limited yes | Prevents untrusted serialized payloads from injecting non-finite SVG output. | deserialize failure test |
| Performance/resource | no | Validation is constant time. | Not applicable |
| Concurrency/race | no | No shared mutable global state is added. | Not applicable |
| Golden artifact/visual | yes | Generated SVG transform text is asserted. | generated transform test |
| Regression | yes | Closes direct `float()` coercion acceptance of invalid values. | boundary tests |

## Mutation Testing Gate

Current result:

- Tool: Cosmic Ray 8.4.6.
- Environment: WSL Python 3.12 virtualenv.
- Raw work items: 2,321.
- Proof-critical work items after filter: 11.
- Killed mutants: 11.
- Survivors: 0.
- Gate result: pass.

The mutation filter targets rows where Cosmic Ray emits useful mutation
operators for the finite scalar and scale decision branches. Position and bbox
wiring are still covered by behavioral tests; they do not produce useful
call-removal mutation rows in this tool configuration.

## PO-SVGCOMP-001: Valid Embedded Geometry Is Preserved

### Claim

For accepted finite bbox, position, and scale values, `SVGComponent` computes
points and generated SVG transforms from those accepted values.

### Proof Method

The test constructs a component from a serialized payload and asserts exact
scaled points plus generated SVG transform text.

### Conclusion

Proven for the declared finite embedded-SVG domain.

## PO-SVGCOMP-002: Invalid Positions Fail

### Claim

Malformed, boolean, and non-finite position coordinates are rejected before
stored component state changes.

### Proof Method

Constructor and setter tests pass malformed, boolean, `NaN`, and infinity
coordinates. Setter tests assert parameters are unchanged after rejection.

### Conclusion

Proven for the tested malformed, boolean, and non-finite partitions.

## PO-SVGCOMP-003: Invalid Scales Fail

### Claim

Scale accepts only finite numeric non-boolean values greater than zero.

### Proof Method

Constructor and setter tests cover boolean, non-finite, zero, negative, and
nonnumeric values. Mutation testing kills all proof-critical scale branch
mutants.

### Conclusion

Proven for the declared scale boundary.

## PO-SVGCOMP-004: Invalid Bboxes Fail

### Claim

Bbox input must contain exactly two finite numeric coordinate pairs.

### Proof Method

Constructor tests cover non-finite coordinates, boolean coordinates, malformed
pair count, and non-sequence input.

### Conclusion

Proven for the declared bbox boundary.

## PO-SVGCOMP-005: Setter Failures Are Atomic

### Claim

Rejected position or scale setter values do not partially mutate component
state.

### Proof Method

The focused test records `parameters`, applies rejected setter values, and
asserts the parameters are unchanged.

### Conclusion

Proven for rejected position and scale setter paths.

## PO-SVGCOMP-006: Deserialization Uses The Same Boundary

### Claim

`SVGComponent.create_from_dict()` cannot bypass finite transform validation.

### Proof Method

The focused test rehydrates a valid payload, then changes the serialized scale
to `NaN` and asserts construction fails.

### Conclusion

Proven for the serialized scale boundary and by construction for bbox/position
because `create_from_dict()` delegates to `SVGComponent.__init__()`.
