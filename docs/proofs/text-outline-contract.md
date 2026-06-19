# Text Outline Contract Proof Obligations

This note applies the InkGen Definition of Done to the TEXT-OUTLINE-P1 text
outline slice. It focuses on DPI-aware unit conversion, deterministic path
sampling, visible glyph geometry, one-pixel margins, global margin defaults, and
whitespace/font-metric fallback geometry.

## Scope

The slice covers:

- `set_add_one_pixel_margin_default()`
- `_px_to_units()`
- `sample_path_points()`
- `outline_for_text()` public output contract

HarfBuzz shaping internals, FontTools glyph drawing internals, and defensive
Shapely non-polygon fallback branches are out of scope except where they affect
the public outline dictionary.

## Architecture Impact

Affected surface:

- `src/InkGen/text_outline.py`: DPI-aware pixel-to-unit conversion.
- `tests/test_text_outline_contract.py`: TEXT-OUTLINE-P1 condition tests.
- `tests/mutation/text_outline_cosmic_ray.toml`: scoped mutation gate.
- `tests/mutation/filter_text_outline_work_items.py`: proof-critical mutation
  filter.

Incoming dependencies:

- `TextComponent` uses `outline_for_text()` for text geometry, bbox, and convex
  hull calculations.
- `TextFitter` uses `outline_for_text()` for glyph-aware fitting and falls back
  to line boxes when outlines are unavailable.
- CAD zoning tests depend on text outline widths for zone-label sizing.
- Public callers import `outline_for_text()` from `InkGen`.

Outgoing dependencies:

- `text_outline.py` depends on HarfBuzz for shaping, FontTools for glyph
  outlines, svgpathtools for path sampling, and Shapely for bbox/hull geometry.
- No dependency was added.

Before/after edge changes:

- Before this slice, `_px_to_units()` accepted a `dpi` argument but used a fixed
  96 DPI conversion for inches and millimeters.
- After this slice, `_px_to_units()` uses the requested DPI while preserving the
  prior default behavior at 96 DPI.
- After this slice, condition tests pin path endpoints, zero-length segments,
  visible glyph output shape, margin expansion, global margin behavior, and
  whitespace fallback dimensions.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced.
- Layer check: outline generation remains in the text geometry utility layer.
- Coupling check: no renderer-specific dependency was added.
- Redundancy check: `_px_to_units()` remains the single conversion helper for
  margin and whitespace fallback units.

ADR/rule impact:

- No new ADR is required. This reinforces the dependency-map rule that geometry
  helpers must prove unit conversion and fallback behavior before downstream
  renderers consume their results.

## Domain Definitions

- Pixel conversion maps pixels to inches as `px / dpi`.
- Pixel conversion maps pixels to millimeters as `px * 25.4 / dpi`.
- Pixel units return the input value unchanged.
- Path sampling includes endpoints for every segment and handles zero-length
  segments without division-by-zero.
- Visible text returns an SVG path, sampled points, bbox, convex hull, and path
  bbox.
- A one-pixel margin expands the hull by one converted pixel in the requested
  units.
- When `add_one_pixel_margin` is `None`, the global margin default is used.
- Whitespace or zero-outline text uses font metrics to produce a finite bbox and
  hull.

## Fix Log

- Fixed `_px_to_units()` to honor the documented `dpi` argument.
- Added condition-marked tests for unit conversion, path sampling, visible
  outlines, margin behavior, global defaults, and whitespace fallback.
- Added scoped mutation configuration and filter.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Unit conversion | Convert px to mm/in using requested DPI; preserve px units | PO-TOUTLINE-001 | `test_text_outline_converts_pixels_using_requested_units_and_dpi` | killed |
| Path sampling | Include endpoints, finite points, exact simple-line samples, and zero-length segment behavior | PO-TOUTLINE-002 | `test_text_outline_samples_all_path_segments_deterministically` | killed |
| Visible glyph output | Return non-empty path, points, bbox, hull, and path bbox with finite values | PO-TOUTLINE-003 | `test_text_outline_returns_finite_geometry_for_visible_text` | killed |
| Margin expansion | Expand bbox by one converted pixel in requested units | PO-TOUTLINE-004 | `test_text_outline_margin_expands_bounds_by_requested_unit_size` | killed |
| Global margin default | `None` uses global default and explicit values override it | PO-TOUTLINE-005 | `test_text_outline_global_margin_default_matches_explicit_margin` | killed |
| Whitespace fallback | Use font metrics and requested DPI for whitespace bbox/hull | PO-TOUTLINE-006 | `test_text_outline_whitespace_uses_font_metric_fallback_and_dpi` | killed |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Unit conversion and path sampling are deterministic. | TEXT-OUTLINE-P1 tests |
| Behavioral/condition | yes | The slice defines public outline behavior. | Tests are marked `@pytest.mark.condition("TEXT-OUTLINE-P1")`. |
| Failure-mode | yes | Zero-length path segments and whitespace text must return safe geometry rather than fail. | Sampling and whitespace tests |
| Integration/live-path | yes | Text fitter, text components, and SVG tests consume outline behavior. | Focused gate includes existing text fitter/text/SVG tests |
| Contract/API compatibility | yes | Existing outline tests and downstream text tests must continue passing. | Focused gate evidence |
| Property/fuzz | no | The proof partitions deterministic unit, sampling, visible-text, and whitespace cases directly. | Not applicable |
| Mutation | yes | Unit conversion, path sampling, margin, and fallback rows are proof-critical. | Mutation result recorded below |
| Security/adversarial | no | The slice does not add file writes, network, templates, auth, SQL, or active content. Existing font-path loading remains unchanged. | Not applicable |
| Performance/resource | no | The change is constant-time arithmetic in an existing helper. | Code inspection |
| Concurrency/race | yes | Global margin default is mutable shared state. | Global default test resets state and verifies final default |
| Golden artifact/visual | no | This slice verifies geometry outputs rather than rendered pixels. | Not applicable |
| Regression | yes | This closes the documented `dpi` parameter being ignored. | DPI conversion tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Weakening DPI conversion must fail unit and whitespace fallback tests.
- Weakening path sampling endpoint/zero-segment behavior must fail sampling
  tests.
- Weakening margin-default selection or margin size must fail margin tests.
- Weakening whitespace font-metric width/height calculations must fail fallback
  tests.

Current result:

- Cosmic Ray 8.4.6, scoped to executable TEXT-OUTLINE-P1 rows: 19 work items,
  19 killed, and 0 survived.

## PO-TOUTLINE-001: Pixel Conversion Is DPI-Aware

### Claim

Pixels convert to inches and millimeters using the caller-provided DPI.

### Domain

`_px_to_units(px, units, dpi)` with inch, millimeter, and pixel units.

### Proof Method

The focused test checks 96 DPI and 300 DPI conversions and verifies pixel units
return unchanged values.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-TOUTLINE-002: Path Sampling Includes Stable Endpoints

### Claim

Path sampling includes segment endpoints and handles zero-length segments
without division-by-zero.

### Domain

SVG line paths with ordinary and zero-length segments.

### Proof Method

Focused tests assert exact sampled points for a simple line, endpoint presence
for a multi-segment path, dense default sampling, and zero-length samples.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-TOUTLINE-003: Visible Text Returns Finite Geometry

### Claim

Visible text returns finite path, point, bbox, hull, and path-bbox data.

### Domain

`outline_for_text()` with a valid installed TrueType font and visible text.

### Proof Method

The focused test checks the returned dictionary shape, non-empty geometry
fields, positive bbox dimensions, and finite bbox/hull coordinates.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-TOUTLINE-004: One-Pixel Margins Expand Bounds

### Claim

When requested, the one-pixel margin expands the outline bbox by one converted
pixel in the requested units.

### Domain

`outline_for_text(add_one_pixel_margin=True)` using millimeter units and custom
DPI.

### Proof Method

Focused tests compare base and expanded bboxes with a tolerance for Shapely
buffer arithmetic.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-TOUTLINE-005: Global Margin Default Is Explicit

### Claim

`add_one_pixel_margin=None` uses the global margin default, and explicit values
do not leave global state dirty.

### Domain

`set_add_one_pixel_margin_default()` and `outline_for_text()`.

### Proof Method

Focused tests enable the global default, compare automatic and explicit margin
output, reset the default, and verify disabled output differs from explicit
margin output.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-TOUTLINE-006: Whitespace Uses Font Metrics

### Claim

Whitespace or zero-outline text returns a finite bbox and hull derived from font
metrics and requested DPI.

### Domain

Whitespace text with a valid TrueType font.

### Proof Method

Focused tests verify empty path/samples, finite positive bbox/hull output, DPI
scaling, and an expected width calculated from the font's space advance.

### Conclusion

Proven for the stated domain after tests and mutation pass.
