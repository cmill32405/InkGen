# PDF Component Factory Payload Contract Proof Obligations

This note applies the InkGen Definition of Done to the
`PDF-COMPONENT-FACTORY-PAYLOAD-P2` slice. It covers concrete PDF primitive
`create_from_dict()` payload envelopes.

## Scope

The slice covers:

- `RectanglePDF.create_from_dict()`
- `LinePDF.create_from_dict()`
- `ArcPDF.create_from_dict()`
- `QuadraticBezierPDF.create_from_dict()`
- `CubicBezierPDF.create_from_dict()`
- `PathPDF.create_from_dict()`
- `RegularPolygonPDF.create_from_dict()`
- `PolygonalPDF.create_from_dict()`
- `CirclePDF.create_from_dict()`
- `TextPDF.create_from_dict()`

Out of scope:

- `ComponentGroupPDF.create_from_dict()` envelope hardening.
- `DocumentPDF.create_from_dict()` envelope hardening.
- Geometry value validation already owned by component constructors.
- PDF operator rendering math.

## Dependency Review

Affected surface:

- `src/InkGen/pdf_generator.py`
- `tests/test_pdf_component_factory_payload_contract.py`
- `docs/proofs/pdf-component-factory-payload-contract.md`

Incoming dependencies:

- `ComponentGroupPDF.create_from_dict()` hydrates child component payloads
  through these factories.
- `DocumentPDF.create_from_dict()` hydrates page groups that may contain these
  component payloads.
- Synthetic drawing workflows rely on `parameters/create_from_dict()` round
  trips for reproducible PDF fixtures.

Outgoing dependencies:

- PDF component factories consume `DrawingStyle.create_from_dict()` and
  `TextStyle.create_from_dict()` when no explicit style object is supplied.
- PDF component factories delegate geometry validation to shared component
  constructors.
- No dependency was added.

Public contract:

- Valid serialized PDF primitive payloads hydrate to equivalent components.
- Compact geometry payloads remain valid when an explicit style object is
  supplied.
- Malformed roots, missing class keys, non-mapping payloads, missing required
  fields, malformed `PathPDF` command envelopes, and non-string `PathPDF`
  command types fail explicitly at the PDF factory boundary.

Serialized/artifact contract:

- `parameters` output remains unchanged.
- Existing valid serialized payloads remain compatible.
- Generated PDF operators are unchanged for valid hydrated components.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced.
- Layer check: the change remains inside the concrete PDF renderer.
- Coupling check: the renderer does not import private component helpers.
- Redundancy check: local `_pdf_payload()` and `_pdf_required_field()` helpers
  centralize the PDF factory envelope rule for this module.

ADR/rule impact:

- No ADR is required. The slice preserves the dependency-free PDF renderer
  policy and adds no library.

## Domain Definitions

- A PDF primitive factory receives a serialized mapping with exactly the class
  key for the primitive being hydrated.
- The class payload is a mapping.
- Required geometry/text fields must be present before constructor delegation.
- `style` is required only when no explicit style object is supplied.
- `PathPDF.commands` is optional; when present it must be a non-string
  sequence of command mappings with a `type` field.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Non-mapping root | Reject explicitly | PO-PDFCPF-001 | malformed-root tests | killed |
| Missing class key | Reject explicitly | PO-PDFCPF-001 | malformed-root tests | killed |
| Non-mapping class payload | Reject explicitly | PO-PDFCPF-001 | malformed-root tests | killed |
| Missing required fields | Reject explicitly | PO-PDFCPF-002 | missing-field tests | killed |
| Missing style without explicit style | Reject explicitly | PO-PDFCPF-003 | style-required tests | killed |
| Explicit-style compact payload | Preserve compatibility | PO-PDFCPF-004 | compact-payload test | killed |
| Path command envelope | Reject malformed commands explicitly | PO-PDFCPF-005 | path-command tests | killed |
| Path command type | Reject non-string command types before `PathCommand` construction | PO-PDFCPF-007 | path-command tests | mutation target |
| Component group dependent path | Child PDF factory contract remains live | PO-PDFCPF-006 | group-hydration test | killed |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Payload helpers and factories are deterministic. | Direct factory tests |
| Behavioral/condition | yes | The slice defines `PDF-COMPONENT-FACTORY-PAYLOAD-P2`. | Condition-marked tests |
| Failure-mode | yes | The old behavior failed through incidental subscription/key errors. | Malformed-root and missing-field tests |
| Integration/live-path | yes | `ComponentGroupPDF` consumes child factory payloads. | Group hydration test |
| Contract/API compatibility | yes | Serialized payload round trips must remain valid. | Existing PDF round-trip tests and compact-payload tests |
| Property/fuzz | no | The domain is finite envelope shape validation. | Explicit partition table |
| Mutation | yes | Validation guards and required-field dispatch are proof-critical. | Cosmic Ray gate |
| Security/adversarial | limited yes | Payloads can be untrusted serialized data but do not trigger file, network, subprocess, SQL, archive, or active content behavior. | Malformed payload tests |
| Performance/resource | no | Constant-time mapping checks and linear path-command hydration only. | Not applicable |
| Golden artifact/visual | limited yes | Valid hydrated components preserve PDF operators. | Existing PDF generator tests |
| Regression | yes | Prevents raw subscription errors from returning. | Failure-mode tests |

## Mutation Testing Gate

Current result:

- Tool: Cosmic Ray 8.4.6.
- Environment: WSL Python 3.12 virtualenv.
- Config: `tests/mutation/pdf_component_factory_payload_cosmic_ray.toml`.
- Filter: `tests/mutation/filter_pdf_component_factory_payload_work_items.py`.
- Test selection: PDF component factory payload, PDF generator, PDF document,
  component factory payload, and style factory payload tests.
- Raw work items: 1998.
- Proof-critical work items after filter: 38.
- Killed mutants: 38.
- Surviving mutants: 0.
- Gate result: pass.

Extension result for `PDF-PATH-COMMAND-TYPE-P2`:

- Config: `tests/mutation/pdf_path_command_type_cosmic_ray.toml`.
- Filter: `tests/mutation/filter_pdf_path_command_type_work_items.py`.
- Raw work items: 2019.
- Proof-critical work items after filter: 5.
- Killed mutants: 5.
- Surviving mutants: 0.
- Gate result: pass.

## PO-PDFCPF-001: PDF Factory Roots Are Explicitly Validated

### Claim

For every concrete PDF primitive factory in scope, non-mapping roots, missing
class keys, and non-mapping class payloads fail before any primitive field or
style hydration is accessed.

### Proof Method

All factories call `_pdf_payload(data, class_key)` before reading component
fields. Condition tests cover the three malformed root partitions for every
factory in scope. Mutation testing targets the helper checks.

### Conclusion

Proven for the concrete PDF primitive factories in scope.

## PO-PDFCPF-002: Required Primitive Fields Fail At The Factory Boundary

### Claim

For every required geometry/text field read by a concrete PDF primitive factory,
absence of the field raises `ValueError` naming the owning PDF payload and field
before incidental `KeyError` or constructor errors.

### Proof Method

Factories read required fields through `_pdf_required_field()`. Condition tests
cover representative required fields for each primitive family.

### Conclusion

Proven for the required-field partitions exercised by the concrete PDF
primitive factories in scope.

## PO-PDFCPF-003: Serialized Style Is Required Only Without Explicit Style

### Claim

When no explicit style object is supplied, each PDF primitive factory requires a
serialized `style` field. When an explicit style object is supplied, compact
geometry payloads remain accepted.

### Proof Method

Factories read the serialized style through `_pdf_required_field()` only when
the `style` argument is `None`. Condition tests cover missing style without an
explicit style and compact payloads with explicit styles.

### Conclusion

Proven for serialized-style and explicit-style partitions in the declared
domain.

## PO-PDFCPF-004: Valid PDF Payload Hydration Is Preserved

### Claim

Valid PDF primitive `parameters` payloads still hydrate to equivalent
components and preserve generated PDF operators.

### Proof Method

Existing PDF generator tests round-trip all primitive payloads and compare
parameters/generated operators. The new compact-payload test proves compatibility
when callers provide styles out of band.

### Conclusion

Proven for valid PDF primitive hydration compatibility in the declared domain.

## PO-PDFCPF-005: Path Command Envelopes Fail Explicitly

### Claim

`PathPDF.create_from_dict()` rejects malformed `commands` values and command
entries before incidental iteration or subscription errors.

### Proof Method

`PathPDF` validates optional `commands` as a non-string sequence and validates
each command as a mapping with a required string `type` field and sequence
`points` field before constructing `PathCommand`.

### Conclusion

Proven for `PathPDF` command envelope partitions in scope.

## PO-PDFCPF-006: Component Group Hydration Uses The Child Factory Contract

### Claim

`ComponentGroupPDF.create_from_dict()` still routes child PDF payloads through
the concrete child factory boundary, so malformed child primitive payloads fail
with the child factory's explicit error.

### Proof Method

The dependent-path test hydrates a valid group, then removes a required
`RectanglePDF` child field and verifies the group path raises the
`RectanglePDF` factory-boundary error.

### Conclusion

Proven for the `ComponentGroupPDF` child-factory dependent path.

## PO-PDFCPF-007: Path Command Type Is Not Stringified

### Claim

`PathPDF.create_from_dict()` rejects non-string serialized command `type`
values before they can be stringified into unsupported command names.

### Domain

Command mappings supplied through `PathPDF.create_from_dict()` and dependent
PDF group hydration.

### Proof Method

`_path_command_from_dict()` reads `type` through `_pdf_required_field()` and
checks that the value is a string before constructing `PathCommand`. Condition
tests cover object, integer, and boolean command-type payloads.

### Conclusion

Proven after focused tests and mutation pass.
