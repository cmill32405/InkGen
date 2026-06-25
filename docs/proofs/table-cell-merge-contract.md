# Table Cell Merge Contract

This note applies the InkGen Definition of Done to the TABLE-CELL-MERGE-P2
slice. It closes the serialized table-cell merge-state boundary so hydrated
cells cannot expose non-boolean merge flags or malformed merge coordinates.

## Scope

The slice covers:

- `Table.create_from_dict()` when hydrating serialized cell merge state
- `_normalize_bool(..., name="merged")`
- `_normalize_cell_coordinate()`
- `Cell.merged`, `Cell.merge_start`, and `Cell.merge_end` as public read
  contracts
- `TableSVG.from_table()` and `FlowDocument` as dependent output paths

## Architecture Impact

Affected surface:

- `src/InkGen/table.py`: serialized cell merge-state validation.
- `tests/test_table_contract.py`: TABLE-CELL-MERGE-P2 behavioral and
  dependent-path tests.
- `docs/proofs/table-cell-merge-contract.md`: this proof note.

Incoming dependencies:

- Public callers read hydrated merge state through `Cell.merged`,
  `Cell.merge_start`, and `Cell.merge_end`.
- Saved table payloads hydrate merge state through `Table.create_from_dict()`.
- `TableSVG` and `FlowDocument` consume the hydrated table as downstream output
  paths.

Outgoing dependencies:

- Merge flag validation depends on the existing strict boolean normalizer.
- Merge coordinate validation depends only on Python sequence unpacking and
  integer/bounds checks against the hydrated table dimensions.

Before/after edge changes:

- Before this slice, serialized payloads assigned raw `merged`,
  `merge_start`, and `merge_end` values directly into private fields.
- After this slice, merge flags must be real bools and merge coordinates must
  be two non-bool integer indexes inside the table dimensions.
- No import, dependency, renderer, or public artifact edge was added.

Cycle/layer/coupling/redundancy result:

- Cycle check: no imports were added.
- Layer check: the table model owns merge-state validation; renderers and flow
  documents remain consumers.
- Coupling check: the helper is local and does not depend on output formats.
- Redundancy check: hydration reuses the existing strict bool helper for the
  merge flag.

ADR/rule impact:

- No ADR is required. This reinforces the dependency-map rule that serialized
  authoring contracts are owned by the authoring model.

## Domain Definitions

- Accepted `merged` values are exactly `True` and `False`.
- Accepted merge coordinates are two real `int` values, excluding booleans.
- Accepted coordinate values must satisfy
  `0 <= row_index < table.row_count` and
  `0 <= column_index < table.column_count`.
- Valid merge state must still hydrate and remain usable by SVG and
  flow-document output paths.

## Fix Log

- Routed serialized `merged` values through `_normalize_bool()`.
- Added `_normalize_cell_coordinate()` for merge coordinate payloads.
- Routed serialized `merge_start` and `merge_end` through the coordinate
  normalizer.
- Added invalid flag, invalid coordinate, valid hydration, SVG, and
  flow-document tests.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid merged table | Preserve flag and coordinates | PO-TCM-001 | `test_table_cell_merge_hydration_valid_state_remains_live` | mutation target |
| Non-bool merge flag | Reject during hydration | PO-TCM-002 | `test_table_cell_merge_hydration_rejects_non_bool_merge_flags` | mutation target |
| String/bytes coordinate | Reject during hydration | PO-TCM-003 | `test_table_cell_merge_hydration_rejects_invalid_coordinates` | mutation target |
| Wrong coordinate length | Reject during hydration | PO-TCM-003 | same | mutation target |
| Bool/non-int coordinate member | Reject during hydration | PO-TCM-003 | same | mutation target |
| Out-of-bounds coordinate | Reject during hydration | PO-TCM-003 | same | mutation target |
| Private field mutation after hydration | Excluded from public contract | Explicit exclusion | none | out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Bool and coordinate normalization are deterministic. | TABLE-CELL-MERGE-P2 tests |
| Behavioral/condition | yes | The slice defines serialized merge-state behavior. | Tests marked `@pytest.mark.condition("TABLE-CELL-MERGE-P2")` |
| Failure-mode | yes | Invalid flags and coordinates must fail loudly. | Rejection tests |
| Integration/live-path | yes | Hydrated merged tables must remain usable downstream. | SVG and flow-document live-path test |
| Contract/API compatibility | yes | Existing merge and table round-trip behavior must continue passing. | Existing `test_table.py` |
| Property/fuzz | no | The covered invalid partitions are explicitly enumerated. | Not applicable |
| Mutation | yes | Bool, unpacking, integer, and bounds checks are proof-critical. | Mutation gate recorded below |
| Security/adversarial | no | No file path, network, subprocess, SQL, template, or active-content surface changed. | Not applicable |
| Performance/resource | no | The change adds constant-time validation per hydrated cell. | Code inspection |
| Concurrency/race | no | No shared state, background workers, locks, or temp files changed. | Not applicable |
| Golden artifact/visual | no | This slice preserves renderer reachability but does not claim pixel or byte identity. | Not applicable |
| Regression | yes | This closes malformed serialized merge-state acceptance. | Rejection tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Weakening `merged` bool validation must fail invalid flag tests.
- Weakening coordinate shape/type checks must fail invalid coordinate tests.
- Weakening bounds checks must fail out-of-bounds coordinate tests.
- Breaking the valid hydration route must fail valid merge-state live-path
  tests.

Current result:

- Cosmic Ray 8.4.6, scoped to serialized merge hydration and coordinate
  normalization rows: 671 generated work items filtered to 45 proof-critical
  work items; 45 killed and 0 survived. Signature-separator mutations on the
  helper were excluded as outside the merge-state proof obligation.

## PO-TCM-001: Valid Merge State Remains Live

### Claim

Valid serialized merge state hydrates into public `Cell` merge properties and
the table remains usable by SVG and flow-document paths.

### Domain

Serialized table payloads created from valid in-bounds `Cell.merge()` calls.

### Proof Method

The live-path test hydrates a valid merged table, checks every public merge
property, renders through `TableSVG.from_table()`, and exports through
`FlowDocument`.

### Conclusion

Supported by behavioral and dependent-path evidence; upgraded to proven for the
stated finite domain when tests and mutation pass.

## PO-TCM-002: Merge Flags Are Strict Booleans

### Claim

Serialized `merged` values accept only real bools.

### Domain

All payloads passed to `Table.create_from_dict()` with cell `merged` values.

### Proof Method

Hydration routes the value through `_normalize_bool(..., name="merged")`, which
checks `isinstance(value, bool)` before assigning cell state.

### Conclusion

Proven for the stated domain when tests and mutation pass.

## PO-TCM-003: Merge Coordinates Are Bounded Integer Pairs

### Claim

Serialized `merge_start` and `merge_end` values must be exactly two non-bool
integers inside the hydrated table dimensions.

### Domain

All payloads passed to `Table.create_from_dict()` with cell merge coordinates.

### Proof Method

Hydration routes both fields through `_normalize_cell_coordinate()`, which
rejects strings/bytes, wrong arity, booleans, non-integers, and out-of-bounds
indexes before assigning cell state.

### Conclusion

Proven for the stated domain when tests and mutation pass.
