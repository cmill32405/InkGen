# Table Contract Proof Obligations

This note applies the InkGen Definition of Done to the TABLE-P1 table model
slice. It focuses on finite numeric geometry, shared padding validation, table
serialization hydration, and live use through SVG and flow-document output.

## Scope

The slice covers:

- `Table.__init__()`
- `Table.position`
- `Table.cell_padding`
- `Table.add_row()`
- `Table.add_column()`
- `Table.create_from_dict()`
- `Row.__init__()` and `Row.height`
- `Column.__init__()` and `Column.width`
- `TableSVG._normalize_padding()`

## Architecture Impact

Affected surface:

- `src/InkGen/table.py`: table origin, row height, column width, and padding
  validation.
- `src/InkGen/svg_generator.py`: `TableSVG` padding now delegates to the table
  model contract.
- `tests/test_table_contract.py`: TABLE-P1 behavioral and live-path tests.
- `tests/mutation/table_contract_cosmic_ray.toml`: scoped mutation gate.

Incoming dependencies:

- Public callers import `Table` and `AutoFitRule` from `InkGen`.
- `TableSVG` renders table geometry into rectangles and text.
- `FlowDocument` consumes tables for DOCX, HTML, RTF, and plain-text output.
- Saved parameters hydrate tables through `Table.create_from_dict()`.
- Synthetic drawing and document fixtures rely on finite table geometry.

Outgoing dependencies:

- Table validation depends only on Python `math.isfinite()`.
- `TableSVG` depends on `Table`, `RectangleSVG`, `TextSVG`, `DrawingStyle`,
  and `TextStyle`.
- `FlowDocument` depends on the public `Table` API and does not own table
  validation.

Before/after edge changes:

- Before this slice, table positions, padding, row heights, and column widths
  could accept `nan`, `inf`, booleans, and some negative values at construction
  or hydration boundaries.
- After this slice, table origins must be finite numeric coordinates; row
  heights, column widths, and padding must be finite non-negative numbers.
- Negative table origins remain valid because drawings may intentionally place
  content outside the visible origin.
- No new third-party dependency or dependency edge was introduced.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced.
- Layer check: validation remains in the table model; renderers consume the
  shared table contract.
- Coupling check: `TableSVG` delegates padding validation instead of duplicating
  it.
- Redundancy check: row/column constructors and setters share the same finite
  numeric helper.

ADR/rule impact:

- No new ADR is required. This reinforces the existing dependency-map rule that
  authoring models own their contracts and output layers consume them.

## Domain Definitions

- A table origin is exactly two finite numeric values.
- A row height is a finite numeric value greater than or equal to zero.
- A column width is a finite numeric value greater than or equal to zero.
- Cell padding is either one finite non-negative numeric value or four finite
  non-negative numeric values ordered as top, right, bottom, left.
- Booleans are not numeric table geometry values.
- A valid table must still render through `TableSVG` and flow-document output.

## Fix Log

- Added finite numeric table position normalization.
- Added shared finite numeric coercion for table dimensions.
- Hardened padding normalization against negative, non-finite, and boolean
  values.
- Routed `TableSVG` padding through `Table._normalize_padding()`.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid table geometry | Preserve origin, row height, column width, and cell content | PO-TABLE-001 | `test_table_svg_and_flow_document_use_valid_table_contract` | mutation target |
| Invalid origins | Reject malformed, boolean, and non-finite coordinates | PO-TABLE-002 | `test_table_rejects_nonfinite_and_boolean_positions` | mutation target |
| Invalid row/column dimensions | Reject negative, boolean, and non-finite dimensions at add/set boundaries | PO-TABLE-003 | `test_table_rejects_invalid_row_column_dimensions` | mutation target |
| Invalid padding | Reject negative, boolean, and non-finite padding in model and SVG renderer | PO-TABLE-004 | `test_table_padding_validation_is_shared_by_model_and_svg_renderer` | mutation target |
| Invalid hydrated parameters | Reject invalid serialized geometry during `create_from_dict()` | PO-TABLE-005 | `test_table_parameters_reject_invalid_hydrated_geometry` | mutation target |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Numeric normalization is deterministic. | TABLE-P1 tests |
| Behavioral/condition | yes | TABLE-P1 defines public table model behavior. | Tests are marked `@pytest.mark.condition("TABLE-P1")`. |
| Failure-mode | yes | Invalid numeric boundaries must fail before rendering/export. | Invalid position, dimension, padding, and hydration tests |
| Integration/live-path | yes | Tables render through SVG and flow-document output. | Live path test |
| Contract/API compatibility | yes | Existing row/column/cell matrix and serialization tests must continue passing. | Existing `test_table.py` |
| Property/fuzz | no | This slice covers finite scalar partitions directly. | Not applicable |
| Mutation | yes | Numeric guards are proof-critical. | Mutation result recorded below |
| Security/adversarial | no | No file path, network, subprocess, auth, SQL, template, or active-content surface is added. | Not applicable |
| Performance/resource | no | The change adds constant-time validation. | Code inspection |
| Concurrency/race | no | No shared state, background workers, locks, or temp files are added. | Not applicable |
| Golden artifact/visual | yes | SVG rectangle/text geometry must stay stable. | Exact component assertions |
| Regression | yes | This closes invalid geometry leaking into render/export paths. | TABLE-P1 tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Removing finite checks must fail invalid-boundary tests.
- Allowing negative row/column/padding values must fail failure-mode tests.
- Replacing the `TableSVG` delegation must fail shared-padding tests.
- Changing valid row/column geometry must fail live SVG assertions.

Current result:

- Cosmic Ray 8.4.6, scoped to executable TABLE-P1 validation and renderer
  delegation rows: 47 work items, 47 killed, and 0 survived. Type-annotation
  union mutations and a keyword-only signature marker mutation were excluded as
  non-executable equivalents.
- Valid-table live path gate, scoped to current table geometry, SVG component
  emission, flow-document table dispatch, DOCX width conversion, and concrete
  table serializers: 365 work items, 364 killed, and 1 documented equivalent
  survivor. The survivor changes the empty-table fast-return guard from
  `not row_count or not column_count` to `not row_count and not column_count`;
  it is outside the valid 2x2 table domain for PO-TABLE-001.

## PO-TABLE-001: Valid Tables Remain Live

### Claim

Valid table geometry renders to SVG components and exports through
`FlowDocument`.

### Domain

Finite table origin, non-negative row heights and column widths, valid padding,
and paragraph text with registered text styles.

### Proof Method

`TableSVG.from_table()` builds rectangle and text components from a 2x2 table,
`Table.cell_bounds()` preserves row and column offsets, `FlowDocument`
round-trips serialized table blocks, and table content emits through plain text,
Markdown, HTML, RTF, and DOCX paths.

### Conclusion

Proven when tests and mutation pass for the stated domain.

## PO-TABLE-002: Table Origins Are Finite Numeric Coordinates

### Claim

Table positions reject malformed shape, booleans, and non-finite values.

### Domain

All table construction and setter calls using public `position`.

### Proof Method

`_normalize_position()` unpacks exactly two values and calls
`_coerce_finite_float()` for each coordinate. The focused test exercises
construction, setter failure, and a valid negative coordinate.

### Conclusion

Proven when tests and mutation pass for the stated domain.

## PO-TABLE-003: Row And Column Dimensions Are Finite Non-Negative Numbers

### Claim

Rows and columns cannot be constructed or updated with negative, boolean, or
non-finite dimensions.

### Domain

`Table.add_row()`, `Table.add_column()`, `Row.height`, `Column.width`, and
serialized hydration through those paths.

### Proof Method

Constructors and setters share `_coerce_finite_float(..., allow_negative=False)`.
Existing and focused tests exercise valid zero/positive dimensions and invalid
boundaries.

### Conclusion

Proven when tests and mutation pass for the stated domain.

## PO-TABLE-004: Padding Validation Is Shared

### Claim

The table model and SVG renderer enforce the same padding contract.

### Domain

Scalar and four-value padding supplied through `Table.cell_padding`, module
normalization, table hydration, and `TableSVG.from_table()`.

### Proof Method

`TableSVG._normalize_padding()` delegates to `Table._normalize_padding()`, which
delegates to the module helper and finite coercion logic.

### Conclusion

Proven when tests and mutation pass for the stated domain.

## PO-TABLE-005: Hydration Cannot Bypass Geometry Validation

### Claim

Serialized table payloads cannot reintroduce invalid width or padding values.

### Domain

`Table.create_from_dict()` payloads containing invalid column widths or padding.

### Proof Method

Hydration uses `Table.add_column()` and `Table.cell_padding`, so the same
validation boundaries apply to serialized input.

### Conclusion

Proven when tests and mutation pass for the stated domain.
