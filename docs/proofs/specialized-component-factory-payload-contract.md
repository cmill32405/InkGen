# Specialized Component Factory Payload Contract Proof Obligations

This note applies the InkGen Definition of Done to the
SPECIALIZED-COMPONENT-FACTORY-PAYLOAD-P2 slice. It covers serialized
payload-envelope validation for specialized drawing component factories while
preserving the existing geometry and renderer contracts.

## Scope

The slice covers:

- `PolarCoordinateDrawingComponent.create_from_dict()`
- `PolygonalDrawingComponent.create_from_dict()`
- `RegularPolygonDrawingComponent.create_from_dict()`
- `Arc.create_from_dict()`
- `QuadraticBezier.create_from_dict()`
- `CubicBezier.create_from_dict()`
- `Path.create_from_dict()`

Renderer-specific SVG/PDF factory envelopes are out of scope for this slice.
Path command semantic validation remains delegated to `PathCommand`.

## Architecture Impact

Affected surface:

- `src/InkGen/component.py`: specialized factory payload-envelope validation.
- `tests/test_specialized_component_factory_payload_contract.py`:
  SPECIALIZED-COMPONENT-FACTORY-PAYLOAD-P2 behavioral tests.
- Existing radial scalar, arc finite, Bezier finite, path finite, component,
  and component-group tests provide dependent-path evidence.

Incoming dependencies:

- Direct callers use `parameters/create_from_dict()` round trips for component
  serialization.
- `ComponentGroup.create_from_dict()` dynamically dispatches into specialized
  component factories.
- Renderer paths depend on constructed component geometry, not on serialized
  factory internals.

Outgoing dependencies:

- Factories depend on `_component_payload()` and
  `_component_required_field()` for serialized root and field checks.
- Factories depend on `DrawingStyle.create_from_dict()` only when no explicit
  style argument is supplied.
- Geometry validity remains delegated to constructors and existing finite
  validation helpers.
- `Path` command validity remains delegated to `PathCommand`.
- No dependency or package was added.

Before/after edge changes:

- Before this slice, malformed specialized factory roots could fail through
  incidental `KeyError`, `TypeError`, or `AttributeError`.
- After this slice, malformed roots and missing required fields fail at the
  factory boundary before constructor, style, or renderer dispatch.
- Explicit style arguments still allow compact payloads that omit serialized
  style fields.

Cycle/layer/coupling/redundancy result:

- Cycle check: no import cycle is introduced.
- Layer check: component serialization remains in `component.py`; no renderer
  dependency was added to component factories.
- Coupling check: geometry validation is still owned by constructors and
  existing helpers.
- Redundancy check: the existing shared payload helpers are reused instead of
  duplicating root checks.

ADR/rule impact:

- No new ADR is required. The change reinforces the dependency-map rule that
  component geometry and serialization remain component-layer concerns.

## Domain Definitions

- Serialized specialized factory data must be a mapping with a top-level key
  equal to the component class name.
- The top-level class payload must be a mapping.
- Required geometry fields must be present before constructor dispatch.
- If no explicit style is supplied, the serialized style field must be present
  and is delegated to `DrawingStyle.create_from_dict()`.
- If an explicit style is supplied, compact geometry payloads without a
  serialized style field remain accepted.

## Fix Log

- Routed all scoped specialized factories through `_component_payload()`.
- Routed required geometry/style fields through `_component_required_field()`.
- Preserved optional `Arc.rotation` default behavior.
- Preserved optional `Path.commands` default behavior.
- Preserved explicit-style compact payload compatibility.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Malformed factory roots | Reject before incidental lookup errors | PO-SCFACT-001 | `test_specialized_component_factories_reject_malformed_payload_roots` | killed |
| Missing required fields | Reject before constructor/style dispatch | PO-SCFACT-002 | `test_specialized_component_factories_reject_missing_required_fields` | killed |
| Missing style without explicit style | Reject before style dispatch | PO-SCFACT-003 | `test_specialized_component_factories_require_style_when_not_explicit` | killed |
| Explicit style compact payloads | Preserve compatibility path | PO-SCFACT-004 | `test_specialized_component_factories_preserve_explicit_style_compact_payloads` | killed |
| Existing dependent paths | Preserve direct and group behavior | PO-SCFACT-005 | `test_component.py`, finite component tests, `test_component_group_contract.py` | killed |
| Renderer-specific factory envelopes | Excluded from this slice | Explicit exclusion | Not applicable | out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Factory root and required-field validation is deterministic. | SPECIALIZED-COMPONENT-FACTORY-PAYLOAD-P2 tests |
| Behavioral/condition | yes | This slice defines a public factory payload contract. | Tests are marked `@pytest.mark.condition("SPECIALIZED-COMPONENT-FACTORY-PAYLOAD-P2")`. |
| Failure-mode | yes | Malformed payloads must fail at the factory boundary. | Malformed root, missing-field, and missing-style tests |
| Integration/live-path | yes | Component groups dynamically dispatch into these factories. | Focused gate includes component-group tests |
| Contract/API compatibility | yes | Existing round trips and explicit style calls must continue passing. | Focused gate includes `test_component.py` |
| Property/fuzz | no | The changed domain is finite root/field shape validation. | Not applicable |
| Mutation | yes | Factory guard branches are proof-critical. | Mutation result recorded below |
| Security/adversarial | no | No path, network, subprocess, archive, SQL, template, or active-content surface changed. | Not applicable |
| Performance/resource | no | Adds constant-time mapping and key checks. | Code inspection |
| Concurrency/race | no | No shared state, locks, workers, or temp files changed. | Not applicable |
| Golden artifact/visual | no | No renderer output syntax changed. | Not applicable |
| Regression | yes | Prevents incidental lookup failures and silent malformed payload acceptance. | SPECIALIZED-COMPONENT-FACTORY-PAYLOAD-P2 tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Weakening root mapping checks must fail malformed-root tests.
- Weakening required-field checks must fail missing-field and missing-style
  tests.
- Changing explicit-style dispatch must fail compact-payload compatibility
  tests.
- Breaking valid specialized factory hydration must fail direct component and
  component-group dependent tests.

Current result:

- Focused dependent-path tests:
  `python -m pytest -q tests\test_specialized_component_factory_payload_contract.py tests\test_component.py tests\test_radial_scalar_contract.py tests\test_arc_finite_contract.py tests\test_bezier_finite_contract.py tests\test_path_finite_contract.py tests\test_component_group_contract.py`
  returned `112 passed`.
- Cosmic Ray 8.4.6, scoped to SPECIALIZED-COMPONENT-FACTORY-PAYLOAD-P2
  specialized factory dispatch rows: 17 work items, 17 killed, 0 survivors.
- Mutation testing exposed a missing assertion for omitted `Arc.rotation`; the
  compact-payload compatibility test now proves the default remains `0.0`.
- Full coverage gate:
  `python -m pytest --cov=src/InkGen --cov-branch --cov-report=term -q`
  returned `670 passed` with `93%` coverage.
- Ruff lint passed for touched implementation, tests, and mutation filter.
- Ruff format passed for the new test and mutation filter.
  `src\InkGen\component.py` remains a known broad-format exception and was not
  broad-formatted.
- MkDocs strict build passed.
- `git diff --check` passed.

## PO-SCFACT-001: Factory Roots Fail Explicitly

### Claim

Scoped specialized factories reject non-mapping roots, missing root keys, and
non-mapping payloads before incidental lookup errors.

### Domain

Public factory calls for `PolarCoordinateDrawingComponent`,
`PolygonalDrawingComponent`, `RegularPolygonDrawingComponent`, `Arc`,
`QuadraticBezier`, `CubicBezier`, and `Path`.

### Proof Method

`_component_payload()` requires a mapping root, the expected class key, and a
mapping payload. Focused condition tests cover each malformed root partition for
every scoped factory.

### Conclusion

Supported by focused tests, mutation testing, full coverage tests, and MkDocs
strict build.

## PO-SCFACT-002: Required Factory Fields Fail Explicitly

### Claim

Scoped factories reject missing required geometry fields before constructor or
style dispatch.

### Domain

Factory payloads with valid roots but missing required geometry fields.

### Proof Method

`_component_required_field()` checks required fields by owner name before
constructors are called. Focused condition tests cover representative required
field omissions across polar, polygonal, regular polygon, arc, quadratic
Bezier, and cubic Bezier factories.

### Conclusion

Supported by focused tests, mutation testing, full coverage tests, and MkDocs
strict build.

## PO-SCFACT-003: Style Fields Are Required Without Explicit Style

### Claim

Scoped factories require a serialized style field when no explicit style
argument is supplied.

### Domain

Valid factory roots for every scoped specialized component where `style` is not
passed as an argument.

### Proof Method

Each factory resolves style through `_component_required_field(payload,
"style", owner)` before calling `DrawingStyle.create_from_dict()`. Focused
condition tests cover the missing-style partition for every scoped factory.

### Conclusion

Supported by focused tests, mutation testing, full coverage tests, and MkDocs
strict build.

## PO-SCFACT-004: Explicit Style Compact Payloads Remain Compatible

### Claim

Callers that supply an explicit style can still hydrate compact payloads that
omit serialized style fields.

### Domain

Scoped specialized factory calls with explicit `DrawingStyle` objects and valid
required geometry fields.

### Proof Method

Factories validate root and required geometry fields, then use the explicit
style argument without requiring a serialized style field. The focused test
hydrates every scoped style-bearing factory through that path.

### Conclusion

Supported by focused tests, mutation testing, full coverage tests, and MkDocs
strict build.

## PO-SCFACT-005: Existing Dependent Paths Are Preserved

### Claim

Existing direct round trips, finite geometry behavior, and component-group
dependent paths remain unchanged.

### Domain

Valid payloads emitted by `parameters` and hydrated through direct factory
calls or `ComponentGroup.create_from_dict()`.

### Proof Method

Existing component, radial scalar, arc finite, Bezier finite, path finite, and
component-group tests exercise valid construction, existing geometry
validation, and dynamic group dispatch after the factory boundary changes.

### Conclusion

Supported by focused tests, mutation testing, full coverage tests, and MkDocs
strict build.
