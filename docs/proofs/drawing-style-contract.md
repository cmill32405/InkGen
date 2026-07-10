# Drawing Style Contract Proof Obligations

This note applies the InkGen Definition of Done to the STYLE-DRAWING-P1 drawing
style slice. It focuses on color normalization, finite stroke width, bounded
opacity, stroke presentation, serialized hydration, and live SVG/PDF use.

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
- `DrawingStyle.stroke_dasharray`
- `DrawingStyle.stroke_dash_offset`
- `DrawingStyle.stroke_linecap`
- `DrawingStyle.stroke_linejoin`
- `DrawingStyle.stroke_miterlimit`
- Drawing-style validation helpers in `src/InkGen/style.py`

## Architecture Impact

Affected surface:

- `src/InkGen/style.py`: drawing color, stroke width, opacity, and stroke
  presentation validation.
- `tests/test_drawing_style_contract.py`: STYLE-DRAWING-P1 behavioral,
  failure-mode, hydration, and live-path tests.
- `tests/mutation/drawing_style_cosmic_ray.toml`: scoped mutation gate.
- `tests/mutation/filter_drawing_style_work_items.py`: proof-critical mutation
  filter.
- `tests/mutation/drawing_style_stroke_presentation_cosmic_ray.toml`: scoped
  stroke presentation mutation gate.
- `tests/mutation/filter_drawing_style_stroke_presentation_work_items.py`:
  proof-critical stroke presentation mutation filter.

Incoming dependencies:

- Drawing components require `DrawingStyle` instances for line, rectangle,
  polygonal, path, curve, and circle authoring.
- SVG renderers consume `stroke`, `stroke_width`, `fill`, `stroke_opacity`,
  `fill_opacity`, dash arrays, line caps, line joins, and miter limits through
  style strings.
- PDF renderers consume drawing colors, stroke width, opacity, dash arrays,
  line caps, line joins, and miter limits through graphics-state operators and
  ExtGState resources.
- DXF materialization carries drawing recipes through neutral component paths
  and emits drawing stroke color and stroke width as DXF entity true-color and
  lineweight group codes.
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
- Before the stroke-presentation update, drawing styles had no renderer-neutral
  way to express dash arrays, dash phase, line caps, line joins, or miter
  limits.
- After this slice, drawing colors are explicitly validated as supported names,
  seven-character hex strings, or `"none"`.
- After this slice, stroke width is finite and greater than or equal to zero.
- After this slice, opacity is finite, numeric, and in `[0.0, 1.0]`, excluding
  booleans.
- After the stroke-presentation update, dash arrays are finite non-negative
  sequences with at least one positive value when present, dash offset is finite
  and non-negative, line caps and joins are closed enums, and miter limit is
  finite and positive.

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
- Stroke dash arrays are empty or finite non-negative numeric sequences with at
  least one positive value.
- Stroke dash offset is finite and greater than or equal to zero.
- Stroke line cap is `butt`, `round`, or `square`.
- Stroke line join is `miter`, `round`, or `bevel`.
- Stroke miter limit is finite and greater than zero.
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
- Added deterministic PDF ExtGState resources for non-opaque stroke/fill
  opacity when drawing styles render through `DocumentPDF`.
- Added renderer-neutral stroke dash/cap/join/miter fields and live SVG/PDF
  output for those fields.
- Added DXF drawing stroke color and lineweight output for neutral drawing
  entities. DXF solid-fill HATCH output is covered by the DXF renderer proof.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid defaults and explicit values | Preserve default black stroke, no fill, width `0.2`, and opacity `1.0`; normalize explicit named and hex colors | PO-DSTYLE-001 | `test_drawing_style_normalizes_colors_and_preserves_valid_numeric_contract` | killed |
| Invalid colors | Reject unsupported strings, malformed hex strings, empty strings, non-strings, and booleans | PO-DSTYLE-002 | `test_drawing_style_rejects_malformed_colors_without_incidental_errors` | killed |
| Invalid stroke width | Reject booleans, negative, non-finite, and non-numeric values at construction and setter boundaries | PO-DSTYLE-003 | `test_drawing_style_rejects_invalid_stroke_width_and_opacity_boundaries` | killed |
| Invalid opacity | Reject booleans, out-of-range, non-finite, and non-numeric values at construction and setter boundaries | PO-DSTYLE-004 | `test_drawing_style_rejects_invalid_stroke_width_and_opacity_boundaries` | killed |
| Invalid stroke presentation | Reject malformed dash arrays, dash offsets, line caps, line joins, and miter limits | PO-DSTYLE-008 | `test_drawing_style_rejects_invalid_stroke_presentation_boundaries`, `test_stroke_presentation_maps_each_renderer_operator_domain` | 154 killed; 4 equivalent survivors |
| Hydrated payloads | Route serialized values through the public constructor validation | PO-DSTYLE-005 | `test_drawing_style_hydration_uses_public_validation_boundaries` | killed |
| SVG/PDF live paths | Emit validated style values into SVG style strings and PDF graphics operators | PO-DSTYLE-006 | `test_drawing_style_contract_remains_live_in_svg_and_pdf_output` | behavioral evidence |
| PDF stroke/fill opacity | Emit non-opaque drawing style alpha through deterministic ExtGState resources | PO-DSTYLE-007 | `test_document_pdf_emits_extgstate_for_drawing_opacity`, `test_document_pdf_reuses_opacity_extgstate_resources`, `test_document_pdf_separates_stroke_and_fill_opacity_domains`, `test_document_pdf_omits_extgstate_for_opaque_drawings`, `test_pdf_opacity_helpers_validate_boundaries_and_reuse_resources` | 111 killed; 24 equivalent survivors |
| DXF stroke style output | Emit validated stroke color and stroke width as DXF true-color and standard lineweight group codes | PO-DSTYLE-009 | `test_dxf_entities_emit_drawing_style_color_and_lineweight`, `test_dxf_style_lineweight_uses_standard_values_and_disabled_stroke_omits_codes` | DXF-STYLES-P2 gate |

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
- Allowing malformed dash arrays, dash offsets, line caps, line joins, or miter
  limits must fail stroke-presentation boundary tests.
- Bypassing public constructor validation during hydration must fail payload
  tests.
- Changing SVG/PDF consumption of validated values must fail live-path tests.
- Removing PDF ExtGState resource registration, reuse, or `gs` operator
  emission should fail opacity live-path tests.

Current result:

- Cosmic Ray 8.4.6, scoped to executable STYLE-DRAWING-P1 rows: 64 work items,
  64 killed, and 0 survived.
- PDF graphics-state continuation:
  `tests/mutation/pdf_graphics_state_cosmic_ray.toml`, filtered by
  `tests/mutation/filter_pdf_graphics_state_work_items.py`: 135 work items,
  111 killed, and 24 documented equivalent survivors. Equivalent survivor
  classes:
  - Keyword-only `*` separator and default-argument mutations on
    `graphics_state_resource_name()`, `resource_name_for_opacity()`,
    `_style_operators()`, and `_drawing_pdf()` do not affect the proven live
    path because InkGen callers pass explicit keyword arguments.
  - `_style_operators()` fallback opacity and stroke-width default mutations
    are equivalent for the proven `DrawingStyle` domain because constructed
    drawing styles always expose validated `stroke_opacity`, `fill_opacity`,
    and `stroke_width` attributes.
  - `resource_name_for_opacity()` mutating `== 1.0` to `>= 1.0` is equivalent
    because opacity values are validated into the closed interval `[0.0, 1.0]`.
- Stroke presentation continuation:
  `tests/mutation/drawing_style_stroke_presentation_cosmic_ray.toml`, filtered
  by `tests/mutation/filter_drawing_style_stroke_presentation_work_items.py`:
  158 work items, 154 killed, and 4 documented equivalent survivors.
  Equivalent survivor classes:
  - `_coerce_stroke_dasharray()` mutating `all(item == 0.0)` to
    `all(item <= 0.0)` is equivalent because each dash item has already passed
    non-negative finite validation.
  - SVG fill opacity mutating `fill.lower() != "none"` to
    `fill.lower() < "none"` is equivalent for the proven `DrawingStyle` domain
    because `Style._get_hex_color()` normalizes every non-`none` fill to a
    lower-case hex string, and `#...` sorts before `none`.
  - SVG/PDF line-cap checks mutating `linecap != "butt"` to
    `linecap > "butt"` are equivalent for the validated line-cap domain because
    the only non-default values, `round` and `square`, sort after `butt`.

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

## PO-DSTYLE-007: PDF Emits Drawing Opacity ExtGState

### Claim

`DocumentPDF.to_pdf_bytes()` emits deterministic PDF ExtGState resources for
non-opaque `DrawingStyle.stroke_opacity` and `DrawingStyle.fill_opacity`, then
applies the matching `gs` operator before painting drawing primitives.

### Domain

Built-in PDF drawing primitives rendered through `DocumentPDF` with valid
`DrawingStyle` opacity values in `[0.0, 1.0]`.

### Proof Method

`DocumentPDF.to_pdf_bytes()` creates one `_PDFGraphicsStateRegistry` for the
render, passes it through `PDFRenderContext`, writes one ExtGState object for
each distinct stroke/fill opacity tuple, and adds those objects to page
`/Resources`. `_style_operators()` requests a graphics-state resource from the
context only when a relevant stroke or fill opacity is non-opaque, then emits
`/<resource> gs` before color and path-painting operators. Focused tests assert
the ExtGState dictionary, resource section, content-stream operator placement,
resource reuse, and absence of ExtGState resources for fully opaque drawings.

### Counterexamples And Exclusions

Direct primitive `generate_pdf()` calls without a document context still emit
dependency-free standalone operators and do not create page-level ExtGState
resources. Clipping paths, dash arrays, line caps/joins, blend modes, gradients,
patterns, and transparency groups remain separate roadmap items.

### Conclusion

Behavioral tests and scoped mutation prove the PDF document live path for
stroke/fill alpha. Remaining mutation survivors are equivalent for the stated
valid `DrawingStyle` domain.

## PO-DSTYLE-008: Stroke Presentation Is Validated And Rendered

### Claim

`DrawingStyle` validates renderer-neutral stroke dash arrays, dash offsets,
line caps, line joins, and miter limits, then SVG and PDF output consume those
values without changing default output for existing styles.

### Domain

Public `DrawingStyle(...)` construction, setters, serialized hydration, SVG
style output, and PDF drawing operators for valid stroke-presentation values.

### Proof Method

`DrawingStyle` routes dash arrays through `_coerce_stroke_dasharray()`, dash
offset through non-negative finite validation, line caps through
`_coerce_line_cap()`, line joins through `_coerce_line_join()`, and miter limit
through positive finite validation. Serialized hydration accepts older payloads
by defaulting missing stroke-presentation fields to the current behavior. SVG
style output emits `stroke-dasharray`, `stroke-dashoffset`, `stroke-linecap`,
`stroke-linejoin`, and `stroke-miterlimit` only when non-default values are
present. PDF output emits the corresponding `d`, `J`, `j`, and `M` operators
only for non-default values.

Focused tests cover valid defaults, serialization, invalid constructor/setter
boundaries, hydrated values, backward-compatible hydration defaults, exact
SVG/PDF live output, each PDF stroke operator mapping, default omission, and
renderer-helper fallback behavior for legacy style-like objects.

### Counterexamples And Exclusions

DXF output still ignores style-specific stroke presentation. PDF clipping
paths, blend modes, gradients, patterns, and transparency groups remain
separate roadmap items.

### Conclusion

Behavioral tests and scoped mutation prove the public style boundary and
SVG/PDF live paths for the stated domain. The mutation gate ran 158 filtered
work items: 154 killed and 4 equivalent survivors documented above.

## PO-DSTYLE-009: DXF Stroke Style Output

### Claim

DXF output consumes validated `DrawingStyle.stroke` and
`DrawingStyle.stroke_width` values for drawing entities.

### Domain

Renderer-neutral drawing primitives exported through `DXFDocument.add_group()`
and represented as DXF LINE, LWPOLYLINE, and CIRCLE entities.

### Proof Method

`DrawingStyle` already validates stroke color and finite non-negative stroke
width. The DXF renderer consumes those values only from validated drawing
styles attached to neutral drawing primitives. It emits stroke colors as DXF
true-color group code `420` and emits stroke width as group code `370`, snapped
to the nearest standard DXF lineweight.

Focused tests cover live document output for line, rectangle/polyline, and
circle entities, standard lineweight snapping, and disabled-stroke omission.

### Counterexamples And Exclusions

DXF solid-fill HATCH output is covered by `PO-DXF-012` in the DXF renderer
proof. DXF stroke opacity, dash arrays, caps, joins, and miter limits are not
claimed in this obligation.

### Conclusion

Behavioral tests and the DXF-STYLES-P2 mutation gate prove the stated domain
with one equivalent survivor documented in `dxf-renderer-contract.md`.
