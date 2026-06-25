# Table Cell Style ID Contract

This note applies the InkGen Definition of Done to the
TABLE-CELL-STYLE-ID-P2 slice. It closes the public table-cell paragraph
`style_id` boundary so only real strings or `None` can enter table state or
serialized table hydration.

## Scope

The slice covers:

- `Cell.add_paragraph()`
- `Cell._append_paragraph()`
- `_normalize_style_id()`
- `Table.create_from_dict()` when hydrating serialized cell paragraphs
- `TableSVG.from_table()` as the dependent renderer path

## Architecture Impact

Affected surface:

- `src/InkGen/table.py`: paragraph style-id validation.
- `tests/test_table_contract.py`: TABLE-CELL-STYLE-ID-P2 behavioral and
  dependent-path tests.
- `docs/proofs/table-cell-style-id-contract.md`: this proof note.

Incoming dependencies:

- Public callers set cell paragraph style IDs through `Cell.add_paragraph()`.
- Saved table payloads hydrate paragraph entries through `Table.create_from_dict()`.
- `TableSVG` reads `cell.paragraph_styles` and uses each style ID as a
  `text_styles` lookup key.

Outgoing dependencies:

- Validation depends only on Python `None` identity and string type checks.
- Rendering still depends on caller-provided `TextStyle` values for every
  referenced style ID.

Before/after edge changes:

- Before this slice, arbitrary objects could be stored as paragraph style IDs.
  A crafted object that compared equal to a provided string key could pass SVG
  style lookup despite violating the public `str | None` contract.
- After this slice, direct calls and hydration reject any non-string,
  non-`None` style ID before table state changes.
- No import, dependency, renderer, or public artifact edge was added.

Cycle/layer/coupling/redundancy result:

- Cycle check: no imports were added.
- Layer check: the table model owns style-id state validation; renderers consume
  the table contract.
- Coupling check: the validation helper is local and does not depend on SVG.
- Redundancy check: direct calls and hydration share `_append_paragraph()`.

ADR/rule impact:

- No ADR is required. This reinforces the dependency-map rule that authoring
  models own public contracts and output layers consume them.

## Domain Definitions

- Accepted style IDs are real strings or `None`.
- Rejected values include string-equivalent objects, bytes, arbitrary objects,
  numbers, and booleans.
- Serialized paragraph `style_id` values must obey the same contract.
- Valid style IDs must still hydrate and render through `TableSVG`.

## Fix Log

- Added `_normalize_style_id()`.
- Routed `Cell._append_paragraph()` through the normalizer after text validation.
- Added direct setter-path, hydration, and SVG live-path tests.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid string style ID | Preserve and render | PO-TCS-001 | `test_table_cell_paragraph_style_id_valid_values_hydrate_and_render` | mutation target |
| Valid `None` style ID | Preserve and render when caller supplies default style | PO-TCS-001 | same | mutation target |
| String-equivalent non-string objects | Reject before state change | PO-TCS-002 | `test_table_cell_paragraph_style_id_rejects_non_string_values` | mutation target |
| Serialized non-string style ID | Reject through hydration | PO-TCS-003 | `test_table_cell_paragraph_style_id_hydration_rejects_non_string_values` | mutation target |
| Missing renderer style for valid ID | Existing `TableSVG` `KeyError` contract | Existing renderer contract | existing tests | out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Style-id normalization is deterministic. | TABLE-CELL-STYLE-ID-P2 tests |
| Behavioral/condition | yes | The slice defines public cell paragraph style-id behavior. | Tests marked `@pytest.mark.condition("TABLE-CELL-STYLE-ID-P2")` |
| Failure-mode | yes | Invalid direct and serialized values must fail loudly. | Rejection tests |
| Integration/live-path | yes | Style IDs are consumed by table rendering. | SVG live-path test |
| Contract/API compatibility | yes | Existing table paragraph and serialization behavior must continue passing. | Existing `test_table.py` |
| Property/fuzz | no | The accepted selector domain is finite by type partition. | Not applicable |
| Mutation | yes | Type guard and shared hydration route are proof-critical. | Mutation gate recorded below |
| Security/adversarial | no | No file path, network, subprocess, SQL, template, or active-content surface changed. | Not applicable |
| Performance/resource | no | The change adds constant-time validation. | Code inspection |
| Concurrency/race | no | No shared state, background workers, locks, or temp files changed. | Not applicable |
| Golden artifact/visual | no | This slice preserves renderer reachability but does not claim pixel or byte identity. | Not applicable |
| Regression | yes | This closes non-string style-id acceptance. | Rejection tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Removing `None` acceptance must fail valid default-style tests.
- Removing string acceptance must fail valid styled-render tests.
- Weakening rejection must fail non-string selector tests.
- Bypassing `_append_paragraph()` validation during hydration must fail
  serialized payload tests.

Current result:

- Cosmic Ray 8.4.6, scoped to the style-id normalizer and append-path rows:
  616 generated work items filtered to 6 proof-critical work items; 6 killed
  and 0 survived. Signature-separator mutations on the private helper were
  excluded as outside the public style-id proof obligation.

## PO-TCS-001: Valid Style IDs Remain Live

### Claim

Valid string and `None` style IDs hydrate and remain usable by `TableSVG`.

### Domain

Tables with cell paragraph style IDs set to a real string or `None`, with a
matching `TextStyle` supplied to `TableSVG` for each referenced key.

### Proof Method

`_append_paragraph()` stores the value returned by `_normalize_style_id()`.
`Table.create_from_dict()` hydrates paragraphs through `_append_paragraph()`.
The live-path test hydrates a table and renders it through `TableSVG.from_table()`.

### Conclusion

Supported by behavioral and dependent-path evidence; upgraded to proven for the
stated type-partitioned domain when tests and mutation pass.

## PO-TCS-002: Non-String Style IDs Are Rejected

### Claim

No non-string, non-`None` value can be stored as a cell paragraph style ID
through the public paragraph path.

### Domain

All public `Cell.add_paragraph()` calls with non-string, non-`None` style IDs.

### Proof Method

`_append_paragraph()` calls `_normalize_style_id()` before appending text or
style state. The focused test verifies state preservation after rejected values,
including a string-equivalent object.

### Conclusion

Proven for the stated domain when tests and mutation pass.

## PO-TCS-003: Hydration Cannot Bypass Style-ID Validation

### Claim

Serialized table payloads cannot store non-string style IDs in hydrated cells.

### Domain

Payloads passed to `Table.create_from_dict()` with paragraph `style_id` values.

### Proof Method

`Table.create_from_dict()` delegates paragraph insertion to `_append_paragraph()`,
so serialized input uses the same normalizer as direct public calls.

### Conclusion

Proven for the stated domain when tests and mutation pass.
