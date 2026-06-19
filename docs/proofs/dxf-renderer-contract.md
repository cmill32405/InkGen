# DXF Renderer Contract Proof Obligations

This note applies the InkGen Definition of Done to the DXF-P1 renderer slice.
It covers dependency-free ASCII DXF output for renderer-neutral drawing recipes,
coordinate conversion, entity dispatch, rounded rectangle sampling, path closure
flags, text/circle entities, file output guards, and PDF-sampled geometry reuse.

## Scope

The slice covers:

- `DXFRenderContext.point()`
- `DXFDocument.add_group()`
- `DXFDocument.to_dxf_string()`
- `DXFDocument.create_dxf()`
- `_component_to_entities()`
- `_rectangle_points()` and `_append_corner_arc()`
- `_line_entity()`, `_lwpolyline_entity()`, `_text_entity()`, and
  `_circle_entity()`
- `_format_value()`

The slice does not change DXF implementation code. It adds condition-marked
tests, a scoped mutation gate, and this proof note.

## Architecture Impact

Affected surface:

- `tests/test_dxf_contract.py`: DXF-P1 condition tests.
- `tests/mutation/dxf_renderer_cosmic_ray.toml`: scoped Cosmic Ray gate.
- `tests/mutation/filter_dxf_renderer_work_items.py`: proof-critical mutation
  filter.
- `docs/proofs/dxf-renderer-contract.md`: proof note.

Incoming dependencies:

- Renderer-neutral drawing recipes use `DXFDocument` to export drawing groups.
- Synthetic drawing workflows rely on deterministic ASCII DXF output.
- Curves, arcs, regular polygons, and paths reuse PDF-sampled geometry through
  `component.to_component(OutputFormat.PDF)`.

Outgoing dependencies:

- `dxf_generator.py` depends on renderer-neutral drawing classes and
  `normalize_rectangle_corner_radii()`.
- Indirect sampled geometry depends on the existing PDF component point
  contracts for arcs, curves, paths, and regular polygons.
- No dependency was added.

Before/after edge changes:

- No source dependency changed.
- The proof makes the existing `dxf_generator.py -> PDF sampled geometry`
  cross-layer edge explicit and tested.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced.
- Layer check: DXF remains a concrete renderer consuming neutral drawing
  recipes.
- Coupling check: the PDF-sampled geometry dependency remains limited to point
  geometry and is recorded in `docs/dependency-map.md`.
- Redundancy check: DXF uses one numeric formatter and one LWPOLYLINE emitter
  for polyline-like geometry.

ADR/rule impact:

- No new ADR is required. The existing dependency-map entry already records the
  intentional PDF-sampled geometry edge.

## Domain Definitions

- A DXF point is an InkGen `(x, y)` point converted by `DXFRenderContext`.
- If `canvas_height is None`, point coordinates are unchanged except for float
  coercion.
- If `canvas_height == H`, DXF y is `H - y`.
- A DXF layer is the explicit `layer` argument, else the group label, else
  `"0"`.
- Closed paths are paths whose final valid `PathCommand.type.upper()` is `"Z"`.
- Rounded rectangles use 4 sampled points per corner and omit a duplicate final
  point when it equals the first point.
- Text entity height is `font_size * 25.4 / 72.0`; newlines are replaced with
  spaces.
- DXF output is ASCII text and ends with `0\nEOF\n`.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Coordinate conversion | Preserve x and optionally flip y | PO-DXF-001 | `test_dxf_context_and_numeric_format_are_deterministic` | killed |
| Layer selection | Explicit layer, group label fallback, `"0"` fallback | PO-DXF-002 | `test_dxf_document_layers_and_ascii_text_contract`, `test_dxf_document_layer_fallback_and_write_guard` | killed |
| File output | Existing directories write ASCII; missing directories fail | PO-DXF-003 | write-guard test and existing DXF generator tests | killed |
| Rounded and sharp rectangles | Emit deterministic closed LWPOLYLINE vertices | PO-DXF-004 | rectangle/closure tests | equivalent survivors documented |
| Path closure | `Z` closes; non-`Z` valid commands remain open | PO-DXF-005 | open/closed path tests | equivalent survivor documented |
| PDF-sampled geometry | Arc, cubic Bezier, regular polygon, and path reuse PDF points | PO-DXF-006 | sampled-geometry test | killed |
| Text and circle entities | Preserve layer, coordinates, height/radius, and newline normalization | PO-DXF-007 | text and circle entity tests | killed |
| Unsupported groups/components | Fail loudly | Existing `test_dxf_document_rejects_unsupported_groups_and_components` | killed |
| Numeric formatting | Integer-like floats and fixed precision serialize deterministically | Formatting tests and exact entity strings | equivalent survivors documented |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Entity helpers and numeric formatting are deterministic. | `tests/test_dxf_contract.py` |
| Behavioral/condition | yes | The slice defines DXF-P1 renderer behavior. | Tests are marked `@pytest.mark.condition("DXF-P1")`. |
| Failure-mode | yes | Bad group types, unsupported components, and missing directories must fail. | DXF generator and contract tests |
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

Current result:

- Tool: Cosmic Ray 8.4.6.
- Environment: WSL Python 3.12 virtualenv.
- Raw work items: 629.
- Proof-critical work items after filter: 201.
- Killed mutants: 182.
- Equivalent survivors: 19.
- Gate result: pass with documented equivalent survivors.

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

`DXFRenderContext.point(x, y)` returns `(float(x), float(y))` when no canvas
height is configured and `(float(x), float(H - y))` otherwise. Tests cover both
branches and mutation kills arithmetic/branch changes.

### Conclusion

Proven for numeric coordinates.

## PO-DXF-002: Layer Selection

### Claim

DXF entities use the explicit layer, then group label, then `"0"`.

### Proof Method

`DXFDocument.add_group()` constructs a context with
`layer or group.group_label or "0"`. Tests cover explicit, group-label, and
empty-label fallback cases.

### Conclusion

Proven for `DrawingComponentGroup` inputs.

## PO-DXF-003: File Output Guard

### Claim

DXF files write only when the destination directory exists.

### Proof Method

`create_dxf()` resolves the target path, checks the parent directory, raises for
missing directories, and writes ASCII output otherwise. Tests cover both
branches.

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
