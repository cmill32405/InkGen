# Component Group Contract Proof Obligations

This note applies the InkGen Definition of Done to the COMPONENT-GROUP-P1 base
component group slice. It covers the shared `ComponentGroup` boundary used by
document layers, SVG/PDF renderers, CAD helpers, truth records, and serialized
recipes.

## Scope

The slice covers:

- `ComponentGroup.__init__()`
- `ComponentGroup.add_component()`
- `ComponentGroup.get_component()`
- `ComponentGroup.remove_component()`
- `ComponentGroup.components()`
- `ComponentGroup.points`
- `ComponentGroup.bbox`
- `ComponentGroup.convex_hull`
- `ComponentGroup.parameters`
- `ComponentGroup.create_from_dict()`

## Architecture Impact

Affected surface:

- `src/InkGen/component.py`: base component-group storage typing and
  fail-fast add boundary.
- `tests/test_component_group_contract.py`: COMPONENT-GROUP-P1 behavioral,
  failure-mode, geometry, and serialization tests.
- `tests/mutation/component_group_cosmic_ray.toml`: scoped mutation gate.
- `tests/mutation/filter_component_group_work_items.py`: proof-critical
  mutation filter.
- `docs/api-reference.md`: base group contract note.
- `docs/proofs/component-group-contract.md`: proof note.

Incoming dependencies:

- `Layer.add_component_group()` consumes component-group points and convex hulls
  for canvas containment and collision checks.
- `Document`, `DocumentSVG`, and `DocumentPDF` serialize groups through
  `parameters` and hydrate them through `create_from_dict()`.
- `ComponentGroupSVG` and `ComponentGroupPDF` inherit from `ComponentGroup`;
  `ComponentGroupPDF` applies its closed-domain guard before delegating to the
  base add boundary.
- CAD zoning and examples build shared component groups.
- Truth emitters and renderers iterate `components()` in insertion order.

Outgoing dependencies:

- Component groups depend on `Component` identity/id contracts.
- Geometry aggregation depends on Shapely `MultiPoint` and `get_coordinates`.
- Serialization hydration depends on concrete component `create_from_dict()`
  implementations and optional style cache reuse.
- No third-party dependency was added.

Before/after edge changes:

- Before this slice, `ComponentGroup.add_component()` silently ignored
  non-`Component` objects.
- After this slice, invalid add attempts raise `TypeError` and leave existing
  group contents unchanged.
- Valid components, insertion order, lookup/removal exceptions, geometry
  aggregation, and serialization round trips are preserved.

Cycle/layer/coupling/redundancy result:

- Cycle check: no new dependency cycle is introduced.
- Layer check: base component grouping remains in the component model.
- Coupling check: renderer-specific guards stay in renderer subclasses; the
  base group only enforces the common `Component` contract.
- Redundancy check: no duplicate group implementation is added.

ADR/rule impact:

- ADR-0002 remains satisfied. `ComponentGroupPDF.add_component()` still rejects
  unsupported PDF components before calling the base group.
- No new ADR is required.

## Domain Definitions

- A valid base group component is an instance of `Component` or a subclass.
- Components are stored by component id and yielded in insertion order.
- Missing component ids raise `InvalidComponentID`.
- Geometry aggregation includes only child components that expose `points`.
- Serialization order follows the stored component insertion order.
- Empty-group geometry behavior is outside this slice; this slice preserves
  the current Shapely-derived behavior for empty groups.

## Fix Log

- Added an explicit `dict[int, Component]` annotation for
  `ComponentGroup._components`.
- Changed `ComponentGroup.add_component()` from silent ignore to `TypeError`
  for non-`Component` values.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid components | Store by id, preserve insertion order, expose through lookup/iteration | PO-CGROUP-001 | `test_component_group_preserves_valid_components_in_insertion_order` | mutation target |
| Invalid add inputs | Reject and preserve existing contents | PO-CGROUP-002 | `test_component_group_rejects_invalid_components_without_mutating_group` | mutation target |
| Missing ids | Raise `InvalidComponentID` on lookup/removal | PO-CGROUP-003 | `test_component_group_lookup_and_removal_fail_loudly_for_missing_ids` | existing behavior |
| Geometry aggregation | Aggregate drawable child points, bbox, and hull | PO-CGROUP-004 | `test_component_group_geometry_aggregates_only_component_points` | existing behavior |
| Serialization | Preserve label, component order, and style cache reuse on round trip | PO-CGROUP-005 | `test_component_group_round_trip_preserves_label_order_and_styles` | existing behavior |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Group storage, lookup, and serialization are deterministic. | COMPONENT-GROUP-P1 tests |
| Behavioral/condition | yes | The slice defines a public component-group contract. | Tests are marked `@pytest.mark.condition("COMPONENT-GROUP-P1")`. |
| Failure-mode | yes | Invalid add inputs and missing ids must fail loudly. | Invalid add and missing-id tests |
| Integration/live-path | yes | Layer, drawing group, and PDF render guard tests exercise dependent paths. | Focused gate includes dependent tests |
| Contract/API compatibility | yes | Existing component and layer tests must continue passing. | Focused gate |
| Property/fuzz | no | The changed add boundary is finite type validation. | Not applicable |
| Mutation | yes | The changed fail-fast boundary is proof-critical. | Result recorded below |
| Security/adversarial | no | No file path, network, subprocess, archive, SQL, template, or active-content surface changed. | Not applicable |
| Performance/resource | no | Adds constant-time type validation on add. | Code inspection |
| Concurrency/race | no | No shared mutable global state, locks, workers, or temp files changed. | Not applicable |
| Golden artifact/visual | no | No renderer output syntax changed. | Not applicable |
| Regression | yes | Prevents invalid components from disappearing silently. | Invalid add test |

## Mutation Testing Gate

Proof-critical mutation targets:

- Weakening or removing the `Component` type check must fail invalid-add tests.
- Removing storage of valid components must fail insertion-order, lookup, and
  serialization tests.
- Raising on valid components must fail dependent component/layer tests.

Current result:

- Cosmic Ray 8.4.6, scoped to the changed
  `ComponentGroup.add_component()` fail-fast boundary: 2805 raw work items, 2
  proof-critical work items after filter, 2 killed, 0 survived.

## PO-CGROUP-001: Valid Components Are Stored Deterministically

### Claim

Valid `Component` instances and subclasses are stored by id, yielded in
insertion order, and serialized in that same order.

### Domain

Base `Component`, drawing components, and standard drawable subclasses.

### Proof Method

The focused test adds representative components, asserts iteration order,
identity-preserving lookup, and exact serialized payload order.

### Conclusion

Proven for the stated domain after focused tests and mutation pass.

## PO-CGROUP-002: Invalid Add Attempts Fail Loudly

### Claim

Objects outside the `Component` hierarchy are rejected at the group boundary and
do not mutate existing group contents.

### Domain

Non-component objects, `None`, and strings passed to `add_component()`.

### Proof Method

`add_component()` checks `isinstance(component, Component)` and raises
`TypeError` otherwise. The focused test verifies contents are unchanged after
multiple invalid attempts.

### Conclusion

Proven for the stated domain after focused tests and mutation pass.

## PO-CGROUP-003: Missing Ids Raise Project Exceptions

### Claim

Missing component ids fail with `InvalidComponentID` during lookup and removal.

### Domain

`get_component()` and `remove_component()` calls where the id is not present in
the group.

### Proof Method

The focused test asserts both lookup and removal failures raise
`InvalidComponentID`.

### Conclusion

Proven for the stated domain after focused tests pass.

## PO-CGROUP-004: Geometry Aggregates Drawable Child Points

### Claim

Group geometry aggregates points from child components that expose `points` and
ignores non-drawing base components.

### Domain

Mixed groups containing a base `Component`, a two-point drawing component, and
a rectangle-like width/height component.

### Proof Method

The focused test asserts the exact aggregated point list, bounding box, and
convex hull.

### Conclusion

Proven for the stated representative domain after focused tests pass.

## PO-CGROUP-005: Serialized Groups Hydrate Deterministically

### Claim

Component-group serialization preserves label, component order, and style cache
reuse on hydration.

### Domain

Groups containing style-bearing component subclasses whose classes are
resolvable from `InkGen.component`.

### Proof Method

The focused test serializes a group, hydrates it with a style cache, and asserts
label, component type order, and exact parameter equality.

### Conclusion

Proven for the stated domain after focused tests pass.
