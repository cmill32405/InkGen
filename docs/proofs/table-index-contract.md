# Table Index Contract

This note applies the InkGen Definition of Done to the TABLE-INDEX-P2 slice. It
closes public table index boundaries so booleans and non-integer values cannot
be accepted through Python list-index coercion.

## Scope

The slice covers:

- `Table.add_row(location=...)`
- `Table.add_column(location=...)`
- `Table.cell()`
- `Table.row_cells()`
- `Table.column_cells()`
- `Table.cell_bounds()`
- `Row.column()`
- `Column.row()`
- `Cell.paragraph()`
- `Cell.remove_paragraph()`
- `_normalize_public_index()`

## Architecture Impact

Affected surface:

- `src/InkGen/table.py`: public index validation for table, row, column, and
  cell accessors.
- `tests/test_table_contract.py`: TABLE-INDEX-P2 behavioral and dependent-path
  tests.
- `docs/proofs/table-index-contract.md`: this proof note.

Incoming dependencies:

- Public callers use table indexes to add rows and columns, read cells, and
  manipulate cell paragraphs.
- `TableSVG` calls `Table.cell_bounds()` and `Table.cell()` while materializing
  table geometry.
- `FlowDocument` table exporters call `Table.cell()` while emitting DOCX, HTML,
  RTF, and plain text.
- Existing examples and docs use valid zero-based integer indexes.

Outgoing dependencies:

- Index validation depends only on Python integer type checks and the current
  in-memory table dimensions.
- Existing row, column, cell, serialization, and rendering contracts remain
  unchanged.

Before/after edge changes:

- Before this slice, boolean indexes such as `True` and `False` were accepted as
  `1` and `0` by public accessors when in range.
- Negative indexes could select from the end of Python lists even though the
  documented contract is zero-based public indexing.
- After this slice, public indexes must be non-bool integers inside the stated
  bounds. Insert locations may also equal the collection length.
- No dependency, renderer, or artifact flow edge was added.

Cycle/layer/coupling/redundancy result:

- Cycle check: no imports from InkGen modules were added.
- Layer check: the table authoring model owns its public index contract.
- Coupling check: renderers continue to consume table APIs without knowing the
  validation details.
- Redundancy check: all touched public index paths share one helper.

ADR/rule impact:

- No ADR is required. This reinforces the dependency-map rule that authoring
  models own their public contracts and renderers consume those contracts.

## Domain Definitions

- Public table indexes are zero-based, non-bool integers.
- Access indexes must satisfy `0 <= index < len(collection)`.
- Insert locations must be `None` or satisfy `0 <= location <= len(collection)`.
- Boolean values are invalid even though `bool` is a subclass of `int`.
- Non-integer values are invalid.
- Valid integer indexes must keep working through public API and downstream
  output paths.

## Fix Log

- Added `_normalize_public_index()`.
- Routed table cell access, row access, column access, cell bounds, insert
  locations, row/column wrapper access, and paragraph access/removal through
  the helper.
- Added invalid bool/non-integer, out-of-range, valid-integer, and downstream
  SVG/flow-document tests.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid access indexes | Preserve zero-based access | PO-TIDX-001 | `test_table_public_access_indexes_reject_bool_and_non_integer_values` | mutation target |
| Valid insert locations | Preserve insertion at start/end | PO-TIDX-002 | `test_table_insert_locations_reject_bool_and_non_integer_values` | mutation target |
| Boolean indexes | Reject with `TypeError` | PO-TIDX-003 | all rejection tests | mutation target |
| Non-integer indexes | Reject with `TypeError` | PO-TIDX-003 | all rejection tests | mutation target |
| Negative indexes | Reject with `IndexError` | PO-TIDX-004 | access and paragraph tests | mutation target |
| Too-large indexes | Reject with `IndexError` | PO-TIDX-004 | access and paragraph tests | mutation target |
| Valid downstream output | Preserve renderer/document behavior | PO-TIDX-005 | SVG and flow-document live-path test | mutation target |
| Private mutation of index fields | Excluded | none | none | out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Index normalization is deterministic. | TABLE-INDEX-P2 tests |
| Behavioral/condition | yes | The slice defines public table index behavior. | Tests marked `@pytest.mark.condition("TABLE-INDEX-P2")` |
| Failure-mode | yes | Bool, non-integer, and out-of-range indexes must fail at the boundary. | Rejection tests |
| Integration/live-path | yes | Renderers and document outputs consume table indexes. | SVG and flow-document live-path test |
| Contract/API compatibility | yes | Existing valid integer indexing must continue to work. | Existing `test_table.py` plus valid-index assertions |
| Property/fuzz | no | The meaningful index partitions are finite and explicitly enumerated. | Not applicable |
| Mutation | yes | Type and bounds checks are proof-critical. | Mutation gate recorded below |
| Security/adversarial | no | No file path, network, subprocess, SQL, template, or active-content surface changed. | Not applicable |
| Performance/resource | no | The change adds constant-time validation per public call. | Code inspection |
| Concurrency/race | no | No shared state, background workers, locks, or temp files changed. | Not applicable |
| Golden artifact/visual | no | The slice preserves output-path reachability but does not claim byte identity. | Not applicable |
| Regression | yes | This closes Python bool/list-index coercion at public boundaries. | TABLE-INDEX-P2 tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Weakening the bool/type check must fail invalid index tests.
- Weakening lower or upper bounds must fail out-of-range tests.
- Changing accessors to bypass `_normalize_public_index()` must fail rejection
  tests.
- Breaking valid integer access must fail existing table and dependent-path
  tests.

Current result:

- Cosmic Ray 8.4.6, scoped to table public index validation and dependent
  `cell_bounds()` rows: 706 generated work items filtered to 65 proof-critical
  work items; 65 killed and 0 survived. Signature/type-annotation operator
  noise was excluded from this index proof obligation.

## PO-TIDX-001: Valid Access Indexes Are Preserved

### Claim

Valid zero-based integer access indexes select the same cells and bounds as the
previous valid public behavior.

### Domain

`Table.cell()`, `Table.row_cells()`, `Table.column_cells()`,
`Table.cell_bounds()`, `Row.column()`, `Column.row()`, and `Cell.paragraph()`
when indexes are non-bool integers inside collection bounds.

### Proof Method

Accessors route through `_normalize_public_index()`, which returns the original
integer unchanged when it is inside bounds. The public methods then use that
same integer for the underlying list lookup.

### Conclusion

Proven for the stated in-memory domain when tests and mutation pass.

## PO-TIDX-002: Valid Insert Locations Are Preserved

### Claim

Valid row and column insert locations still insert at the requested zero-based
position, while `None` still means append.

### Domain

`Table.add_row(location=...)` and `Table.add_column(location=...)` for
`None` and non-bool integer locations where `0 <= location <= len(collection)`.

### Proof Method

`_validate_insert_index()` preserves `None` as append and delegates explicit
locations to `_normalize_public_index(..., allow_end=True)`.

### Conclusion

Proven for the stated domain when tests and mutation pass.

## PO-TIDX-003: Bool And Non-Integer Indexes Are Rejected

### Claim

Every public index boundary rejects booleans and non-integer values before
Python list indexing can coerce or reinterpret them.

### Domain

All public methods listed in the scope section.

### Proof Method

All scoped public methods call `_normalize_public_index()` before list access or
insertion. The helper rejects `bool` before the `int` check and rejects all
non-integers.

### Conclusion

Proven for the stated domain when tests and mutation pass.

## PO-TIDX-004: Out-Of-Range Indexes Are Rejected

### Claim

Negative and too-large access indexes fail with `IndexError`; too-large insert
locations also fail with `IndexError`.

### Domain

All scoped public index methods.

### Proof Method

`_normalize_public_index()` uses an explicit `0 <= value <= limit` check before
any list operation. Access limits are `len(collection) - 1`; insert limits are
`len(collection)`.

### Conclusion

Proven for the stated domain when tests and mutation pass.

## PO-TIDX-005: Downstream Table Output Paths Remain Live

### Claim

Valid integer table indexes remain compatible with SVG and flow-document output
paths.

### Domain

Tables built through the public API with valid integer indexes.

### Proof Method

The live-path test materializes a valid table through `TableSVG.from_table()`
and `FlowDocument.to_plain_text()`.

### Conclusion

Supported by behavioral and dependent-path evidence; proven for the stated
index contract when tests and mutation pass.
