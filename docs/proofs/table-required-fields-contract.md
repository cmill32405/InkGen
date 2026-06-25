# Table Required Fields Contract

This note applies the InkGen Definition of Done to the
TABLE-REQUIRED-FIELDS-P2 slice. It closes serialized table hydration required
field boundaries so malformed payloads fail explicitly before raw `KeyError`
lookups.

## Scope

The slice covers required fields in:

- `Table.create_from_dict()` root payloads: `position`, `auto_fit`
- column payloads: `width`, `width_rule`
- row payloads: `height`, `height_rule`
- paragraph payloads: `text`
- `_required_payload_field()`

Optional existing fields remain optional: `padding`, `merged`, `merge_start`,
`merge_end`, `vertical_alignment`, paragraph `style_id`, and empty collection
defaults where previous proof notes define them.

## Architecture Impact

Affected surface:

- `src/InkGen/table.py`: required-field validation during table hydration.
- `tests/test_table_contract.py`: TABLE-REQUIRED-FIELDS-P2 behavioral and
  dependent-path tests.
- `docs/proofs/table-required-fields-contract.md`: this proof note.

Incoming dependencies:

- Saved table payloads hydrate through `Table.create_from_dict()`.
- `FlowDocument.create_from_dict()` delegates table blocks to
  `Table.create_from_dict()`.
- `TableSVG` and `FlowDocument` consume valid hydrated table content.

Outgoing dependencies:

- Required-field validation depends only on mapping membership and existing
  downstream validators for value type/range checks.
- Existing geometry, bool, enum, style-id, alignment, merge, envelope, index,
  and matrix-dimension helpers retain their narrower responsibilities.

Before/after edge changes:

- Before this slice, missing required table fields raised raw `KeyError`.
- After this slice, missing required fields raise explicit `ValueError`
  messages naming the owner and missing field.
- No dependency, renderer, or artifact flow edge was added.

Cycle/layer/coupling/redundancy result:

- Cycle check: no imports from InkGen modules were added.
- Layer check: table authoring owns its serialized payload contract.
- Coupling check: renderers continue to consume valid table state.
- Redundancy check: all missing-field checks share one helper.

ADR/rule impact:

- No ADR is required. This reinforces the dependency-map rule that
  `parameters` / `create_from_dict()` round trips are public contracts.

## Domain Definitions

- Required fields are those emitted by `Table.parameters` and needed to
  reconstruct table geometry, autofit behavior, row/column rules, and paragraph
  text.
- Missing required fields are rejected before constructors, setters, or
  downstream validators run.
- Optional fields retain their existing defaults.
- Valid generated payloads must continue to hydrate and remain usable through
  SVG and flow-document output paths.

## Fix Log

- Added `_required_payload_field()`.
- Routed required root, row, column, and paragraph field reads through the
  helper.
- Added missing-field rejection tests for every scoped required field.
- Added valid round-trip and downstream live-path tests.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid generated payload | Preserve and hydrate | PO-TRF-001 | `test_table_hydration_required_fields_preserve_valid_round_trip` | mutation target |
| Missing root `position` | Reject explicitly | PO-TRF-002 | missing-field test | mutation target |
| Missing root `auto_fit` | Reject explicitly | PO-TRF-002 | missing-field test | mutation target |
| Missing column `width` | Reject explicitly | PO-TRF-002 | missing-field test | mutation target |
| Missing column `width_rule` | Reject explicitly | PO-TRF-002 | missing-field test | mutation target |
| Missing row `height` | Reject explicitly | PO-TRF-002 | missing-field test | mutation target |
| Missing row `height_rule` | Reject explicitly | PO-TRF-002 | missing-field test | mutation target |
| Missing paragraph `text` | Reject explicitly | PO-TRF-002 | missing-field test | mutation target |
| Optional fields omitted | Preserve existing defaults | existing contracts | existing merge/alignment/payload tests | out of scope here |
| Malformed field values | Delegate to existing validators | existing table proof notes | existing tests | out of scope here |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Required-field lookup is deterministic. | TABLE-REQUIRED-FIELDS-P2 tests |
| Behavioral/condition | yes | The slice defines serialized table required-field behavior. | Tests marked `@pytest.mark.condition("TABLE-REQUIRED-FIELDS-P2")` |
| Failure-mode | yes | Missing required fields must fail explicitly. | Missing-field rejection tests |
| Integration/live-path | yes | Valid hydrated payloads must remain usable downstream. | SVG and flow-document live-path test |
| Contract/API compatibility | yes | Valid `Table.parameters` round trips must remain stable. | Existing and new table round-trip tests |
| Property/fuzz | no | Required field partitions are finite and enumerated. | Not applicable |
| Mutation | yes | Required-field guards are proof-critical. | Mutation gate recorded below |
| Security/adversarial | no | No file path, network, subprocess, SQL, template, or active-content surface changed. | Not applicable |
| Performance/resource | no | The change adds constant-time membership checks. | Code inspection |
| Concurrency/race | no | No shared state, background workers, locks, or temp files changed. | Not applicable |
| Golden artifact/visual | no | The slice preserves output-path reachability but does not claim byte identity. | Not applicable |
| Regression | yes | This closes raw `KeyError` failures for malformed payloads. | Missing-field tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Weakening `_required_payload_field()` must fail missing-field tests.
- Bypassing required-field reads in `Table.create_from_dict()` must fail
  missing-field tests.
- Breaking valid required-field reads must fail round-trip and live-path tests.

Current result:

- Cosmic Ray 8.4.6, scoped to the required-field helper row: 734 generated work
  items filtered to 1 proof-critical work item; 1 killed and 0 survived. The
  field-name call sites are constants and are covered by condition tests rather
  than operator-level mutations.

## PO-TRF-001: Valid Required Fields Preserve Round Trip

### Claim

Payloads generated by `Table.parameters` hydrate without behavior changes and
remain usable by SVG and flow-document output paths.

### Domain

Generated table payloads with all required fields present.

### Proof Method

The live-path test hydrates a valid payload, checks table state and cell text,
then renders through `TableSVG` and `FlowDocument`.

### Conclusion

Supported by behavioral and dependent-path evidence; proven for the stated
required-field domain when tests and mutation pass.

## PO-TRF-002: Missing Required Fields Fail Explicitly

### Claim

Every scoped required field is checked before direct mapping lookup can raise a
raw `KeyError`.

### Domain

All table root, column, row, and paragraph payload mappings reached during
`Table.create_from_dict()`.

### Proof Method

`Table.create_from_dict()` reads each scoped required field through
`_required_payload_field()`, which checks membership and raises `ValueError`
with the owner and field name before returning the value.

### Conclusion

Proven for the stated domain when tests and mutation pass.
