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

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid paragraph geometry | Preserve layout and materialization | PO-PARA-001 | `test_paragraph_contract_remains_live_through_render_and_document_paths` | behavioral evidence |
| Invalid origins | Reject malformed, boolean, and non-finite coordinates | PO-PARA-002 | `test_paragraph_rejects_nonfinite_boolean_and_malformed_positions` | killed |
| Invalid measurements | Reject negative, boolean, non-finite, and non-numeric bounded values | PO-PARA-003 | `test_paragraph_rejects_invalid_numeric_measurements` | killed |
| Line spacing and outline levels | Enforce finite positive spacing and integer outline range | PO-PARA-004 | `test_paragraph_rejects_invalid_line_spacing_and_outline_level` | killed |
| Tab stops | Enforce finite non-negative tab-stop positions and alignment normalization | PO-PARA-005 | `test_tab_stops_reject_invalid_positions` | killed |
| Hydrated payloads | Reject malformed serialized text, booleans, outline level, and tab stops | PO-PARA-006 | `test_paragraph_hydration_uses_public_validation_boundaries` | killed |
| Enum selectors | Accept enum members and real strings; reject arbitrary stringifiable objects | PO-PARA-007 | `test_paragraph_rejects_stringifiable_enum_selectors`, `test_paragraph_hydration_rejects_stringifiable_enum_selectors` | killed |
| Style override map boundary | Reject non-mapping `styles` values before style lookup | PO-PARA-008 | `test_paragraph_hydration_rejects_malformed_style_override_maps` | killed |
| Tab-stop removal index | Reject bool, non-integer, negative, and out-of-range indexes before mutation | PO-PARA-009 | `test_paragraph_remove_tab_stop_rejects_python_index_coercion`, `test_paragraph_remove_tab_stop_preserves_valid_order_and_round_trip` | killed |
| Tab-stop collections | Reject malformed direct and serialized tab-stop collections before public state or hydration iteration | PO-PARA-010 | `test_paragraph_constructor_rejects_malformed_tab_stop_collections`, `test_paragraph_constructor_rejects_non_tab_stop_entries`, `test_paragraph_hydration_rejects_malformed_tab_stop_collections`, `test_paragraph_hydration_rejects_non_mapping_tab_stop_entries` | killed |

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

## PO-PARA-001: Valid Paragraphs Remain Live

### Claim

Valid paragraphs still lay out into text lines, materialize to renderer-neutral
drawing groups, and export through `FlowDocument`.

### Domain

Finite paragraph origin, valid width and spacing, supported alignment, valid
text style, and paragraph text.

### Proof Method

`Paragraph.layout_lines()` produces line records, `to_drawing_group()` emits
`TextDrawing` recipes, and the live-path test materializes those recipes to SVG
and PDF groups while also exporting through HTML and plain-text flow-document
paths.

### Conclusion

Supported by behavioral evidence for the stated domain.

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
