# SVG Curve Factory Payload Contract Proof Obligations

This note applies the InkGen Definition of Done to the
`SVG-CURVE-FACTORY-PAYLOAD-P2` slice. It covers serialized payload-envelope
validation for SVG curve primitive factory hydration without changing the
existing curve geometry or SVG path-rendering contracts.

## Scope

The slice covers:

- `ArcSVG.create_from_dict()`
- `QuadraticBezierSVG.create_from_dict()`
- `CubicBezierSVG.create_from_dict()`

Out of scope:

- SVG document/group hydration.
- SVG non-curve primitive factory payloads.
- Curve finite geometry validation, already owned by shared component
  constructors and existing finite-boundary proof notes.
- SVG path output syntax for valid curves.

## Dependency Review

Affected surface:

- `src/InkGen/svg_generator.py`: SVG curve factory root and required-field
  validation.
- `tests/test_svg_curve_factory_payload_contract.py`: condition tests for this
  slice.
- `docs/proofs/svg-curve-factory-payload-contract.md`: this proof note.

Incoming dependencies:

- Synthetic drawing workflows rely on `parameters/create_from_dict()` round
  trips for SVG curve primitives.
- SVG document and group hydration can consume curve payloads through concrete
  SVG component factories.
- Curve finite-boundary tests rely on malformed geometry failing in shared
  constructors after the factory envelope has been validated.

Outgoing dependencies:

- The factories reuse local SVG payload helpers from `svg_generator.py`.
- Field-value validation remains delegated to `Arc`, `QuadraticBezier`, and
  `CubicBezier` component constructors.
- No dependency or package was added.

Before/after edge changes:

- Before this slice, SVG curve factories used raw nested indexing for class
  payloads and required geometry fields.
- After this slice, malformed roots, missing class keys, non-mapping payloads,
  missing style without explicit style, and missing required geometry fields
  fail explicitly at the SVG curve factory boundary.
- Valid explicit-style compact payloads continue to hydrate.

Cycle/layer/coupling/redundancy result:

- Cycle check: no import cycle is introduced.
- Layer check: the change remains inside the concrete SVG renderer.
- Coupling check: SVG factories still delegate geometry semantics to shared
  component classes.
- Redundancy check: the slice reuses the local SVG payload helpers instead of
  adding a second parser or new dependency.

ADR/rule impact:

- No ADR is required. This reinforces the existing dependency-free renderer
  policy and does not change supported SVG output semantics.

## Domain Definitions

- A serialized SVG curve factory payload is a mapping with exactly the class key
  being hydrated.
- The class payload is a mapping.
- Required curve geometry fields must be present before constructor dispatch.
- `style` is required only when no explicit `DrawingStyle` object is supplied.
- Geometry value validation remains delegated to the shared curve constructors.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Malformed roots | Reject before incidental subscription errors | PO-SVGCF-001 | `test_svg_curve_factories_reject_malformed_payload_roots` | killed |
| Missing style without explicit style | Reject before style hydration lookup errors | PO-SVGCF-002 | `test_svg_curve_factories_require_style_when_not_explicit` | killed |
| Missing required geometry fields | Reject before constructor dispatch | PO-SVGCF-003 | `test_svg_curve_factories_reject_missing_required_fields` | killed |
| Valid explicit-style payloads | Preserve compact payload compatibility | PO-SVGCF-004 | `test_svg_curve_factories_preserve_explicit_style_compact_payloads` | killed |
| Geometry values | Delegate to shared curve constructors | Explicit delegation | Existing finite-boundary tests | previously covered |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Factory envelope checks are deterministic. | SVG curve factory payload tests |
| Behavioral/condition | yes | This slice defines `SVG-CURVE-FACTORY-PAYLOAD-P2`. | Condition-marked tests |
| Failure-mode | yes | Malformed payloads must fail at the factory boundary. | Root, style, and missing-field tests |
| Integration/live-path | limited | Existing SVG generator tests exercise valid generated SVG after hydration. | `tests/test_svg_generator.py` |
| Contract/API compatibility | yes | Existing valid compact payloads must still hydrate. | Compact-payload test |
| Property/fuzz | no | The domain is finite envelope-shape validation. | Explicit partition tests |
| Mutation | yes | Guard branches and required-field dispatch are proof-critical. | Mutation result below |
| Security/adversarial | limited yes | Payloads may be untrusted serialized data but do not trigger file, network, subprocess, archive, SQL, template, or active content behavior. | Malformed payload tests |
| Performance/resource | no | Adds constant-time mapping/key checks. | Code inspection |
| Concurrency/race | no | No shared state, locks, workers, or temp files changed. | Not applicable |
| Golden artifact/visual | limited yes | Valid hydrated curve components preserve SVG output behavior. | Existing SVG generator tests |
| Regression | yes | Prevents raw lookup failures from returning. | Failure-mode tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Weakening root mapping checks must fail malformed-root tests.
- Weakening required-field checks must fail missing-field tests.
- Changing valid explicit-style hydration must fail compact-payload tests.

Current result:

- Tool and version: Cosmic Ray 8.4.6 in WSL.
- Mutated source path: `src/InkGen/svg_generator.py`.
- Reproducible setup:
  `cosmic-ray baseline
  tests/mutation/svg_curve_factory_payload_cosmic_ray.toml`,
  `cosmic-ray init tests/mutation/svg_curve_factory_payload_cosmic_ray.toml
  svg_curve_factory_payload_codex_20260625.sqlite`, then
  `python tests/mutation/filter_svg_curve_factory_payload_work_items.py
  svg_curve_factory_payload_codex_20260625.sqlite --clear-results`.
- Test selection:
  `python -m pytest -x tests/test_svg_curve_factory_payload_contract.py`.
- Raw work items: 2393.
- Proof-critical work items after filtering: 6.
- Mutants killed: 6.
- Mutants survived: 0.
- Gate result: pass.

## PO-SVGCF-001: SVG Curve Factory Roots Are Explicitly Validated

### Claim

For every SVG curve primitive factory in scope, non-mapping roots, missing class
keys, and non-mapping class payloads fail before any primitive field or style is
accessed.

### Proof Method

Each factory calls `_svg_payload(data, class_key)` before reading component
fields. Condition tests cover the three malformed root partitions for every
factory in scope.

### Conclusion

Proven for the SVG curve primitive factories in scope.

## PO-SVGCF-002: Style Is Required Without Explicit Style

### Claim

When callers do not pass a `DrawingStyle`, SVG curve factories require a
serialized `style` field before style hydration.

### Proof Method

Each factory reads `style` through `_svg_required_field()` only when the
explicit style argument is `None`. Condition tests cover the missing-style path
for every factory in scope.

### Conclusion

Proven for the SVG curve primitive factories in scope.

## PO-SVGCF-003: Required Curve Fields Fail At The Factory Boundary

### Claim

Required curve geometry fields are checked before constructor dispatch, so
missing fields fail with explicit `ValueError` messages rather than incidental
`KeyError`.

### Proof Method

Factories read all required fields through `_svg_required_field()`. Condition
tests cover every required geometry field for `ArcSVG`, `QuadraticBezierSVG`,
and `CubicBezierSVG`.

### Conclusion

Proven for the SVG curve primitive factories in scope.

## PO-SVGCF-004: Valid Compact Payloads Remain Compatible

### Claim

Valid explicit-style compact payloads hydrate to the same public geometry as
before this slice.

### Proof Method

The compatibility test hydrates one valid explicit-style payload for each
factory and checks representative public geometry fields.

### Conclusion

Proven for the SVG curve primitive factories in scope.
