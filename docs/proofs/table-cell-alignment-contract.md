# Table Cell Alignment Contract

This note applies the InkGen Definition of Done to the
TABLE-CELL-ALIGNMENT-P2 slice. It closes the public cell vertical-alignment
selector boundary so only real strings from the supported alignment set can
enter table state or serialized table hydration.

## Scope

The slice covers:

- `Cell.vertical_alignment`
- `_normalize_vertical_alignment()`
- `Table.create_from_dict()` when hydrating serialized cell alignment
- `TableSVG.from_table()` as the dependent renderer path
- `FlowDocument` plain-text output as the dependent document path

## Architecture Impact

Affected surface:

- `src/InkGen/table.py`: cell vertical-alignment validation.
- `tests/test_table_contract.py`: TABLE-CELL-ALIGNMENT-P2 behavioral and
  dependent-path tests.
- `docs/proofs/table-cell-alignment-contract.md`: this proof note.

Incoming dependencies:

- Public callers set `Cell.vertical_alignment` through `Table.cell()`.
- Saved table payloads hydrate alignment through `Table.create_from_dict()`.
- `TableSVG` reads `cell.vertical_alignment` to choose text vertical placement.
- `FlowDocument` consumes the same table object for document output paths.

Outgoing dependencies:

- Validation depends only on Python string type checks and finite membership in
  the local allowed set: `{"top", "middle", "bottom"}`.

Before/after edge changes:

- Before this slice, a crafted non-string object that compared equal to an
  allowed alignment could pass membership testing and be stored as table state.
- After this slice, alignment values must be real strings before membership is
  checked.
- No import, dependency, renderer, or public artifact edge was added.

Cycle/layer/coupling/redundancy result:

- Cycle check: no imports were added.
- Layer check: the table model owns its selector contract; renderers consume it.
- Coupling check: the normalizer is local and does not couple table authoring to
  a renderer.
- Redundancy check: direct setter and hydration share the same setter path.

ADR/rule impact:

- No ADR is required. This reinforces the dependency-map rule that authoring
  models own public contracts and output layers consume them.

## Domain Definitions

- Accepted alignment values are exactly the strings `"top"`, `"middle"`, and
  `"bottom"`.
- Rejected values include unsupported strings and every non-string value,
  including string-equivalent objects, bytes, arbitrary objects, and `None`.
- Serialized `vertical_alignment` values must obey the same contract.
- Valid strings must still hydrate and render through table-dependent output
  paths.

## Fix Log

- Added `_normalize_vertical_alignment()`.
- Routed `Cell.vertical_alignment` through the normalizer.
- Added direct setter, hydration, SVG renderer, and flow-document tests.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid alignment strings | Preserve and render | PO-TCA-001 | `test_table_cell_vertical_alignment_valid_strings_hydrate_and_render` | mutation target |
| Unsupported strings | Reject and preserve previous state | PO-TCA-002 | `test_table_cell_vertical_alignment_rejects_non_string_selectors` | mutation target |
| String-equivalent non-string objects | Reject and preserve previous state | PO-TCA-003 | same | mutation target |
| Serialized non-string alignment | Reject through hydration | PO-TCA-004 | `test_table_cell_vertical_alignment_hydration_rejects_non_string_selector` | mutation target |
| Private `_vertical_alignment` mutation | Excluded from public contract | Explicit exclusion | none | out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Selector normalization is deterministic and finite. | TABLE-CELL-ALIGNMENT-P2 tests |
| Behavioral/condition | yes | The slice defines public cell alignment behavior. | Tests marked `@pytest.mark.condition("TABLE-CELL-ALIGNMENT-P2")` |
| Failure-mode | yes | Invalid direct and serialized values must fail loudly. | Rejection tests |
| Integration/live-path | yes | Alignment is consumed by table render/export paths. | SVG and flow-document live-path test |
| Contract/API compatibility | yes | Existing table serialization and cell behavior must continue passing. | Existing `test_table.py` |
| Property/fuzz | no | The accepted selector domain is finite and exhaustively named. | Not applicable |
| Mutation | yes | Type and membership guards are proof-critical. | Mutation gate recorded below |
| Security/adversarial | no | No file path, network, subprocess, SQL, template, or active-content surface changed. | Not applicable |
| Performance/resource | no | The change adds constant-time validation. | Code inspection |
| Concurrency/race | no | No shared state, background workers, locks, or temp files changed. | Not applicable |
| Golden artifact/visual | no | This slice preserves renderer reachability but does not claim pixel or byte identity. | Not applicable |
| Regression | yes | This closes non-string selector acceptance. | Rejection tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Removing the string type check must fail non-string selector tests.
- Weakening membership validation must fail unsupported-string tests.
- Bypassing the setter during hydration must fail serialized payload tests.
- Breaking the valid return path must fail valid hydration/render tests.

Current result:

- Cosmic Ray 8.4.6, scoped to the alignment normalizer and setter rows:
  602 generated work items filtered to 3 proof-critical work items; 3 killed
  and 0 survived.

## PO-TCA-001: Valid Strings Remain Live

### Claim

Valid alignment strings hydrate and remain usable by SVG and flow-document
dependent paths.

### Domain

Tables with cell vertical alignment set to one accepted string.

### Proof Method

The setter stores the string returned by `_normalize_vertical_alignment()`.
`Table.create_from_dict()` hydrates through the setter. The live-path test
hydrates a table, renders it through `TableSVG.from_table()`, and exports it
through `FlowDocument`.

### Conclusion

Supported by behavioral and dependent-path evidence; upgraded to proven for the
stated finite domain when tests and mutation pass.

## PO-TCA-002: Unsupported Strings Are Rejected

### Claim

Strings outside `"top"`, `"middle"`, and `"bottom"` raise `ValueError` and do
not alter existing cell alignment state.

### Domain

All public setter calls and serialized hydration values that are strings.

### Proof Method

`_normalize_vertical_alignment()` checks membership before returning. The
setter assigns only after the helper returns.

### Conclusion

Proven for the stated domain when tests and mutation pass.

## PO-TCA-003: Non-String Selectors Are Rejected

### Claim

No non-string object can be stored as `Cell.vertical_alignment` through the
public setter, even if it compares equal to an accepted string.

### Domain

All public setter calls with non-string values.

### Proof Method

`_normalize_vertical_alignment()` checks `isinstance(value, str)` before
performing membership. The focused test includes a string-equivalent object
that would otherwise pass set membership by equality.

### Conclusion

Proven for the stated domain when tests and mutation pass.

## PO-TCA-004: Hydration Cannot Bypass Alignment Validation

### Claim

Serialized table payloads cannot store non-string alignment values in hydrated
cells.

### Domain

Payloads passed to `Table.create_from_dict()` that include
`vertical_alignment`.

### Proof Method

`Table.create_from_dict()` assigns `cell.vertical_alignment`, so serialized
input uses the same setter and normalizer as direct public calls.

### Conclusion

Proven for the stated domain when tests and mutation pass.
