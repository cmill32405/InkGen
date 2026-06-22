# Error Contract Proof Obligations

This note applies the InkGen Definition of Done to the ERRORS-P1 public
exception contract slice. It covers the project-specific exception classes,
their package-root exports, and representative live failure paths that consume
them.

## Scope

The slice covers:

- `src/InkGen/errors.py` module and public exception classes
- `src/InkGen/__init__.py` root exports for project exceptions
- Existing failure paths in boundary, component, layer, and document code
- `tests/test_error_contract.py` condition tests

## Architecture Impact

Affected surface:

- `src/InkGen/errors.py`: module and class docstrings for public exceptions.
- `src/InkGen/__init__.py`: package-root aliases and `__all__` entries.
- `tests/test_error_contract.py`: ERRORS-P1 behavioral and live-path tests.
- `tests/mutation/error_contract_cosmic_ray.toml`: scoped mutation attempt.
- `tests/mutation/filter_error_contract_work_items.py`: proof-critical
  mutation filter.
- `docs/api-reference.md`: public error API documentation.
- `docs/proofs/error-contract.md`: proof note.

Incoming dependencies:

- Boundary and canvas validation raise `IllegalArgumentError` and
  `InvalidConvexHull`.
- Polygon components raise `InvalidPolygonError`.
- Component groups raise `InvalidComponentID`.
- Layers raise `InvalidComponentGroupID`, `ComponentGroupCollision`, and
  `ComponentGroupOffCanvas`.
- Documents and page stacks raise `IncompatibleCanvas`.
- Tests and docs import project exceptions as stable public classes.

Outgoing dependencies:

- Exception classes inherit directly from Python `ValueError`.
- Root exports alias the canonical classes from `InkGen.errors`.
- No third-party dependency was added.

Before/after edge changes:

- Before this slice, project exceptions were available through
  `InkGen.errors` but were not listed on the package root despite being part of
  the user-visible failure contract.
- After this slice, project exceptions remain plain `ValueError` subclasses and
  can also be imported from `InkGen`.
- Existing exception raise sites and messages are unchanged.

Cycle/layer/coupling/redundancy result:

- Cycle check: no new behavior import cycle is introduced.
- Layer check: `errors.py` remains the shared low-level exception module.
- Coupling check: implementation modules continue to import from
  `InkGen.errors`; package-root exports are for callers.
- Redundancy check: no duplicate exception classes are introduced.

ADR/rule impact:

- No ADR is required. This implements the public API rule that documented
  stable caller-facing classes may be available from the package root.

## Domain Definitions

- A project exception is one of the finite classes in
  `tests/test_error_contract.py::PUBLIC_EXCEPTION_NAMES`.
- Project exceptions must be `ValueError` subclasses.
- Constructing an exception with a message must preserve default Python
  exception `args` and `str()` behavior.
- A root exception export must be identical to the canonical class in
  `InkGen.errors`.
- This slice does not promise that all internal validation errors are project
  exceptions; built-in `TypeError` and `ValueError` remain valid where already
  used.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Exception inheritance | Every project exception remains a plain `ValueError` subclass | PO-ERR-001 | `test_project_exceptions_are_plain_value_errors` | mutation attempted |
| Message preservation | Default `args` and `str()` behavior is retained | PO-ERR-002 | `test_project_exceptions_are_plain_value_errors` | mutation attempted |
| Root export aliases | Root names exist in `InkGen.__all__` and alias canonical classes | PO-ERR-003 | `test_project_exceptions_are_exported_from_package_root` | mutation attempted |
| Live raise paths | Representative public failures raise documented classes | PO-ERR-004 | `test_exception_contracts_are_live_in_existing_failure_paths` | mutation attempted |
| Exclusions | Built-in errors remain out of scope | PO-ERR-005 | documented exclusion | not applicable |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Exception inheritance and alias identity are deterministic. | ERRORS-P1 tests |
| Behavioral/condition | yes | The slice defines public exception behavior. | Tests are marked `@pytest.mark.condition("ERRORS-P1")`. |
| Failure-mode | yes | Public validation and lookup failures must raise the documented classes. | Live-path exception test |
| Integration/live-path | yes | Boundary, component, layer, and document paths are exercised directly. | Live-path exception test |
| Contract/API compatibility | yes | Existing exception identities and root aliases are public contracts. | identity assertions |
| Property/fuzz | no | The exception set is finite and explicitly enumerated. | Not applicable |
| Mutation | attempted | Exception classes and export bindings may produce limited or no work items. | Result recorded below |
| Security/adversarial | no | No path, network, subprocess, archive, SQL, template, or active-content surface changed. | Not applicable |
| Performance/resource | no | Plain exception classes and import aliases have no material runtime cost. | Not applicable |
| Concurrency/race | no | No shared mutable state, locks, or background work are added. | Not applicable |
| Golden artifact/visual | no | No rendered artifact surface is changed. | Not applicable |
| Regression | yes | Prevents public exceptions from silently losing root export coverage. | ERRORS-P1 tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Changing inheritance away from `ValueError` must fail inheritance tests.
- Replacing canonical root exports with different objects must fail identity
  tests.
- Removing a root export or `__all__` entry must fail export tests.
- Changing representative live failure paths away from the documented exception
  classes must fail live-path tests.

Current result:

- Tool: Cosmic Ray 8.4.6.
- Environment: WSL Python 3.12 virtualenv.
- Raw work items after init/filter: 0 -> 0.
- Result: not applicable. Cosmic Ray did not generate mutation work items for
  the plain exception classes, docstrings, import bindings, or `__all__` list in
  this slice.
- Replacement evidence: focused ERRORS-P1 tests directly exercise inheritance,
  message preservation, root export membership, canonical object identity, and
  representative live failure paths for every project exception class.

## PO-ERR-001: Exceptions Preserve ValueError Semantics

### Claim

Every project-specific public exception is a `ValueError` subclass and remains
usable as a normal Python exception.

### Domain

The finite exception set listed in `PUBLIC_EXCEPTION_NAMES`.

### Proof Method

The focused test constructs each class, checks `issubclass(..., ValueError)`,
and checks `issubclass(..., Exception)`.

### Conclusion

Proven for the stated domain after focused tests pass.

## PO-ERR-002: Messages Preserve Default Exception Behavior

### Claim

Constructing a project exception with a message preserves standard `args` and
`str()` behavior.

### Domain

The finite exception set listed in `PUBLIC_EXCEPTION_NAMES`.

### Proof Method

The focused test constructs each class with `"contract message"` and asserts
the exact `args` tuple and string conversion.

### Conclusion

Proven for the stated domain after focused tests pass.

## PO-ERR-003: Root Exports Preserve Canonical Identity

### Claim

Package-root exception exports alias the canonical `InkGen.errors` classes.

### Domain

The finite exception set listed in `PUBLIC_EXCEPTION_NAMES`.

### Proof Method

The focused test checks each exception name is present in `InkGen.__all__` and
that `getattr(InkGen, name) is getattr(InkGen.errors, name)`.

### Conclusion

Proven for the stated domain after focused tests pass.

## PO-ERR-004: Existing Failure Paths Raise Documented Exceptions

### Claim

Representative public failure paths continue to raise the documented project
exception classes.

### Domain

Boundary/canvas validation, polygon validation, missing component lookup,
missing group lookup, layer collision, off-canvas group insertion, and
document-page canvas compatibility.

### Proof Method

The focused live-path test triggers each public failure and asserts the
documented exception class imported from the package root.

### Conclusion

Proven for the stated representative domain after focused tests pass.
