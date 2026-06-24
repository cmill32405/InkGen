# Style Factory Payload Contract Proof Obligations

This note applies the InkGen Definition of Done to the
STYLE-FACTORY-PAYLOAD-P2 slice. It covers serialized payload-envelope
validation for style factory hydration without changing the existing drawing
style, font, or text style value domains.

## Scope

The slice covers:

- `Style.create_from_dict()`
- `DrawingStyle.create_from_dict()`
- `Font.create_from_dict()`
- `TextStyle.create_from_dict()`
- `_style_payload()`
- `_style_required_field()`

Value validation for colors, font size, font paths, text alignment, and line
spacing remains covered by the existing P1 style proofs.

## Architecture Impact

Affected surface:

- `src/InkGen/style.py`: style factory root and required-field validation.
- `tests/test_style_factory_payload_contract.py`:
  STYLE-FACTORY-PAYLOAD-P2 behavioral tests.
- Existing drawing-style, font, text-style, component, and component-factory
  tests provide compatibility and dependent-path evidence.

Incoming dependencies:

- Component factories hydrate `DrawingStyle` and `TextStyle` payloads.
- Component-group, document-model, SVG, PDF, DXF, and flow-document hydration
  paths depend on style factory behavior.
- Existing style proof notes depend on valid serialized hydration remaining
  compatible.

Outgoing dependencies:

- `DrawingStyle.create_from_dict()` delegates value validation to
  `DrawingStyle.__init__()`.
- `Font.create_from_dict()` delegates value validation and font discovery to
  `Font.__init__()`.
- `TextStyle.create_from_dict()` delegates nested font hydration to
  `Font.create_from_dict()` and then setter validation to `TextStyle`.
- No dependency or package was added.

Before/after edge changes:

- Before this slice, malformed style factory roots failed through incidental
  subscription errors or missing-key lookups.
- After this slice, style factories validate the serialized root and required
  fields before constructor or setter dispatch.
- Valid serialized payloads continue to hydrate through existing public
  constructors and setters.

Cycle/layer/coupling/redundancy result:

- Cycle check: no import cycle is introduced.
- Layer check: style serialization remains in the core style model.
- Coupling check: no renderer-specific behavior is added to `style.py`.
- Redundancy check: one shared payload helper handles repeated root checks.

ADR/rule impact:

- No new ADR is required. This reinforces the dependency-map rule that core
  primitives own style input contracts before values reach components or
  renderers.

## Domain Definitions

- Serialized style factory data must be a mapping with a top-level key equal to
  the class name.
- The top-level class payload must be a mapping.
- Required fields must be present before constructor or setter dispatch.
- Nested `TextStyle.font` must be present before delegating to
  `Font.create_from_dict()`.
- Existing field-value validation remains delegated to the existing public
  constructors and setters.

## Fix Log

- Added `_style_payload()` to validate style factory root mappings.
- Added `_style_required_field()` to validate required payload fields.
- Routed `Style`, `DrawingStyle`, `Font`, and `TextStyle` factory paths through
  the shared helpers.
- Added dependent component-hydration tests proving style payload failures are
  still visible through live component factory paths.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Malformed factory roots | Reject before incidental subscription errors | PO-SFACT-001 | `test_style_factories_reject_malformed_payload_roots` | killed |
| Missing required fields | Reject before constructor/setter dispatch | PO-SFACT-002 | `test_style_factories_reject_missing_required_fields` | killed |
| Valid payloads | Preserve existing style/font/text-style hydration | PO-SFACT-003 | `test_style_factories_preserve_valid_hydration` | killed |
| Dependent component paths | Preserve component style hydration and failure propagation | PO-SFACT-004 | `test_style_factory_payload_contract_remains_live_in_component_hydration` | killed |
| Field-value validation | Delegated to existing P1 contracts | Explicit delegation | Existing style/font/text-style tests | previously covered |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Factory root and required-field validation is deterministic. | STYLE-FACTORY-PAYLOAD-P2 tests |
| Behavioral/condition | yes | This slice defines a public factory payload contract. | Tests are marked `@pytest.mark.condition("STYLE-FACTORY-PAYLOAD-P2")`. |
| Failure-mode | yes | Malformed payloads must fail at the factory boundary. | Malformed root and missing-field tests |
| Integration/live-path | yes | Component factories consume style payloads. | Dependent component hydration test |
| Contract/API compatibility | yes | Existing serialized style/font/text-style payloads must continue hydrating. | Existing style tests and focused gate |
| Property/fuzz | no | The changed domain is finite root/field shape validation. | Not applicable |
| Mutation | yes | Factory guard branches are proof-critical. | Mutation result recorded below |
| Security/adversarial | yes | `Font` custom paths are file-system inputs, but this slice only validates envelope shape before the existing path contract. | Existing FONT-P1 path tests remain in the focused gate |
| Performance/resource | no | Adds constant-time mapping and key checks. | Code inspection |
| Concurrency/race | no | No shared state beyond pre-existing style-name registration changed. | Not applicable |
| Golden artifact/visual | no | No renderer output syntax changed. | Not applicable |
| Regression | yes | Prevents incidental lookup failures in serialized style hydration. | STYLE-FACTORY-PAYLOAD-P2 tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Weakening root mapping checks must fail malformed-root tests.
- Weakening required-field checks must fail missing-field tests.
- Changing valid hydration dispatch must fail style/font/text-style round-trip
  tests.
- Breaking component style hydration must fail dependent component tests.

Current result:

- Focused dependent-path tests:
  `python -m pytest -q tests\test_style_factory_payload_contract.py tests\test_style.py tests\test_drawing_style_contract.py tests\test_font_contract.py tests\test_text_style_contract.py tests\test_component_factory_payload_contract.py tests\test_component.py`
  returned `112 passed`.
- Cosmic Ray 8.4.6, scoped to STYLE-FACTORY-PAYLOAD-P2 helper and factory
  rows: 6 work items, 6 killed, 0 survivors.
- Full coverage gate:
  `python -m pytest --cov=src/InkGen --cov-branch --cov-report=term -q`
  returned `683 passed` with `94%` coverage.
- Ruff lint passed for touched implementation, tests, and mutation filter.
- Ruff format passed for the new test and mutation filter.
  `src\InkGen\style.py` remains a legacy broad-format exception for this
  narrow slice and was not broad-formatted.
- MkDocs strict build passed.
- `git diff --check` passed.

## PO-SFACT-001: Factory Roots Fail Explicitly

### Claim

Scoped style factories reject non-mapping roots, missing root keys, and
non-mapping payloads before incidental lookup errors.

### Domain

Public factory calls for `Style`, `DrawingStyle`, `Font`, and `TextStyle`.

### Proof Method

`_style_payload()` requires a mapping root, the expected class key, and a
mapping payload. Focused condition tests cover each malformed root partition for
every scoped factory.

### Conclusion

Supported by focused tests, mutation testing, full coverage tests, and MkDocs
strict build.

## PO-SFACT-002: Required Factory Fields Fail Explicitly

### Claim

Scoped style factories reject missing required payload fields before constructor
or setter dispatch.

### Domain

Factory payloads with valid roots but missing required style, font, or
text-style fields.

### Proof Method

`_style_required_field()` checks required fields by owner name before values are
passed to constructors or setters. Focused condition tests cover representative
required-field omissions across every scoped factory.

### Conclusion

Supported by focused tests, mutation testing, full coverage tests, and MkDocs
strict build.

## PO-SFACT-003: Valid Hydration Is Preserved

### Claim

Valid serialized style, drawing style, font, and text style payloads still
hydrate through existing public constructors and setters.

### Domain

Serialized payloads matching the public `parameters` shape for the scoped style
classes.

### Proof Method

Factory methods validate envelope shape and then pass payload values to the
same constructors and setters used before this slice. Focused tests and
existing style proof tests exercise valid hydration.

### Conclusion

Supported by focused tests, mutation testing, full coverage tests, and MkDocs
strict build.

## PO-SFACT-004: Component Hydration Still Consumes Style Payloads

### Claim

Component factory hydration continues to consume valid style payloads and
surfaces malformed nested style payloads at the style factory boundary.

### Domain

`DrawingComponent.create_from_dict()` and `TextComponent.create_from_dict()`
using serialized `DrawingStyle` and `TextStyle` payloads.

### Proof Method

The dependent-path test hydrates valid drawing and text components, then checks
that malformed nested style payloads fail with style factory error messages.

### Conclusion

Supported by focused tests, mutation testing, full coverage tests, and MkDocs
strict build.
