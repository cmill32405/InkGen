# DXF Renderer Contract Proof Obligations

This note applies the InkGen Definition of Done to the DXF-P1 renderer slice.
It covers dependency-free ASCII DXF output for renderer-neutral drawing recipes,
coordinate conversion, entity dispatch, rounded rectangle sampling, path closure
flags, text/circle entities, image sidecar references, file output guards, and
PDF-sampled geometry reuse.

## Scope

The slice covers:

- `DXFRenderContext.point()`
- `DXFRenderContext.__post_init__()`
- `DXFDocument.add_group()`
- `DXFDocument.to_dxf_string()`
- `DXFDocument.create_dxf()`
- `_coerce_finite_float()`
- `_component_to_entities()`
- `_rectangle_points()` and `_append_corner_arc()`
- `_line_entity()`, `_lwpolyline_entity()`, `_text_entity()`, and
  `_circle_entity()`
- `_image_entity()`, `_dxf_objects_section()`, `_DXFImageRegistry`
- `_format_value()`

The original DXF-P1 slice added condition-marked tests, a scoped mutation gate,
and this proof note. The finite-boundary hardening update changes the public
DXF context and document canvas-height boundaries so malformed numeric values
fail before DXF artifact text is emitted. The filepath hardening update changes
the public DXF writer boundary so malformed output paths fail before `open()`.
The layer-boundary hardening update changes the public DXF context and
`DXFDocument.add_group()` layer override boundaries so malformed layer values
fail before `_format_value()` can stringify them into artifact text. The raster
image update adds IMAGE entities, IMAGEDEF objects, and deterministic PNG
sidecar writes for `ImageDrawing` components. The style update adds DXF
true-color and lineweight group codes for drawing entities that carry a
`DrawingStyle` stroke.

## Architecture Impact

Affected surface:

- `tests/test_dxf_contract.py`: DXF-P1 condition tests.
- `src/InkGen/dxf_generator.py`: finite numeric validation for public DXF
  coordinate and canvas-height boundaries, file-writer path validation, layer
  override validation, raster image reference emission, and drawing stroke style
  group-code emission.
- `tests/mutation/dxf_renderer_cosmic_ray.toml`: scoped Cosmic Ray gate.
- `tests/mutation/filter_dxf_renderer_work_items.py`: proof-critical mutation
  filter.
- `tests/mutation/dxf_context_finite_cosmic_ray.toml`: finite-boundary
  hardening mutation gate.
- `tests/mutation/filter_dxf_context_finite_work_items.py`: finite-boundary
  hardening mutation filter.
- `tests/mutation/dxf_style_cosmic_ray.toml`: stroke style-emission mutation
  gate.
- `tests/mutation/filter_dxf_style_work_items.py`: proof-critical stroke style
  filter.
- `docs/proofs/dxf-renderer-contract.md`: proof note.

Incoming dependencies:

- Renderer-neutral drawing recipes use `DXFDocument` to export drawing groups.
- Synthetic drawing workflows rely on deterministic ASCII DXF output.
- Curves, arcs, regular polygons, and paths reuse PDF-sampled geometry through
  `component.to_component(OutputFormat.PDF)`.

Outgoing dependencies:

- `dxf_generator.py` depends on renderer-neutral drawing classes,
  `RasterImageAsset`, and `normalize_rectangle_corner_radii()`.
- Indirect sampled geometry depends on the existing PDF component point
  contracts for arcs, curves, paths, and regular polygons.
- The raster image update adds the documented `dxf_generator.py ->
  image_assets.py` edge for PNG sidecar generation.

Before/after edge changes:

- The raster image update adds the documented `dxf_generator.py ->
  image_assets.py` edge.
- The style update consumes `DrawingStyle` fields already attached to neutral
  drawing primitives and does not add a new dependency layer.
- The proof makes the existing `dxf_generator.py -> PDF sampled geometry`
  cross-layer edge explicit and tested.
- The hardening update adds a local DXF numeric validator; it does not import a
  helper from another InkGen layer and does not add a dependency.
- The filepath hardening update adds a local DXF output path validator; it does
  not add a dependency or change DXF entity generation.
- The layer-boundary hardening update adds a local DXF layer validator; it does
  not add a dependency or change valid DXF entity generation.
- The raster image update consumes existing image assets and does not add an
  external package dependency.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced.
- Layer check: DXF remains a concrete renderer consuming neutral drawing
  recipes.
- Coupling check: the PDF-sampled geometry dependency remains limited to point
  geometry and is recorded in `docs/dependency-map.md`.
- Redundancy check: DXF uses one numeric formatter, one LWPOLYLINE emitter for
  polyline-like geometry, and one stroke style-pair helper. Raster sidecar
  filenames and handles come from one deterministic registry.

ADR/rule impact:

- No new ADR is required. The dependency map records the intentional
  PDF-sampled geometry edge and the raster image sidecar edge.

## Domain Definitions

- A DXF point is an InkGen `(x, y)` point converted by `DXFRenderContext`.
- DXF context coordinates are finite non-boolean numeric values.
- `canvas_height` is either `None` or a finite non-boolean numeric value greater
  than or equal to zero.
- If `canvas_height is None`, point coordinates are unchanged except for float
  coercion.
- If `canvas_height == H`, DXF y is `H - y`.
- A DXF layer is the explicit string `layer` argument, else the group label,
  else `"0"`. Empty explicit layer strings use the existing fallback path.
- Closed paths are paths whose final valid `PathCommand.type.upper()` is `"Z"`.
- Rounded rectangles use 4 sampled points per corner and omit a duplicate final
  point when it equals the first point.
- Text entity height is `font_size * 25.4 / 72.0`; newlines are replaced with
  spaces.
- DXF output is ASCII text and ends with `0\nEOF\n`.
- DXF file output accepts string and path-like paths that resolve to existing
  directories and rejects non-path, bytes, and empty path values.
- DXF image output stores referenced raster payloads as deterministic PNG
  sidecar files named `imageN.png`.
- Reused identical image payloads share one IMAGEDEF object and one sidecar.
- DXF drawing stroke colors are emitted as group code `420` true-color values
  from validated `#rrggbb` strokes.
- DXF drawing stroke widths are emitted as group code `370` lineweights in
  hundredths of a millimeter, snapped to the nearest standard DXF lineweight.
- Drawing styles with `stroke="none"` omit DXF stroke color and lineweight
  group codes. DXF fill/HATCH entities are out of scope for this slice.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Coordinate conversion | Preserve x and optionally flip y | PO-DXF-001 | `test_dxf_context_and_numeric_format_are_deterministic` | killed |
| Coordinate and canvas-height validation | Reject booleans, non-numeric values, non-finite values, and negative heights | PO-DXF-008 | `test_dxf_context_rejects_malformed_coordinate_boundaries` | killed |
| Layer selection and validation | Explicit string layer, group label fallback, `"0"` fallback, malformed non-string overrides rejected | PO-DXF-002, PO-DXF-009 | `test_dxf_document_layers_and_ascii_text_contract`, `test_dxf_document_layer_fallback_and_write_guard`, `test_dxf_document_rejects_malformed_layer_overrides` | killed |
| File output | String/path-like existing-directory paths write ASCII; malformed paths and missing directories fail before writing | PO-DXF-003 | write-guard test, malformed-path test, and existing DXF generator tests | killed |
| Rounded and sharp rectangles | Emit deterministic closed LWPOLYLINE vertices | PO-DXF-004 | rectangle/closure tests | equivalent survivors documented |
| Path closure | `Z` closes; non-`Z` valid commands remain open | PO-DXF-005 | open/closed path tests | equivalent survivor documented |
| PDF-sampled geometry | Arc, cubic Bezier, regular polygon, and path reuse PDF points | PO-DXF-006 | sampled-geometry test | killed |
| Text and circle entities | Preserve layer, coordinates, height/radius, and newline normalization | PO-DXF-007 | text and circle entity tests | killed |
| Image entities | Emit IMAGE/IMAGEDEF references, write PNG sidecars, and deduplicate identical image assets | PO-DXF-010 | `test_dxf_document_exports_image_references_and_writes_sidecars`, `test_dxf_document_deduplicates_identical_image_sidecars`, `test_dxf_document_assigns_distinct_image_sidecars_and_handles` | raster image gate killed meaningful mutants; equivalent survivors documented |
| Drawing stroke style | Emit stroke true-color and standard lineweight group codes through live DXF document paths | PO-DXF-011 | `test_dxf_entities_emit_drawing_style_color_and_lineweight`, `test_dxf_style_lineweight_uses_standard_values_and_disabled_stroke_omits_codes` | DXF style gate |
| Unsupported groups/components | Fail loudly | Existing `test_dxf_document_rejects_unsupported_groups_and_components` | killed |
| Numeric formatting | Integer-like floats and fixed precision serialize deterministically | Formatting tests and exact entity strings | equivalent survivors documented |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Entity helpers and numeric formatting are deterministic. | `tests/test_dxf_contract.py` |
| Behavioral/condition | yes | The slice defines DXF-P1 renderer behavior. | Tests are marked `@pytest.mark.condition("DXF-P1")`. |
| Failure-mode | yes | Bad coordinates, bad canvas heights, bad layer overrides, bad group types, unsupported components, malformed output paths, and missing directories must fail. | DXF generator and contract tests |
| Integration/live-path | yes | `DXFDocument.add_group()` and `to_dxf_string()` are exercised with neutral drawing groups. | document layer/text tests and existing DXF generator tests |
| Contract/API compatibility | yes | Public `DXFDocument`/`DXFRenderContext` behavior and private proof-critical entity contracts are pinned. | focused DXF gate |
| Property/fuzz | limited yes | Bounded deterministic partitions cover coordinate, layer, closure, and sampled-geometry domains. | DXF-P1 tests |
| Mutation | yes | Renderer branches and entity helpers are proof-critical. | Cosmic Ray result below |
| Security/adversarial | limited yes | No network/auth/SQL/templates are added; file writes reject missing directories and remain ASCII. | write guard and ASCII encode checks |
| Performance/resource | no | DXF emission is linear over existing group components and point lists. | Not applicable |
| Concurrency/race | no | No shared mutable global state or background workers are added. | Not applicable |
| Golden artifact/visual | yes | DXF output is a text artifact. Exact entity strings and vertex lists are checked. | exact text/circle/rectangle/path assertions |
| Regression | yes | The slice protects the DXF modality added for drawing outputs. | focused DXF gate and mutation |

## Mutation Testing Gate

Current result after the finite-boundary hardening update:

- Tool: Cosmic Ray 8.4.6.
- Environment: WSL Python 3.12 virtualenv.
- Config: `tests/mutation/dxf_context_finite_cosmic_ray.toml`.
- Filter: `tests/mutation/filter_dxf_context_finite_work_items.py`.
- Test selection: DXF context deterministic conversion and malformed-boundary
  tests.
- Raw work items: 674.
- Proof-critical work items after filter: 25.
- Killed mutants: 25.
- Surviving mutants: 0.
- Gate result: pass.

Current result after the filepath hardening update:

- Tool: Cosmic Ray 8.4.6.
- Environment: WSL Python 3.12 virtualenv.
- Config: `tests/mutation/dxf_renderer_cosmic_ray.toml`.
- Filter: `tests/mutation/filter_dxf_filepath_work_items.py`.
- Test selection: focused DXF-P1 contract tests.
- Raw work items: 690.
- Proof-critical work items after filter: 7.
- Killed mutants: 7.
- Surviving mutants: 0.
- Gate result: pass.

Current result after the layer-boundary hardening update:

- Tool: Cosmic Ray 8.4.6.
- Environment: WSL Python 3.12 virtualenv.
- Config: `tests/mutation/dxf_layer_cosmic_ray.toml`.
- Filter: `tests/mutation/filter_dxf_layer_work_items.py`.
- Test selection: focused DXF-P1 layer contract tests.
- Raw work items: 705.
- Proof-critical work items after filter: 6.
- Killed mutants: 6.
- Surviving mutants: 0.
- Gate result: pass.

Current result after the raster image reference update:

- Tool: Cosmic Ray 8.4.6.
- Config: `tests/mutation/raster_image_cosmic_ray.toml`.
- Filter: `tests/mutation/filter_raster_image_work_items.py`.
- Test selection: raster image, DOCX image, DXF image/reference, DXF contract,
  and public API tests.
- Raw work items: 9,410.
- Proof-critical work items after filter: 640.
- Killed mutants: 589.
- Surviving mutants: 47, documented as equivalent in
  `docs/proofs/raster-image-contract.md`.
- Incompetent mutants: 4 invalid PDF resource string arithmetic replacements.
- Gate result: pass.

Execution note:

- The WSL mutation environment needs the mutation virtualenv on `PATH` so the
  Cosmic Ray worker command `python -m pytest ...` resolves `python`.

Current result after the stroke style-emission update:

- Tool: Cosmic Ray 8.4.6.
- Config: `tests/mutation/dxf_style_cosmic_ray.toml`.
- Filter: `tests/mutation/filter_dxf_style_work_items.py`.
- Test selection: focused DXF-P1 contract tests.
- Raw work items: 1,020.
- Proof-critical work items after filter: 21.
- Killed mutants: 20.
- Surviving mutants: 1 documented equivalent survivor.
- Equivalent survivor class:
  - `_dxf_style_pairs()` mutating `style.stroke == "none"` to
    `style.stroke >= "none"` is equivalent for the validated `DrawingStyle`
    domain because non-`none` stroke colors are normalized to `#rrggbb`, and
    `#` sorts before `n`.

Equivalent survivor classes:

- `_component_to_entities()` path closure `== "Z"` changed to `>= "Z"`.
  `PathCommand` only accepts valid SVG commands; among valid commands, only
  `"Z"` is greater than or equal to `"Z"`.
- `_rectangle_points()` zero-radius comparisons changed to nonnegative variants.
  `normalize_rectangle_corner_radii()` normalizes valid radii to nonnegative
  values, so `< 0` cases are unreachable in this function.
- `_rectangle_points()` final duplicate-pop checks changed around a branch that
  is unreachable for generated rounded-rectangle point sequences; the sampling
  starts after each already-appended corner endpoint.
- `_append_corner_arc()` range start changed from `1` to `0`; through
  `_rectangle_points()`, the index-0 point duplicates the previously appended
  endpoint and is suppressed.
- `append()` duplicate checks changed to identity/index variants that do not
  alter the generated rounded-rectangle sequence in the proven domain.
- `_format_value()` integer-threshold variants produce the same emitted strings
  for the tested DXF artifact domain because six-decimal formatting with
  trailing-zero stripping serializes integer-like floats identically.

## PO-DXF-001: Coordinate Conversion

### Claim

DXF point conversion preserves x and flips y exactly when a canvas height is
provided.

### Proof Method

`DXFRenderContext.point(x, y)` returns `(x, y)` as finite floats when no canvas
height is configured and `(x, H - y)` as finite floats otherwise. Tests cover
both branches and mutation kills arithmetic/branch changes.

### Conclusion

Proven for finite non-boolean numeric coordinates.

## PO-DXF-008: DXF Numeric Boundaries Fail Closed

### Claim

DXF context coordinates and canvas heights reject malformed numeric values
before DXF entity text is emitted.

### Domain

Public `DXFRenderContext(canvas_height=...)`, `DXFDocument(canvas_height=...)`,
and `DXFRenderContext.point(x, y)` calls.

### Assumptions

Renderer-neutral drawing components validate their own geometry before
`DXFDocument.add_group()` consumes them. This obligation covers direct public
DXF context/document use and the final coordinate conversion boundary.

### Theorem

For all accepted public DXF context/document canvas heights, the stored height
is either `None` or a finite float greater than or equal to zero. For all
accepted public DXF context points, emitted coordinates are finite floats. All
tested booleans, non-numeric values, non-finite values, and negative
canvas-height values raise `TypeError` or `ValueError`.

### Proof Method

`DXFRenderContext.__post_init__()`, `DXFDocument.__init__()`, and
`DXFRenderContext.point()` route public numeric values through one local helper,
`_coerce_finite_float()`. The helper rejects booleans before numeric coercion,
rejects non-numeric values, rejects non-finite floats, and enforces a
nonnegative minimum for `canvas_height`. The condition test covers direct
context, document, x-coordinate, and y-coordinate invalid partitions and
confirms a valid context still converts coordinates deterministically.

### Counterexamples And Exclusions

Negative point coordinates are allowed because InkGen geometry can be
off-canvas. Private mutation of frozen dataclass internals and hostile monkey
patching are excluded.

### Conclusion

Proven for the stated public DXF numeric boundaries.

## PO-DXF-002: Layer Selection

### Claim

DXF entities use the explicit string layer, then group label, then `"0"`.

### Proof Method

`DXFDocument.add_group()` constructs a context with
`layer or group.group_label or "0"`. Tests cover explicit, group-label, and
empty-label fallback cases.

### Conclusion

Proven for `DrawingComponentGroup` inputs.

## PO-DXF-009: DXF Layer Boundaries Fail Closed

### Claim

DXF context and document layer overrides reject malformed values before DXF
artifact text is emitted.

### Domain

Public `DXFRenderContext(layer=...)` and
`DXFDocument.add_group(group, layer=...)` calls.

### Assumptions

`DrawingComponentGroup` validates `group_label` as a string at the neutral
drawing boundary. This obligation covers the public DXF override path and direct
DXF context construction.

### Theorem

For all accepted public DXF layer override values, the stored layer is a string.
All tested boolean, numeric, and arbitrary object overrides raise `TypeError`.
Empty explicit strings preserve the existing fallback contract in
`DXFDocument.add_group()`.

### Proof Method

`DXFRenderContext.__post_init__()` and `DXFDocument.add_group()` route layer
values through `_coerce_dxf_layer()`. The helper accepts only strings and
rejects values that `_format_value()` would otherwise stringify into DXF group
code text. The condition test covers direct context construction, the public
document add path, and the empty-string fallback path.

### Counterexamples And Exclusions

Private mutation of `DrawingComponentGroup.group_label`, hostile monkey
patching, and DXF consumers with stricter layer-name character policies are
outside this slice.

### Conclusion

Proven for the stated public DXF layer override boundaries.

## PO-DXF-003: File Output Guard

### Claim

DXF files write only when the destination path is a string or path-like value
whose destination directory exists.

### Proof Method

`create_dxf()` delegates to `_normalize_output_filepath()` before writing. The
helper accepts string and path-like values through `os.fspath()`, rejects
non-path objects, bytes, and empty paths, checks the parent directory, and then
returns the absolute path for ASCII output. Tests cover valid string and
path-like writes, malformed object/integer/bytes/empty paths, and missing
directories.

### Conclusion

Proven for filesystem paths in the test environment.

## PO-DXF-004: Rectangle Entity Geometry

### Claim

Sharp rectangles emit four closed vertices. Rounded rectangles emit twenty
deterministic sampled vertices without a duplicated final point.

### Proof Method

Tests assert exact sharp rectangle points, exact rounded rectangle points, the
closed LWPOLYLINE flag, and duplicate suppression behavior.

### Conclusion

Proven for declared sharp, zero-radius, and representative rounded rectangles.

## PO-DXF-005: Path Closure

### Claim

Path DXF entities are closed only when the final valid path command is `Z`.

### Proof Method

Tests cover open `M/L` paths and closed `M/L/Z` paths. Mutation survivors around
`>= "Z"` are equivalent because `PathCommand` rejects commands outside the valid
SVG set.

### Conclusion

Proven for valid `PathCommand` sequences.

## PO-DXF-006: PDF-Sampled Geometry Reuse

### Claim

DXF branches for arcs, cubic Beziers, regular polygons, and paths reuse the same
point lists as the corresponding PDF materialization.

### Proof Method

Tests compare emitted DXF vertices to six-decimal rounded
`component.to_component(OutputFormat.PDF).points` for each indirect branch.

### Conclusion

Proven for the representative indirect component set.

## PO-DXF-007: Text And Circle Entities

### Claim

Text and circle DXF entities preserve layer, coordinates, text/radius, and
height conversion.

### Proof Method

Tests assert exact text and circle entity payloads, including y-coordinate flip,
newline-to-space normalization, text height, and circle radius.

### Conclusion

Proven for the stated entity fields.

## PO-DXF-010: Raster Image References

### Claim

DXF image output emits external IMAGE references, writes deterministic PNG
sidecars next to the DXF artifact, and deduplicates identical image assets.

### Proof Method

`DXFDocument.add_group()` routes `ImageDrawing` components through one
`_DXFImageRegistry`. The registry converts the existing `RasterImageAsset` to
PNG bytes, keys definitions by SHA-256 digest, assigns deterministic handles and
filenames, and `create_dxf()` writes registered sidecars before writing the DXF
file. Tests assert IMAGE and IMAGEDEF group codes, the handle reference, flipped
placement vectors, sidecar alpha preservation, and deduplication.

### Conclusion

Proven for static raster sidecar references written by `DXFDocument.create_dxf()`.

## PO-DXF-011: Drawing Stroke Style Group Codes

### Claim

DXF drawing entities emit validated `DrawingStyle` stroke color and stroke
width through live `DXFDocument.add_group()` paths.

### Proof Method

`DXFDocument.add_group()` iterates over neutral drawing primitives and passes
their attached `DrawingStyle` to `_line_entity()`, `_lwpolyline_entity()`, or
`_circle_entity()`. Those entity helpers call `_dxf_style_pairs()`, which emits
group code `420` for the validated stroke true-color integer and group code
`370` for the nearest standard DXF lineweight in hundredths of a millimeter.
The helper omits both codes when `stroke == "none"` so disabled strokes are not
serialized as misleading black defaults.

Tests exercise the public document path with line, rectangle/polyline, and
circle drawing entities, assert exact true-color and lineweight values, assert
standard lineweight snapping, and assert disabled strokes omit both style codes.

### Counterexamples And Exclusions

DXF fill output would require HATCH or other filled-entity semantics and is not
claimed here. Stroke opacity, dash arrays, caps, joins, and miter limits also
remain outside the DXF style domain until there is an explicit DXF contract for
those features.

### Conclusion

Behavioral tests and scoped mutation prove the stated domain with one
equivalent survivor documented above.
