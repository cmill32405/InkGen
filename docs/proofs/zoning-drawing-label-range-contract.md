# Zoning Drawing Label Range Contract

This note applies the InkGen Definition of Done to the
`ZONING-DRAWING-LABEL-RANGE-P2` slice. It closes the boundary where
`ZoningDrawing` validated only the first zone-label character, then generated
later labels by adding offsets that could leave the alphanumeric ASCII ranges.

## Scope

The slice covers `ZoningDrawing` in `src/InkGen/drawing_components.py`:

- `ZoningDrawing.__init__()`
- `ZoningDrawing.create_from_dict()`
- `ZoningDrawing._apply_parameters()`
- `ZoningDrawing._validate_zone_label_ranges()`
- `_zone_label_sequence_fits()`

Out of scope:

- Multi-character labels such as `10` or `AA`.
- Legacy SVG-specific `cad_component_groups.Zoning` behavior.
- Changing the zoning geometry layout algorithm.

## Dependency Review

Affected surface:

- `src/InkGen/drawing_components.py`: renderer-neutral zoning label validation.
- `tests/test_drawing_components.py`: zoning direct construction, hydration,
  and materialization tests.
- `tests/mutation/zoning_drawing_label_range_cosmic_ray.toml`
- `tests/mutation/filter_zoning_drawing_label_range_work_items.py`

Incoming dependencies:

- Public callers import `ZoningDrawing` from `InkGen`.
- `ZoningDrawing.parameters` and `create_from_dict()` persist and hydrate
  zoning recipes.
- SVG/PDF/DXF/document paths consume the neutral drawing group after zoning
  construction.
- Legacy-comparison tests use `cad_component_groups.Zoning` only as an SVG
  geometry compatibility oracle for valid label inputs.

Outgoing dependencies:

- Zoning construction depends on `Canvas`, `DrawingStyle`, `TextStyle`,
  `TextDrawing`, and renderer-neutral drawing groups.
- Label rendering depends on Python `chr()` over stored ASCII code points.
- No dependency was added.

Public contract:

- Valid one-character zoning label sequences must stay inside one of the
  supported ASCII ranges: digits, uppercase letters, or lowercase letters.
- Invalid label ranges fail during construction or hydration before text
  components are generated.
- Valid serialized payloads still hydrate and materialize.

Serialized/artifact contract:

- `parameters` shape is unchanged.
- Existing ten-horizontal-zone valid fixtures now explicitly use
  `first_horizontal_char=48` so the emitted one-character labels are `0` through
  `9`.
- A default `first_horizontal_char=49` supports at most nine one-character
  numeric labels; ten horizontal zones with the default start now fail instead
  of emitting `:`.

Cycle/layer/coupling/redundancy result:

- Cycle check: no new imports or dependency cycles.
- Layer check: validation remains in the neutral authoring recipe before
  renderer materialization.
- Coupling check: the helper is local to zoning label validation.
- Redundancy check: the range rule is not duplicated in renderers.

ADR/rule impact:

- No ADR is required. This is public-boundary hardening with no architecture
  decision change and no new library dependency.

## Domain Definitions

- `first_horizontal_char` and `first_vertical_char` are integer ASCII code
  points in one of these closed ranges: `48..57`, `65..90`, or `97..122`.
- `horizontal_zones` and `vertical_zones` are positive even integers.
- A valid label run is the closed sequence
  `[first_code, first_code + zone_count - 1]`.
- A label run is accepted only when the full sequence remains inside the same
  digit, uppercase, or lowercase range as `first_code`.

## Fix Log

- Added `ZoningDrawing._validate_zone_label_ranges()`.
- Added `_zone_label_sequence_fits()`.
- Routed constructor and `create_from_dict()` hydration through the same label
  range validation because both call `_apply_parameters()`.
- Updated valid ten-horizontal-zone fixtures to use `first_horizontal_char=48`.
- Added direct valid-label, direct invalid-label, and serialized invalid-label
  condition tests.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid digit label run | Preserve | PO-ZD-LABEL-001 | `test_zoning_drawing_preserves_alphanumeric_label_sequences` | mutation target |
| Valid uppercase label run | Preserve | PO-ZD-LABEL-001 | same | mutation target |
| Default `1` plus ten horizontal zones | Reject | PO-ZD-LABEL-002 | invalid sequence test | mutation target |
| Digit, uppercase, and lowercase overflow starts | Reject | PO-ZD-LABEL-002 | invalid sequence test | mutation target |
| Serialized invalid label ranges | Reject | PO-ZD-LABEL-003 | hydration rejection test | mutation target |
| Multi-character labels | Excluded | explicit exclusion | none | out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | `_validate_zone_label_ranges()` and `_zone_label_sequence_fits()` are deterministic. | direct partition tests |
| Behavioral/condition | yes | The slice defines `ZONING-DRAWING-LABEL-RANGE-P2`. | condition-marked tests |
| Failure-mode | yes | Invalid label ranges previously emitted punctuation/control labels. | invalid direct and hydration tests |
| Integration/live-path | yes | Valid labels still materialize through SVG/PDF and document-output paths. | focused zoning/document-output tests |
| Contract/API compatibility | yes | Valid `parameters/create_from_dict()` remains stable. | existing payload round-trip tests |
| Property/fuzz | no | The ASCII range domain is finite and partitioned. | explicit partitions |
| Mutation | yes | Range arithmetic and validation routing are proof-critical. | Cosmic Ray gate |
| Security/adversarial | limited | Serialized payloads may be untrusted but do not touch filesystem, network, subprocesses, SQL, or active content. | malformed payload tests |
| Performance/resource | no | Adds constant-time validation before existing text measurement. | code inspection |
| Golden artifact/visual | yes | Valid SVG geometry compatibility is preserved for valid label inputs. | legacy geometry comparison |
| Regression | yes | Prevents punctuation/control labels from public zoning recipes. | invalid sequence tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Removing the call to `_validate_zone_label_ranges()` should fail direct and
  hydration invalid-sequence tests.
- Weakening the range upper-bound arithmetic should fail overflow tests.
- Changing range membership should fail valid-label or invalid-label tests.

Current result:

- Cosmic Ray 8.4.6, scoped to zoning label-range validation rows.
- Work items after filter: `43`.
- Result: `42 killed`, `1 equivalent survivor`, `0 non-equivalent survivors`.
- Equivalent survivor: changing the chained range membership upper-bound check
  from `first_code <= upper` to `first_code < upper`. Public zone counts are
  positive even integers, so a start exactly at the upper endpoint of a
  one-character range cannot produce a valid run; count `1` is outside the
  public zoning domain.

## PO-ZD-LABEL-001: Accepted Label Runs Stay Alphanumeric

### Claim

Every accepted one-character zoning label generated by `ZoningDrawing` is an
alphanumeric ASCII character.

### Domain

All public constructor and hydration paths that set `first_horizontal_char`,
`first_vertical_char`, `horizontal_zones`, or `vertical_zones`.

### Proof Method

`_apply_parameters()` validates individual first-character code points and zone
counts, then `_validate_zone_label_ranges()` checks each full label run with
`_zone_label_sequence_fits()`. The helper accepts a run only when
`first_code + zone_count - 1` stays inside the same ASCII digit, uppercase, or
lowercase range.

### Conclusion

Proven after focused tests and mutation pass with one equivalent survivor.

## PO-ZD-LABEL-002: Overflowing Label Runs Fail Before Text Generation

### Claim

Label ranges that would emit punctuation, non-printable characters, or
cross-range labels fail before `TextDrawing` components are created.

### Domain

Constructor-supplied label starts and zone counts, including default
`first_horizontal_char=49` combined with ten horizontal zones.

### Proof Method

`_apply_parameters()` calls `_validate_zone_label_ranges()` before
`_get_character_sizes()`, `_set_zoning_widths()`, and `_create_zoning()`.
Failure-mode tests cover digit, uppercase, and lowercase overflow starts.

### Conclusion

Proven after focused tests and mutation pass with one equivalent survivor.

## PO-ZD-LABEL-003: Hydration Cannot Bypass Label Validation

### Claim

Serialized zoning payloads cannot hydrate invalid label ranges into public
zoning state.

### Domain

Payloads passed to `ZoningDrawing.create_from_dict()` with malformed label
range combinations.

### Proof Method

`create_from_dict()` delegates validated fields to `cls(..., **parameters)`.
The hydration test mutates a valid serialized payload to an invalid
`first_horizontal_char` and asserts the same label-range failure.

### Conclusion

Proven after focused tests and mutation pass with one equivalent survivor.
