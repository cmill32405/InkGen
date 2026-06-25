# SVG Group Factory Payload Contract Proof Obligations

This note applies the InkGen Definition of Done to the
`SVG-GROUP-FACTORY-PAYLOAD-P2` slice. It covers
`ComponentGroupSVG.create_from_dict()` payload envelopes and closed child
component/style dispatch.

## Scope

The slice covers:

- `ComponentGroupSVG.create_from_dict()`.
- SVG child component envelope validation.
- SVG child style envelope validation.
- Closed SVG component type dispatch for serialized group children.

Out of scope:

- `DocumentSVG.create_from_dict()` root/page/layer envelope validation.
- Concrete SVG primitive, curve, and path factory field validation, covered by
  separate SVG factory payload slices.
- Standalone `SVGComponent.create_from_dict()` payload hardening.
- `TableSVG` construction from `Table`, because current group serialization
  emits the built child primitives rather than a `TableSVG` child envelope.

## Dependency Review

Affected surface:

- `src/InkGen/svg_generator.py`.
- `tests/test_svg_group_factory_payload_contract.py`.
- `docs/proofs/svg-group-factory-payload-contract.md`.

Incoming dependencies:

- `DocumentSVG.create_from_dict()` hydrates nested SVG groups through
  `ComponentGroupSVG.create_from_dict()`.
- Synthetic SVG fixture workflows rely on SVG group
  `parameters/create_from_dict()` round trips.
- SVG label and segmentation generation rely on hydrated groups preserving
  component geometry.

Outgoing dependencies:

- SVG group hydration consumes concrete SVG primitive, curve, path, `DrawingStyle`,
  and `TextStyle` factories.
- No dependency was added.

Public contract:

- Valid `ComponentGroupSVG` payloads hydrate to equivalent groups.
- Malformed roots, missing `group_label`, missing or malformed `components`,
  malformed child entries, malformed style envelopes, and unsupported child or
  style types fail explicitly before dynamic dispatch.
- Child payloads still flow through the concrete child factory contract.

Serialized/artifact contract:

- `ComponentGroupSVG.parameters` output remains unchanged.
- Valid group hydration preserves label and segmentation-mask behavior.
- `DocumentSVG.create_from_dict()` remains compatible with valid nested SVG
  groups.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced.
- Layer check: the change remains inside the concrete SVG renderer.
- Coupling check: dynamic dispatch is narrowed to the existing concrete SVG
  child component set.
- Redundancy check: local SVG payload helpers now cover primitive, curve, path,
  and group factory boundaries.

ADR/rule impact:

- No ADR is required. The slice preserves the renderer separation rule and adds
  no library.

## Domain Definitions

- A valid SVG group payload is a mapping with a `ComponentGroupSVG` mapping
  payload.
- `group_label` is required and remains validated by the base `ComponentGroup`
  constructor.
- `components` is a required non-string sequence.
- Every child component entry is a single-key mapping with a string SVG
  component type and mapping payload.
- Supported serialized child component types are exactly
  `SVG_RENDER_COMPONENT_TYPES`.
- Child style envelopes, when present, are single-key mappings for
  `DrawingStyle` or `TextStyle` with a string `name`.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Malformed group root | Reject explicitly | PO-SVGGROUP-001 | malformed-root tests | killed |
| Missing required group fields | Reject explicitly | PO-SVGGROUP-001 | missing-field tests | killed |
| Malformed component collection | Reject explicitly | PO-SVGGROUP-002 | component collection tests | killed |
| Malformed child entry | Reject explicitly | PO-SVGGROUP-003 | child-entry tests | killed |
| Unsupported child type | Reject explicitly | PO-SVGGROUP-004 | unsupported-type tests | killed |
| Malformed style envelope | Reject explicitly | PO-SVGGROUP-005 | style-envelope tests | killed |
| Valid SVG group hydration | Preserve compatibility | PO-SVGGROUP-006 | round-trip/cache test | killed |
| Document nested group hydration | Contract remains live | PO-SVGGROUP-007 | document-path test | killed |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Payload helpers and dispatch checks are deterministic. | Direct group factory tests |
| Behavioral/condition | yes | The slice defines `SVG-GROUP-FACTORY-PAYLOAD-P2`. | Condition-marked tests |
| Failure-mode | yes | Old behavior failed through incidental lookup, subscription, or dynamic dispatch errors. | Malformed payload tests |
| Integration/live-path | yes | `DocumentSVG.create_from_dict()` consumes nested SVG groups. | Document hydration test |
| Contract/API compatibility | yes | Existing valid group/document round trips must remain. | Existing and new round-trip tests |
| Property/fuzz | no | The envelope domain is finite shape validation. | Explicit partitions |
| Mutation | yes | Validation guards and closed dispatch are proof-critical. | Cosmic Ray gate |
| Security/adversarial | limited yes | Serialized payloads can be untrusted but do not trigger file, network, subprocess, SQL, archive, or active content behavior. | Malformed payload tests |
| Performance/resource | no | Adds constant-time envelope checks and one linear component loop. | Not applicable |
| Concurrency/race | no | Uses caller-provided style cache as before; no new shared concurrency primitive is added. | Not applicable |
| Golden artifact/visual | limited yes | Valid group hydration preserves generated geometry labels and masks. | label/mask equality assertions |
| Regression | yes | Prevents arbitrary module dispatch from group payloads. | Unsupported-type tests |

## Mutation Testing Gate

Current result:

- Tool: Cosmic Ray 8.4.6.
- Environment: WSL Python 3.12 virtualenv.
- Config: `tests/mutation/svg_group_factory_payload_cosmic_ray.toml`.
- Filter: `tests/mutation/filter_svg_group_factory_payload_work_items.py`.
- Test selection: SVG group factory payload, SVG generator, and SVG document
  tests.
- Raw work items: 2474.
- Proof-critical work items after filter: 26.
- Killed mutants: 26.
- Surviving mutants: 0.
- Gate result: pass.

## PO-SVGGROUP-001: SVG Group Roots And Required Fields Are Validated

### Claim

`ComponentGroupSVG.create_from_dict()` rejects malformed group roots and missing
required group fields before child component hydration.

### Proof Method

The factory reads the root through `_svg_payload()` and required fields through
`_svg_required_field()` / `_svg_required_sequence()`. Condition tests cover
non-mapping roots, missing class key, non-mapping payload, missing `group_label`,
missing `components`, and string `components`.

### Conclusion

Proven for group roots and required group fields in the declared domain.

## PO-SVGGROUP-002: Component Collections Are Required Sequences

### Claim

`components` must be present and must be a non-string sequence before
enumeration.

### Proof Method

The factory iterates `_svg_required_sequence(payload, "components",
"ComponentGroupSVG")`. Tests cover missing and string component collections.

### Conclusion

Proven for required SVG group component collections.

## PO-SVGGROUP-003: Child Component Entries Are Typed Mapping Envelopes

### Claim

Each child component entry must be a single-key mapping whose key is a string
type name and whose value is a mapping payload.

### Proof Method

The factory validates each child entry through `_svg_single_mapping_entry()`.
Tests cover non-mapping entries, zero-key/multi-key entries, non-string type
keys, and non-mapping child payloads.

### Conclusion

Proven for child component entry envelope partitions in scope.

## PO-SVGGROUP-004: SVG Group Hydration Uses Closed Component Dispatch

### Claim

SVG group hydration only dispatches to classes in `SVG_RENDER_COMPONENT_TYPES`.

### Proof Method

`_svg_component_class()` resolves a type name and rejects missing or out-of-set
types before calling `create_from_dict()`. Tests cover a missing type name and a
real in-module class that is not a supported SVG child payload.

### Conclusion

Proven for closed SVG component dispatch in group hydration.

## PO-SVGGROUP-005: Child Style Envelopes Are Validated Before Style Hydration

### Claim

Child style envelopes must be single-key mappings for `DrawingStyle` or
`TextStyle` with a string `name`.

### Proof Method

`_svg_style_entry()` validates the style envelope before style cache lookup or
style factory hydration. Tests cover malformed mappings, malformed type keys,
non-mapping style payloads, missing/non-string names, and unsupported style
types.

### Conclusion

Proven for child style envelope partitions in scope.

## PO-SVGGROUP-006: Valid SVG Group Hydration Is Preserved

### Claim

Valid SVG group payloads still hydrate, preserve serialized parameters, and
reuse caller-provided style caches.

### Proof Method

The compatibility test builds a valid `ComponentGroupSVG` with drawing and text
children, serializes it, hydrates it twice through the same style cache, and
asserts parameter equality, label/mask generation, and style object reuse.

### Conclusion

Proven for valid SVG group payloads in the declared domain.

## PO-SVGGROUP-007: SVG Document Hydration Uses The Group Contract

### Claim

`DocumentSVG.create_from_dict()` routes nested `ComponentGroupSVG` payloads
through the hardened group factory.

### Proof Method

The document-path test serializes a `DocumentSVG` containing a nested SVG group,
hydrates it successfully, then corrupts the nested group `components` field and
asserts that document hydration raises the group factory's explicit sequence
error.

### Conclusion

Proven for nested SVG group hydration in the declared document path.
