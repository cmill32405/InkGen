# Zoning Drawing Layout Contract

This note applies the InkGen Definition of Done to the
`ZONING-DRAWING-LAYOUT-P2` slice. It closes the boundary where a valid canvas
and valid scalar parameters could still produce an impossible zoning layout and
fail later through downstream primitive construction.

## Scope

The slice covers `ZoningDrawing` in `src/InkGen/drawing_components.py`:

- `ZoningDrawing.__init__()`
- `ZoningDrawing.create_from_dict()`
- `ZoningDrawing._create_zoning()`
- `_validate_zoning_layout()`

Out of scope:

- Changing the zoning geometry algorithm for valid layouts.
- Changing default margin, zone-width, or label selection policy.
- Legacy SVG-specific `cad_component_groups.Zoning` behavior.

## Dependency Review

Affected surface:

- `src/InkGen/drawing_components.py`: renderer-neutral zoning layout
  validation.
- `tests/test_drawing_components.py`: direct construction and hydration
  failure-mode tests.
- `tests/mutation/filter_zoning_drawing_layout_work_items.py`: scoped mutation
  filter for the layout boundary.

Incoming dependencies:

- Public callers import `ZoningDrawing` from `InkGen`.
- SVG, PDF, DXF, and document-output paths consume the neutral drawing group
  after zoning construction succeeds.
- Serialized zoning payloads hydrate through `ZoningDrawing.create_from_dict()`.

Outgoing dependencies:

- Zoning construction depends on `Canvas`, `DrawingStyle`, `TextStyle`, and
  renderer-neutral drawing primitives.
- The layout check depends only on derived numeric widths and heights already
  calculated inside `ZoningDrawing._create_zoning()`.
- No dependency was added.

Public contract:

- The outer zoning rectangle must have positive width and height.
- The inner drawing area after margins and zone-width bands must have positive
  width and height.
- Impossible layouts fail at the zoning boundary before any drawing primitive
  is constructed.

Serialized/artifact contract:

- `parameters` shape is unchanged.
- Valid serialized payloads still hydrate and materialize.
- Serialized impossible layouts fail through the same constructor path as direct
  construction.

Cycle/layer/coupling/redundancy result:

- Cycle check: no new imports or dependency cycles.
- Layer check: validation remains in the neutral authoring recipe before
  renderer materialization.
- Coupling check: no renderer-specific behavior is introduced.
- Redundancy check: downstream primitive geometry validation remains intact,
  but zoning now owns zoning-specific layout feasibility.

ADR/rule impact:

- No ADR is required. This is boundary hardening with no architecture decision
  change and no new library dependency.

## Domain Definitions

- Outer drawing area is `canvas width - left_margin - right_margin` by
  `canvas height - top_margin - bottom_margin`.
- Inner drawing area subtracts both margins and zoning band widths from the
  canvas dimensions.
- A valid zoning layout has strictly positive outer and inner width and height.

## Fix Log

- Added `_validate_zoning_layout()`.
- Routed `ZoningDrawing._create_zoning()` through the helper before creating
  `RectangleDrawing`, `LineDrawing`, or `TextDrawing` primitives.
- Reused computed `outer_width` and `outer_height` values for the outer
  rectangle after validation.
- Added direct construction and serialized hydration tests for impossible
  layouts, including negative and exact-zero outer and inner boundary cases.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid zoning layout | Preserve | PO-ZD-LAYOUT-001 | existing zoning materialization and legacy-geometry tests | full regression gate |
| Non-positive outer area | Reject before primitive construction | PO-ZD-LAYOUT-002 | `test_zoning_drawing_rejects_impossible_layouts_before_primitive_construction` | killed |
| Non-positive inner area | Reject before primitive construction | PO-ZD-LAYOUT-003 | same | killed |
| Serialized impossible layout | Reject through hydration | PO-ZD-LAYOUT-004 | `test_zoning_drawing_hydration_rejects_impossible_layouts_before_primitive_construction` | killed |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | `_validate_zoning_layout()` is deterministic. | direct impossible-layout tests |
| Behavioral/condition | yes | The slice defines `ZONING-DRAWING-LAYOUT-P2`. | condition-marked tests |
| Failure-mode | yes | Impossible layouts previously failed through downstream primitive geometry. | direct and hydration failure tests |
| Integration/live-path | yes | Valid zoning still materializes through SVG/PDF and legacy comparison paths. | existing zoning tests |
| Contract/API compatibility | yes | Parameters and valid hydration remain unchanged. | existing round-trip and payload tests |
| Property/fuzz | no | The layout partitions are finite and explicitly tested. | explicit partitions |
| Mutation | yes | Layout guard comparisons and call routing are proof-critical. | Cosmic Ray gate |
| Security/adversarial | limited | Serialized payloads may be untrusted but do not touch filesystem, network, subprocesses, SQL, or active content. | malformed payload tests |
| Performance/resource | no | Adds constant-time validation before existing geometry generation. | code inspection |
| Golden artifact/visual | yes | Valid SVG geometry compatibility is preserved. | legacy geometry comparison |
| Regression | yes | Prevents incidental `RectangleDrawing` errors for impossible zoning layouts. | impossible-layout tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Removing the `_validate_zoning_layout()` call should fail direct and
  hydration impossible-layout tests.
- Weakening outer width or height comparisons should fail outer-area tests.
- Weakening inner width or height comparisons should fail inner-area tests.

Current result:

- Focused tests: `72 passed`.
- Compatibility tests: `193 passed`.
- Scoped Cosmic Ray mutation: `24 killed`, `0 survived`.
- Full coverage gate: `1550 passed`, `95%` total branch coverage.

## PO-ZD-LAYOUT-001: Valid Layouts Are Preserved

### Claim

Valid zoning layouts continue to construct, serialize, hydrate, and materialize
through SVG/PDF paths.

### Domain

Existing valid `ZoningDrawing` fixtures with positive outer and inner drawing
areas.

### Proof Method

The new helper only rejects derived outer or inner dimensions that are less than
or equal to zero. Existing materialization, payload, and legacy geometry tests
cover valid zoning layouts.

### Conclusion

Passed. Focused, compatibility, and full coverage gates preserved valid zoning
materialization and serialized payload behavior.

## PO-ZD-LAYOUT-002: Non-Positive Outer Layouts Fail At Zoning Boundary

### Claim

Margins that consume the full canvas width or height fail before any primitive
is constructed.

### Domain

Constructor and hydration paths whose derived outer width or height is less
than or equal to zero.

### Proof Method

`ZoningDrawing._create_zoning()` computes `outer_width` and `outer_height` and
calls `_validate_zoning_layout()` before adding components to the drawing group.
The focused test supplies oversized horizontal and vertical margins, including
negative and exact-zero derived outer-area cases, and asserts the
zoning-specific error.

### Conclusion

Passed. Scoped mutation killed the proof-critical comparison changes for outer
width and height, and full tests passed.

## PO-ZD-LAYOUT-003: Non-Positive Inner Layouts Fail At Zoning Boundary

### Claim

Margins and zoning bands that consume the inner drawing area fail before
downstream rectangle, line, or text primitives are constructed.

### Domain

Constructor and hydration paths whose derived inner width or height is less
than or equal to zero.

### Proof Method

`_validate_zoning_layout()` checks `inner_width` and `inner_height` before
`_create_zoning()` creates the outer rectangle, inner rectangle, zone lines, or
zone labels. Focused tests cover too-small default canvases and oversized zone
widths, including negative and exact-zero derived inner-area cases.

### Conclusion

Passed. Scoped mutation killed the proof-critical comparison changes for inner
width and height, and full tests passed.

## PO-ZD-LAYOUT-004: Hydration Cannot Bypass Layout Validation

### Claim

Serialized zoning payloads cannot hydrate impossible layouts into public
zoning state.

### Domain

Payloads passed to `ZoningDrawing.create_from_dict()` with canvas and parameter
combinations that produce non-positive outer or inner dimensions.

### Proof Method

`create_from_dict()` delegates to `cls(..., **parameters)`, which runs
`_create_zoning()` and therefore `_validate_zoning_layout()`. The hydration
test mutates a valid serialized payload to use a too-small canvas and asserts
the same layout failure.

### Conclusion

Passed. Hydration delegates through the live constructor path and cannot bypass
layout validation.
