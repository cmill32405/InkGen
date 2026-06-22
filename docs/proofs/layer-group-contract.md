# Layer Group Contract Proof Obligations

This note applies the InkGen Definition of Done to the LAYER-GROUP-P2 layer
group containment slice. It closes the shared contract gap exposed by SVG and
PDF duplicate-label rendering: `Layer.component_groups` is a label lookup, not
a complete traversal API.

## Scope

The slice covers:

- `Layer.groups()`
- `Layer.remove_component_group()`
- `Layer._restore_group_name_lookup()`
- `Layer.parameters`
- `Layer.create_from_dict()`
- `DocumentSVG._iter_layer_groups()`
- `DocumentPDF._iter_layer_groups()`

## Architecture Impact

Affected surface:

- `src/InkGen/document.py`: public complete group traversal and duplicate-label
  removal semantics.
- `src/InkGen/svg_generator.py`: SVG document traversal now consumes the public
  layer traversal contract.
- `src/InkGen/pdf_generator.py`: PDF document traversal now consumes the public
  layer traversal contract.
- `tests/test_layer_group_contract.py`: LAYER-GROUP-P2 condition tests.
- `tests/mutation/layer_group_cosmic_ray.toml`: scoped mutation gate.
- `tests/mutation/filter_layer_group_work_items.py`: proof-critical mutation
  filter.

Incoming dependencies:

- `DocumentSVG` renders all groups stored on page layers.
- `DocumentPDF` renders all groups and emits truth records from page layers.
- YAML recipe round trips depend on `Layer.parameters` and
  `Layer.create_from_dict()`.
- Existing callers may use `Layer.component_groups` as a label-to-id lookup.

Outgoing dependencies:

- `Layer` depends on `ComponentGroup`, `Canvas`, `Boundary`, and project
  exceptions.
- No renderer dependency was added to `document.py`.
- No package dependency was added.

Before/after edge changes:

- Before this slice, complete traversal required private access to
  `Layer._component_groups` because `component_groups` collapses repeated
  labels.
- Before this slice, removing one group with a repeated label deleted the label
  lookup even when another group with that label remained.
- After this slice, `Layer.groups()` returns every stored group in insertion
  order, including repeated labels.
- After this slice, removing a repeated label restores lookup to the latest
  remaining group with that label, or removes the label only when no group
  remains.
- SVG and PDF traversal no longer depend on private `Layer` storage.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced.
- Layer check: group ownership remains in `document.py`; renderers consume the
  document model contract.
- Coupling check: private renderer-to-layer storage coupling is removed.
- Redundancy check: complete traversal is owned by one public method.

ADR/rule impact:

- No ADR is required. This enforces the dependency-map rule that renderers must
  consume document model contracts rather than private containment storage.

## Domain Definitions

- A `Layer` may contain more than one group with the same semantic
  `group_label`.
- `Layer.component_groups` remains a backwards-compatible label-to-id lookup and
  maps a repeated label to the latest group with that label.
- `Layer.groups()` is the complete traversal API and preserves insertion order.
- `Layer.remove_component_group(id)` removes the addressed group only.
- `Layer.remove_component_group(label)` removes the current lookup target for
  that label.
- Serialized layer payloads must preserve repeated-label groups as distinct
  entries.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Repeated labels in complete traversal | Preserve every stored group in insertion order | PO-LAYER-001 | `test_layer_groups_returns_all_groups_in_insertion_order` | mutation gate |
| Removal by id with repeated labels | Remove only addressed group and keep remaining lookup live | PO-LAYER-002 | `test_layer_remove_by_id_keeps_duplicate_label_lookup_live` | mutation gate |
| Removal by label with repeated labels | Remove current lookup target and restore previous duplicate | PO-LAYER-003 | `test_layer_remove_by_label_restores_previous_duplicate_lookup` | mutation gate |
| Removing the final label group | Clear lookup and reject stale labels | PO-LAYER-004 | `test_layer_remove_last_duplicate_deletes_label_lookup` | mutation gate |
| Serialization round trip | Preserve repeated-label groups as distinct entries | PO-LAYER-005 | `test_layer_serialization_preserves_repeated_label_groups` | mutation gate |
| Renderer dependency path | SVG/PDF consume public traversal | PO-LAYER-006 | `test_document_renderers_use_public_layer_group_contract` | mutation gate |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Layer group lookup/removal/traversal are deterministic. | LAYER-GROUP-P2 tests |
| Behavioral/condition | yes | The slice defines public layer behavior. | Tests are marked `@pytest.mark.condition("LAYER-GROUP-P2")`. |
| Failure-mode | yes | Stale label removal must fail after the final duplicate is removed. | stale-label assertion |
| Integration/live-path | yes | SVG and PDF renderers depend on layer traversal. | renderer helper contract test plus existing SVG/PDF document tests |
| Contract/API compatibility | yes | `component_groups` remains a label lookup while `groups()` adds complete traversal. | lookup and traversal assertions |
| Property/fuzz | no | The duplicate-label partitions are finite and directly tested. | Not applicable |
| Mutation | yes | Traversal, removal, and serialization rows are proof-critical. | Cosmic Ray result recorded below |
| Security/adversarial | no | No path, network, subprocess, archive, SQL, template, or active-content surface changed. | Not applicable |
| Performance/resource | no | Traversal returns a tuple over existing groups; removal scans existing groups by label. | Not applicable |
| Concurrency/race | no | No shared concurrent state, locks, or background workers are added. | Not applicable |
| Golden artifact/visual | covered by dependents | SVG/PDF output is already covered in renderer document slices. | SVG-DOC-P1 and PDF-DOC-P2 focused tests |
| Regression | yes | This closes the shared duplicate-label API gap found during renderer hardening. | LAYER-GROUP-P2 tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Complete group traversal must not collapse repeated labels.
- Removal by id must not delete unrelated duplicate-label groups.
- Removal by label must restore lookup to a remaining duplicate when one
  exists.
- Removing the final duplicate must clear lookup and collision settings.
- Serialization/hydration must preserve repeated-label entries.
- SVG/PDF traversal helpers must call the public `Layer.groups()` contract.

Current result:

- Tool: Cosmic Ray 8.4.6.
- Environment: WSL Python 3.12 virtualenv.
- Raw work items: 4,729.
- Proof-critical work items after filter: 16.
- Killed mutants: 16.
- Surviving mutants: 0.

## PO-LAYER-001: Complete Traversal Preserves Repeated Labels

### Claim

`Layer.groups()` returns every component group stored in a layer in insertion
order, including groups that share the same `group_label`.

### Domain

Public `Layer` instances populated through `add_component_group()`.

### Proof Method

`Layer.groups()` returns the ordered values of the internal group store. The
focused test creates two groups with the same label and verifies both object
identities and insertion order while the label lookup continues to point at the
latest group.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-LAYER-002: Removal By Id Preserves Remaining Duplicate Lookup

### Claim

Removing one duplicate-label group by id removes only that group and leaves any
remaining group with the same label addressable.

### Domain

Public `Layer.remove_component_group(group_id)` calls where `group_id` is a
valid integer id for a stored group.

### Proof Method

The removal path deletes the addressed group and rebuilds the label lookup from
remaining groups. The focused test removes the first duplicate by id and checks
that the second duplicate remains in `groups()`, `component_groups`, and
`group()`.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-LAYER-003: Removal By Label Restores Prior Duplicate Lookup

### Claim

Removing by label removes the current lookup target and restores lookup to a
remaining duplicate if one exists.

### Domain

Public `Layer.remove_component_group(group_label)` calls where the label exists
in `component_groups`.

### Proof Method

String removal resolves the current label target, removes that group, then
rebuilds the label lookup by scanning remaining groups in reverse insertion
order. The focused test removes the latest duplicate and verifies lookup
restores to the prior duplicate.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-LAYER-004: Removing Final Duplicate Clears Lookup

### Claim

After the last group for a label is removed, the label is absent from
`component_groups` and a repeated removal by that label fails.

### Domain

Public removal calls for labels with exactly one remaining stored group.

### Proof Method

The lookup restore helper removes the label and collision settings when no
remaining group has the removed label. The focused test removes the final group
and verifies stale label removal raises `InvalidComponentGroupID`.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-LAYER-005: Serialization Preserves Repeated Labels

### Claim

Layer serialization and hydration preserve repeated-label groups as distinct
component group entries.

### Domain

`Layer.parameters` payloads produced by InkGen and hydrated with
`Layer.create_from_dict()`.

### Proof Method

`Layer.parameters` serializes all stored groups. Hydration iterates each group
payload and adds it back through the public `add_component_group()` path. The
focused test round trips two groups with the same label and verifies both
entries survive.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-LAYER-006: Renderers Consume Public Layer Traversal

### Claim

SVG and PDF document traversal use the public complete group traversal contract
instead of private `Layer` storage.

### Domain

`DocumentSVG._iter_layer_groups()` and `DocumentPDF._iter_layer_groups()` for a
layer populated through `add_component_group()`.

### Proof Method

Both renderer helpers delegate to `Layer.groups()`. The focused test verifies
the helpers return the same complete tuple as the public layer contract.

### Conclusion

Proven for the stated domain after tests and mutation pass.
