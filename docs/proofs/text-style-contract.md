# Text Style Contract Proof Obligations

This note applies the InkGen Definition of Done to the TEXT-STYLE-P1 text style
slice. It focuses on font ownership, color normalization, script flags,
alignment/anchor mapping, finite line spacing, serialized hydration, and live
SVG/PDF text use.

## Scope

The slice covers:

- `TextStyle.__init__()`
- `TextStyle.create_from_dict()`
- `TextStyle.font`
- `TextStyle.color`
- `TextStyle.subscript`
- `TextStyle.superscript`
- `TextStyle.text_align`
- `TextStyle.text_anchor`
- `TextStyle.line_spacing`

Font discovery internals and font metric correctness are out of scope for this
slice.

## Architecture Impact

Affected surface:

- `src/InkGen/style.py`: text style validation and hydration boundaries.
- `tests/test_text_style_contract.py`: TEXT-STYLE-P1 behavioral,
  failure-mode, hydration, and live-path tests.
- `tests/mutation/text_style_cosmic_ray.toml`: scoped mutation gate.
- `tests/mutation/filter_text_style_work_items.py`: proof-critical mutation
  filter.
- `tests/mutation/text_style_live_path_cosmic_ray.toml`: scoped SVG/PDF
  renderer live-path mutation gate.
- `tests/mutation/filter_text_style_live_path_work_items.py`:
  proof-critical renderer live-path mutation filter.

Incoming dependencies:

- `TextComponent`, `TextSVG`, and `TextPDF` consume `TextStyle` for text color,
  alignment, font size, and line spacing.
- Paragraphs, tables, flow documents, CAD zoning, and document outputs carry
  `TextStyle` values through rendering and export paths.
- Saved component and document payloads hydrate text styles through
  `TextStyle.create_from_dict()`.

Outgoing dependencies:

- `TextStyle` depends on `Font` for font family, size, style, and file
  resolution.
- Color validation reuses the proven `Style._is_color()` and
  `Style._get_hex_color()` contract.
- Line spacing reuses the finite non-negative scalar helper introduced for
  drawing styles.
- No new third-party dependency or dependency edge was introduced.

Before/after edge changes:

- Before this slice, invalid `font` values could reserve a global style name
  before failing.
- Before this slice, unsupported `text_align` strings were silently ignored and
  non-string alignment values leaked `AttributeError`.
- Before this slice, `line_spacing` accepted booleans and rejected non-finite
  values through incidental comparison behavior.
- After this slice, invalid fonts fail before name registration, alignments must
  be supported strings, and line spacing must be finite, non-negative, and
  non-boolean.
- Zero line spacing remains valid for compatibility with the prior public
  contract.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced.
- Layer check: validation remains in the text style model; renderers and
  document outputs consume the style contract.
- Coupling check: no renderer-specific dependency was added to `style.py`.
- Redundancy check: line spacing now delegates to the shared scalar helper
  rather than duplicating type and range checks.

ADR/rule impact:

- No new ADR is required. This reinforces the dependency-map rule that authoring
  models own their public input contracts.

## Domain Definitions

- A text style name must remain globally unique under the existing
  `Style.style_names` registry.
- A text style font must be a `Font` instance.
- A text color is a supported named color, a seven-character hex string
  beginning with `#`, or `"none"`.
- Stored text colors are lowercase hex strings or `"none"`.
- `superscript` and `subscript` are booleans only.
- Text alignment accepts `start`/`left`, `end`/`right`, and
  `middle`/`center`, normalizing to `text_align` values
  `start`/`end`/`center` and `text_anchor` values `start`/`end`/`middle`.
- Line spacing is a finite numeric value greater than or equal to zero.
- Booleans are not line-spacing values.

## Fix Log

- Validated `font` before registering the style name.
- Added explicit text alignment type and value validation.
- Routed line spacing through the shared finite non-negative scalar helper.
- Added condition-marked tests for defaults, invalid font handling, color,
  alignment, script flags, line spacing, hydration, and SVG/PDF live paths.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid defaults and updates | Preserve deterministic defaults and normalized public updates | PO-TSTYLE-001 | `test_text_style_defaults_and_valid_updates_are_serialized` | killed |
| Invalid font | Reject non-`Font` values before style-name registration | PO-TSTYLE-002 | `test_text_style_rejects_invalid_font_without_registering_name` | killed |
| Invalid colors/alignment/script flags | Reject malformed colors, unsupported alignment, non-string alignment, and non-boolean script flags | PO-TSTYLE-003 | `test_text_style_rejects_invalid_color_align_and_script_boundaries` | killed |
| Invalid line spacing | Reject booleans, negatives, non-finite values, and non-numeric values while preserving zero | PO-TSTYLE-004 | `test_text_style_rejects_invalid_line_spacing_boundaries` | killed |
| Hydrated payloads | Route serialized values through public validation boundaries | PO-TSTYLE-005 | `test_text_style_hydration_uses_public_validation_boundaries` | killed |
| SVG/PDF live paths | Emit validated text style values into SVG and PDF text output | PO-TSTYLE-006 | `test_text_style_contract_remains_live_in_svg_and_pdf_output` | 157 killed; 6 equivalent survivors |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Font type, alignment, booleans, color, and scalar validation are deterministic. | TEXT-STYLE-P1 tests |
| Behavioral/condition | yes | The slice defines public text-style behavior. | Tests are marked `@pytest.mark.condition("TEXT-STYLE-P1")`. |
| Failure-mode | yes | Invalid font, color, alignment, script flags, and line spacing must fail at the public boundary. | Invalid-boundary tests |
| Integration/live-path | yes | SVG and PDF renderers consume text style values. | Text SVG/PDF live-path test |
| Contract/API compatibility | yes | Existing style, text, SVG, PDF, and document output behavior must continue passing. | Focused gate includes existing tests |
| Property/fuzz | no | The proof partitions finite scalar and finite enum/color cases directly. | Not applicable |
| Mutation | yes | Font, alignment, line-spacing, hydration, and live style use are proof-critical. | Mutation result recorded below |
| Security/adversarial | no | No file path, network, subprocess, auth, SQL, template, font discovery, image, or active-content surface is added. | Not applicable |
| Performance/resource | no | The change adds constant-time validation. | Code inspection |
| Concurrency/race | no | No shared state beyond the pre-existing style-name registry is changed. | Not applicable |
| Golden artifact/visual | yes | SVG/PDF emitted text style values must remain stable. | Exact style/operator assertions |
| Regression | yes | This closes invalid text styles leaking into output paths or global style-name state. | TEXT-STYLE-P1 tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Allowing invalid font values must fail and must not reserve the style name.
- Weakening alignment normalization must fail alignment/anchor tests.
- Weakening boolean script flag guards must fail script flag tests.
- Allowing boolean, negative, non-finite, or non-numeric line spacing must fail
  scalar-boundary tests.
- Bypassing public validation during hydration must fail payload tests.
- Changing SVG/PDF consumption of validated values must fail live-path tests.

Current result:

- Cosmic Ray 8.4.6, scoped to executable TEXT-STYLE-P1 rows: 22 work items,
  22 killed, and 0 survived.
- SVG/PDF live-path continuation:
  `tests/mutation/text_style_live_path_cosmic_ray.toml`, filtered by
  `tests/mutation/filter_text_style_live_path_work_items.py`: 163 work items,
  157 killed, and 6 documented equivalent survivors. Equivalent survivor
  classes:
  - `_pdf_text_aligned_x()` comparison mutations from `==` to `is` are
    equivalent for the public `TextStyle` domain because `TextStyle.text_align`
    normalizes valid inputs to the canonical `start`, `end`, or `center`
    strings consumed by `TextPDF`.
  - `_pdf_text_aligned_x()` comparison mutations from `==` to `<=` are
    equivalent for the normalized text-align domain: `center` still takes the
    center branch, `end` still takes the end branch, and `start` still falls
    through.
  - `TextPDF.generate_pdf()` default `line_spacing` value mutations are
    equivalent for the public `TextPDF` domain because valid `TextStyle`
    instances always expose a validated `line_spacing` attribute.

## PO-TSTYLE-001: Valid Text Styles Normalize Deterministically

### Claim

Valid text styles preserve defaults and normalize public color, alignment, and
line-spacing updates deterministically.

### Domain

Public `TextStyle(...)` construction and setters using a valid `Font`, valid
colors, supported alignments, boolean script flags, and finite non-negative
line spacing.

### Proof Method

Construction validates the font before registration, then routes default values
through public setters. Focused tests check defaults, color normalization,
alignment/anchor mapping, script flags, zero line spacing, and serialized
parameters.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-TSTYLE-002: Invalid Fonts Do Not Reserve Names

### Claim

Non-`Font` values fail before `Style.style_names` is mutated.

### Domain

Public `TextStyle(name, font)` construction.

### Proof Method

`TextStyle.__init__()` checks `isinstance(font, Font)` before calling
`Style.__init__()`. The focused test verifies a failed construction leaves the
name reusable.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-TSTYLE-003: Color, Alignment, And Script Flags Are Explicit

### Claim

Text colors, alignments, and script flags reject unsupported public values and
preserve prior valid state after failed setter calls.

### Domain

`TextStyle.color`, `TextStyle.text_align`, `TextStyle.superscript`, and
`TextStyle.subscript`.

### Proof Method

Color uses the shared color validator, alignment validates string type and
supported aliases, and script flags require `bool`. Focused tests cover valid
aliases, invalid values, and state preservation.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-TSTYLE-004: Line Spacing Is Finite And Non-Negative

### Claim

Line spacing cannot be boolean, negative, non-finite, or non-numeric, while
zero remains valid.

### Domain

`TextStyle.line_spacing` and hydration through `TextStyle.create_from_dict()`.

### Proof Method

Line spacing delegates to `_coerce_nonnegative_float()` and wraps errors with
a text-style-specific message. Focused tests cover valid zero/positive values
and invalid partitions.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-TSTYLE-005: Hydration Cannot Bypass Validation

### Claim

`TextStyle.create_from_dict()` rejects malformed serialized style values through
the same public validation boundaries as direct construction and setters.

### Domain

Serialized `TextStyle.parameters` payloads and manually supplied payloads with
matching shape.

### Proof Method

Hydration constructs a `Font`, then calls the public constructor and public
setters for color, script flags, alignment, and line spacing. Focused tests
cover valid hydration and invalid field payloads.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-TSTYLE-006: Renderers Consume Validated Text Style Values

### Claim

SVG and PDF text output consume validated text-style values.

### Domain

Text SVG and PDF generation using a valid text style with explicit color,
alignment, line spacing, and font size.

### Proof Method

The live-path test renders text through SVG and PDF paths and asserts emitted
SVG style tokens, escaped SVG text, PDF RGB operators, font-size operator, PDF
alignment transforms, PDF line-spacing transforms, and escaped PDF literal
text. The scoped live-path mutation gate targets the current `TextSVG`
style/text output rows and `TextPDF` color, font, alignment, line-spacing, and
literal text rows.

### Conclusion

Proven for the stated domain after focused tests and mutation pass with
documented equivalent survivors.
