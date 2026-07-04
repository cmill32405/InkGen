# PDF Document Renderer Contract Proof Obligations

This note applies the InkGen Definition of Done to PDF document contract slices.
It covers group traversal in rendered PDF bytes, extraction truth, grammar truth
when a layer contains repeated semantic labels, the public PDF file-writer path
boundary, and PDF page-structure metadata.

## Scope

The slice covers:

- `DocumentPDF._iter_layer_groups()`
- `DocumentPDF._render_page_content()`
- `DocumentPDF.create_pdf()`
- `DocumentPDF.add_page()`
- `DocumentPDF.remove_page()`
- `DocumentPDF.set_page_label()`
- `DocumentPDF.page_label()`
- `DocumentPDF.set_page_box()`
- `DocumentPDF.page_box()`
- `DocumentPDF.to_pdf_bytes()`
- `DocumentPDF.create_from_dict()`
- `DocumentPDF.parameters`
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
- `tests/mutation/pdf_document_structure_cosmic_ray.toml`: scoped mutation gate
  for PDF-DOC-STRUCT-P3.
- `tests/mutation/filter_pdf_document_structure_work_items.py`: page-structure
  proof-critical mutation filter.
- `docs/proofs/pdf-document-contract.md`: proof note.
- `docs/adr/0003-pdf-page-structure-metadata.md`: accepted ADR for the
  page-label and page-box contract.

Incoming dependencies:

- Synthetic drawing workflows rely on `DocumentPDF.to_pdf_bytes()` rendering
  every group added to a page layer.
- Extraction-truth consumers rely on `DocumentPDF.extraction_truth()` including
  all annotated groups and components.
- Grammar-truth consumers rely on `DocumentPDF.grammar_truth()` including all
  annotated groups and components.
- `DocumentPDF` depends on `Layer` for group containment.
- Callers can depend on `DocumentPDF.set_page_label()` and
  `DocumentPDF.set_page_box()` for PDF-specific page metadata, and on
  `DocumentPDF.parameters` plus `DocumentPDF.create_from_dict()` to preserve that
  metadata.

Outgoing dependencies:

- `DocumentPDF` consumes `Layer`, `Layers`, `ComponentGroupPDF`, PDF component
  renderers, extraction-truth helpers, and grammar-truth helpers.
- No dependency was added.
- Page-structure metadata uses only local PDF dictionary serialization and the
  existing `Document` page model.

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
- After the page-structure update, `DocumentPDF` owns a PDF-specific metadata
  map keyed by one-based page number. Insertions and removals shift or delete
  metadata with the affected page indices. `to_pdf_bytes()` emits `/PageLabels`
  in the catalog and allowed page boxes in each page dictionary.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced.
- Layer check: the fix remains inside the PDF renderer and does not alter the
  base `Layer` API.
- Coupling check: the renderer uses private layer storage only to recover an
  already-existing containment contract that the public label lookup cannot
  express.
- Redundancy check: traversal is centralized in `DocumentPDF._iter_layer_groups()`.
- Page metadata is intentionally local to `DocumentPDF`; flow documents and
  renderer-neutral drawing components consume drawing primitives and do not own
  PDF page dictionary rendering.

ADR/rule impact:

- ADR-0003 records the page-structure metadata decision because this slice adds
  public API and serialized parameters.

## Domain Definitions

- A layer may contain multiple groups with the same semantic `group_label`.
- `Layer.component_groups` is a label lookup and is not a complete group
  iterator when labels repeat.
- PDF rendering must emit every stored `ComponentGroupPDF` in insertion order.
- PDF truth outputs must inspect every stored group and every child component.
- Truth output must remain deterministic.
- PDF file output accepts string and path-like paths that resolve to existing
  directories and rejects malformed output path values.
- PDF page labels are non-empty Latin-1 strings because the dependency-free
  backend currently emits literal PDF strings.
- PDF page boxes are finite four-number bottom-left coordinate rectangles with
  positive area inside the page MediaBox.
- Page-structure metadata is page-owned state and must follow page insertion and
  removal operations.
- Serialized page labels and page boxes must be rejected before rendering if they
  are malformed.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Duplicate group labels in PDF render path | Preserve and render every group | PO-PDFDOC-001 | duplicate-label render test | killed |
| Distinct group insertion order | Preserve insertion order in PDF content | PO-PDFDOC-002 | render-order test | killed |
| Duplicate labels with extraction truth | Emit both annotated groups | PO-PDFDOC-003 | extraction-truth duplicate-label test | killed |
| Duplicate labels with grammar truth | Emit both annotated groups | PO-PDFDOC-004 | grammar-truth duplicate-label test | killed |
| PDF file writer path boundary | Accept string/path-like paths and reject malformed output paths before writing | PO-PDFDOC-005 | path-like and malformed-path tests | killed |
| Page labels | Emit escaped PDF `/PageLabels`, preserve deterministic bytes, and round-trip through parameters | PO-PDFDOC-006 | page label and page box render/round-trip test | killed |
| Page boxes | Emit only allowed Crop/Bleed/Trim/Art boxes in bottom-left coordinates inside MediaBox | PO-PDFDOC-007 | page box render/invalid metadata tests | killed |
| Page metadata index shifts | Insert/remove pages shift or delete label/box metadata with the page index | PO-PDFDOC-008 | insertion/removal metadata tests | pass with equivalent survivors |
| Serialized page metadata | Reject malformed page label/page box payloads before rendering | PO-PDFDOC-009 | serialized metadata rejection test | killed |
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
| Serialized payload | yes | Page labels and boxes are persisted in document parameters. | render/round-trip and malformed-payload tests |

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

Current result after the page-structure metadata update:

- Tool: Cosmic Ray 8.4.6.
- Config: `tests/mutation/pdf_document_structure_cosmic_ray.toml`.
- Filter: `tests/mutation/filter_pdf_document_structure_work_items.py`.
- Test selection: focused PDF document, factory payload, and PDF generator tests.
- Raw work items: 3227.
- Proof-critical work items after filter: 216.
- Killed mutants: 213.
- Equivalent survivors: 3.
- Surviving equivalent mutations:
  - `DocumentPDF.add_page()` line 1539 changed `page_number >= 1` to
    `page_number >= 0`. `_validate_insert_position()` returns either `-1` for
    append or a positive one-based insertion index, and rejects `0`, so the
    predicate is equivalent over the validated domain.
  - `_shift_pdf_page_metadata_for_removal()` line 1596 changed the label-shift
    expression from `index > page_number` to `index >= page_number`. The
    comprehension filters `index != page_number` before evaluating the output
    expression, so equality is excluded from the expression domain.
  - `_shift_pdf_page_metadata_for_removal()` line 1599 made the same equivalent
    `>` to `>=` change for page boxes, with the same `index != page_number`
    pre-filter.
- Gate result: pass with documented equivalent survivors.

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

## PO-PDFDOC-006: PDF Page Labels Emit And Round Trip

### Claim

`DocumentPDF` emits explicit page labels in the PDF catalog, escapes literal
string characters, preserves deterministic bytes, and round-trips the labels
through `parameters` and `create_from_dict()`.

### Proof Method

`set_page_label()` validates that labels are non-empty Latin-1 strings for the
current literal-string backend. `_page_label_dictionary()` sorts one-based page
numbers, converts them to zero-based PDF page indices, and escapes backslashes
and parentheses through `_escape_pdf_string()`. The behavioral test renders two
labels, checks the exact `/PageLabels` bytes, checks deterministic repeated
rendering, recreates the document from `parameters`, and checks byte and
parameter equality.

### Counterexamples And Exclusions

Full Unicode page labels are excluded until the PDF backend supports UTF-16BE or
another explicit Unicode PDF string encoding policy.

### Conclusion

Proven for Latin-1 labels in the declared PDF document domain.

## PO-PDFDOC-007: PDF Page Boxes Are Bounded Metadata

### Claim

`DocumentPDF` emits only `/CropBox`, `/BleedBox`, `/TrimBox`, and `/ArtBox`
entries, and every emitted page box is a finite positive-area rectangle inside
the page MediaBox.

### Proof Method

`set_page_box()` validates the page number, canonicalizes the box name through
`_coerce_pdf_page_box_name()`, and validates the four-coordinate rectangle
through `_coerce_pdf_page_box()` against the target page canvas. The behavioral
tests check exact emitted `/CropBox` and `/TrimBox` bytes, name aliases with and
without a leading slash, non-string and unsupported names, non-sequence boxes,
wrong length, boolean coordinates, NaN, zero-area, negative, and over-MediaBox
coordinates.

### Counterexamples And Exclusions

The backend does not enforce semantic relationships among page boxes, such as a
TrimBox being inside a BleedBox. It enforces only the PDF dictionary key set,
finite coordinates, positive area, and MediaBox containment.

### Conclusion

Proven for the declared page-box key and coordinate domain.

## PO-PDFDOC-008: Page Metadata Follows Page Index Mutations

### Claim

When pages are inserted or removed, explicit PDF page labels and page boxes stay
attached to the same logical page position after the mutation, and metadata for
a removed page is deleted.

### Proof Method

`DocumentPDF.add_page()` validates the target insertion position, shifts metadata
for page indices greater than or equal to the insertion point, and then delegates
to `Document.add_page()`. `DocumentPDF.remove_page()` validates the existing page
number, delegates to `Document.remove_page()`, then deletes metadata for the
removed page and shifts later entries down. The behavioral test sets metadata on
the tail page, inserts before it, removes before it, and then removes the tagged
page while checking labels, boxes, page count, and serialized absence.

### Conclusion

Proven for page indices admitted by the `DocumentPDF` public page mutation
methods, with the three equivalent mutation survivors documented above.

## PO-PDFDOC-009: Serialized Page Metadata Fails Explicitly

### Claim

Malformed serialized `page_labels` and `page_boxes` payloads are rejected during
`DocumentPDF.create_from_dict()` before any rendered PDF can be produced from
bad page-structure metadata.

### Proof Method

`create_from_dict()` reads optional mappings through `_pdf_optional_mapping()`,
normalizes page keys through `_pdf_page_number_key()`, requires per-page box
entries to be mappings, and then delegates to `set_page_label()` and
`set_page_box()` for the same public boundary validation. Tests mutate a valid
payload into non-mapping page label/page box containers, invalid page numbers,
empty labels, unsupported box names, and invalid box coordinates.

### Conclusion

Proven for serialized page labels and page boxes in the declared payload domain.
