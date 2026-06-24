# Zoning Drawing Payload Contract

This note applies the InkGen Definition of Done to the
`ZONING-DRAWING-PAYLOAD-P2` slice. It covers serialized payload envelope
validation for renderer-neutral zoning recipes.

## Scope

The slice covers:

- `ZoningDrawing.create_from_dict()`
- `_zoning_payload()`
- `_zoning_required_field()`
- `_zoning_required_mapping()`
- `_zoning_style_name()`

Out of scope:

- Positive-real zoning dimension validation, covered by
  `ZONING-DRAWING-FINITE-P2`.
- `Canvas`, `DrawingStyle`, and `TextStyle` field-level validation.
- Zoning geometry generation and renderer materialization math.

## Dependency Review

Affected surface:

- `src/InkGen/drawing_components.py`
- `tests/test_zoning_drawing_payload_contract.py`
- `docs/proofs/zoning-drawing-payload-contract.md`

Incoming dependencies:

- Public callers import `ZoningDrawing` from `InkGen`.
- Synthetic drawing builders use `ZoningDrawing.parameters` and
  `create_from_dict()` to persist neutral zoning recipes.
- SVG, PDF, DXF, and flow-document paths consume the neutral group emitted by
  valid zoning recipes.

Outgoing dependencies:

- Zoning hydration delegates canvas validation to `Canvas.create_from_dict()`.
- Style field validation remains delegated to `DrawingStyle.create_from_dict()`
  and `TextStyle.create_from_dict()`.
- Valid materialization remains delegated to `DrawingComponentGroup.to_group()`.
- No dependency was added.

Public contract:

- Valid serialized zoning payloads still hydrate to equivalent zoning recipes.
- Malformed roots, missing fields, malformed mapping fields, malformed style
  envelopes, non-mapping style registries, and wrong-kind style override values
  fail explicitly before incidental subscription or attribute errors.

Serialized/artifact contract:

- `ZoningDrawing.parameters` output remains unchanged.
- Valid hydrated zoning still materializes to the same SVG group geometry.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced.
- Layer check: neutral zoning still owns recipe construction and delegates
  concrete output to renderer-neutral drawing groups.
- Coupling check: envelope validation is local and does not duplicate style or
  canvas field validation.
- Redundancy check: helper functions are scoped to this public factory boundary.

ADR/rule impact:

- No ADR is required. The slice preserves renderer neutrality and adds no
  library dependency.

## Domain Definitions

- A valid zoning payload is a mapping with a `ZoningDrawing` mapping payload.
- `canvas`, `line_style`, `text_style`, and `parameters` are required fields.
- `line_style`, `text_style`, and `parameters` must be mappings.
- `line_style` must contain a `DrawingStyle` mapping with a string `name`.
- `text_style` must contain a `TextStyle` mapping with a string `name`.
- If a style registry override is supplied, it must be a mapping and each
  matching override must be the style kind required by that field.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Malformed root payload | Reject explicitly | PO-ZD-PAYLOAD-001 | root tests | killed |
| Missing required fields | Reject explicitly | PO-ZD-PAYLOAD-002 | missing-field tests | killed |
| Malformed mapping fields | Reject explicitly | PO-ZD-PAYLOAD-002 | mapping-field tests | killed |
| Malformed style envelopes | Reject explicitly | PO-ZD-PAYLOAD-003 | style-envelope tests | killed |
| Malformed style registry | Reject explicitly | PO-ZD-PAYLOAD-004 | style-registry tests | killed |
| Valid hydration/materialization | Preserve compatibility | PO-ZD-PAYLOAD-005 | round-trip SVG test | killed |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Payload helpers are deterministic. | Direct factory tests |
| Behavioral/condition | yes | The slice defines `ZONING-DRAWING-PAYLOAD-P2`. | Condition-marked tests |
| Failure-mode | yes | Old behavior failed through incidental indexing and attribute errors. | Malformed payload tests |
| Integration/live-path | yes | Valid hydration feeds SVG materialization. | Round-trip SVG test |
| Contract/API compatibility | yes | Valid `parameters/create_from_dict()` must remain stable. | Existing and new round-trip tests |
| Property/fuzz | no | The envelope domain is finite shape validation. | Explicit partitions |
| Mutation | yes | Factory, required-field, mapping, and style-name rows are proof-critical. | Cosmic Ray gate |
| Security/adversarial | limited | Serialized payloads may be untrusted but do not touch filesystem, network, subprocesses, SQL, or active content. | Malformed payload tests |
| Performance/resource | no | Adds constant-time envelope checks before existing zoning construction. | Not applicable |
| Golden artifact/visual | yes | Valid SVG geometry must remain stable. | SVG component parameter comparison |
| Regression | yes | Prevents raw `KeyError`, subscription, and `.get` attribute failures. | Failure-mode tests |

## Mutation Testing Gate

Current result: passed.

- Cosmic Ray 8.4.6, scoped to zoning payload factory/helper rows.
- Work items after filter: `23`.
- Result: `23 killed`, `0 survived`.

## PO-ZD-PAYLOAD-001: Zoning Roots Are Validated

### Claim

`ZoningDrawing.create_from_dict()` rejects non-mapping roots, missing
`ZoningDrawing` roots, and non-mapping root payloads before reading nested
fields.

### Proof Method

The factory routes input through `_zoning_payload()`. Condition tests cover the
malformed root partitions.

### Conclusion

Proven by condition tests and scoped mutation testing.

## PO-ZD-PAYLOAD-002: Required Mapping Fields Are Validated

### Claim

`canvas`, `line_style`, `text_style`, and `parameters` are required, and mapping
fields are validated before style lookup or constructor delegation.

### Proof Method

The factory reads required fields through `_zoning_required_field()` and mapping
fields through `_zoning_required_mapping()`. Tests cover missing fields and a
malformed `parameters` mapping.

### Conclusion

Proven by condition tests and scoped mutation testing.

## PO-ZD-PAYLOAD-003: Style Envelopes Are Validated

### Claim

Serialized line and text style envelopes must contain the expected style type
mapping and a string style name before registry lookup.

### Proof Method

`_zoning_style_name()` validates expected style keys, nested mapping entries,
and string names. Tests cover malformed line and text style envelopes.

### Conclusion

Proven by condition tests and scoped mutation testing.

## PO-ZD-PAYLOAD-004: Style Registry Overrides Match Required Kinds

### Claim

Supplied style registries must be mappings, and matching overrides must be
`DrawingStyle` for `line_style` and `TextStyle` for `text_style`.

### Proof Method

`create_from_dict()` validates the `styles` argument before `.get()` and checks
override values before construction. Tests cover a non-mapping registry and
wrong-kind overrides for both style roles.

### Conclusion

Proven by condition tests and scoped mutation testing.

## PO-ZD-PAYLOAD-005: Valid Zoning Hydration Is Preserved

### Claim

Valid zoning payloads hydrate to equivalent recipes and preserve SVG
materialization geometry.

### Proof Method

The valid-path test compares serialized parameters and SVG component parameters
between the source and hydrated zoning recipes.

### Conclusion

Proven by condition tests and scoped mutation testing.
