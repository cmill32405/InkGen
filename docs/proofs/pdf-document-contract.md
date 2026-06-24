# PDF Document Renderer Contract Proof Obligations

This note applies the InkGen Definition of Done to the PDF-DOC-P2 document
renderer traversal slice. It covers group traversal in rendered PDF bytes,
extraction truth, grammar truth when a layer contains repeated semantic labels,
and the public PDF file-writer path boundary.

## Scope

The slice covers:

- `DocumentPDF._iter_layer_groups()`
- `DocumentPDF._render_page_content()`
- `DocumentPDF.create_pdf()`
- `DocumentPDF.extraction_truth()`
- `DocumentPDF.grammar_truth()`

## Architecture Impact

Affected surface:

- `src/InkGen/pdf_generator.py`: PDF document traversal now reads the layer's
  stored groups rather than the lossy label lookup. The filepath hardening
  update also validates public PDF output paths before writing.
- `tests/test_pdf_document_contract.py`: PDF-DOC-P2 condition tests.
- `tests/mutation/pdf_document_cosmic_ray.toml`: scoped mutation gate.
- `tests/mutation/filter_pdf_document_work_items.py`: proof-critical mutation
  filter.
- `docs/proofs/pdf-document-contract.md`: proof note.

Incoming dependencies:

- Synthetic drawing workflows rely on `DocumentPDF.to_pdf_bytes()` rendering
  every group added to a page layer.
- Extraction-truth consumers rely on `DocumentPDF.extraction_truth()` including
  all annotated groups and components.
- Grammar-truth consumers rely on `DocumentPDF.grammar_truth()` including all
  annotated groups and components.
- `DocumentPDF` depends on `Layer` for group containment.

Outgoing dependencies:

- `DocumentPDF` consumes `Layer`, `Layers`, `ComponentGroupPDF`, PDF component
  renderers, extraction-truth helpers, and grammar-truth helpers.
- No dependency was added.

Before/after edge changes:

- Before this slice, PDF rendering and truth emission traversed
  `Layer.component_groups`, a label-to-id lookup. Repeated semantic labels
  collapse in that lookup, so only the last group for a label was rendered or
  emitted as truth.
- After this slice, `DocumentPDF` traverses `Layer._component_groups.values()`
  through one local helper, preserving every stored group.
- Render traversal preserves insertion order.
- Truth traversal sorts all stored groups by `(group_label, group_id)` before
  final truth-record sorting, preserving deterministic output.
- After the filepath hardening update, `DocumentPDF.create_pdf()` accepts string
  and path-like output paths and rejects non-path, bytes, empty, and
  missing-directory paths before writing.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced.
- Layer check: the fix remains inside the PDF renderer and does not alter the
  base `Layer` API.
- Coupling check: the renderer uses private layer storage only to recover an
  already-existing containment contract that the public label lookup cannot
  express.
- Redundancy check: traversal is centralized in `DocumentPDF._iter_layer_groups()`.

ADR/rule impact:

- No new ADR is required. The slice keeps renderer-specific traversal local to
  the renderer and does not add dependencies or change public serialization.

## Domain Definitions

- A layer may contain multiple groups with the same semantic `group_label`.
- `Layer.component_groups` is a label lookup and is not a complete group
  iterator when labels repeat.
- PDF rendering must emit every stored `ComponentGroupPDF` in insertion order.
- PDF truth outputs must inspect every stored group and every child component.
- Truth output must remain deterministic.
- PDF file output accepts string and path-like paths that resolve to existing
  directories and rejects malformed output path values.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Duplicate group labels in PDF render path | Preserve and render every group | PO-PDFDOC-001 | duplicate-label render test | killed |
| Distinct group insertion order | Preserve insertion order in PDF content | PO-PDFDOC-002 | render-order test | killed |
| Duplicate labels with extraction truth | Emit both annotated groups | PO-PDFDOC-003 | extraction-truth duplicate-label test | killed |
| Duplicate labels with grammar truth | Emit both annotated groups | PO-PDFDOC-004 | grammar-truth duplicate-label test | killed |
| PDF file writer path boundary | Accept string/path-like paths and reject malformed output paths before writing | PO-PDFDOC-005 | path-like and malformed-path tests | killed |
| Non-PDF group in a PDF page | Continue to fail loudly | Existing PDF generator test | killed |
| Private layer storage mutation | Excluded from public contract | Explicit exclusion | Not applicable |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | limited yes | The helper is private but deterministic. | Exercised through public PDF and truth paths |
| Behavioral/condition | yes | The slice defines PDF-DOC-P2 renderer behavior. | Tests are marked `@pytest.mark.condition("PDF-DOC-P2")`. |
| Failure-mode | yes | Existing non-PDF group failure and malformed output path failures must remain. | `test_document_pdf_rejects_non_pdf_child_in_standard_group`; filepath tests |
| Integration/live-path | yes | Rendering and truth emission cross document, layer, group, component, and truth helpers. | PDF/truth focused tests |
| Contract/API compatibility | yes | The `Layer` public lookup stays unchanged while PDF traversal becomes complete. | Existing PDF generator tests |
| Property/fuzz | no | The regression is a finite traversal partition. | Not applicable |
| Mutation | yes | Traversal branches are proof-critical. | Cosmic Ray result below |
| Security/adversarial | limited yes | The slice writes only explicit local paths and adds no subprocess, network, SQL, template, archive, or active-content handling. | filepath tests |
| Performance/resource | no | The helper creates a tuple of existing groups and optionally sorts for truth. | Not applicable |
| Concurrency/race | no | No shared concurrent state is added. | Not applicable |
| Golden artifact/visual | yes | PDF content stream is a generated artifact. | content-stream assertions |
| Regression | yes | This closes the duplicate-label traversal regression. | dedicated tests |

## Mutation Testing Gate

Current result:

- Tool: Cosmic Ray 8.4.6.
- Environment: WSL Python 3.12 virtualenv.
- Raw work items: 1955.
- Proof-critical work items after filter: 12.
- Killed mutants: 11.
- Equivalent survivors: 1.
- Surviving equivalent mutation:
  - `_iter_layer_groups()` line 835 changed the return type annotation from
    `tuple[ComponentGroup, ...]` to a mutated annotation form. Runtime behavior is
    unchanged because annotations are postponed by `from __future__ import
    annotations` and the function body is unchanged.
- Gate result: pass with documented equivalent survivor.

Current result after the filepath hardening update:

- Tool: Cosmic Ray 8.4.6.
- Environment: WSL Python 3.12 virtualenv.
- Config: `tests/mutation/pdf_document_cosmic_ray.toml`.
- Filter: `tests/mutation/filter_pdf_filepath_work_items.py`.
- Test selection: focused PDF document, PDF generator, extraction-truth, and
  grammar-truth tests.
- Raw work items: 1987.
- Proof-critical work items after filter: 7.
- Killed mutants: 7.
- Surviving mutants: 0.
- Gate result: pass.

## PO-PDFDOC-001: PDF Rendering Traverses Every Stored Group

### Claim

`DocumentPDF.to_pdf_bytes()` renders every stored group in each page layer, even
when semantic labels repeat.

### Proof Method

Tests add two `ComponentGroupPDF` objects with the same label and distinct
rectangles to one layer, render the document, and assert both rectangle
operators appear in the PDF content stream. Mutation kills traversal changes
that return only the label lookup behavior.

### Conclusion

Proven for repeated semantic labels in the declared PDF document domain.

## PO-PDFDOC-002: PDF Render Order Preserves Group Insertion

### Claim

PDF page content preserves layer group insertion order rather than sorting by
label during rendering.

### Proof Method

Tests add groups in reverse alphabetical label order and assert the content
stream emits the first inserted group's rectangle before the second.

### Conclusion

Proven for group render order in a layer.

## PO-PDFDOC-003: Extraction Truth Traverses Every Stored Group

### Claim

`DocumentPDF.extraction_truth()` emits annotations from every stored group when
semantic labels repeat.

### Proof Method

Tests annotate two same-label groups with different `instance_id` and `value`
fields and assert both records appear.

### Conclusion

Proven for repeated-label group annotations.

## PO-PDFDOC-004: Grammar Truth Traverses Every Stored Group

### Claim

`DocumentPDF.grammar_truth()` emits annotations from every stored group when
semantic labels repeat.

### Proof Method

Tests annotate two same-label groups with different `instance_id` and `value`
fields and assert both records appear.

### Conclusion

Proven for repeated-label grammar annotations.

## PO-PDFDOC-005: PDF File Writer Paths Are Validated

### Claim

`DocumentPDF.create_pdf()` accepts string and path-like output paths, rejects
malformed path values at the InkGen boundary, and preserves deterministic PDF
bytes.

### Proof Method

`DocumentPDF.create_pdf()` delegates to `_normalize_output_filepath()` before
opening the destination. The helper accepts string and path-like values through
`os.fspath()`, rejects non-path objects, bytes, and empty paths, preserves the
existing missing-directory `ValueError`, and returns an absolute path for the
byte write. Focused tests cover valid string and path-like writes, malformed
object/integer/bytes/empty paths, missing directories, and payload equality.

### Counterexamples And Exclusions

Filesystem permission errors, concurrent file replacement, and
platform-specific reserved path names remain delegated to the operating system.

### Conclusion

Proven for filesystem paths in the test environment.
