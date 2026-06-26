# SVG Component Factory Payload Contract Proof Obligations

This note applies the InkGen Definition of Done to the
`SVG-COMPONENT-FACTORY-PAYLOAD-P2` slice. It covers standalone
`SVGComponent.create_from_dict()` payload envelopes and serialized path entries.

## Scope

The slice covers:

- `SVGComponent.create_from_dict()`.
- Serialized `SVGComponent` root and required field validation.
- Serialized embedded path entry validation.
- Delegation of bbox, position, and scale payloads to the existing finite
  geometry boundary.

Out of scope:

- `flatten_svg()` parsing and normalization, covered by SVG utility tests.
- `SVGComponent` constructor geometry validation, covered by
  `SVG-COMPONENT-FINITE-P2`.
- `ComponentGroupSVG` and `DocumentSVG` hydration, covered by their own factory
  payload slices.

## Dependency Review

Affected surface:

- `src/InkGen/svg_generator.py`.
- `tests/test_svg_component_factory_payload_contract.py`.
- `docs/proofs/svg-component-factory-payload-contract.md`.

Incoming dependencies:

- External SVG embedding and synthetic drawing workflows consume
  `SVGComponent.parameters`, `SVGComponent.create_from_dict()`,
  `SVGComponent.points`, `bbox`, `convex_hull`, and `generate_svg()`.
- Existing SVG utility tests prove `SVGComponent` consumes `flatten_svg()` output
  in the live path.

Outgoing dependencies:

- `SVGComponent` depends on the base component model, local finite geometry
  validation, and `flatten_svg()`.
- No dependency was added.

Public contract:

- Valid `SVGComponent.parameters` payloads hydrate to equivalent components.
- Malformed roots, missing `paths`, missing `bbox`, malformed `paths`, malformed
  path entries, missing path `d`, non-string path `d`, and non-string path style
  fail explicitly before `generate_svg()` can encounter incidental errors.
- Bbox, position, and scale values still flow through the existing finite
  geometry validation boundary.

Serialized/artifact contract:

- `SVGComponent.parameters` output remains unchanged.
- Valid hydrated components preserve scaled points and generated SVG path markup.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced.
- Layer check: the change remains inside the concrete SVG renderer component.
- Coupling check: no PDF, DXF, document-output, or new external dependency was
  added.
- Redundancy check: root/required-field checks reuse the existing SVG helper
  pattern used by other SVG factories.

ADR/rule impact:

- No ADR is required. The slice preserves the SVG-only component boundary and
  adds no library.

## Domain Definitions

- A valid standalone SVG component payload is a mapping with an `SVGComponent`
  mapping payload.
- `paths` and `bbox` are required fields.
- `paths` must be a non-string sequence.
- Every path entry must be a mapping with a string `d` field.
- Path `style`, when present, must be a string or `None`.
- Bbox, position, and scale retain the finite/non-boolean domain defined by
  `SVG-COMPONENT-FINITE-P2`.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Malformed root | Reject explicitly | PO-SVGCOMPFACT-001 | root tests | killed |
| Missing required fields | Reject explicitly | PO-SVGCOMPFACT-001 | missing-field tests | killed |
| Malformed paths collection | Reject explicitly | PO-SVGCOMPFACT-002 | paths sequence test | killed |
| Malformed path entry | Reject explicitly | PO-SVGCOMPFACT-003 | path-entry tests | killed |
| Invalid bbox payloads | Delegate to finite boundary | PO-SVGCOMPFACT-004 | bbox delegation tests | killed |
| Valid serialized component | Preserve compatibility | PO-SVGCOMPFACT-005 | round-trip, defaults, and markup tests | killed |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Payload helper and factory behavior are deterministic. | Direct factory tests |
| Behavioral/condition | yes | The slice defines `SVG-COMPONENT-FACTORY-PAYLOAD-P2`. | Condition-marked tests |
| Failure-mode | yes | Old behavior failed through incidental indexing or render-time path errors. | Malformed payload tests |
| Integration/live-path | yes | Hydrated path entries feed `generate_svg()` and points. | Markup and point assertions |
| Contract/API compatibility | yes | Valid serialized `SVGComponent` payloads must keep round-tripping. | Round-trip test and existing tests |
| Property/fuzz | no | The envelope domain is finite shape validation. | Explicit partitions |
| Mutation | yes | Required-field and path-entry guards are proof-critical. | Cosmic Ray gate |
| Security/adversarial | limited yes | Serialized payloads can be untrusted but do not trigger file, network, subprocess, SQL, archive, or active content behavior in this path. | Malformed payload tests |
| Performance/resource | no | Adds constant-time checks and one linear path-entry loop. | Not applicable |
| Golden artifact/visual | limited yes | Valid hydration preserves generated SVG markup. | Markup assertion |
| Regression | yes | Prevents raw `KeyError`/`TypeError` from serialized SVG component hydration and rendering. | Failure-mode tests |

## Mutation Testing Gate

Current result:

- Tool: Cosmic Ray 8.4.6.
- Environment: WSL Python 3.12 virtualenv.
- Config: `tests/mutation/svg_component_factory_payload_cosmic_ray.toml`.
- Filter: `tests/mutation/filter_svg_component_factory_payload_work_items.py`.
- Test selection: SVG component factory payload, SVG utilities, and SVG
  generator tests.
- Raw work items: 2489.
- Proof-critical work items after filter: 18.
- Killed mutants: 18.
- Surviving mutants: 0.
- Gate result: pass.

## PO-SVGCOMPFACT-001: SVG Component Root And Required Fields Are Validated

### Claim

`SVGComponent.create_from_dict()` rejects malformed roots and missing `paths` or
`bbox` before constructor hydration.

### Proof Method

The factory reads the root through `_svg_payload()` and required fields through
`_svg_required_field()` / `_svg_required_sequence()`. Condition tests cover
non-mapping roots, missing class key, non-mapping payload, missing `paths`,
missing `bbox`, and string `paths`.

### Conclusion

Proven for root and required-field partitions.

## PO-SVGCOMPFACT-002: Path Collections Are Required Sequences

### Claim

Serialized `paths` must be present and must be a non-string sequence before path
entry validation.

### Proof Method

`_svg_component_path_entries()` reads `paths` through `_svg_required_sequence()`.
Tests cover missing and string path collections.

### Conclusion

Proven for serialized path collection partitions.

## PO-SVGCOMPFACT-003: Path Entries Are Typed Mappings

### Claim

Every serialized path entry must be a mapping with a string `d` field and a
string-or-`None` style value.

### Proof Method

`_svg_component_path_entries()` validates each path entry before
`SVGComponent.generate_svg()` can consume it. Tests cover non-mapping path
entries, missing `d`, non-string `d`, and non-string style.

### Conclusion

Proven for path entry partitions.

## PO-SVGCOMPFACT-004: Geometry Fields Use The Existing Finite Boundary

### Claim

Bbox, position, and scale payloads cannot bypass the already-proven finite
geometry validation.

### Proof Method

`SVGComponent.create_from_dict()` passes the required bbox and optional
position/scale fields into `SVGComponent.__init__()`, which is covered by
`SVG-COMPONENT-FINITE-P2`. This slice adds malformed bbox delegation tests.

### Conclusion

Proven for bbox delegation in this slice and inherited for position/scale from
`SVG-COMPONENT-FINITE-P2`.

## PO-SVGCOMPFACT-005: Valid SVG Component Hydration Is Preserved

### Claim

Valid standalone `SVGComponent` payloads still hydrate, round-trip, compute
scaled points, and emit path markup.

### Proof Method

The compatibility test hydrates a valid serialized component, compares
parameters and points, and asserts generated SVG transform and path markup.
Existing SVG utility/generator tests also cover flattened SVG live-path
round-trips.

### Conclusion

Proven for valid standalone SVG component payloads.
