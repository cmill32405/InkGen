# CAD Zoning Contract Proof Obligations

This note applies the InkGen Definition of Done to the CAD-ZONING-P1 legacy
zoning slice. It focuses on documenting and proving the intentional
SVG-specific `cad_component_groups.Zoning` path, including CSS-like parameter
specificity and serialization.

## Scope

The slice covers `Zoning` in `src/InkGen/cad_component_groups.py`.

The public behavior under review is:

- `Zoning.__init__()`
- `Zoning.component_group`
- `Zoning.parameters`
- `Zoning.create_from_dict()`
- `_set_margins()`
- `_set_zoning_widths()`

## Architecture Impact

Affected surface:

- `src/InkGen/cad_component_groups.py`: legacy SVG zoning helper.
- `tests/test_cad_zoning_contract.py`: focused CAD-ZONING-P1 tests.
- `tests/test_cad_component_groups.py`: existing legacy compatibility tests.

Incoming dependencies:

- Public callers can import `Zoning` from `InkGen`.
- Existing examples and saved recipes reference the legacy zoning helper.
- `ZoningDrawing` compatibility tests compare neutral SVG geometry against this
  legacy path.

Outgoing dependencies:

- `Zoning` depends on `Canvas`, `DrawingStyle`, `TextStyle`, `TextComponent`,
  base `ComponentGroup`, and concrete SVG components.
- The SVG dependency is intentional and documented as a legacy exception in the
  dependency map.

Before/after edge changes:

- Before this slice, explicit zero margin or zone-width values passed validation
  but were ignored during specificity resolution because truthiness was used.
- After this slice, explicit zero values are honored by the same specificity
  rules as any other provided value.
- No dependency edge or third-party dependency was introduced.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced.
- Layer check: the SVG-specific edge remains confined to the documented legacy
  helper; neutral multi-format zoning remains in `drawing_components.py`.
- Coupling check: no new coupling is added.
- Redundancy check: no duplicate neutral zoning logic was added.

Evidence source and freshness:

- Source-backed: `cad_component_groups.py`, legacy tests, `docs/dependency-map.md`,
  and docs mentioning `Zoning`/`ZoningDrawing` were read before editing.
- Test-backed: focused tests exercise SVG-only output, explicit zero
  specificity, invalid parameters, serialization round trip, and text-derived
  default widths.
- No architecture claim in this note relies only on stale memory.

ADR/rule impact:

- No new ADR is required because the dependency map already records the legacy
  SVG-specific edge as intentional.
- Future work should not copy this edge into new authoring APIs; use
  `ZoningDrawing` for multi-format zoning.

## Domain Definitions

- A valid zoning helper is built from a `Canvas`, `DrawingStyle`, and
  `TextStyle`.
- Margins, zone widths, and radii accept numeric values greater than or equal to
  zero.
- More-specific margin and width parameters override less-specific parameters,
  including when the more-specific value is zero.
- Horizontal and vertical zone counts must be positive even integers.
- First-zone characters must be alphanumeric ASCII code points.
- Output is a legacy base `ComponentGroup` containing SVG components.

## Fix Log

- `_set_margins()` now treats `0.0` as a supplied value.
- `_set_zoning_widths()` now treats `0.0` as a supplied value.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid default zoning | Emit SVG rectangles, lines, and text labels | PO-CADZ-001 | `test_legacy_zoning_emits_only_svg_components` | behavioral evidence |
| Explicit zero margin/width | Preserve as supplied most-specific values | PO-CADZ-002 | `test_legacy_zoning_honors_zero_specific_margins_and_widths` | killed |
| Invalid parameter types/ranges/names | Reject before geometry generation | PO-CADZ-003 | `test_legacy_zoning_rejects_invalid_boundary_parameters` | behavioral evidence |
| Serialization with style registry | Preserve parameters and generated component geometry | PO-CADZ-004 | `test_legacy_zoning_round_trips_parameters_with_style_registry` | behavioral evidence |
| Default zone width calculation | Use widest A/W/Y text outline plus padding | PO-CADZ-005 | `test_legacy_zoning_default_width_tracks_text_outline` | killed |
| Multi-format zoning | Excluded from legacy helper | Explicit exclusion | `ZoningDrawing` tests | Out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Parameter specificity and serialization are deterministic. | CAD-ZONING-P1 tests |
| Behavioral/condition | yes | The slice defines the legacy zoning contract. | Tests are marked `@pytest.mark.condition("CAD-ZONING-P1")`. |
| Failure-mode | yes | Invalid parameters must fail before component generation. | Invalid-boundary test |
| Integration/live-path | yes | `Zoning.component_group` is consumed by SVG/component-group paths and compared to `ZoningDrawing`. | Focused and existing tests |
| Contract/API compatibility | yes | Existing legacy parameters and round trip must remain compatible. | Existing legacy tests |
| Property/fuzz | no | This slice proves finite parameter partitions. | Not applicable |
| Mutation | yes | The changed specificity logic is proof-critical. | Mutation result recorded below |
| Security/adversarial | no | The slice adds no file path, network, subprocess, auth, secrets, SQL, template, deserialization, or active-content surface. | Not applicable |
| Performance/resource | no | The slice changes constant-time parameter selection. | Code inspection |
| Concurrency/race | no | No shared state, workers, locks, or temp files are added. | Not applicable |
| Golden artifact/visual | yes | SVG zoning component geometry must remain stable. | Component parameter comparisons |
| Regression | yes | This closes accepted zero values being ignored. | Explicit-zero test |

## Mutation Testing Gate

Proof-critical mutation targets:

- Reverting explicit-zero checks to truthiness should fail the zero-specificity
  test.
- Changing resolved margin or zone-width assignments should fail parameter and
  geometry assertions.

Current result:

- Cosmic Ray 8.4.6, scoped to margin/zone-width specificity checks and resolved
  assignment rows: 20 work items, 20 killed, and 0 survived.

## PO-CADZ-001: Legacy Zoning Emits SVG Components

### Claim

Legacy `Zoning` emits a base `ComponentGroup` containing SVG-specific rectangle,
line, and text components.

### Domain

Valid `Zoning` construction for supported canvas, line style, and text style
objects.

### Proof Method

`Zoning._create_zoning()` constructs `RectangleSVG`, `LineSVG`, and `TextSVG`
instances directly and stores them in a base `ComponentGroup`.

### Conclusion

Supported by behavioral evidence for the stated domain.

## PO-CADZ-002: Zero Specific Values Override Less-Specific Values

### Claim

Explicit zero margin and zone-width values participate in the same specificity
rules as nonzero values.

### Domain

All margin and zone-width parameter families where a more-specific value is
`0.0` and a less-specific fallback is nonzero.

### Proof Method

`_set_margins()` and `_set_zoning_widths()` now test `is not None`, so zero is a
supplied value. The focused test proves the resolved parameters and outer
rectangle geometry.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-CADZ-003: Invalid Parameters Fail Before Geometry

### Claim

Invalid zoning parameters raise `ValueError` or `KeyError` during construction.

### Domain

Malformed numeric parameters, negative numeric parameters, invalid zone counts,
invalid character codes, and unknown parameter names.

### Proof Method

`__init__()` validates each keyword before calling `_create_zoning()`.

### Conclusion

Supported by behavioral evidence for the stated domain.

## PO-CADZ-004: Serialization Preserves Legacy Zoning

### Claim

`parameters` and `create_from_dict()` preserve legacy zoning inputs and emitted
component geometry when supplied with the style registry.

### Domain

Valid zoning instances with serializable canvas and styles.

### Proof Method

`parameters` stores canvas, style payloads, and resolved parameters.
`create_from_dict()` resolves styles by name or recreates them, then constructs a
new `Zoning` with the stored parameters.

### Conclusion

Supported by behavioral evidence for the stated domain.

## PO-CADZ-005: Default Width Uses Text Outline

### Claim

Default zone widths equal the widest A/W/Y text outline plus four units.

### Domain

Valid zoning instances without explicit zone-width overrides.

### Proof Method

`_set_zoning_widths()` reads cached character outlines and computes
`max(A, W, Y) + 4`.

### Conclusion

Supported by behavioral evidence; assignment rows are included in mutation.

## Current Slice Decision

The slice preserves `Zoning` as a documented legacy SVG-specific helper while
closing a concrete parameter-contract bug. New multi-format code should continue
to use `ZoningDrawing` instead of copying this dependency direction.
