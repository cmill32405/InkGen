# Component Factory Payload Contract Proof Obligations

This note applies the InkGen Definition of Done to the
COMPONENT-FACTORY-PAYLOAD-P2 primitive component factory slice. It covers
serialized payload-envelope validation for the base component factories used by
component-group hydration.

## Scope

The slice covers:

- `Component.create_from_dict()`
- `DrawingComponent.create_from_dict()`
- `StandardDrawingComponent.create_from_dict()`
- `SingleDimensionDrawingComponent.create_from_dict()`
- `WidthHeightDrawingComponent.create_from_dict()`
- `TextComponent.create_from_dict()`
- `_component_payload()`
- `_component_required_field()`

Specialized curve, polygon, path, and renderer factories are out of scope for
this slice and remain candidates for separate hardening slices.

## Architecture Impact

Affected surface:

- `src/InkGen/component.py`: primitive factory payload-envelope validation.
- `tests/test_component_factory_payload_contract.py`:
  COMPONENT-FACTORY-PAYLOAD-P2 behavioral tests.
- `tests/test_component.py`, `tests/test_component_group_contract.py`,
  `tests/test_width_height_contract.py`, and
  `tests/test_single_dimension_contract.py`: compatibility and dependent-path
  evidence.

Incoming dependencies:

- `ComponentGroup.create_from_dict()` dynamically dispatches into these
  factories.
- `Layer.create_from_dict()`, `Document`, `DocumentSVG`, and `DocumentPDF`
  reach these factories through component-group hydration.
- Existing examples and tests depend on `parameters/create_from_dict()` round
  trips.

Outgoing dependencies:

- Drawing factories depend on `DrawingStyle.create_from_dict()` when an
  explicit style is not supplied.
- Text factories depend on `TextStyle.create_from_dict()` when an explicit
  style is not supplied.
- Geometry and text field semantics remain delegated to constructors, setters,
  and existing validation helpers.
- No dependency or package was added.

Before/after edge changes:

- Before this slice, malformed primitive component factory roots could fail
  through incidental `KeyError` or subscription errors.
- Before this slice, `Component.create_from_dict()` and
  `DrawingComponent.create_from_dict(data, style)` could silently ignore
  malformed payload data.
- After this slice, the scoped factories validate their serialized root and
  required fields before constructing components or styles.
- Explicit style arguments still allow compact geometry/text payloads for
  backward compatibility with existing callers.

Cycle/layer/coupling/redundancy result:

- Cycle check: no new import cycle is introduced.
- Layer check: component serialization remains in `component.py`.
- Coupling check: renderer-specific behavior is not added to component
  factories.
- Redundancy check: one shared payload helper handles repeated root validation.

ADR/rule impact:

- No new ADR is required. The change reinforces the dependency-map rule that
  `parameters/create_from_dict()` round trips are protected public contracts.

## Domain Definitions

- Serialized primitive factory data must be a mapping with a top-level key equal
  to the component class name.
- The top-level class payload must be a mapping.
- Required geometry/text fields must be present before constructor dispatch.
- If no explicit style is supplied, the serialized style field must be present
  and is delegated to the owning style factory.
- If an explicit style is supplied, compact geometry/text payloads without a
  serialized style field remain accepted.

## Fix Log

- Added `_component_payload()` to validate factory root mappings.
- Added `_component_required_field()` to validate required payload fields.
- Routed `Component`, `DrawingComponent`, `StandardDrawingComponent`,
  `SingleDimensionDrawingComponent`, `WidthHeightDrawingComponent`, and
  `TextComponent` factory paths through the shared helpers.
- Preserved valid explicit-style compact payload compatibility.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Malformed factory roots | Reject before incidental subscription errors | PO-CFACT-001 | `test_component_factories_reject_malformed_payload_roots` | killed |
| Missing required fields | Reject before constructor/style dispatch | PO-CFACT-002 | `test_component_factories_reject_missing_required_payload_fields` | killed |
| Explicit style compact payloads | Preserve existing accepted compatibility path | PO-CFACT-003 | `test_component_factories_preserve_explicit_style_payload_compatibility` | killed |
| Valid serialized round trips | Preserve existing component and component-group behavior | PO-CFACT-004 | `test_component.py`, `test_component_group_contract.py` | killed |
| Specialized curve/path/polygon factories | Excluded from this slice | Explicit exclusion | Not applicable | out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Factory root and required-field validation is deterministic. | COMPONENT-FACTORY-PAYLOAD-P2 tests |
| Behavioral/condition | yes | This slice defines a public factory payload contract. | Tests are marked `@pytest.mark.condition("COMPONENT-FACTORY-PAYLOAD-P2")`. |
| Failure-mode | yes | Malformed payloads must fail at the factory boundary. | Malformed root and missing-field tests |
| Integration/live-path | yes | Component groups dynamically dispatch into these factories. | Focused gate includes component-group tests |
| Contract/API compatibility | yes | Existing serialized round trips and explicit style calls must continue passing. | Focused gate includes `test_component.py` |
| Property/fuzz | no | The changed domain is finite root/field shape validation. | Not applicable |
| Mutation | yes | Factory guard branches are proof-critical. | Mutation result recorded below |
| Security/adversarial | no | No path, network, subprocess, archive, SQL, template, or active-content surface changed. | Not applicable |
| Performance/resource | no | Adds constant-time mapping and key checks. | Code inspection |
| Concurrency/race | no | No shared state, locks, workers, or temp files changed. | Not applicable |
| Golden artifact/visual | no | No renderer output syntax changed. | Not applicable |
| Regression | yes | Prevents silent malformed payload acceptance and incidental lookup failures. | COMPONENT-FACTORY-PAYLOAD-P2 tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Weakening root mapping checks must fail malformed-root tests.
- Weakening required-field checks must fail missing-field tests.
- Changing explicit-style dispatch must fail compact-payload compatibility tests.
- Breaking valid round trips must fail existing component and group tests.

Current result:

- Focused dependent-path tests:
  `python -m pytest -q tests\test_component_factory_payload_contract.py tests\test_component.py tests\test_component_group_contract.py tests\test_width_height_contract.py tests\test_single_dimension_contract.py`
  returned `99 passed`.
- Cosmic Ray 8.4.6, scoped to COMPONENT-FACTORY-PAYLOAD-P2 helper and factory
  dispatch rows: 16 work items, 16 killed, 0 survivors.
- Ruff lint passed for touched implementation, tests, and mutation filter.
- Ruff format passed for the new test and mutation filter. `src\InkGen\component.py`
  remains a known broad-format exception and was not broad-formatted.
- Full coverage gate:
  `python -m pytest --cov=src/InkGen --cov-branch --cov-report=term -q`
  returned `648 passed` with `93%` coverage.
- MkDocs strict build passed.

## PO-CFACT-001: Factory Roots Fail Explicitly

### Claim

Scoped primitive component factories reject non-mapping roots, missing root
keys, and non-mapping payloads before incidental lookup errors.

### Domain

Public factory calls for `Component`, `DrawingComponent`,
`StandardDrawingComponent`, `SingleDimensionDrawingComponent`,
`WidthHeightDrawingComponent`, and `TextComponent`.

### Proof Method

`_component_payload()` requires a mapping root, the expected class key, and a
mapping payload. Focused condition tests cover each malformed root partition for
every scoped factory.

### Conclusion

Supported by focused tests, mutation testing, full coverage tests, and MkDocs
strict build.

## PO-CFACT-002: Required Factory Fields Fail Explicitly

### Claim

Scoped factories reject missing required payload fields before constructor or
style dispatch.

### Domain

Factory payloads with valid roots but missing required style, geometry, or text
fields.

### Proof Method

`_component_required_field()` checks required fields by owner name before
constructors are called. Focused condition tests cover missing style,
coordinate, dimension, and text fields.

### Conclusion

Supported by focused tests, mutation testing, full coverage tests, and MkDocs
strict build.

## PO-CFACT-003: Explicit Style Compact Payloads Remain Compatible

### Claim

Callers that supply an explicit style can still hydrate compact payloads that
omit serialized style fields.

### Domain

`DrawingComponent`, `StandardDrawingComponent`,
`SingleDimensionDrawingComponent`, `WidthHeightDrawingComponent`, and
`TextComponent` calls with explicit style objects.

### Proof Method

Factories validate the root and required geometry/text fields, then use the
explicit style argument without requiring a serialized style field. The focused
test hydrates every scoped style-bearing factory through that path.

### Conclusion

Supported by focused tests, mutation testing, full coverage tests, and MkDocs
strict build.

## PO-CFACT-004: Existing Round Trips Are Preserved

### Claim

Existing full serialized payload round trips for the scoped factories and their
component-group dependent path remain unchanged.

### Domain

Valid payloads emitted by `parameters` and hydrated through direct factory
calls or `ComponentGroup.create_from_dict()`.

### Proof Method

Existing component and component-group tests exercise full payload round trips,
style cache reuse, and dynamic group dispatch after the helper changes.

### Conclusion

Supported by focused tests, mutation testing, full coverage tests, and MkDocs
strict build.
