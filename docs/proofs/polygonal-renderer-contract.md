# Polygonal Renderer Contract Proof Obligations

This note applies the InkGen Definition of Done to the POLYGON-P1 irregular
polygon renderer-contract slice. It focuses on rejecting invalid polygon
geometry at the component boundary and preserving valid vertex order through
SVG, PDF, neutral drawing recipes, and DXF export.

## Scope

The slice covers polygon validation and geometry access in
`src/InkGen/component.py`, SVG serialization in `src/InkGen/svg_generator.py`,
PDF serialization in `src/InkGen/pdf_generator.py`, renderer-neutral
materialization in `src/InkGen/drawing_components.py`, and DXF export in
`src/InkGen/dxf_generator.py`.

The public behavior under review is:

- `PolygonalDrawingComponent.__init__()`
- `PolygonalDrawingComponent.points`
- `PolygonalDrawingComponent.bbox`
- `PolygonalDrawingComponent.convex_hull`
- `PolygonalDrawingComponent.parameters/create_from_dict()`
- `PolygonalSVG.generate_svg()`
- `PolygonalPDF.generate_pdf()`
- `PolygonalDrawing.__post_init__()`
- `PolygonalDrawing.to_component(OutputFormat.SVG/PDF)`
- `FlowDocument.create_from_dict()` hydration of serialized
  `PolygonalDrawing` payloads
- `DXFDocument.add_group()` for `PolygonalDrawing`

## Architecture Impact

Affected surface:

- `src/InkGen/component.py`: shared irregular polygon validation and geometry.
- `src/InkGen/svg_generator.py`: concrete SVG path output.
- `src/InkGen/pdf_generator.py`: concrete PDF closed-path output.
- `src/InkGen/drawing_components.py`: neutral polygon recipe materialization.
- `src/InkGen/dxf_generator.py`: closed DXF polyline output.
- `tests/test_polygonal_contract.py`: validation, renderer, materialization,
  and live DXF evidence.
- `tests/test_flow_document_contract.py`: dependent flow-document drawing
  hydration path coverage.
- `tests/mutation/polygonal_drawing_geometry_cosmic_ray.toml`: neutral polygon
  mutation gate.
- `tests/mutation/filter_polygonal_drawing_geometry_work_items.py`: neutral
  polygon mutation filter.

Incoming dependencies:

- Label, mask, collision, and text-fitting paths rely on polygon `points`,
  `bbox`, `convex_hull`, and `polygon` being valid Shapely geometry.
- SVG/PDF fixture generation relies on deterministic vertex order.
- DXF export relies on neutral polygon recipes becoming closed `LWPOLYLINE`
  entities.
- `FlowDocument.create_from_dict()` hydrates serialized drawing payloads by
  dispatching to `PolygonalDrawing(style=style, **payload)`.

Outgoing dependencies:

- Polygon validation depends on Shapely `Polygon`, Python `math.isfinite()`,
  and local style handling.
- SVG output depends on shared SVG style serialization.
- PDF output depends on `_path_from_points()` and `_drawing_pdf()`.
- DXF output depends on `_lwpolyline_entity()`.
- Neutral materialization depends on `normalize_output_format()` and lazy
  concrete renderer imports.

Before/after edge changes:

- Before this slice, `PolygonalDrawingComponent` checked only point count and
  point arity before constructing Shapely polygons.
- After this slice, nonnumeric, non-finite, boolean, collinear, empty,
  self-intersecting, and non-positive-area polygons fail at construction or
  setter boundaries.
- Before the neutral slice, `PolygonalDrawing` could store malformed point
  payloads until SVG/PDF/DXF materialization or flow-document output.
- After the neutral slice, direct neutral construction and `FlowDocument`
  hydration reject malformed polygon payloads before public neutral drawing
  state is exposed.
- Before `POLYGONAL-DRAWING-LIVE-POINTS-P2`, callers could mutate the public
  `PolygonalDrawing.points` list after construction and bypass the constructor
  polygon validator before SVG/PDF materialization.
- After `POLYGONAL-DRAWING-LIVE-POINTS-P2`, `PolygonalDrawing.to_component()`
  revalidates the current public points list through the shared polygon
  component contract before constructing `PolygonalSVG` or `PolygonalPDF`.
- No new dependency edge or third-party dependency was introduced.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced. Neutral drawing classes still lazy-import
  concrete renderers only inside `to_component()`.
- Layer check: polygon validity remains in the shared component layer, while
  renderers only serialize valid geometry.
- Coupling check: SVG/PDF/DXF share the component geometry contract without
  sharing renderer-specific syntax.
- Redundancy check: no duplicate polygon validation was added to renderers.
- Redundancy check for the neutral boundary: `PolygonalDrawing` delegates to
  the existing concrete `PolygonalDrawingComponent` validation source of truth.

Evidence source and freshness:

- Source-backed: `component.py`, `svg_generator.py`, `pdf_generator.py`,
  `drawing_components.py`, `dxf_generator.py`, `docs/dependency-map.md`, and
  adjacent tests were read before editing.
- Test-backed: focused tests in `test_polygonal_contract.py` exercise valid
  geometry, invalid failures, SVG/PDF exact output, serialization, neutral
  materialization, and live DXF export.
- No architecture claim in this note relies only on stale memory.

ADR/rule impact:

- No new ADR is required because the slice preserves the existing dependency
  map and dependency-free renderer policy.
- A future change that repairs invalid polygons instead of rejecting them should
  record an ADR because it changes boundary semantics.

## Domain Definitions

- A valid irregular polygon is an ordered list or tuple with at least three
  coordinate pairs.
- Each coordinate value must be numeric, finite, and not boolean.
- The resulting Shapely polygon must be non-empty, valid, and have positive
  area.
- The public point order is the exterior vertex order without the closing
  duplicate.
- Neutral `PolygonalDrawing` mirrors the concrete component domain and stores
  the normalized point list returned by `PolygonalDrawingComponent`.
- If callers mutate the public `PolygonalDrawing.points` list after
  construction, materialization revalidates the current list through the same
  concrete polygon boundary.
- Serialized neutral polygon payloads hydrated through `FlowDocument` must
  satisfy the same polygon boundary.
- SVG and PDF outputs are closed paths.
- DXF output is a closed `LWPOLYLINE`.

## Fix Log

- `PolygonalDrawingComponent` now validates numeric finite coordinate pairs.
- Boolean coordinate values are rejected instead of being coerced to `0.0` or
  `1.0`.
- Degenerate, empty, self-intersecting, and zero-area polygons are rejected.
- The points setter uses the same validation path as construction.
- `PolygonalDrawing.__post_init__()` now validates through
  `PolygonalDrawingComponent` and stores normalized points before
  materialization.
- `PolygonalDrawing.to_component()` now revalidates the live public `points`
  list through `PolygonalDrawingComponent` before SVG/PDF materialization.
- Added direct neutral and `FlowDocument` hydration tests for malformed
  polygon payloads.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid concave/irregular polygon | Preserve point order, bbox, area, hull | PO-POLYGON-001 | `test_polygonal_component_preserves_valid_irregular_geometry` | Must be killed or proven equivalent |
| Too few points | Reject with `InvalidPolygonError` | PO-POLYGON-002 | `test_polygonal_component_rejects_invalid_inputs` | Must be killed or proven equivalent |
| Wrong arity or non-sequence points | Reject with `InvalidPolygonError` | PO-POLYGON-002 | same | Must be killed or proven equivalent |
| Nonnumeric, non-finite, boolean coordinates | Reject with `InvalidPolygonError` | PO-POLYGON-002 | same | Must be killed or proven equivalent |
| Collinear or self-intersecting coordinates | Reject with `InvalidPolygonError` | PO-POLYGON-002 | same | Must be killed or proven equivalent |
| SVG output | Emit exact closed SVG path | PO-POLYGON-003 | `test_polygonal_svg_emits_exact_closed_path` | Must be killed or proven equivalent |
| PDF output | Emit exact closed PDF path | PO-POLYGON-004 | `test_polygonal_pdf_emits_exact_closed_path` | Must be killed or proven equivalent |
| Serialization | Preserve parameters round trip | PO-POLYGON-005 | `test_polygonal_primitives_round_trip_parameters` | Must be killed or proven equivalent |
| Neutral materialization | Materialize to `PolygonalSVG`/`PolygonalPDF` | PO-POLYGON-006 | `test_polygonal_drawing_materializes_svg_and_pdf_components` | Must be killed or proven equivalent |
| DXF output | Emit closed `LWPOLYLINE` vertices | PO-POLYGON-007 | `test_dxf_polygonal_drawing_exports_closed_polyline` | Must be killed or proven equivalent |
| Neutral polygon construction | Normalize valid point payloads and reject malformed polygon payloads before materialization | PO-POLYGON-008 | `test_polygonal_drawing_normalizes_geometry_before_materialization`; `test_polygonal_drawing_rejects_malformed_geometry_payloads` | mutation target |
| Serialized neutral polygon hydration | Reject malformed serialized polygon payloads before flow-document public state is exposed | PO-POLYGON-009 | `test_flow_document_hydration_rejects_malformed_polygonal_geometry_payloads` | mutation target |
| Live mutated `PolygonalDrawing.points` list | Reject malformed public point-list mutations before SVG/PDF materialization | PO-POLYGON-010 | `test_polygonal_drawing_revalidates_mutated_points_before_materialization`; `test_polygonal_group_materialization_revalidates_mutated_points` | mutation gate plus static path proof |
| Polygon repair, holes, multipolygons, winding normalization, and fill-rule semantics | Excluded from proven domain | Explicit exclusion | Not applicable | Out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Validation and geometry access are deterministic. | POLYGON-P1 tests named above |
| Behavioral/condition | yes | POLYGON-P1 defines polygon behavior across validation and renderers. POLYGONAL-DRAWING-LIVE-POINTS-P2 defines the live neutral point-list boundary. | Tests are marked `@pytest.mark.condition("POLYGON-P1")`, `@pytest.mark.condition("POLYGONAL-DRAWING-GEOMETRY-P2")`, or `@pytest.mark.condition("POLYGONAL-DRAWING-LIVE-POINTS-P2")`. |
| Failure-mode | yes | Invalid polygons and mutated neutral polygon point lists must fail before rendering. | `test_polygonal_component_rejects_invalid_inputs`; `test_polygonal_drawing_revalidates_mutated_points_before_materialization` |
| Integration/live-path | yes | DXF proof must exercise `DXFDocument.add_group()`. | `test_dxf_polygonal_drawing_exports_closed_polyline` |
| Integration/live-path | yes | Flow-document drawing hydration dispatches to the neutral polygon constructor. | `test_flow_document_hydration_rejects_malformed_polygonal_geometry_payloads` |
| Integration/live-path | yes | Mutated neutral polygon points must fail through `DrawingComponentGroup.to_group()`, not only direct helper calls. | `test_polygonal_group_materialization_revalidates_mutated_points` |
| Contract/API compatibility | yes | Valid polygons preserve point order and serialization. | Geometry and round-trip tests |
| Property/fuzz | limited | This slice proves representative polygon partitions rather than arbitrary computational geometry. | Edge matrix above |
| Mutation | yes | Validation, output paths, materialization, and DXF closure are proof-critical. | Mutation result recorded below |
| Security/adversarial | no | The slice adds no file path, network, subprocess, auth, secrets, SQL, template, deserialization, font, image, or active-content surface. | Not applicable |
| Performance/resource | no | The slice adds only linear validation over input points. | Code inspection |
| Concurrency/race | no | The slice adds no shared mutable global state, workers, sessions, locks, queues, or temp-file coordination. | Not applicable |
| Observability/logging | no | The slice adds no service, background work, external call, or recovered exception path. | Not applicable |
| Golden artifact/visual | yes | SVG/PDF/DXF geometry must be stable enough for synthetic fixtures. | Exact output tests |
| Regression | yes | This closes invalid polygon acceptance at the shared component boundary. | Failure-mode tests |

## Invariants, Preconditions, And Postconditions

Invariants:

- Stored polygon geometry is non-empty, valid, and positive-area.
- Public `points` returns the exterior vertex order without the closing
  duplicate.
- `bbox` reflects the stored Shapely polygon bounds.
- SVG, PDF, and DXF outputs are closed.
- Neutral polygon materialization preserves the point list.
- Neutral polygon materialization revalidates the current public point list
  before concrete renderer construction.

Preconditions:

- Callers provide ordinary numeric coordinate pairs.
- Callers do not mutate inherited private geometry fields behind public
  setters.
- Holes, multipolygons, and repaired invalid polygons are outside this slice.

Postconditions:

- Invalid polygon inputs raise `InvalidPolygonError`.
- Valid polygon construction and point updates store valid Shapely geometry.
- `PolygonalSVG.generate_svg()` emits deterministic closed SVG path data.
- `PolygonalPDF.generate_pdf()` emits deterministic closed PDF path operators.
- `PolygonalDrawing.to_component(OutputFormat.SVG)` returns `PolygonalSVG`.
- `PolygonalDrawing.to_component(OutputFormat.PDF)` returns `PolygonalPDF`.
- `PolygonalDrawing.to_component()` raises `InvalidPolygonError` for mutated
  public point lists that no longer satisfy the polygon boundary.
- `DXFDocument.add_group()` emits a closed `LWPOLYLINE` for each neutral
  `PolygonalDrawing`.

## Mutation Testing Gate

Proof-critical mutation targets:

- Weakening coordinate validation should fail invalid-input tests.
- Changing Shapely validity or positive-area checks should fail invalid-input
  tests.
- Changing point order, closure, or operator output should fail exact renderer
  tests.
- Redirecting `PolygonalDrawing.to_component()` should fail materialization
  tests.
- Weakening the shared polygon validator should fail direct construction,
  hydration, and live-point materialization tests.
- Changing DXF closure flags or vertices should fail live DXF tests.

Current result:

- Cosmic Ray 8.4.6, scoped to polygonal validation, SVG/PDF generation,
  neutral materialization, and DXF export: 87 work items, 84 killed, and 3
  survived.
- The mutation run exposed and the tests closed real gaps for extra coordinate
  arity, non-finite coordinate guard independence, and independent Shapely
  predicate handling.
- Equivalent survivors:
  - `polygon.area <= 0.0` changed to `polygon.area == 0.0`. Shapely polygon
    area is nonnegative, so the two predicates are equivalent for the stored
    polygon domain while zero-area polygons remain rejected.
  - `target is OutputFormat.SVG` changed to `target == OutputFormat.SVG`.
    `normalize_output_format()` returns an `OutputFormat` member, so identity
    and equality are equivalent for this enum-domain comparison.
  - `target is OutputFormat.SVG` changed to `target >= OutputFormat.SVG`.
    `OutputFormat.SVG` is the first supported string enum value in this
    normalized two-format branch; the existing SVG and PDF materialization
    assertions cover the reachable outcomes.
- PASS for the neutral authoring extension. Cosmic Ray generated 4,624 raw
  component/drawing mutants. The `POLYGONAL-DRAWING-GEOMETRY-P2` filter
  reduced this to 58 proof-critical work items. Result: 57 killed, 1 survived.
  The survivor is the equivalent `polygon.area <= 0.0` to
  `polygon.area == 0.0` predicate already classified above; Shapely polygon
  area is nonnegative in the declared domain, so both predicates reject
  zero-area polygons and accept positive-area polygons.
- `POLYGONAL-DRAWING-LIVE-POINTS-P2` refreshed result: after the path-command
  slices shifted `drawing_components.py` line numbers, the neutral polygon
  mutation filter was refreshed and rerun with the live-point tests included.
  Cosmic Ray generated 4,708 raw component/drawing mutants and the refreshed
  filter retained 46 proof-critical work items. Result: 45 killed, 1 survived.
  The survivor is the same equivalent `polygon.area <= 0.0` to
  `polygon.area == 0.0` predicate. Cosmic Ray did not emit a separate
  function-call-removal mutant for the `PolygonalDrawing.to_component()`
  revalidation assignment, so the live wiring claim is covered by static path
  proof plus direct/dependent behavioral tests while the shared validator
  remains mutation-covered.

## PO-POLYGON-001: Valid Geometry Is Preserved

### Claim

Valid irregular polygons preserve point order and expose correct bbox, area,
and convex hull geometry.

### Domain

All `PolygonalDrawingComponent` instances constructed with valid ordinary
coordinate pairs and no holes.

### Proof Method

`_create_valid_polygon()` normalizes points to floats and constructs a Shapely
`Polygon`. `points`, `bbox`, `polygon`, and `convex_hull` read from that stored
polygon.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-POLYGON-002: Invalid Geometry Fails At Boundary

### Claim

Invalid polygon inputs raise `InvalidPolygonError` at construction or setter
time.

### Domain

Too-few, wrong-arity, nonnumeric, non-finite, boolean, collinear, and
self-intersecting polygon inputs.

### Proof Method

`_create_valid_polygon()` returns `None` unless the input is sequence-like,
contains at least three two-value coordinate pairs, all values are numeric and
finite, and the resulting Shapely polygon is valid with positive area.
Construction and setter paths both raise `InvalidPolygonError` when validation
returns `None`.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-POLYGON-003: SVG Emits Closed Path

### Claim

`PolygonalSVG.generate_svg()` emits the polygon vertices in order and closes the
path.

### Domain

All `PolygonalSVG` instances with valid geometry.

### Proof Method

`generate_svg()` iterates over `self.points`, appends each coordinate pair to a
single path data string, and ends the path with `Z`.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-POLYGON-004: PDF Emits Closed Path

### Claim

`PolygonalPDF.generate_pdf()` emits the polygon vertices in order and closes
the path.

### Domain

All `PolygonalPDF` instances with valid geometry.

### Proof Method

`generate_pdf()` calls `_path_from_points(list(self.points), close=True)` and
wraps the result with `_drawing_pdf()`.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-POLYGON-005: Serialization Preserves Polygon Parameters

### Claim

SVG and PDF polygon primitives recreate from their own serialized parameters.

### Domain

All `PolygonalSVG` and `PolygonalPDF` instances with valid geometry and
serializable styles.

### Proof Method

`parameters` stores points and style. `create_from_dict()` reconstructs points
and style before calling the class constructor.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-POLYGON-006: Neutral Polygon Materializes To SVG And PDF

### Claim

`PolygonalDrawing.to_component()` preserves points when materializing to SVG or
PDF components.

### Domain

All `PolygonalDrawing` instances with supported output formats `SVG` and `PDF`.

### Proof Method

`PolygonalDrawing.to_component()` normalizes the requested format and
revalidates the current public point list. SVG returns
`PolygonalSVG(points, self.style)`. PDF returns
`PolygonalPDF(points, self.style)` using the normalized point list.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-POLYGON-007: DXF Exports Closed Polyline

### Claim

DXF export for a neutral `PolygonalDrawing` emits one closed `LWPOLYLINE` with
the polygon vertices.

### Domain

All valid neutral `PolygonalDrawing` instances exported through
`DXFDocument.add_group()`.

### Proof Method

`DXFDocument.add_group()` iterates over neutral components.
`_component_to_entities()` matches `PolygonalDrawing` and returns
`_lwpolyline_entity(component.points, context, closed=True)`.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-POLYGON-008: Neutral PolygonalDrawing Geometry Boundary

### Claim

`PolygonalDrawing` normalizes valid point payloads at construction and rejects
malformed polygon payloads before SVG/PDF/DXF materialization.

### Domain

Direct `PolygonalDrawing` construction with the same valid and invalid polygon
partitions as `PolygonalDrawingComponent`: at least three finite numeric
non-boolean coordinate pairs, positive-area valid Shapely polygon, and
malformed partitions including too-few points, wrong arity, nonnumeric values,
non-finite values, boolean coordinates, collinear points, self-intersections,
and non-sequence point containers.

### Proof Method

`PolygonalDrawing.__post_init__()` checks the style boundary, constructs a
temporary `PolygonalDrawingComponent` with the provided points, and stores that
component's normalized public `points` list. Focused tests cover valid
normalization, SVG/PDF materialization, and the declared malformed partitions.
Mutation testing targets the constructor wiring and the existing component
validation rows it delegates to.

### Conclusion

Proven for the stated public construction domain after focused tests and
mutation pass, with only the equivalent Shapely area survivor.

## PO-POLYGON-009: FlowDocument PolygonalDrawing Hydration Boundary

### Claim

Serialized `PolygonalDrawing` payloads hydrated through
`FlowDocument.create_from_dict()` cannot expose malformed neutral polygon
geometry.

### Domain

Flow-document drawing blocks containing serialized `PolygonalDrawing` payloads
and style overrides for the malformed polygon partitions named in
PO-POLYGON-008.

### Proof Method

`document_outputs._drawing_component_from_parameters()` dispatches exact
component type names to `DRAWING_COMPONENT_CONSTRUCTORS[component_type]` with
`style=style, **payload`. Therefore serialized neutral polygon payloads must
pass `PolygonalDrawing.__post_init__()` before the hydrated group is returned.
Focused tests mutate serialized payload fields and assert hydration raises.

### Conclusion

Proven for the stated flow-document hydration domain after focused tests and
mutation pass, with only the equivalent Shapely area survivor.

## PO-POLYGON-010: PolygonalDrawing Revalidates Live Points

### Claim

`PolygonalDrawing.to_component()` rejects malformed values in the current
public `points` list before constructing `PolygonalSVG` or `PolygonalPDF`.

### Domain

All public `PolygonalDrawing` instances at materialization time, including
instances whose accepted post-construction `points` list was mutated to contain
non-point objects, too few points, wrong arity, non-finite values, boolean
coordinates, collinear points, or self-intersecting geometry.

### Proof Method

`PolygonalDrawing.to_component()` calls `_normalize_polygonal_drawing_points()`
on the current `self.points` value before renderer dispatch. The helper
constructs a `PolygonalDrawingComponent`, which is the shared polygon
validation source of truth, and returns that component's normalized public
point list. Therefore the same point-count, point-shape, finite-coordinate,
boolean-coordinate, Shapely-validity, and positive-area checks used by
construction run again before concrete renderer construction. Focused tests
mutate the public point list and prove both direct
`to_component(OutputFormat.SVG)` and dependent `DrawingComponentGroup.to_group()`
calls raise `InvalidPolygonError`. Mutation testing over the shared polygon
validator killed all non-equivalent proof-critical mutants; Cosmic Ray did not
emit a function-call-removal mutant for the revalidation assignment, so the live
call wiring is established by static path proof plus behavioral live-path
tests.

### Counterexamples And Exclusions

Private mutation of inherited polygon internals, hostile monkey-patching of
renderer classes, holes, multipolygons, and automatic polygon repair remain
outside this public neutral point-list contract. The public `points` list
remains mutable for compatibility; the guarantee is fail-fast materialization,
not immutable state.

### Conclusion

Proven for the stated domain after focused tests, static path proof, and the
shared validator mutation gate, with only the equivalent Shapely area survivor.

## Current Slice Decision

The slice chooses fail-fast validation over implicit Shapely repair. That keeps
synthetic drawings deterministic and makes invalid geometry visible before it
reaches renderers or downstream parser fixtures.
