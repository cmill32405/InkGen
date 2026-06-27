# Text Fitter Contract Proof Obligations

This note applies the InkGen Definition of Done to the TEXT-FITTER-P1 text
fitting slice. It focuses on fitting text inside arbitrary polygons, fail-closed
behavior, deterministic wrapping, jitter containment, component adapters, and
the binary search that selects the largest valid font size.

## Scope

The slice covers:

- `FittingResult.text_bounding_box`
- `FitterShape.__post_init__()`
- `TextFitter._calculate_inner_boundary()`
- `TextFitter._adaptive_word_wrap()`
- `TextFitter._check_fit()`
- `TextFitter.fit()`
- `component_to_fitter_shape()`

Glyph shaping internals in `text_outline.py`, visual debug image generation,
and the private stochastic jitter sampler are out of scope except where they
affect the public `fit()` result.

## Architecture Impact

Affected surface:

- `src/InkGen/text_fitter.py`: binary-search fit behavior.
- `tests/test_text_fitter_contract.py`: TEXT-FITTER-P1 condition tests.
- `tests/mutation/text_fitter_cosmic_ray.toml`: scoped mutation gate.
- `tests/mutation/filter_text_fitter_work_items.py`: proof-critical mutation
  filter.

Incoming dependencies:

- Public callers import `TextFitter`, `TextBlock`, `FitterShape`,
  `FittingResult`, and `component_to_fitter_shape` from `InkGen`.
- Text and layout documentation describes text fitting as an authoring tool for
  synthetic drawings.
- Component adapters depend on component `convex_hull` or `radius` contracts.

Outgoing dependencies:

- `TextFitter` depends on Shapely for geometric containment and translation.
- `TextFitter` depends on Pillow font metrics for line widths and ascent.
- `TextFitter` depends on `outline_for_text()` for glyph outlines and falls
  back to conservative line boxes when outlines are unavailable.
- Jitter containment cross-checks through `Boundary.boundary_check()`.
- No dependency was added.

Before/after edge changes:

- Before this slice, `TextFitter` behavior was covered by unmarked tests, but
  there was no condition-marked proof, proof note, or mutation gate for the
  fitting contract.
- After this slice, condition tests pin fail-closed no-fit cases, exact-width
  wrapping, asymmetric polygon bounds, binary-search font selection, minimum
  font thresholds, outline fallback, jitter acceptance/rejection, and final
  outline replacement.
- Before TEXT-FITTER-JITTER-MARGIN-P2, `fit(..., jitter_margin=...)` accepted
  booleans, strings, and non-finite values through `float()` coercion before
  jitter containment math.
- After TEXT-FITTER-JITTER-MARGIN-P2, jitter margins must be finite non-boolean
  numeric values; negative finite margins remain clamped to zero.
- Before TEXT-FITTER-SHAPE-P2, public `FitterShape` instances accepted
  malformed polygons, line-thickness ranges, and padding values until Shapely
  or fitting math failed downstream.
- After TEXT-FITTER-SHAPE-P2, public `FitterShape` instances reject non-polygon,
  empty, or invalid polygons; unordered, malformed, negative, or
  non-finite line-thickness ranges; and negative, non-finite, boolean, string,
  bytes, or arbitrary-object padding values at construction.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced.
- Layer check: fitting remains in the text layout utility layer.
- Coupling check: no renderer-specific dependency was added.
- Redundancy check: the slice adds tests/proof and one local binary-search fix;
  it does not duplicate layout logic elsewhere.

ADR/rule impact:

- No new ADR is required. This reinforces the dependency-map rule that geometry
  utilities must prove containment before downstream renderers consume their
  results.

## Domain Definitions

- A successful fit returns a non-empty `FittingResult`.
- Successful text geometry and convex hull must be covered by the target
  polygon.
- Failed fits return `None`; partial unsafe geometry is not returned.
- Word wrapping uses horizontal polygon bounds and optional `max_line_width`.
- Exact-width lines are valid; only lines wider than available width fail.
- `fit()` returns the largest valid font size greater than or equal to the
  configured minimum threshold.
- Jitter may change positions only when the candidate geometry remains
  contained.
- Jitter safety margins are finite numeric values. Negative finite margins are
  accepted and clamped to zero; booleans, strings, bytes, arbitrary objects,
  `nan`, and infinity are invalid.
- A `FitterShape` requires a non-empty valid Shapely polygon.
- A `FitterShape` line-thickness range is exactly two ordered finite
  non-negative numeric values.
- A `FitterShape` padding value is a finite non-negative numeric scalar.
- Missing glyph outlines fall back to conservative line boxes.
- `component_to_fitter_shape()` derives fitting polygons from convex hulls or
  radius-based circular buffers.

## Fix Log

- Added a regression proof that `TextFitter.fit()` selects the largest valid
  font size over a bounded range.
- Added condition-marked tests for contained wrapped fits, fail-closed
  impossible fits, outline fallback, jitter acceptance/rejection, jitter margin
  clamping, binary-search optimality, minimum threshold handling, asymmetric
  bounds, exact-width wrapping, final outline replacement, and component
  adapters.
- Added scoped mutation configuration and filter.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Successful contained fit | Return lines, widths, positions, font size, thickness, geometry, and hull inside the target polygon | PO-TFITTER-001 | `test_text_fitter_fits_wrapped_text_inside_convex_shape` | killed |
| Fail-closed impossible fit | Return `None` for excessive inset or impossible width | PO-TFITTER-002 | `test_text_fitter_returns_none_for_impossible_or_unsafe_fits` | killed |
| Outline fallback | Use line boxes when glyph outlines are unavailable | PO-TFITTER-003 | `test_text_fitter_uses_rectangle_fallback_when_outlines_are_unavailable` | killed |
| Jitter containment | Accept contained offsets and reject escaping offsets | PO-TFITTER-004 | `test_text_fitter_jitter_accepts_contained_offsets_and_rejects_escape` | killed |
| Jitter margin boundary | Clamp finite negative margins and reject malformed/non-finite public values | PO-TFITTER-009 | `test_text_fitter_jitter_margin_is_clamped_before_offset_calculation`, `test_text_fitter_rejects_malformed_jitter_margins` | killed |
| Fitter shape boundary | Reject malformed polygons, ranges, padding, and adapter inputs before fitting math consumes them | PO-TFITTER-010 | `test_fitter_shape_normalizes_public_boundary_values`, malformed shape tests, `test_component_to_fitter_shape_reuses_public_shape_validation` | killed |
| Binary search | Select the largest valid font size and enforce minimum threshold | PO-TFITTER-005 | Binary-search and threshold tests | killed |
| Word wrapping | Use horizontal bounds, center lines, and allow exact-width fits | PO-TFITTER-006 | `test_text_fitter_word_wrap_uses_shape_width_and_centers_lines` | one equivalent survivor |
| Final outline correction | Replace line-box geometry with final outline geometry when outlines are available | PO-TFITTER-007 | `test_text_fitter_replaces_line_boxes_with_final_outline_geometry` | killed |
| Component adapters | Convert convex-hull and radius components into valid fitter shapes | PO-TFITTER-008 | `test_component_to_fitter_shape_uses_convex_hull_or_radius_contract` | killed |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Wrapping, binary search, fallback, and adapter behavior are deterministic under controlled inputs. | TEXT-FITTER-P1 tests |
| Behavioral/condition | yes | The slice defines public text fitting behavior. | Tests are marked `@pytest.mark.condition("TEXT-FITTER-P1")`. |
| Failure-mode | yes | Impossible fits must fail closed. | Excessive inset and impossible-width tests |
| Integration/live-path | yes | Text fitting depends on Shapely geometry, Pillow metrics, and outline fallback. | Focused gate includes existing text fitter tests |
| Contract/API compatibility | yes | Existing text fitter, SVG text, and text contract behavior must continue passing. | Focused mutation command includes existing tests |
| Property/fuzz | no | The proof partitions finite geometric cases directly. | Not applicable |
| Mutation | yes | Wrapping, containment, binary search, and adapter rows are proof-critical. | Mutation result recorded below |
| Security/adversarial | no | No file write, network, template, auth, SQL, or active-content surface is added. Font paths are consumed by existing Pillow/outlining paths. | Not applicable |
| Performance/resource | yes | The binary search must converge over the bounded font-size range. | Binary-search sequence test |
| Concurrency/race | no | No shared mutable state or background behavior is introduced. | Not applicable |
| Golden artifact/visual | no | This slice verifies geometry and metadata rather than rendered artifact pixels. | Not applicable |
| Regression | yes | This closes skipped font sizes in binary search and unmarked text fitter behavior. | TEXT-FITTER-P1 tests |
| Defensive/API boundary | yes | `FitterShape` is a public dataclass consumed by fitting math and component adapters. | TEXT-FITTER-SHAPE-P2 tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Weakening inner-boundary inset handling must fail.
- Weakening wrapping bounds, exact-width behavior, or centering must fail.
- Weakening fail-closed containment checks must fail.
- Weakening binary-search progression or minimum threshold handling must fail.
- Weakening final outline replacement must fail.
- Weakening component adapter defaults or geometry paths must fail.

Current result:

- Cosmic Ray 8.4.6, scoped to executable TEXT-FITTER-P1 rows: 107 work items,
  106 killed, and 1 survived.
- The survivor changes `line_w > available_width` to
  `line_w is available_width`. This is equivalent for the stated domain because
  `line_w` and `available_width` are separately computed float objects; object
  identity does not hold in normal measurements. Exact-width numeric behavior
  is tested and killed the `>=` and `==` variants.
- Cosmic Ray 8.4.6, scoped to TEXT-FITTER-SHAPE-P2 boundary rows: 50 work
  items, 50 killed, and 0 survived.

## PO-TFITTER-001: Successful Fits Stay Contained

### Claim

A successful fit returns text geometry and convex hull covered by the target
polygon.

### Domain

`TextFitter.fit()` with valid text, font path, font range, and a polygon with
enough interior space.

### Proof Method

The focused test fits wrapped text inside a rectangle and checks non-empty
geometry, line metadata, selected font-size bounds, fixed line thickness, and
shape containment.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-TFITTER-002: Impossible Fits Fail Closed

### Claim

Impossible or unsafe fits return `None` rather than partial geometry.

### Domain

Shapes whose padding/stroke inset removes the interior and text that cannot
fit within the maximum line width.

### Proof Method

Focused tests cover excessive inset and impossible-word width.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-TFITTER-003: Missing Outlines Use Conservative Boxes

### Claim

When glyph outlines are unavailable, fitting can still succeed with
conservative line-box geometry.

### Domain

`TextFitter.fit()` with `_create_line_outline()` returning `None`.

### Proof Method

The focused test replaces outline creation with a `None` return and verifies a
contained result.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-TFITTER-004: Jitter Cannot Escape The Shape

### Claim

Jittered placements are accepted only when the candidate geometry remains
contained.

### Domain

`TextFitter.fit(..., jitter_x=True|jitter_y=True)` with contained and escaping
candidate offsets.

### Proof Method

Focused tests compare baseline positions, accepted x/y offsets, rejected
escaping offsets, and jitter-margin clamping.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-TFITTER-005: Binary Search Selects The Largest Valid Size

### Claim

`fit()` returns the largest fitting font size and respects the configured
minimum size.

### Domain

Bounded integer font-size ranges.

### Proof Method

A deterministic fake `_check_fit()` accepts sizes through 11 and rejects larger
sizes. The test verifies the search sequence and returned size. A second test
verifies exact minimum threshold acceptance and below-threshold rejection.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-TFITTER-006: Word Wrap Uses Horizontal Bounds

### Claim

Word wrapping uses horizontal polygon bounds, centers accepted lines, and
accepts exact-width lines.

### Domain

Rectangular inner boundaries with asymmetric coordinate ranges and controlled
font metrics.

### Proof Method

Focused tests use stub font metrics to verify wrapped lines, line widths,
horizontal centering, vertical centering, asymmetric bounds, and exact-width
acceptance.

### Conclusion

Proven for the stated domain after tests and mutation pass; one object-identity
mutation is documented as equivalent.

## PO-TFITTER-007: Final Outlines Replace Temporary Geometry

### Claim

When final glyph outlines are available, the returned geometry and hull use
those outlines rather than temporary line boxes.

### Domain

`fit()` results where `_check_fit()` returns an initial geometry and final
outline creation returns a different geometry.

### Proof Method

The focused test injects distinct initial and outline geometries and verifies
that the result geometry, hull, and corrected position come from the outline.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-TFITTER-008: Component Adapters Produce Fitter Shapes

### Claim

Components with `convex_hull` or `radius` can be converted into valid
`FitterShape` instances, and unsupported objects return `None`.

### Domain

Regular polygon SVG components, radius-based stubs, and unsupported stubs.

### Proof Method

Focused tests verify polygon validity, positive area, default/custom adapter
settings, center coverage for radius buffers, and unsupported-object fallback.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-TFITTER-009: Jitter Margins Are Finite Numeric Values

### Claim

`TextFitter.fit(..., jitter_margin=...)` accepts only finite non-boolean numeric
values before jitter containment math runs.

### Domain

Public `TextFitter.fit()` calls with `jitter_x=True` or `jitter_y=True`.

### Dependencies

- `_normalize_jitter_margin()`
- `TextFitter.fit()`
- `TextFitter._compute_jitter_offsets()`

### Proof Method

`TextFitter.fit()` normalizes `jitter_margin` through
`_normalize_jitter_margin()` before calling `_compute_jitter_offsets()`. The
helper rejects booleans, strings, bytes, arbitrary nonnumeric objects, `nan`,
and infinity, while preserving the existing behavior that clamps finite
negative margins to zero. Focused tests force the public `fit()` path to reach
jitter handling and assert both the valid clamp behavior and malformed-value
rejection.

### Counterexamples And Exclusions

This proof does not change jitter sampling or containment semantics. It only
protects the public safety-margin scalar boundary.

### Conclusion

Focused tests cover the malformed public partitions. Mutation, full coverage,
lint, docs, and diff hygiene remain release-gate checks for the slice.

## PO-TFITTER-010: Fitter Shapes Fail Fast At The Boundary

### Claim

`FitterShape` accepts only valid geometry and finite ordered numeric fitting
parameters before downstream fitting math consumes them.

### Domain

Public `FitterShape(...)` construction and `component_to_fitter_shape(...)`
adapter calls.

### Dependencies

- `FitterShape.__post_init__()`
- `_normalize_fitter_polygon()`
- `_normalize_finite_range()`
- `_normalize_non_negative_float()`
- `_normalize_finite_float()`
- `component_to_fitter_shape()`

### Proof Method

`FitterShape.__post_init__()` normalizes every public construction path. It
requires a non-empty valid Shapely polygon, a two-value ordered finite
non-negative line-thickness range, and a finite non-negative padding value. The
focused tests partition valid normalization, non-polygon objects,
empty/degenerate polygons, invalid polygons with positive area, malformed range
arity, boolean/string/bytes coercion hazards, non-finite values, negative
values, reversed ranges, and the component adapter path.

### Counterexamples And Exclusions

This proof does not classify arbitrary Shapely geometry types as fit targets;
the current contract is specifically `Polygon`. It also does not alter text
fitting, wrapping, jitter, or outline behavior after a valid `FitterShape` is
constructed.

### Conclusion

Focused tests and mutation cover the public boundary partitions. Full coverage,
lint, docs, and diff hygiene remain release-gate checks for the slice.
