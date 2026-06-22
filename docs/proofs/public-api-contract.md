# Public API Contract Proof Obligations

This note applies the InkGen Definition of Done to the PUBLIC-API-P1 package
root export slice. It covers the top-level `InkGen` import surface used by
external callers and examples.

## Scope

The slice covers:

- `src/InkGen/__init__.py` import bindings
- `src/InkGen/__init__.py::__all__`
- Root exports for documented PDF classes, extraction-truth helpers, table row
  objects, SVG flattening utilities, and renderer-neutral zoning recipes

## Architecture Impact

Affected surface:

- `src/InkGen/__init__.py`: top-level package aliases for existing public
  classes and functions.
- `tests/test_public_api_contract.py`: PUBLIC-API-P1 condition tests.
- `tests/mutation/public_api_cosmic_ray.toml`: scoped mutation attempt.
- `tests/mutation/filter_public_api_work_items.py`: proof-critical mutation
  filter.
- `docs/api-reference.md`: root import contract documentation.
- `docs/proofs/public-api-contract.md`: proof note.

Incoming dependencies:

- External callers import InkGen primitives from the package root.
- Documentation describes PDF, extraction truth, table, SVG utility, and
  renderer-neutral drawing APIs as primary InkGen surfaces.
- Examples and downstream fixture generators rely on stable class identities
  from submodules.

Outgoing dependencies:

- `__init__.py` imports existing public objects from InkGen submodules.
- No implementation module imports `InkGen.__init__` for behavior.
- No third-party dependency was added.

Before/after edge changes:

- Before this slice, several documented public APIs were available only through
  submodule imports even though the package root already exported many sibling
  objects.
- After this slice, PDF primitives/documents, extraction truth, table
  row/column/cell types, SVG flattening utilities, and `ZoningDrawing` are also
  available from the package root.
- Object identity is preserved; root exports alias the canonical submodule
  objects instead of wrapping or copying them.

Cycle/layer/coupling/redundancy result:

- Cycle check: no new runtime cycle is introduced.
- Layer check: `__init__.py` remains a pure public API aggregation layer.
- Coupling check: no feature code depends on package-root imports.
- Redundancy check: no duplicate implementation is added.

ADR/rule impact:

- No ADR is required. This implements the dependency-map rule that `__init__.py`
  re-exports public APIs and does not introduce behavior.

## Domain Definitions

- `InkGen.__all__` is the root public import allow-list.
- A root export must be bound, public, and identical to its canonical submodule
  object.
- Private names are not exported.
- This slice does not promise every internal helper is root-importable.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Bound `__all__` names | Every listed symbol exists on `InkGen` | PO-API-001 | `test_package_all_exports_are_bound_and_public` | mutation attempted |
| Documented root symbols | PDF, extraction truth, table row objects, SVG utilities, zoning recipe exported | PO-API-002 | `test_documented_public_symbols_are_exported_from_package_root` | mutation attempted |
| Identity preservation | Root aliases match submodule objects | PO-API-003 | `test_root_exports_match_submodule_identities` | mutation attempted |
| Dependent authoring path | Root-imported PDF classes generate valid bytes | PO-API-004 | `test_root_exports_work_in_pdf_authoring_path` | mutation attempted |
| Private leakage | No `__all__` name starts with `_` | PO-API-005 | `test_package_all_exports_are_bound_and_public` | mutation attempted |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | `__all__` and alias identity are deterministic. | PUBLIC-API-P1 tests |
| Behavioral/condition | yes | The slice defines package-root import behavior. | Tests are marked `@pytest.mark.condition("PUBLIC-API-P1")`. |
| Failure-mode | limited | Missing exports fail import or membership assertions. | documented-symbol missing set |
| Integration/live-path | yes | Root-imported PDF objects render a minimal PDF content stream. | PDF authoring test |
| Contract/API compatibility | yes | Existing submodule object identity is preserved. | identity assertions |
| Property/fuzz | no | The export set is finite and explicitly enumerated. | Not applicable |
| Mutation | attempted | Module-level imports may produce no meaningful mutation work items. | Result recorded below |
| Security/adversarial | no | No path, network, subprocess, archive, SQL, template, or active-content surface changed. | Not applicable |
| Performance/resource | no | Import aggregation only. | Not applicable |
| Concurrency/race | no | No shared mutable runtime state is added. | Not applicable |
| Golden artifact/visual | limited | Minimal PDF bytes prove root-imported objects work. | PDF byte/content assertion |
| Regression | yes | Prevents documented public symbols from silently dropping out of the root API. | PUBLIC-API-P1 tests |

## Mutation Testing Gate

Current result:

- Tool: Cosmic Ray 8.4.6.
- Environment: WSL Python 3.12 virtualenv.
- Raw work items: 0.
- Proof-critical work items after filter: 0.
- Result: not applicable. Cosmic Ray did not generate mutation work items for
  the module-level import bindings or `__all__` list in `src/InkGen/__init__.py`.
- Replacement evidence: focused PUBLIC-API-P1 tests directly exercise bound
  exports, documented symbol membership, canonical object identity, private-name
  exclusion, and a root-imported PDF authoring path.

## PO-API-001: `__all__` Names Are Bound And Public

### Claim

Every symbol listed in `InkGen.__all__` is bound on the package module and no
listed symbol is private.

### Domain

The finite `InkGen.__all__` list.

### Proof Method

The focused test asserts uniqueness, rejects leading underscores, and resolves
each listed symbol with `getattr(InkGen, name)`.

### Conclusion

Proven for the stated domain after focused tests pass. Mutation was attempted
and produced no applicable work items for this import/export-only module.

## PO-API-002: Documented Public Symbols Are Root Exported

### Claim

Documented public APIs for PDF generation, extraction truth, table row objects,
SVG flattening, and renderer-neutral zoning are available from `InkGen`.

### Domain

The documented finite symbol set named in `tests/test_public_api_contract.py`.

### Proof Method

The focused test compares the documented symbol set to `InkGen.__all__` and
checks each symbol is present on the module.

### Conclusion

Proven for the stated domain after focused tests pass. Mutation was attempted
and produced no applicable work items for this import/export-only module.

## PO-API-003: Root Exports Preserve Canonical Identity

### Claim

Root exports are aliases to canonical submodule objects.

### Domain

Representative public classes spanning PDF, extraction truth, and tables.

### Proof Method

The focused test imports each object from the root and its submodule and asserts
object identity with `is`.

### Conclusion

Proven for the stated domain after focused tests pass. Mutation was attempted
and produced no applicable work items for this import/export-only module.

## PO-API-004: Root Imports Work In A Dependent Authoring Path

### Claim

Root-imported PDF classes can build and render a minimal valid PDF document.

### Domain

`Canvas`, `DocumentPDF`, `ComponentGroupPDF`, `RectanglePDF`, and
`DrawingStyle` imported from the package root or canonical style module.

### Proof Method

The focused test builds one page, adds one rectangle, renders PDF bytes, and
asserts the PDF header plus rectangle operator.

### Conclusion

Proven for the stated domain after focused tests pass. Mutation was attempted
and produced no applicable work items for this import/export-only module.
