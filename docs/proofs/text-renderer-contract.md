# Text Renderer Contract Proof Obligations

This note applies the InkGen Definition of Done to the TEXT-P1 text
renderer-contract slice. It focuses on finite text-anchor validation and
preserving text, position, and style through SVG, PDF, neutral drawing recipes,
and DXF export.

## Scope

The slice covers text validation and geometry access in
`src/InkGen/component.py`, SVG serialization in `src/InkGen/svg_generator.py`,
PDF serialization in `src/InkGen/pdf_generator.py`, renderer-neutral
materialization in `src/InkGen/drawing_components.py`, and DXF export in
`src/InkGen/dxf_generator.py`.

The public behavior under review is:

- `TextComponent.__init__()`
- `TextComponent.text`
- `TextComponent.position`
- `TextComponent.points`
- `TextComponent.bbox`
- `TextComponent.convex_hull`
- `TextSVG.generate_svg()`
- `TextPDF.generate_pdf()`
- `TextDrawing.to_component(OutputFormat.SVG/PDF)`
- `DXFDocument.add_group()` for `TextDrawing`

## Architecture Impact

Affected surface:

- `src/InkGen/component.py`: finite numeric text-position validation.
- `src/InkGen/svg_generator.py`: concrete SVG text output.
- `src/InkGen/pdf_generator.py`: concrete PDF text object output.
- `src/InkGen/drawing_components.py`: neutral text recipe materialization.
- `src/InkGen/dxf_generator.py`: DXF `TEXT` entity output.
- `tests/test_text_contract.py`: validation, renderer, materialization, and
  live DXF evidence.

Incoming dependencies:

- Label, text fitting, mask, and extraction-fixture paths rely on text
  positions, bbox, and convex hull being usable geometry.
- SVG/PDF fixture generation relies on deterministic text escaping and anchor
  coordinates.
- DXF export relies on neutral text recipes becoming `TEXT` entities.

Outgoing dependencies:

- Text position validation depends on Python `math.isfinite()`.
- Text outline geometry depends on the existing font outline helper and the
  fallback outline path.
- SVG output depends on XML escaping and shared text-style serialization.
- PDF output depends on PDF string escaping, `_number()`, and color component
  parsing.
- DXF output depends on `DXFRenderContext.point()` and `_text_entity()`.
- Neutral materialization depends on `normalize_output_format()` and lazy
  concrete renderer imports.

Before/after edge changes:

- Before this slice, `TextComponent.position` accepted values that could be
  coerced into `nan`, `inf`, or boolean coordinates.
- After this slice, malformed, boolean, and non-finite text positions fail at
  construction or setter boundaries.
- Text remains allowed at negative coordinates; this preserves existing text
  placement semantics and differs from the shared drawing-line boundary.
- No new dependency edge or third-party dependency was introduced.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced. Neutral drawing classes still lazy-import
  concrete renderers only inside `to_component()`.
- Layer check: text-anchor validity remains in the shared component layer,
  while renderers only serialize valid text geometry.
- Coupling check: SVG/PDF/DXF share the text component contract without sharing
  renderer-specific syntax.
- Redundancy check: no duplicate text-position validation was added to
  renderers.

Evidence source and freshness:

- Source-backed: `component.py`, `svg_generator.py`, `pdf_generator.py`,
  `drawing_components.py`, `dxf_generator.py`, and adjacent tests were read
  before editing.
- Test-backed: focused tests in `test_text_contract.py` exercise valid text,
  invalid position failures, SVG/PDF exact output, serialization, neutral
  materialization, defensive PDF defaults, and live DXF export.
- No architecture claim in this note relies only on stale memory.

ADR/rule impact:

- No new ADR is required because the slice preserves the existing dependency
  map and dependency-free renderer policy.
- A future change that forbids negative text coordinates should record an ADR
  because it changes text placement semantics.

## Domain Definitions

- A valid text anchor is a two-value tuple or list.
- Each coordinate value must be numeric, finite, and not boolean.
- Negative text coordinates are valid.
- Text values accepted by `TextComponent.text` are converted to strings.
- SVG output must XML-escape text content.
- PDF output must escape literal-string controls.
- DXF output is a `TEXT` entity and normalizes embedded newlines to spaces.

## Fix Log

- `TextComponent.position` now validates shape, numeric coercion, boolean
  rejection, and finite coordinates before storing the text anchor.
- The position setter uses the same validation path as construction.
- `TextPDF.generate_pdf()` is proven for exact escaped output and its defensive
  black/10-point fallback constants.
- DXF text export is proven to emit a `0/TEXT` entity pair and apply optional
  canvas-height Y inversion.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid text anchor | Preserve text, position, bbox, and hull | PO-TEXT-001 | `test_text_component_preserves_text_position_and_outline` | killed/equivalent |
| Malformed, boolean, or non-finite anchor | Reject at boundary | PO-TEXT-002 | `test_text_component_rejects_invalid_position_boundaries` | killed/equivalent |
| Negative text anchor | Preserve as valid text placement | PO-TEXT-001 | valid-position tests and policy note | killed/equivalent |
| SVG output | Emit exact escaped text element | PO-TEXT-003 | `test_text_svg_emits_exact_escaped_text` | killed/equivalent |
| PDF output | Emit exact escaped text object | PO-TEXT-004 | `test_text_pdf_emits_exact_text_object_and_escapes_string` | killed/equivalent |
| PDF defensive defaults | Use black and 10-point defaults for incomplete internals | PO-TEXT-004 | `test_text_pdf_uses_black_and_ten_point_defensive_defaults` | killed |
| Serialization | Preserve parameters round trip | PO-TEXT-005 | `test_text_primitives_round_trip_parameters` | killed/equivalent |
| Neutral materialization | Materialize to `TextSVG`/`TextPDF` | PO-TEXT-006 | `test_text_drawing_materializes_svg_and_pdf_components` | killed/equivalent |
| DXF output | Emit `TEXT` entity with transformed anchor | PO-TEXT-007 | `test_dxf_text_drawing_exports_text_entity_with_canvas_transform` | killed/equivalent |
| Multiline text layout, rich text runs, and font embedding | Excluded from proven domain | Explicit exclusion | Not applicable | Out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Validation and geometry access are deterministic. | TEXT-P1 tests named above |
| Behavioral/condition | yes | TEXT-P1 defines text behavior across validation and renderers. | Tests are marked `@pytest.mark.condition("TEXT-P1")`. |
| Failure-mode | yes | Invalid text anchors must fail before rendering. | Invalid-boundary test |
| Integration/live-path | yes | DXF proof exercises `DXFDocument.add_group()`. | DXF test |
| Contract/API compatibility | yes | Valid text preserves anchor and serialization. | Geometry and round-trip tests |
| Property/fuzz | limited | This slice proves representative text-anchor partitions. | Edge matrix above |
| Mutation | yes | Validation, output paths, materialization, and DXF entity generation are proof-critical. | Mutation result recorded below |
| Security/adversarial | no | The slice adds no file path, network, subprocess, auth, secrets, SQL, template, deserialization, or active-content surface. | Not applicable |
| Performance/resource | no | The slice adds constant-time validation over two coordinates. | Code inspection |
| Concurrency/race | no | The slice adds no shared mutable global state, workers, sessions, locks, queues, or temp-file coordination. | Not applicable |
| Golden artifact/visual | yes | SVG/PDF/DXF text geometry must be stable enough for synthetic fixtures. | Exact output tests |
| Regression | yes | This closes invalid text-position acceptance at the component boundary. | Failure-mode tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Weakening text-position shape, boolean, or finite validation should fail
  invalid-input tests.
- Changing SVG escaping, style, anchor, or emitted text should fail exact output
  tests.
- Changing PDF color, font-size, matrix, escaping, or text operators should fail
  exact output tests.
- Redirecting `TextDrawing.to_component()` should fail materialization tests.
- Changing DXF entity type, layer, anchor codes, z coordinate, text height, text
  value, or Y inversion should fail live DXF tests.

Current result:

- Cosmic Ray 8.4.6, scoped to text validation, SVG/PDF generation, neutral
  materialization, and DXF export: 113 work items, 111 killed, and 2 survived.
- The mutation run exposed and the tests closed real gaps for defensive PDF
  fallback constants.
- Equivalent survivors:
  - `target is OutputFormat.SVG` changed to `target == OutputFormat.SVG`.
    `normalize_output_format()` returns an `OutputFormat` member, so identity
    and equality are equivalent for this enum-domain comparison.
  - `target is OutputFormat.SVG` changed to `target >= OutputFormat.SVG`.
    `OutputFormat.SVG` is the first supported string enum value in this
    normalized two-format branch; existing SVG and PDF materialization
    assertions cover the reachable outcomes.

## PO-TEXT-001: Valid Text Geometry Is Preserved

### Claim

Valid text values and anchors preserve text, position, bbox, points, and convex
hull geometry.

### Domain

All `TextComponent` instances constructed with accepted text values and finite
numeric two-coordinate anchors.

### Proof Method

`text` converts accepted scalar values to strings. `_coerce_position()`
normalizes the anchor to a finite float pair. `points`, `bbox`, and
`convex_hull` read from the computed or fallback text outline.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-TEXT-002: Invalid Text Anchors Fail At Boundary

### Claim

Invalid text anchors raise `ValueError` or `TypeError` at construction or
setter time.

### Domain

Malformed, nonnumeric, non-finite, and boolean position inputs.

### Proof Method

`_coerce_position()` rejects malformed values, boolean coordinates, failed
numeric coercions, and non-finite values. Construction and setter paths both use
the same validation.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-TEXT-003: SVG Emits Escaped Text

### Claim

`TextSVG.generate_svg()` emits escaped text content with deterministic style and
anchor fields.

### Domain

All `TextSVG` instances with valid text anchors and serializable text styles.

### Proof Method

The exact SVG output assertion checks font style, font size, font family, fill,
anchor fields, id fields, coordinates, and XML-escaped text content.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-TEXT-004: PDF Emits Escaped Text Object

### Claim

`TextPDF.generate_pdf()` emits deterministic PDF text operators, escaped literal
string content, color, font size, and text matrix.

### Domain

All `TextPDF` instances with valid text anchors and text styles. The defensive
default branch is also proven for incomplete style internals.

### Proof Method

The exact PDF output assertion checks graphics-state save/restore, color,
`BT`/`ET`, font selection, text matrix, escaped literal text, and `Tj`.
The fallback assertion checks black color and 10-point defaults when style
internals are incomplete.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-TEXT-005: Serialization Preserves Text Parameters

### Claim

SVG and PDF text primitives recreate from their own serialized parameters.

### Domain

All `TextSVG` and `TextPDF` instances with valid anchors and serializable
styles.

### Proof Method

`parameters` stores text, position, and style. `create_from_dict()` reconstructs
position and style before calling the class constructor.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-TEXT-006: Neutral Text Materializes To SVG And PDF

### Claim

`TextDrawing.to_component()` preserves text and anchor when materializing to SVG
or PDF components.

### Domain

All `TextDrawing` instances with supported output formats `SVG` and `PDF`.

### Proof Method

`TextDrawing.to_component()` normalizes the requested format. SVG returns
`TextSVG(self.text, self.position, self.style)`. PDF returns
`TextPDF(self.text, self.position, self.style)`.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-TEXT-007: DXF Exports Text Entity

### Claim

DXF export for a neutral `TextDrawing` emits one `TEXT` entity with transformed
anchor coordinates, text height, layer, and normalized text content.

### Domain

All valid neutral `TextDrawing` instances exported through
`DXFDocument.add_group()`.

### Proof Method

`DXFDocument.add_group()` iterates over neutral components.
`_component_to_entities()` matches `TextDrawing` and returns
`_text_entity(component, context)`.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## Current Slice Decision

The slice chooses fail-fast validation for non-finite text anchors while
preserving negative text coordinates. That keeps existing text placement
semantics intact and prevents invalid geometry from reaching SVG, PDF, DXF, or
downstream parser fixtures.
