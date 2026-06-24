# Drawing Group Contract Proof Obligations

This note applies the InkGen Definition of Done to the DRAWING-GROUP-P1
renderer-neutral drawing group slice. It focuses on the boundary where neutral
drawing recipes become concrete SVG or PDF component groups and where backend
selectors are normalized.

## Scope

The slice covers `DrawingComponentGroup`, output-format normalization, and the
`ZoningDrawing.to_group()` pass-through in `src/InkGen/drawing_components.py`.

The public behavior under review is:

- `normalize_output_format()`
- `DrawingComponentGroup.__post_init__()`
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
- Before the label-contract hardening update, `DrawingComponentGroup` could be
  constructed with non-string labels, and flow-document drawing hydration
  stringified malformed serialized labels.
- Before the format-selector hardening update, `normalize_output_format()`
  stringified arbitrary objects, so an object whose `__str__()` returned
  `"svg"` or `"pdf"` could cross a boundary documented as accepting only
  strings or `OutputFormat` enum values.
- After this slice, neutral components must expose a callable
  `to_component(output_format)` and concrete materialization must return an
  InkGen `Component`.
- After the label-contract hardening update, neutral drawing groups reject
  non-string labels at construction, and flow-document hydration delegates to
  that same boundary instead of repairing malformed labels.
- After the format-selector hardening update, backend selectors must be
  `OutputFormat` members or real strings before unsupported-value normalization
  can run.
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
- `group_label` must be a real string. Empty strings remain valid for callers
  that intentionally want renderer defaults.
- A valid primitive provides a callable `to_component(output_format)` method.
- A valid concrete materialization returns an InkGen `Component`.
- Supported group output formats are `svg` and `pdf`, represented by strings or
  `OutputFormat` enum values.
- Non-string objects are not backend selectors, even if their string
  representation matches a supported format.
- Unsupported formats fail before component materialization.

## Fix Log

- `DrawingComponentGroup.add_component()` now rejects attribute-only objects
  where `to_component` is not callable.
- `DrawingComponentGroup.to_group()` now rejects materializations that do not
  return a concrete InkGen `Component`.
- `DrawingComponentGroup.__post_init__()` now rejects non-string labels.
- Flow-document drawing hydration no longer stringifies serialized group
  labels, so invalid labels fail at the neutral group boundary.
- `normalize_output_format()` now rejects non-string, non-`OutputFormat`
  selectors instead of stringifying arbitrary objects.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid neutral group to SVG | Preserve label, order, component type, annotations | PO-DGROUP-001 | `test_drawing_group_materializes_svg_and_pdf_groups` | killed/equivalent |
| Valid neutral group to PDF | Preserve label, order, component type, annotations | PO-DGROUP-001 | same | killed/equivalent |
| Invalid group label | Reject non-string labels before rendering or serialization | PO-DGROUP-005 | `test_drawing_group_rejects_non_string_labels` | killed |
| Invalid serialized flow-document drawing label | Reject instead of stringifying during hydration | PO-DGROUP-005 | `test_flow_document_drawing_group_hydration_rejects_malformed_label` | behavioral evidence |
| Attribute-only invalid primitive | Reject at add boundary | PO-DGROUP-002 | `test_drawing_group_rejects_invalid_recipe_boundaries` | killed |
| Primitive returning non-component | Reject at materialization boundary | PO-DGROUP-002 | same | killed |
| Unsupported output format | Reject before materialization | PO-DGROUP-003 | `test_drawing_group_rejects_unsupported_formats_before_materializing` | killed/equivalent |
| Stringifiable non-string output selector | Reject before materialization | PO-DGROUP-006 | `test_normalize_output_format_rejects_stringifiable_objects`, `test_drawing_group_rejects_non_string_format_before_materializing` | killed |
| Zoning pass-through | Delegate to neutral group and preserve existing geometry | PO-DGROUP-004 | `test_neutral_zoning_*` tests | killed/equivalent |
| Arbitrary custom PDF renderer components | Excluded by ADR-0002 | Explicit exclusion | PDF renderer tests | Out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Group boundary validation is deterministic. | DRAWING-GROUP-P1 tests |
| Behavioral/condition | yes | The slice defines a renderer-neutral group contract. | Tests are marked `@pytest.mark.condition("DRAWING-GROUP-P1")`. |
| Failure-mode | yes | Invalid labels, invalid primitives, unsupported formats, and wrong-type backend selectors must fail loudly. | Invalid-boundary, hydration, and format-selector tests |
| Integration/live-path | yes | Group materialization crosses into SVG/PDF group classes, grammar truth, and flow-document hydration. | Materialization, flow-document, and existing zoning tests |
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
- Weakening output-format type validation should fail stringifiable-object tests
  and prove group materialization does not start.
- Weakening group-label validation should fail invalid-label and flow-document
  hydration tests.
- Weakening callable validation should fail invalid-add tests.
- Weakening concrete `Component` validation should fail invalid-materialization
  tests.
- Redirecting SVG/PDF group dispatch should fail materialization tests.
- Breaking zoning pass-through or round-trip should fail existing zoning tests.

Current result:

- Cosmic Ray 8.4.6, scoped to group normalization/materialization and zoning
  pass-through after label-contract hardening: 20 work items, 18 killed, and 2
  survived.
- Equivalent survivors:
  - `target is OutputFormat.SVG` changed to `target == OutputFormat.SVG`.
    `normalize_output_format()` returns an `OutputFormat` member, so identity
    and equality are equivalent for this enum-domain comparison.
  - `target is OutputFormat.SVG` changed to `target >= OutputFormat.SVG`.
    `OutputFormat.SVG` is the first supported string enum value in this
    normalized two-format branch; SVG and PDF materialization assertions cover
    the reachable outcomes.
  - The label-validation guard mutants in `DrawingComponentGroup.__post_init__()`
    were killed.
- Cosmic Ray 8.4.6, scoped to format-selector type validation after the
  format-selector hardening update: 3 work items, 3 killed, and 0 survived.

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

## PO-DGROUP-006: Output Selectors Do Not Use Arbitrary Stringification

### Claim

For every public backend selector passed to `normalize_output_format()` or
`DrawingComponentGroup.to_group()`, only `OutputFormat` members and real strings
can enter supported-format normalization; arbitrary objects are rejected before
component materialization, even when their `__str__()` value is `"svg"` or
`"pdf"`.

### Domain

All public selector values supplied to neutral primitive `to_component()` paths
and group `to_group()` paths.

### Proof Method

`normalize_output_format()` returns enum values directly, rejects non-strings
with `TypeError`, and only then lowercases and validates real strings through
the `OutputFormat` enum. Focused tests cover direct helper rejection and the
dependent group live path with a recording primitive that proves
materialization was not attempted. The DRAWING-FORMAT-P2 mutation gate mutates
the proof-critical rows and all 3 retained mutants are killed.

### Conclusion

Proven for the stated selector domain. Subclasses of `str` remain inside the
accepted string domain.

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

## PO-DGROUP-005: Neutral Group Labels Are Strings

### Claim

Every public `DrawingComponentGroup` instance has a string `group_label`, and
flow-document drawing hydration cannot convert malformed serialized labels into
apparently valid strings.

### Domain

Public `DrawingComponentGroup(group_label=...)` construction and
`FlowDocument.create_from_dict()` payloads that contain drawing blocks.

### Proof Method

`DrawingComponentGroup.__post_init__()` rejects non-string labels before any
components are added or renderers are selected. `_drawing_from_parameters()`
passes the serialized `group_label` through unchanged, so malformed serialized
labels are checked by the same neutral group constructor. Focused tests cover
direct non-string labels and a flow-document drawing block with a malformed
serialized label.

### Counterexamples And Exclusions

Private mutation of dataclass attributes after construction is outside the
public constructor and hydration contract. Empty string labels remain valid
because DXF and renderer defaults use them intentionally.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## Current Slice Decision

The slice keeps renderer-neutral groups as the construction boundary and adds
only fail-fast validation for invalid primitive protocols or invalid concrete
returns. This prevents silent omission while preserving lazy renderer imports,
grammar truth propagation, and the closed PDF renderer domain.
