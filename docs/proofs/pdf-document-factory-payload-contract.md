# PDF Document Factory Payload Contract Proof Obligations

This note applies the InkGen Definition of Done to the
`PDF-DOCUMENT-FACTORY-PAYLOAD-P2` slice. It covers PDF document, page, and layer
hydration payload envelopes.

## Scope

The slice covers:

- `DocumentPDF.create_from_dict()`
- `_layers_pdf_from_dict()`
- `_layer_pdf_from_dict()`
- The local `_pdf_required_mapping()` helper used by this path.

Out of scope:

- `ComponentGroupPDF.create_from_dict()`, covered by
  `PDF-GROUP-FACTORY-PAYLOAD-P2`.
- Concrete PDF primitive factories, covered by
  `PDF-COMPONENT-FACTORY-PAYLOAD-P2`.
- PDF rendering, truth sorting, and file-writing path validation.

## Dependency Review

Affected surface:

- `src/InkGen/pdf_generator.py`
- `tests/test_pdf_document_factory_payload_contract.py`
- `docs/proofs/pdf-document-factory-payload-contract.md`

Incoming dependencies:

- Synthetic fixture workflows rely on `DocumentPDF.parameters` /
  `DocumentPDF.create_from_dict()` round trips.
- PDF rendering and truth output depend on hydrated pages and layers preserving
  document structure.
- Nested PDF group hydration depends on `ComponentGroupPDF.create_from_dict()`.

Outgoing dependencies:

- PDF document hydration consumes `Canvas`, `Layers`, `Layer`,
  `ComponentGroupPDF`, extraction-truth helpers, and grammar-truth helpers.
- No dependency was added.

Public contract:

- Valid `DocumentPDF` payloads hydrate to equivalent documents and deterministic
  PDF bytes.
- Malformed document roots, malformed `pages`, malformed page `Layers`
  envelopes, malformed layer envelopes, malformed layer collection fields, and
  malformed group collision setting entries fail explicitly before incidental
  subscription, iteration, or nested group hydration errors.
- Nested group payload failures remain delegated to the already-hardened PDF
  group factory boundary.

Serialized/artifact contract:

- `DocumentPDF.parameters` output remains unchanged.
- Valid document hydration preserves generated PDF bytes.
- Page/layer ordering remains the same as serialized data.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced.
- Layer check: PDF-specific hydration remains inside the concrete PDF renderer.
- Coupling check: document/page/layer hydration delegates child groups to the
  PDF group factory rather than duplicating group child validation.
- Redundancy check: local PDF payload helpers now cover primitive, group, and
  document-level PDF hydration envelopes.

ADR/rule impact:

- No ADR is required. The slice preserves the dependency-free PDF renderer
  policy and adds no library.

## Domain Definitions

- A valid PDF document payload is a mapping with a `DocumentPDF` mapping
  payload.
- `canvas` and `pages` are required document fields; `pages` must be a
  non-string sequence.
- Each page payload must be a `Layers` mapping payload with required `canvas`
  and `layers` mapping fields.
- Each layer payload must be a `Layer` mapping payload with required
  `layer_name`, `canvas`, `model`, `component_groups`, and
  `group_collision_settings` fields.
- `component_groups` must be a non-string sequence.
- `group_collision_settings` must be a mapping, and setting entries present for
  group labels must be mappings.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Malformed document root | Reject explicitly | PO-PDFDOCFACT-001 | document-root tests | killed |
| Missing document fields | Reject explicitly | PO-PDFDOCFACT-001 | missing-field tests | killed |
| Malformed page collection | Reject explicitly | PO-PDFDOCFACT-001 | pages sequence tests | killed |
| Malformed `Layers` page envelope | Reject explicitly | PO-PDFDOCFACT-002 | page-envelope tests | killed |
| Malformed layer envelope | Reject explicitly | PO-PDFDOCFACT-003 | layer-envelope tests | killed |
| Malformed layer collections/settings | Reject explicitly | PO-PDFDOCFACT-004 | layer collection/settings tests | killed |
| Valid document hydration | Preserve compatibility | PO-PDFDOCFACT-005 | valid round-trip and non-default layer tests | killed |
| Nested group hydration | Delegate to group factory | PO-PDFDOCFACT-006 | nested group failure test | killed |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Payload helpers and hydration functions are deterministic. | Direct factory tests |
| Behavioral/condition | yes | The slice defines `PDF-DOCUMENT-FACTORY-PAYLOAD-P2`. | Condition-marked tests |
| Failure-mode | yes | Old behavior failed through incidental subscription/iteration errors. | Malformed payload tests |
| Integration/live-path | yes | `DocumentPDF.create_from_dict()` crosses document, page, layer, group, component, and style hydration. | Focused PDF tests |
| Contract/API compatibility | yes | Valid serialized documents must preserve bytes. | Existing and new round-trip tests |
| Property/fuzz | no | The envelope domain is finite shape validation. | Explicit partitions |
| Mutation | yes | Required-field, mapping, sequence, and live-path rows are proof-critical. | Cosmic Ray gate |
| Security/adversarial | limited yes | Serialized payloads can be untrusted but do not trigger file, network, subprocess, SQL, archive, or active content behavior. | Malformed payload tests |
| Performance/resource | no | Adds constant-time envelope checks and existing linear hydration loops. | Not applicable |
| Golden artifact/visual | yes | Valid hydration preserves PDF bytes. | `to_pdf_bytes()` equality |
| Regression | yes | Prevents raw `KeyError`/attribute errors from document hydration. | Failure-mode tests |

## Mutation Testing Gate

Current result: passed.

- Focused tests: `105 passed`
- Latest filtered Cosmic Ray run: `14` proof-critical work items
- Mutation result: `14 killed`, `0 survived`

The former `core/ZeroIterationForLoop` survivor at
`src/InkGen/pdf_generator.py:1146` is killed by a valid hydration test whose
serialized page contains only a non-default `drawing` layer. If the constructor
default layer is not removed, the hydrated page exposes an extra `base` layer.

## PO-PDFDOCFACT-001: PDF Document Root And Pages Are Validated

### Claim

`DocumentPDF.create_from_dict()` rejects malformed document roots, missing
`canvas`, missing `pages`, and non-sequence `pages` before page hydration.

### Proof Method

The factory reads the root through `_pdf_payload()`, required fields through
`_pdf_required_field()`, and pages through `_pdf_required_sequence()`. Condition
tests cover malformed root and pages partitions.

### Conclusion

Proven by condition tests and scoped mutation testing.

## PO-PDFDOCFACT-002: PDF Page `Layers` Envelopes Are Validated

### Claim

Page payloads must be `Layers` mapping payloads with required `canvas` and
mapping `layers` fields.

### Proof Method

`_layers_pdf_from_dict()` validates the `Layers` root and required fields before
constructing the `Layers` object or iterating layer payloads. Tests mutate valid
document payloads at each page-envelope partition.

### Conclusion

Proven by condition tests and scoped mutation testing.

## PO-PDFDOCFACT-003: PDF Layer Envelopes Are Validated

### Claim

Layer payloads must be `Layer` mapping payloads with required layer metadata and
canvas fields before group hydration.

### Proof Method

`_layer_pdf_from_dict()` validates the `Layer` root and reads `layer_name`,
`canvas`, and `model` through required-field helpers before constructing
`Layer`.

### Conclusion

Proven by condition tests and scoped mutation testing.

## PO-PDFDOCFACT-004: Layer Component Collections And Collision Settings Are Validated

### Claim

Layer `component_groups` must be a non-string sequence and
`group_collision_settings` must be a mapping whose relevant entries are
mappings before groups are added.

### Proof Method

`_layer_pdf_from_dict()` reads `component_groups` through
`_pdf_required_sequence()` and `group_collision_settings` through
`_pdf_required_mapping()`. Tests cover malformed collection and setting
partitions.

### Conclusion

Proven by condition tests and scoped mutation testing.

## PO-PDFDOCFACT-005: Valid PDF Document Hydration Is Preserved

### Claim

Valid PDF document payloads still hydrate to equivalent documents and preserve
deterministic PDF bytes.

### Proof Method

Tests hydrate valid one-page documents with style caches and compare serialized
parameters and `to_pdf_bytes()` output. A non-default-layer case also proves
hydration removes the `Layers` constructor's default `base` layer before adding
serialized layers.

### Conclusion

Proven by condition tests and scoped mutation testing.

## PO-PDFDOCFACT-006: Nested Groups Use The PDF Group Factory Contract

### Claim

Malformed nested group payloads fail with the `ComponentGroupPDF` factory
boundary while document/page/layer envelopes remain valid.

### Proof Method

The dependent-path test mutates a nested group `components` field and verifies
`DocumentPDF.create_from_dict()` raises the group factory sequence error.

### Conclusion

Proven by condition tests and scoped mutation testing.
