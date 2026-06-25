# SVG Document Factory Payload Contract Proof Obligations

This note applies the InkGen Definition of Done to the
`SVG-DOCUMENT-FACTORY-PAYLOAD-P2` slice. It covers SVG document, page, and layer
hydration payload envelopes.

## Scope

The slice covers:

- `DocumentSVG.create_from_dict()`.
- `DocumentSVG._layers_from_svg_dict()`.
- `DocumentSVG._layer_from_svg_dict()`.
- The local SVG required mapping/sequence helpers used by this path.

Out of scope:

- `ComponentGroupSVG.create_from_dict()`, covered by
  `SVG-GROUP-FACTORY-PAYLOAD-P2`.
- Concrete SVG primitive, curve, and path factories, covered by separate SVG
  factory payload slices.
- SVG rendering, include-layer overlays, and file-writing path validation.

## Dependency Review

Affected surface:

- `src/InkGen/svg_generator.py`.
- `tests/test_svg_document_factory_payload_contract.py`.
- `docs/proofs/svg-document-factory-payload-contract.md`.

Incoming dependencies:

- Synthetic fixture workflows rely on `DocumentSVG.parameters` /
  `DocumentSVG.create_from_dict()` round trips.
- SVG rendering depends on hydrated pages and layers preserving document
  structure.
- Nested SVG group hydration depends on `ComponentGroupSVG.create_from_dict()`.
- Legacy serialized SVG documents may contain generic `ComponentGroup` payloads.

Outgoing dependencies:

- SVG document hydration consumes `Canvas`, `Layers`, `Layer`,
  `ComponentGroupSVG`, generic `ComponentGroup`, and style caches.
- No dependency was added.

Public contract:

- Valid `DocumentSVG` payloads hydrate to equivalent documents.
- Malformed document roots, malformed `pages`, malformed page `Layers`
  envelopes, malformed layer envelopes, malformed layer collection fields,
  malformed component-group entries, and malformed group collision setting
  entries fail explicitly before incidental subscription, iteration, or nested
  group hydration errors.
- Nested SVG group payload failures remain delegated to the already-hardened
  SVG group factory boundary.
- Generic group compatibility remains intact.

Serialized/artifact contract:

- `DocumentSVG.parameters` output remains unchanged.
- Valid document hydration preserves generated SVG markup for standard base
  layer documents.
- Page/layer ordering remains the same as serialized data.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced.
- Layer check: SVG-specific hydration remains inside the concrete SVG renderer.
- Coupling check: document/page/layer hydration delegates child groups to the
  SVG or generic group factory rather than duplicating group child validation.
- Redundancy check: local SVG payload helpers now cover primitive, group, and
  document-level SVG hydration envelopes.

ADR/rule impact:

- No ADR is required. The slice preserves the renderer separation rule and adds
  no library.

## Domain Definitions

- A valid SVG document payload is a mapping with a `DocumentSVG` mapping
  payload.
- `canvas` and `pages` are required document fields; `pages` must be a
  non-string sequence.
- Each page payload must be a `Layers` mapping payload with required `canvas`
  and `layers` mapping fields.
- Each layer payload must be a `Layer` mapping payload with required
  `layer_name`, `canvas`, `model`, `component_groups`, and
  `group_collision_settings` fields.
- `component_groups` must be a non-string sequence.
- Every component group entry must be a mapping before SVG-vs-generic group
  dispatch.
- `group_collision_settings` must be a mapping, and setting entries present for
  group labels must be mappings.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Malformed document root | Reject explicitly | PO-SVGDOCFACT-001 | document-root tests | killed |
| Missing document fields | Reject explicitly | PO-SVGDOCFACT-001 | missing-field tests | killed |
| Malformed page collection | Reject explicitly | PO-SVGDOCFACT-001 | pages sequence tests | killed |
| Malformed `Layers` page envelope | Reject explicitly | PO-SVGDOCFACT-002 | page-envelope tests | killed |
| Malformed layer envelope | Reject explicitly | PO-SVGDOCFACT-003 | layer-envelope tests | killed |
| Malformed layer collections/settings | Reject explicitly | PO-SVGDOCFACT-004 | layer collection/settings tests | killed |
| Malformed component group entry | Reject explicitly | PO-SVGDOCFACT-004 | group-entry test | killed |
| Valid SVG document hydration | Preserve compatibility | PO-SVGDOCFACT-005 | valid round-trip and non-default layer tests | killed |
| Generic group hydration | Preserve compatibility | PO-SVGDOCFACT-006 | generic group test | killed |
| Nested group hydration | Delegate to group factory | PO-SVGDOCFACT-007 | nested group failure test | killed |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Payload helpers and hydration functions are deterministic. | Direct factory tests |
| Behavioral/condition | yes | The slice defines `SVG-DOCUMENT-FACTORY-PAYLOAD-P2`. | Condition-marked tests |
| Failure-mode | yes | Old behavior failed through incidental subscription/iteration errors. | Malformed payload tests |
| Integration/live-path | yes | `DocumentSVG.create_from_dict()` crosses document, page, layer, group, component, and style hydration. | Focused SVG tests |
| Contract/API compatibility | yes | Valid serialized documents and generic groups must keep working. | Existing and new round-trip tests |
| Property/fuzz | no | The envelope domain is finite shape validation. | Explicit partitions |
| Mutation | yes | Required-field, mapping, sequence, and live-path rows are proof-critical. | Cosmic Ray gate |
| Security/adversarial | limited yes | Serialized payloads can be untrusted but do not trigger file, network, subprocess, SQL, archive, or active content behavior. | Malformed payload tests |
| Performance/resource | no | Adds constant-time envelope checks and existing linear hydration loops. | Not applicable |
| Golden artifact/visual | limited yes | Valid hydration preserves generated SVG markup for the standard base-layer path. | Markup assertions |
| Regression | yes | Prevents raw `KeyError`/attribute errors from document hydration. | Failure-mode tests |

## Mutation Testing Gate

Current result:

- Tool: Cosmic Ray 8.4.6.
- Environment: WSL Python 3.12 virtualenv.
- Config: `tests/mutation/svg_document_factory_payload_cosmic_ray.toml`.
- Filter: `tests/mutation/filter_svg_document_factory_payload_work_items.py`.
- Test selection: SVG document factory payload, SVG document, SVG group
  factory payload, and SVG generator tests.
- Raw work items: 2480.
- Proof-critical work items after filter: 16.
- Killed mutants: 16.
- Surviving mutants: 0.
- Gate result: pass.

## PO-SVGDOCFACT-001: SVG Document Root And Pages Are Validated

### Claim

`DocumentSVG.create_from_dict()` rejects malformed document roots, missing
`canvas`, missing `pages`, and non-sequence `pages` before page hydration.

### Proof Method

The factory reads the root through `_svg_payload()`, required fields through
`_svg_required_field()`, and pages through `_svg_required_sequence()`. Condition
tests cover malformed root and pages partitions.

### Conclusion

Proven for document roots and page collection partitions.

## PO-SVGDOCFACT-002: SVG Page `Layers` Envelopes Are Validated

### Claim

Page payloads must be `Layers` mapping payloads with required `canvas` and
mapping `layers` fields.

### Proof Method

`DocumentSVG._layers_from_svg_dict()` validates the `Layers` root and required
fields before constructing the `Layers` object or iterating layer payloads.
Tests mutate valid document payloads at each page-envelope partition.

### Conclusion

Proven for page `Layers` envelope partitions.

## PO-SVGDOCFACT-003: SVG Layer Envelopes Are Validated

### Claim

Layer payloads must be `Layer` mapping payloads with required layer metadata and
canvas fields before group hydration.

### Proof Method

`DocumentSVG._layer_from_svg_dict()` validates the `Layer` root and reads
`layer_name`, `canvas`, and `model` through required-field helpers before
constructing `Layer`.

### Conclusion

Proven for layer envelope partitions.

## PO-SVGDOCFACT-004: Layer Component Collections And Collision Settings Are Validated

### Claim

Layer `component_groups` must be a non-string sequence and
`group_collision_settings` must be a mapping whose relevant entries are
mappings before groups are added.

### Proof Method

`DocumentSVG._layer_from_svg_dict()` reads `component_groups` through
`_svg_required_sequence()` and `group_collision_settings` through
`_svg_required_mapping()`. Tests cover malformed collection, malformed group
entry, and setting partitions.

### Conclusion

Proven for layer collection and collision-setting partitions.

## PO-SVGDOCFACT-005: Valid SVG Document Hydration Is Preserved

### Claim

Valid SVG document payloads still hydrate to equivalent documents and preserve
standard base-layer SVG markup.

### Proof Method

Tests hydrate valid one-page documents with style caches and compare serialized
parameters, generated rectangle markup, and layer order. A non-default-layer
case also proves hydration removes the `Layers` constructor's default `base`
layer before adding serialized layers.

### Conclusion

Proven for valid SVG document payloads in the declared domain.

## PO-SVGDOCFACT-006: Generic Group Compatibility Is Preserved

### Claim

SVG document hydration still accepts legacy generic `ComponentGroup` payloads.

### Proof Method

The compatibility test serializes a `DocumentSVG` containing a generic
`ComponentGroup`, hydrates it, and compares parameters and layer order.

### Conclusion

Proven for generic group compatibility.

## PO-SVGDOCFACT-007: Nested Groups Use The SVG Group Factory Contract

### Claim

Malformed nested `ComponentGroupSVG` payloads fail with the
`ComponentGroupSVG` factory boundary while document/page/layer envelopes remain
valid.

### Proof Method

The dependent-path test mutates a nested group `components` field and verifies
`DocumentSVG.create_from_dict()` raises the SVG group factory sequence error.

### Conclusion

Proven for nested SVG group delegation.
