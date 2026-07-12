# Paragraph Contract Proof Obligations

This note applies the InkGen Definition of Done to the PARAGRAPH-P1 paragraph
model slice. It focuses on finite numeric paragraph measurements, strict
serialized hydration, tab-stop validation, and live materialization through
drawing and flow-document output.

## Scope

The slice covers:

- `TabStop.__post_init__()`
- `TabStop.create_from_dict()`
- `Paragraph.position`
- `Paragraph.width`
- `Paragraph.first_line_indent`
- `Paragraph.hanging_indent`
- `Paragraph.left_indent`
- `Paragraph.right_indent`
- `Paragraph.space_before`
- `Paragraph.space_after`
- `Paragraph.line_spacing`
- `Paragraph.outline_level`
- `Paragraph.__init__(..., tab_stops=...)`
- `Paragraph.add_tab_stop()`
- `Paragraph.remove_tab_stop()`
- `Paragraph.create_from_dict()`
- `Paragraph.to_drawing_group()`

## Architecture Impact

Affected surface:

- `src/InkGen/paragraph.py`: paragraph measurement and hydration validation.
- `tests/test_paragraph_contract.py`: PARAGRAPH-P1 behavioral and live-path
  tests.
- `tests/mutation/paragraph_cosmic_ray.toml`: scoped mutation gate.
- `tests/mutation/filter_paragraph_work_items.py`: proof-critical mutation
  filter.

Incoming dependencies:

- Public callers import `Paragraph`, `ParagraphAlignment`, `LineSpacingRule`,
  `ParagraphLine`, and `TabStop` from `InkGen`.
- `FlowDocument` consumes paragraphs for DOCX, HTML, RTF, and plain-text
  output.
- `Paragraph.to_drawing_group()` feeds renderer-neutral text recipes into SVG
  and PDF materialization.
- Saved parameters hydrate paragraphs through `Paragraph.create_from_dict()`.
- Text and layout docs describe paragraph parameters as Word-like settings.

Outgoing dependencies:

- Paragraph validation depends only on Python `math.isfinite()`.
- Paragraph layout depends on `TextStyle.font.size` for text measurement and
  line-height estimates.
- Paragraph rendering depends on `DrawingComponentGroup` and `TextDrawing`.
- Flow-document output depends on the public paragraph contract and should not
  duplicate paragraph validation.

Before/after edge changes:

- Before this slice, paragraph positions, tab stops, line spacing, outline
  levels, and several measurements could accept `nan`, `inf`, booleans, or
  malformed serialized values.
- Before `PARAGRAPH-ENUM-SELECTOR-P2`, paragraph alignment, line-spacing rule,
  and tab-stop alignment selectors could accept arbitrary objects whose
  `__str__()` returned a valid enum value.
- Before `PARAGRAPH-STYLES-MAPPING-P2`, direct paragraph hydration could accept
  a malformed non-mapping `styles` override container and fail later through an
  incidental `.get()` error.
- After this slice, public paragraph measurements must be finite numeric values,
  bounded fields enforce their bounds, outline levels reject booleans, and
  serialized hydration uses the same public validation boundaries.
- After `PARAGRAPH-ENUM-SELECTOR-P2`, enum selectors must be real enum members
  or strings before enum-value normalization can run.
- After `PARAGRAPH-STYLES-MAPPING-P2`, optional paragraph style overrides must
  be mappings or `None` before style lookup begins.
- Before `PARAGRAPH-TAB-INDEX-P2`, `Paragraph.remove_tab_stop()` delegated
  directly to Python list deletion, so `True`, `False`, and negative indexes
  could remove real tab stops.
- After `PARAGRAPH-TAB-INDEX-P2`, public tab-stop removal indexes must be
  non-boolean integers within `[0, len(tab_stops))`.
- Before `PARAGRAPH-TAB-STOPS-P2`, direct constructor `tab_stops` could store
  arbitrary objects or strings as public tab-stop state, and serialized
  `tab_stops` could fail through incidental string-index errors during
  hydration.
- After `PARAGRAPH-TAB-STOPS-P2`, direct `tab_stops` must be a sequence of
  `TabStop` values, and serialized `tab_stops` must be a sequence of mapping
  payloads before `TabStop` hydration begins.
- Before `PARAGRAPH-TABSTOP-PAYLOAD-P2`, direct `TabStop.create_from_dict()`
  and paragraph hydration could fail through incidental `TypeError` or raw
  `KeyError` for malformed tab-stop payload roots or missing `position`.
- After `PARAGRAPH-TABSTOP-PAYLOAD-P2`, serialized tab-stop payloads must be
  mappings with a required `position` field before `TabStop` construction
  begins.
- Before `PARAGRAPH-TABSTOP-LEADER-P2`, direct tab-stop construction,
  `Paragraph.add_tab_stop()`, and tab-stop hydration could store arbitrary
  objects as `leader` values even though the public type is `str | None`.
- After `PARAGRAPH-TABSTOP-LEADER-P2`, tab-stop leaders must be strings or
  `None` across direct construction, paragraph insertion, and hydration.
- Before `PARAGRAPH-ROOT-PAYLOAD-P2`, malformed paragraph hydration roots or
  wrapped `Paragraph` payloads failed through incidental Python errors.
- After `PARAGRAPH-ROOT-PAYLOAD-P2`, both wrapped and direct paragraph payloads
  must be mappings before field hydration begins.
- Before `PARAGRAPH-STYLE-PAYLOAD-P2`, malformed paragraph style envelopes
  could fail through incidental indexing errors or reach `TextStyle`
  construction with a non-string name.
- After `PARAGRAPH-STYLE-PAYLOAD-P2`, paragraph style payloads must be mappings
  with a `TextStyle` mapping containing a string `name` before style override
  lookup or `TextStyle` construction.
- Before `PARAGRAPH-REQUIRED-FIELDS-P2`, missing required paragraph hydration
  fields failed through raw `KeyError` lookups.
- After `PARAGRAPH-REQUIRED-FIELDS-P2`, required paragraph hydration fields
  must be present before constructor routing begins, and missing fields fail
  with explicit `ValueError` messages through both direct paragraph hydration
  and `FlowDocument` paragraph-block hydration.
- Before `PARAGRAPH-POSITION-PAYLOAD-P2`, serialized paragraph positions were
  converted with `tuple(position)`, allowing string and bytes payloads such as
  `"12"` and `b"\x01\x02"` to hydrate into numeric coordinates.
- After `PARAGRAPH-POSITION-PAYLOAD-P2`, serialized paragraph positions must
  be explicit two-value list or tuple payloads before numeric coordinate
  coercion begins.
- Negative paragraph origins and negative first-line indents remain valid
  because they are legitimate layout choices.
- No new third-party dependency or dependency edge was introduced.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced.
- Layer check: validation remains in the paragraph authoring model; renderers
  and flow-document exporters consume that contract.
- Coupling check: no renderer-specific validation was added to paragraph logic.
- Redundancy check: shared finite numeric coercion avoids duplicate guards
  across setters.

ADR/rule impact:

- No new ADR is required. This reinforces the dependency-map rule that authoring
  models own their contracts and output layers consume them.

## Domain Definitions

- A paragraph origin is exactly two finite numeric coordinates.
- Paragraph width, hanging indent, left indent, right indent, space before, and
  space after are finite numeric values greater than or equal to zero.
- First-line indent is any finite numeric value, including negative values.
- Line spacing is a finite numeric value greater than zero.
- Outline level is an integer from 0 through 9, excluding booleans.
- Tab-stop position is a finite numeric value greater than or equal to zero.
- Direct tab-stop collections are `None` or non-string sequences whose entries
  are all `TabStop` instances.
- Serialized tab-stop collections are non-string sequences whose entries are
  all mapping payloads.
- Serialized tab-stop payload roots are mappings with a required `position`
  field. Optional `alignment` and `leader` retain existing defaults.
- Tab-stop leader values are strings or `None`.
- Paragraph hydration roots are mappings; wrapped `Paragraph` payload values
  are mappings; direct unwrapped payload mappings remain supported.
- Paragraph style payloads are mappings with a `TextStyle` mapping whose
  `name` value is a string.
- Required paragraph hydration fields are present before constructor routing:
  `text`, `position`, `width`, `alignment`, `first_line_indent`,
  `hanging_indent`, `left_indent`, `right_indent`, `space_before`,
  `space_after`, `line_spacing`, `line_spacing_rule`, `keep_together`,
  `keep_with_next`, `page_break_before`, `widow_control`, and
  `outline_level`.
- Serialized paragraph position payloads are explicit two-value lists or
  tuples; strings, bytes, mappings, objects, and wrong-length sequences are
  rejected before tuple conversion or numeric coercion.
- Tab-stop removal index is a non-boolean integer in the current tab-stop
  range.
- Serialized hydration must reject malformed values instead of silently
  coercing them into valid-looking state.

## Fix Log

- Added shared finite numeric coercion for paragraph measurements.
- Hardened paragraph position, non-negative measurements, line spacing, and
  first-line indent validation.
- Hardened `TabStop` construction and hydration.
- Made `Paragraph.create_from_dict()` route text, booleans, numeric values, and
  outline level through the public constructor validation instead of coercing
  with `str()`, `bool()`, `int()`, or `float()` first.
- Hardened paragraph alignment, line-spacing rule, tab-stop alignment, and
  serialized selector hydration so arbitrary stringifiable objects cannot cross
  the public enum boundary.
- Hardened `Paragraph.create_from_dict(..., styles=...)` so malformed style
  override containers fail at the public boundary.
- Hardened `Paragraph.remove_tab_stop()` so booleans, non-integers, negative
  indexes, and out-of-range indexes fail without mutating tab-stop state.
- Hardened direct and serialized paragraph tab-stop collection boundaries so
  malformed collections or entries fail before public state mutation or
  payload iteration.
- Hardened `TabStop.create_from_dict()` so malformed roots and missing required
  `position` fields fail explicitly before direct or paragraph-mediated
  hydration.
- Hardened tab-stop leader values so direct construction, paragraph insertion,
  and hydration reject non-string, non-`None` leaders.
- Hardened `Paragraph.create_from_dict()` root normalization so malformed roots
  and malformed wrapped payloads fail before paragraph field hydration.
- Hardened paragraph style payload hydration so malformed style roots, wrong
  style kind, malformed `TextStyle` entries, and non-string style names fail
  before override lookup or `TextStyle` construction.
- Hardened required paragraph field hydration so missing required fields fail
  explicitly before raw mapping indexing errors can escape.
- Hardened serialized paragraph position payloads so string, bytes, mapping,
  object, and wrong-length payloads fail before position coercion.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid paragraph geometry | Preserve layout and materialization | PO-PARA-001 | `test_paragraph_contract_remains_live_through_render_and_document_paths` | mutation target |
| Invalid origins | Reject malformed, boolean, and non-finite coordinates | PO-PARA-002 | `test_paragraph_rejects_nonfinite_boolean_and_malformed_positions` | killed |
| Invalid measurements | Reject negative, boolean, non-finite, and non-numeric bounded values | PO-PARA-003 | `test_paragraph_rejects_invalid_numeric_measurements` | killed |
| Line spacing and outline levels | Enforce finite positive spacing and integer outline range | PO-PARA-004 | `test_paragraph_rejects_invalid_line_spacing_and_outline_level` | killed |
| Tab stops | Enforce finite non-negative tab-stop positions and alignment normalization | PO-PARA-005 | `test_tab_stops_reject_invalid_positions` | killed |
| Hydrated payloads | Reject malformed serialized text, booleans, outline level, and tab stops | PO-PARA-006 | `test_paragraph_hydration_uses_public_validation_boundaries` | killed |
| Enum selectors | Accept enum members and real strings; reject arbitrary stringifiable objects | PO-PARA-007 | `test_paragraph_rejects_stringifiable_enum_selectors`, `test_paragraph_hydration_rejects_stringifiable_enum_selectors` | killed |
| Style override map boundary | Reject non-mapping `styles` values before style lookup | PO-PARA-008 | `test_paragraph_hydration_rejects_malformed_style_override_maps` | killed |
| Tab-stop removal index | Reject bool, non-integer, negative, and out-of-range indexes before mutation | PO-PARA-009 | `test_paragraph_remove_tab_stop_rejects_python_index_coercion`, `test_paragraph_remove_tab_stop_preserves_valid_order_and_round_trip` | killed |
| Tab-stop collections | Reject malformed direct and serialized tab-stop collections before public state or hydration iteration | PO-PARA-010 | `test_paragraph_constructor_rejects_malformed_tab_stop_collections`, `test_paragraph_constructor_rejects_non_tab_stop_entries`, `test_paragraph_hydration_rejects_malformed_tab_stop_collections`, `test_paragraph_hydration_rejects_non_mapping_tab_stop_entries` | killed |
| Tab-stop payloads | Reject malformed roots and missing required position fields before tab-stop construction | PO-PARA-011 | `test_tab_stop_factory_rejects_malformed_payload_roots`, `test_tab_stop_factory_rejects_missing_position`, `test_paragraph_hydration_rejects_tab_stop_entries_missing_position` | killed |
| Tab-stop leaders | Reject non-string, non-`None` leader values across direct, insertion, and hydration paths | PO-PARA-012 | `test_tab_stop_rejects_malformed_leaders`, `test_paragraph_add_tab_stop_rejects_malformed_leaders`, `test_paragraph_hydration_rejects_malformed_tab_stop_leaders` | killed |
| Paragraph root payload | Reject malformed hydration roots and wrapped payloads before field access | PO-PARA-013 | `test_paragraph_hydration_rejects_malformed_root_payloads`, `test_paragraph_hydration_rejects_malformed_wrapped_payloads`, `test_paragraph_hydration_preserves_direct_payload_compatibility` | killed |
| Paragraph style payload | Reject malformed style envelopes before style override lookup or style construction | PO-PARA-014 | `test_paragraph_hydration_rejects_malformed_style_payloads`, `test_flow_document_paragraph_hydration_rejects_malformed_style_payloads`, `test_paragraph_hydration_preserves_valid_style_override_lookup` | killed |
| Required paragraph fields | Reject missing required hydration fields before constructor routing | PO-PARA-015 | `test_paragraph_hydration_rejects_missing_required_fields`, `test_flow_document_paragraph_hydration_rejects_missing_required_fields` | killed |
| Paragraph position payload | Reject string, bytes, mapping, object, and wrong-length serialized positions before coordinate coercion | PO-PARA-016 | `test_paragraph_hydration_rejects_malformed_position_payloads`, `test_flow_document_paragraph_hydration_rejects_malformed_position_payloads`, `test_paragraph_hydration_preserves_valid_position_payloads` | killed |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Numeric normalization and enum/range validation are deterministic. | PARAGRAPH-P1 tests |
| Behavioral/condition | yes | PARAGRAPH-P1 defines public paragraph model behavior. | Tests are marked `@pytest.mark.condition("PARAGRAPH-P1")`. |
| Failure-mode | yes | Invalid measurements, payloads, enum selectors, and style override containers must fail before rendering/export. | Invalid boundary, hydration, enum-selector, and style-map tests |
| Integration/live-path | yes | Paragraphs materialize through drawing groups and flow-document output. | Live path test |
| Contract/API compatibility | yes | Existing paragraph layout and serialization behavior must continue passing. | Existing `test_paragraph.py` |
| Property/fuzz | no | This slice covers finite scalar partitions directly. | Not applicable |
| Mutation | yes | Numeric guards and hydration branches are proof-critical. | Mutation result recorded below |
| Security/adversarial | no | No file path, network, subprocess, auth, SQL, template, or active-content surface is added. | Not applicable |
| Performance/resource | no | The change adds constant-time validation. | Code inspection |
| Concurrency/race | no | No shared state, background workers, locks, or temp files are added. | Not applicable |
| Golden artifact/visual | yes | SVG/PDF text-line materialization must stay live and stable. | Component-group type assertions |
| Regression | yes | This closes invalid geometry and malformed serialized payloads leaking into output paths. | PARAGRAPH-P1 tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Removing finite checks must fail invalid-boundary tests.
- Allowing boolean or malformed numeric values must fail failure-mode tests.
- Loosening line-spacing or outline boundaries must fail boundary tests.
- Bypassing public validation during hydration must fail payload tests.
- Reintroducing stringification of enum selectors must fail direct and
  hydration selector-boundary tests.
- Weakening style override map validation must fail malformed-style-map tests.
- Breaking valid paragraph materialization must fail live-path tests.
- Allowing Python bool or negative index coercion through tab-stop removal must
  fail public index-boundary tests.
- Allowing malformed direct or serialized tab-stop collections into paragraph
  state or hydration iteration must fail collection-boundary tests.
- Allowing malformed tab-stop payload roots or missing required fields into
  factory construction must fail tab-stop payload tests.
- Allowing non-string, non-`None` tab-stop leaders into paragraph state must
  fail leader-boundary tests.
- Allowing non-mapping paragraph hydration roots into field hydration must fail
  root-payload tests.
- Allowing malformed paragraph style envelopes into override lookup or style
  construction must fail style-payload tests.
- Allowing missing required paragraph hydration fields to reach raw mapping
  indexing must fail required-field tests.
- Allowing string, bytes, mapping, object, or wrong-length serialized position
  payloads to reach coordinate coercion must fail position-payload tests.

Current result:

- Cosmic Ray 8.4.6, scoped to executable PARAGRAPH-P1 validation and hydration
  rows: 81 work items, 81 killed, and 0 survived. Type-annotation union
  mutations and a keyword-only signature marker mutation were excluded as
  non-executable equivalents.
- Cosmic Ray 8.4.6, scoped to enum selector normalization after
  `PARAGRAPH-ENUM-SELECTOR-P2`: 6 work items, 6 killed, and 0 survived.
- Cosmic Ray 8.4.6, scoped to style override map validation after
  `PARAGRAPH-STYLES-MAPPING-P2`: 6 work items, 6 killed, and 0 survived.
- Cosmic Ray 8.4.6, scoped to tab-stop index validation after
  `PARAGRAPH-TAB-INDEX-P2`: 19 work items, 19 killed, and 0 survived.
- Cosmic Ray 8.4.6, scoped to tab-stop collection validation after
  `PARAGRAPH-TAB-STOPS-P2`: 14 work items, 14 killed, and 0 survived.
- Cosmic Ray 8.4.6, scoped to tab-stop payload validation after
  `PARAGRAPH-TABSTOP-PAYLOAD-P2`: 3 work items, 3 killed, and 0 survived.
- Cosmic Ray 8.4.6, scoped to tab-stop leader validation after
  `PARAGRAPH-TABSTOP-LEADER-P2`: 3 work items, 3 killed, and 0 survived.
- Cosmic Ray 8.4.6, scoped to paragraph root payload validation after
  `PARAGRAPH-ROOT-PAYLOAD-P2`: 5 work items, 5 killed, and 0 survived.
- Cosmic Ray 8.4.6, scoped to paragraph style payload validation after
  `PARAGRAPH-STYLE-PAYLOAD-P2`: 11 work items, 11 killed, and 0 survived.
- Cosmic Ray 8.4.6, scoped to paragraph required-field validation after
  `PARAGRAPH-REQUIRED-FIELDS-P2`: 1 work item, 1 killed, and 0 survived.
- Cosmic Ray 8.4.6, scoped to paragraph position payload validation after
  `PARAGRAPH-POSITION-PAYLOAD-P2`: 14 work items, 14 killed, and 0 survived.
- Valid-paragraph live path gate, scoped to current paragraph line layout,
  renderer-neutral text materialization, SVG/PDF group conversion, flow-document
  paragraph dispatch, and concrete paragraph serializers: 449 work items, 449
  killed, and 0 survived. Enum identity-to-equality equivalents, unclaimed
  fallback constants, and single-line newline fallback mutations were excluded
  from this live-path gate.

## PO-PARA-001: Valid Paragraphs Remain Live

### Claim

Valid paragraphs still lay out into text lines, materialize to renderer-neutral
drawing groups, and export through `FlowDocument`.

### Domain

Finite paragraph origin, valid width and spacing, supported alignment, valid
text style, and paragraph text.

### Proof Method

`Paragraph.layout_lines()` produces exact right-aligned line records with
non-zero indents and spacing, `to_drawing_group()` emits matching `TextDrawing`
recipes, and the live-path test materializes those recipes to SVG and PDF groups
while also exporting through plain text, Markdown, HTML, RTF, and DOCX
flow-document paths.

### Conclusion

Proven when tests and mutation pass for the stated domain.

## PO-PARA-002: Paragraph Origins Are Finite Numeric Coordinates

### Claim

Paragraph positions reject malformed shape, booleans, and non-finite values.

### Domain

All paragraph construction and setter calls using public `position`.

### Proof Method

The position setter checks shape and calls shared finite numeric coercion for
both coordinates. Focused tests exercise invalid construction and a valid
negative origin.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-PARA-003: Paragraph Measurements Respect Bounds

### Claim

Bounded paragraph measurements are finite non-negative numbers, while
first-line indent is finite and may be negative.

### Domain

`width`, `hanging_indent`, `left_indent`, `right_indent`, `space_before`,
`space_after`, and `first_line_indent`.

### Proof Method

Setters share `_coerce_finite_float()` either directly or through
`_validate_non_negative()`. Focused tests cover negative, non-finite, boolean,
non-numeric, zero, positive, and valid negative first-line-indent partitions.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-PARA-004: Line Spacing And Outline Level Are Bounded

### Claim

Line spacing is finite and positive, and outline level is an integer from 0
through 9 excluding booleans.

### Domain

All public construction and setter paths for `line_spacing` and
`outline_level`.

### Proof Method

`line_spacing` uses shared finite coercion with an exclusive zero minimum.
`outline_level` rejects booleans before applying the integer range check.
Focused tests cover lower and upper boundaries.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-PARA-005: Tab Stops Are Valid Positions

### Claim

Tab-stop positions are finite non-negative numbers and string alignments are
normalized to `ParagraphAlignment`.

### Domain

`TabStop` construction, `TabStop.create_from_dict()`, and
`Paragraph.add_tab_stop()`.

### Proof Method

`TabStop.__post_init__()` validates position and normalizes alignment. Focused
tests cover invalid positions, zero position, string alignment normalization,
and paragraph insertion.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-PARA-006: Hydration Cannot Bypass Public Validation

### Claim

Serialized paragraph payloads cannot silently coerce invalid text, boolean,
outline, tab-stop, or measurement values into valid state.

### Domain

`Paragraph.create_from_dict()` payloads for public paragraph parameters.

### Proof Method

Hydration passes payload values into the constructor and `TabStop` factory
without lossy primitive coercion. Focused tests prove malformed text, booleans,
outline level, and tab-stop values are rejected.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-PARA-007: Enum Selectors Are Explicit Values

### Claim

Paragraph enum selectors accept only enum members or real strings, never
arbitrary objects that stringify to supported enum values.

### Domain

`Paragraph.alignment`, `Paragraph.line_spacing_rule`, `TabStop.alignment`,
`Paragraph.add_tab_stop()`, `Paragraph.create_from_dict()`, and
`TabStop.create_from_dict()`.

### Proof Method

Paragraph alignment and line-spacing rule normalization now share explicit
runtime type guards before enum construction. Hydration passes serialized
selector values through those same guards instead of converting them with
`str()`. The focused tests cover direct construction, property assignment,
tab-stop creation, `add_tab_stop()`, paragraph hydration, and tab-stop
hydration.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-PARA-008: Style Overrides Are Mappings

### Claim

`Paragraph.create_from_dict(..., styles=...)` accepts only mappings or `None`
as optional style override containers.

### Domain

Direct public paragraph hydration with caller-supplied style override
containers.

### Proof Method

Hydration normalizes `styles` through `_normalize_text_style_overrides()` before
style lookup. The focused condition test covers malformed object, list, string,
and bytes containers, plus the valid mapping path that reuses the supplied
`TextStyle`.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-PARA-009: Tab-Stop Removal Uses Public Indexes

### Claim

`Paragraph.remove_tab_stop()` rejects booleans, non-integers, negative indexes,
and out-of-range indexes before mutating the tab-stop tuple.

### Domain

All public calls to `Paragraph.remove_tab_stop(index)` over the current
paragraph tab-stop collection.

### Proof Method

`remove_tab_stop()` first normalizes the supplied index through
`_normalize_tab_stop_index()`. The helper rejects booleans before Python can
coerce them to `0` or `1`, rejects non-integers, rejects negative indexes, and
rejects indexes greater than or equal to the current tab-stop count. The
failure-mode test asserts invalid indexes preserve tab-stop state. The valid
path test removes a middle tab stop, round-trips the paragraph through
serialization, and materializes the paragraph through a renderer-neutral
drawing group.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-PARA-010: Tab-Stop Collections Are Explicit

### Claim

Direct paragraph tab-stop collections contain only `TabStop` values, and
serialized tab-stop collections contain only mapping payloads before hydration
iteration begins.

### Domain

`Paragraph(..., tab_stops=...)` and `Paragraph.create_from_dict()` over the
public `tab_stops` collection field.

### Proof Method

The constructor routes `tab_stops` through `_normalize_tab_stops()`, which
accepts `None` as an empty collection, rejects string/bytes and non-sequence
containers, and rejects non-`TabStop` entries before assigning public state.
Hydration routes the serialized field through `_normalize_tab_stop_payloads()`,
which rejects string/bytes and non-sequence containers, and rejects non-mapping
entries before `TabStop.create_from_dict()` is called. Focused tests cover
malformed direct containers, malformed direct entries, malformed serialized
containers, malformed serialized entries, and valid direct tuple preservation.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-PARA-011: Tab-Stop Payloads Are Explicit

### Claim

`TabStop.create_from_dict()` accepts only mapping payloads with a required
`position` field, and paragraph hydration preserves that same tab-stop payload
boundary.

### Domain

Direct public calls to `TabStop.create_from_dict(data)` and
`Paragraph.create_from_dict()` calls whose serialized `tab_stops` collection
contains tab-stop payload entries.

### Proof Method

`TabStop.create_from_dict()` routes its input through `_tab_stop_payload()`,
which rejects non-mapping roots, and `_required_tab_stop_field()`, which rejects
missing `position` before constructing the `TabStop`. Paragraph hydration first
normalizes the tab-stop collection and then calls the same public factory for
each entry. Focused tests cover malformed direct roots, missing direct
`position`, valid minimal payload defaults, and the paragraph hydration path for
missing tab-stop position.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-PARA-012: Tab-Stop Leaders Are Strings Or None

### Claim

Tab-stop leaders are either strings or `None` across direct construction,
paragraph insertion, and serialized hydration.

### Domain

`TabStop(..., leader=...)`, `Paragraph.add_tab_stop(..., leader=...)`, and
`TabStop.create_from_dict()` as called directly or through
`Paragraph.create_from_dict()`.

### Proof Method

`TabStop.__post_init__()` routes `leader` through
`_normalize_tab_stop_leader()`. Because all public paths construct `TabStop`
instances, the same check covers direct construction, paragraph insertion, and
hydration. Focused tests cover invalid integer and object leaders on all three
paths, preservation of prior paragraph state after failed insertion, and valid
string/`None` leaders.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-PARA-013: Paragraph Root Payloads Are Mappings

### Claim

`Paragraph.create_from_dict()` rejects malformed root inputs and malformed
wrapped `Paragraph` payloads before paragraph field hydration begins, while
preserving direct unwrapped payload mapping compatibility.

### Domain

Public paragraph hydration through `Paragraph.create_from_dict(data, styles)`.

### Proof Method

Hydration routes `data` through `_paragraph_payload()`. The helper rejects
non-mapping roots, unwraps the `Paragraph` key when present, rejects malformed
wrapped payloads, and returns direct unwrapped mappings unchanged. Focused tests
cover malformed roots, malformed wrapped payloads, and valid direct payload
round-trip compatibility.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-PARA-014: Paragraph Style Payloads Are Explicit

### Claim

`Paragraph.create_from_dict()` rejects malformed style payload envelopes before
style override lookup or `TextStyle` construction, and the same boundary is
preserved when paragraphs are hydrated through `FlowDocument`.

### Domain

Public paragraph hydration through `Paragraph.create_from_dict()` and
paragraph-block hydration through `FlowDocument.create_from_dict()`.

### Proof Method

Hydration routes the paragraph payload through `_paragraph_style_payload()` and
`_paragraph_style_name()`. The helpers require a `style` field, require a
mapping style payload, require a `TextStyle` mapping rather than another style
kind, and require a string style name before override lookup. Focused tests
cover missing style, malformed style root, wrong style kind, malformed
`TextStyle` entry, missing/non-string name, the FlowDocument dependent path,
and valid override reuse.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-PARA-015: Required Paragraph Fields Are Explicit

### Claim

`Paragraph.create_from_dict()` rejects missing required paragraph fields before
constructor routing begins, and the same field boundary is preserved when
paragraphs are hydrated through `FlowDocument`.

### Domain

Public paragraph hydration through `Paragraph.create_from_dict()` and
paragraph-block hydration through `FlowDocument.create_from_dict()` for required
serialized paragraph fields. Optional `tab_stops` remains optional and defaults
to an empty collection.

### Proof Method

Hydration routes every required serialized paragraph field through
`_required_paragraph_field()`. The helper checks membership before reading the
mapping and raises an explicit `ValueError` naming the missing field. Focused
tests enumerate every required field and exercise the `FlowDocument` dependent
path for a missing paragraph field.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-PARA-016: Paragraph Position Payloads Are Explicit

### Claim

`Paragraph.create_from_dict()` rejects malformed serialized paragraph position
payloads before tuple conversion or numeric coordinate coercion, and the same
boundary is preserved when paragraphs are hydrated through `FlowDocument`.

### Domain

Public paragraph hydration through `Paragraph.create_from_dict()` and
paragraph-block hydration through `FlowDocument.create_from_dict()` for the
serialized `position` field. Valid list and tuple pairs remain supported.

### Proof Method

Hydration routes the required `position` field through
`_paragraph_position_payload()`. The helper accepts only list or tuple payloads
with exactly two entries and returns those two entries for the existing
constructor coordinate validation. Focused tests cover strings, bytes, objects,
mappings, short and long lists, the `FlowDocument` dependent path, and valid
list/tuple pairs.

### Conclusion

Proven for the stated domain after tests and mutation pass.
