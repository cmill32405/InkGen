# Path Finite Boundary Contract Proof Obligations

This note applies the InkGen Definition of Done to the PATH-FINITE-P2 path
command finite-boundary hardening slice.

## Scope

The slice covers public coordinate boundaries for:

- `PathCommand.__init__()`
- `PathCommand.points`
- `PathCommand.add_point()`
- `Path.add_command()` dictionary insertion through `PathCommand`

## Architecture Impact

Affected surface:

- `src/InkGen/component.py`: finite numeric path command coordinate validation.
- `tests/test_path_finite_contract.py`: PATH-FINITE-P2 behavioral,
  failure-mode, state-preservation, and dictionary insertion tests.
- `tests/mutation/path_finite_cosmic_ray.toml`: scoped mutation gate.
- `tests/mutation/filter_path_finite_work_items.py`: proof-critical mutation
  filter.
- `docs/proofs/path-finite-contract.md`: proof note.

Incoming dependencies:

- `Path`, `PathPDF`, `PathSVG`, `PathDrawing`, and DXF path export consume
  `PathCommand.points`.
- Synthetic drawing fixtures rely on path command coordinates being finite
  renderer-safe values.

Outgoing dependencies:

- The finite validator depends only on `math.isfinite()`.
- No dependency or package was added.

Before/after edge changes:

- Before this slice, `NaN`, `inf`, and boolean coordinates could be stored in
  path commands and exposed to SVG/PDF/DXF renderers.
- After this slice, all public path command coordinate boundaries require
  finite numeric non-boolean values.
- Existing valid SVG-style command normalization and finite point formatting
  remain unchanged.

Cycle/layer/coupling/redundancy result:

- Cycle check: no dependency edge was added.
- Layer check: path command validation remains in `component.py`.
- Coupling check: concrete renderers continue to consume normalized command
  data rather than revalidating coordinates.
- Redundancy check: one local finite validator is reused by constructor,
  `points`, and `add_point()` paths.

ADR/rule impact:

- No ADR is required. This closes an invalid public input gap in an existing
  component contract.

## Domain Definitions

- A path command point is a two-coordinate tuple/list whose coordinates are
  finite numeric non-boolean values.
- Rejected `points` setter and `add_point()` inputs must not mutate prior valid
  command state.
- `Path.add_command()` dictionary insertion must consume the same
  `PathCommand` validation boundary.

## Fix Log

- Added finite numeric coordinate validation to `PathCommand._coerce_point()`.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid finite command points | Preserve command normalization and points | PO-PFIN-001 | `test_path_command_preserves_valid_finite_points` | mutation target |
| Invalid command points | Reject non-finite, nonnumeric, boolean, and malformed point values | PO-PFIN-002 | `test_path_command_rejects_invalid_constructor_and_setter_points` | mutation target |
| Dictionary insertion | Reject invalid dictionary-sourced points and preserve path state | PO-PFIN-003 | `test_path_add_command_dictionary_rejects_nonfinite_coordinates` | focused test |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Finite numeric command validation is deterministic. | PATH-FINITE-P2 tests |
| Behavioral/condition | yes | The slice defines public path command point boundaries. | Tests marked `@pytest.mark.condition("PATH-FINITE-P2")` |
| Failure-mode | yes | Invalid points must fail and preserve state. | Constructor, setter, add-point, and dictionary tests |
| Integration/live-path | limited | `Path.add_command()` dictionary insertion is the live public path aggregator. | Dictionary insertion test |
| Contract/API compatibility | yes | Existing PATH-P1 behavior must continue passing. | Focused gate includes `tests/test_path_contract.py` |
| Property/fuzz | no | Partitions are finite numeric type/range classes. | Not applicable |
| Mutation | yes | The validator and public mutation calls are proof-critical. | Result recorded below |
| Security/adversarial | no | No path, network, subprocess, archive, SQL, template, or active-content surface changed. | Not applicable |
| Performance/resource | no | Constant-time validation only. | Not applicable |
| Concurrency/race | no | No shared state, workers, locks, or temp files changed. | Not applicable |
| Regression | yes | Prevents non-finite path command geometry from reaching renderers. | Invalid command tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Weakening boolean, numeric, finite, or arity checks must fail invalid command
  tests.
- Removing `points` or `add_point()` validation calls must fail invalid-input or
  state-preservation tests.

Current result:

- PASS. Cosmic Ray generated 2,854 raw component mutants. The
  `PATH-FINITE-P2` filter reduced this to 17 proof-critical work items. All 17
  were killed and 0 survived.

## PO-PFIN-001: Valid Finite Path Inputs Preserve Geometry

### Claim

Finite numeric path command inputs preserve command normalization and public
point output.

### Domain

Path commands with finite numeric coordinate pairs.

### Proof Method

Construction, `points`, and `add_point()` pass point coordinates through finite
coercion and then store floats. Focused tests assert command type normalization
and point output before and after appending a point.

### Conclusion

Proven for the stated domain after focused tests and mutation pass.

## PO-PFIN-002: Invalid Path Command Inputs Fail Without Mutation

### Claim

Invalid path command points are rejected before construction, setter calls, or
append calls store invalid geometry.

### Domain

`NaN`, positive/negative infinity, booleans, nonnumeric objects, nonnumeric
strings, one-coordinate points, and three-coordinate points.

### Proof Method

`PathCommand._coerce_point()` checks arity and validates each coordinate with
finite numeric coercion. Focused tests cover invalid constructor, `points`
setter, and `add_point()` partitions and compare serialized state after
rejected mutations.

### Conclusion

Proven for the stated domain after focused tests and mutation pass.

## PO-PFIN-003: Dictionary Insertion Uses Same Boundary

### Claim

`Path.add_command()` rejects invalid dictionary-sourced points and preserves
prior path state.

### Domain

`Path.add_command()` calls with command dictionaries containing invalid point
coordinates.

### Proof Method

`Path.add_command()` constructs a `PathCommand` from dictionary data before
appending it. Focused tests assert invalid dictionary-sourced points raise and
the original path parameters remain unchanged.

### Conclusion

Proven for the stated representative dictionary insertion paths after focused
tests pass.
