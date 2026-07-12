# Boundary Canvas Contract Proof Obligations

This note applies the InkGen Definition of Done to the BOUNDARY-CANVAS-P1
boundary and canvas slice. It focuses on finite convex hull coordinates,
positive finite canvas dimensions, explicit unit validation, serialized
round-trips, and live use through layer off-canvas checks.

## Scope

The slice covers:

- `Boundary.__init__()`
- `Boundary.create_from_dict()`
- `Boundary.parameters`
- `Boundary.boundary_points`
- `Boundary.boundary_check()`
- `Canvas.__init__()`
- `Canvas.create_from_dict()`
- `Canvas.width`
- `Canvas.height`
- `Canvas.parameters`
- Boundary-local validation helpers in `src/InkGen/boundary.py`

## Architecture Impact

Affected surface:

- `src/InkGen/boundary.py`: finite coordinate validation, convex hull
  validation, canvas dimension validation, and unit validation.
- `tests/test_boundary_canvas_contract.py`: BOUNDARY-CANVAS-P1 behavioral,
  failure-mode, serialization, and live-path tests.
- `tests/mutation/boundary_canvas_cosmic_ray.toml`: scoped boundary model
  mutation gate.
- `tests/mutation/layer_canvas_live_path_cosmic_ray.toml`: scoped layer
  live-path mutation gate.
- `tests/mutation/filter_boundary_canvas_work_items.py`: proof-critical
  mutation filter.

Incoming dependencies:

- `Layer.add_component_group()` uses `Canvas.boundary_check()` to reject
  off-canvas groups.
- `Layer._create_boundary()` uses `Boundary` for component-group collision
  checks.
- `Document`, `DocumentPDF`, and `DocumentSVG` rely on `Canvas` for page and
  layer dimensions.
- `text_fitter.py` uses `Boundary.boundary_check()` as one containment signal
  when jittering text inside regions.
- Saved layer and document payloads hydrate canvases through
  `Canvas.create_from_dict()`.
- Existing docs and examples construct A4-style canvases with millimeter or
  inch aliases.

Outgoing dependencies:

- Boundary geometry depends on Shapely `MultiPoint`, `Polygon`,
  `get_coordinates`, and `GEOSException`.
- Validation depends only on Python `math.isfinite()`.
- No new third-party dependency or dependency edge was introduced.

Before/after edge changes:

- Before this slice, canvases could accept booleans, zero or negative
  dimensions, `nan`, and some malformed unit values before failing later or
  silently storing invalid geometry.
- Before this slice, malformed boundary-check candidate hulls could leak
  Shapely errors.
- After this slice, boundary hulls and candidate hulls must be finite numeric
  coordinate pairs with at least three distinct points and nonzero convex hull
  area.
- After this slice, canvas dimensions must be finite numeric values greater
  than zero, excluding booleans.
- Legacy unordered convex hull inputs remain supported, and `boundary_points`
  preserves the submitted non-closing point order.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced.
- Layer check: boundary validation remains in the boundary model; document,
  layer, and text-fitting code consume the contract.
- Coupling check: no renderer-specific logic was added to boundary code.
- Redundancy check: shared local helpers avoid duplicate finite numeric and hull
  validation.

ADR/rule impact:

- No new ADR is required. This reinforces the dependency-map rule that authoring
  and geometry models own their public input contracts.

## Domain Definitions

- A boundary hull is an iterable of finite numeric `(x, y)` coordinate pairs.
- Boundary hull input may be unordered, but every point must lie on the convex
  hull. Interior points are invalid.
- A closed hull may repeat the first point at the end; serialization removes
  the closing duplicate.
- `Boundary.boundary_check([])` returns `False`.
- Non-empty boundary-check inputs must be finite candidate hull coordinate
  pairs.
- `strict` and `outer_boundary` are booleans, not truthy flags.
- A canvas width and height are finite numeric values greater than zero.
- Canvas unit aliases normalize to `"mm"` or `"in"`.

## Fix Log

- Added shared finite numeric validation excluding booleans and non-finite
  values.
- Added positive finite validation for canvas width and height.
- Added explicit unit type validation before alias normalization.
- Added hull normalization for boundary and candidate hull inputs.
- Built boundary geometry from `MultiPoint(...).convex_hull` so legacy
  unordered convex hull input stays valid.
- Preserved submitted boundary point order for serialization while removing a
  trailing closing duplicate.
- Added explicit malformed-candidate handling to `Boundary.boundary_check()`.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid canvases | Preserve positive finite dimensions and unit aliases | PO-BCAN-001 | `test_canvas_rejects_bool_nonpositive_and_nonfinite_dimensions`, `test_canvas_units_fail_at_public_boundary` | killed |
| Invalid canvas dimensions | Reject booleans, zero, negative, `nan`, and `inf` | PO-BCAN-002 | `test_canvas_rejects_bool_nonpositive_and_nonfinite_dimensions` | killed |
| Invalid units | Reject non-string units and unsupported string units | PO-BCAN-003 | `test_canvas_units_fail_at_public_boundary` | killed |
| Boundary hulls | Accept finite convex unordered or closed hulls and reject malformed/degenerate/nonfinite hulls | PO-BCAN-004 | `test_boundary_rejects_malformed_degenerate_and_nonfinite_hulls` | 2 equivalent survivors documented |
| Candidate hull checks | Return containment result for valid hulls and reject malformed candidate hulls | PO-BCAN-005 | `test_boundary_check_validates_candidate_hulls_and_strict_flag` | killed |
| Layer live path | Hardened canvas boundary remains wired into off-canvas rejection | PO-BCAN-006 | `test_boundary_canvas_contract_is_live_in_layer_off_canvas_check` | killed |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Numeric and hull validation is deterministic. | BOUNDARY-CANVAS-P1 tests |
| Behavioral/condition | yes | The slice defines public boundary and canvas behavior. | Tests are marked `@pytest.mark.condition("BOUNDARY-CANVAS-P1")`. |
| Failure-mode | yes | Invalid hulls, dimensions, units, and strict flags must fail at the public boundary. | Invalid-boundary tests |
| Integration/live-path | yes | `Layer.add_component_group()` consumes the canvas boundary contract. | Live off-canvas test |
| Contract/API compatibility | yes | Existing boundary, document, and text-boundary tests must continue passing. | Focused gate includes existing tests |
| Property/fuzz | no | The proof partitions finite scalar and finite point-list cases directly. | Not applicable |
| Mutation | yes | Validation guards and hull branches are proof-critical. | Mutation result recorded below |
| Security/adversarial | no | No file path, network, subprocess, auth, SQL, template, or active-content surface is added. | Not applicable |
| Performance/resource | no | The change adds finite point-list validation and convex-hull construction already required by the existing model. | Code inspection |
| Concurrency/race | no | No shared state, background workers, locks, or temp files are added. | Not applicable |
| Golden artifact/visual | no | This slice changes geometry validation, not renderer output. | Existing renderer tests cover downstream compatibility |
| Regression | yes | This closes invalid canvases and malformed hulls leaking into geometry paths. | BOUNDARY-CANVAS-P1 tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Removing finite checks must fail invalid hull or canvas tests.
- Allowing zero, negative, boolean, or non-finite canvas dimensions must fail
  dimension tests.
- Loosening unit validation must fail unit tests.
- Weakening hull shape, distinct-point, closure, or candidate-hull validation
  must fail boundary tests unless a downstream check enforces the same result.
- Breaking the live canvas boundary check must fail the layer off-canvas test.

Current result:

- Cosmic Ray 8.4.6, scoped to executable BOUNDARY-CANVAS-P1 validation rows:
  74 work items, 72 killed, and 2 documented equivalent survivors.
- Cosmic Ray 8.4.6, scoped to `Layer.add_component_group()` canvas-boundary
  live-path rows: 3 work items, 3 killed, and 0 survived.
- Equivalent survivors:
  - `_normalize_hull`: `len(raw_points) < 3` changed to
    `len(raw_points) < 2`.
  - `_normalize_hull`: `len(set(points)) < 3` changed to
    `len(set(points)) < 2`.
- Equivalence proof: two-point hulls that pass either weakened early guard are
  still rejected before construction completes. With two raw points, the
  distinct-point guard rejects when fewer than three distinct points remain; if
  that second guard is independently weakened, `MultiPoint(...).convex_hull`
  yields a line with zero area, and `Boundary.__init__()` rejects it via
  `self._boundary_polygon.area <= 0`. Therefore no accepted public hull changes
  under either single survivor.

## PO-BCAN-001: Valid Canvases Preserve Geometry

### Claim

Valid canvases preserve positive finite dimensions and normalized unit aliases.

### Domain

Public `Canvas(...)` construction and `Canvas.create_from_dict()` hydration
with positive finite width and height values and supported unit aliases.

### Proof Method

`Canvas.__init__()` coerces width and height through the positive finite helper
and normalizes supported string aliases to `"mm"` or `"in"`. Focused tests cover
integer, float, small positive, millimeter alias, and inch alias cases.

### Conclusion

Proven for the stated domain after tests and mutation pass with documented
equivalent survivors unrelated to valid canvas dimensions.

## PO-BCAN-002: Invalid Canvas Dimensions Fail Early

### Claim

Canvas dimensions reject booleans, zero, negative values, and non-finite
numbers before Shapely geometry is constructed.

### Domain

Public canvas width and height inputs.

### Proof Method

`_coerce_positive_number()` rejects malformed values before `Canvas` calls
`Boundary.__init__()`. Focused tests cover boolean, zero, negative, `nan`, and
`inf` partitions.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-BCAN-003: Canvas Units Are Explicit

### Claim

Canvas unit aliases must be strings and must normalize to `"mm"` or `"in"`.

### Domain

Public `units` values supplied to `Canvas(...)` and hydrated through
`Canvas.create_from_dict()`.

### Proof Method

`Canvas.__init__()` checks `isinstance(units, str)` before `.lower()` and then
matches the supported alias sets. Focused tests cover non-string and invalid
string failure modes.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-BCAN-004: Boundary Hulls Are Finite Convex Hulls

### Claim

Boundary hulls must contain finite numeric coordinate pairs that define a
nonzero-area convex hull, and all submitted points must lie on that hull.

### Domain

Public `Boundary(...)` construction and `Boundary.create_from_dict()` hydration.

### Proof Method

`_normalize_hull()` validates iterable coordinate pairs, finite values, and at
least three distinct points. `Boundary.__init__()` constructs a Shapely convex
hull from the submitted points, rejects zero-area hulls, and `_hull_check()`
rejects interior points.

### Conclusion

Proven for the stated domain after tests and mutation pass with two documented
equivalent cardinality survivors.

## PO-BCAN-005: Candidate Boundary Checks Are Explicit

### Claim

`Boundary.boundary_check()` returns `False` for empty candidate input, rejects
malformed non-empty candidate hulls, and preserves containment behavior for
valid candidates.

### Domain

Public `Boundary.boundary_check(points, strict)` calls with finite candidate
hulls and malformed point inputs.

### Proof Method

`boundary_check()` validates the `strict` flag, converts candidate inputs at the
public boundary, returns `False` for empty input, and routes non-empty
candidate hulls through `_normalize_hull()` before Shapely containment checks.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-BCAN-006: Layer Off-Canvas Checks Consume The Contract

### Claim

The hardened canvas boundary remains wired into the layer live path.

### Domain

`Layer.add_component_group()` calls using component groups with points inside
or outside the canvas.

### Proof Method

The live-path test adds an inside group successfully, then verifies an
off-canvas group raises `ComponentGroupOffCanvas` through
`Canvas.boundary_check()`.

### Conclusion

Proven for the stated domain after focused live-path tests and scoped mutation:
3 layer live-path work items, 3 killed, and 0 survived.
