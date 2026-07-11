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
- `PDFRenderContext.font_resource_name()`
- `DocumentPDF.to_pdf_bytes()`
- `TextDrawing.__post_init__()`
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
- `tests/mutation/pdf_text_alignment_cosmic_ray.toml`: scoped mutation gate for
  TEXT-PDF-ALIGN-P2.
- `tests/mutation/filter_pdf_text_alignment_work_items.py`: proof-critical
  mutation filter for PDF text-line alignment.

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
- PDF document output depends on `_PDFFontRegistry` to assign deterministic
  standard or embedded font resources after page text content is rendered.
- DXF output depends on `DXFRenderContext.point()` and `_text_entity()`.
- Neutral materialization depends on `normalize_output_format()` and lazy
  concrete renderer imports.

Before/after edge changes:

- Before this slice, `TextComponent.position` accepted values that could be
  coerced into `nan`, `inf`, or boolean coordinates.
- After this slice, malformed, boolean, and non-finite text positions fail at
  construction or setter boundaries.
- The `TEXT-DRAWING-TEXT-P2` continuation found that `TextDrawing` stored
  arbitrary non-scalar text until SVG/PDF materialization failed, and
  `FlowDocument.create_from_dict()` could hydrate malformed serialized
  `TextDrawing.text` payloads into public neutral drawing state.
- After `TEXT-DRAWING-TEXT-P2`, `TextDrawing` normalizes accepted scalar text to
  strings at construction and rejects non-scalar values before materialization
  or flow-document hydration can expose malformed state.
- The `TEXT-DRAWING-POSITION-P2` continuation found that `TextDrawing` accepted
  malformed or non-finite neutral anchors until SVG/PDF materialization, DOCX
  VML output, DXF export, or FlowDocument hydration consumed the bad state.
- After `TEXT-DRAWING-POSITION-P2`, `TextDrawing` routes its neutral anchor
  through the same finite point-pair boundary used by other neutral drawing
  primitives before any public state is exposed.
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
- `TextDrawing.text` accepts the same scalar text domain as `TextComponent`
  (`str`, `int`, `float`, `complex`, and `bool`) and stores the normalized
  string immediately.
- Non-scalar `TextDrawing.text` values such as arbitrary objects, lists,
  mappings, and `None` are invalid and must fail at the neutral recipe
  boundary.
- `TextDrawing.position` must be a two-value numeric, finite, non-boolean point
  pair.
- Negative `TextDrawing.position` coordinates remain valid text placement.
- SVG output must XML-escape text content.
- PDF output must escape literal-string controls.
- DXF output is a `TEXT` entity and normalizes embedded newlines to spaces.

## Fix Log

- `TextComponent.position` now validates shape, numeric coercion, boolean
  rejection, and finite coordinates before storing the text anchor.
- The position setter uses the same validation path as construction.
- `TextPDF.generate_pdf()` is proven for exact escaped output and its defensive
  black/10-point fallback constants.
- `TextPDF.generate_pdf()` now asks `PDFRenderContext` for its font resource
  when rendered inside `DocumentPDF`.
- `TextPDF.generate_pdf()` now normalizes CRLF/CR/LF line breaks and emits one
  positioned PDF text-showing operation per line using `TextStyle.line_spacing`.
- `TextPDF.generate_pdf()` now applies `TextStyle.text_align` to each emitted
  PDF text line using InkGen's deterministic text-width estimate.
- `DocumentPDF.to_pdf_bytes()` now emits built-in PDF Standard font resources
  for Helvetica, Times, and Courier family classes, including bold and italic
  variants, instead of always binding `/F1` to Helvetica.
- `DocumentPDF.to_pdf_bytes()` now embeds named installed TrueType/OpenType font
  files with WinAnsi widths, font descriptors, and deterministic resource reuse.
- `DocumentPDF.to_pdf_bytes()` now attaches deterministic `/ToUnicode` CMaps to
  used Standard 14 and embedded WinAnsi font resources for printable ASCII text
  extraction.
- DXF text export is proven to emit a `0/TEXT` entity pair and apply optional
  canvas-height Y inversion.
- `TextDrawing.__post_init__()` now stores normalized scalar text strings and
  rejects non-scalar payloads before direct materialization or
  `FlowDocument.create_from_dict()` can hold malformed neutral text state.
- `TextDrawing.__post_init__()` now normalizes finite text anchors and rejects
  malformed, boolean, or non-finite anchors before materialization or
  `FlowDocument.create_from_dict()` can expose malformed neutral geometry.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid text anchor | Preserve text, position, bbox, and hull | PO-TEXT-001 | `test_text_component_preserves_text_position_and_outline` | killed/equivalent |
| Malformed, boolean, or non-finite anchor | Reject at boundary | PO-TEXT-002 | `test_text_component_rejects_invalid_position_boundaries` | killed/equivalent |
| Negative text anchor | Preserve as valid text placement | PO-TEXT-001 | valid-position tests and policy note | killed/equivalent |
| SVG output | Emit exact escaped text element | PO-TEXT-003 | `test_text_svg_emits_exact_escaped_text` | killed/equivalent |
| PDF output | Emit exact escaped text object and one positioned text operation per normalized line | PO-TEXT-004 | `test_text_pdf_emits_exact_text_object_and_escapes_string`, `test_text_pdf_multiline_uses_line_spacing_and_normalizes_line_breaks` | killed/equivalent |
| PDF text alignment | Apply start, center, and end alignment to each normalized PDF text line | PO-TEXT-013 | `test_text_pdf_applies_alignment_to_each_line` | pass with equivalent survivors |
| PDF defensive defaults | Use black and 10-point defaults for incomplete internals | PO-TEXT-004 | `test_text_pdf_uses_black_and_ten_point_defensive_defaults` | killed |
| PDF Standard font resources | Map built-in family/style/weight classes to deterministic page resources | PO-TEXT-010 | `test_document_pdf_maps_text_styles_to_standard_font_resources`, `test_document_pdf_maps_standard_font_variants`, `test_document_pdf_numeric_weight_threshold_keeps_599_regular`, `test_document_pdf_empty_page_has_no_font_resource_dictionary` | killed |
| PDF embedded named font resources | Embed named installed fonts with widths, descriptors, font-file streams, and deterministic reuse | PO-TEXT-011 | `test_document_pdf_embeds_named_installed_font_resources`, `test_document_pdf_reuses_embedded_font_resources_across_sizes`, `test_pdf_embedded_font_helpers_cover_missing_glyphs_and_open_type_streams`, `test_pdf_embedded_font_lookup_falls_back_for_missing_font_files`, `test_font_preserves_requested_family_for_renderer_policy` | killed/equivalent |
| PDF WinAnsi ToUnicode maps | Attach deterministic CMaps to used Standard 14 and embedded font dictionaries | PO-TEXT-012 | `test_document_pdf_standard_fonts_emit_tounicode_cmaps`, `test_document_pdf_maps_text_styles_to_standard_font_resources`, `test_document_pdf_embeds_named_installed_font_resources` | killed |
| Serialization | Preserve parameters round trip | PO-TEXT-005 | `test_text_primitives_round_trip_parameters` | killed/equivalent |
| Neutral materialization | Materialize to `TextSVG`/`TextPDF` | PO-TEXT-006 | `test_text_drawing_materializes_svg_and_pdf_components` | killed/equivalent |
| Neutral scalar text payloads | Normalize to strings before public state is exposed | PO-TEXT-008 | `test_text_drawing_normalizes_scalar_text_before_materialization` | killed |
| Non-scalar neutral text payloads | Reject at `TextDrawing` construction and FlowDocument hydration | PO-TEXT-008 | `test_text_drawing_rejects_non_scalar_text_payloads`, `test_flow_document_hydration_rejects_malformed_text_drawing_payloads` | killed |
| Neutral text anchors | Normalize finite pairs and reject malformed anchors before public state is exposed | PO-TEXT-009 | `test_text_drawing_normalizes_valid_position_before_materialization`, `test_text_drawing_rejects_malformed_positions_before_materialization`, `test_flow_document_hydration_rejects_malformed_text_drawing_positions` | killed/equivalent |
| DXF output | Emit `TEXT` entity with transformed anchor | PO-TEXT-007 | `test_dxf_text_drawing_exports_text_entity_with_canvas_transform` | killed/equivalent |
| Rich text runs, Unicode/CID font encoding, complex shaping in PDF operators, and glyph subsetting | Excluded from proven domain | Explicit exclusion | Not applicable | Out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Validation and geometry access are deterministic. | TEXT-P1 tests named above |
| Behavioral/condition | yes | TEXT-P1 defines text behavior across validation and renderers; TEXT-PDF-ALIGN-P2 defines PDF text-line alignment behavior. | Tests are marked `@pytest.mark.condition("TEXT-P1")` and `@pytest.mark.condition("TEXT-PDF-ALIGN-P2")`. |
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
- Changing PDF color, font-size, matrix, escaping, font resource selection, or
  text operators should fail exact output tests.
- Changing PDF line-break normalization, line-spacing offsets, or per-line
  escaping should fail multiline PDF output tests.
- Changing PDF text-line width or alignment-origin calculation should fail
  TEXT-PDF-ALIGN-P2 exact PDF matrix tests.
- Removing or misrouting PDF `/ToUnicode` CMaps should fail font-resource
  extraction-map tests.
- Redirecting `TextDrawing.to_component()` should fail materialization tests.
- Weakening `TextDrawing` text coercion or non-scalar rejection should fail
  direct neutral text and FlowDocument hydration tests.
- Weakening `TextDrawing` position normalization, boolean rejection, finite
  checks, or hydration boundaries should fail direct neutral text-anchor and
  FlowDocument hydration tests.
- Changing DXF entity type, layer, anchor codes, z coordinate, text height, text
  value, or Y inversion should fail live DXF tests.

Current result:

- Cosmic Ray 8.4.6, scoped to text validation, SVG/PDF generation, neutral
  materialization, and DXF export: 113 work items, 111 killed, and 2 survived.
- The mutation run exposed and the tests closed real gaps for defensive PDF
  fallback constants.
- PDF Standard font resource mutation slice:
  `tests/mutation/pdf_standard_font_cosmic_ray.toml`, filtered by
  `tests/mutation/filter_pdf_standard_font_work_items.py`: 37 work items, 37
  killed, and 0 survived.
- PDF embedded font continuation uses the same config and filter expanded to
  `_PDFFontResource`, `_PDFFontRegistry`, embedded-font helpers, font object
  emission, and the text content path: 87 work items, 61 killed, 17 survived as
  documented equivalents, and 9 incompetent mutants.
- PDF ToUnicode continuation:
  `tests/mutation/pdf_tounicode_cosmic_ray.toml`, filtered by
  `tests/mutation/filter_pdf_tounicode_work_items.py`: 50 work items, 50
  killed, and 0 survived.
- PDF multiline text continuation:
  `tests/mutation/pdf_text_multiline_cosmic_ray.toml`, filtered by
  `tests/mutation/filter_pdf_text_multiline_work_items.py`: 4,509 raw work
  items filtered to 15 proof-critical items; 13 killed and 2 survived as
  documented equivalents.
- Equivalent survivor classes:
  - Embedded-font fallback exception replacements still return `None` for the
    tested missing-file and invalid-font paths, preserving Standard 14 fallback.
  - Real-font metadata branches for positive units-per-em, postscript-name
    presence, OS/2 table presence, and `post` table presence are equivalent for
    the installed DejaVu font fixture.
  - Embedded resource key fallback using `font_file or base_font` mutates to an
    equivalent key for resources with both non-empty values in the tested
    domain.
  - Font-file subtype comparisons for the literal `FontFile3` are equivalent
    for the tested TrueType and OpenType resource objects.
  - `TextPDF.generate_pdf()` fallback `line_spacing` default mutations from
    `1.0` to `0.0` or `2.0` are equivalent for the valid `TextStyle` domain
    because `TextStyle` construction always exposes a validated
    `line_spacing` attribute.
- Incompetent mutants were invalid boolean/exception/subtype mutations that
  could not run as viable behavioral alternatives.
- Equivalent survivors:
  - `target is OutputFormat.SVG` changed to `target == OutputFormat.SVG`.
    `normalize_output_format()` returns an `OutputFormat` member, so identity
    and equality are equivalent for this enum-domain comparison.
  - `target is OutputFormat.SVG` changed to `target >= OutputFormat.SVG`.
    `OutputFormat.SVG` is the first supported string enum value in this
    normalized two-format branch; existing SVG and PDF materialization
    assertions cover the reachable outcomes.
- `TEXT-DRAWING-TEXT-P2` continuation: Cosmic Ray 8.4.6 scoped to
  `_coerce_text_value()` and `TextDrawing.__post_init__()` produced
  1 proof-critical work item. Result: 1 killed, 0 survived.
- `TEXT-DRAWING-POSITION-P2` continuation: Cosmic Ray 8.4.6 scoped to
  `_coerce_point_pair()` and `TextDrawing.__post_init__()` produced
  33 proof-critical work items. Result: 32 killed and 1 survived.
- Equivalent survivor:
  - `_coerce_point_pair(value: object, *, name: str)` changed to
    `_coerce_point_pair(value: object, /, name: str)`. All production callers
    pass `value` positionally and `name` by keyword, so this does not change the
    reachable public API behavior under the current helper-private contract.
- `TEXT-PDF-ALIGN-P2` continuation:
  `tests/mutation/pdf_text_alignment_cosmic_ray.toml`, filtered by
  `tests/mutation/filter_pdf_text_alignment_work_items.py`: 5,797 raw work
  items filtered to 129 proof-critical items; 123 killed and 6 survived as
  documented equivalents.
- Equivalent survivors:
  - `_pdf_text_aligned_x()` comparisons from `==` to `is` for `"center"` and
    `"end"` are equivalent for the public `TextStyle` domain because
    `TextStyle.text_align` stores normalized literal string values.
  - `_pdf_text_aligned_x()` comparisons from `==` to `<=` for `"center"` and
    `"end"` are equivalent for the normalized three-value domain: only
    `"center"` reaches the center branch, only `"end"` reaches the end branch,
    and `"start"` falls through.
  - `TextPDF.generate_pdf()` fallback `line_spacing` default mutations from
    `1.0` to `0.0` or `2.0` are equivalent for the valid `TextStyle` domain
    because `TextStyle` construction always exposes a validated
    `line_spacing` attribute.

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
string content, color, font size, text matrices, and one text-showing operation
per normalized text line.

### Domain

All `TextPDF` instances with valid text anchors and text styles. The multiline
domain covers LF, CRLF, and CR line breaks and uses `TextStyle.line_spacing` as
the line advance multiplier. The defensive default branch is also proven for
incomplete style internals.

### Proof Method

The exact PDF output assertion checks graphics-state save/restore, color,
`BT`/`ET`, font selection, text matrix, escaped literal text, and `Tj`.
The multiline assertion checks CRLF/CR/LF normalization, per-line `Tm`/`Tj`
operators, line-spacing y offsets, and absence of raw line-break escape text in
PDF literals. The fallback assertion checks black color and 10-point defaults
when style internals are incomplete.

### Counterexamples And Exclusions

This obligation handles explicit line breaks only. Automatic wrapping,
alignment across line boxes, tabs, rich text runs, Unicode/CID font encoding,
complex shaping, vertical text, and glyph subsetting remain out of scope.

### Conclusion

Proven for the stated domain after focused tests and scoped mutation, with
equivalent default-fallback survivors documented above.

## PO-TEXT-013: PDF Applies Text Alignment Per Line

### Claim

`TextPDF.generate_pdf()` positions each normalized text line according to the
validated `TextStyle.text_align` value. `start` alignment uses the anchor x
coordinate directly, `center` subtracts half of the line width, and `end`
subtracts the full line width. Each line uses its own width, so multiline text
with different line lengths does not reuse the first line's offset.

### Domain

All `TextPDF` instances with valid text anchors and `TextStyle.text_align`
values admitted by `TextStyle`: `start`/`left`, `center`/`middle`, and
`end`/`right`. The width model is InkGen's deterministic PDF text estimate:
`font_size * 0.6 * character_count`.

### Proof Method

The alignment test renders multiline text with center and right alignment,
using different line lengths and a trailing empty line. It asserts the exact
`Tm` x origins and the emitted `Tj` lines. A mutation gate targets the
alignment helper and `TextPDF.generate_pdf()` line-origin path.

### Counterexamples And Exclusions

This obligation does not prove automatic wrapping, tabs, columns, kerning,
glyph-specific metrics, complex-script shaping, vertical text, rich text runs,
or Unicode/CID font encoding.

### Conclusion

Proven for explicit-line PDF text alignment in the stated domain, with
equivalent mutation survivors documented above.

## PO-TEXT-010: PDF Uses Standard Font Resources From TextStyle

### Claim

`DocumentPDF.to_pdf_bytes()` maps `TextStyle.font` family, style, and weight to
deterministic built-in PDF Standard font resources instead of binding every
text object to Helvetica.

### Domain

Text rendered through `DocumentPDF` with font families that resolve to
Helvetica/sans-serif, Times/serif, or Courier/monospace classes, including bold
and italic/oblique variants.

### Proof Method

`TextPDF.generate_pdf()` receives a `PDFRenderContext` during document
rendering and asks that context for the font resource name. The context delegates
to `_PDFFontRegistry`, which maps the style to a PDF Standard base font and
assigns deterministic `/F<n>` resource names. The focused test renders one
document with serif bold-italic text and monospace text, then asserts both the
content stream resource names and the emitted `/BaseFont` resources.

### Counterexamples And Exclusions

Named TrueType/OpenType embedding is covered separately by PO-TEXT-011. Font
subsetting, glyph encoding beyond WinAnsi, rich text runs, and multiline layout
are not part of this obligation.

### Conclusion

Proven for built-in PDF Standard font resource selection after focused tests
and scoped mutation pass. Full quality gates remain part of the slice closeout.

## PO-TEXT-011: PDF Embeds Named Installed Fonts

### Claim

`DocumentPDF.to_pdf_bytes()` embeds named installed TrueType/OpenType font files
instead of collapsing those text styles to Helvetica.

### Domain

Text rendered through `DocumentPDF` with a `TextStyle.font` whose requested
family is not generic and whose `Font.font_file` resolves to a readable
TrueType/OpenType file. Text bytes remain in the simple WinAnsi text-string
domain.

### Proof Method

`Font` preserves `requested_family` before Matplotlib resolves the closest
installed font. `_PDFFontRegistry` keeps generic families on the Standard 14
path and converts named resolved font files into embedded font resources.
`fonttools` reads units-per-em, WinAnsi glyph widths, bounding box, ascent,
descent, cap height, italic angle, and font outline type. `DocumentPDF` writes a
compressed font-file stream, a font descriptor, and a `/TrueType` font resource
that is reused for the same font file across different text sizes.

### Counterexamples And Exclusions

Generic families intentionally remain PDF Standard 14 resources. Full Unicode
CID fonts, glyph subsetting, PDF text shaping, vertical text, and
complex-script extraction are excluded from this obligation. WinAnsi
ToUnicode maps are covered separately by PO-TEXT-012.

### Conclusion

Proven for named installed WinAnsi-compatible font resources after focused
tests and scoped mutation. Full quality gates remain part of the slice
closeout.

## PO-TEXT-012: PDF Fonts Include WinAnsi ToUnicode Maps

### Claim

`DocumentPDF.to_pdf_bytes()` attaches deterministic `/ToUnicode` CMaps to used
Standard 14 and embedded WinAnsi font dictionaries so printable ASCII bytes in
generated text streams have explicit Unicode extraction mappings.

### Domain

Text rendered through `DocumentPDF` with the current InkGen PDF text encoding
domain: single-byte WinAnsi literal strings over `PDF_WINANSI_FIRST_CHAR` to
`PDF_WINANSI_LAST_CHAR`.

### Proof Method

`DocumentPDF.to_pdf_bytes()` allocates a ToUnicode CMap stream for every used
font resource before emitting that font dictionary. `_pdf_font_object()` writes
the `/ToUnicode <object> 0 R` reference for both Standard 14 and embedded
TrueType font dictionaries. `_pdf_tounicode_cmap_object()` emits a deterministic
`beginbfchar` map from each current printable WinAnsi byte to the same Unicode
code point. Focused tests assert Standard and embedded font dictionaries include
`/ToUnicode`, include the expected CMap name, and include representative
space, `A`, and `~` mappings.

### Counterexamples And Exclusions

This does not implement full Unicode/CID font encoding, glyph subsetting,
multi-byte text strings, shaping, vertical writing, or CMaps for text outside
the current printable WinAnsi range.

### Conclusion

Behavioral tests and scoped mutation prove the Standard 14 and embedded-font
live paths for the current WinAnsi extraction-map domain.

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

## PO-TEXT-008: Neutral Text Payloads Are Normalized Or Rejected

### Claim

`TextDrawing` cannot expose malformed text state through direct construction,
materialization, serialization, or `FlowDocument` hydration.

### Domain

All `TextDrawing` instances created directly and all serialized
`TextDrawing` payloads hydrated through `FlowDocument.create_from_dict()`.

### Assumptions

The neutral text recipe should match the scalar text domain already accepted by
`TextComponent.text`: `str`, `int`, `float`, `complex`, and `bool` values are
converted to strings; non-scalar values are invalid.

### Proof Method

`TextDrawing.__post_init__()` routes every construction path, including
FlowDocument drawing hydration, through `_coerce_text_value()`. The helper has a
closed scalar type check and stores the normalized string by using
`object.__setattr__()` on the frozen dataclass before validating the text style.
Direct condition tests cover accepted scalar partitions and rejected non-scalar
partitions. The FlowDocument condition test mutates serialized drawing payloads
and proves the dependent hydration path fails before returning malformed public
block state.

### Counterexamples And Exclusions

Private mutation of `TextDrawing.__dict__` after construction is outside the
public contract. Rich text runs and structured text spans remain out of scope.

### Conclusion

Proven for the stated public construction and FlowDocument hydration domain
after focused tests and mutation pass.

## PO-TEXT-009: Neutral Text Anchors Are Normalized Or Rejected

### Claim

`TextDrawing` cannot expose malformed text-anchor geometry through direct
construction, materialization, serialization, or `FlowDocument` hydration.

### Domain

All `TextDrawing` instances created directly and all serialized
`TextDrawing.position` payloads hydrated through
`FlowDocument.create_from_dict()`.

### Assumptions

Neutral `TextDrawing.position` should use the same finite two-coordinate point
pair domain as renderer-neutral rectangles, arcs, and Bezier primitives, while
preserving the existing text-placement allowance for negative coordinates.

### Proof Method

`TextDrawing.__post_init__()` routes every construction path, including
FlowDocument drawing hydration, through `_coerce_point_pair()` before storing
the frozen dataclass field. The helper rejects strings, bytes, non-sequences,
wrong-length sequences, boolean coordinates, nonnumeric coordinates, and
non-finite coordinates. Direct condition tests cover malformed partitions and
valid negative-anchor normalization. The FlowDocument hydration test mutates a
serialized drawing payload and proves the dependent document path fails before
returning malformed public block state.

### Counterexamples And Exclusions

Private mutation of `TextDrawing.__dict__` after construction is outside the
public contract. Changing the policy to forbid negative text coordinates would
be a new semantic decision and is outside this slice.

### Conclusion

Proven for the stated public construction and FlowDocument hydration domain
after focused tests and mutation pass.

## Current Slice Decision

The slice chooses fail-fast validation for non-finite text anchors while
preserving negative text coordinates. That keeps existing text placement
semantics intact and prevents invalid geometry from reaching SVG, PDF, DXF, or
downstream parser fixtures.

The `TEXT-DRAWING-TEXT-P2` continuation preserves the existing scalar
text-to-string compatibility while making malformed neutral text states
impossible through the public constructor and FlowDocument drawing hydration
paths.

The `TEXT-DRAWING-POSITION-P2` continuation preserves valid negative text
placement while making malformed neutral text-anchor geometry impossible
through the public constructor and FlowDocument drawing hydration paths.
