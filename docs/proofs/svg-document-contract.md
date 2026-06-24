# SVG Document Renderer Contract Proof Obligations

This note applies the InkGen Definition of Done to the SVG document renderer
slices. It covers SVG file writing, path boundary validation, include-layer flag
combinations, modeling-layer rebuild behavior, duplicate semantic labels, and
document parameter round trips.

## Scope

The slice covers:

- `IncludeLayer`
- `DocumentSVG.create_svg()`
- `DocumentSVG._normalize_output_path()`
- `DocumentSVG._target_filename()`
- `DocumentSVG._write_svg()`
- `DocumentSVG._iter_layer_groups()`
- `DocumentSVG._add_modeling_layer()`
- `DocumentSVG.create_from_dict()`
- `DocumentSVG._layer_from_svg_dict()`
- `DocumentSVG._layers_from_svg_dict()`

## Architecture Impact

Affected surface:

- `src/InkGen/svg_generator.py`: fixed combined include flags, SVG-specific
  document deserialization, duplicate-label layer traversal, and SVG writer path
  input validation.
- `tests/test_svg_document_contract.py`: SVG-DOC-P1 and SVG-FILEPATH-P2
  condition tests.
- `tests/mutation/svg_document_cosmic_ray.toml`: scoped mutation gate.
- `tests/mutation/filter_svg_document_work_items.py`: proof-critical mutation
  filter.
- `tests/mutation/filter_svg_filepath_work_items.py`: filepath proof-critical
  mutation filter.
- `docs/proofs/svg-document-contract.md`: proof note.

Incoming dependencies:

- Drawing components and component groups feed the base SVG layer.
- Synthetic drawing workflows depend on deterministic file creation and optional
  label/mask overlays.
- `DocumentSVG.parameters` depends on `Layers`, `Layer`, and component-group
  serialization.

Outgoing dependencies:

- SVG rendering depends on `Canvas`, `Document`, `Layer`, `Layers`,
  `ComponentGroup`, `ComponentGroupSVG`, and SVG primitive generators.
- No dependency was added.

Before/after edge changes:

- Before this slice, `IncludeLayer.LABEL | IncludeLayer.MASK` added neither
  modeling layer because equality checks were used against a `Flag`.
- Before this slice, `DocumentSVG.create_from_dict()` used generic
  `Layers.create_from_dict()`, which could not rehydrate `ComponentGroupSVG`
  payloads.
- Before this slice, SVG document traversal used the label lookup map and
  collapsed repeated semantic labels.
- Before the filepath slice, `DocumentSVG.create_svg()` called `os.path`
  directly on unvalidated public input, so malformed path values failed through
  incidental stdlib errors.
- After this slice, include flags use membership checks, SVG documents rehydrate
  SVG groups through SVG-specific helpers while retaining generic-group
  compatibility, renderer traversal includes every stored group, and SVG file
  writers normalize only string/path-like paths before writing.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced.
- Layer check: SVG document behavior remains in the SVG renderer layer.
- Coupling check: no PDF/DXF/document-export dependency was added.
- Redundancy check: SVG document rehydration is local to `DocumentSVG` instead
  of changing generic `Layers` semantics.

ADR/rule impact:

- No new ADR is required. The slice preserves the existing renderer separation
  rule: drawing classes render to SVG/PDF/DXF, while document modalities remain
  separate.

## Domain Definitions

- A single-page SVG document writes `<base>.svg`.
- A multipage SVG document writes `<base>_page_<n>.svg` for each page.
- String and path-like output paths are accepted at the public file-writer
  boundary.
- Non-path objects, bytes paths, and empty paths fail before writing files.
- A missing output directory fails before writing files.
- Include-layer flags are composable: `LABEL | MASK` requests both overlays.
- Label overlays render bbox rectangles.
- Mask overlays render polygonal masks.
- Modeling overlays are rebuilt from current model layers on each render.
- Repeated semantic group labels must remain represented in SVG output and model
  overlays.
- SVG document round-trip reconstruction preserves SVG component payloads and
  remains backward compatible with generic `ComponentGroup` payloads.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Single-page output | Write `<base>.svg` | PO-SVGDOC-001 | file-write test | killed |
| Multipage output | Write numbered page files | PO-SVGDOC-001 | file-write test | killed |
| Path-like output path | Normalize and write | PO-SVGDOC-007 | path-like test | killed |
| Malformed output path | Raise `TypeError` or `ValueError` before writing | PO-SVGDOC-007 | malformed-path tests | killed |
| Missing directory | Raise `ValueError` | Failure-mode test | missing-directory test | killed |
| Combined include flags | Add label and mask overlays | PO-SVGDOC-002 | combined-flag test | killed |
| Label overlay | Render bbox rectangles with dimensions | PO-SVGDOC-003 | label-rectangle test | killed |
| Mask overlay | Render polygon masks | PO-SVGDOC-003 | combined-flag test | killed |
| Stale overlays | Rebuild target model layer | PO-SVGDOC-004 | stale-layer test | killed |
| Duplicate labels | Preserve repeated semantic labels | PO-SVGDOC-005 | duplicate-label test | killed |
| SVG group round trip | Rehydrate `ComponentGroupSVG` | PO-SVGDOC-006 | round-trip test | killed |
| Generic group compatibility | Rehydrate legacy generic groups | PO-SVGDOC-006 | existing SVG generator test | killed |
| Style cache reuse | Populate caller-provided style cache | PO-SVGDOC-006 | round-trip cache assertion | killed |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Private deterministic helpers have direct behavioral effects. | `tests/test_svg_document_contract.py` |
| Behavioral/condition | yes | The slices define SVG-DOC-P1 document-render behavior and SVG-FILEPATH-P2 path-boundary behavior. | Tests are marked `@pytest.mark.condition("SVG-DOC-P1")` and `@pytest.mark.condition("SVG-FILEPATH-P2")`. |
| Failure-mode | yes | Missing output directories and malformed file paths must fail loudly before writing. | missing-directory and malformed-path tests |
| Integration/live-path | yes | `create_svg()` writes files and mutates document overlays. | file, flag, stale-layer, duplicate-label tests |
| Contract/API compatibility | yes | `create_from_dict()` must preserve existing generic-group behavior. | existing SVG generator test plus SVG round-trip test |
| Property/fuzz | limited yes | Deterministic partitions cover single/multi page, missing directory, label/mask/both, duplicate labels, and SVG/generic group payloads. | SVG-DOC-P1 tests |
| Mutation | yes | Proof-critical renderer decisions are mutation tested. | Cosmic Ray result below |
| Security/adversarial | limited yes | The slice writes only explicit local paths and adds no subprocess, network, SQL, or template execution. Malformed path-like boundaries are rejected before write attempts. | missing-directory and malformed-path tests |
| Performance/resource | no | Rendering is linear over pages, layers, groups, and components. | Not applicable |
| Concurrency/race | no | No shared concurrency primitive is added. | Not applicable |
| Golden artifact/visual | yes | SVG XML output is a text artifact. | file and markup assertions |
| Regression | yes | This closes combined flags, SVG round-trip, and duplicate-label traversal regressions. | dedicated tests and mutation |

## Mutation Testing Gate

Current result:

- Tool: Cosmic Ray 8.4.6.
- Environment: WSL Python 3.12 virtualenv.
- Raw work items: 2321.
- Proof-critical work items after filter: 65.
- Killed mutants: 59.
- Equivalent survivors: 6.
- Surviving equivalent mutations:
  - `_target_filename()` changed `self.pages == 1` to `self.pages <= 1`.
    `create_svg()` calls `_target_filename()` only inside `range(1, self.pages
    + 1)`, so the live write path never calls it when `self.pages < 1`.
  - `_add_modeling_layer()` changed `model_type == 'label'` to comparison
    variants that either add an unused `bbox` field to mask entries or are
    equivalent for the private callers `_add_label_layer()` and
    `_add_segmentation_layer()`, which pass the literal strings `'label'` and
    `'mask'`.
- Gate result: pass with documented equivalent survivors.

Additional SVG-FILEPATH-P2 result:

- Tool: Cosmic Ray 8.4.6.
- Environment: WSL Python 3.12 virtualenv.
- Raw work items: 2337.
- Proof-critical work items after filter: 9.
- Killed mutants: 9.
- Survivors: 0.
- Gate result: pass.

## PO-SVGDOC-001: SVG Files Are Written Deterministically

### Claim

SVG document output filenames are deterministic and missing directories fail
loudly.

### Proof Method

Tests write single-page and multipage documents to a temporary directory and
assert exact target filenames and payload content. A failure-mode test asserts a
missing output directory raises `ValueError`.

### Conclusion

Proven for the declared file-targeting contract.

## PO-SVGDOC-002: Include Flags Compose

### Claim

`IncludeLayer` values can be combined to request label and mask overlays in one
render.

### Proof Method

Tests call `create_svg(..., include=IncludeLayer.LABEL | IncludeLayer.MASK)`,
assert both layers exist, and assert the mask layer contains polygonal
components.

### Conclusion

Proven for combined label/mask include requests.

## PO-SVGDOC-003: Modeling Layers Render the Correct Primitive Type

### Claim

Label layers render bbox rectangles and mask layers render polygonal masks.

### Proof Method

Tests assert label-layer components are `RectangleSVG` instances with expected
position and dimensions, and mask-layer components include `PolygonalSVG`.

### Conclusion

Proven for rectangular bbox and polygonal mask outputs in the tested geometry
domain.

## PO-SVGDOC-004: Modeling Layers Are Rebuilt

### Claim

Repeated renders rebuild the target modeling layer from current model-layer
content instead of accumulating stale overlays.

### Proof Method

Tests render labels, add a new base group, render labels again, and assert the
label layer reflects the current source groups.

### Conclusion

Proven for repeated label renders.

## PO-SVGDOC-005: Duplicate Semantic Labels Are Preserved

### Claim

Multiple groups with the same semantic label remain represented in rendered and
modeling output.

### Proof Method

Tests add two base groups with the same label and assert the generated label
layer keeps both by preserving the first label and suffixing the second.

### Conclusion

Proven for duplicate source labels in SVG document traversal.

## PO-SVGDOC-006: Document Round Trip Preserves Group Payloads

### Claim

`DocumentSVG.create_from_dict()` rehydrates SVG component groups and remains
compatible with existing generic component-group payloads.

### Proof Method

Tests round-trip a `ComponentGroupSVG` document, assert parameter equality,
assert rendered SVG component markup, and assert the caller-provided style cache
is populated. Existing SVG generator tests cover generic `ComponentGroup`
round-trip compatibility.

### Conclusion

Proven for SVG and generic group payloads in the current serialization domain.

## PO-SVGDOC-007: SVG File Paths Fail At The Boundary

### Claim

For every public `DocumentSVG.create_svg()` path input in the declared domain,
string and `os.PathLike[str]` values are normalized before writing, while
non-path objects, byte paths, and empty strings are rejected before any file
write is attempted.

### Proof Method

The implementation applies `os.fspath()` once at the SVG writer boundary,
accepts only resulting `str` values, rejects empty strings, then passes the
normalized value into the existing deterministic filename and missing-directory
logic. Tests cover a `pathlib.Path` live write, object/integer/bytes rejection,
empty-string rejection, and the existing missing-directory failure. The
SVG-FILEPATH-P2 Cosmic Ray gate mutates proof-critical validation rows and all
9 mutants are killed.

### Conclusion

Proven for the declared string/path-like SVG writer domain. Private mutation of
post-normalization internal variables and race conditions between directory
validation and file opening are outside this proof obligation.
