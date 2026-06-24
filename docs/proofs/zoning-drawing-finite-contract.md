# Zoning Drawing Finite Boundary Contract

This note applies the InkGen Definition of Done to the
ZONING-DRAWING-FINITE-P2 neutral zoning parameter slice. It closes the boundary
where public zoning dimensions accepted booleans and non-finite values before
geometry generation.

## Scope

The slice covers `ZoningDrawing` in `src/InkGen/drawing_components.py`.

The public behavior under review is:

- `ZoningDrawing.__init__()`
- `ZoningDrawing.parameters`
- `ZoningDrawing.create_from_dict()`
- `ZoningDrawing.to_group()`
- `_apply_parameters()`

## Architecture Impact

Affected surface:

- `src/InkGen/drawing_components.py`: neutral zoning parameter validation.
- `tests/test_drawing_components.py`: existing zoning materialization,
  serialization, and legacy-geometry compatibility tests plus new finite
  boundary tests.

Incoming dependencies:

- Public callers import `ZoningDrawing` from `InkGen`.
- Multi-format synthetic drawing builders use `ZoningDrawing` for zoning
  overlays before selecting SVG, PDF, or DXF output.
- `DXFDocument`, `DocumentPDF`, `ComponentGroupSVG`, and flow-document paths can
  consume the neutral drawing group emitted by zoning recipes.
- Legacy zoning compatibility tests compare neutral SVG output against
  `cad_component_groups.Zoning`.

Outgoing dependencies:

- Zoning construction depends on `Canvas`, `DrawingStyle`, `TextStyle`,
  `TextComponent`, and neutral drawing primitives.
- `to_group()` delegates to `DrawingComponentGroup.to_group()` for concrete
  renderer materialization.
- Validation depends only on Python numeric coercion and `math.isfinite()`.

Before/after edge changes:

- Before this slice, positive-real zoning parameters accepted booleans,
  `nan`, and infinities because validation only checked `isinstance(value,
  (float, int))` and negativity.
- After this slice, positive-real zoning parameters are coerced through one
  finite non-negative boundary helper before geometry generation.
- No dependency direction changed and no third-party dependency was introduced.

Cycle/layer/coupling/redundancy result:

- Cycle check: no new imports from concrete renderers were added.
- Layer check: neutral zoning still owns recipe geometry and delegates concrete
  output to `DrawingComponentGroup`.
- Coupling check: the helper is local to public zoning parameter validation.
- Redundancy check: no duplicate renderer logic or document-output logic was
  added.

Evidence source and freshness:

- Source-backed: `drawing_components.py`, `__init__.py`,
  `docs/dependency-map.md`, relevant ADRs, existing zoning tests, drawing-group
  proof, and CAD zoning proof were read before editing.
- Test-backed: focused tests exercise invalid constructor parameters, explicit
  zero overrides, serialized hydration rejection, valid SVG/PDF materialization,
  and legacy SVG geometry compatibility.

ADR/rule impact:

- ADR-0001 remains satisfied because grammar truth propagation through neutral
  groups is unchanged.
- ADR-0002 remains satisfied because PDF materialization remains delegated to
  the closed PDF renderer path.
- No new ADR is required because this is a boundary hardening change with no
  architecture decision change.

## Domain Definitions

- Positive-real zoning parameters are margins, zone widths, and inner/outer
  radii.
- Accepted values are finite, non-boolean numeric values greater than or equal
  to zero.
- Zone counts remain positive even integers.
- First-zone characters remain alphanumeric ASCII code points.
- Supported output materialization remains SVG and PDF through
  `DrawingComponentGroup.to_group()`; DXF consumes the same neutral group
  through `DXFDocument`.

## Fix Log

- Added `_coerce_finite_non_negative_float()`.
- Routed all `ZoningDrawing._POSITIVE_REALS` parameters through that helper.
- Added constructor, zero-override, and hydration tests for
  ZONING-DRAWING-FINITE-P2.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid finite non-negative dimensions | Preserve and coerce to floats | PO-ZD-FIN-001 | existing zoning materialization and new zero test | mutation target |
| Explicit zero dimension overrides | Preserve as supplied specific values | PO-ZD-FIN-002 | `test_zoning_drawing_preserves_zero_dimension_overrides` | mutation target |
| Boolean dimensions | Reject at public boundary | PO-ZD-FIN-003 | `test_zoning_drawing_rejects_invalid_dimension_parameters` | mutation target |
| Non-numeric dimensions | Reject at public boundary | PO-ZD-FIN-003 | same | mutation target |
| Negative dimensions | Reject at public boundary | PO-ZD-FIN-003 | same | mutation target |
| `nan` and infinities | Reject at public boundary | PO-ZD-FIN-003 | same | mutation target |
| Serialized invalid dimensions | Reject through `create_from_dict()` | PO-ZD-FIN-004 | `test_zoning_drawing_hydration_rejects_invalid_dimensions` | mutation target |
| Private mutation after construction | Excluded from public contract | Explicit exclusion | none | out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Validation helper and parameter boundary are deterministic. | ZONING-DRAWING-FINITE-P2 tests |
| Behavioral/condition | yes | The slice defines public zoning parameter behavior. | Tests marked `@pytest.mark.condition("ZONING-DRAWING-FINITE-P2")` |
| Failure-mode | yes | Invalid constructor and serialized values must fail before geometry. | Invalid-parameter and hydration tests |
| Integration/live-path | yes | Valid zoning still materializes through SVG/PDF paths. | Existing `test_neutral_zoning_*` tests |
| Contract/API compatibility | yes | Public parameters and legacy geometry compatibility must remain stable. | Existing round-trip and legacy comparison tests |
| Property/fuzz | no | This slice has a finite partitioned validation domain. | Not applicable |
| Mutation | yes | Validation guards and hydration routing are proof-critical. | Mutation gate recorded below |
| Security/adversarial | no | No file path, network, subprocess, secret, SQL, template, or active-content surface changed. | Not applicable |
| Performance/resource | no | The slice adds constant-time validation before existing font measurement work. | Code inspection |
| Concurrency/race | no | No shared state, sessions, locks, workers, or temp files changed. | Not applicable |
| Golden artifact/visual | yes | Valid zoning geometry must remain compatible with legacy SVG output. | Existing legacy geometry comparison |
| Regression | yes | This closes accepted boolean and non-finite dimensions. | Invalid-parameter tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Weakening `_POSITIVE_REALS` routing should fail invalid-dimension tests.
- Removing boolean rejection should fail invalid-dimension tests.
- Removing `isfinite()` checks should fail `nan` and infinity tests.
- Weakening negative-value rejection should fail invalid-dimension tests.
- Bypassing `create_from_dict()` constructor validation should fail hydration
  tests.

Current result:

- Cosmic Ray 8.4.6, scoped to positive-real zoning validation and hydration
  routing: 20 work items, 20 killed, and 0 survived.

## PO-ZD-FIN-001: Valid Dimensions Are Finite Non-Negative Floats

### Claim

Every public positive-real zoning parameter accepted by `ZoningDrawing` is
stored as a finite float greater than or equal to zero.

### Domain

All `_POSITIVE_REALS` parameters supplied through the constructor or through
`create_from_dict()`.

### Proof Method

`_apply_parameters()` routes every non-`None` positive-real value through
`_coerce_finite_non_negative_float()`. The helper excludes booleans, coerces
numeric values with `float()`, rejects non-finite values with `isfinite()`, and
rejects negatives before storage.

### Conclusion

Proven after focused tests and mutation pass.

## PO-ZD-FIN-002: Zero Overrides Are Preserved

### Claim

Zero is accepted as a valid explicit dimension and participates in zoning
specificity rules.

### Domain

Margin and zone-width parameter families where a more-specific value is `0.0`
and a less-specific fallback is nonzero.

### Proof Method

The validator permits `0.0`, and existing specificity code checks `is not None`
before falling back. The focused test asserts resolved zero margin and width
parameters after construction.

### Conclusion

Proven after focused tests and mutation pass.

## PO-ZD-FIN-003: Invalid Dimensions Fail Before Geometry

### Claim

Boolean, non-numeric, negative, `nan`, and infinite positive-real zoning
parameters raise before character measurement or geometry generation can
produce invalid drawing primitives.

### Domain

All constructor-supplied positive-real zoning parameters.

### Proof Method

`_apply_parameters()` validates keyword values before `_get_character_sizes()`,
`_set_margins()`, `_set_zoning_widths()`, and `_create_zoning()` run. The
focused invalid-parameter test covers each invalid partition.

### Conclusion

Proven after focused tests and mutation pass.

## PO-ZD-FIN-004: Hydration Cannot Bypass Validation

### Claim

Serialized `ZoningDrawing` payloads with invalid positive-real dimensions fail
through the same validation boundary as direct construction.

### Domain

Payloads passed to `ZoningDrawing.create_from_dict()` with invalid
`parameters` entries.

### Proof Method

`create_from_dict()` resolves canvas and styles, then delegates to `cls(...,
**payload["parameters"])`. The focused hydration test injects `nan` into the
serialized parameters and asserts the same validation failure.

### Conclusion

Proven after focused tests and mutation pass.

## Current Slice Decision

The slice keeps `ZoningDrawing` renderer-neutral and dependency-free. It adds
one local validation boundary instead of changing renderer behavior, legacy CAD
zoning behavior, or document-output behavior.
