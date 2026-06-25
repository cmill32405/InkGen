# Table Payload Envelope Contract

This note applies the InkGen Definition of Done to the
TABLE-PAYLOAD-ENVELOPE-P2 slice. It closes serialized table hydration envelope
boundaries so malformed roots and nested row, column, matrix, cell, and
paragraph containers fail explicitly before incidental indexing errors.

## Scope

The slice covers:

- `Table.create_from_dict()` root and nested payload dispatch
- `_normalize_payload_mapping()`
- `_normalize_payload_sequence()`
- Valid table hydration through `TableSVG` and `FlowDocument`

## Architecture Impact

Affected surface:

- `src/InkGen/table.py`: serialized table payload envelope validation.
- `tests/test_table_contract.py`: TABLE-PAYLOAD-ENVELOPE-P2 behavioral and
  dependent-path tests.
- `docs/proofs/table-payload-envelope-contract.md`: this proof note.

Incoming dependencies:

- Saved table payloads hydrate through `Table.create_from_dict()`.
- `FlowDocument.create_from_dict()` delegates table blocks to
  `Table.create_from_dict()`.
- `TableSVG` consumes hydrated table geometry and cell text.

Outgoing dependencies:

- Envelope validation depends only on `collections.abc.Mapping` and
  `collections.abc.Sequence`.
- Existing table field validation remains delegated to the established numeric,
  bool, enum, style-id, alignment, and merge-state helpers.

Before/after edge changes:

- Before this slice, malformed roots and nested containers could be indexed as
  strings, lists, or arbitrary objects, producing incidental exceptions.
- After this slice, table payload roots and payload entries must be mappings,
  and collection fields must be non-string sequences.
- No renderer, dependency, or artifact flow edge was added.

Cycle/layer/coupling/redundancy result:

- Cycle check: no imports from InkGen modules were added.
- Layer check: table authoring owns its serialized payload contract.
- Coupling check: envelope validation is independent of SVG/PDF/document output.
- Redundancy check: root and nested mapping/sequence checks share two helpers.

ADR/rule impact:

- No ADR is required. This reinforces the dependency-map rule that
  `parameters` / `create_from_dict()` round trips are public contracts.

## Domain Definitions

- Table root payloads must be mappings, either direct table payloads or
  `{"Table": <mapping>}` wrappers.
- `rows`, `columns`, `matrix`, and `paragraphs` fields must be sequences when
  present, but strings and bytes are rejected.
- Row, column, cell, and paragraph entries must be mappings.
- Valid table payloads must still hydrate and remain usable by SVG and
  flow-document output paths.

## Fix Log

- Added `_normalize_payload_mapping()`.
- Added `_normalize_payload_sequence()`.
- Routed `Table.create_from_dict()` root, row, column, matrix, cell, and
  paragraph envelopes through the helpers.
- Added malformed root, malformed nested collection, and valid live-path tests.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Direct/wrapped mapping root | Preserve and hydrate | PO-TPE-001 | `test_table_hydration_valid_envelopes_remain_live` | mutation target |
| Non-mapping root/wrapped payload | Reject before field lookup | PO-TPE-002 | `test_table_hydration_rejects_malformed_root_payloads` | mutation target |
| String collection fields | Reject as malformed sequence envelopes | PO-TPE-003 | `test_table_hydration_rejects_malformed_collection_envelopes` | mutation target |
| Non-mapping row/column/cell/paragraph entries | Reject before item lookup | PO-TPE-004 | same | mutation target |
| Valid nested envelopes | Hydrate and remain live | PO-TPE-001 | live-path test | mutation target |
| Required field absence | Existing KeyError contract | Existing tests/legacy behavior | none | out of scope for this slice |
| Matrix dimension mismatch | Existing IndexError contract | Existing behavior | none | out of scope for this slice |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Mapping and sequence checks are deterministic. | TABLE-PAYLOAD-ENVELOPE-P2 tests |
| Behavioral/condition | yes | The slice defines serialized table envelope behavior. | Tests marked `@pytest.mark.condition("TABLE-PAYLOAD-ENVELOPE-P2")` |
| Failure-mode | yes | Malformed roots and nested envelopes must fail explicitly. | Rejection tests |
| Integration/live-path | yes | Hydrated valid payloads must remain usable downstream. | SVG and flow-document live-path test |
| Contract/API compatibility | yes | Existing table round-trip and renderer tests must continue passing. | Existing `test_table.py` |
| Property/fuzz | no | The covered envelope partitions are explicitly enumerated. | Not applicable |
| Mutation | yes | Type and dispatch checks are proof-critical. | Mutation gate recorded below |
| Security/adversarial | no | No file path, network, subprocess, SQL, template, or active-content surface changed. | Not applicable |
| Performance/resource | no | The change adds constant-time validation per payload envelope. | Code inspection |
| Concurrency/race | no | No shared state, background workers, locks, or temp files changed. | Not applicable |
| Golden artifact/visual | no | This slice preserves renderer reachability but does not claim pixel or byte identity. | Not applicable |
| Regression | yes | This closes incidental malformed payload indexing. | Rejection tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Weakening mapping checks must fail malformed root and nested mapping tests.
- Weakening sequence checks must fail malformed collection tests.
- Bypassing helper calls in hydration must fail rejection tests.
- Breaking valid hydration must fail the live-path test.

Current result:

- Cosmic Ray 8.4.6, scoped to table payload envelope helper and hydration rows:
  711 generated work items filtered to 11 proof-critical work items; 11 killed
  and 0 survived. Signature-separator helper mutations and an equivalent
  `_autofit_suppressed` mutation were excluded from this envelope proof
  obligation.

## PO-TPE-001: Valid Envelopes Remain Live

### Claim

Valid serialized table payload envelopes hydrate and remain usable by SVG and
flow-document output paths.

### Domain

Direct or wrapped table payload mappings generated from `Table.parameters`.

### Proof Method

The live-path test hydrates a valid payload, checks cell text, renders through
`TableSVG.from_table()`, and exports through `FlowDocument`.

### Conclusion

Supported by behavioral and dependent-path evidence; upgraded to proven for the
stated envelope domain when tests and mutation pass.

## PO-TPE-002: Root Payloads Are Mappings

### Claim

`Table.create_from_dict()` rejects non-mapping root payloads and non-mapping
`Table` wrapper payloads before field lookup.

### Domain

All values passed to `Table.create_from_dict()`.

### Proof Method

Hydration routes the root and wrapper payload through
`_normalize_payload_mapping()` before reading required fields.

### Conclusion

Proven for the stated domain when tests and mutation pass.

## PO-TPE-003: Collection Fields Are Non-String Sequences

### Claim

`rows`, `columns`, `matrix`, and `paragraphs` fields reject strings, bytes, and
non-sequence values.

### Domain

Serialized table payload collection fields when present.

### Proof Method

Hydration routes each collection field through `_normalize_payload_sequence()`,
which rejects strings/bytes before checking `Sequence`.

### Conclusion

Proven for the stated domain when tests and mutation pass.

## PO-TPE-004: Nested Entries Are Mappings

### Claim

Row, column, cell, and paragraph payload entries must be mappings before field
lookup.

### Domain

All nested row, column, cell, and paragraph entries reached during table
hydration.

### Proof Method

Hydration routes each entry through `_normalize_payload_mapping()` before
reading fields such as `width`, `height`, `paragraphs`, or `text`.

### Conclusion

Proven for the stated domain when tests and mutation pass.
