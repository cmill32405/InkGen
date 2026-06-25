# Table Merge Argument Contract

This note applies the InkGen Definition of Done to the TABLE-MERGE-ARG-P2
slice. It closes the direct public `Cell.merge()` argument boundary so
non-`Cell` values fail explicitly before incidental attribute lookup.

## Scope

The slice covers:

- `Cell.merge()` argument validation.
- Valid same-table direct merge behavior.
- Existing cross-table merge rejection.
- Valid direct merge output through `TableSVG` and `FlowDocument`.

Serialized merge-state hydration remains covered by
`table-cell-merge-contract.md`.

## Architecture Impact

Affected surface:

- `src/InkGen/table.py`: direct `Cell.merge()` public boundary.
- `tests/test_table_contract.py`: TABLE-MERGE-ARG-P2 behavioral and
  dependent-path tests.
- `docs/proofs/table-merge-argument-contract.md`: this proof note.

Incoming dependencies:

- Public callers invoke `Cell.merge(other_cell)` to define merge regions.
- Serialized table payloads are produced from valid direct merge state.
- `TableSVG` and `FlowDocument` consume merged table state downstream.

Outgoing dependencies:

- Merge argument validation depends only on the local `Cell` class.
- Existing table ownership checks, index access, and merge-state assignment
  remain unchanged.

Before/after edge changes:

- Before this slice, `Cell.merge(None)` and other non-cell values raised raw
  `AttributeError` from `.table` lookup.
- After this slice, non-cell values raise explicit `TypeError`.
- Same-table valid merges and cross-table `ValueError` behavior are preserved.
- No dependency, renderer, or artifact flow edge was added.

Cycle/layer/coupling/redundancy result:

- Cycle check: no imports from InkGen modules were added.
- Layer check: table authoring owns its merge API contract.
- Coupling check: renderers remain consumers of merge state, not validators of
  merge arguments.
- Redundancy check: this complements serialized merge validation; it does not
  duplicate the hydration coordinate checks.

ADR/rule impact:

- No ADR is required. This reinforces the dependency-map rule that authoring
  models own their public contracts.

## Domain Definitions

- Accepted merge arguments are `Cell` instances from the same table.
- `Cell` instances from another table are rejected with `ValueError`.
- Non-`Cell` values are rejected with `TypeError`.
- Valid direct merge state must still expose public merge properties and remain
  usable by SVG and flow-document output paths.

## Fix Log

- Added an explicit `isinstance(other, Cell)` guard in `Cell.merge()`.
- Added non-cell rejection tests.
- Added cross-table rejection preservation test.
- Added valid direct merge live-path test.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Same-table `Cell` | Preserve merge region | PO-TMARG-001 | `test_table_cell_merge_valid_argument_remains_live` | mutation target |
| Different-table `Cell` | Reject with `ValueError` | PO-TMARG-002 | `test_table_cell_merge_preserves_cross_table_rejection` | mutation target |
| Non-`Cell` values | Reject with `TypeError` before attribute access | PO-TMARG-003 | `test_table_cell_merge_rejects_non_cell_arguments` | mutation target |
| Serialized merge state | Existing hydration contract | TABLE-CELL-MERGE-P2 | existing tests | out of scope here |
| Private mutation of cell indexes | Excluded | none | none | out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Direct argument validation is deterministic. | TABLE-MERGE-ARG-P2 tests |
| Behavioral/condition | yes | The slice defines direct public merge behavior. | Tests marked `@pytest.mark.condition("TABLE-MERGE-ARG-P2")` |
| Failure-mode | yes | Non-cell values must fail explicitly. | Rejection tests |
| Integration/live-path | yes | Valid merges must remain usable downstream. | SVG and flow-document live-path test |
| Contract/API compatibility | yes | Existing cross-table rejection and valid merge behavior must continue. | Existing `test_table.py` plus new preservation tests |
| Property/fuzz | no | Merge argument classes are finite and enumerated. | Not applicable |
| Mutation | yes | Argument guard and ownership branch are proof-critical. | Mutation gate recorded below |
| Security/adversarial | no | No file path, network, subprocess, SQL, template, or active-content surface changed. | Not applicable |
| Performance/resource | no | The change adds one constant-time type check. | Code inspection |
| Concurrency/race | no | No shared state, background workers, locks, or temp files changed. | Not applicable |
| Golden artifact/visual | no | The slice preserves output-path reachability but does not claim byte identity. | Not applicable |
| Regression | yes | This closes raw `AttributeError` failures for malformed merge arguments. | Non-cell rejection tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Weakening the non-cell guard must fail non-cell rejection tests.
- Weakening the cross-table guard must fail cross-table rejection tests.
- Breaking valid merge state must fail public merge-state and output-path tests.

Current result:

- Cosmic Ray 8.4.6, scoped to direct merge argument, ownership, and merge-region
  rows: 736 generated work items filtered to 39 proof-critical work items; 39
  killed and 0 survived. Mutation exposed two test gaps that were closed before
  the passing rerun: table ownership must be identity rather than equality, and
  valid merge tests must cover a 3x3 region so inclusive loop bounds are
  constrained.

## PO-TMARG-001: Same-Table Cells Merge

### Claim

Merging two cells from the same table still marks every cell in the rectangular
merge region and returns the top-left cell.

### Domain

`Cell.merge(other)` calls where `other` is a `Cell` from the same table.

### Proof Method

The valid live-path test merges a 2x2 region, checks public merge properties on
all four cells, renders through `TableSVG`, and exports through `FlowDocument`.

### Conclusion

Supported by behavioral and dependent-path evidence; proven for the stated
finite domain when tests and mutation pass.

## PO-TMARG-002: Different-Table Cells Are Rejected

### Claim

Cells from different tables continue to fail with `ValueError`.

### Domain

`Cell.merge(other)` calls where `other` is a `Cell` from another `Table`.

### Proof Method

The method checks table identity after type validation and raises `ValueError`
when the owners differ.

### Conclusion

Proven for the stated domain when tests and mutation pass.

## PO-TMARG-003: Non-Cell Arguments Are Rejected

### Claim

All non-`Cell` merge arguments fail with `TypeError` before attribute access.

### Domain

All public `Cell.merge(other)` calls where `other` is not an instance of
`Cell`.

### Proof Method

The method checks `isinstance(other, Cell)` before reading `other.table`.
Condition tests cover representative non-cell values.

### Conclusion

Proven for the stated domain when tests and mutation pass.
