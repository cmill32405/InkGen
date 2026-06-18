# Drawing Group Contract Proof Obligations

This note applies the InkGen Definition of Done to the DRAWING-GROUP-P1
renderer-neutral drawing group slice. It focuses on the boundary where neutral
drawing recipes become concrete SVG or PDF component groups.

## Scope

The slice covers `DrawingComponentGroup`, output-format normalization, and the
`ZoningDrawing.to_group()` pass-through in `src/InkGen/drawing_components.py`.

The public behavior under review is:

- `normalize_output_format()`
- `DrawingComponentGroup.add_component()`
- `DrawingComponentGroup.to_group()`
- `ZoningDrawing.to_group()`
- `ZoningDrawing.create_from_dict()` for renderer-neutral round trip

## Architecture Impact

Affected surface:

- `src/InkGen/drawing_components.py`: renderer-neutral group boundary and
  materialization checks.
- `tests/test_drawing_group_contract.py`: focused group-boundary tests.
- `tests/test_drawing_components.py`: existing zoning and primitive dependent
  path tests.

Incoming dependencies:

- Synthetic drawing builders use `DrawingComponentGroup` to collect neutral
  primitives before selecting SVG or PDF output.
- Flow document outputs consume drawing groups.
- Grammar truth annotations rely on neutral group and component annotations
  being copied to concrete PDF components.
- Existing zoning recipes rely on `ZoningDrawing.to_group()` delegating to the
  neutral group.

Outgoing dependencies:

- Group materialization depends on `normalize_output_format()`, concrete
  `ComponentGroupSVG`/`ComponentGroupPDF`, concrete primitive `to_component()`
  implementations, base `Component`, and grammar truth copy helpers.
- Zoning construction depends on `Canvas`, `DrawingStyle`, `TextStyle`, and
  neutral primitive recipes.

Before/after edge changes:

- Before this slice, `add_component()` accepted objects with a non-callable
  `to_component` attribute.
- Before this slice, `to_group()` trusted concrete materialization and could
  pass a non-`Component` object to a concrete group, where it could be silently
  omitted by the base group implementation.
- After this slice, neutral components must expose a callable
  `to_component(output_format)` and concrete materialization must return an
  InkGen `Component`.
- No dependency direction changed and no third-party dependency was introduced.

Cycle/layer/coupling/redundancy result:

- Cycle check: no new cycle is introduced; concrete renderer imports remain
  lazy inside `to_group()`.
- Layer check: neutral recipes still own recipe intent, while concrete renderers
  own generated syntax.
- Coupling check: the group boundary still accepts the protocol shape, but now
  fails loudly if materialization breaks the component contract.
- Redundancy check: no duplicate primitive validation was added.

Evidence source and freshness:

- Source-backed: `drawing_components.py`, base `ComponentGroup`,
  `ComponentGroupSVG`, `ComponentGroupPDF`, grammar truth helpers, dependency
  map, and ADRs were read before editing.
- Test-backed: focused tests exercise supported materialization, grammar truth
  propagation, invalid recipe boundaries, unsupported formats, zoning
  round-trip, and legacy zoning geometry compatibility.
- No architecture claim in this note relies only on stale memory.

ADR/rule impact:

- ADR-0001 remains satisfied because grammar truth annotations still copy from
  neutral groups and components to concrete groups and components.
- ADR-0002 remains satisfied because PDF materialization produces
  `ComponentGroupPDF` with built-in PDF components only.
- No new ADR is required.

## Domain Definitions

- A neutral drawing group has a string label and an ordered list of drawing
  primitives.
- A valid primitive provides a callable `to_component(output_format)` method.
- A valid concrete materialization returns an InkGen `Component`.
- Supported group output formats are `svg` and `pdf`, represented by strings or
  `OutputFormat` enum values.
- Unsupported formats fail before component materialization.

## Fix Log

- `DrawingComponentGroup.add_component()` now rejects attribute-only objects
  where `to_component` is not callable.
- `DrawingComponentGroup.to_group()` now rejects materializations that do not
  return a concrete InkGen `Component`.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid neutral group to SVG | Preserve label, order, component type, annotations | PO-DGROUP-001 | `test_drawing_group_materializes_svg_and_pdf_groups` | killed/equivalent |
| Valid neutral group to PDF | Preserve label, order, component type, annotations | PO-DGROUP-001 | same | killed/equivalent |
| Attribute-only invalid primitive | Reject at add boundary | PO-DGROUP-002 | `test_drawing_group_rejects_invalid_recipe_boundaries` | killed |
| Primitive returning non-component | Reject at materialization boundary | PO-DGROUP-002 | same | killed |
| Unsupported output format | Reject before materialization | PO-DGROUP-003 | `test_drawing_group_rejects_unsupported_formats_before_materializing` | killed/equivalent |
| Zoning pass-through | Delegate to neutral group and preserve existing geometry | PO-DGROUP-004 | `test_neutral_zoning_*` tests | killed/equivalent |
| Arbitrary custom PDF renderer components | Excluded by ADR-0002 | Explicit exclusion | PDF renderer tests | Out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Group boundary validation is deterministic. | DRAWING-GROUP-P1 tests |
| Behavioral/condition | yes | The slice defines a renderer-neutral group contract. | Tests are marked `@pytest.mark.condition("DRAWING-GROUP-P1")`. |
| Failure-mode | yes | Invalid primitives and unsupported formats must fail loudly. | Invalid-boundary tests |
| Integration/live-path | yes | Group materialization crosses into SVG/PDF group classes and grammar truth. | Materialization and existing zoning tests |
| Contract/API compatibility | yes | Existing zoning and primitive materialization behavior must remain compatible. | Existing `PDF-P3` tests |
| Property/fuzz | no | The slice is finite dispatch and type-boundary behavior. | Not applicable |
| Mutation | yes | The changed code is proof-critical boundary and dispatch logic. | Mutation result recorded below |
| Security/adversarial | no | The slice adds no file path, network, subprocess, auth, secrets, SQL, template, deserialization, or active-content surface. | Not applicable |
| Performance/resource | no | The slice adds constant-time boundary checks per component. | Code inspection |
| Concurrency/race | no | The slice adds no shared mutable global state, workers, sessions, locks, queues, or temp-file coordination. | Not applicable |
| Golden artifact/visual | yes | SVG/PDF group materialization must preserve component order and geometry. | Materialization and zoning geometry tests |
| Regression | yes | This prevents silent omission of invalid materialized components. | Invalid-materialization test |

## Mutation Testing Gate

Proof-critical mutation targets:

- Weakening output-format normalization should fail unsupported-format tests.
- Weakening callable validation should fail invalid-add tests.
- Weakening concrete `Component` validation should fail invalid-materialization
  tests.
- Redirecting SVG/PDF group dispatch should fail materialization tests.
- Breaking zoning pass-through or round-trip should fail existing zoning tests.

Current result:

- Cosmic Ray 8.4.6, scoped to group normalization/materialization and zoning
  pass-through: 19 work items, 17 killed, and 2 survived.
- Equivalent survivors:
  - `target is OutputFormat.SVG` changed to `target == OutputFormat.SVG`.
    `normalize_output_format()` returns an `OutputFormat` member, so identity
    and equality are equivalent for this enum-domain comparison.
  - `target is OutputFormat.SVG` changed to `target >= OutputFormat.SVG`.
    `OutputFormat.SVG` is the first supported string enum value in this
    normalized two-format branch; SVG and PDF materialization assertions cover
    the reachable outcomes.

## PO-DGROUP-001: Valid Groups Materialize To Concrete Groups

### Claim

Valid neutral drawing groups materialize to SVG or PDF component groups while
preserving label, component order, and grammar truth annotations.

### Domain

All `DrawingComponentGroup` instances whose primitives return concrete InkGen
components for supported output formats.

### Proof Method

`to_group()` normalizes the output format, constructs the concrete group,
copies group annotations, materializes each primitive with the same normalized
target, validates the result as `Component`, copies component annotations, and
adds it to the concrete group.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-DGROUP-002: Invalid Recipe Boundaries Fail Loudly

### Claim

Invalid neutral recipes fail at the add or materialization boundary instead of
being silently omitted.

### Domain

Objects without callable `to_component()` and primitives whose
`to_component()` returns a non-`Component` object.

### Proof Method

`add_component()` checks callability before appending. `to_group()` checks the
concrete return value before copying annotations or adding to a concrete group.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-DGROUP-003: Unsupported Formats Fail Before Materialization

### Claim

Unsupported output formats raise `ValueError` before primitive materialization.

### Domain

All values outside the supported `OutputFormat.SVG` and `OutputFormat.PDF`
domain.

### Proof Method

`normalize_output_format()` is called before concrete group construction or
component iteration. Invalid values fail in enum normalization.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-DGROUP-004: Zoning Uses The Neutral Group Contract

### Claim

`ZoningDrawing.to_group()` delegates to the neutral group and preserves existing
zoning geometry and serialization behavior.

### Domain

Valid zoning recipes over supported SVG and PDF outputs.

### Proof Method

`ZoningDrawing.to_group()` returns `self._group.to_group(output_format)`.
Existing dependent tests compare neutral SVG geometry to legacy zoning geometry,
prove PDF rendering through `DocumentPDF`, and prove serialization round trip.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## Current Slice Decision

The slice keeps renderer-neutral groups as the construction boundary and adds
only fail-fast validation for invalid primitive protocols or invalid concrete
returns. This prevents silent omission while preserving lazy renderer imports,
grammar truth propagation, and the closed PDF renderer domain.
