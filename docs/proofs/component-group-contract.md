# Component Group Contract Proof Obligations

This note applies the InkGen Definition of Done to the COMPONENT-GROUP-P1,
COMPONENT-GROUP-PAYLOAD-P2, and COMPONENT-GROUP-STYLES-MAPPING-P2 base
component group slices. It covers the shared `ComponentGroup` boundary used by
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

- `src/InkGen/component.py`: base component-group storage typing, fail-fast add
  boundary, serialized payload validation, and style-cache validation.
- `tests/test_component_group_contract.py`: COMPONENT-GROUP-P1,
  COMPONENT-GROUP-PAYLOAD-P2, and COMPONENT-GROUP-STYLES-MAPPING-P2
  behavioral, failure-mode, geometry, and serialization tests.
- `tests/mutation/component_group_cosmic_ray.toml`: scoped mutation gate.
- `tests/mutation/filter_component_group_work_items.py`: proof-critical
  mutation filter.
- `tests/mutation/filter_component_group_payload_work_items.py`:
  COMPONENT-GROUP-PAYLOAD-P2 mutation filter.
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
- Style-cache reuse depends on mutable mappings keyed by style name and style
  values matching the serialized style class.
- No third-party dependency was added.

Before/after edge changes:

- Before this slice, `ComponentGroup.add_component()` silently ignored
  non-`Component` objects.
- Before COMPONENT-GROUP-PAYLOAD-P2, malformed serialized group roots,
  component envelopes, style envelopes, and unsupported dynamic type names
  could fail through incidental subscription, `AttributeError`, or dynamic
  dispatch errors.
- Before COMPONENT-GROUP-STYLES-MAPPING-P2, direct component-group hydration
  accepted malformed style-cache containers until incidental `.keys()` or item
  assignment failures, and cached style entries were reused without checking
  that they matched the serialized style kind.
- After this slice, invalid add attempts raise `TypeError` and leave existing
  group contents unchanged.
- After COMPONENT-GROUP-PAYLOAD-P2, group hydration validates the serialized
  root, component collection, component envelopes, style envelopes, and dynamic
  class names before constructing components.
- After COMPONENT-GROUP-STYLES-MAPPING-P2, group hydration accepts only mutable
  style-cache mappings or `None` and rejects wrong-kind cached style overrides
  before constructing style-bearing components.
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
- Serialized component-group roots must be mappings with a `ComponentGroup`
  mapping payload.
- Serialized group payloads must include `group_label` and a non-string
  `components` sequence.
- Each serialized component entry must be a single-key mapping whose key is a
  string component type and whose value is a mapping payload.
- Serialized style envelopes, when present, must be single-key mappings with a
  string style type and a mapping entry containing a string `name`.
- Direct style-cache arguments must be mutable mappings or `None`.
- Existing style-cache entries reused during hydration must be instances of the
  serialized style class.
- Dynamic component type names must resolve to classes in the `Component`
  hierarchy.
- Empty-group geometry behavior is outside this slice; this slice preserves
  the current Shapely-derived behavior for empty groups.

## Fix Log

- Added an explicit `dict[int, Component]` annotation for
  `ComponentGroup._components`.
- Changed `ComponentGroup.add_component()` from silent ignore to `TypeError`
  for non-`Component` values.
- Added explicit serialized payload-envelope validation for
  `ComponentGroup.create_from_dict()`.
- Preserved valid base `Component` hydration by calling its one-argument
  factory without a style argument.
- Added explicit `styles` cache validation for direct
  `ComponentGroup.create_from_dict()` calls.
- Added wrong-kind cached style override rejection before component factory
  dispatch.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid components | Store by id, preserve insertion order, expose through lookup/iteration | PO-CGROUP-001 | `test_component_group_preserves_valid_components_in_insertion_order` | mutation target |
| Invalid add inputs | Reject and preserve existing contents | PO-CGROUP-002 | `test_component_group_rejects_invalid_components_without_mutating_group` | mutation target |
| Missing ids | Raise `InvalidComponentID` on lookup/removal | PO-CGROUP-003 | `test_component_group_lookup_and_removal_fail_loudly_for_missing_ids` | existing behavior |
| Geometry aggregation | Aggregate drawable child points, bbox, and hull | PO-CGROUP-004 | `test_component_group_geometry_aggregates_only_component_points` | existing behavior |
| Serialization | Preserve label, component order, and style cache reuse on round trip | PO-CGROUP-005 | `test_component_group_round_trip_preserves_label_order_and_styles` | existing behavior |
| Serialized group payload envelopes | Reject malformed roots, collections, component entries, style envelopes, and unsupported type names before dynamic dispatch | PO-CGROUP-006 | `test_component_group_hydration_rejects_malformed_payload_envelopes`, `test_component_group_hydration_rejects_malformed_style_envelopes` | killed/equivalent |
| Base component payloads | Hydrate valid style-free base `Component` entries | PO-CGROUP-007 | `test_component_group_round_trip_preserves_base_components` | killed/equivalent |
| Style-cache mapping boundary | Reject non-mutable style caches and wrong-kind cached style overrides before component construction | PO-CGROUP-008 | `test_component_group_hydration_rejects_malformed_style_caches`, `test_component_group_hydration_reuses_valid_style_cache_entries`, `test_component_group_hydration_rejects_wrong_kind_style_overrides` | pending |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Group storage, lookup, and serialization are deterministic. | COMPONENT-GROUP-P1 tests |
| Behavioral/condition | yes | The slice defines a public component-group contract. | Tests are marked `@pytest.mark.condition("COMPONENT-GROUP-P1")`. |
| Failure-mode | yes | Invalid add inputs and missing ids must fail loudly. | Invalid add and missing-id tests |
| Integration/live-path | yes | Layer, drawing group, and PDF render guard tests exercise dependent paths. | Focused gate includes dependent tests |
| Contract/API compatibility | yes | Existing component and layer tests plus serialized payload tests must continue passing. | Focused gate |
| Property/fuzz | no | The changed add boundary is finite type validation. | Not applicable |
| Mutation | yes | The changed fail-fast boundary is proof-critical. | Result recorded below |
| Security/adversarial | no | No file path, network, subprocess, archive, SQL, template, or active-content surface changed. | Not applicable |
| Performance/resource | no | Adds constant-time type validation on add. | Code inspection |
| Concurrency/race | no | No shared mutable global state, locks, workers, or temp files changed. | Not applicable |
| Golden artifact/visual | no | No renderer output syntax changed. | Not applicable |
| Regression | yes | Prevents invalid components from disappearing silently. | Invalid add test |
| Serialized payload adversarial input | yes | Malformed group hydration payloads must fail before incidental dynamic dispatch errors. | COMPONENT-GROUP-PAYLOAD-P2 tests |
| Style-cache adversarial input | yes | Direct hydration style caches are externally supplied mutable state and must fail before incidental mapping or downstream component-constructor errors. | COMPONENT-GROUP-STYLES-MAPPING-P2 tests |

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
- Cosmic Ray 8.4.6, scoped to COMPONENT-GROUP-PAYLOAD-P2 payload validation
  and dispatch rows: 57 work items, 56 killed, and 1 documented equivalent
  survivor.
- Cosmic Ray 8.4.6, scoped to COMPONENT-GROUP-STYLES-MAPPING-P2 style-cache
  normalization and cached override type-guard rows: 7 work items, 7 killed,
  and 0 survivors.
- Equivalent survivor:
  - `create_from_dict`: `component_class is Component` changed to
    `component_class == Component`.
- Equivalence proof: inside the declared domain, `component_class` is a normal
  Python class object resolved from `InkGen.component`. Python class equality
  for these classes is identity equality, so `component_class == Component` and
  `component_class is Component` select the same branch for every supported
  serialized component type.

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

## PO-CGROUP-006: Serialized Group Envelopes Fail Explicitly

### Claim

`ComponentGroup.create_from_dict()` rejects malformed serialized roots,
component collections, component entries, style envelopes, and unsupported type
names before dynamic component construction.

### Domain

Public group hydration calls using `ComponentGroup.create_from_dict(data,
styles=None)`.

### Proof Method

Local helpers validate the `ComponentGroup` root, required fields, collection
shape, component-entry envelope, style envelope, and dynamic class resolution
before component factories are called. Focused condition tests cover malformed
roots, missing fields, string collections, non-mapping entries, empty or
multi-key entries, non-string type keys, non-mapping component payloads,
unsupported component names, non-class module attributes, non-component classes,
and malformed style envelopes.

### Conclusion

Proven for the stated domain after focused tests and mutation pass with one
documented equivalent survivor.

## PO-CGROUP-007: Base Components Hydrate Without Style Arguments

### Claim

Serialized base `Component` entries in a component group hydrate without passing
an unsupported style argument.

### Domain

Component groups containing valid style-free base `Component` payloads.

### Proof Method

`ComponentGroup.create_from_dict()` dispatches the base `Component` factory with
only the serialized entry and dispatches subclasses through the existing
style-aware path. The focused test round trips a group containing a base
`Component` and asserts exact serialized parameters.

### Conclusion

Proven for the stated domain after focused tests and mutation pass with one
documented equivalent survivor.

## PO-CGROUP-008: Style Cache Boundaries Fail Explicitly

### Claim

`ComponentGroup.create_from_dict()` rejects malformed direct style-cache
containers and rejects cached style overrides whose value type does not match
the serialized style envelope.

### Domain

Public component-group hydration calls using
`ComponentGroup.create_from_dict(data, styles=...)` with `styles` as `None`,
mutable mappings, or malformed non-mapping/non-mutable containers.

### Proof Method

`_component_group_style_cache()` normalizes `None` to a fresh mutable mapping
and rejects non-`MutableMapping` inputs before hydration loops touch the cache.
During style-envelope hydration, the serialized style class is resolved before
cache reuse, and any existing cached style with the serialized name must be an
instance of that resolved class. Focused tests cover malformed style-cache
containers, identity-preserving valid cache reuse, and wrong-kind cached style
override rejection.

### Conclusion

Proven for the stated domain after focused behavioral tests and scoped mutation
testing. Full repository coverage, lint, docs, and diff hygiene remain
release-gate checks for the slice.
