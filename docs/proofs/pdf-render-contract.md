# PDF Render Guard Contract Proof Obligations

This note applies the InkGen Definition of Done to the PDF-GUARD-P3 render
contract guard slice. It covers the helper module that keeps `DocumentPDF` and
`ComponentGroupPDF` inside the closed renderer domain required by ADR-0002.

## Scope

The slice covers:

- `ensure_builtin_pdf_component()`
- `ensure_pdf_group()`
- The `ComponentGroupPDF.add_component()` and `ComponentGroupPDF.generate_pdf()`
  dependent guard paths.
- The `DocumentPDF.to_pdf_bytes()` live group guard path.

## Architecture Impact

Affected surface:

- `src/InkGen/pdf_render_contract.py`: closed-domain guard behavior.
- `tests/test_pdf_render_contract.py`: PDF-GUARD-P3 condition tests.
- `tests/mutation/pdf_render_contract_cosmic_ray.toml`: scoped mutation gate.
- `tests/mutation/filter_pdf_render_contract_work_items.py`: proof-critical
  mutation filter.
- `docs/proofs/pdf-render-contract.md`: proof note.

Incoming dependencies:

- `ComponentGroupPDF.add_component()` uses `ensure_builtin_pdf_component()`.
- `ComponentGroupPDF.generate_pdf()` repeats `ensure_builtin_pdf_component()`
  before rendering.
- `DocumentPDF._render_page_content()` uses `ensure_pdf_group()` before calling
  `group.generate_pdf()`.
- ADR-0002 requires the PDF renderer to reject arbitrary dynamic
  `generate_pdf()` extension.

Outgoing dependencies:

- The guard module depends only on `Component`.
- No renderer, document, style, or third-party dependency was added to the guard
  module.

Before/after edge changes:

- Before this slice, `ensure_pdf_group()` used `isinstance()`, so a
  `ComponentGroupPDF` subclass overriding `generate_pdf()` passed the
  document-level guard.
- After this slice, both component and group guards use exact type matching for
  the closed renderer domain.
- Existing exact `ComponentGroupPDF` and built-in primitive render paths remain
  supported.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced.
- Layer check: guard policy remains in `pdf_render_contract.py`; renderer code
  consumes it.
- Coupling check: renderer code remains coupled to a small proof-critical guard
  module rather than duplicating checks.
- Redundancy check: duplicate guard calls intentionally defend both public add
  paths and private mutation render paths.

ADR/rule impact:

- This slice reinforces ADR-0002. It does not introduce a new ADR.

## Domain Definitions

- Built-in PDF primitive components are accepted only when `type(component)` is
  one of the allowed built-in classes.
- Custom subclasses of built-in PDF primitive components are outside the proven
  renderer domain.
- PDF document groups are accepted only when `type(group) is ComponentGroupPDF`.
- Custom subclasses of `ComponentGroupPDF` are outside the proven renderer
  domain because they can override `generate_pdf()`.
- Guard diagnostics are supplied by callers through a keyword-only `message`.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Exact built-in primitive | Accepted | PO-PDFGUARD-001 | `test_builtin_pdf_component_guard_accepts_exact_allowed_type` | mutation gate |
| Primitive subclass | Rejected with caller message | PO-PDFGUARD-002 | `test_builtin_pdf_component_guard_rejects_subclasses_and_preserves_message` | mutation gate |
| Exact `ComponentGroupPDF` | Accepted | PO-PDFGUARD-003 | `test_pdf_group_guard_accepts_exact_component_group_type` | mutation gate |
| Standard group and PDF group subclass | Rejected with caller message | PO-PDFGUARD-004 | `test_pdf_group_guard_rejects_standard_groups_and_pdf_subclasses` | mutation gate |
| Document live path | Rejects custom group subclass before custom render code runs | PO-PDFGUARD-005 | `test_pdf_document_live_path_rejects_custom_group_subclass` | mutation gate |
| Diagnostic API | `message` remains keyword-only | PO-PDFGUARD-006 | `test_pdf_render_contract_helpers_keep_keyword_only_message` | mutation gate |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Guard functions are deterministic pure checks. | PDF-GUARD-P3 helper tests |
| Behavioral/condition | yes | The slice defines PDF-GUARD-P3 closed-domain behavior. | Tests are marked `@pytest.mark.condition("PDF-GUARD-P3")`. |
| Failure-mode | yes | Unsupported components/groups must fail before rendering. | subclass and standard group rejection tests |
| Integration/live-path | yes | `DocumentPDF.to_pdf_bytes()` must consume the group guard. | live custom group rejection test |
| Contract/API compatibility | yes | Exact built-in components and exact `ComponentGroupPDF` still work. | acceptance tests plus existing PDF generator tests |
| Property/fuzz | no | The closed type set is finite and explicit. | Not applicable |
| Mutation | yes | Guard branch operators are proof-critical. | Cosmic Ray result recorded below |
| Security/adversarial | limited | The guard prevents arbitrary custom render code from entering the proven path. | custom `generate_pdf()` group subclass rejected |
| Performance/resource | no | Constant-time type checks. | Not applicable |
| Concurrency/race | no | No shared state is changed. | Not applicable |
| Golden artifact/visual | covered by dependents | Existing PDF tests cover generated bytes. | `tests/test_pdf_generator.py` |
| Regression | yes | Prevents bypassing the ADR-0002 closed renderer with subclasses. | PDF-GUARD-P3 tests |

## Mutation Testing Gate

Current result:

- Tool: Cosmic Ray 8.4.6.
- Environment: WSL Python 3.12 virtualenv.
- Raw work items: 24.
- Proof-critical work items after filter: 2.
- Killed mutants: 2.
- Surviving mutants: 0.

## PO-PDFGUARD-001: Exact Built-In Components Are Accepted

### Claim

`ensure_builtin_pdf_component()` accepts exact instances of allowed built-in PDF
component classes.

### Domain

Public guard calls with `type(component)` present in `allowed_types`.

### Proof Method

The focused test calls the guard with an exact `RectanglePDF` and an allowed
tuple containing `RectanglePDF`.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-PDFGUARD-002: Primitive Subclasses Are Rejected

### Claim

`ensure_builtin_pdf_component()` rejects custom subclasses even when their base
class is allowed.

### Domain

Custom subclasses of built-in PDF primitive classes.

### Proof Method

The guard compares exact `type(component)` against the allowed tuple. The
focused test passes a `CustomRectanglePDF` where only `RectanglePDF` is allowed
and asserts the caller diagnostic message.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-PDFGUARD-003: Exact PDF Groups Are Accepted

### Claim

`ensure_pdf_group()` accepts exact `ComponentGroupPDF` instances.

### Domain

Public guard calls with `type(group) is ComponentGroupPDF`.

### Proof Method

The focused test calls the guard with an exact `ComponentGroupPDF`.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-PDFGUARD-004: Non-Exact Groups Are Rejected

### Claim

`ensure_pdf_group()` rejects both standard `ComponentGroup` instances and
custom `ComponentGroupPDF` subclasses.

### Domain

Non-PDF groups and custom subclasses of `ComponentGroupPDF`.

### Proof Method

The guard uses exact type identity. The focused test covers both a standard
group and a custom subclass with a caller diagnostic message.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-PDFGUARD-005: DocumentPDF Consumes The Group Guard

### Claim

`DocumentPDF.to_pdf_bytes()` rejects a custom group subclass before any custom
`generate_pdf()` operators enter the PDF content stream.

### Domain

Document pages populated through public `Layer.add_component_group()` with a
custom `ComponentGroupPDF` subclass.

### Proof Method

The focused live-path test adds a custom group subclass whose `generate_pdf()`
returns custom operators, then asserts `DocumentPDF.to_pdf_bytes()` raises the
document guard error.

### Conclusion

Proven for the stated domain after tests and mutation pass.
