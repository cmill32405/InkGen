# Boundary Canvas Payload Contract Proof Obligations

This note applies the InkGen Definition of Done to the
BOUNDARY-CANVAS-PAYLOAD-P2 slice. It covers serialized payload-envelope
validation for `Boundary` and `Canvas` factory hydration without changing the
existing finite geometry, convex hull, dimension, or unit contracts.

## Scope

The slice covers:

- `Boundary.create_from_dict()`
- `Canvas.create_from_dict()`
- `_boundary_payload()`
- `_boundary_required_field()`

Finite hull, canvas dimension, unit, and layer containment validation remains
covered by the existing BOUNDARY-CANVAS-P1 proof.

## Architecture Impact

Affected surface:

- `src/InkGen/boundary.py`: boundary/canvas factory root and required-field
  validation.
- `tests/test_boundary_canvas_payload_contract.py`:
  BOUNDARY-CANVAS-PAYLOAD-P2 behavioral tests.
- Existing boundary, document-model, and document tests provide compatibility
  and dependent-path evidence.

Incoming dependencies:

- `Layer`, `Layers`, and `Document` hydrate canvases through
  `Canvas.create_from_dict()`.
- SVG/PDF documents and parser-facing truth records depend on stable canvas
  dimensions and units.
- Boundary serialization is used by collision and containment-related tests.

Outgoing dependencies:

- `Boundary.create_from_dict()` delegates hull and `outer_boundary` validation
  to `Boundary.__init__()`.
- `Canvas.create_from_dict()` delegates dimension and unit validation to
  `Canvas.__init__()`.
- No dependency or package was added.

Before/after edge changes:

- Before this slice, malformed `Boundary` and `Canvas` factory roots failed
  through incidental subscription errors or missing-key lookups.
- After this slice, both factories validate serialized root and required fields
  before constructor dispatch.
- Valid serialized payloads continue to hydrate through existing public
  constructors.

Cycle/layer/coupling/redundancy result:

- Cycle check: no import cycle is introduced.
- Layer check: core boundary/canvas serialization remains in `boundary.py`.
- Coupling check: no renderer-specific behavior is added.
- Redundancy check: one shared payload helper handles repeated root checks.

ADR/rule impact:

- No new ADR is required. This reinforces the dependency-map rule that core
  primitives own canvas and boundary input contracts before document or renderer
  paths consume them.

## Domain Definitions

- Serialized boundary/canvas factory data must be a mapping with a top-level key
  equal to the class name.
- The top-level class payload must be a mapping.
- Required fields must be present before constructor dispatch.
- Existing field-value validation remains delegated to `Boundary.__init__()` and
  `Canvas.__init__()`.

## Fix Log

- Added `_boundary_payload()` to validate boundary/canvas factory root
  mappings.
- Added `_boundary_required_field()` to validate required payload fields.
- Routed `Boundary` and `Canvas` factory paths through the shared helpers.
- Added document-hydration dependent-path coverage for nested canvas payloads.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Malformed factory roots | Reject before incidental subscription errors | PO-BCPAY-001 | `test_boundary_canvas_factories_reject_malformed_payload_roots` | killed |
| Missing required fields | Reject before constructor dispatch | PO-BCPAY-002 | `test_boundary_canvas_factories_reject_missing_required_fields` | killed |
| Valid payloads | Preserve existing boundary/canvas hydration | PO-BCPAY-003 | `test_boundary_canvas_factories_preserve_valid_hydration` | killed |
| Dependent document path | Preserve document canvas hydration and failure propagation | PO-BCPAY-004 | `test_canvas_payload_contract_remains_live_in_document_hydration` | killed |
| Field-value validation | Delegated to BOUNDARY-CANVAS-P1 | Explicit delegation | Existing boundary/canvas tests | previously covered |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Factory root and required-field validation is deterministic. | BOUNDARY-CANVAS-PAYLOAD-P2 tests |
| Behavioral/condition | yes | This slice defines a public factory payload contract. | Tests are marked `@pytest.mark.condition("BOUNDARY-CANVAS-PAYLOAD-P2")`. |
| Failure-mode | yes | Malformed payloads must fail at the factory boundary. | Malformed root and missing-field tests |
| Integration/live-path | yes | Document hydration consumes canvas payloads. | Dependent document hydration test |
| Contract/API compatibility | yes | Existing boundary/canvas payloads must continue hydrating. | Existing boundary and document tests |
| Property/fuzz | no | The changed domain is finite root/field shape validation. | Not applicable |
| Mutation | yes | Factory guard branches are proof-critical. | Mutation result recorded below |
| Security/adversarial | no | No path, network, subprocess, archive, SQL, template, or active-content surface changed. | Not applicable |
| Performance/resource | no | Adds constant-time mapping and key checks. | Code inspection |
| Concurrency/race | no | No shared state, locks, workers, or temp files changed. | Not applicable |
| Golden artifact/visual | no | No renderer output syntax changed. | Not applicable |
| Regression | yes | Prevents incidental lookup failures in serialized boundary/canvas hydration. | BOUNDARY-CANVAS-PAYLOAD-P2 tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Weakening root mapping checks must fail malformed-root tests.
- Weakening required-field checks must fail missing-field tests.
- Changing valid hydration dispatch must fail boundary/canvas round-trip tests.
- Breaking document canvas hydration must fail dependent document tests.

Current result:

- Focused dependent-path tests:
  `python -m pytest -q tests\test_boundary_canvas_payload_contract.py tests\test_boundary.py tests\test_boundary_canvas_contract.py tests\test_document_model_contract.py tests\test_document.py`
  returned `70 passed`.
- Cosmic Ray 8.4.6, scoped to BOUNDARY-CANVAS-PAYLOAD-P2 helper and factory
  rows: 6 work items, 6 killed, 0 survivors.
- Full coverage gate:
  `python -m pytest --cov=src/InkGen --cov-branch --cov-report=term -q`
  returned `691 passed` with `94%` coverage.
- Ruff lint passed for touched implementation, tests, and mutation filter.
- Ruff format passed for touched implementation, tests, and mutation filter.
- MkDocs strict build passed.
- `git diff --check` passed.

## PO-BCPAY-001: Factory Roots Fail Explicitly

### Claim

`Boundary` and `Canvas` factories reject non-mapping roots, missing root keys,
and non-mapping payloads before incidental lookup errors.

### Domain

Public factory calls for `Boundary.create_from_dict()` and
`Canvas.create_from_dict()`.

### Proof Method

`_boundary_payload()` requires a mapping root, the expected class key, and a
mapping payload. Focused condition tests cover each malformed root partition for
both scoped factories.

### Conclusion

Supported by focused tests, mutation testing, full coverage tests, and MkDocs
strict build.

## PO-BCPAY-002: Required Factory Fields Fail Explicitly

### Claim

`Boundary` and `Canvas` factories reject missing required payload fields before
constructor dispatch.

### Domain

Factory payloads with valid roots but missing `hull`, `outer_boundary`,
`width`, `height`, or `units`.

### Proof Method

`_boundary_required_field()` checks required fields by owner name before values
are passed to constructors. Focused condition tests cover representative
required-field omissions for both factories.

### Conclusion

Supported by focused tests, mutation testing, full coverage tests, and MkDocs
strict build.

## PO-BCPAY-003: Valid Hydration Is Preserved

### Claim

Valid serialized `Boundary` and `Canvas` payloads still hydrate through
existing public constructors.

### Domain

Serialized payloads matching the public `parameters` shape for `Boundary` and
`Canvas`.

### Proof Method

Factory methods validate envelope shape and then pass payload values to the
same constructors used before this slice. Focused tests and existing boundary
tests exercise valid hydration.

### Conclusion

Supported by focused tests, mutation testing, full coverage tests, and MkDocs
strict build.

## PO-BCPAY-004: Document Hydration Still Consumes Canvas Payloads

### Claim

Document factory hydration continues to consume valid canvas payloads and
surfaces malformed nested canvas payloads at the canvas factory boundary.

### Domain

`Document.create_from_dict()` with serialized `Canvas` payloads.

### Proof Method

The dependent-path test hydrates a valid document and checks its serialized
canvas, then verifies malformed nested canvas payloads fail with canvas factory
error messages.

### Conclusion

Supported by focused tests, mutation testing, full coverage tests, and MkDocs
strict build.
