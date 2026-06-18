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
- `PolygonalDrawing.to_component(OutputFormat.SVG/PDF)`
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

Incoming dependencies:

- Label, mask, collision, and text-fitting paths rely on polygon `points`,
  `bbox`, `convex_hull`, and `polygon` being valid Shapely geometry.
- SVG/PDF fixture generation relies on deterministic vertex order.
- DXF export relies on neutral polygon recipes becoming closed `LWPOLYLINE`
  entities.

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
- No new dependency edge or third-party dependency was introduced.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced. Neutral drawing classes still lazy-import
  concrete renderers only inside `to_component()`.
- Layer check: polygon validity remains in the shared component layer, while
  renderers only serialize valid geometry.
- Coupling check: SVG/PDF/DXF share the component geometry contract without
  sharing renderer-specific syntax.
- Redundancy check: no duplicate polygon validation was added to renderers.

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
- SVG and PDF outputs are closed paths.
- DXF output is a closed `LWPOLYLINE`.

## Fix Log

- `PolygonalDrawingComponent` now validates numeric finite coordinate pairs.
- Boolean coordinate values are rejected instead of being coerced to `0.0` or
  `1.0`.
- Degenerate, empty, self-intersecting, and zero-area polygons are rejected.
- The points setter uses the same validation path as construction.

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
| Polygon repair, holes, multipolygons, winding normalization, and fill-rule semantics | Excluded from proven domain | Explicit exclusion | Not applicable | Out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Validation and geometry access are deterministic. | POLYGON-P1 tests named above |
| Behavioral/condition | yes | POLYGON-P1 defines polygon behavior across validation and renderers. | Tests are marked `@pytest.mark.condition("POLYGON-P1")`. |
| Failure-mode | yes | Invalid polygons must fail before rendering. | `test_polygonal_component_rejects_invalid_inputs` |
| Integration/live-path | yes | DXF proof must exercise `DXFDocument.add_group()`. | `test_dxf_polygonal_drawing_exports_closed_polyline` |
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

`PolygonalDrawing.to_component()` normalizes the requested format. SVG returns
`PolygonalSVG(self.points, self.style)`. PDF returns
`PolygonalPDF(self.points, self.style)`.

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

## Current Slice Decision

The slice chooses fail-fast validation over implicit Shapely repair. That keeps
synthetic drawings deterministic and makes invalid geometry visible before it
reaches renderers or downstream parser fixtures.
