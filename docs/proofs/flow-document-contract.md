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
- Before the root-payload hardening update, malformed `FlowDocument` root
  payloads and string `blocks`/`paragraphs` collections could fail through
  incidental attribute errors or character-by-character iteration.
- Before the drawing-component envelope hardening update, malformed serialized
  drawing component envelopes could fail through incidental lookup errors, and
  unsupported component types could fail through style extraction before the
  intended unsupported-type check.
- Before the drawing-payload hardening update, malformed serialized drawing
  payloads could fail through incidental `KeyError` or character-by-character
  component iteration.
- Before the drawing-style hardening update, malformed serialized drawing style
  envelopes and mismatched style override map entries could fail through
  incidental `KeyError` or reach primitive construction with the wrong style
  type.
- Before the style-mapping hardening update, non-mapping `styles` override
  containers could fail through incidental iterable or index errors during
  block hydration.
- Before the path-command hardening update, malformed serialized `PathDrawing`
  command envelopes could fail through incidental indexing errors before
  reaching `PathCommand`.
- Before the filepath hardening update, malformed file-writer paths could fail
  through incidental `os.path` or `open()` errors, and path-like objects were
  not part of the documented writer contract.
- After this slice, DOCX ZIP parts use a fixed timestamp and drawing
  materialization must return an InkGen `Component`.
- After the drawing-label hardening update, drawing block hydration passes
  serialized labels unchanged into `DrawingComponentGroup`, where non-string
  labels fail at the renderer-neutral boundary.
- After the block-envelope hardening update, block hydration first validates
  that each block is a mapping with a string `type` and mapping `payload`.
- After the root-payload hardening update, `create_from_dict()` first validates
  the wrapped or direct flow-document payload and collection fields.
- After the drawing-component envelope hardening update, drawing component
  hydration validates component envelope shape and discriminator support before
  style extraction, then dispatches supported non-path primitives through an
  exact constructor map.
- After the drawing-payload hardening update, drawing block hydration validates
  that the drawing payload contains `group_label` and a non-string component
  sequence before constructing the neutral drawing group.
- After the drawing-style hardening update, component hydration requires a style
  payload, validates the nested style envelope and style name, and verifies
  override-map values match the component's drawing/text style kind.
- After the style-mapping hardening update, `FlowDocument.create_from_dict()`
  validates that `styles` is a mapping or `None` before block hydration.
- After the path-command hardening update, `PathDrawing` hydration validates
  that commands are a non-string sequence of command envelopes with `type` and
  `points` before constructing `PathCommand` objects.
- After `PATH-POINT-SHAPE-P2`, malformed point entries inside serialized
  `PathDrawing` commands are rejected by the delegated `PathCommand` point
  boundary instead of being accepted as character/byte coordinate pairs.
- After the filepath hardening update, file writers normalize string and
  path-like output paths through one boundary helper and reject non-string,
  bytes, and empty paths before writing.
- After the RTF Unicode hardening update, `FlowDocument.to_rtf()` emits
  non-ASCII title and paragraph text as RTF `\uN?` escapes instead of raw
  Unicode text in an `\ansi` document.
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
  materialize to an InkGen `Component` with the renderer-specific fragment
  surface needed by the target document format.

## Fix Log

- DOCX ZIP parts are now written through `_write_docx_part()` with
  `DOCX_FIXED_TIMESTAMP`.
- Flow-document drawing HTML, bounds, and VML helpers now call
  `_materialize_drawing_component()`.
- `_materialize_drawing_component()` rejects missing/non-callable materializers
  and non-`Component` materialization results.
- `_svg_fragment()` rejects SVG materializations that cannot provide a string
  `generate_svg()` fragment, and DOCX VML conversion rejects PDF
  materializations without a `points` surface.
- `_drawing_from_parameters()` now delegates serialized drawing labels to
  `DrawingComponentGroup` without stringifying malformed values.
- `_block_from_parameters()` now validates serialized block envelopes before
  dispatching to paragraph, table, or drawing hydration.
- `_flow_document_payload()` and `_payload_sequence()` validate root payloads
  and serialized collection fields before block or paragraph iteration.
- `_drawing_component_from_parameters()` validates drawing component envelopes
  and supported discriminators before style extraction.
- `_drawing_from_parameters()` validates drawing payload keys and component
  sequence shape before iterating components.
- `_style_from_payload()` validates drawing style envelope shape and override
  type before constructing or reusing a style object.
- `_normalize_style_overrides()` validates optional style override maps before
  paragraph or drawing hydration can use membership or index lookups.
- `_path_commands_from_payload()` validates serialized path command envelope
  shape before delegating command semantics to `PathCommand`.
- `PathCommand` validates serialized path command point-entry shape for
  `FlowDocument` path hydration.
- `_normalize_output_filepath()` validates all flow-document file-writer output
  paths before text or byte writes.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Repeated DOCX generation | Preserve exact bytes and fixed part order/timestamps | PO-FDOC-001 | `test_flow_document_docx_bytes_are_deterministic` | killed |
| Text with XML/HTML/RTF controls | Escape per target format | PO-FDOC-002 | `test_flow_document_escapes_text_across_output_formats` | behavioral evidence |
| RTF non-ASCII text | Emit RTF Unicode escapes for title and paragraph text | PO-FDOC-016 | `test_flow_document_rtf_escapes_unicode_text` | killed with documented equivalent survivors |
| Paragraph/table/drawing block order | Preserve through parameters and output | PO-FDOC-003 | `test_flow_document_preserves_mixed_block_order_after_round_trip` | behavioral evidence |
| Root payload shape | Accept wrapped/direct mappings and reject malformed payload roots or collection fields | PO-FDOC-008 | `test_flow_document_hydrates_direct_payload_mapping`, `test_flow_document_hydration_rejects_malformed_root_payloads` | killed |
| Serialized block envelope and dispatch | Reject malformed envelopes and dispatch valid dynamic type strings by value | PO-FDOC-007 | `test_flow_document_hydration_rejects_malformed_block_envelopes`, `test_flow_document_hydration_dispatches_dynamic_block_type_strings` | killed |
| Serialized drawing payload | Reject missing drawing payload keys and non-sequence component collections before component iteration | PO-FDOC-010 | `test_flow_document_hydration_rejects_malformed_drawing_payloads` | killed |
| Serialized drawing component envelope and dispatch | Reject malformed component envelopes, reject unsupported types before style extraction, and dispatch valid dynamic type strings by value | PO-FDOC-009 | `test_flow_document_hydration_rejects_malformed_drawing_component_envelopes`, `test_flow_document_hydration_dispatches_dynamic_drawing_component_type_strings` | killed |
| Serialized drawing style envelope | Reject missing/malformed style envelopes, mismatched style keys, non-string style names, and wrong-type style overrides | PO-FDOC-011 | `test_flow_document_hydration_rejects_malformed_drawing_style_payloads`, `test_flow_document_hydration_rejects_mismatched_drawing_style_overrides`, `test_flow_document_hydration_constructs_missing_drawing_style_overrides_by_kind` | killed |
| Style override map boundary | Reject non-mapping `styles` values before block hydration | PO-FDOC-015 | `test_flow_document_hydration_rejects_malformed_style_override_maps` | killed |
| Serialized path command envelope | Reject malformed `PathDrawing` command collections before `PathCommand` construction and delegate point-entry shape validation to `PathCommand` | PO-FDOC-012 | `test_flow_document_hydration_rejects_malformed_path_command_payloads` | killed |
| File writer path boundary | Accept string/path-like output paths and reject malformed output path values before writing | PO-FDOC-013 | `test_flow_document_file_writers_accept_pathlike_outputs`, `test_flow_document_file_writers_reject_malformed_paths`, `test_flow_document_file_writers_fail_on_missing_directory` | killed |
| Malformed serialized drawing label | Reject through the neutral group label contract | PO-FDOC-006 | `test_flow_document_drawing_group_hydration_rejects_malformed_label` | behavioral evidence |
| Invalid drawing materialization | Reject before silent omission | PO-FDOC-004 | `test_flow_document_rejects_invalid_drawing_materialization` | killed |
| Invalid drawing render fragments | Reject SVG materializations without string `generate_svg()` fragments and DOCX/PDF materializations without points | PO-FDOC-014 | `test_flow_document_rejects_materializations_without_render_fragments` | killed |
| DOCX VML linework | Emit group-relative points | PO-FDOC-005 | `test_flow_document_docx_drawing_polyline_uses_group_relative_points` | killed |
| Unsupported block private mutation | Excluded from public contract | Explicit exclusion | Not applicable | Out of scope |
| Full WordprocessingML feature parity | Excluded from minimal dependency-free backend | Explicit exclusion | Not applicable | Out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Helpers are deterministic. | FLOW-DOCUMENT-P1 tests |
| Behavioral/condition | yes | The slice defines document-output behavior. | Tests are marked `@pytest.mark.condition("FLOW-DOCUMENT-P1")`, `@pytest.mark.condition("FLOW-DOCUMENT-SVG-MATERIALIZATION-P2")`, and `@pytest.mark.condition("FLOW-DOCUMENT-STYLES-MAPPING-P2")`. |
| Failure-mode | yes | Invalid content, malformed root payloads, malformed serialized block envelopes, malformed drawing payloads, malformed drawing component envelopes, malformed drawing style envelopes, malformed style override maps, malformed path command envelopes, malformed serialized drawing labels, malformed materialization fragments, malformed output paths, and invalid output paths must fail loudly. | Invalid hydration, invalid materialization, render-fragment, style-map, and writer tests |
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
- Weakening SVG fragment callability/string checks or DOCX VML points-surface
  checks should fail render-fragment tests.
- Changing DOCX VML group-relative points should fail exact polyline tests.
- Reintroducing drawing-label stringification should fail the serialized drawing
  label hydration test.
- Reintroducing raw non-ASCII RTF output should fail the RTF Unicode text test.
- Weakening serialized block envelope validation or dispatch should fail the
  malformed-envelope test.
- Weakening root payload or collection validation should fail malformed-root
  tests.
- Weakening serialized drawing component envelope validation or dispatch should
  fail malformed-component and dynamic-component-dispatch tests.
- Weakening serialized drawing payload key or component-sequence validation
  should fail malformed-drawing-payload tests.
- Weakening serialized drawing style envelope or override type validation should
  fail malformed-style, mismatched-override, or fallback-construction tests.
- Weakening style override map validation should fail malformed-style-map tests.
- Weakening serialized path command envelope validation should fail malformed
  path-command tests.
- Weakening file-writer path normalization should fail malformed-path or
  path-like output tests.

Current result:

- Cosmic Ray 8.4.6, scoped to changed DOCX package assembly, drawing
  materialization guards, and VML point rows: 34 work items, 34 killed, and 0
  survived.
- Cosmic Ray 8.4.6, scoped to RTF title/paragraph call sites and
  `_rtf_escape()` Unicode/control escaping rows after the RTF Unicode hardening
  update: 34 work items, 31 killed, and 3 documented equivalent survivors. The
  survivors are `==` to `is` mutations for the one-character RTF control
  comparisons (`\`, `{`, `}`), which are equivalent under the target CPython
  runtime's cached single-character string behavior. Strengthened U+0080 and
  U+8000 edge assertions killed the actionable Unicode-boundary survivors.
- Cosmic Ray 8.4.6, scoped to serialized block-envelope validation and
  dispatch rows after the block-envelope hardening update: 32 work items, 32
  killed, and 0 survived.
- Cosmic Ray 8.4.6, scoped to root-payload validation rows after the
  root-payload hardening update: 8 work items, 8 killed, and 0 survived.
- Cosmic Ray 8.4.6, scoped to drawing component envelope validation and
  dispatch rows after the drawing-component hardening update: 17 work items, 17
  killed, and 0 survived.
- Cosmic Ray 8.4.6, scoped to drawing payload validation rows after the
  drawing-payload hardening update: 7 work items, 7 killed, and 0 survived.
- Cosmic Ray 8.4.6, scoped to drawing style envelope validation rows after the
  drawing-style hardening update: 15 work items, 15 killed, and 0 survived.
- Cosmic Ray 8.4.6, scoped to path command envelope validation rows after the
  path-command hardening update: 19 work items, 19 killed, and 0 survived.
- Cosmic Ray 8.4.6, scoped to file-writer path normalization rows after the
  filepath hardening update: 7 work items, 7 killed, and 0 survived.
- Cosmic Ray 8.4.6, scoped to render-fragment guards after the SVG
  materialization hardening update: 7 work items, 7 killed, and 0 survived.
- Cosmic Ray 8.4.6, scoped to style override map validation after the
  style-mapping hardening update: 4 work items, 4 killed, and 0 survived.

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

## PO-FDOC-016: RTF Unicode Text Is Escaped

### Claim

RTF output represents non-ASCII title and paragraph text with RTF Unicode
escapes instead of raw Unicode characters.

### Domain

`FlowDocument.to_rtf()` output for valid Python `str` titles and paragraph
text, including BMP and supplementary Unicode code points.

### Proof Method

`_rtf_escape()` preserves existing ASCII output, escapes RTF control characters,
and encodes every non-ASCII character as one or more UTF-16 code units rendered
as signed RTF `\uN?` fallback escapes. The focused test covers title and
paragraph text, BMP characters, and a supplementary emoji represented as a
surrogate pair.

### Counterexamples And Exclusions

Full RTF font-table internationalization and reader-specific fallback glyph
selection are outside this dependency-free minimal backend. The contract is the
artifact text shape emitted by InkGen.

### Conclusion

Proven for valid public `FlowDocument` title and paragraph strings, with the
mutation gate limited only by documented equivalent single-character identity
survivors.

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

## PO-FDOC-008: Root Payload Shape Is Validated

### Claim

`FlowDocument.create_from_dict()` accepts wrapped and direct mapping payloads
and rejects malformed root payloads before iterating blocks or legacy
paragraphs.

### Domain

Public `FlowDocument.create_from_dict(data, styles=None)` calls using either
`{"FlowDocument": payload}` or direct payload mappings.

### Proof Method

`_flow_document_payload()` requires `data` to be a mapping, unwraps
`FlowDocument` when present, and requires the unwrapped payload to be a mapping.
`_payload_sequence()` accepts absent collection fields as empty lists, rejects
strings and bytes, and requires collection fields to be sequences before
iteration. Focused tests cover a valid direct payload, non-mapping root data,
non-mapping wrapped payloads, and malformed `blocks`/`paragraphs` collections.

### Counterexamples And Exclusions

Individual malformed block envelopes are delegated to PO-FDOC-007. Malformed
legacy paragraph payloads inside a valid `paragraphs` sequence are delegated to
the paragraph contract.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-FDOC-009: Drawing Component Envelopes Are Validated

### Claim

Flow-document drawing block hydration rejects malformed drawing component
envelopes at the document boundary and dispatches supported component type
strings by value.

### Domain

Each item in a serialized drawing block's `components` sequence.

### Proof Method

`_drawing_component_from_parameters()` first requires the component entry to be
a mapping, then requires both `type` and `payload`, a string `type`, membership
in the closed `DRAWING_COMPONENT_TYPES` set, and a mapping payload. Only after
those checks does it extract style data. `TextDrawing` style selection uses an
explicit text-component discriminator set, `PathDrawing` rebuilds path commands,
and all other supported primitives dispatch through
`DRAWING_COMPONENT_CONSTRUCTORS` by exact key lookup. Focused tests cover a
non-mapping component entry, missing discriminator or payload, non-string
discriminator, non-mapping payload, unsupported string discriminator, and valid
dynamically constructed discriminators for every supported drawing component
type.

### Counterexamples And Exclusions

Malformed style payloads and malformed primitive geometry inside a valid
component envelope are delegated to the owning style and drawing primitive
contracts. Malformed `TextDrawing.text` payload values are delegated to
PO-TEXT-008 in `text-renderer-contract.md`, and malformed
`RectangleDrawing` geometry payloads are delegated to PO-RECT-006 in
`rectangle-renderer-contract.md`, and malformed `LineDrawing` endpoint payloads
are delegated to PO-LINE-008 in `line-renderer-contract.md`; dependent-path
tests prove those payloads cannot hydrate into public document state.

### Conclusion

Proven for the stated domain after focused tests, mutation, and the full DoD
gate pass.

## PO-FDOC-010: Drawing Payloads Are Validated

### Claim

Flow-document drawing block hydration rejects malformed drawing payloads before
constructing a `DrawingComponentGroup` or iterating component entries.

### Domain

Serialized drawing block payloads passed through `FlowDocument.create_from_dict()`.

### Proof Method

`_drawing_from_parameters()` requires the drawing payload to be a mapping with
both `group_label` and `components`. It then requires `components` to be a
non-string sequence before iterating. Focused tests cover missing
`group_label`, missing `components`, string components, bytes components, and a
non-sequence object.

### Counterexamples And Exclusions

Malformed labels are delegated to the `DrawingComponentGroup` label contract.
Malformed component entries inside a valid component sequence are delegated to
the drawing component envelope contract.

### Conclusion

Proven for the stated domain after focused tests, mutation, and the full DoD
gate pass.

## PO-FDOC-011: Drawing Style Envelopes Are Validated

### Claim

Flow-document drawing component hydration rejects malformed serialized style
envelopes and mismatched style override entries before primitive construction.

### Domain

Serialized drawing component payloads passed through
`FlowDocument.create_from_dict()`, including the optional `styles` override map.

### Proof Method

`_drawing_component_from_parameters()` requires every component payload to
include `style`. `_style_from_payload()` then requires the style payload to be a
mapping with the expected `DrawingStyle` or `TextStyle` key, a mapping style
entry, and a string style name. If an override exists in `styles`, the override
must be a `DrawingStyle` for drawing primitives or a `TextStyle` for text
primitives. Without an override, focused tests prove fallback construction uses
the correct style class for both drawing and text components.

### Counterexamples And Exclusions

Style field-level validation, such as color, opacity, font, and line-spacing
rules, remains delegated to `DrawingStyle`, `TextStyle`, and `Font`.

### Conclusion

Proven for the stated domain after focused tests, mutation, and the full DoD
gate pass.

## PO-FDOC-012: Path Command Envelopes Are Validated

### Claim

Flow-document `PathDrawing` hydration rejects malformed serialized path command
envelopes before constructing `PathCommand` objects.

### Domain

Serialized `PathDrawing` component payloads passed through
`FlowDocument.create_from_dict()`.

### Proof Method

`_path_commands_from_payload()` requires `commands` to be present and to be a
non-string sequence. Each command entry must be a mapping with both `type` and
`points`, and `points` must be a non-string sequence. Focused tests cover a
missing command collection, string/bytes/non-sequence collections, non-mapping
command entries, missing command fields, and malformed point collections.

### Counterexamples And Exclusions

Path command semantic validation, including supported command letters, point
arity, numeric coercion, and finite coordinate checks, remains delegated to
`PathCommand`.

### Conclusion

Proven for the stated domain after focused tests, mutation, and the full DoD
gate pass.

## PO-FDOC-013: File Writer Paths Are Validated

### Claim

Flow-document file writers accept string and path-like output paths, reject
malformed path values at the InkGen boundary, and preserve generated payloads.

### Domain

`FlowDocument.create_docx()`, `create_html()`, `create_rtf()`, and
`create_text()` calls.

### Proof Method

All four writer methods delegate to `_normalize_output_filepath()` through
`_write_text()` or `_write_bytes()`. The helper uses `os.fspath()` to accept
string and path-like values, rejects bytes and non-path objects, rejects empty
paths, and preserves the existing missing-directory `ValueError`. Focused tests
cover successful `pathlib.Path` writes for every writer, malformed object,
integer, bytes, and empty-string paths, plus the existing missing-directory
failure and payload equality checks.

### Counterexamples And Exclusions

Filesystem permission errors, concurrent file replacement, and platform-specific
reserved path names remain delegated to the operating system.

### Conclusion

Proven for the stated domain after focused tests, mutation, and the full DoD
gate pass.

## PO-FDOC-014: Drawing Materializations Expose Render Fragments

### Claim

Flow-document drawing outputs fail before silently omitting a drawing primitive
whose concrete materialization lacks the renderer-specific fragment contract.

### Domain

Drawing groups exported through `FlowDocument.to_html()` and
`FlowDocument.to_docx_bytes()`.

### Proof Method

HTML drawing output routes each neutral primitive through `_svg_fragment()`,
which first uses `_materialize_drawing_component()` to prove the object is an
InkGen `Component`, then requires a callable `generate_svg()` method returning
a string. DOCX VML output materializes non-special-case primitives through the
PDF path and requires a `points` surface before deciding whether an empty point
list should produce no polyline. Focused tests cover a base `Component`
materialization that previously produced empty HTML/DOCX drawing output and a
malformed SVG materialization whose `generate_svg()` does not return a string.

### Counterexamples And Exclusions

Valid components with an empty `points` collection remain allowed to produce no
VML polyline. Full SVG semantic validation remains delegated to the concrete
SVG renderer tests.

### Conclusion

Proven after focused tests, mutation, and the full DoD gate pass.

## PO-FDOC-015: Style Override Maps Are Validated

### Claim

`FlowDocument.create_from_dict()` rejects malformed `styles` override
containers before paragraph or drawing block hydration can use membership or
index lookups.

### Domain

Public `FlowDocument.create_from_dict(data, styles=...)` calls with `styles`
set to `None`, a mapping, or a malformed non-mapping container.

### Proof Method

`FlowDocument.create_from_dict()` normalizes `styles` through
`_normalize_style_overrides()` before reading serialized blocks. The same helper
is used inside `_style_from_payload()` so internal callers cannot reintroduce
sequence or arbitrary-object lookup behavior. Focused tests cover arbitrary
objects, lists, strings, and bytes as malformed override containers while
existing round-trip and fallback tests preserve valid `None` and mapping
behavior.

### Counterexamples And Exclusions

Validation of individual style override values remains covered by
`PO-FDOC-011`. Private mutation of the normalized mapping after validation is
outside the public `create_from_dict()` contract.

### Conclusion

Proven after focused tests, mutation, and the full DoD gate pass.

## Current Slice Decision

The slice keeps `FlowDocument` dependency-free and minimal. It fixes byte
determinism and boundary validation without adding document libraries or
expanding the flow-document renderer into a general drawing renderer.
