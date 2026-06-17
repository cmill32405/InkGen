# Regular Polygon Renderer Contract Proof Obligations

This note applies the InkGen Definition of Done to the REGPOLY-P1 regular
polygon renderer-contract slice. It focuses on vertex geometry, validation
boundaries, and the dependency path from renderer-neutral drawing recipes into
PDF and DXF output.

## Scope

The slice covers regular polygon geometry and validation owned by
`src/InkGen/component.py`, closed-path PDF rendering in
`src/InkGen/pdf_generator.py`, renderer-neutral materialization in
`src/InkGen/drawing_components.py`, and DXF polygon export in
`src/InkGen/dxf_generator.py`.

The public behavior under review is:

- `RegularPolygonDrawingComponent.sides`
- `RegularPolygonDrawingComponent.radius`
- `RegularPolygonDrawingComponent.corner_radius`
- `RegularPolygonDrawingComponent._get_points()`
- `RegularPolygonPDF.generate_pdf()`
- `RegularPolygonDrawing.to_component(OutputFormat.PDF)`
- `DXFDocument.add_group()` for `RegularPolygonDrawing`

## Architecture Impact

Affected surface:

- `src/InkGen/component.py`: source of regular polygon geometry and validation.
- `src/InkGen/pdf_generator.py`: PDF rendering as a closed path from component
  vertices.
- `src/InkGen/drawing_components.py`: neutral regular polygon recipe
  materialization to concrete renderers.
- `src/InkGen/dxf_generator.py`: DXF closed polyline output that intentionally
  reuses PDF-materialized regular polygon points.
- `tests/test_regular_polygon_contract.py`: math, validation, renderer, and
  dependency-path evidence.

Incoming dependencies:

- SVG/PDF/DXF renderers, labels, masks, truth emitters, generated fixtures, and
  synthetic drawing consumers rely on stable regular polygon `points`, `bbox`,
  and `convex_hull` semantics.
- PDF fixture consumers rely on `RegularPolygonPDF.generate_pdf()` emitting a
  closed path whose vertices match `RegularPolygonDrawingComponent.points`.
- DXF export relies on `RegularPolygonDrawing.to_component(OutputFormat.PDF)`
  returning a concrete component whose `points` represent the neutral regular
  polygon.

Outgoing dependencies:

- `RegularPolygonDrawingComponent` depends on the polar component base class,
  numeric position/sides/radius/angle/corner-radius inputs, `DrawingStyle`,
  `numpy` trigonometry through `_rect()`, `shapely` geometry for bbox/hull, and
  `PRECISION`.
- `RegularPolygonPDF` depends on the shared regular polygon point contract and
  local `_path_from_points()` / `_drawing_pdf()` helpers.
- `DXFDocument` depends on renderer-neutral drawing recipes and intentionally
  materializes regular polygons through the PDF path for vertex geometry.

Before/after edge changes:

- No new production dependency edge was added in this slice.
- The existing edge
  `dxf_generator.py -> component.to_component(OutputFormat.PDF)` for regular
  polygon geometry is now explicitly tested.
- The existing neutral recipe edge `RegularPolygonDrawing -> RegularPolygonPDF`
  is now explicitly tested for PDF output.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced. Components do not import PDF or DXF.
- Layer check: concrete renderers depend on component geometry and neutral
  recipes according to `docs/dependency-map.md`.
- Coupling check: DXF's reuse of PDF-materialized points is explicit and tested.
- Redundancy check: the slice avoids introducing a second regular polygon
  vertex implementation for PDF or DXF.

Evidence source and freshness:

- Source-backed: `component.py`, `pdf_generator.py`, `drawing_components.py`,
  and `dxf_generator.py` were read before adding tests.
- Test-backed: focused tests in `test_regular_polygon_contract.py` exercise the
  math, validation, and live dependency paths.
- Design-backed: `docs/dependency-map.md` already records the DXF-to-PDF
  sampled/point geometry edge as intentional.
- No architecture claim in this section relies only on stale memory.

ADR/rule impact:

- No new ADR is required because no new architecture decision was made.
- A future change that replaces DXF closed-polyline regular polygon output with
  another entity should add or update an ADR because it changes the
  generated-artifact contract and dependency direction.

## Domain Definitions

- A regular polygon is defined by non-negative-position coordinates accepted by
  the base component, integer `sides >= 3`, positive `radius`, `angle` in
  degrees, and `0 <= corner_radius <= radius / 2`.
- `RegularPolygonDrawingComponent.points` returns one vertex per side using the
  public `radius` and rounded public `angle` values.
- The vertex angle for point index `p` is:

```text
(angle + 90 + p * 360 / sides) % 360
```

The emitted point is the polar-to-Cartesian conversion of that radius/angle,
translated by `position`.

## Fix Log

- Fixed construction-time radius validation so `radius=0` is rejected. The
  setter already rejected zero, but the constructor only rejected negative
  values.
- Fixed `sides` validation so non-integer values fail at the public setter
  instead of later when `_get_points()` calls `range()`.
- Fixed `corner_radius` validation so negative values are rejected, exactly half
  the radius is accepted, and radius changes cannot leave an existing corner
  radius greater than half of the new radius.
- Corrected the typo in the corner-radius error message from `exced` to
  `exceed`.
- Mutation testing forced additional boundary coverage for small positive
  radius values, setter `radius=0`, fractional half-radius corner values, and a
  7-sided polygon where `/` versus `//` changes vertex angles.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid integer sides and positive radius | Emit one vertex per side from the polar radius/angle formula | PO-REGPOLY-001 | `test_regular_polygon_vertices_follow_radius_angle_formula` | Must be killed or proven equivalent |
| Invalid side count or side type | Reject with a boundary error before rendering | PO-REGPOLY-002 | `test_regular_polygon_rejects_invalid_boundaries` | Must be killed or proven equivalent |
| Invalid radius or corner radius | Reject non-positive radius, negative corner radius, and corner radius greater than half radius | PO-REGPOLY-002 | `test_regular_polygon_rejects_invalid_boundaries` | Must be killed or proven equivalent |
| PDF regular polygon rendering | Emit a closed PDF path from component vertices | PO-REGPOLY-003 | `test_regular_polygon_pdf_emits_closed_path_from_component_points` | Must be killed or proven equivalent |
| Renderer-neutral regular polygon exported to DXF | Materialize to PDF and emit DXF closed polyline vertices from the same points | PO-REGPOLY-004 | `test_regular_polygon_drawing_materializes_pdf_component`; `test_dxf_regular_polygon_reuses_pdf_points_as_closed_polyline` | Must be killed or proven equivalent |
| Negative base coordinates, non-finite values, hostile mutation of private fields, monkey-patched renderers, rounded-corner geometry, and native DXF polygon entities | Excluded from proven domain | Explicit exclusions in PO-REGPOLY-001 through PO-REGPOLY-004 | none | Out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Vertex generation and validation are deterministic math/validation units. | `test_regular_polygon_vertices_follow_radius_angle_formula`; `test_regular_polygon_rejects_invalid_boundaries` |
| Behavioral/condition | yes | REGPOLY-P1 defines expected regular polygon behavior across component, PDF, neutral recipe, and DXF paths. | New tests are marked `@pytest.mark.condition("REGPOLY-P1")`. |
| Failure-mode | yes | Invalid side/radius/corner-radius inputs must fail at public boundaries. | `test_regular_polygon_rejects_invalid_boundaries` |
| Integration/live-path | yes | DXF must exercise the public neutral group path, not just a helper. | `test_dxf_regular_polygon_reuses_pdf_points_as_closed_polyline` calls `DXFDocument.add_group()`. |
| Contract/API compatibility | yes | Existing point and parameter contracts must remain stable. | Existing regular polygon tests plus REGPOLY-P1 point/materialization tests. |
| Property/fuzz | yes | Vertex generation has a deterministic formula over side indices. | Deterministic bounded property-style tests plus algebraic proof below. |
| Mutation | yes | Vertex generation, validation, renderer dispatch, and PDF/DXF path generation are proof-critical. | Mutation run result recorded below. |
| Security/adversarial | no | The slice adds no file path, network, subprocess, auth, secrets, SQL, template, deserialization, font, image, or active-content surface. | Not applicable. |
| Performance/resource | no | The slice adds no unbounded loop beyond caller-provided `sides`, which is constrained to an integer of at least 3 but not otherwise capped by this legacy class. | Not applicable for this proof. |
| Concurrency/race | no | The slice adds no shared mutable global state, background workers, sessions, locks, queues, or temp-file coordination. | Not applicable. |
| Observability/logging | no | The slice adds no state-changing service, background work, external call, or recovery path. | Not applicable. |
| Golden artifact/visual | yes | PDF and DXF generated geometry must be stable enough for synthetic fixtures. | PDF path test and DXF vertex test. |
| Regression | yes | This slice closes validation defects discovered during pre-change dependency/contract review. | REGPOLY-P1 tests named above. |

## Invariants, Preconditions, And Postconditions

Invariants:

- `sides` is an integer and is at least 3.
- `radius` is strictly positive.
- `corner_radius` is non-negative and not greater than half the current radius.
- `points` contains exactly `sides` vertices.
- Each vertex is translated from the component position by the current radius
  and public angle formula.
- PDF and DXF regular polygon output use the same component vertex contract.

Preconditions:

- Position is accepted by the base drawing component coordinate domain.
- Radius, angle, and corner radius are finite numeric values.
- Callers do not monkey-patch polygon classes or mutate private fields.

Postconditions:

- `RegularPolygonDrawingComponent.points` returns one point per side.
- `RegularPolygonPDF.generate_pdf()` emits a closed path from those points.
- `DXFDocument.add_group()` emits a closed `LWPOLYLINE` whose vertices match the
  PDF-materialized regular polygon points.

## Mutation Testing Gate

Proof-critical mutation targets:

- Changing any side-count, radius, corner-radius, angle-step, translation, or
  point-count term should fail formula and boundary tests.
- Weakening side/radius/corner-radius validation should fail invalid-boundary
  tests.
- Opening the PDF path or changing the PDF vertex source should fail PDF path
  tests.
- Redirecting DXF regular polygon export away from
  `component.to_component(OutputFormat.PDF).points` without preserving vertices
  should fail the DXF dependency-path test.

Current result:

- Tool and version: Cosmic Ray 8.4.6 in WSL.
- Mutated source paths: `src/InkGen/component.py`,
  `src/InkGen/drawing_components.py`, `src/InkGen/pdf_generator.py`, and
  `src/InkGen/dxf_generator.py`.
- Reproducible setup:
  `cosmic-ray baseline tests/mutation/regular_polygon_cosmic_ray.toml`,
  `cosmic-ray init tests/mutation/regular_polygon_cosmic_ray.toml
  /tmp/inkgen_regular_polygon_mutation.sqlite`, then
  `python tests/mutation/filter_regular_polygon_work_items.py
  /tmp/inkgen_regular_polygon_mutation.sqlite --clear-results`.
- Test selection:
  `python -m pytest -x tests/test_regular_polygon_contract.py
  tests/test_component.py tests/test_drawing_components.py
  tests/test_pdf_generator.py tests/test_dxf_generator.py`.
- Proof-critical work items after filtering: 184.
- Mutants killed: 180.
- Mutants survived: 4.
- Mutants excluded/equivalent: 4 equivalent mutants:

  - `src/InkGen/component.py:1038`: replacing modulo by `+ 360` or `- 360`.
    Within the declared domain, `_rect()` converts degrees with sine and cosine.
    For any finite angle `a`:

    ```text
    cos(radians(a % 360)) == cos(radians(a + 360)) == cos(radians(a - 360))
    sin(radians(a % 360)) == sin(radians(a + 360)) == sin(radians(a - 360))
    ```

    Therefore the emitted points are equivalent.

  - `src/InkGen/drawing_components.py:205`: `target == OutputFormat.SVG` and
    `target >= OutputFormat.SVG`. Within the declared public domain,
    `normalize_output_format()` returns one of exactly two string-enum values:
    `OutputFormat.SVG == "svg"` or `OutputFormat.PDF == "pdf"`. Therefore:

    ```text
    OutputFormat.SVG is OutputFormat.SVG => true
    OutputFormat.SVG == OutputFormat.SVG => true
    OutputFormat.SVG >= OutputFormat.SVG => true
    OutputFormat.PDF is OutputFormat.SVG => false
    OutputFormat.PDF == OutputFormat.SVG => false
    OutputFormat.PDF >= OutputFormat.SVG => false, because "pdf" < "svg"
    ```

    If a future output format is added, this equivalence must be revisited.

During mutation, real test gaps were found and closed:

- `radius <= 0` construction and setter checks needed small positive, zero, and
  negative boundary coverage.
- Corner-radius half-radius checks needed exact and fractional boundary
  coverage.
- Vertex formula coverage needed a side count where `360 / sides` is not an
  integer, so floor-division mutation is observable.

Gate result: passed for the declared domain. The mutation report has no
surviving non-equivalent proof-critical mutants.

## PO-REGPOLY-001: Regular Polygon Vertex Formula

### Claim

`RegularPolygonDrawingComponent.points` emits one vertex per side using InkGen's
public radius and angle formula.

### Domain

All regular polygon components with accepted position coordinates, integer
`sides >= 3`, positive radius, valid corner radius, finite numeric angle, and no
private-field mutation.

### Assumptions

- `PolarCoordinateDrawingComponent._rect()` implements standard
  polar-to-Cartesian conversion.
- The public `angle` property rounds to InkGen `PRECISION`; `_get_points()` uses
  that public angle.

### Theorem

For every point index `p` where `0 <= p < sides`, the emitted point is:

```text
x = position.x + radius * cos(radians((angle + 90 + p * 360 / sides) % 360))
y = position.y + radius * sin(radians((angle + 90 + p * 360 / sides) % 360))
```

where `angle` and `radius` are the component's public properties.

### Proof Method

Static/algebraic reasoning over `_get_points()`:

1. The method iterates `p` from `0` through `sides - 1`.
2. It computes `(self.angle + 90 + p * 360 / self.sides) % 360`.
3. It calls `_rect(self.length, computed_angle)`.
4. `_rect()` computes `length*cos(angle)` and `length*sin(angle)`.
5. The method translates each computed point by `self.position`.
6. Therefore every emitted point matches the theorem.

### Counterexamples And Exclusions

- Negative base coordinates are outside the existing base component domain.
- Rounded-corner rendering is not implemented by current SVG/PDF/DXF regular
  polygon renderers, so this proof covers the validation invariant only.
- Direct mutation of private fields is outside the public construction/setter
  contract.

### Conclusion

Proven for the stated domain.

## PO-REGPOLY-002: Validation Boundaries

### Claim

Regular polygon public construction and setters preserve valid side, radius, and
corner-radius boundaries.

### Domain

All public construction and setter calls for `sides`, `radius`, and
`corner_radius`.

### Proof Method

Construction assigns `sides` through the public setter, rejects non-positive
radius before initializing the polar base, and assigns `corner_radius` through
the public setter. The `sides` setter rejects booleans and non-integers, then
requires `sides >= 3`. The `radius` setter rejects non-positive values and
rejects radius changes that would make the existing corner radius exceed half
the new radius. The `corner_radius` setter rejects negative values and values
greater than half the current radius. Therefore public construction and setters
preserve the validation invariants.

### Conclusion

Proven for the stated domain.

## PO-REGPOLY-003: PDF Regular Polygon Uses Closed Component Path

### Claim

`RegularPolygonPDF.generate_pdf()` emits a closed PDF path from regular polygon
component vertices.

### Domain

All `RegularPolygonPDF` instances in the stated regular polygon domain.

### Proof Method

`RegularPolygonPDF.generate_pdf()` calls `_path_from_points(self._get_points(),
close=True)` and passes the result to `_drawing_pdf()`. `_path_from_points()`
emits one move-to operator for the first point, one line operator for each
remaining point, and a close-path operator when `close=True`. Therefore PDF
output is closed and derived from component vertices.

### Conclusion

Proven for the stated domain.

## PO-REGPOLY-004: DXF Reuses PDF-Materialized Regular Polygon Geometry

### Claim

DXF export for a neutral `RegularPolygonDrawing` emits vertices from the same
points as the neutral polygon's PDF materialization.

### Domain

All `RegularPolygonDrawing` instances exported through `DXFDocument.add_group()`.

### Proof Method

Static path proof over `drawing_components.py` and `dxf_generator.py`:

1. `RegularPolygonDrawing.to_component(OutputFormat.PDF)` returns a
   `RegularPolygonPDF`.
2. `DXFDocument.add_group()` iterates over `group.components`.
3. `_component_to_entities()` matches `RegularPolygonDrawing`.
4. That branch assigns `concrete = component.to_component(OutputFormat.PDF)`.
5. It returns `_lwpolyline_entity(concrete.points, context, closed=True)`.
6. `_lwpolyline_entity()` emits one vertex for each supplied point and sets the
   closed-polyline flag.
7. Therefore the generated vertices are the PDF-materialized points, transformed
   only by `DXFRenderContext.point()`.

### Counterexamples And Exclusions

- Native DXF polygon entities are not part of the current contract.
- If DXF changes to a different representation, this proof must be replaced and
  an ADR should record the new dependency direction.

### Conclusion

Proven for the stated domain.

## Current Slice Decision

The slice has mathematical proof for regular polygon vertex generation, runtime
validation for side/radius/corner-radius boundaries, and closed-path rendering,
plus live-path evidence for neutral recipe and DXF dependency propagation.

The main design constraint is that DXF regular polygon export intentionally
depends on PDF-materialized component points, not a separate DXF vertex
implementation. That edge is now explicit and tested.
