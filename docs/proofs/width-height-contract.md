# Width Height Contract Proof Obligations

This note applies the InkGen Definition of Done to the WIDTH-HEIGHT-P1
width/height component slice. It covers geometry modeled as a position plus
separate width and height dimensions.

## Scope

The slice covers:

- `WidthHeightDrawingComponent.__init__()`
- `WidthHeightDrawingComponent._coerce_dimension()`
- `WidthHeightDrawingComponent.width`
- `WidthHeightDrawingComponent.height`
- `WidthHeightDrawingComponent.position`
- `WidthHeightDrawingComponent.points`
- `WidthHeightDrawingComponent.bbox`
- Dependent `RectangleSVG` and `RectanglePDF` inherited dimensions

## Architecture Impact

Affected surface:

- `src/InkGen/component.py`: width/height dimension validation.
- `tests/test_width_height_contract.py`: WIDTH-HEIGHT-P1 behavioral,
  failure-mode, mutation, and dependent renderer tests.
- `tests/mutation/width_height_cosmic_ray.toml`: scoped mutation gate.
- `tests/mutation/filter_width_height_work_items.py`: proof-critical mutation
  filter.
- `docs/proofs/width-height-contract.md`: proof note.

Incoming dependencies:

- `RectangleSVG` and `RectanglePDF` inherit this geometry contract.
- Component groups, layer containment, and boundary checks consume
  width/height component points and bboxes.
- CAD zoning and examples construct rectangle-like components.
- Serialization round trips rely on deterministic `width` and `height`
  properties.

Outgoing dependencies:

- The dimension validator depends only on Python `math.isfinite()`.
- Endpoint assignment continues to delegate to inherited point validation.
- No dependency or package was added.

Before/after edge changes:

- Before this slice, negative width or height could be accepted whenever the
  resulting endpoint coordinate remained nonnegative.
- Before this slice, boolean and non-finite dimensions could reach endpoint
  construction in some paths.
- After this slice, width and height must be finite numeric nonnegative values
  at construction and setter boundaries.
- Zero dimensions remain accepted to preserve existing degenerate geometry
  behavior.

Cycle/layer/coupling/redundancy result:

- Cycle check: no new dependency cycle is introduced.
- Layer check: shared component geometry validation remains in `component.py`.
- Coupling check: renderer-specific rectangle behavior remains outside the
  base component class.
- Redundancy check: one local validator is reused by constructor and setters.

ADR/rule impact:

- No ADR is required. This closes an invalid geometry input gap in an existing
  component contract.

## Domain Definitions

- A width/height component is defined by public `position = (x, y)`, `width`,
  and `height`.
- Width and height are finite numeric values greater than or equal to zero.
- `point_1 == position` and `point_2 == (x + width, y + height)`.
- The point list is the rectangle hull in insertion order:
  top-left, top-right, bottom-right, bottom-left.
- Renderer-specific corner-radius behavior is covered by RECT-P1 and is not
  re-proven here.

## Fix Log

- Added `_coerce_dimension()` to reject booleans, nonnumeric values,
  non-finite values, and negative values.
- Routed construction, `width`, and `height` setter paths through the shared
  validator.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Positive dimensions | Preserve geometry and endpoint coordinates | PO-WH-001 | `test_width_height_component_preserves_positive_and_zero_dimensions` | mutation target |
| Zero dimensions | Preserve existing accepted degenerate geometry | PO-WH-001 | same | focused test |
| Invalid constructor dimensions | Reject negative, non-finite, boolean, and nonnumeric values | PO-WH-002 | `test_width_height_component_rejects_invalid_constructor_dimensions` | mutation target |
| Invalid setter dimensions | Reject and preserve prior state | PO-WH-003 | `test_width_height_setters_rejects_invalid_dimensions_without_mutating` | mutation target |
| Position mutation | Preserve validated dimensions | PO-WH-004 | `test_width_height_position_mutation_preserves_dimensions` | focused test |
| Rectangle dependencies | SVG/PDF rectangles reject invalid inherited dimensions | PO-WH-005 | `test_rectangle_renderers_consume_width_height_dimension_contract` | focused test |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Dimension validation and geometry setters are deterministic. | WIDTH-HEIGHT-P1 tests |
| Behavioral/condition | yes | The slice defines a public component geometry contract. | Tests marked `@pytest.mark.condition("WIDTH-HEIGHT-P1")` |
| Failure-mode | yes | Invalid dimensions must fail and not mutate existing state. | Invalid constructor/setter tests |
| Integration/live-path | yes | Rectangle SVG/PDF constructors consume the inherited contract. | Dependent renderer test |
| Contract/API compatibility | yes | Existing component, rectangle, component group, and boundary tests must continue passing. | Focused gate |
| Property/fuzz | no | The partitions are finite numeric type/range classes. | Not applicable |
| Mutation | yes | Dimension guards and setter formulas are proof-critical. | Result recorded below |
| Security/adversarial | no | No path, network, subprocess, archive, SQL, template, or active-content surface changed. | Not applicable |
| Performance/resource | no | Constant-time validation only. | Not applicable |
| Concurrency/race | no | No shared state, locks, workers, or temp files changed. | Not applicable |
| Golden artifact/visual | limited | Renderer-specific output is covered by existing rectangle tests. | RECT-P1 focused gate |
| Regression | yes | Prevents invalid negative dimensions from reaching renderers. | Invalid dimension tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Weakening type, finite, or negative checks must fail invalid constructor or
  setter tests.
- Mutating width or height endpoint formulas must fail geometry tests.
- Removing setter assignment must fail geometry or state-preservation tests.

Current result:

- PASS. Cosmic Ray generated 2,830 raw component mutants. The
  `WIDTH-HEIGHT-P1` filter reduced this to 24 proof-critical work items. All
  24 were killed and 0 survived.

## PO-WH-001: Nonnegative Dimensions Produce Coherent Geometry

### Claim

Width/height components preserve position, width, height, point list, and bbox
for nonnegative dimensions.

### Domain

Finite numeric width and height values greater than or equal to zero.

### Proof Method

Construction and setters pass dimensions through `_coerce_dimension()`.
`point_2` is computed from `(x + width, y + height)`. Focused tests cover
positive and zero partitions.

### Conclusion

Proven for the stated domain after focused tests and mutation pass.

## PO-WH-002: Invalid Constructor Dimensions Fail

### Claim

Invalid width and height values are rejected before component construction
stores invalid geometry.

### Domain

Negative, non-finite, boolean, and nonnumeric width/height values.

### Proof Method

The constructor calls `_coerce_dimension()` before computing `point_2`.
Focused tests cover every invalid partition for width and height.

### Conclusion

Proven for the stated domain after focused tests and mutation pass.

## PO-WH-003: Invalid Setter Dimensions Do Not Mutate State

### Claim

Invalid width/height setter calls raise and leave existing geometry unchanged.

### Domain

Existing valid width/height components and invalid setter inputs.

### Proof Method

Each setter calls `_coerce_dimension()` before assigning `point_2`. Focused
tests compare serialized parameters before and after rejected setter calls.

### Conclusion

Proven for the stated domain after focused tests and mutation pass.

## PO-WH-004: Position Mutation Preserves Dimensions

### Claim

Changing position moves the component while preserving current width and height.

### Domain

Existing valid width/height components and valid new positions.

### Proof Method

The position setter stores current `width` and `height`, updates `point_1`, and
then recomputes `point_2`. The focused test asserts the final endpoint.

### Conclusion

Proven for the stated domain after focused tests pass.

## PO-WH-005: Rectangle Renderers Consume The Contract

### Claim

SVG and PDF rectangle constructors reject invalid inherited dimensions before
rendering.

### Domain

`RectangleSVG` and `RectanglePDF` construction with invalid width or height.

### Proof Method

Both rectangle classes call `WidthHeightDrawingComponent.__init__()`. Focused
tests assert invalid dimensions raise before renderer output.

### Conclusion

Proven for the stated representative dependent paths after focused tests pass.
