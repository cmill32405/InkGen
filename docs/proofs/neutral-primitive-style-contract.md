# Neutral Primitive Style Contract

This note applies the InkGen Definition of Done to the
`NEUTRAL-PRIMITIVE-STYLE-P2` slice. It covers style-kind validation at
renderer-neutral drawing primitive construction boundaries.

## Scope

The slice covers:

- `_require_drawing_style()`
- `_require_text_style()`
- `__post_init__()` style validation for `RectangleDrawing`, `LineDrawing`,
  `ArcDrawing`, `QuadraticBezierDrawing`, `CubicBezierDrawing`, `PathDrawing`,
  `RegularPolygonDrawing`, `PolygonalDrawing`, `CircleDrawing`, and
  `TextDrawing`.

Out of scope:

- Geometry validation, already covered by component, curve, path, radial, text,
  and renderer-specific contracts.
- Serialized flow-document drawing style envelope validation, covered by the
  flow-document drawing style slice.
- Style field validation inside `DrawingStyle` and `TextStyle`.

## Dependency Review

Affected surface:

- `src/InkGen/drawing_components.py`
- `tests/test_neutral_primitive_style_contract.py`
- `docs/proofs/neutral-primitive-style-contract.md`

Incoming dependencies:

- Synthetic drawing builders construct neutral primitives before selecting SVG,
  PDF, or DXF output.
- `DrawingComponentGroup.to_group()` materializes neutral primitives into
  concrete renderer components.
- Flow document outputs, DXF export, PDF output, SVG output, and grammar truth
  propagation consume neutral primitive recipes.

Outgoing dependencies:

- Neutral drawing primitives depend on `DrawingStyle` or `TextStyle`.
- Concrete rendering remains delegated to the existing lazy `to_component()`
  imports.
- No dependency was added.

Public contract:

- Drawing primitives that draw geometry require `DrawingStyle`.
- `TextDrawing` requires `TextStyle`.
- Wrong-kind or malformed style objects fail at construction before renderer or
  document-output paths can observe malformed recipe state.
- Valid primitives continue to materialize to SVG and PDF components.

Serialized/artifact contract:

- No serialized payload shape changes.
- Valid SVG/PDF materialization remains unchanged.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced.
- Layer check: neutral recipes validate their own public constructor boundary
  and still delegate concrete output to renderer modules.
- Coupling check: style-kind checks are local and do not duplicate style field
  validation.
- Redundancy check: a shared helper prevents ten repeated ad hoc checks from
  diverging.

ADR/rule impact:

- No ADR is required. The slice preserves renderer neutrality and adds no
  dependency.

## Domain Definitions

- Drawing-style primitives: rectangle, line, arc, quadratic Bezier, cubic
  Bezier, path, regular polygon, polygonal, and circle recipes.
- Text-style primitive: text recipe.
- Valid drawing-style value: an instance of `DrawingStyle`.
- Valid text-style value: an instance of `TextStyle`.
- Invalid style values include `None`, arbitrary objects, and the wrong style
  kind.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid drawing styles | Preserve construction and materialization | PO-NPSTYLE-001 | valid materialization test | killed |
| Valid text styles | Preserve construction and materialization | PO-NPSTYLE-001 | valid materialization test | killed |
| Missing/arbitrary drawing styles | Reject at construction | PO-NPSTYLE-002 | drawing primitive invalid-style tests | killed |
| TextStyle supplied to drawing primitive | Reject at construction | PO-NPSTYLE-002 | wrong-kind drawing style test | killed |
| Missing/arbitrary text styles | Reject at construction | PO-NPSTYLE-003 | text invalid-style tests | killed |
| DrawingStyle supplied to TextDrawing | Reject at construction | PO-NPSTYLE-003 | text wrong-kind style test | killed |
| Post-construction public list mutation | Excluded | Explicit exclusion | downstream group/document guards | out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Style-kind helpers and dataclass post-init checks are deterministic. | Direct constructor tests |
| Behavioral/condition | yes | The slice defines `NEUTRAL-PRIMITIVE-STYLE-P2`. | Condition-marked tests |
| Failure-mode | yes | Wrong-kind styles previously failed later in renderers or document outputs. | Invalid-style tests |
| Integration/live-path | yes | Valid recipes still materialize through SVG/PDF. | Valid materialization test and existing consumers |
| Contract/API compatibility | yes | Existing valid neutral recipes must keep working. | Existing drawing/document/DXF focused tests |
| Property/fuzz | no | The style-kind domain is finite runtime type validation. | Explicit partitions |
| Mutation | yes | Constructor guards are proof-critical. | Cosmic Ray gate |
| Security/adversarial | no | No file, network, subprocess, SQL, archive, or active-content surface changed. | Not applicable |
| Performance/resource | no | Constant-time `isinstance()` checks. | Not applicable |
| Golden artifact/visual | limited yes | Valid SVG/PDF materialization must remain reachable. | Existing renderer tests |
| Regression | yes | Prevents malformed neutral style state from reaching downstream renderers. | Failure-mode tests |

## Mutation Testing Gate

Cosmic Ray 8.4.6 was scoped to the neutral primitive style guards in
`src/InkGen/drawing_components.py`.

- Config: `tests/mutation/neutral_primitive_style_cosmic_ray.toml`
- Filter: `tests/mutation/filter_neutral_primitive_style_work_items.py`
- Work items after filter: `4`
- Result: `4 killed`, `0 survived`

## PO-NPSTYLE-001: Valid Styles Preserve Materialization

### Claim

Neutral primitives constructed with the correct style kind still materialize to
SVG and PDF components.

### Proof Method

The valid-path test constructs representative drawing and text primitives with
valid styles and asserts SVG/PDF component materialization still succeeds.

### Conclusion

Proven by condition tests and scoped mutation testing.

## PO-NPSTYLE-002: Drawing Primitives Require DrawingStyle

### Claim

All non-text neutral drawing primitives reject `None`, arbitrary objects, and
wrong-kind text styles at construction.

### Proof Method

Each non-text primitive routes `__post_init__()` through
`_require_drawing_style()`. Condition tests cover every public non-text neutral
primitive and a wrong-kind `TextStyle` representative.

### Conclusion

Proven by condition tests and scoped mutation testing.

## PO-NPSTYLE-003: TextDrawing Requires TextStyle

### Claim

`TextDrawing` rejects `None`, arbitrary objects, and wrong-kind `DrawingStyle`
values at construction.

### Proof Method

`TextDrawing.__post_init__()` routes through `_require_text_style()`. Condition
tests cover malformed values and the wrong-style-kind representative.

### Conclusion

Proven by condition tests and scoped mutation testing.
