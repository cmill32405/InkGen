# Line Renderer Contract Proof Obligations

This note applies the InkGen Definition of Done to the LINE-P1 line
renderer-contract slice. It focuses on two-point coordinate validation and
preserving endpoints through SVG, PDF, neutral drawing recipes, and DXF export.

## Scope

The slice covers shared two-point validation in `src/InkGen/component.py`, SVG
serialization in `src/InkGen/svg_generator.py`, PDF serialization in
`src/InkGen/pdf_generator.py`, renderer-neutral materialization in
`src/InkGen/drawing_components.py`, and DXF export in
`src/InkGen/dxf_generator.py`.

The public behavior under review is:

- `StandardDrawingComponent.__init__()`
- `StandardDrawingComponent.point_1`
- `StandardDrawingComponent.point_2`
- `StandardDrawingComponent.points`
- `StandardDrawingComponent.bbox`
- `StandardDrawingComponent.convex_hull`
- `LineSVG.generate_svg()`
- `LinePDF.generate_pdf()`
- `LineDrawing.__post_init__()`
- `LineDrawing.to_component(OutputFormat.SVG/PDF)`
- `DXFDocument.add_group()` for `LineDrawing`

## Architecture Impact

Affected surface:

- `src/InkGen/component.py`: shared finite nonnegative two-point coordinate
  validation.
- `src/InkGen/svg_generator.py`: concrete SVG open path output.
- `src/InkGen/pdf_generator.py`: concrete PDF open stroked path output.
- `src/InkGen/drawing_components.py`: neutral line recipe materialization.
- `src/InkGen/dxf_generator.py`: DXF `LINE` entity output.
- `tests/test_line_contract.py`: validation, renderer, materialization, and
  live DXF evidence.

Incoming dependencies:

- Rectangles, circles, single-dimension components, and line renderers inherit
  the shared two-point boundary.
- SVG/PDF fixture generation relies on stable endpoint order.
- DXF export relies on neutral line recipes becoming `LINE` entities, not
  closed polylines.

Outgoing dependencies:

- Point validation depends on Shapely `Point` and Python `math.isfinite()`.
- SVG output depends on shared SVG style serialization.
- PDF output depends on `_drawing_pdf()` and style operator generation.
- DXF output depends on `DXFRenderContext.point()` and `_line_entity()`.
- Neutral materialization depends on `normalize_output_format()` and lazy
  concrete renderer imports.

Before/after edge changes:

- Before this slice, `StandardDrawingComponent` let Shapely coerce `nan`,
  `inf`, and boolean coordinates into stored points.
- After this slice, malformed, boolean, non-finite, and negative coordinates
  fail at construction or setter boundaries.
- Existing internal `Point` setter paths remain supported for size/radius
  updates in inherited components.
- The `LINE-DRAWING-GEOMETRY-P2` continuation found that `LineDrawing` could
  store malformed or negative endpoint payloads until SVG/PDF materialization
  failed. The same payloads could hydrate through
  `FlowDocument.create_from_dict()` into public neutral drawing state.
- After `LINE-DRAWING-GEOMETRY-P2`, neutral line endpoints are validated and
  normalized at construction before direct materialization, serialization, or
  FlowDocument hydration can expose malformed state.
- No new dependency edge or third-party dependency was introduced.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced. Neutral drawing classes still lazy-import
  concrete renderers only inside `to_component()`.
- Layer check: coordinate validity remains in the shared component layer, while
  renderers only serialize valid geometry.
- Coupling check: SVG/PDF/DXF share the component endpoint contract without
  sharing renderer-specific syntax.
- Redundancy check: no duplicate line validation was added to renderers.

Evidence source and freshness:

- Source-backed: `component.py`, `svg_generator.py`, `pdf_generator.py`,
  `drawing_components.py`, `dxf_generator.py`, and adjacent tests were read
  before editing.
- Test-backed: focused tests in `test_line_contract.py` exercise valid
  geometry, invalid failures, SVG/PDF exact output, serialization, neutral
  materialization, and live DXF export.
- No architecture claim in this note relies only on stale memory.

ADR/rule impact:

- No new ADR is required because the slice preserves the existing dependency
  map and dependency-free renderer policy.
- A future change that allows negative drawing coordinates should record an ADR
  because it changes the shared `StandardDrawingComponent` boundary.

## Domain Definitions

- A valid line is two ordered points.
- Each coordinate value must be numeric, finite, not boolean, and nonnegative.
- Zero coordinates are valid.
- Neutral line endpoints are normalized to float pairs at `LineDrawing`
  construction.
- The public point order is `[point_1, point_2]`.
- SVG and PDF outputs are open paths.
- DXF output is a `LINE` entity.

## Fix Log

- `StandardDrawingComponent` now validates point shape, numeric coercion,
  boolean rejection, finite coordinates, and nonnegative coordinates before
  storing endpoints.
- Existing internal setters that pass a Shapely `Point` remain supported.
- `LinePDF.generate_pdf()` is proven to ignore fill style and stroke only.
- DXF line export is proven to emit a `0/LINE` entity pair and apply optional
  canvas-height Y inversion.
- `LineDrawing.__post_init__()` now validates and normalizes both endpoint
  pairs before renderer materialization or FlowDocument hydration can hold
  malformed neutral line state.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid two-point line | Preserve endpoints, bbox, hull | PO-LINE-001 | `test_line_component_preserves_points_bbox_and_hull` | killed/equivalent |
| Zero coordinate endpoints | Preserve as valid geometry | PO-LINE-001 | same | killed/equivalent |
| Malformed, boolean, non-finite, or negative endpoints | Reject at boundary | PO-LINE-002 | `test_line_component_rejects_invalid_point_boundaries` | killed/equivalent |
| Internal Shapely `Point` setter path | Preserve existing inherited component behavior | PO-LINE-002 | same | killed/equivalent |
| SVG output | Emit exact open path | PO-LINE-003 | `test_line_svg_emits_exact_open_path` | killed/equivalent |
| PDF output | Emit exact open stroked path with no fill | PO-LINE-004 | `test_line_pdf_emits_exact_open_stroked_path` | killed/equivalent |
| Serialization | Preserve parameters round trip | PO-LINE-005 | `test_line_primitives_round_trip_parameters` | killed/equivalent |
| Neutral materialization | Materialize to `LineSVG`/`LinePDF` | PO-LINE-006 | `test_line_drawing_materializes_svg_and_pdf_components` | killed/equivalent |
| Neutral valid endpoints | Normalize before public state is exposed | PO-LINE-008 | `test_line_drawing_normalizes_geometry_before_materialization` | killed/equivalent |
| Neutral malformed endpoints | Reject at construction and FlowDocument hydration | PO-LINE-008 | `test_line_drawing_rejects_malformed_geometry_payloads`, `test_flow_document_hydration_rejects_malformed_line_geometry_payloads` | killed/equivalent |
| DXF output | Emit `LINE` entity with transformed endpoints | PO-LINE-007 | `test_dxf_line_drawing_exports_line_entity_with_canvas_transform` | killed/equivalent |
| Negative-coordinate drawing systems | Excluded from proven domain | Explicit exclusion | Not applicable | Out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Validation and geometry access are deterministic. | LINE-P1 tests named above |
| Behavioral/condition | yes | LINE-P1 defines line behavior across validation and renderers. | Tests are marked `@pytest.mark.condition("LINE-P1")`. |
| Failure-mode | yes | Invalid endpoints must fail before rendering. | Invalid-boundary test |
| Integration/live-path | yes | DXF proof exercises `DXFDocument.add_group()`. | DXF test |
| Contract/API compatibility | yes | Valid lines preserve endpoint order and serialization. | Geometry and round-trip tests |
| Property/fuzz | limited | This slice proves representative endpoint partitions. | Edge matrix above |
| Mutation | yes | Validation, output paths, materialization, and DXF entity generation are proof-critical. | Mutation result recorded below |
| Security/adversarial | no | The slice adds no file path, network, subprocess, auth, secrets, SQL, template, deserialization, font, image, or active-content surface. | Not applicable |
| Performance/resource | no | The slice adds constant-time validation over two points. | Code inspection |
| Concurrency/race | no | The slice adds no shared mutable global state, workers, sessions, locks, queues, or temp-file coordination. | Not applicable |
| Golden artifact/visual | yes | SVG/PDF/DXF endpoint geometry must be stable enough for synthetic fixtures. | Exact output tests |
| Regression | yes | This closes invalid two-point coordinate acceptance at the shared component boundary. | Failure-mode tests and adjacent renderer tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Weakening coordinate shape, boolean, finite, or nonnegative validation should
  fail invalid-input tests.
- Changing zero-coordinate handling should fail valid-geometry tests.
- Changing SVG or PDF endpoint operators should fail exact renderer tests.
- Redirecting `LineDrawing.to_component()` should fail materialization tests.
- Weakening neutral line endpoint validation should fail direct neutral recipe
  and FlowDocument hydration tests.
- Changing DXF entity type, layer, endpoint codes, z coordinates, or Y inversion
  should fail live DXF tests.

Current result:

- Cosmic Ray 8.4.6, scoped to line validation, SVG/PDF generation, neutral
  materialization, and DXF export: 116 work items, 114 killed, and 2 survived.
- The mutation run exposed and the tests closed real gaps for zero-coordinate
  preservation, all negative-coordinate branches, internal Shapely `Point`
  setter compatibility, PDF no-fill behavior, and DXF `0/LINE` entity coding.
- Equivalent survivors:
  - `target is OutputFormat.SVG` changed to `target == OutputFormat.SVG`.
    `normalize_output_format()` returns an `OutputFormat` member, so identity
    and equality are equivalent for this enum-domain comparison.
  - `target is OutputFormat.SVG` changed to `target >= OutputFormat.SVG`.
    `OutputFormat.SVG` is the first supported string enum value in this
    normalized two-format branch; existing SVG and PDF materialization
    assertions cover the reachable outcomes.
- `LINE-DRAWING-GEOMETRY-P2` continuation:
  - Cosmic Ray 8.4.6, scoped to `_coerce_point_pair()`,
    `_coerce_non_negative_point_pair()`, and `LineDrawing.__post_init__()`:
    60 proof-critical work items.
  - Result: 58 killed, 2 survived and classified equivalent.
  - Equivalent survivors:
    - `*` changed to `/` in `_coerce_point_pair(value, *, name)`.
    - `*` changed to `/` in `_coerce_non_negative_point_pair(value, *, name)`.
    - Both helpers are called with `value` positionally and `name` by keyword in
      the declared domain. Changing `value` from positional-or-keyword to
      positional-only does not change public construction or hydration behavior.

## PO-LINE-001: Valid Geometry Is Preserved

### Claim

Valid line endpoints preserve point order and expose correct `points`, `bbox`,
and `convex_hull` geometry.

### Domain

All lines constructed with two finite nonnegative numeric endpoint pairs.

### Proof Method

`_coerce_point()` normalizes each endpoint to a finite float pair.
`point_1`, `point_2`, `points`, `bbox`, and `convex_hull` read from stored
Shapely points.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-LINE-002: Invalid Geometry Fails At Boundary

### Claim

Invalid line endpoints raise `ValueError` or `TypeError` at construction or
setter time.

### Domain

Malformed, nonnumeric, non-finite, boolean, and negative endpoint inputs.

### Proof Method

`_coerce_point()` rejects malformed, boolean, and non-finite coordinates before
Shapely coercion. `_check_inputs()` rejects negative coordinates. Construction
and setter paths both use the same validation.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-LINE-003: SVG Emits Open Path

### Claim

`LineSVG.generate_svg()` emits a path that moves to `point_1` and draws one
line segment to `point_2`.

### Domain

All `LineSVG` instances with valid endpoints.

### Proof Method

The exact SVG output assertion checks style, `M`, `L`, endpoint order, and id.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-LINE-004: PDF Emits Open Stroked Path

### Claim

`LinePDF.generate_pdf()` emits an open stroked path and never fills the line.

### Domain

All `LinePDF` instances with valid endpoints, including styles with non-`none`
fill colors.

### Proof Method

The exact PDF output assertion checks graphics-state setup, move/line
operators, the absence of close/fill behavior, and final stroke operator.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-LINE-005: Serialization Preserves Line Parameters

### Claim

SVG and PDF line primitives recreate from their own serialized parameters.

### Domain

All `LineSVG` and `LinePDF` instances with valid endpoints and serializable
styles.

### Proof Method

`parameters` stores endpoints and style. `create_from_dict()` reconstructs
endpoints and style before calling the class constructor.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-LINE-006: Neutral Line Materializes To SVG And PDF

### Claim

`LineDrawing.to_component()` preserves endpoints when materializing to SVG or
PDF components.

### Domain

All `LineDrawing` instances with supported output formats `SVG` and `PDF`.

### Proof Method

`LineDrawing.to_component()` normalizes the requested format. SVG returns
`LineSVG(self.point_1, self.point_2, self.style)`. PDF returns
`LinePDF(self.point_1, self.point_2, self.style)`.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-LINE-007: DXF Exports Line Entity

### Claim

DXF export for a neutral `LineDrawing` emits one `LINE` entity with transformed
endpoint coordinates.

### Domain

All valid neutral `LineDrawing` instances exported through
`DXFDocument.add_group()`.

### Proof Method

`DXFDocument.add_group()` iterates over neutral components.
`_component_to_entities()` matches `LineDrawing` and returns
`_line_entity(component.point_1, component.point_2, context)`.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-LINE-008: Neutral Line Geometry Is Validated Before Public State

### Claim

`LineDrawing` cannot expose malformed or negative endpoint geometry through
direct construction, materialization, serialization, or FlowDocument hydration.

### Domain

All `LineDrawing` instances created directly and all serialized `LineDrawing`
payloads hydrated through `FlowDocument.create_from_dict()`.

### Assumptions

The neutral line recipe should match the concrete line component endpoint
contract: each endpoint is a finite two-value numeric pair, boolean coordinates
are invalid, and coordinates must be greater than or equal to zero.

### Proof Method

`LineDrawing.__post_init__()` routes every public construction path, including
FlowDocument drawing hydration, through `_coerce_non_negative_point_pair()`.
That wrapper delegates shape, boolean, numeric, and finite checks to
`_coerce_point_pair()` and then rejects negative coordinates before storing the
normalized float pairs. Direct condition tests cover valid zero endpoints and
malformed endpoint partitions. The FlowDocument condition test mutates
serialized line payloads and proves malformed endpoints cannot hydrate into
returned document state.

### Counterexamples And Exclusions

Private mutation after construction remains outside the public contract. The
slice does not change concrete line renderer output, DXF entity semantics, or
the existing nonnegative drawing-coordinate policy.

### Conclusion

Proven for the stated public construction and FlowDocument hydration domain
after focused tests and scoped mutation pass.

## Current Slice Decision

The slice keeps InkGen's existing nonnegative drawing-coordinate boundary and
adds finite numeric validation before Shapely coercion. This prevents invalid
geometry from reaching SVG, PDF, DXF, or downstream parser fixtures while
preserving existing inherited component update paths.

The `LINE-DRAWING-GEOMETRY-P2` continuation keeps renderer output unchanged
while moving malformed neutral line endpoint rejection to the renderer-neutral
recipe boundary.
