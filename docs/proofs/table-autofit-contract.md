# Table Autofit Boolean Contract

This note applies the InkGen Definition of Done to the TABLE-AUTOFIT-P2 table
autofit slice. It closes the public boolean boundary where `Table` previously
coerced arbitrary truthy and falsy values with `bool(...)`.

## Scope

The slice covers:

- `Table.__init__()`
- `Table.autofit`
- `Table.parameters`
- `Table.create_from_dict()`
- `_normalize_bool()`
- `_register_autofit()`

## Architecture Impact

Affected surface:

- `src/InkGen/table.py`: autofit construction, setter, hydration, and queue
  registration.
- `tests/test_table_contract.py`: focused TABLE-AUTOFIT-P2 tests.
- `tests/test_table.py`: existing autofit queue compatibility tests.

Incoming dependencies:

- Public callers import `Table` from `InkGen`.
- `TableSVG` and `FlowDocument` consume table geometry and cell content.
- Saved table payloads hydrate through `Table.create_from_dict()`.
- Cell paragraph insertion relies on `_register_autofit()` when autofit is
  enabled.

Outgoing dependencies:

- Autofit queue entries depend on row and column `AutoFitRule` values.
- Serialization stores the boolean as `auto_fit`.
- Validation depends only on Python `isinstance(value, bool)`.

Before/after edge changes:

- Before this slice, constructor, setter, and hydration used `bool(...)`, so
  values such as `"false"`, `1`, and arbitrary objects could silently enable
  autofit.
- After this slice, public autofit values must be actual `bool` instances.
- No dependency direction changed and no third-party dependency was introduced.

Cycle/layer/coupling/redundancy result:

- Cycle check: no imports were added.
- Layer check: the table model owns table state validation; renderers remain
  consumers.
- Coupling check: queue behavior still depends only on the table's own row and
  column rule state.
- Redundancy check: constructor and setter share one local helper.

Evidence source and freshness:

- Source-backed: `table.py`, `test_table.py`, `test_table_contract.py`,
  `docs/proofs/table-contract.md`, and `docs/dependency-map.md` were read
  before editing.
- Test-backed: focused tests exercise constructor rejection, setter rejection
  with state preservation, hydration rejection, and live queue behavior for
  valid `True`.

ADR/rule impact:

- No new ADR is required because this is a public boundary hardening change
  inside the existing table model responsibility.

## Domain Definitions

- Accepted autofit values are exactly `True` and `False`.
- Rejected values include integers, strings, empty strings, objects, and any
  non-`bool` value.
- Serialized `auto_fit` must obey the same boolean contract.
- Valid `True` must still register autofit queue entries when cell content is
  added.

## Fix Log

- Added `_normalize_bool()`.
- Routed `Table.__init__()` and the `autofit` setter through the helper.
- Added constructor, setter atomicity, hydration, and live queue tests.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid `True` | Preserve and register queue entries | PO-TAF-001 | `test_table_autofit_true_still_registers_queue_entries` | mutation target |
| Valid `False` | Preserve and suppress queue entries | PO-TAF-001 | existing `test_table.py` coverage | mutation target |
| Non-bool constructor values | Reject before table state is created | PO-TAF-002 | `test_table_autofit_rejects_non_bool_values` | mutation target |
| Non-bool setter values | Reject and preserve previous state | PO-TAF-003 | same | mutation target |
| Serialized non-bool `auto_fit` | Reject through hydration | PO-TAF-004 | `test_table_autofit_hydration_rejects_non_bool_values` | mutation target |
| Private `_auto_fit` mutation | Excluded from public contract | Explicit exclusion | none | out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Boolean validation and queue registration are deterministic. | TABLE-AUTOFIT-P2 tests |
| Behavioral/condition | yes | The slice defines public table autofit behavior. | Tests marked `@pytest.mark.condition("TABLE-AUTOFIT-P2")` |
| Failure-mode | yes | Invalid constructor, setter, and payload values must fail loudly. | Rejection tests |
| Integration/live-path | yes | Valid true autofit must affect cell paragraph registration. | Queue live-path test |
| Contract/API compatibility | yes | Existing table geometry and serialization behavior must continue passing. | Existing table tests |
| Property/fuzz | no | The boolean domain is finite and exhaustively partitioned. | Not applicable |
| Mutation | yes | Guards, hydration routing, and queue branch are proof-critical. | Mutation gate recorded below |
| Security/adversarial | no | No file path, network, subprocess, secret, SQL, template, or active-content surface changed. | Not applicable |
| Performance/resource | no | The slice adds constant-time validation. | Code inspection |
| Concurrency/race | no | No shared state, locks, workers, or temp files changed. | Not applicable |
| Golden artifact/visual | no | No generated artifact syntax or geometry changes. | Not applicable |
| Regression | yes | This closes truthiness coercion of non-bool values. | Rejection tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Replacing strict bool validation should fail constructor/setter/hydration
  rejection tests.
- Bypassing constructor validation during hydration should fail serialized
  payload tests.
- Weakening `_register_autofit()` should fail queue behavior tests.

Current result:

- Cosmic Ray 8.4.6, scoped to strict bool validation, hydration routing, and
  queue registration: 10 work items, 10 killed, and 0 survived.

## PO-TAF-001: Valid Bool Values Control Queue Behavior

### Claim

For `autofit=True`, adding cell content registers an autofit queue entry; for
`autofit=False`, existing tests show the queue remains suppressed.

### Domain

Tables constructed or updated through the public boolean autofit boundary.

### Proof Method

`_register_autofit()` checks the stored boolean state before appending queue
entries. Focused and existing tests exercise the public cell paragraph path.

### Conclusion

Proven after focused tests and mutation pass.

## PO-TAF-002: Constructor Rejects Non-Bool Autofit

### Claim

`Table(autofit=value)` accepts only real bool values.

### Domain

All public constructor calls.

### Proof Method

`Table.__init__()` routes `autofit` through `_normalize_bool()`, which rejects
anything that is not a `bool`.

### Conclusion

Proven after focused tests and mutation pass.

## PO-TAF-003: Setter Rejects Non-Bool Autofit Atomically

### Claim

Assigning a non-bool to `table.autofit` raises and preserves the previous
boolean value.

### Domain

All public setter assignments.

### Proof Method

The setter calls `_normalize_bool()` before assigning `_auto_fit`. The focused
test captures the previous state and compares after each rejected assignment.

### Conclusion

Proven after focused tests and mutation pass.

## PO-TAF-004: Hydration Cannot Bypass Bool Validation

### Claim

Serialized table payloads with non-bool `auto_fit` values fail during
`Table.create_from_dict()`.

### Domain

Payloads passed to `Table.create_from_dict()`.

### Proof Method

`create_from_dict()` delegates `payload["auto_fit"]` to the constructor, so the
same `_normalize_bool()` boundary applies.

### Conclusion

Proven after focused tests and mutation pass.

## Current Slice Decision

The slice rejects truthiness coercion instead of interpreting strings or
integers. This keeps the public API narrow, matches the annotation, and prevents
serialized data from silently changing table autofit behavior.
