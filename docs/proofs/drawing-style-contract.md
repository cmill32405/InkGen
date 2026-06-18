# Drawing Style Contract Proof Obligations

This note applies the InkGen Definition of Done to the STYLE-DRAWING-P1 drawing
style slice. It focuses on color normalization, finite stroke width, bounded
opacity, serialized hydration, and live SVG/PDF use.

## Scope

The slice covers:

- `Style._is_color()`
- `Style._get_hex_color()`
- `DrawingStyle.__init__()`
- `DrawingStyle.create_from_dict()`
- `DrawingStyle.stroke`
- `DrawingStyle.fill`
- `DrawingStyle.stroke_width`
- `DrawingStyle.stroke_opacity`
- `DrawingStyle.fill_opacity`
- Drawing-style validation helpers in `src/InkGen/style.py`

## Architecture Impact

Affected surface:

- `src/InkGen/style.py`: drawing color, stroke width, and opacity validation.
- `tests/test_drawing_style_contract.py`: STYLE-DRAWING-P1 behavioral,
  failure-mode, hydration, and live-path tests.
- `tests/mutation/drawing_style_cosmic_ray.toml`: scoped mutation gate.
- `tests/mutation/filter_drawing_style_work_items.py`: proof-critical mutation
  filter.

Incoming dependencies:

- Drawing components require `DrawingStyle` instances for line, rectangle,
  polygonal, path, curve, and circle authoring.
- SVG renderers consume `stroke`, `stroke_width`, `fill`, `stroke_opacity`, and
  `fill_opacity` through style strings.
- PDF renderers consume drawing colors and stroke width through graphics-state
  operators.
- DXF materialization carries drawing recipes through neutral component paths,
  although DXF output does not currently emit style-specific color or width.
- Saved component payloads hydrate drawing styles through
  `DrawingStyle.create_from_dict()`.

Outgoing dependencies:

- Drawing-style validation depends only on Python `math.isfinite()`.
- Font discovery and `TextStyle` remain out of scope for this slice.
- No new third-party dependency or dependency edge was introduced.

Before/after edge changes:

- Before this slice, malformed color values such as empty strings or non-string
  objects could raise incidental `IndexError` or `AttributeError`.
- Before this slice, stroke width accepted booleans, negative values, `nan`,
  and `inf`.
- Before this slice, opacity accepted booleans and could fail non-numeric values
  through comparison `TypeError` rather than through a shared public boundary.
- After this slice, drawing colors are explicitly validated as supported names,
  seven-character hex strings, or `"none"`.
- After this slice, stroke width is finite and greater than or equal to zero.
- After this slice, opacity is finite, numeric, and in `[0.0, 1.0]`, excluding
  booleans.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced.
- Layer check: validation remains in the style model; SVG and PDF renderers
  consume the style contract.
- Coupling check: no renderer-specific dependency was added to `style.py`.
- Redundancy check: `_get_hex_color()` now trusts `_is_color()` as the single
  validation boundary instead of duplicating hex checks.

ADR/rule impact:

- No new ADR is required. This reinforces the dependency-map rule that authoring
  models own their public input contracts.

## Domain Definitions

- A drawing style name must remain globally unique under the existing
  `Style.style_names` registry.
- A drawing color is a supported named color, a seven-character hex string
  beginning with `#`, or `"none"`.
- Stored hex colors are lowercase.
- Stored named colors are normalized to lowercase hex strings.
- `"none"` remains the paint-disabled sentinel.
- Stroke width is a finite numeric value greater than or equal to zero.
- Stroke and fill opacity are finite numeric values from `0.0` through `1.0`.
- Booleans are not numeric drawing-style values.

## Fix Log

- Added shared finite numeric coercion for drawing-style scalar values.
- Added non-negative finite validation for stroke width.
- Added bounded finite validation for stroke and fill opacity.
- Hardened color validation against non-string and empty values.
- Simplified hex color normalization so `_is_color()` owns the validation
  contract and `_get_hex_color()` only normalizes already-valid colors.
- Added condition-marked contract tests for valid defaults, malformed colors,
  scalar failure modes, hydration, and SVG/PDF live paths.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid defaults and explicit values | Preserve default black stroke, no fill, width `0.2`, and opacity `1.0`; normalize explicit named and hex colors | PO-DSTYLE-001 | `test_drawing_style_normalizes_colors_and_preserves_valid_numeric_contract` | killed |
| Invalid colors | Reject unsupported strings, malformed hex strings, empty strings, non-strings, and booleans | PO-DSTYLE-002 | `test_drawing_style_rejects_malformed_colors_without_incidental_errors` | killed |
| Invalid stroke width | Reject booleans, negative, non-finite, and non-numeric values at construction and setter boundaries | PO-DSTYLE-003 | `test_drawing_style_rejects_invalid_stroke_width_and_opacity_boundaries` | killed |
| Invalid opacity | Reject booleans, out-of-range, non-finite, and non-numeric values at construction and setter boundaries | PO-DSTYLE-004 | `test_drawing_style_rejects_invalid_stroke_width_and_opacity_boundaries` | killed |
| Hydrated payloads | Route serialized values through the public constructor validation | PO-DSTYLE-005 | `test_drawing_style_hydration_uses_public_validation_boundaries` | killed |
| SVG/PDF live paths | Emit validated style values into SVG style strings and PDF graphics operators | PO-DSTYLE-006 | `test_drawing_style_contract_remains_live_in_svg_and_pdf_output` | behavioral evidence |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Color and scalar validation are deterministic. | STYLE-DRAWING-P1 tests |
| Behavioral/condition | yes | The slice defines public drawing-style behavior. | Tests are marked `@pytest.mark.condition("STYLE-DRAWING-P1")`. |
| Failure-mode | yes | Invalid colors and scalar values must fail at the public boundary. | Invalid-boundary tests |
| Integration/live-path | yes | SVG and PDF renderers consume drawing-style values. | Rectangle SVG/PDF live-path test |
| Contract/API compatibility | yes | Existing style, SVG, and PDF behavior must continue passing. | Focused gate includes existing tests |
| Property/fuzz | no | The proof partitions finite scalar and color-format cases directly. | Not applicable |
| Mutation | yes | Color, width, opacity, and hydration guards are proof-critical. | Mutation result recorded below |
| Security/adversarial | no | No file path, network, subprocess, auth, SQL, template, font discovery, image, or active-content surface is added. | Not applicable |
| Performance/resource | no | The change adds constant-time validation. | Code inspection |
| Concurrency/race | no | No shared state beyond the pre-existing style-name registry is changed. | Not applicable |
| Golden artifact/visual | yes | SVG/PDF emitted style values must remain stable. | Exact style/operator assertions |
| Regression | yes | This closes invalid style values leaking into output paths. | STYLE-DRAWING-P1 tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Weakening color shape checks must fail malformed-color tests.
- Changing default style values must fail default-contract tests.
- Allowing boolean, negative, non-finite, or non-numeric stroke widths must fail
  scalar-boundary tests.
- Allowing boolean, out-of-range, non-finite, or non-numeric opacity values must
  fail scalar-boundary tests.
- Bypassing public constructor validation during hydration must fail payload
  tests.
- Changing SVG/PDF consumption of validated values must fail live-path tests.

Current result:

- Cosmic Ray 8.4.6, scoped to executable STYLE-DRAWING-P1 rows: 64 work items,
  64 killed, and 0 survived.

## PO-DSTYLE-001: Valid Drawing Styles Normalize Deterministically

### Claim

Valid drawing styles preserve defaults, normalize named colors to lowercase hex,
normalize hex colors to lowercase, and preserve finite scalar values.

### Domain

Public `DrawingStyle(...)` construction and scalar setters using supported
colors, finite non-negative stroke width, and finite opacity values in
`[0.0, 1.0]`.

### Proof Method

Construction routes scalars through shared finite validators and routes color
values through `_is_color()` plus `_get_hex_color()`. The focused test checks
default values, explicit zero boundary values, named colors, hex colors, setter
updates, and serialized parameters.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-DSTYLE-002: Malformed Colors Fail Explicitly

### Claim

Malformed color values fail with `ValueError` at constructor and setter
boundaries without incidental indexing or attribute errors.

### Domain

Public `stroke` and `fill` inputs for construction and setters.

### Proof Method

`_is_color()` returns `False` for non-strings and validates shape before reading
hex characters. Constructor and setters convert `False` into `ValueError`.
Focused tests cover empty strings, malformed hex strings, non-`#` seven-character
strings, non-strings, and booleans.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-DSTYLE-003: Stroke Width Is Finite And Non-Negative

### Claim

Stroke width cannot be boolean, negative, non-finite, or non-numeric.

### Domain

`DrawingStyle.__init__()`, `DrawingStyle.stroke_width`, and hydration through
`DrawingStyle.create_from_dict()`.

### Proof Method

All stroke-width entry points route through `_coerce_nonnegative_float()`.
Focused tests cover invalid construction, invalid setters with state
preservation, valid zero, and valid positive values.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-DSTYLE-004: Opacity Is Finite And Bounded

### Claim

Stroke and fill opacity are finite numeric values in `[0.0, 1.0]`, excluding
booleans.

### Domain

`DrawingStyle.__init__()`, `DrawingStyle.stroke_opacity`,
`DrawingStyle.fill_opacity`, and hydration through
`DrawingStyle.create_from_dict()`.

### Proof Method

All opacity entry points route through `_coerce_opacity()`. Focused tests cover
valid inclusive endpoints, out-of-range values, non-finite values, booleans,
non-numeric values, and setter state preservation.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-DSTYLE-005: Hydration Cannot Bypass Validation

### Claim

`DrawingStyle.create_from_dict()` rejects malformed serialized style values
through the same public validation boundaries as direct construction.

### Domain

Serialized `DrawingStyle.parameters` payloads and manually supplied payloads
with matching shape.

### Proof Method

Hydration calls the public constructor with serialized values. Focused tests
cover valid hydration and invalid color, stroke-width, and opacity payloads.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-DSTYLE-006: Renderers Consume Validated Style Values

### Claim

SVG and PDF drawing output consume the validated drawing-style values.

### Domain

Rectangle SVG and PDF generation using a valid drawing style with explicit
stroke, fill, stroke width, stroke opacity, and fill opacity.

### Proof Method

The live-path test renders a rectangle through SVG and PDF paths and asserts
the emitted SVG style tokens and PDF graphics operators.

### Conclusion

Supported by behavioral evidence for the stated domain.
