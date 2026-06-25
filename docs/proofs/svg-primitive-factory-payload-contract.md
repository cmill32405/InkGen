# SVG Primitive Factory Payload Contract Proof Obligations

This note applies the InkGen Definition of Done to the
`SVG-PRIMITIVE-FACTORY-PAYLOAD-P2` slice. It covers serialized
payload-envelope validation for non-curve SVG primitive factory hydration.

## Scope

The slice covers:

- `RectangleSVG.create_from_dict()`
- `LineSVG.create_from_dict()`
- `RegularPolygonSVG.create_from_dict()`
- `PolygonalSVG.create_from_dict()`
- `CircleSVG.create_from_dict()`
- `TextSVG.create_from_dict()`

Out of scope:

- SVG curve primitive factories, covered by
  `SVG-CURVE-FACTORY-PAYLOAD-P2`.
- `PathSVG.create_from_dict()`, covered by
  `SVG-PATH-COMMAND-PAYLOAD-P2`.
- SVG group/document dynamic dispatch.
- Geometry/text value validation, delegated to shared component constructors.

## Dependency Review

Affected surface:

- `src/InkGen/svg_generator.py`: primitive factory root and required-field
  validation.
- `tests/test_svg_primitive_factory_payload_contract.py`: condition tests.
- `docs/proofs/svg-primitive-factory-payload-contract.md`: this proof note.

Incoming dependencies:

- SVG document/group hydration can consume these concrete primitive payloads.
- Synthetic drawing workflows rely on `parameters/create_from_dict()` round
  trips for SVG primitives.
- Existing geometry proof notes rely on constructors owning field-value
  validation after factory envelope checks.

Outgoing dependencies:

- Factories reuse local SVG payload helpers from `svg_generator.py`.
- Drawing factories consume `DrawingStyle.create_from_dict()` when no explicit
  style object is supplied.
- `TextSVG` consumes `TextStyle.create_from_dict()` when no explicit text style
  object is supplied.
- No dependency or package was added.

Before/after edge changes:

- Before this slice, non-curve SVG primitive factories used raw nested indexing
  for payloads and required fields.
- After this slice, malformed roots, missing class keys, non-mapping payloads,
  missing style without explicit style, and missing required primitive fields
  fail explicitly at the SVG primitive factory boundary.
- Valid explicit-style compact payloads continue to hydrate.

Cycle/layer/coupling/redundancy result:

- Cycle check: no import cycle is introduced.
- Layer check: changes remain inside the concrete SVG renderer.
- Coupling check: geometry and text semantics remain delegated to shared
  component/style classes.
- Redundancy check: the slice reuses existing SVG payload helpers.

ADR/rule impact:

- No ADR is required. This preserves existing SVG output semantics and adds no
  dependency.

## Domain Definitions

- A serialized SVG primitive factory payload is a mapping with the class key
  being hydrated.
- The class payload is a mapping.
- Required primitive fields must be present before constructor dispatch.
- `style` is required only when no explicit style object is supplied.
- Field-value validation remains delegated to the shared constructors.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Malformed roots | Reject before incidental subscription errors | PO-SVGPF-001 | `test_svg_primitive_factories_reject_malformed_payload_roots` | killed |
| Missing style without explicit style | Reject before style hydration lookup errors | PO-SVGPF-002 | `test_svg_primitive_factories_require_style_when_not_explicit` | killed |
| Missing required primitive fields | Reject before constructor dispatch | PO-SVGPF-003 | `test_svg_primitive_factories_reject_missing_required_fields` | killed |
| Valid explicit-style payloads | Preserve compact payload compatibility | PO-SVGPF-004 | `test_svg_primitive_factories_preserve_explicit_style_compact_payloads` | killed |
| Field values | Delegate to shared constructors | Explicit delegation | Existing geometry/text tests | previously covered |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Factory envelope checks are deterministic. | SVG primitive factory tests |
| Behavioral/condition | yes | This slice defines `SVG-PRIMITIVE-FACTORY-PAYLOAD-P2`. | Condition-marked tests |
| Failure-mode | yes | Malformed payloads must fail at the factory boundary. | Root, style, and missing-field tests |
| Integration/live-path | limited | Existing SVG generator tests exercise valid SVG generation after hydration. | `tests/test_svg_generator.py` |
| Contract/API compatibility | yes | Valid explicit-style compact payloads remain accepted. | Compact-payload test |
| Property/fuzz | no | The domain is finite envelope-shape validation. | Explicit partition tests |
| Mutation | yes | Guard branches and required-field dispatch are proof-critical. | Mutation result below |
| Security/adversarial | limited yes | Payloads may be untrusted serialized data but do not trigger file, network, subprocess, archive, SQL, template, or active content behavior. | Malformed payload tests |
| Performance/resource | no | Adds constant-time mapping/key checks. | Code inspection |
| Concurrency/race | no | No shared state, locks, workers, or temp files changed. | Not applicable |
| Golden artifact/visual | limited yes | Valid hydrated primitives preserve SVG output behavior. | Existing SVG generator tests |
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
  tests/mutation/svg_primitive_factory_payload_cosmic_ray.toml`,
  `cosmic-ray init
  tests/mutation/svg_primitive_factory_payload_cosmic_ray.toml
  svg_primitive_factory_payload_codex_20260625.sqlite`, then
  `python tests/mutation/filter_svg_primitive_factory_payload_work_items.py
  svg_primitive_factory_payload_codex_20260625.sqlite --clear-results`.
- Test selection:
  `python -m pytest -x
  tests/test_svg_primitive_factory_payload_contract.py`.
- Raw work items: 2459.
- Proof-critical work items after filtering: 6.
- Mutants killed: 6.
- Mutants survived: 0.
- Gate result: pass.

## PO-SVGPF-001: SVG Primitive Factory Roots Are Explicitly Validated

### Claim

For every SVG primitive factory in scope, non-mapping roots, missing class keys,
and non-mapping class payloads fail before any primitive field or style is
accessed.

### Proof Method

Each factory calls `_svg_payload(data, class_key)` before reading component
fields. Condition tests cover the three malformed root partitions for every
factory in scope.

### Conclusion

Proven for the SVG primitive factories in scope.

## PO-SVGPF-002: Style Is Required Without Explicit Style

### Claim

When callers do not pass an explicit style, SVG primitive factories require a
serialized `style` field before style hydration.

### Proof Method

Each factory reads `style` through `_svg_required_field()` only when the
explicit style argument is `None`. Condition tests cover the missing-style path
for every factory in scope.

### Conclusion

Proven for the SVG primitive factories in scope.

## PO-SVGPF-003: Required Primitive Fields Fail At The Factory Boundary

### Claim

Required primitive fields are checked before constructor dispatch, so missing
fields fail with explicit `ValueError` messages rather than incidental
`KeyError`.

### Proof Method

Factories read required fields through `_svg_required_field()`. Condition tests
cover representative required fields for every factory in scope.

### Conclusion

Proven for the SVG primitive factories in scope.

## PO-SVGPF-004: Valid Compact Payloads Remain Compatible

### Claim

Valid explicit-style compact payloads hydrate to the same public state as before
this slice.

### Proof Method

The compatibility test hydrates one valid explicit-style payload for every
factory in scope and checks representative public fields.

### Conclusion

Proven for the SVG primitive factories in scope.
