# Table Autofit Rule Contract

This note applies the InkGen Definition of Done to the TABLE-AUTOFIT-RULE-P2
slice. It closes the serialized row/column autofit-rule selector boundary so
hydration cannot accept arbitrary string-equivalent objects as enum values.

## Scope

The slice covers:

- `Table.create_from_dict()` when hydrating serialized `width_rule` and
  `height_rule` values
- `_normalize_autofit_rule()`
- `Column.width_rule` and `Row.height_rule` as hydrated public state
- Autofit queue registration as the dependent live path

## Architecture Impact

Affected surface:

- `src/InkGen/table.py`: serialized row/column rule validation.
- `tests/test_table_contract.py`: TABLE-AUTOFIT-RULE-P2 behavioral and
  dependent-path tests.
- `docs/proofs/table-autofit-rule-contract.md`: this proof note.

Incoming dependencies:

- Saved table payloads hydrate row and column rule strings through
  `Table.create_from_dict()`.
- Public callers read `Row.height_rule` and `Column.width_rule`.
- `Table._register_autofit()` captures hydrated row/column rules into queue
  entries when autofit is enabled.

Outgoing dependencies:

- Rule validation depends on the local `AutoFitRule` enum.
- The helper requires a real string before enum construction.

Before/after edge changes:

- Before this slice, `AutoFitRule(value)` could accept a non-string object that
  compared equal to an enum value string.
- After this slice, serialized rules must be real strings before enum
  normalization.
- No import, dependency, renderer, or public artifact edge was added.

Cycle/layer/coupling/redundancy result:

- Cycle check: no imports were added.
- Layer check: the table model owns serialized rule validation.
- Coupling check: validation remains local to table authoring state and does
  not depend on renderer output.
- Redundancy check: row and column hydration share one helper.

ADR/rule impact:

- No ADR is required. This reinforces the existing serialized table contract.

## Domain Definitions

- Accepted serialized rule values are exactly the strings matching
  `AutoFitRule` values: `"EXPAND"`, `"FIT"`, `"CUT"`, and `"FIXED"`.
- Rejected values include string-equivalent objects, bytes, arbitrary objects,
  and unknown strings.
- Valid hydrated rules must still drive autofit queue registration.

## Fix Log

- Added `_normalize_autofit_rule()`.
- Routed serialized `width_rule` and `height_rule` through the helper.
- Added non-string selector, unknown string, and valid live queue tests.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid rule strings | Preserve as `AutoFitRule` and queue values | PO-TAR-001 | `test_table_autofit_rule_hydration_valid_strings_remain_live` | mutation target |
| String-equivalent non-string objects | Reject during hydration | PO-TAR-002 | `test_table_autofit_rule_hydration_rejects_non_string_selectors` | mutation target |
| Unknown strings | Reject during hydration | PO-TAR-003 | `test_table_autofit_rule_hydration_rejects_unknown_strings` | mutation target |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Rule selector normalization is deterministic. | TABLE-AUTOFIT-RULE-P2 tests |
| Behavioral/condition | yes | The slice defines serialized row/column rule behavior. | Tests marked `@pytest.mark.condition("TABLE-AUTOFIT-RULE-P2")` |
| Failure-mode | yes | Invalid selectors and unknown strings must fail loudly. | Rejection tests |
| Integration/live-path | yes | Hydrated rules affect autofit queue entries. | Queue live-path test |
| Contract/API compatibility | yes | Existing table rule setters and table round trips must continue passing. | Existing `test_table.py` |
| Property/fuzz | no | The accepted enum domain is finite and explicitly named. | Not applicable |
| Mutation | yes | Type guard and enum normalization are proof-critical. | Mutation gate recorded below |
| Security/adversarial | no | No file path, network, subprocess, SQL, template, or active-content surface changed. | Not applicable |
| Performance/resource | no | The change adds constant-time validation per row/column. | Code inspection |
| Concurrency/race | no | No shared state, background workers, locks, or temp files changed. | Not applicable |
| Golden artifact/visual | no | This slice preserves queue behavior but does not claim artifact byte identity. | Not applicable |
| Regression | yes | This closes string-equivalent enum selector acceptance. | Rejection tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Removing the string guard must fail non-string selector tests.
- Breaking enum construction must fail valid/unknown string tests.
- Bypassing rule normalization during hydration must fail rejection tests.
- Breaking hydrated queue semantics must fail the live queue test.

Current result:

- Cosmic Ray 8.4.6, scoped to serialized row/column rule hydration and rule
  normalization rows: 684 generated work items filtered to 4 proof-critical
  work items; 4 killed and 0 survived. A signature-separator mutation on the
  helper was excluded as outside the serialized selector proof obligation.

## PO-TAR-001: Valid Rules Remain Live

### Claim

Valid serialized row and column rule strings hydrate to `AutoFitRule` members
and are captured by autofit queue registration.

### Domain

Serialized table payloads with valid `width_rule` and `height_rule` strings and
`auto_fit=True`.

### Proof Method

Hydration routes both strings through `_normalize_autofit_rule()`. The live-path
test adds content after hydration and asserts the queue entry contains the
hydrated row and column rules.

### Conclusion

Supported by behavioral and dependent-path evidence; upgraded to proven for the
finite enum domain when tests and mutation pass.

## PO-TAR-002: Non-String Selectors Are Rejected

### Claim

Serialized row and column rules reject non-string values before enum
construction.

### Domain

All payloads passed to `Table.create_from_dict()` with non-string `width_rule`
or `height_rule` values.

### Proof Method

`_normalize_autofit_rule()` checks `isinstance(value, str)` before calling
`AutoFitRule(value)`. The focused test includes a string-equivalent object that
would otherwise be accepted by the enum constructor.

### Conclusion

Proven for the stated domain when tests and mutation pass.

## PO-TAR-003: Unknown Strings Are Rejected

### Claim

Serialized row and column rule strings outside the `AutoFitRule` value set fail
during hydration.

### Domain

All payloads passed to `Table.create_from_dict()` with string rule values.

### Proof Method

After the string guard, `_normalize_autofit_rule()` delegates to the closed enum
constructor. Unknown strings raise `ValueError`.

### Conclusion

Proven for the stated domain when tests and mutation pass.
