# Single Dimension Contract Proof Obligations

This note applies the InkGen Definition of Done to the SINGLE-DIM-P1
single-dimension component slice. It covers the shared geometry invariant for
components modeled as a position plus one scalar size.

## Scope

The slice covers:

- `SingleDimensionDrawingComponent.position`
- `SingleDimensionDrawingComponent.size`
- `SingleDimensionDrawingComponent.points`
- `SingleDimensionDrawingComponent.bbox`
- `SingleDimensionDrawingComponent.convex_hull`
- `SingleDimensionDrawingComponent.parameters`
- `SingleDimensionDrawingComponent.create_from_dict()`
- Dependent `CircleSVG.radius` mutation through the inherited size setter

## Architecture Impact

Affected surface:

- `src/InkGen/component.py`: `SingleDimensionDrawingComponent.size` setter.
- `tests/test_single_dimension_contract.py`: SINGLE-DIM-P1 geometry,
  mutation, round-trip, and dependent-circle tests.
- `tests/mutation/single_dimension_cosmic_ray.toml`: scoped mutation gate.
- `tests/mutation/filter_single_dimension_work_items.py`: proof-critical
  mutation filter.
- `docs/proofs/single-dimension-contract.md`: proof note.

Incoming dependencies:

- `CircleSVG` and `CirclePDF` inherit from `SingleDimensionDrawingComponent`.
- `RegularPolygonDrawingComponent` depends on the same component hierarchy
  through `PolarCoordinateDrawingComponent`.
- Component serialization tests rely on deterministic `parameters` and
  `create_from_dict()` behavior.
- Component groups and renderers consume inherited `point_1`, `point_2`,
  `points`, `bbox`, and `convex_hull` where subclasses do not override them.

Outgoing dependencies:

- The size setter delegates validation to `StandardDrawingComponent.point_2`,
  which checks finite non-negative coordinates.
- No dependency or package was added.

Before/after edge changes:

- Before this slice, setting `size` at an asymmetric position used
  `x + size` for both `point_2.x` and `point_2.y`.
- After this slice, the diagonal endpoint is `(x + size, y + size)`.
- Existing radius validation remains owned by circle and regular-polygon
  subclasses.

Cycle/layer/coupling/redundancy result:

- Cycle check: no new dependency cycle is introduced.
- Layer check: geometry remains in the component model.
- Coupling check: dependent renderers remain consumers of component geometry.
- Redundancy check: no duplicate size logic was added.

ADR/rule impact:

- No ADR is required. This is a bug fix to an existing geometry invariant.

## Domain Definitions

- A single-dimension component is defined by public `position = (x, y)` and
  scalar `size`.
- The public invariant is `point_1 == position` and
  `point_2 == (x + size, y + size)`.
- This slice preserves existing validation semantics for negative sizes and
  non-finite values by relying on `point_2` validation.
- Renderer-specific circle output is outside this slice except for the inherited
  hidden point geometry after `CircleSVG.radius` mutation.

## Fix Log

- Fixed `SingleDimensionDrawingComponent.size` setter to compute
  `point_2.y` from `self._p1.y + value` instead of `self._p1.x + value`.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Asymmetric position size mutation | Preserve `(x + size, y + size)` endpoint | PO-SDIM-001 | `test_single_dimension_size_updates_asymmetric_position_diagonal` | mutation target |
| Position mutation | Preserve current size and recompute both axes | PO-SDIM-002 | `test_single_dimension_position_updates_preserve_size_on_asymmetric_coordinates` | focused test |
| Serialization | Round-trip mutated geometry deterministically | PO-SDIM-003 | `test_single_dimension_parameters_round_trip_after_size_mutation` | focused test |
| Dependent circle path | Circle radius setter keeps inherited endpoint coherent | PO-SDIM-004 | `test_circle_radius_setter_preserves_hidden_single_dimension_diagonal` | focused test |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Geometry setters are deterministic. | SINGLE-DIM-P1 tests |
| Behavioral/condition | yes | The slice defines public component geometry behavior. | Tests marked `@pytest.mark.condition("SINGLE-DIM-P1")` |
| Failure-mode | limited | The fix addresses wrong accepted output, not a rejected-input path. | Regression test on asymmetric coordinate partition |
| Integration/live-path | yes | Circle radius mutation exercises a dependent subclass. | Circle hidden-point test |
| Contract/API compatibility | yes | Existing component, circle, and rectangle tests must continue passing. | Focused gate |
| Property/fuzz | no | The bug is a two-axis formula error covered by asymmetric representative values. | Not applicable |
| Mutation | yes | The arithmetic formula is proof-critical. | Result recorded below |
| Security/adversarial | no | No path, network, subprocess, archive, SQL, template, or active-content surface changed. | Not applicable |
| Performance/resource | no | Constant-time arithmetic change only. | Not applicable |
| Concurrency/race | no | No shared state, locks, workers, or temp files changed. | Not applicable |
| Golden artifact/visual | limited | No renderer bytes changed in this slice; inherited geometry coherence is tested. | Circle hidden-point test |
| Regression | yes | Prevents reintroduction of x-axis reuse for y-coordinate. | Size mutation test |

## Mutation Testing Gate

Proof-critical mutation targets:

- Replacing `self._p1.y` with `self._p1.x` or otherwise changing the y-axis
  endpoint formula must fail asymmetric geometry tests.
- Removing point assignment must fail size mutation, round-trip, or circle
  dependent tests.

Current result:

- Cosmic Ray 8.4.6, scoped to `SingleDimensionDrawingComponent.size`:
  2805 raw work items, 33 proof-critical work items after filter, 33 killed, 0
  survived.

## PO-SDIM-001: Size Mutation Preserves Both Axes

### Claim

Setting `size` preserves the position and moves `point_2` to
`(position.x + size, position.y + size)`.

### Domain

Single-dimension components with finite non-negative coordinates and ordinary
numeric size values accepted by inherited point validation.

### Proof Method

The setter constructs `Point(self._p1.x + value, self._p1.y + value)` and then
delegates to `point_2`. The focused test uses `position=(5, 2)` and
`size=7.5`, where x/y confusion is observable.

### Conclusion

Proven for the stated domain after focused tests and mutation pass.

## PO-SDIM-002: Position Mutation Preserves Size

### Claim

Changing position preserves the current size and recomputes the diagonal from
the new position.

### Domain

Existing single-dimension components whose current size is valid at the new
position.

### Proof Method

The position setter stores the current `size`, updates `point_1`, then assigns
`size` through the fixed setter. The focused test uses asymmetric coordinates.

### Conclusion

Proven for the stated domain after focused tests pass.

## PO-SDIM-003: Serialization Reflects Correct Geometry

### Claim

Serialized single-dimension payloads round-trip after size mutation.

### Domain

Single-dimension components with style-bearing payloads.

### Proof Method

The focused test mutates size, serializes parameters, hydrates with a style
cache, and compares parameters plus the hidden endpoint.

### Conclusion

Proven for the stated domain after focused tests pass.

## PO-SDIM-004: Dependent Circle Radius Mutation Is Coherent

### Claim

`CircleSVG.radius` mutation, which delegates to inherited `size`, keeps hidden
single-dimension endpoint geometry coherent.

### Domain

Circle SVG instances with valid radius values at asymmetric positions.

### Proof Method

The focused test mutates `circle.radius` at `position=(5, 2)` and asserts
`point_2 == (12.5, 9.5)`.

### Conclusion

Proven for the stated representative dependent path after focused tests pass.
