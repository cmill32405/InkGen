# Flow Document Contract Proof Obligations

This note applies the InkGen Definition of Done to the FLOW-DOCUMENT-P1 flow
document output slice. It focuses on deterministic dependency-free DOCX output,
ordered mixed block serialization, text escaping, and validated drawing
materialization for document exports.

## Scope

The slice covers `FlowDocument` and proof-critical helpers in
`src/InkGen/document_outputs.py`.

The public behavior under review is:

- `FlowDocument.to_docx_bytes()`
- `FlowDocument.to_html()`
- `FlowDocument.to_rtf()`
- `FlowDocument.to_plain_text()`
- `FlowDocument.parameters`
- `FlowDocument.create_from_dict()`
- `FlowDocument.add_paragraph()`
- `FlowDocument.add_table()`
- `FlowDocument.add_drawing_group()`

## Architecture Impact

Affected surface:

- `src/InkGen/document_outputs.py`: DOCX package metadata, drawing
  materialization guards, and document-output helpers.
- `tests/test_flow_document_contract.py`: focused FLOW-DOCUMENT-P1 evidence.
- `tests/test_document_outputs.py`: existing document-output compatibility
  evidence.

Incoming dependencies:

- Public callers import `FlowDocument` and `DocumentOutputFormat` from
  `InkGen`.
- Word and Google Docs workflows rely on DOCX output being dependency-free and
  importable.
- Generated synthetic fixtures rely on stable DOCX/HTML/RTF/text block order.
- Drawing groups rely on neutral drawing recipes remaining the geometry source
  of truth.

Outgoing dependencies:

- Flow documents consume `Paragraph`, `Table`, and `DrawingComponentGroup`.
- DOCX output depends only on Python `zipfile`, WordprocessingML strings, and
  VML drawing fragments.
- Drawing fragments depend on neutral drawing primitives materializing to SVG or
  PDF components through `to_component()`.
- Text escaping depends on stdlib HTML and XML escaping plus local RTF escaping.

Before/after edge changes:

- Before this slice, DOCX ZIP parts used current timestamps, so repeated
  generation could produce different bytes.
- Before this slice, flow-document drawing HTML/DOCX helpers could bypass the
  neutral group materialization guard and silently omit invalid materialized
  components.
- Before the drawing-label hardening update, drawing block hydration stringified
  malformed serialized group labels instead of preserving the neutral drawing
  group contract.
- Before the block-envelope hardening update, malformed serialized block
  envelopes could fail through incidental `KeyError` or downstream type errors.
- After this slice, DOCX ZIP parts use a fixed timestamp and drawing
  materialization must return an InkGen `Component`.
- After the drawing-label hardening update, drawing block hydration passes
  serialized labels unchanged into `DrawingComponentGroup`, where non-string
  labels fail at the renderer-neutral boundary.
- After the block-envelope hardening update, block hydration first validates
  that each block is a mapping with a string `type` and mapping `payload`.
- No new dependency edge or third-party dependency was introduced.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced.
- Layer check: `document_outputs.py` still consumes paragraph/table/drawing
  abstractions and does not become a drawing renderer source of truth.
- Coupling check: the only concrete drawing dependency remains materialization
  through neutral recipes.
- Redundancy check: no duplicate paragraph, table, or primitive geometry model
  was added.

Evidence source and freshness:

- Source-backed: `document_outputs.py`, `test_document_outputs.py`,
  `docs/dependency-map.md`, public exports, and flow-document docs were read
  before editing.
- Test-backed: focused tests exercise deterministic DOCX bytes, fixed ZIP
  timestamps, output escaping, mixed block round trip, invalid drawing
  materialization failure, and exact VML polyline coordinates.
- No architecture claim in this note relies only on stale memory.

ADR/rule impact:

- No new ADR is required because the slice preserves the dependency-free output
  policy and existing flow-document dependency direction.
- A future change that adds a document-output dependency must record an ADR and
  user approval.

## Domain Definitions

- A flow document is an ordered list of `Paragraph`, `Table`, and
  `DrawingComponentGroup` blocks.
- Supported document outputs are DOCX, HTML, RTF, and plain text.
- DOCX output is a minimal WordprocessingML ZIP package.
- Repeated DOCX generation for the same document state must produce identical
  bytes.
- Drawing output must fail loudly if a neutral drawing primitive cannot
  materialize to an InkGen `Component`.

## Fix Log

- DOCX ZIP parts are now written through `_write_docx_part()` with
  `DOCX_FIXED_TIMESTAMP`.
- Flow-document drawing HTML, bounds, and VML helpers now call
  `_materialize_drawing_component()`.
- `_materialize_drawing_component()` rejects missing/non-callable materializers
  and non-`Component` materialization results.
- `_drawing_from_parameters()` now delegates serialized drawing labels to
  `DrawingComponentGroup` without stringifying malformed values.
- `_block_from_parameters()` now validates serialized block envelopes before
  dispatching to paragraph, table, or drawing hydration.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Repeated DOCX generation | Preserve exact bytes and fixed part order/timestamps | PO-FDOC-001 | `test_flow_document_docx_bytes_are_deterministic` | killed |
| Text with XML/HTML/RTF controls | Escape per target format | PO-FDOC-002 | `test_flow_document_escapes_text_across_output_formats` | behavioral evidence |
| Paragraph/table/drawing block order | Preserve through parameters and output | PO-FDOC-003 | `test_flow_document_preserves_mixed_block_order_after_round_trip` | behavioral evidence |
| Serialized block envelope and dispatch | Reject malformed envelopes and dispatch valid dynamic type strings by value | PO-FDOC-007 | `test_flow_document_hydration_rejects_malformed_block_envelopes`, `test_flow_document_hydration_dispatches_dynamic_block_type_strings` | killed |
| Malformed serialized drawing label | Reject through the neutral group label contract | PO-FDOC-006 | `test_flow_document_drawing_group_hydration_rejects_malformed_label` | behavioral evidence |
| Invalid drawing materialization | Reject before silent omission | PO-FDOC-004 | `test_flow_document_rejects_invalid_drawing_materialization` | killed |
| DOCX VML linework | Emit group-relative points | PO-FDOC-005 | `test_flow_document_docx_drawing_polyline_uses_group_relative_points` | killed |
| Unsupported block private mutation | Excluded from public contract | Explicit exclusion | Not applicable | Out of scope |
| Full WordprocessingML feature parity | Excluded from minimal dependency-free backend | Explicit exclusion | Not applicable | Out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Helpers are deterministic. | FLOW-DOCUMENT-P1 tests |
| Behavioral/condition | yes | The slice defines document-output behavior. | Tests are marked `@pytest.mark.condition("FLOW-DOCUMENT-P1")`. |
| Failure-mode | yes | Invalid content, malformed serialized block envelopes, malformed serialized drawing labels, and invalid output paths must fail loudly. | Invalid hydration, invalid materialization, and existing writer tests |
| Integration/live-path | yes | DOCX ZIP, HTML, RTF, text, table, and drawing paths cross module boundaries. | Focused and existing document-output tests |
| Contract/API compatibility | yes | Parameters and public add methods must preserve existing behavior. | Round-trip and existing rejection tests |
| Property/fuzz | no | This slice proves finite output and dispatch contracts. | Not applicable |
| Mutation | yes | Deterministic package writing and materialization guards are proof-critical. | Mutation result recorded below |
| Security/adversarial | limited | File writers touch local paths; existing tests cover missing-directory failures. | `test_flow_document_file_writers_fail_on_missing_directory` |
| Performance/resource | no | The slice adds constant-time checks and fixed metadata. | Code inspection |
| Concurrency/race | no | No shared state, workers, locks, or temp files are added. | Not applicable |
| Golden artifact/visual | yes | DOCX XML/VML output must be stable. | ZIP/XML/VML assertions |
| Regression | yes | This closes nondeterministic DOCX bytes and silent drawing omission. | Determinism and invalid-materialization tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Changing DOCX part names, payload routing, fixed timestamps, or compression
  should fail deterministic package tests.
- Weakening drawing materializer callability or return-type checks should fail
  invalid-materialization tests.
- Changing DOCX VML group-relative points should fail exact polyline tests.
- Reintroducing drawing-label stringification should fail the serialized drawing
  label hydration test.
- Weakening serialized block envelope validation or dispatch should fail the
  malformed-envelope test.

Current result:

- Cosmic Ray 8.4.6, scoped to changed DOCX package assembly, drawing
  materialization guards, and VML point rows: 34 work items, 34 killed, and 0
  survived.
- Cosmic Ray 8.4.6, scoped to serialized block-envelope validation and
  dispatch rows after the block-envelope hardening update: 32 work items, 32
  killed, and 0 survived.

## PO-FDOC-001: DOCX Bytes Are Deterministic

### Claim

Repeated `to_docx_bytes()` calls for the same document state produce identical
bytes.

### Domain

All `FlowDocument` instances whose blocks are deterministic paragraphs, tables,
and drawing groups.

### Proof Method

`to_docx_bytes()` writes parts in fixed order. `_write_docx_part()` assigns the
same ZIP timestamp and compression method to every part. The test compares two
generated payloads and inspects each part timestamp.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-FDOC-002: Text Is Escaped Per Output Format

### Claim

Text control characters are escaped in DOCX XML, HTML, and RTF outputs.

### Domain

Paragraph text and titles containing XML/HTML/RTF control characters.

### Proof Method

DOCX uses XML escaping, HTML uses HTML escaping, and RTF escapes backslashes and
braces. The focused test asserts representative control characters in all three
formats.

### Conclusion

Supported by behavioral evidence for the stated representative domain.

## PO-FDOC-003: Mixed Block Order Round-Trips

### Claim

Paragraph, table, and drawing blocks preserve document order through
`parameters` and `create_from_dict()`.

### Domain

Documents built through public add methods and recreated with required style
registries for globally unique style names.

### Proof Method

The block serializers tag each block by type in document order. The focused test
recreates a paragraph/table/drawing document and compares block classes,
parameters, and plain-text order.

### Conclusion

Proven for the stated domain after tests.

## PO-FDOC-004: Invalid Drawing Materialization Fails Loudly

### Claim

Flow-document drawing exports reject invalid neutral materialization instead of
silently omitting content.

### Domain

Drawing groups containing a primitive whose `to_component()` returns a
non-`Component` object.

### Proof Method

`_materialize_drawing_component()` validates materializer callability and
concrete return type before HTML or DOCX drawing output uses the result.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-FDOC-005: DOCX VML Points Are Group-Relative

### Claim

Linework emitted into DOCX VML uses coordinates relative to the drawing group's
minimum x/y bounds.

### Domain

Neutral drawing groups containing linework whose PDF materialization exposes
points.

### Proof Method

`_drawing_bounds()` computes group bounds from materialized PDF points.
`_component_vml()` subtracts minimum x/y from each point before writing VML
polyline points. The focused test checks exact `coordsize` and polyline
coordinates for nonzero source points.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-FDOC-006: Drawing Labels Hydrate Through Neutral Contract

### Claim

Flow-document drawing hydration preserves the `DrawingComponentGroup` label
contract and rejects malformed serialized labels instead of stringifying them.

### Domain

`FlowDocument.create_from_dict()` payloads containing drawing blocks.

### Proof Method

`_drawing_from_parameters()` passes `data["group_label"]` directly to
`DrawingComponentGroup`. The neutral group constructor validates the label
before any component hydration or output rendering occurs. The focused test
supplies a malformed serialized label and asserts the neutral group label error.

### Conclusion

Proven for the stated domain after tests.

## PO-FDOC-007: Serialized Block Envelopes Are Validated

### Claim

`FlowDocument.create_from_dict()` rejects malformed serialized block envelopes
at the flow-document boundary instead of relying on incidental downstream
errors.

### Domain

Each item in the serialized `FlowDocument.blocks` sequence.

### Proof Method

`_block_from_parameters()` first requires each block to be a mapping, then
requires both `type` and `payload`, a string `type`, and a mapping `payload`.
Only after those checks does it dispatch to paragraph, table, or drawing
hydration by string value. Focused tests cover a non-mapping block, missing
discriminator or payload, non-string discriminator, non-mapping payload,
unsupported string discriminators, and valid dynamically constructed block type
strings for all three supported block kinds.

### Counterexamples And Exclusions

Malformed payloads inside valid paragraph, table, or drawing envelopes are
delegated to the owning paragraph, table, or drawing contract.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## Current Slice Decision

The slice keeps `FlowDocument` dependency-free and minimal. It fixes byte
determinism and boundary validation without adding document libraries or
expanding the flow-document renderer into a general drawing renderer.
