# Font Contract Proof Obligations

This note applies the InkGen Definition of Done to the FONT-P1 font slice. It
focuses on constructor/setter equivalence, finite bounded font sizes, explicit
family/weight/stretch validation, custom font path handling, serialized
hydration, and live output use.

## Scope

The slice covers:

- `Font.__init__()`
- `Font.create_from_dict()`
- `Font.family`
- `Font.requested_family`
- `Font.style`
- `Font.variant`
- `Font.stretch`
- `Font.weight`
- `Font.size`
- Font validation helpers in `src/InkGen/style.py`

OS font discovery, font fallback selection, glyph metrics, and font outline
correctness are out of scope for this slice.

## Architecture Impact

Affected surface:

- `src/InkGen/style.py`: font input validation and serialized hydration.
- `tests/test_font_contract.py`: FONT-P1 behavioral, failure-mode, hydration,
  path, and live-output tests.
- `tests/mutation/font_cosmic_ray.toml`: scoped mutation gate.
- `tests/mutation/filter_font_work_items.py`: proof-critical mutation filter.

Incoming dependencies:

- `TextStyle` owns a `Font` instance.
- SVG, PDF, DXF, text outline, paragraph, table, and document output paths
  consume font size, style, weight, family, and font file resolution.
- Saved text-style payloads hydrate fonts through `Font.create_from_dict()`.

Outgoing dependencies:

- `Font` depends on Matplotlib font-manager APIs for font discovery and
  platform font fallback.
- Validation depends only on local finite-number helpers already used by style
  contracts.
- No third-party dependency or dependency edge was added.

Before/after edge changes:

- Before this slice, the constructor delegated directly to Matplotlib
  `FontProperties`, so booleans, zero sizes, and non-finite sizes could leak
  into public font state or be silently normalized.
- Before this slice, constructor behavior differed from setter behavior.
- Before this slice, caller-provided `custom_font_paths` lists were modified in
  place while normalizing trailing slashes.
- After this slice, constructor input routes through the same public validation
  boundaries as setter input.
- After this slice, font size must be a supported named size or a finite
  numeric value in `(0.0, 240.0]`, excluding booleans.
- After this slice, weight and stretch reject booleans and unsupported values at
  InkGen's public boundary.
- After this slice, custom path lists are copied before normalization.
- The PDF embedded-font update records the requested family separately from the
  resolved family so renderers can distinguish generic family policy from named
  installed-font policy.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced.
- Layer check: validation remains in the style model; renderers and document
  outputs consume the font contract.
- Coupling check: no renderer-specific dependency was added to `style.py`.
- Redundancy check: constructor and setters share validation helpers rather than
  relying on separate Matplotlib behavior.

ADR/rule impact:

- No new ADR is required. This reinforces the dependency-map rule that
  authoring models own their public input contracts before values reach output
  generators.

## Domain Definitions

- A font family is a non-empty string or non-empty list of non-empty strings.
- `Font.requested_family` is the validated family value last passed by the
  caller before Matplotlib resolves it to an installed font.
- Font style is `normal`, `italic`, or `oblique`.
- Font variant is `normal` or `small-caps`.
- Font stretch is an integer from `0` through `1000` or a supported Matplotlib
  stretch name.
- Font weight is an integer from `0` through `1000` or a supported Matplotlib
  weight name.
- Font size is a supported named size or a finite numeric value greater than
  `0.0` and less than or equal to `240.0`.
- Booleans are not numeric font values.
- Custom font paths are `None`, a path string, or a list of path strings.
- Custom font paths must exist before use and are copied before normalization.

## Fix Log

- Added `_coerce_font_size()` and `_coerce_font_family()`.
- Routed `Font.__init__()` through public setters after font-manager
  initialization.
- Accepted integer font sizes as the public docs and existing tests already
  used them.
- Rejected boolean, zero, negative, out-of-range, non-finite, and non-numeric
  font sizes.
- Rejected boolean numeric weight/stretch values.
- Copied custom font path lists before appending trailing separators.
- Added condition-marked tests for constructor/setter equivalence, invalid
  partitions, custom paths, hydration, and live SVG/PDF/DXF/DOCX output use.
- Added `Font.requested_family` for renderer policy decisions that must know
  whether the caller requested a generic family or a named installed font.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid constructor and setter values | Preserve valid enums, numeric boundaries, named size conversion, and integer sizes | PO-FONT-001 | `test_font_constructor_and_setters_share_valid_contract` | killed |
| Invalid size values | Reject booleans, zero, negative, out-of-range, non-finite, unsupported names, and non-numeric values | PO-FONT-002 | `test_font_rejects_invalid_size_boundaries` | killed |
| Invalid family/weight/stretch values | Reject empty families, malformed family lists, booleans, unsupported names, and out-of-range numeric values at InkGen boundary | PO-FONT-003 | `test_font_rejects_invalid_weight_stretch_and_family_boundaries` | killed |
| Requested family tracking | Preserve the caller-requested family independently from resolved font-manager family | PO-FONT-007 | `test_font_preserves_requested_family_for_renderer_policy` | killed/equivalent |
| Custom font paths | Validate type/existence and avoid mutating caller lists | PO-FONT-004 | `test_font_custom_paths_are_validated_and_copied` | killed |
| Hydrated payloads | Route serialized values through public validation boundaries | PO-FONT-005 | `test_font_hydration_uses_public_validation_boundaries` | killed |
| Live output paths | Emit validated font size/style/weight into SVG, PDF, DXF, and DOCX output | PO-FONT-006 | `test_font_contract_remains_live_in_output_paths` | behavioral evidence |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Font enum, family, path, and scalar validation are deterministic. | FONT-P1 tests |
| Behavioral/condition | yes | The slice defines public font behavior. | Tests are marked `@pytest.mark.condition("FONT-P1")`. |
| Failure-mode | yes | Invalid sizes, families, weight/stretch values, and paths must fail at public boundaries. | Invalid-boundary tests |
| Integration/live-path | yes | Renderers and document outputs consume font values. | SVG/PDF/DXF/DOCX live-path test |
| Contract/API compatibility | yes | Existing style, SVG, PDF, DXF, document, and text behavior must continue passing. | Focused gate includes existing tests |
| Property/fuzz | no | The proof partitions finite scalar and finite enum/path cases directly. | Not applicable |
| Mutation | yes | Size, family, weight/stretch, hydration, and path guards are proof-critical. | Mutation result recorded below |
| Security/adversarial | yes | Font paths are file-system inputs. | Type/existence validation and no caller-list mutation |
| Performance/resource | no | The change adds constant-time validation before existing font discovery. | Code inspection |
| Concurrency/race | no | No shared mutable state or background behavior is introduced. | Not applicable |
| Golden artifact/visual | yes | Output formats must materialize font values consistently. | Exact SVG/PDF/DXF/DOCX assertions |
| Regression | yes | This closes invalid font values leaking into live output paths. | FONT-P1 tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Weakening finite size validation must fail scalar-boundary tests.
- Changing inclusive size, weight, or stretch boundaries must fail boundary
  tests.
- Allowing boolean numeric values must fail invalid-boundary tests.
- Bypassing public validation during hydration must fail payload tests.
- Mutating custom path type/existence/copy behavior must fail path tests.
- Mutating requested-family storage must fail renderer-policy tests.
- Changing live consumption of validated font values must fail SVG/PDF/DXF/DOCX
  output tests.

Current result:

- Cosmic Ray 8.4.6, scoped to executable FONT-P1 rows: 74 work items, 74 killed,
  and 0 survived.
- The PDF embedded-font continuation expands the filter to include
  `requested_family`: 78 work items, 77 killed, 1 survived as an equivalent
  public-error-path survivor.
- Equivalent survivor:
  - `custom_font_paths` list validation changed `and` to `or`. The malformed
    list fixture still raises `TypeError` before public font state is usable;
    only the internal failing expression changes.

## PO-FONT-001: Valid Font Values Normalize Deterministically

### Claim

Valid constructor and setter values preserve the same public font domain.

### Domain

Public `Font(...)` construction and public setters using supported family,
style, variant, stretch, weight, and size values.

### Proof Method

Construction initializes font-manager state, creates a default `FontProperties`
object, then routes all public fields through setters. Focused tests check
constructor values, setter updates, named size conversion, integer size support,
and inclusive numeric boundaries.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-FONT-002: Font Size Is Finite, Positive, And Bounded

### Claim

Font size cannot be boolean, zero, negative, non-finite, unsupported by name,
or greater than `240.0`.

### Domain

`Font.size`, constructor `size`, and hydration through `Font.create_from_dict()`.

### Proof Method

Font size delegates to `_coerce_font_size()`, which accepts supported named
sizes or finite numeric values in `(0.0, 240.0]`. Focused tests cover valid
minimum/maximum boundaries and invalid partitions.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-FONT-003: Family, Weight, And Stretch Are Explicit

### Claim

Malformed family values and unsupported weight/stretch values fail at InkGen's
public boundary.

### Domain

`Font.family`, `Font.weight`, `Font.stretch`, constructor values, and hydration.

### Proof Method

Family delegates to `_coerce_font_family()`. Weight and stretch reject booleans,
unsupported names, and out-of-range numeric values before delegating to
Matplotlib. Tests assert InkGen error messages for bad public values so the
proof does not rely on incidental Matplotlib rejection.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-FONT-004: Custom Font Paths Are Validated Without Caller Mutation

### Claim

Custom font path inputs are type-checked, must exist, and do not mutate the
caller's list when normalized.

### Domain

`Font(custom_font_paths=...)` using `None`, a path string, a list of path
strings, malformed values, and missing paths.

### Proof Method

The constructor normalizes a local copy of the path list. Focused tests verify
valid path normalization, caller-list preservation, malformed type rejection,
and missing path rejection.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-FONT-005: Hydration Cannot Bypass Validation

### Claim

`Font.create_from_dict()` rejects malformed serialized font payloads through
the same public validation boundaries as direct construction and setters.

### Domain

Serialized `Font.parameters` payloads and manually supplied payloads with
matching shape.

### Proof Method

Hydration calls `Font(...)` with serialized values. Focused tests cover valid
hydration and invalid field payloads for family, style, variant, stretch,
weight, size, and custom paths.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-FONT-006: Output Paths Consume Validated Font Values

### Claim

SVG, PDF, DXF, and DOCX output paths consume validated font size, style, and
weight values.

### Domain

Text output generation using a valid font with explicit size, style, and
weight.

### Proof Method

The live-path test renders text through SVG, PDF, DXF, and DOCX paths and
asserts emitted CSS font style/size, PDF font operator, DXF text height, and
DOCX half-point/bold/italic run properties.

### Conclusion

Supported by behavioral evidence for the stated domain.

## PO-FONT-007: Requested Family Is Preserved For Renderer Policy

### Claim

`Font.requested_family` preserves the validated family value supplied by the
caller before Matplotlib resolves it to an installed font.

### Domain

Public `Font(...)` construction and `Font.family` setter calls using valid
string or list family values.

### Proof Method

The family setter validates the value through `_coerce_font_family()`, stores a
copy for list inputs, and then passes the same value to Matplotlib's
`FontProperties`. The focused test covers list preservation, setter updates,
and continued resolved-family availability.

### Conclusion

Proven for the stated renderer-policy domain after focused tests and scoped
mutation.
