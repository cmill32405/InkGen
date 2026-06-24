# Flow Document Title Contract

This note applies the InkGen Definition of Done to the
FLOW-DOCUMENT-TITLE-P2 flow-document title slice. It closes the public boundary
where direct construction accepted arbitrary objects and hydration silently
stringified malformed serialized titles.

## Scope

The slice covers:

- `FlowDocument.__init__()`
- `FlowDocument.parameters`
- `FlowDocument.create_from_dict()`
- `FlowDocument.to_html()`
- `FlowDocument.to_rtf()`
- `_normalize_title()`

## Architecture Impact

Affected surface:

- `src/InkGen/document_outputs.py`: title normalization at construction and
  hydration.
- `tests/test_flow_document_contract.py`: focused FLOW-DOCUMENT-TITLE-P2 tests.
- `tests/test_document_outputs.py`: existing flow-document compatibility tests.

Incoming dependencies:

- Public callers import `FlowDocument` from `InkGen`.
- Word and Google Docs workflows rely on valid DOCX/HTML/RTF title strings.
- Serialized flow-document payloads hydrate through `FlowDocument.create_from_dict()`.

Outgoing dependencies:

- HTML titles depend on stdlib HTML escaping.
- DOCX titles are embedded through paragraph/run XML paths where applicable.
- RTF titles depend on local `_rtf_escape()`.
- Block serialization remains delegated to paragraph, table, and drawing-group
  contracts.

Before/after edge changes:

- Before this slice, `FlowDocument(title=object())` stored an object and failed
  later during output escaping; hydration used `str(...)`, hiding malformed
  serialized titles.
- After this slice, title validation happens at the public boundary and
  hydration uses the same constructor path.
- No dependency direction changed and no third-party dependency was introduced.

Cycle/layer/coupling/redundancy result:

- Cycle check: no imports were added.
- Layer check: flow-document validation remains in the flow-document model.
- Coupling check: title validation does not affect paragraph/table/drawing
  block ownership.
- Redundancy check: constructor and hydration share one local helper.

Evidence source and freshness:

- Source-backed: `document_outputs.py`, flow-document tests, flow-document
  proof note, dependency map, and document-output docs were read before editing.
- Test-backed: focused tests cover non-string rejection, default-title
  preservation, hydration rejection, valid title round trip, and escaped output.

ADR/rule impact:

- No new ADR is required because this is a public data-boundary hardening
  change with no architecture decision change.

## Domain Definitions

- Accepted title values are strings, `None`, and the empty string.
- `None` and the empty string preserve the existing default title
  `"InkGen Document"`.
- Non-string values are rejected at construction and hydration.
- Valid title strings round-trip through `parameters` and are escaped by output
  formats.

## Fix Log

- Added `_normalize_title()`.
- Routed `FlowDocument.__init__()` and `create_from_dict()` through the helper.
- Added constructor, default, hydration, and valid-output tests.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid string title | Preserve and escape in outputs | PO-FDT-001 | `test_flow_document_valid_title_round_trips_and_escapes` | mutation target |
| `None` title | Preserve existing default | PO-FDT-002 | `test_flow_document_default_title_is_preserved` | mutation target |
| Empty title | Preserve existing default | PO-FDT-002 | same | mutation target |
| Non-string constructor title | Reject before output generation | PO-FDT-003 | `test_flow_document_rejects_non_string_titles` | mutation target |
| Non-string serialized title | Reject through hydration | PO-FDT-004 | `test_flow_document_title_hydration_rejects_malformed_title` | mutation target |
| Private title mutation after construction | Excluded from public contract | Explicit exclusion | none | out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Title normalization is deterministic. | FLOW-DOCUMENT-TITLE-P2 tests |
| Behavioral/condition | yes | The slice defines public title behavior. | Tests marked `@pytest.mark.condition("FLOW-DOCUMENT-TITLE-P2")` |
| Failure-mode | yes | Malformed constructor and serialized values must fail loudly. | Rejection tests |
| Integration/live-path | yes | Valid titles are consumed by HTML and RTF output paths. | Escaped-output test |
| Contract/API compatibility | yes | Existing default-title and block serialization behavior must continue passing. | Existing flow-document tests |
| Property/fuzz | no | The title type domain is finite by partition. | Not applicable |
| Mutation | yes | Validation guards and hydration routing are proof-critical. | Mutation gate recorded below |
| Security/adversarial | limited | Titles are untrusted display strings and must be escaped. | Existing and new escaping tests |
| Performance/resource | no | The slice adds constant-time validation. | Code inspection |
| Concurrency/race | no | No shared state, locks, workers, or temp files changed. | Not applicable |
| Golden artifact/visual | yes | HTML/RTF output must preserve escaped title content. | Exact output assertions |
| Regression | yes | This closes delayed crashes and silent stringification. | Rejection and hydration tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Removing constructor title normalization should fail constructor rejection or
  valid title output tests.
- Replacing hydration normalization with stringification or bypassing the
  constructor should fail hydration rejection tests.
- Weakening `None` or empty-string default handling should fail default-title
  tests.
- Weakening non-string rejection should fail constructor and hydration tests.

Current result:

- Cosmic Ray 8.4.6, scoped to title normalization and hydration routing: 8
  work items, 8 killed, and 0 survived.

## PO-FDT-001: Valid Titles Round-Trip And Escape

### Claim

Valid string titles are preserved through `parameters` and
`create_from_dict()` and are escaped in output formats.

### Domain

All string title values supplied through the public constructor or serialized
payloads.

### Proof Method

`_normalize_title()` returns valid strings unchanged. `parameters` stores the
normalized title, and `create_from_dict()` routes it back through the same
boundary. Focused tests assert round trip and escaped HTML/RTF output.

### Conclusion

Proven after focused tests and mutation pass.

## PO-FDT-002: Default Title Behavior Is Preserved

### Claim

`None` and empty-string titles produce `"InkGen Document"`.

### Domain

Direct construction and hydration where title is missing, `None`, or empty.

### Proof Method

`_normalize_title()` maps `None` and `""` to the default title. Focused tests
assert the public constructor and output path.

### Conclusion

Proven after focused tests and mutation pass.

## PO-FDT-003: Constructor Rejects Non-String Titles

### Claim

`FlowDocument(title=value)` rejects non-string, non-`None` values before output
generation.

### Domain

All public constructor calls.

### Proof Method

`FlowDocument.__init__()` routes title through `_normalize_title()`, which
raises `TypeError` for non-string values.

### Conclusion

Proven after focused tests and mutation pass.

## PO-FDT-004: Hydration Cannot Stringify Malformed Titles

### Claim

`FlowDocument.create_from_dict()` rejects non-string serialized title values
instead of silently stringifying them.

### Domain

Payloads passed to `FlowDocument.create_from_dict()`.

### Proof Method

Hydration passes `payload.get("title")` through `_normalize_title()` and then
the constructor. The focused hydration test injects an object title and asserts
the same validation failure.

### Conclusion

Proven after focused tests and mutation pass.

## Current Slice Decision

The slice keeps document output dependency-free and narrow. It validates title
type at the boundary instead of adding format-specific title repair or document
library dependencies.
