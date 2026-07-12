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
- `FlowDocument.to_markdown()`
- `FlowDocument.to_rtf()`
- `FlowDocument.to_plain_text()`
- `FlowDocument.parameters`
- `FlowDocument.create_from_dict()`
- `FlowDocument.add_paragraph()`
- `FlowDocument.add_table()`
- `FlowDocument.add_drawing_group()`

## Architecture Impact

Affected surface:

- `src/InkGen/document_outputs.py`: DOCX package metadata, DrawingML vector
  and image output, drawing materialization guards, and document-output
  helpers.
- `tests/test_flow_document_contract.py`: focused FLOW-DOCUMENT-P1 evidence.
- `tests/test_document_outputs.py`: existing document-output compatibility
  evidence.

Incoming dependencies:

- Public callers import `FlowDocument` and `DocumentOutputFormat` from
  `InkGen`.
- Word and Google Docs workflows rely on DOCX output being dependency-free and
  importable.
- Generated synthetic fixtures rely on stable DOCX/HTML/Markdown/RTF/text block
  order.
- Drawing groups rely on neutral drawing recipes remaining the geometry source
  of truth.

Outgoing dependencies:

- Flow documents consume `Paragraph`, `Table`, and `DrawingComponentGroup`.
- DOCX output depends only on Python `zipfile`, WordprocessingML strings,
  DrawingML shape/picture fragments, and local XML escaping helpers.
- Drawing fragments depend on neutral drawing primitives materializing to SVG or
  PDF components through `to_component()`.
- Text escaping depends on stdlib HTML and XML escaping plus local Markdown and
  RTF escaping.

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
- Before the file-parent hardening update, output paths whose parent segment
  existed as a file could still pass the existence check and then fail through
  incidental `open()` errors.
- Before the materialized-points hardening update, custom or post-construction
  mutated drawing primitives whose concrete materialization exposed malformed
  `points` could fail through incidental numeric formatting errors before the
  document-output boundary named the bad point surface.
- Before the live drawing component hardening update, `to_plain_text()`
  silently summarized malformed post-construction drawing-group mutations and
  `parameters` could fail through incidental `AttributeError` while reading
  `component.__dict__`.
- Before the artifact-number hardening update, special-case live
  `CircleDrawing` DOCX/HTML bounds and DOCX vector output could consume
  malformed position/radius values through raw arithmetic and `float()`
  formatting. DOCX twip conversion also used direct `float()` coercion for
  final artifact numbers.
- Before the DrawingML modernization update, DOCX vector drawing output used
  VML groups and polylines while raster images already used DrawingML picture
  parts.
- Before the Markdown output update, flow documents could not export a
  dependency-free document artifact that common static-site, README, and docs
  systems can consume while preserving table and drawing blocks.
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
- After the file-parent hardening update, file writers require the output
  parent path to be an existing directory, not merely an existing filesystem
  path.
- After the RTF Unicode hardening update, `FlowDocument.to_rtf()` emits
  non-ASCII title and paragraph text as RTF `\uN?` escapes instead of raw
  Unicode text in an `\ansi` document.
- After the text escaping hardening update, `FlowDocument.to_rtf()` also emits
  DEL (`0x7f`) through the RTF Unicode escape path instead of raw control text,
  while preserving printable ASCII.
- After the materialized-points hardening update, HTML/DOCX drawing bounds and
  DOCX DrawingML output validate materialized point surfaces as finite
  coordinate pairs before generated document artifacts consume them.
- After the live drawing component hardening update, plain-text drawing
  summaries revalidate public mutable drawing component lists before using
  class names, and serialized flow-document drawing parameters reject malformed
  or unsupported drawing primitives before reading component internals.
- After the artifact-number hardening update, special-case circle
  bounds/DrawingML and DOCX twip conversion reject booleans, strings, bytes,
  arbitrary objects, non-finite values, and non-positive circle radii before
  document artifacts are emitted.
- After the DrawingML modernization update, DOCX vector drawing output emits
  dependency-free DrawingML anchors and `wps:wsp` shapes. Rectangles and circles
  become native preset shapes, text drawings become DrawingML text boxes, and
  other materialized point sequences become anchored DrawingML line segments.
- After the Markdown output update, `FlowDocument.to_markdown()` emits
  dependency-free Markdown with escaped titles/paragraphs, pipe tables, and
  validated inline SVG for drawing blocks.
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
  timestamps, output escaping, Markdown block export, mixed block round trip,
  invalid drawing materialization failure, native DrawingML vector emission, and
  exact DrawingML coordinate/extents in EMUs.
- No architecture claim in this note relies only on stale memory.

ADR/rule impact:

- No new ADR is required because the slice preserves the dependency-free output
  policy and existing flow-document dependency direction.
- A future change that adds a document-output dependency must record an ADR and
  user approval.

## Domain Definitions

- A flow document is an ordered list of `Paragraph`, `Table`, and
  `DrawingComponentGroup` blocks.
- Supported document outputs are DOCX, HTML, Markdown, RTF, and plain text.
- DOCX output is a minimal WordprocessingML ZIP package.
- Repeated DOCX generation for the same document state must produce identical
  bytes.
- Drawing output must fail loudly if a neutral drawing primitive cannot
  materialize to an InkGen `Component` with the renderer-specific fragment
  surface needed by the target document format.
- DOCX vector output uses DrawingML shapes and anchors. It is not a complete
  Word shape renderer; unsupported complex paths are represented through
  materialized line segments rather than custom geometry.

## Fix Log

- DOCX ZIP parts are now written through `_write_docx_part()` with
  `DOCX_FIXED_TIMESTAMP`.
- Flow-document drawing HTML, bounds, and DrawingML helpers now call
  `_materialize_drawing_component()`.
- `_materialize_drawing_component()` rejects missing/non-callable materializers
  and non-`Component` materialization results.
- `_svg_fragment()` rejects SVG materializations that cannot provide a string
  `generate_svg()` fragment, and DOCX DrawingML conversion rejects PDF
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
- `ArcDrawing` validates serialized neutral arc geometry during
  `FlowDocument` drawing component hydration before malformed center, radius,
  angle, or rotation payloads can become public neutral drawing state.
- `QuadraticBezierDrawing` and `CubicBezierDrawing` validate serialized neutral
  Bezier point geometry during `FlowDocument` drawing component hydration
  before malformed point payloads can become public neutral drawing state.
- `CircleDrawing` and `RegularPolygonDrawing` validate serialized neutral
  radial geometry during `FlowDocument` drawing component hydration before
  malformed radial payloads can become public neutral drawing state.
- `PolygonalDrawing` validates serialized neutral irregular polygon geometry
  during `FlowDocument` drawing component hydration before malformed polygon
  payloads can become public neutral drawing state.
- `_normalize_output_filepath()` validates all flow-document file-writer output
  paths before text or byte writes.
- `_normalize_output_filepath()` now requires file-writer parent paths to be
  directories, closing the existing-file-as-parent boundary.
- `_materialized_points()` validates concrete drawing materialization `points`
  surfaces before HTML bounds or DOCX DrawingML output consume them.
- `_drawing_plain_text()` validates each live drawing component before
  summarizing names from a public mutable drawing-group list.
- `_drawing_component_parameters()` validates each live drawing component and
  requires a supported serializable neutral primitive type before reading
  component internals for `FlowDocument.parameters`.
- `_artifact_number()`, `_artifact_point_pair()`,
  `_positive_artifact_number()`, and `_nonnegative_artifact_number()` validate
  final document artifact numeric boundaries used by DrawingML shapes,
  circle/bounds, and DOCX twip conversion.
- `_component_drawingml()`, `_drawingml_shape_docx()`, and
  `_drawingml_segments_docx()` replace the DOCX VML vector group with native
  DrawingML shape anchors while preserving neutral drawing ownership.
- `_nonnegative_artifact_number()` guards live rectangle dimensions before
  DrawingML extents are emitted.
- `FlowDocument.to_markdown()`, `create_markdown()`, `_block_markdown()`,
  `_table_markdown()`, and Markdown escaping helpers add a dependency-free
  document output that preserves flow-document block order and reuses validated
  SVG drawing materialization.
- `_rtf_escape()` now treats only codepoints below `0x7f` as raw ASCII, so DEL
  is escaped consistently with non-ASCII RTF text.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Repeated DOCX generation | Preserve exact bytes and fixed part order/timestamps | PO-FDOC-001 | `test_flow_document_docx_bytes_are_deterministic` | killed |
| Text with XML/HTML/Markdown/RTF controls | Escape per target format | PO-FDOC-002 | `test_flow_document_escapes_text_across_output_formats` | 127 killed; 3 equivalent survivors |
| RTF non-ASCII text | Emit RTF Unicode escapes for title and paragraph text | PO-FDOC-016 | `test_flow_document_rtf_escapes_unicode_text` | killed with documented equivalent survivors |
| Paragraph/table/drawing block order | Preserve through parameters and output | PO-FDOC-003 | `test_flow_document_preserves_mixed_block_order_after_round_trip` | killed |
| Root payload shape | Accept wrapped/direct mappings and reject malformed payload roots or collection fields | PO-FDOC-008 | `test_flow_document_hydrates_direct_payload_mapping`, `test_flow_document_hydration_rejects_malformed_root_payloads` | killed |
| Serialized block envelope and dispatch | Reject malformed envelopes and dispatch valid dynamic type strings by value | PO-FDOC-007 | `test_flow_document_hydration_rejects_malformed_block_envelopes`, `test_flow_document_hydration_dispatches_dynamic_block_type_strings` | killed |
| Serialized drawing payload | Reject missing drawing payload keys and non-sequence component collections before component iteration | PO-FDOC-010 | `test_flow_document_hydration_rejects_malformed_drawing_payloads` | killed |
| Serialized drawing component envelope and dispatch | Reject malformed component envelopes, reject unsupported types before style extraction, and dispatch valid dynamic type strings by value | PO-FDOC-009 | `test_flow_document_hydration_rejects_malformed_drawing_component_envelopes`, `test_flow_document_hydration_dispatches_dynamic_drawing_component_type_strings` | killed |
| Serialized drawing style envelope | Reject missing/malformed style envelopes, mismatched style keys, non-string style names, and wrong-type style overrides | PO-FDOC-011 | `test_flow_document_hydration_rejects_malformed_drawing_style_payloads`, `test_flow_document_hydration_rejects_mismatched_drawing_style_overrides`, `test_flow_document_hydration_constructs_missing_drawing_style_overrides_by_kind` | killed |
| Style override map boundary | Reject non-mapping `styles` values before block hydration | PO-FDOC-015 | `test_flow_document_hydration_rejects_malformed_style_override_maps` | killed |
| Serialized path command envelope | Reject malformed `PathDrawing` command collections before `PathCommand` construction and delegate point-entry shape validation to `PathCommand` | PO-FDOC-012 | `test_flow_document_hydration_rejects_malformed_path_command_payloads` | killed |
| Serialized arc drawing geometry | Reject malformed `ArcDrawing` center, radius, angle, and rotation payloads by dispatching through the neutral constructor | PO-FDOC-018 | `test_flow_document_hydration_rejects_malformed_arc_geometry_payloads` | mutation target in arc slice |
| Serialized Bezier drawing geometry | Reject malformed `QuadraticBezierDrawing` and `CubicBezierDrawing` point payloads by dispatching through the neutral constructors | PO-FDOC-019 | `test_flow_document_hydration_rejects_malformed_bezier_geometry_payloads` | mutation target in Bezier slice |
| Serialized radial drawing geometry | Reject malformed `CircleDrawing` and `RegularPolygonDrawing` geometry payloads by dispatching through the neutral constructors | PO-FDOC-020 | `test_flow_document_hydration_rejects_malformed_radial_geometry_payloads` | mutation target in radial slice |
| Serialized polygonal drawing geometry | Reject malformed `PolygonalDrawing` point payloads by dispatching through the neutral constructor | PO-FDOC-021 | `test_flow_document_hydration_rejects_malformed_polygonal_geometry_payloads` | mutation target in polygonal slice |
| File writer path boundary | Accept string/path-like output paths and reject malformed output path values or non-directory parents before writing | PO-FDOC-013 | `test_flow_document_file_writers_accept_pathlike_outputs`, `test_flow_document_file_writers_reject_malformed_paths`, `test_flow_document_file_writers_fail_on_missing_directory`, `test_flow_document_file_writers_reject_file_parent_paths` | killed |
| Materialized drawing point surface | Accept finite coordinate pairs and reject malformed/non-finite materialized point surfaces before HTML/Markdown/DOCX artifacts consume them | PO-FDOC-022 | `test_flow_document_accepts_valid_materialized_drawing_points`, `test_flow_document_rejects_malformed_materialized_drawing_points` | killed |
| Live drawing components in text/parameter paths | Reject malformed public drawing-group mutations before plain-text summaries or serialized parameters consume them | PO-FDOC-023 | `test_flow_document_plain_text_revalidates_mutated_drawing_components`, `test_flow_document_parameters_revalidate_mutated_drawing_components`, `test_flow_document_parameters_preserve_path_drawing_commands` | killed |
| Document artifact numbers | Reject malformed live circle DrawingML numbers and malformed DOCX twip numbers before artifact serialization | PO-FDOC-026 | `test_flow_document_formats_valid_circle_drawingml_and_twips`, `test_flow_document_empty_drawing_bounds_use_unit_fallback`, `test_flow_document_circle_bounds_continue_to_materialized_components`, `test_flow_document_rejects_malformed_circle_drawingml_numbers`, `test_flow_document_rejects_malformed_docx_twip_numbers` | 65 killed; 2 equivalent survivors |
| Malformed serialized drawing label | Reject through the neutral group label contract | PO-FDOC-006 | `test_flow_document_drawing_group_hydration_rejects_malformed_label` | killed |
| Invalid drawing materialization | Reject before silent omission | PO-FDOC-004 | `test_flow_document_rejects_invalid_drawing_materialization` | killed |
| Invalid drawing render fragments | Reject SVG materializations without string `generate_svg()` fragments and DOCX/PDF materializations without points | PO-FDOC-014 | `test_flow_document_rejects_materializations_without_render_fragments` | killed |
| DOCX DrawingML linework | Emit group-relative anchored DrawingML coordinates and extents | PO-FDOC-005 | `test_flow_document_docx_drawingml_line_uses_group_relative_points` | killed |
| DOCX DrawingML native primitives | Emit rectangles, circles, text, images, and materialized linework through DrawingML rather than VML | PO-FDOC-027 | `test_flow_document_exports_tables_and_drawing_primitives`, `test_flow_document_docx_keeps_vector_coordinates_when_images_share_drawing_group`, `test_flow_document_accepts_valid_materialized_drawing_points`, `test_flow_document_docx_drawingml_preserves_style_text_and_line_flips`, `test_flow_document_docx_drawingml_helper_fragments_cover_branches`, `test_flow_document_docx_drawingml_component_helpers_preserve_offsets_and_extents`, `test_flow_document_docx_drawingml_shape_helper_preserves_explicit_flip_flags`, `test_flow_document_docx_drawingml_markup_is_well_formed` | 171 killed; 6 equivalent survivors |
| Markdown document export | Emit escaped Markdown paragraphs, pipe tables, and validated inline SVG drawing blocks in document order | PO-FDOC-028 | `test_flow_document_exports_html_rtf_and_text`, `test_flow_document_exports_tables_and_drawing_primitives`, `test_flow_document_markdown_exports_ordered_blocks_with_escaped_tables_and_svg`, `test_flow_document_markdown_table_separator_is_inserted_once_after_header`, `test_flow_document_markdown_omits_zero_column_tables`, `test_flow_document_rejects_invalid_drawing_materialization`, `test_flow_document_text_writers_create_requested_files`, `test_flow_document_file_writers_accept_pathlike_outputs`, `test_flow_document_file_writers_reject_malformed_paths` | 34 killed; 2 equivalent survivors |
| Unsupported block private mutation | Excluded from public contract | Explicit exclusion | Not applicable | Out of scope |
| Full WordprocessingML feature parity | Excluded from minimal dependency-free backend | Explicit exclusion | Not applicable | Out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Helpers are deterministic. | FLOW-DOCUMENT-P1 tests |
| Behavioral/condition | yes | The slice defines document-output behavior. | Tests are marked `@pytest.mark.condition("FLOW-DOCUMENT-P1")`, `@pytest.mark.condition("FLOW-DOCUMENT-SVG-MATERIALIZATION-P2")`, `@pytest.mark.condition("FLOW-DOCUMENT-STYLES-MAPPING-P2")`, `@pytest.mark.condition("FLOW-DOCUMENT-DRAWING-LIVE-COMPONENTS-P2")`, and `@pytest.mark.condition("FLOW-DOCUMENT-FILEPATH-DIRECTORY-P2")`. |
| Failure-mode | yes | Invalid content, malformed root payloads, malformed serialized block envelopes, malformed drawing payloads, malformed drawing component envelopes, malformed drawing style envelopes, malformed style override maps, malformed path command envelopes, malformed serialized drawing labels, malformed materialization fragments, malformed materialized point surfaces, malformed live drawing components, malformed output paths, and invalid output paths must fail loudly. | Invalid hydration, invalid materialization, render-fragment, point-surface, live-component, style-map, and writer tests |
| Integration/live-path | yes | DOCX ZIP, HTML, Markdown, RTF, text, table, and drawing paths cross module boundaries. | Focused and existing document-output tests |
| Contract/API compatibility | yes | Parameters and public add methods must preserve existing behavior. | Round-trip and existing rejection tests |
| Property/fuzz | no | This slice proves finite output and dispatch contracts. | Not applicable |
| Mutation | yes | Deterministic package writing, Markdown escaping/table formatting, and materialization guards are proof-critical. | Mutation result recorded below |
| Security/adversarial | limited | File writers touch local paths; tests cover malformed, missing-directory, and file-as-parent failures. | `test_flow_document_file_writers_fail_on_missing_directory`, `test_flow_document_file_writers_reject_file_parent_paths` |
| Performance/resource | no | The slice adds constant-time checks and fixed metadata. | Code inspection |
| Concurrency/race | no | No shared state, workers, locks, or temp files are added. | Not applicable |
| Golden artifact/visual | yes | DOCX XML/DrawingML output must be stable. | ZIP/XML/DrawingML assertions |
| Regression | yes | This closes nondeterministic DOCX bytes and silent drawing omission. | Determinism and invalid-materialization tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Changing DOCX part names, payload routing, fixed timestamps, or compression
  should fail deterministic package tests.
- Weakening drawing materializer callability or return-type checks should fail
  invalid-materialization tests.
- Weakening SVG fragment callability/string checks or DOCX DrawingML points-surface
  checks should fail render-fragment tests.
- Changing DOCX DrawingML group-relative coordinates should fail exact EMU
  coordinate tests.
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
- Weakening file-writer path normalization should fail malformed-path,
  path-like output, missing-directory, or file-parent output tests.
- Weakening materialized drawing point validation should fail point-surface
  failure-mode tests or exact bounds/DrawingML assertions.
- Weakening live drawing component validation before plain-text summaries or
  serialized parameters should fail live-component mutation tests.
- Weakening final artifact-number validation should fail malformed circle
  DrawingML, malformed twip, or exact circle DrawingML/twip formatting tests.
- Weakening Markdown table separator placement, zero-column handling, block
  dispatch, escaping, or writer routing should fail Markdown output tests.

Current result:

- Cosmic Ray 8.4.6, scoped to changed DOCX package assembly, drawing
  materialization guards, and legacy VML point rows before the DrawingML
  modernization: 34 work items, 34 killed, and 0 survived.
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
  filepath and file-parent hardening updates: 7 work items, 7 killed, and 0
  survived.
- Cosmic Ray 8.4.6, scoped to render-fragment guards after the SVG
  materialization hardening update: 7 work items, 7 killed, and 0 survived.
- Cosmic Ray 8.4.6, scoped to style override map validation after the
  style-mapping hardening update: 4 work items, 4 killed, and 0 survived.
- Cosmic Ray 8.4.6, scoped to materialized drawing point validation after the
  point-surface hardening update: 18 work items, 18 killed, and 0 survived.
- `FLOW-DOCUMENT-DRAWING-LIVE-COMPONENTS-P2` continuation: Cosmic Ray 8.4.6
  scoped to `_drawing_plain_text()`, `_drawing_component_parameters()`, and
  `_validate_drawing_component_boundary()` produced 8 proof-critical work
  items. Result: 8 killed, 0 survived.
- `FLOW-DOCUMENT-DRAWINGML-P3` supersedes the legacy
  `FLOW-DOCUMENT-VML-NUMBER-P2` vector path. The artifact-number filter was
  corrected from stale VML line ranges to current DrawingML circle bounds,
  artifact-number helper, and DOCX twip conversion rows. The corrected slice
  produced 67 proof-critical work items. Result: 65 killed, 2 documented
  equivalent survivors. Equivalent survivors:
  - `_drawing_bounds()`: empty drawing fallback max-x `1.0` changed to `0.0`.
    The public HTML path clamps empty width to at least `1.0`, so the emitted
    empty fallback remains `width="1mm"` and `viewBox="0 0 1 1"`.
  - `_drawing_bounds()`: empty drawing fallback max-y `1.0` changed to `0.0`.
    The public HTML path clamps empty height to at least `1.0`, so the emitted
    empty fallback remains `height="1mm"` and `viewBox="0 0 1 1"`.
- `FLOW-DOCUMENT-DRAWINGML-P3` scoped to `_drawing_docx()`,
  `_component_drawingml()`, `_drawingml_segments_docx()`,
  `_drawingml_shape_docx()`, `_drawingml_fill()`, `_drawingml_line()`,
  `_drawingml_text_body()`, and `_nonnegative_artifact_number()` produced 177
  proof-critical work items. Result: 171 killed, 6 documented equivalent
  survivors. Equivalent survivors:
  - `_drawingml_fill()`: `style.fill == "none"` to `>= "none"` is equivalent
    for the valid `DrawingStyle.fill` domain because values are normalized to
    `"none"` or lowercase hex strings beginning with `#`; hex strings compare
    below `"none"` and `"none"` still selects no fill.
  - `_drawingml_line()`: `style.stroke == "none"` to `>= "none"` is equivalent
    for the same normalized color domain.
  - `_drawingml_line()`: `style.stroke_width <= 0.0` to `== 0.0` is equivalent
    for the valid `DrawingStyle.stroke_width` domain because negative widths
    cannot be constructed.
  - `_drawingml_text_body()`: default text-size constants `1000 -> 999` and
    `1000 -> 1001` both round to the same DOCX half-point value (`20`) in the
    no-font fallback path.
  - `_nonnegative_artifact_number()`: the mutation of the keyword-only `*`
    separator to `/` does not change any valid call shape used by InkGen.
- `FLOW-DOCUMENT-MARKDOWN-P3` scoped to `to_markdown()`,
  `create_markdown()`, `_block_markdown()`, `_paragraph_markdown()`,
  `_table_markdown()`, `_markdown_escape()`, and `_markdown_table_cell()`
  produced 36 proof-critical work items. Result: 34 killed, 2 documented
  equivalent survivors. Equivalent survivors:
  - `_table_markdown()`: `table.column_count == 0` to `<= 0` is equivalent
    for the valid `Table` domain because column counts cannot be negative.
  - `_table_markdown()`: `row_index == 0` to `<= 0` is equivalent because
    indices produced by `range(table.row_count)` are never negative.
- `FLOW-DOCUMENT-FILEPATH-DIRECTORY-P2` refreshed the file-writer path
  boundary and mutation filter. Focused flow-document tests returned
  `121 passed`; compatibility tests returned `178 passed`; the full coverage
  gate returned `1540 passed` with `95%` total coverage.
- `FLOW-DOCUMENT-P1` scoped to the drawing-label hydration call site produced
  7 proof-critical work items: 7 killed and 0 survived. Cosmic Ray did not
  generate a constructor-argument mutant for adding `str(...)`, so the focused
  test explicitly uses a stringifiable non-string label to pin that historical
  failure mode.
- `FLOW-DOCUMENT-P1` scoped to ASCII control escaping in DOCX, HTML, Markdown,
  and RTF produced 130 proof-critical work items: 127 killed and 3 documented
  equivalent survivors. Equivalent survivors:
  - `_rtf_escape()`: `character == "\\"` changed to `character is "\\"`.
  - `_rtf_escape()`: `character == "{"` changed to `character is "{"`.
  - `_rtf_escape()`: `character == "}"` changed to `character is "}"`.
  In CPython, iterating a string yields cached one-character strings for these
  literals, so identity and equality take the same branch for the tested public
  RTF text domain. The threshold mutant changing `< 128` to `< 127` exposed a
  real DEL boundary and was closed by escaping DEL through the Unicode path.
- `FLOW-DOCUMENT-P1` scoped to mixed block order across append methods,
  `parameters`, hydration, plain text, HTML, Markdown, RTF, DOCX XML, and block
  dispatch produced 128 proof-critical work items: 128 killed and 0 survived.

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

Text control characters are escaped in DOCX XML, HTML, Markdown, and RTF
outputs.

### Domain

Paragraph text and titles containing XML/HTML/Markdown/RTF control characters.

### Proof Method

DOCX uses XML escaping, HTML uses HTML escaping, Markdown escapes Markdown
syntax characters, and RTF escapes backslashes, braces, non-ASCII text, and DEL
(`0x7f`). The focused test asserts representative title and multiline
paragraph control characters through every public format.

### Conclusion

Proven for the stated representative domain after focused tests, mutation, and
documented equivalent survivors.

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

The public add methods append to the same `_blocks` list read by `blocks`,
`parameters`, hydration, and every output loop. The block serializers tag each
block by type in document order. The focused test recreates a
paragraph/table/drawing document and compares block classes, parameters,
plain-text order, HTML order, Markdown order, RTF order, and DOCX XML order.

### Conclusion

Proven for the stated domain after focused tests and mutation pass.

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

## PO-FDOC-005: DOCX DrawingML Points Are Group-Relative

### Claim

Linework emitted into DOCX DrawingML uses coordinates relative to the drawing
group's minimum x/y bounds.

### Domain

Neutral drawing groups containing linework whose PDF materialization exposes
points.

### Proof Method

`_drawing_bounds()` computes group bounds from materialized PDF points.
`_component_drawingml()` and `_drawingml_segments_docx()` subtract minimum x/y
from each point before writing anchored DrawingML line shapes. The focused test
checks exact DrawingML position offsets and EMU extents for nonzero source
points.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-FDOC-027: DOCX Vectors Use Native DrawingML

### Claim

DOCX drawing blocks emit native DrawingML vector shapes instead of VML drawing
groups, while preserving the renderer-neutral drawing dependency boundary.

### Domain

`FlowDocument.to_docx_bytes()` calls on documents containing
`DrawingComponentGroup` blocks with supported neutral drawing primitives and
image drawings.

### Dependencies

- `DrawingComponentGroup`
- `RectangleDrawing`
- `CircleDrawing`
- `TextDrawing`
- `ImageDrawing`
- `_drawing_bounds()`
- `_component_drawingml()`
- `_drawingml_shape_docx()`
- `_drawingml_segments_docx()`
- `_image_drawing_docx()`

### Proof Method

`_drawing_docx()` routes raster image drawings to the existing DrawingML
picture path and routes all vector drawing components through
`_component_drawingml()`. Rectangles and circles are emitted as preset
DrawingML shapes. Text drawings are emitted as DrawingML text boxes. Other
supported linework materializes through the existing PDF point surface and is
serialized as anchored DrawingML line segments. The focused tests assert that
DOCX vector output contains `wp:anchor` and `wps:wsp`, contains native preset
geometry for rectangle, ellipse, and line cases, preserves EMU offsets/extents,
and does not emit `<w:pict>` for vector drawings.

### Counterexamples And Exclusions

This is not a full DrawingML custom-geometry implementation. Complex paths,
curves, arcs, and polygons remain represented as line segments from the
materialized point surface. Visual rendering in Word and Google Docs should be
verified with fixture spot checks when a consumer depends on exact appearance.

### Conclusion

Focused tests prove the package/XML live path and the absence of VML for vector
drawings in the covered domains. Full coverage, lint, docs, and diff hygiene
passed for the slice. Mutation killed all non-equivalent proof-critical
mutants.

## PO-FDOC-028: Markdown Export Preserves Flow Blocks

### Claim

Markdown output emits document blocks in order, escapes Markdown control
characters in text content, preserves tables as pipe tables, and includes
validated inline SVG for drawing groups.

### Domain

`FlowDocument.to_markdown()` and `FlowDocument.create_markdown()` calls on
documents containing `Paragraph`, `Table`, and `DrawingComponentGroup` blocks.

### Dependencies

- `Paragraph`
- `Table`
- `DrawingComponentGroup`
- `_block_markdown()`
- `_paragraph_markdown()`
- `_table_markdown()`
- `_drawing_html()`
- `_markdown_escape()`

### Proof Method

`FlowDocument.to_markdown()` builds the same ordered block sequence used by the
other document exporters, then dispatches each block through
`_block_markdown()`. Paragraphs escape Markdown control characters and preserve
line breaks as hard breaks. Tables render as pipe tables with escaped cells and
HTML `<br>` line separators inside multi-line cells. Drawing groups reuse
`_drawing_html()`, so the Markdown path goes through the same SVG
materialization and malformed-drawing guards as HTML.

Focused tests assert block order, title/paragraph/table escaping, pipe-table
syntax, inline SVG presence, file-writer persistence, path-like support,
malformed path rejection, and invalid drawing materialization failures.

### Counterexamples And Exclusions

Markdown export is a lightweight interchange format, not a full CommonMark
layout engine. Inline SVG rendering depends on the downstream Markdown
consumer. DOCX-native media packaging remains owned by the DOCX exporter.

### Conclusion

Behavioral tests prove the Markdown live path for ordered blocks, escaping,
tables, drawings, and file writes. Scoped mutation killed all non-equivalent
proof-critical mutants.

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
supplies direct and stringifiable malformed serialized labels and asserts the
neutral group label error.

### Conclusion

Proven for the stated domain after focused tests and mutation pass.

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
malformed path values at the InkGen boundary, require parent paths to be
directories, and preserve generated payloads.

### Domain

`FlowDocument.create_docx()`, `create_html()`, `create_markdown()`,
`create_rtf()`, and `create_text()` calls.

### Proof Method

All writer methods delegate to `_normalize_output_filepath()` through
`_write_text()` or `_write_bytes()`. The helper uses `os.fspath()` to accept
string and path-like values, rejects bytes and non-path objects, rejects empty
paths, and requires the parent path to pass `os.path.isdir()`. Focused tests
cover successful `pathlib.Path` writes for every writer, malformed object,
integer, bytes, empty-string paths, missing directories, existing-file parent
paths, and payload equality checks.

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
a string. DOCX DrawingML output materializes non-special-case linework through
the PDF path and requires a `points` surface before deciding whether an empty
point list should produce no line segments. Focused tests cover a base
`Component` materialization that previously produced empty HTML/DOCX drawing
output and a malformed SVG materialization whose `generate_svg()` does not
return a string.

### Counterexamples And Exclusions

Valid components with an empty `points` collection remain allowed to produce no
DrawingML line segments. Full SVG semantic validation remains delegated to the
concrete SVG renderer tests.

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

## PO-FDOC-022: Materialized Drawing Points Are Finite Coordinate Pairs

### Claim

Flow-document HTML and DOCX drawing exports reject malformed concrete
materialization `points` surfaces before generated document artifacts consume
them.

### Domain

`FlowDocument.to_html()` and `FlowDocument.to_docx_bytes()` calls on documents
containing `DrawingComponentGroup` blocks whose neutral drawing primitives
materialize to InkGen `Component` instances exposing `points`.

### Proof Method

`_drawing_bounds()` and `_component_drawingml()` both route concrete
materialization points through `_materialized_points()`. The helper treats a
missing points surface as empty only for bounds discovery, preserves the DOCX
DrawingML requirement that renderable non-special-case linework expose points,
rejects non-sequence point collections, rejects malformed point shapes, and
rejects boolean, string, non-numeric, or non-finite coordinates. Focused tests
cover a valid custom point surface through both HTML bounds and DOCX DrawingML
output, plus malformed point containers, malformed point shapes, `nan`, `inf`,
booleans, and string coordinates.

### Counterexamples And Exclusions

SVG fragment semantic validation remains delegated to SVG renderer tests.
Private mutation of concrete renderer internals after materialization is outside
the public `FlowDocument` export call.

### Conclusion

Proven for the stated domain after focused tests and mutation pass. Full
coverage, lint, docs, and diff hygiene remain release-gate checks for the
slice.

## PO-FDOC-023: Live Drawing Components Are Revalidated For Text And Parameters

### Claim

Flow-document plain-text summaries and serialized parameters reject malformed
post-construction mutations in a drawing group's public `components` list before
consuming component names or internals.

### Domain

`FlowDocument.to_plain_text()` and `FlowDocument.parameters` calls on documents
containing `DrawingComponentGroup` blocks whose public `components` list was
mutated after construction.

### Proof Method

`_drawing_plain_text()` validates each live component has a callable
`to_component(output_format)` boundary before reading class names for the text
summary. `_drawing_component_parameters()` uses the same callable boundary and
then restricts serialized output to supported hydrateable neutral primitive
types before reading `component.__dict__`. Focused tests mutate the public list
with an arbitrary object and prove both public paths fail with explicit
boundary errors. A second serialization test uses a callable but unsupported
primitive and proves `FlowDocument.parameters` rejects it before producing an
unhydrateable serialized component envelope. The path-command preservation test
closes the dependent serialized `PathDrawing.commands` regression surface
exposed during mutation testing.

### Counterexamples And Exclusions

`DrawingComponentGroup.to_group()`, HTML, and DOCX materialization are already
covered by drawing-group and flow-document materialization obligations.
Custom drawing primitives can still be used for live materialization if they
meet the renderer contract, but flow-document serialization remains limited to
the supported neutral primitive set that `FlowDocument.create_from_dict()` can
hydrate.

### Conclusion

Proven for the stated public text and parameter domains after focused tests and
mutation pass. Full coverage, lint, docs, and diff hygiene remain release-gate
checks for the slice.

## PO-FDOC-024: Serializable Drawing Types Are Authentic

### Claim

Flow-document drawing serialization accepts only the actual supported neutral
drawing primitive classes, not arbitrary objects whose class name matches a
supported discriminator.

### Domain

`FlowDocument.parameters` calls on documents containing `DrawingComponentGroup`
blocks whose public `components` list contains objects with a callable
`to_component()` method.

### Dependencies

- `DRAWING_COMPONENT_CONSTRUCTORS`
- `DRAWING_COMPONENT_TYPE_NAMES`
- `PathDrawing`
- `_drawing_component_parameters()`
- `FlowDocument.create_from_dict()`

### Proof Method

`_drawing_component_parameters()` resolves the serialized discriminator from an
exact `type(component)` lookup in `DRAWING_COMPONENT_TYPE_NAMES`. The registry
contains the same concrete neutral drawing classes that
`FlowDocument.create_from_dict()` can hydrate, with `PathDrawing` handled as the
special command-preserving case. The focused test appends a lookalike object
whose class name is deliberately changed to `RectangleDrawing` and whose
`to_component()` method can produce a valid rectangle materialization. The
object still fails serialization because its actual type is not one of the
registered neutral primitive classes.

### Counterexamples And Exclusions

Subclass serialization is intentionally excluded unless the subclass is added
to the explicit registry and hydration map. Custom drawing primitives may still
participate in live HTML/DOCX materialization when they satisfy the renderer
contract, but `FlowDocument.parameters` remains limited to hydrateable InkGen
neutral primitives.

### Conclusion

Proven for the stated flow-document drawing serialization domain after focused
tests and mutation pass.

## PO-FDOC-026: Document Artifact Numbers Are Finite

### Claim

Final document artifact numeric serialization rejects malformed, non-finite, or
contract-breaking live values before DOCX/HTML markup is emitted.

### Domain

`FlowDocument.to_html()` and `FlowDocument.to_docx_bytes()` calls on documents
containing drawing groups with live `CircleDrawing` values, plus DOCX paragraph
twip conversion.

### Dependencies

- `_drawing_bounds()`
- `_component_drawingml()`
- `_drawingml_shape_docx()`
- `_drawingml_segments_docx()`
- `_vml_number()`
- `_artifact_point_pair()`
- `_artifact_number()`
- `_positive_artifact_number()`
- `_mm_to_twips()`

### Proof Method

Special-case `CircleDrawing` bounds and DrawingML output now normalize live
position coordinates through `_artifact_point_pair()` and live radius values
through `_positive_artifact_number()` before arithmetic or string formatting.
Artifact number formatting and DOCX twip conversion use `_artifact_number()` so
booleans, strings, bytes, arbitrary objects, `nan`, and infinity fail before
artifact text is emitted. Focused tests pin valid circle DrawingML and twip
formatting, empty drawing fallback bounds, mixed circle/materialized-component
bound traversal, and the exact millimeter-to-twip scale. They then mutate live
circle and paragraph state to cover malformed point shape, boolean coordinates,
non-finite coordinates, malformed radius values, non-positive radii, and
malformed twip values.

### Counterexamples And Exclusions

Normal public `CircleDrawing` and `Paragraph` setters already validate these
values. This proof covers the final document-output boundary against corrupted
live state and special-case renderer paths. It does not broaden the document
backend into a full geometry validator for every renderer; non-circle drawing
geometry remains delegated to materialized component point-surface checks.

### Conclusion

Focused tests and mutation cover the public output paths and corrupted
live-state partitions. The corrected mutation slice produced 67 proof-critical
work items: 65 killed and 2 equivalent empty-fallback survivors. Full coverage,
lint, docs, and diff hygiene remain release-gate checks for the slice.

## Current Slice Decision

The slice keeps `FlowDocument` dependency-free and minimal. It fixes byte
determinism and boundary validation without adding document libraries or
expanding the flow-document renderer into a general drawing renderer.
