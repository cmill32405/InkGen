# PDF Group Factory Payload Contract Proof Obligations

This note applies the InkGen Definition of Done to the
`PDF-GROUP-FACTORY-PAYLOAD-P2` slice. It covers
`ComponentGroupPDF.create_from_dict()` payload envelopes and closed child
component/style dispatch.

## Scope

The slice covers:

- `ComponentGroupPDF.create_from_dict()`
- `ComponentGroupPDF.set_clip_rect()`, `clear_clip_rect()`, and `clip_rect()`.
- `ComponentGroupPDF.set_blend_mode()`, `clear_blend_mode()`, and
  `blend_mode()`.
- PDF child component envelope validation.
- PDF child style envelope validation.
- Closed PDF component type dispatch.
- Rectangular PDF group clip serialization, hydration, and render output.
- Standard PDF group blend-mode serialization, hydration, and render output.

Out of scope:

- `DocumentPDF.create_from_dict()` root/page/layer envelope validation.
- Concrete PDF primitive factory field validation, covered by
  `PDF-COMPONENT-FACTORY-PAYLOAD-P2`.
- PDF rendering math and truth-record sorting.

## Dependency Review

Affected surface:

- `src/InkGen/pdf_generator.py`
- `tests/test_pdf_group_factory_payload_contract.py`
- `docs/proofs/pdf-group-factory-payload-contract.md`

Incoming dependencies:

- `DocumentPDF.create_from_dict()` hydrates nested page groups through
  `ComponentGroupPDF.create_from_dict()`.
- Synthetic PDF fixture workflows rely on PDF group
  `parameters/create_from_dict()` round trips.
- PDF rendering relies on `ComponentGroupPDF` preserving the closed component
  set enforced by `ComponentGroupPDF.add_component()`.

Outgoing dependencies:

- PDF group hydration consumes concrete PDF primitive factories, `DrawingStyle`,
  `TextStyle`, extraction-truth helpers, and grammar-truth helpers.
- No dependency was added.

Public contract:

- Valid `ComponentGroupPDF` payloads hydrate to equivalent groups.
- Optional `clip_rect` payloads hydrate to finite positive rectangular PDF
  group clipping state.
- Optional `blend_mode` payloads hydrate to a supported standard PDF blend
  mode or clear the setting for `Normal`.
- Malformed roots, missing `group_label`, missing or malformed `components`,
  malformed `clip_rect`, malformed `blend_mode`, malformed child entries,
  malformed style envelopes, and unsupported child or style types fail
  explicitly before dynamic dispatch or rendering.
- Child payloads still flow through the concrete child factory contract.

Serialized/artifact contract:

- `ComponentGroupPDF.parameters` adds `clip_rect` only when a group clip is
  configured.
- `ComponentGroupPDF.parameters` adds `blend_mode` only when a non-default
  group blend mode is configured.
- Valid group hydration preserves generated PDF operators.
- `DocumentPDF.create_from_dict()` remains compatible with valid nested groups.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced.
- Layer check: the change remains inside the concrete PDF renderer.
- Coupling check: dynamic dispatch is narrowed to the existing closed PDF
  component set.
- Redundancy check: local PDF payload helpers now cover primitive and group
  factory boundaries.

ADR/rule impact:

- ADR-0014 records the bounded PDF group clipping decision.
- ADR-0015 records the bounded PDF group blend-mode decision.
- The slices preserve the dependency-free PDF renderer policy and add no
  library.

## Domain Definitions

- A valid PDF group payload is a mapping with a `ComponentGroupPDF` mapping
  payload.
- `group_label` is required and remains validated by the base `ComponentGroup`
  constructor.
- `components` is a required non-string sequence.
- `clip_rect`, when present, is a four-number non-string sequence in InkGen
  document coordinates: `(x, y, width, height)`.
- Clip rectangle values must be finite non-boolean numbers, and width and
  height must be positive.
- `blend_mode`, when present, is a string naming a standard PDF blend mode.
- `Normal` and `None` clear blend state and are not serialized.
- Non-default blend mode spellings normalize to canonical PDF names after
  removing spaces, hyphens, and underscores.
- Every child component entry is a single-key mapping with a string PDF
  component type and mapping payload.
- Supported child component types are exactly `PDF_RENDER_COMPONENT_TYPES`.
- Child style envelopes, when present, are single-key mappings for
  `DrawingStyle` or `TextStyle` with a string `name`.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Malformed group root | Reject explicitly | PO-PDFGROUP-001 | malformed-root tests | killed |
| Missing required group fields | Reject explicitly | PO-PDFGROUP-001 | missing-field tests | killed |
| Malformed component collection | Reject explicitly | PO-PDFGROUP-002 | component collection tests | killed |
| Malformed child entry | Reject explicitly | PO-PDFGROUP-003 | child-entry tests | killed |
| Unsupported child type | Reject explicitly | PO-PDFGROUP-004 | unsupported-type tests | killed |
| Malformed style envelope | Reject explicitly | PO-PDFGROUP-005 | style-envelope tests | killed |
| Valid PDF group hydration | Preserve compatibility | PO-PDFGROUP-006 | round-trip test | killed |
| Document nested group hydration | Contract remains live | PO-PDFGROUP-007 | document-path test | killed |
| Configured clip rectangle | Emit `re W n` before children | PO-PDFGROUP-008 | clip render test | mutation target |
| Serialized clip rectangle | Preserve through parameters/hydration | PO-PDFGROUP-009 | clip round-trip test | mutation target |
| Malformed clip rectangle | Reject before public state mutation or hydration return | PO-PDFGROUP-010 | malformed clip tests | mutation target |
| Document live clip path | Emit clipping through `DocumentPDF` page stream | PO-PDFGROUP-011 | document live-path test | mutation target |
| Configured blend mode | Emit `/ExtGState` resource and group `gs` operator | PO-PDFGROUP-012 | blend render test | mutation target |
| Serialized blend mode | Preserve through parameters/hydration | PO-PDFGROUP-013 | blend round-trip test | mutation target |
| Malformed blend mode | Reject before public state mutation or hydration return | PO-PDFGROUP-014 | malformed blend tests | mutation target |
| Blend plus clip | Share one group graphics-state wrapper | PO-PDFGROUP-015 | blend+clip live-path test | mutation target |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Payload helpers and dispatch checks are deterministic. | Direct group factory tests |
| Behavioral/condition | yes | The proof note covers `PDF-GROUP-FACTORY-PAYLOAD-P2` and `PDF-GROUP-CLIP-P3`. | Condition-marked tests |
| Failure-mode | yes | Old behavior failed through incidental lookup, subscription, or dynamic dispatch errors. | Malformed payload tests |
| Integration/live-path | yes | `DocumentPDF.create_from_dict()` consumes nested PDF groups and `DocumentPDF.to_pdf_bytes()` emits clipped/blended groups. | Document hydration, live clipping, and live blend tests |
| Contract/API compatibility | yes | Existing valid group/document round trips must remain. | Existing and new round-trip tests |
| Property/fuzz | no | The envelope domain is finite shape validation. | Explicit partitions |
| Mutation | yes | Validation guards and closed dispatch are proof-critical. | Cosmic Ray gate |
| Security/adversarial | limited yes | Serialized payloads can be untrusted but do not trigger file, network, subprocess, SQL, archive, or active content behavior. | Malformed payload and clip tests |
| Performance/resource | no | Adds constant-time envelope checks and one linear component loop. | Not applicable |
| Golden artifact/visual | limited yes | Valid group hydration preserves generated PDF operators, and clipped/blended groups emit deterministic PDF operators. | `generate_pdf()` equality and stream assertions |
| Regression | yes | Prevents arbitrary module dispatch from group payloads. | Unsupported-type tests |

## Mutation Testing Gate

Current result:

- Tool: Cosmic Ray 8.4.6.
- Environment: WSL Python 3.12 virtualenv.
- Config: `tests/mutation/pdf_group_factory_payload_cosmic_ray.toml`.
- Filter: `tests/mutation/filter_pdf_group_factory_payload_work_items.py`.
- Test selection: PDF group factory payload, PDF component factory payload, PDF
  generator, and PDF document tests.
- Raw work items: 2015.
- Proof-critical work items after filter: 42.
- Killed mutants: 42.
- Surviving mutants: 0.
- Gate result: pass.

`PDF-GROUP-CLIP-P3` mutation result:

- Tool: Cosmic Ray 8.4.6.
- Environment: WSL Python 3.12 virtualenv.
- Config: `tests/mutation/pdf_group_clip_cosmic_ray.toml`.
- Filter: `tests/mutation/filter_pdf_group_clip_work_items.py`.
- Test selection: PDF generator, PDF group factory payload, and PDF render
  contract tests.
- Raw work items: 4864.
- Proof-critical work items after filter: 43.
- Killed mutants: 43.
- Surviving mutants: 0.
- Gate result: pass.
- Mutation exposed missing boundary partitions for long clip sequences,
  negative width, zero height, and fractional negative height; those tests were
  added before the passing mutation run.

`PDF-GROUP-BLEND-P3` mutation result:

- Tool: Cosmic Ray 8.4.6.
- Environment: WSL Python 3.12 virtualenv.
- Config: `tests/mutation/pdf_group_blend_cosmic_ray.toml`.
- Filter: `tests/mutation/filter_pdf_group_blend_work_items.py`.
- Test selection: PDF generator, PDF group factory payload, and PDF render
  contract tests.
- Raw work items: 4994.
- Proof-critical work items after filter: 47.
- Killed mutants: 47.
- Surviving mutants: 0.
- Gate result: pass.
- Mutation exposed missing proof pressure for blend resource object-id
  continuity; the live-path test now asserts contiguous object ids.

## PO-PDFGROUP-001: PDF Group Roots And Required Fields Are Validated

### Claim

`ComponentGroupPDF.create_from_dict()` rejects malformed group roots and missing
required group fields before child component hydration.

### Proof Method

The factory reads the root through `_pdf_payload()` and required fields through
`_pdf_required_field()` / `_pdf_required_sequence()`. Condition tests cover
non-mapping roots, missing class key, non-mapping payload, missing `group_label`,
missing `components`, and string `components`.

### Conclusion

Proven for group roots and required group fields in the declared domain.

## PO-PDFGROUP-002: Component Collections Are Required Sequences

### Claim

`components` must be present and must be a non-string sequence before
enumeration.

### Proof Method

The factory iterates `_pdf_required_sequence(payload, "components",
"ComponentGroupPDF")`. Tests cover missing and string component collections.

### Conclusion

Proven for required PDF group component collections.

## PO-PDFGROUP-003: Child Component Entries Are Typed Mapping Envelopes

### Claim

Each child component entry must be a single-key mapping whose key is a string
type name and whose value is a mapping payload.

### Proof Method

The factory validates each child entry through `_pdf_single_mapping_entry()`.
Tests cover non-mapping entries, zero-key/multi-key entries, non-string type
keys, and non-mapping child payloads.

### Conclusion

Proven for child component entry envelope partitions in scope.

## PO-PDFGROUP-004: PDF Group Hydration Uses Closed Component Dispatch

### Claim

PDF group hydration only dispatches to classes in `PDF_RENDER_COMPONENT_TYPES`.

### Proof Method

`_pdf_component_class()` resolves a type name and rejects missing or out-of-set
types before calling `create_from_dict()`. Tests cover a missing type name and a
real in-module class that is not a PDF primitive.

### Conclusion

Proven for closed PDF component dispatch in group hydration.

## PO-PDFGROUP-005: Child Style Envelopes Are Validated Before Style Hydration

### Claim

Child style envelopes must be single-key mappings for `DrawingStyle` or
`TextStyle` with a string `name`.

### Proof Method

`_pdf_style_entry()` validates the style envelope before style cache lookup or
style factory hydration. Tests cover malformed mappings, malformed type keys,
non-mapping style payloads, missing/non-string names, and unsupported style
types.

### Conclusion

Proven for child style envelope partitions in scope.

## PO-PDFGROUP-006: Valid PDF Group Hydration Is Preserved

### Claim

Valid PDF group payloads still hydrate to equivalent groups and preserve
generated PDF operators.

### Proof Method

Tests hydrate a group containing drawing and text children with a style cache,
then compare serialized parameters and `generate_pdf()` output.

### Conclusion

Proven for valid PDF group hydration compatibility.

## PO-PDFGROUP-007: Document Hydration Uses The Group Factory Contract

### Claim

`DocumentPDF.create_from_dict()` routes nested group payloads through
`ComponentGroupPDF.create_from_dict()`, so malformed nested group payloads fail
with group-factory errors.

### Proof Method

The dependent-path test hydrates a valid PDF document, then corrupts a nested
group `components` field and verifies the document path raises the group
factory sequence error.

### Conclusion

Proven for nested group hydration through `DocumentPDF.create_from_dict()`.

## PO-PDFGROUP-008: Group Clip Rectangles Emit Deterministic Operators

### Claim

`ComponentGroupPDF.generate_pdf()` emits a configured rectangular clip path
before child component operators and restores graphics state after the group.

### Proof Method

`set_clip_rect()` stores a validated rectangle. `generate_pdf()` inserts `q`,
the rectangle `re` path, `W`, `n`, existing child operators, and `Q`. The
condition test asserts operator ordering relative to a child rectangle.

### Conclusion

Proven for rectangular group clipping after tests and mutation pass.

## PO-PDFGROUP-009: Group Clip Rectangles Round Trip Through Parameters

### Claim

A configured clip rectangle is serialized only when present and hydrates back to
equivalent group state and generated PDF operators.

### Proof Method

`parameters` writes `clip_rect` as a numeric list. `create_from_dict()` calls
`set_clip_rect()` when the field is present. The round-trip condition test
compares serialized parameters and generated PDF operators.

### Conclusion

Proven for serialized rectangular clip state after tests and mutation pass.

## PO-PDFGROUP-010: Malformed Clip Rectangles Fail Explicitly

### Claim

Malformed direct and serialized clip rectangles fail before public group state
is mutated or a hydrated group is returned.

### Proof Method

`_coerce_pdf_clip_rect()` rejects strings, non-sequences, wrong lengths,
boolean values, nonnumeric values, non-finite values, and non-positive width or
height. Condition tests cover representative partitions and assert failed
direct calls leave `clip_rect()` unset.

### Conclusion

Proven for declared malformed clip rectangle partitions after tests and
mutation pass.

## PO-PDFGROUP-011: DocumentPDF Consumes Group Clips On The Live Path

### Claim

`DocumentPDF.to_pdf_bytes()` emits clipped `ComponentGroupPDF` content on the
page content-stream path without relaxing closed group/component guards.

### Proof Method

The document live-path condition test adds a clipped exact `ComponentGroupPDF`
to a page layer and asserts the page content stream contains the page transform
followed by the group clipping operators before child operators. Existing
PDF-GUARD-P3 tests continue to prove closed group/component dispatch.

### Conclusion

Proven for the document live path after tests and mutation pass.

## PO-PDFGROUP-012: Group Blend Modes Emit Deterministic ExtGState Operators

### Claim

`DocumentPDF.to_pdf_bytes()` emits deterministic PDF `/ExtGState` resources for
configured non-default group blend modes, then applies the resource before group
child operators.

### Proof Method

`ComponentGroupPDF.generate_pdf()` requests a blend-mode resource from
`PDFRenderContext`. `DocumentPDF.to_pdf_bytes()` writes the resource as a
deterministic ExtGState object and includes it in the page resource dictionary.
The live-path condition test asserts the resource object and content-stream
operator placement.

### Conclusion

Proven for supported non-default group blend modes after tests and mutation
pass.

## PO-PDFGROUP-013: Group Blend Modes Round Trip Through Parameters

### Claim

A configured non-default blend mode is serialized only when present and hydrates
back to equivalent canonical group state.

### Proof Method

`parameters` writes `blend_mode` as the canonical PDF name. `create_from_dict()`
calls `set_blend_mode()` when the field is present. The round-trip condition
test compares serialized parameters and hydrated state.

### Conclusion

Proven for serialized group blend state after tests and mutation pass.

## PO-PDFGROUP-014: Malformed Blend Modes Fail Explicitly

### Claim

Malformed direct and serialized blend modes fail before public group state is
mutated or a hydrated group is returned.

### Proof Method

`_coerce_pdf_blend_mode()` rejects non-string values, empty strings, and names
outside the supported standard PDF blend-mode set. Condition tests cover direct
state mutation and serialized hydration.

### Conclusion

Proven for declared malformed blend mode partitions after tests and mutation
pass.

## PO-PDFGROUP-015: Blend Modes Compose With Group Clipping

### Claim

A group configured with both a blend mode and a clip rectangle emits one group
graphics-state wrapper, applies the blend mode before the clip path, and then
emits child operators.

### Proof Method

The blend+clip condition test adds both controls to one exact
`ComponentGroupPDF` and asserts the live page content stream contains one group
wrapper sequence with `/GSx gs`, `re`, `W`, `n`, and then child operators.

### Conclusion

Proven for group blend plus rectangular clip composition after tests and
mutation pass.
