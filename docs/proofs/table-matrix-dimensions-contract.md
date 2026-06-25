# Table Matrix Dimensions Contract

This note applies the InkGen Definition of Done to the
TABLE-MATRIX-DIMENSIONS-P2 slice. It closes serialized table hydration matrix
shape boundaries so non-empty tables cannot hydrate from missing, short, or
oversized matrix payloads.

## Scope

The slice covers:

- `Table.create_from_dict()` matrix row-count validation.
- `Table.create_from_dict()` matrix column-count validation.
- Valid rectangular matrix hydration through `TableSVG` and `FlowDocument`.

## Architecture Impact

Affected surface:

- `src/InkGen/table.py`: serialized matrix dimension validation during table
  hydration.
- `tests/test_table_contract.py`: TABLE-MATRIX-DIMENSIONS-P2 behavioral and
  dependent-path tests.
- `docs/proofs/table-matrix-dimensions-contract.md`: this proof note.

Incoming dependencies:

- Saved table payloads hydrate through `Table.create_from_dict()`.
- `FlowDocument.create_from_dict()` delegates table blocks to
  `Table.create_from_dict()`.
- `TableSVG` and `FlowDocument` consume hydrated table cell content.

Outgoing dependencies:

- Matrix validation depends only on rows and columns already built from the
  serialized payload.
- Existing payload-envelope, index, style-id, alignment, merge, and autofit
  helpers remain responsible for their narrower contracts.

Before/after edge changes:

- Before this slice, missing or short matrix payloads for non-empty tables
  hydrated and silently lost cell content.
- Oversized matrix payloads failed only through incidental table index errors.
- After this slice, matrix row count must match `row_count`, and every matrix
  row length must match `column_count`.
- No dependency, renderer, or artifact flow edge was added.

Cycle/layer/coupling/redundancy result:

- Cycle check: no imports from InkGen modules were added.
- Layer check: table authoring owns its serialized payload shape contract.
- Coupling check: renderers continue to consume fully hydrated table state.
- Redundancy check: this complements, rather than duplicates, payload-envelope
  checks: envelopes prove container type; this slice proves rectangular shape.

ADR/rule impact:

- No ADR is required. This reinforces the dependency-map rule that
  `parameters` / `create_from_dict()` round trips are public contracts.

## Domain Definitions

- Generated table payloads include `rows`, `columns`, and a rectangular
  `matrix`.
- Matrix row count must equal the number of hydrated rows.
- Each matrix row length must equal the number of hydrated columns.
- Empty tables with zero rows accept an empty matrix.
- Non-empty tables with missing, short, or oversized matrix payloads are
  malformed and rejected.

## Fix Log

- Added row-count validation after matrix envelope normalization.
- Added per-row column-count validation before cell hydration.
- Added malformed missing/short/oversized matrix tests.
- Added valid rectangular matrix live-path tests through SVG and flow-document
  outputs.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Generated rectangular matrix | Preserve and hydrate | PO-TMAT-001 | `test_table_hydration_rectangular_matrix_remains_live` | mutation target |
| Missing matrix for non-empty table | Reject as row-count mismatch | PO-TMAT-002 | `test_table_hydration_rejects_mismatched_matrix_dimensions` | mutation target |
| Short matrix rows | Reject as row-count mismatch | PO-TMAT-002 | same | mutation target |
| Extra matrix rows | Reject as row-count mismatch | PO-TMAT-002 | same | mutation target |
| Short matrix row cells | Reject as column-count mismatch | PO-TMAT-003 | same | mutation target |
| Extra matrix row cells | Reject as column-count mismatch | PO-TMAT-003 | same | mutation target |
| Non-sequence matrix envelopes | Existing envelope rejection | TABLE-PAYLOAD-ENVELOPE-P2 | existing tests | out of scope here |
| Per-cell malformed content | Existing cell/style/merge/alignment contracts | existing table proof notes | existing tests | out of scope here |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Matrix shape checks are deterministic. | TABLE-MATRIX-DIMENSIONS-P2 tests |
| Behavioral/condition | yes | The slice defines serialized table matrix behavior. | Tests marked `@pytest.mark.condition("TABLE-MATRIX-DIMENSIONS-P2")` |
| Failure-mode | yes | Missing, short, and oversized matrix payloads must fail explicitly. | Rejection tests |
| Integration/live-path | yes | Hydrated tables must remain usable downstream. | SVG and flow-document live-path test |
| Contract/API compatibility | yes | `Table.parameters` round trips must remain rectangular and data-preserving. | Existing and new table round-trip tests |
| Property/fuzz | no | The matrix dimension partitions are explicitly enumerated. | Not applicable |
| Mutation | yes | Dimension guards are proof-critical. | Mutation gate recorded below |
| Security/adversarial | no | No file path, network, subprocess, SQL, template, or active-content surface changed. | Not applicable |
| Performance/resource | no | The change adds length checks over already-loaded sequences. | Code inspection |
| Concurrency/race | no | No shared state, background workers, locks, or temp files changed. | Not applicable |
| Golden artifact/visual | no | The slice preserves output-path reachability but does not claim byte identity. | Not applicable |
| Regression | yes | This closes silent cell-content loss from malformed matrices. | Rejection tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Weakening row-count validation must fail missing/short/extra row tests.
- Weakening column-count validation must fail short/extra cell tests.
- Breaking valid rectangular hydration must fail the live-path test.

Current result:

- Cosmic Ray 8.4.6, scoped to table matrix dimension validation rows: 722
  generated work items filtered to 17 proof-critical work items; 17 killed and
  0 survived.

## PO-TMAT-001: Rectangular Matrices Preserve Cell Content

### Claim

Valid rectangular serialized matrices hydrate without losing cell content and
remain usable by downstream output paths.

### Domain

Payloads generated by `Table.parameters` for tables with any row and column
count.

### Proof Method

Rows and columns are created before matrix hydration. A matrix whose dimensions
match those counts is iterated cell-by-cell, preserving paragraph content. The
live-path test verifies hydrated content through `TableSVG` and
`FlowDocument`.

### Conclusion

Supported by behavioral and dependent-path evidence; proven for the stated
shape contract when tests and mutation pass.

## PO-TMAT-002: Matrix Row Count Matches Table Rows

### Claim

`Table.create_from_dict()` rejects matrix payloads whose row count differs from
the hydrated table row count.

### Domain

All serialized table payloads after row hydration and matrix envelope
normalization.

### Proof Method

The implementation compares `len(matrix_payload)` with `table.row_count` before
iterating matrix rows.

### Conclusion

Proven for the stated domain when tests and mutation pass.

## PO-TMAT-003: Matrix Column Counts Match Table Columns

### Claim

Every matrix row must contain exactly one cell payload per hydrated table
column.

### Domain

All matrix row sequences reached after row-count validation.

### Proof Method

The implementation compares `len(row_payload)` with `table.column_count` before
iterating cell payloads.

### Conclusion

Proven for the stated domain when tests and mutation pass.
