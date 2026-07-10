# PDF Document Renderer Contract Proof Obligations

This note applies the InkGen Definition of Done to PDF document contract slices.
It covers group traversal in rendered PDF bytes, extraction truth, grammar truth
when a layer contains repeated semantic labels, the public PDF file-writer path
boundary, PDF page-structure metadata, flat/nested PDF outlines/bookmarks, URI
link annotations, internal page link annotations, named destinations, text
annotations, highlight annotations, square annotations, and circle annotations.

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
- `DocumentPDF.add_outline()`
- `DocumentPDF.clear_outlines()`
- `DocumentPDF.outlines()`
- `DocumentPDF.add_uri_link()`
- `DocumentPDF.clear_uri_links()`
- `DocumentPDF.uri_links()`
- `DocumentPDF.add_page_link()`
- `DocumentPDF.clear_page_links()`
- `DocumentPDF.page_links()`
- `DocumentPDF.add_named_destination()`
- `DocumentPDF.clear_named_destinations()`
- `DocumentPDF.named_destinations()`
- `DocumentPDF.add_named_destination_link()`
- `DocumentPDF.clear_named_destination_links()`
- `DocumentPDF.named_destination_links()`
- `DocumentPDF.add_text_annotation()`
- `DocumentPDF.clear_text_annotations()`
- `DocumentPDF.text_annotations()`
- `DocumentPDF.add_highlight_annotation()`
- `DocumentPDF.clear_highlight_annotations()`
- `DocumentPDF.highlight_annotations()`
- `DocumentPDF.add_square_annotation()`
- `DocumentPDF.clear_square_annotations()`
- `DocumentPDF.square_annotations()`
- `DocumentPDF.add_circle_annotation()`
- `DocumentPDF.clear_circle_annotations()`
- `DocumentPDF.circle_annotations()`
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
- `docs/adr/0004-pdf-flat-outlines.md`: accepted ADR for the flat outline
  contract.
- `docs/adr/0005-pdf-uri-link-annotations.md`: accepted ADR for the URI link
  annotation contract.
- `docs/adr/0006-pdf-internal-page-links.md`: accepted ADR for the internal
  page link annotation contract.
- `docs/adr/0007-pdf-named-destinations.md`: accepted ADR for the named
  destination contract.
- `docs/adr/0008-pdf-nested-outlines.md`: accepted ADR for the one-level nested
  outline contract.
- `docs/adr/0009-pdf-text-annotations.md`: accepted ADR for the text annotation
  contract.
- `docs/adr/0010-pdf-outline-expansion-state.md`: accepted ADR for the outline
  expansion-state contract.
- `docs/adr/0011-pdf-deep-outline-trees.md`: accepted ADR for the arbitrary-depth
  outline tree contract.
- `docs/adr/0013-pdf-highlight-annotations.md`: accepted ADR for the highlight
  annotation contract.
- `docs/adr/0016-pdf-square-annotations.md`: accepted ADR for the square
  annotation contract.
- `docs/adr/0019-pdf-circle-annotations.md`: accepted ADR for the circle
  annotation contract.

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
- Callers can depend on `DocumentPDF.add_outline()` to create top-level or
  arbitrary-depth child PDF outline entries that target existing pages, and on
  serialization to preserve target, parent, and expansion state.
- Callers can depend on `DocumentPDF.add_uri_link()` to create PDF URI link
  annotations on existing pages, and on serialization to preserve them.
- Callers can depend on `DocumentPDF.add_page_link()` to create internal PDF page
  link annotations from one existing page to another, and on serialization to
  preserve them.
- Callers can depend on `DocumentPDF.add_named_destination()` to create named
  page destinations and on `DocumentPDF.add_named_destination_link()` to create
  link annotations targeting those destinations.
- Callers can depend on `DocumentPDF.add_text_annotation()` to create PDF text
  annotations on existing pages, and on serialization to preserve them.
- Callers can depend on `DocumentPDF.add_highlight_annotation()` to create PDF
  highlight annotations on existing pages, and on serialization to preserve
  them.
- Callers can depend on `DocumentPDF.add_square_annotation()` to create PDF
  square annotations on existing pages, and on serialization to preserve them.
- Callers can depend on `DocumentPDF.add_circle_annotation()` to create PDF
  circle annotations on existing pages, and on serialization to preserve them.

Outgoing dependencies:

- `DocumentPDF` consumes `Layer`, `Layers`, `ComponentGroupPDF`, PDF component
  renderers, extraction-truth helpers, and grammar-truth helpers.
- No dependency was added.
- Page-structure metadata uses only local PDF dictionary serialization and the
  existing `Document` page model.
- Outlines use the same local PDF object writer, existing page-number
  validation, literal string escaping, strict boolean validation, and `/XYZ`
  destination number validation; no dependency was added.
- URI link annotations use the same local PDF object writer, existing page-number
  validation, and the page-box rectangle validator; no dependency was added.
- Internal page link annotations use the same local PDF object writer, existing
  page-number validation, page-box rectangle validator, and `/XYZ` destination
  number validation; no dependency was added.
- Named destinations and named-destination links use the same local PDF object
  writer, existing page-number validation, page-box rectangle validator, literal
  string escaping, and `/XYZ` destination number validation; no dependency was
  added.
- Text annotations use the same local PDF object writer, existing page-number
  validation, page-box rectangle validator, literal string escaping, and strict
  boolean validation; no dependency was added.
- Highlight annotations use the same local PDF object writer, existing
  page-number validation, page-box rectangle validator, literal string escaping,
  and local RGB color validation; no dependency was added.
- Square annotations use the same local PDF object writer, existing page-number
  validation, page-box rectangle validator, literal string escaping, and local
  RGB color validation; no dependency was added.
- Circle annotations use the same local PDF object writer, existing page-number
  validation, page-box rectangle validator, literal string escaping, and local
  RGB color validation; no dependency was added.

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
- After the outline update, `DocumentPDF` owns a flat ordered outline list.
  Insertions and removals shift or delete outline targets with affected page
  indices. `to_pdf_bytes()` emits a PDF `/Outlines` root, linked flat item
  objects, `/Dest` arrays, and `/PageMode /UseOutlines` in the catalog.
- After the nested outline update, `DocumentPDF.add_outline(parent=...)` added
  title-based child outline relationships.
  Insertions and removals preserve parent metadata and prune orphan children when
  their parent outline is removed. `to_pdf_bytes()` emits deterministic
  root-level links, parent child links, child sibling links, and item `/Dest`
  arrays.
- After the outline expansion update, `DocumentPDF.add_outline(expanded=...)`
  stores strict boolean expansion state. Insertions and removals preserve the
  flag. `to_pdf_bytes()` emits positive descendant `/Count` values for expanded
  parents and negative descendant `/Count` values for collapsed parents.
- After the deep outline update, parent lookup spans all existing outlines and
  still requires exactly one matching title. `to_pdf_bytes()` emits recursive
  parent, sibling, and child links at every depth, and parent `/Count` magnitude
  is the number of descendant outline items.
- After the URI link update, `DocumentPDF` owns a flat ordered URI link list.
  Insertions and removals shift or delete link page targets with affected page
  indices. `to_pdf_bytes()` emits page `/Annots` arrays and `/Subtype /Link`
  annotation objects with URI actions.
- After the internal page link update, `DocumentPDF` owns a flat ordered page
  link list. Insertions and removals shift or delete both source pages and target
  pages with affected page indices. `to_pdf_bytes()` performs two-pass page
  object allocation so internal link annotations can target later page objects,
  then emits page `/Annots` arrays and `/Subtype /Link` annotation objects with
  direct `/Dest` arrays.
- After the named destination update, `DocumentPDF` owns a named destination map
  and a flat ordered named-destination link list. Insertions and removals shift
  or delete destination page targets and link source pages. `to_pdf_bytes()`
  emits the catalog `/Names` dictionary with a `/Dests` name array and emits
  `/Subtype /Link` annotations with literal-string `/Dest` names.
- After the text annotation update, `DocumentPDF` owns a flat ordered text
  annotation list. Insertions and removals shift or delete annotation source
  pages. `to_pdf_bytes()` emits `/Subtype /Text` annotation objects in page
  `/Annots` arrays after URI, internal page, and named-destination links.
- After the highlight annotation update, `DocumentPDF` owns a flat ordered
  highlight annotation list. Insertions and removals shift or delete annotation
  source pages. `to_pdf_bytes()` emits `/Subtype /Highlight` annotation objects
  in page `/Annots` arrays after text annotations.
- After the square annotation update, `DocumentPDF` owns a flat ordered square
  annotation list. Insertions and removals shift or delete annotation source
  pages. `to_pdf_bytes()` emits `/Subtype /Square` annotation objects in page
  `/Annots` arrays after highlight annotations.
- After the circle annotation update, `DocumentPDF` owns a flat ordered circle
  annotation list. Insertions and removals shift or delete annotation source
  pages. `to_pdf_bytes()` emits `/Subtype /Circle` annotation objects in page
  `/Annots` arrays after square annotations.

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
- Outline metadata is also local to `DocumentPDF`; arbitrary-depth hierarchy
  semantics use the existing flat serialized outline list and title-based parent
  references.
- Outline expansion state applies at every outline depth; the PDF `/Count`
  magnitude is computed from recursive descendants.
- URI link metadata is local to `DocumentPDF`; generic annotations and richer
  annotation appearances remain deferred until there is a concrete fixture need.
- Internal page link metadata is local to `DocumentPDF`; generic annotations and
  richer annotation appearances remain deferred until there is a concrete
  fixture need.
- Named destination metadata is local to `DocumentPDF`; generic non-text
  annotations, tagged PDF, and richer annotation appearances remain deferred
  until there is a concrete fixture need.
- Text, highlight, square, and circle annotation metadata is local to `DocumentPDF`;
  file attachments, stamps, widgets, replies, rich appearances, fill colors,
  and other annotation subtypes remain deferred until there is a concrete
  fixture need.

ADR/rule impact:

- ADR-0003 records the page-structure metadata decision because this slice adds
  public API and serialized parameters.
- ADR-0004 records the flat outline decision because this slice adds public API
  and serialized parameters.
- ADR-0005 records the URI link annotation decision because this slice adds
  public API and serialized parameters.
- ADR-0006 records the internal page link decision because this slice adds
  public API and serialized parameters.
- ADR-0007 records the named destination decision because this slice adds public
  API and serialized parameters.
- ADR-0008 records the nested outline decision because this slice extends public
  API and serialized parameters.
- ADR-0009 records the text annotation decision because this slice adds public
  API and serialized parameters.
- ADR-0010 records the outline expansion-state decision because this slice
  extends public API and serialized parameters.
- ADR-0011 records the deep outline decision because this slice extends public
  outline hierarchy semantics without changing the serialized payload shape.
- ADR-0013 records the highlight annotation decision because this slice adds
  public API and serialized parameters.
- ADR-0016 records the square annotation decision because this slice adds public
  API and serialized parameters.
- ADR-0019 records the circle annotation decision because this slice adds public
  API and serialized parameters.

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
- PDF outlines are insertion-ordered entries. Each entry has a non-empty
  Latin-1 title, targets an existing one-based page number, and has finite
  destination numbers when `left`, `top`, or `zoom` are provided.
- A child outline may name one earlier unique parent at any depth by exact title
  value. Duplicate flat titles remain valid until the duplicate title is used as
  a parent, at which point the parent reference is rejected as ambiguous.
- Outline `expanded` state is a strict boolean. Expanded outlines are the
  default and omit `expanded` from serialized payloads. Collapsed outlines store
  `expanded: false` and emit negative descendant `/Count` values when they have
  children.
- Omitted outline `top` and `zoom` values emit PDF `null` destination tokens.
- Serialized outline entries must be rejected before rendering if malformed.
- PDF URI link annotations are flat, insertion-ordered entries. Each entry has a
  non-empty Latin-1 URI string, targets an existing one-based page number, and
  owns a finite positive-area rectangle inside the target page MediaBox.
- Page `/Annots` arrays must include every URI link on that page in insertion
  order.
- Serialized URI link entries must be rejected before rendering if malformed.
- PDF internal page link annotations are flat, insertion-ordered entries. Each
  entry has an existing one-based source page number, an existing one-based
  target page number, a finite positive-area rectangle inside the source page
  MediaBox, and finite `/XYZ` destination numbers when provided.
- Page `/Annots` arrays must include every internal page link on that page after
  any URI links on that page.
- Serialized internal page link entries must be rejected before rendering if
  malformed.
- PDF named destinations are unique non-empty Latin-1 names targeting existing
  one-based page numbers with finite `/XYZ` destination numbers when provided.
- Named destinations emit in deterministic name order in the catalog `/Names`
  dictionary.
- Named destination link annotations target existing destination names and use a
  finite positive-area rectangle inside the source page MediaBox.
- Serialized named destinations and named destination links must be rejected
  before rendering if malformed.
- PDF text annotations are flat, insertion-ordered entries. Each entry has an
  existing one-based page number, a finite positive-area rectangle inside the
  page MediaBox, non-empty Latin-1 contents, optional non-empty Latin-1 title,
  and a strict boolean open state.
- Page `/Annots` arrays must include every text annotation on that page after
  URI links, internal page links, and named-destination links on that page.
- Serialized text annotation entries must be rejected before rendering if
  malformed.
- PDF highlight annotations are flat, insertion-ordered entries. Each entry has
  an existing one-based page number, a finite positive-area rectangle inside the
  page MediaBox, a strict RGB color accepted as a `#rrggbb` string or serialized
  0.0-1.0 numeric triple, and optional non-empty Latin-1 contents.
- Page `/Annots` arrays must include every highlight annotation on that page
  after URI links, internal page links, named-destination links, and text
  annotations on that page.
- Highlight `/QuadPoints` must be derived deterministically from the annotation
  rectangle and must stay inside the same rectangle.
- Serialized highlight annotation entries must be rejected before rendering if
  malformed.
- PDF square annotations are flat, insertion-ordered entries. Each entry has an
  existing one-based page number, a finite positive-area rectangle inside the
  page MediaBox, a strict RGB border color accepted as a `#rrggbb` string or
  serialized 0.0-1.0 numeric triple, and optional non-empty Latin-1 contents.
- Page `/Annots` arrays must include every square annotation on that page after
  URI links, internal page links, named-destination links, text annotations, and
  highlight annotations on that page.
- Square annotations emit a deterministic `/Border [0 0 1]` contract.
- Serialized square annotation entries must be rejected before rendering if
  malformed.

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
| Flat outlines | Emit deterministic flat `/Outlines` root and linked item objects | PO-PDFDOC-010 | outline render/round-trip test | mutation target |
| Outline target index shifts | Insert/remove pages shift or delete outline targets with page indices | PO-PDFDOC-011 | outline page mutation test | mutation target |
| Serialized outline metadata | Reject malformed outline payloads before rendering | PO-PDFDOC-012 | serialized outline rejection test | mutation target |
| Nested outlines | Emit deterministic outline child chains and prune orphaned children | PO-PDFDOC-022 | nested outline render/round-trip and page mutation tests | mutation target |
| Nested outline parent validation | Reject missing, ambiguous, non-Latin-1, and non-string parents | PO-PDFDOC-023 | invalid parent and serialized parent tests | mutation target |
| Nested outline serialization | Preserve child parent metadata through parameters and hydration | PO-PDFDOC-024 | nested outline round-trip test | mutation target |
| Outline expansion state | Emit positive child counts for expanded parents and negative child counts for collapsed parents | PO-PDFDOC-028 | collapsed outline render/round-trip test | mutation target |
| Outline expansion page shifts | Insert/remove pages preserve expansion state while shifting outline targets | PO-PDFDOC-029 | outline page mutation test | mutation target |
| Serialized outline expansion state | Reject non-boolean expansion state and default missing values to expanded | PO-PDFDOC-030 | invalid serialized expanded test | mutation target |
| Deep outline trees | Emit recursive parent, sibling, and child links at every depth | PO-PDFDOC-031 | deep outline render/round-trip test | mutation target |
| Deep outline parent ambiguity | Reject ambiguous deep parent references before rendering | PO-PDFDOC-032 | invalid deep parent tests | mutation target |
| Deep outline orphan pruning | Remove descendants whose parent chain no longer resolves | PO-PDFDOC-033 | deep page removal test | mutation target |
| URI link annotations | Emit deterministic page `/Annots` arrays and `/Subtype /Link` URI action objects | PO-PDFDOC-013 | URI link render/round-trip test | mutation target |
| URI link target index shifts | Insert/remove pages shift or delete URI link page targets with page indices | PO-PDFDOC-014 | URI link page mutation test | mutation target |
| Serialized URI link metadata | Reject malformed URI link payloads before rendering | PO-PDFDOC-015 | serialized URI link rejection test | mutation target |
| Internal page link annotations | Emit deterministic page `/Annots` arrays and `/Subtype /Link` destination objects | PO-PDFDOC-016 | page link render/round-trip test | mutation target |
| Internal page link source/target index shifts | Insert/remove pages shift or delete page link source and target pages with page indices | PO-PDFDOC-017 | page link page mutation test | mutation target |
| Serialized internal page link metadata | Reject malformed page link payloads before rendering | PO-PDFDOC-018 | serialized page link rejection test | mutation target |
| Named destinations | Emit deterministic catalog `/Names` `/Dests` arrays and named-destination links | PO-PDFDOC-019 | named destination render/round-trip test | mutation target |
| Named destination page/index shifts | Insert/remove pages shift or delete destination targets and named-link source pages | PO-PDFDOC-020 | named destination page mutation test | mutation target |
| Serialized named destination metadata | Reject malformed named destination payloads before rendering | PO-PDFDOC-021 | serialized named destination rejection test | mutation target |
| Text annotations | Emit deterministic `/Subtype /Text` annotation objects and round-trip through parameters | PO-PDFDOC-025 | text annotation render/round-trip test | mutation target |
| Text annotation page/index shifts | Insert/remove pages shift or delete text annotation pages with page indices | PO-PDFDOC-026 | text annotation page mutation test | mutation target |
| Serialized text annotation metadata | Reject malformed text annotation payloads before rendering | PO-PDFDOC-027 | serialized text annotation rejection test | mutation target |
| Highlight annotations | Emit deterministic `/Subtype /Highlight` annotation objects and round-trip through parameters | PO-PDFDOC-034 | highlight annotation render/round-trip test | mutation target |
| Highlight annotation page/index shifts | Insert/remove pages shift or delete highlight annotation pages with page indices | PO-PDFDOC-035 | highlight annotation page mutation test | mutation target |
| Serialized highlight annotation metadata | Reject malformed highlight annotation payloads before rendering | PO-PDFDOC-036 | serialized highlight annotation rejection test | mutation target |
| Square annotations | Emit deterministic `/Subtype /Square` annotation objects and round-trip through parameters | PO-PDFDOC-037 | square annotation render/round-trip test | mutation target |
| Square annotation page/index shifts | Insert/remove pages shift or delete square annotation pages with page indices | PO-PDFDOC-038 | square annotation page mutation test | mutation target |
| Serialized square annotation metadata | Reject malformed square annotation payloads before rendering | PO-PDFDOC-039 | serialized square annotation rejection test | mutation target |
| Circle annotations | Emit deterministic `/Subtype /Circle` annotation objects and round-trip through parameters | PO-PDFDOC-040 | circle annotation render/round-trip test | pass with equivalent survivors |
| Circle annotation page/index shifts | Insert/remove pages shift or delete circle annotation pages with page indices | PO-PDFDOC-041 | circle annotation page mutation test | pass with equivalent survivors |
| Serialized circle annotation metadata | Reject malformed circle annotation payloads before rendering | PO-PDFDOC-042 | serialized circle annotation rejection test | pass with equivalent survivors |
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
| Navigation metadata | yes | Flat/nested PDF outlines, URI links, internal page links, named destinations, text annotations, highlight annotations, square annotations, and circle annotations add document navigation/comment objects and page annotation arrays. | outline, URI link, page link, named destination, text annotation, highlight annotation, square annotation, and circle annotation render/round-trip tests |

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

Current result after the flat outline update:

- Tool: Cosmic Ray 8.4.6.
- Config: `tests/mutation/pdf_document_outline_cosmic_ray.toml`.
- Filter: `tests/mutation/filter_pdf_document_outline_work_items.py`.
- Test selection: focused PDF document, factory payload, and PDF generator tests.
- Raw work items: 3524.
- Proof-critical work items after filter: 136.
- Killed mutants: 132.
- Equivalent survivors: 4.
- Surviving equivalent mutations:
  - `_shift_pdf_page_metadata_for_removal()` line 1681 changed
    `outline.page_number > page_number` to `>=`. The comprehension filters
    `outline.page_number != page_number` before evaluating the output
    expression, so equality is excluded from the expression domain.
  - `_outline_objects()` line 1732 changed `zip(..., strict=True)` to
    `strict=False`. `outline_item_ids` is constructed from
    `len(self._pdf_outlines)`, so it has exactly the same length as the outline
    sequence passed into `_outline_objects()`.
  - `_outline_objects()` line 1733 changed `index > 0` to `index != 0`.
    `enumerate()` produces non-negative integer indices only, so the predicates
    are equivalent for every loop iteration.
  - `_outline_objects()` line 1734 changed `index + 1 < len(outline_item_ids)`
    to `index + 1 != len(outline_item_ids)`. In the loop domain,
    `index + 1 <= len(outline_item_ids)` always holds, so `< len` and
    `!= len` are equivalent.
- Gate result: pass with documented equivalent survivors.

Current result after the URI link annotation update:

- Tool: Cosmic Ray 8.4.6.
- Config: `tests/mutation/pdf_document_uri_link_cosmic_ray.toml`.
- Filter: `tests/mutation/filter_pdf_document_uri_link_work_items.py`.
- Test selection: focused PDF document, factory payload, and PDF generator tests.
- Raw work items: 3660.
- Proof-critical work items after filter: 79.
- Killed mutants: 76.
- Equivalent survivors: 3.
- Surviving equivalent mutations:
  - `_coerce_pdf_link_rect()` line 401 changed the parameter separator from
    keyword-only `*` to positional-only `/` for `rect`. Public callers pass
    `rect` positionally and `canvas_width`/`canvas_height` by keyword, so the
    public `DocumentPDF.add_uri_link()` domain is unchanged.
  - `_shift_pdf_page_metadata_for_removal()` line 1748 changed
    `link.page_number > page_number` to `>=`. The comprehension filters
    `link.page_number != page_number` before evaluating the output expression,
    so equality is excluded from the expression domain.
  - `to_pdf_bytes()` line 1982 changed `zip(..., strict=True)` to
    `strict=False`. `annotation_ids` is constructed from `len(page_annotations)`,
    so it has exactly the same length as the annotation sequence.
- Gate result: pass with documented equivalent survivors.

Current result after the internal page link annotation update:

- Tool: Cosmic Ray 8.4.6.
- Config: `tests/mutation/pdf_document_page_link_cosmic_ray.toml`.
- Filter: `tests/mutation/filter_pdf_document_page_link_work_items.py`.
- Test selection: focused PDF document, factory payload, and PDF generator tests.
- Raw work items: 3881.
- Proof-critical work items after filter: 134.
- Killed mutants: 128.
- Equivalent survivors: 6.
- Surviving equivalent mutations:
  - `_coerce_pdf_destination_number()` line 381 changed the separator before
    `owner` from keyword-only `*` to positional-only `/` for `value` and `name`.
    Public callers pass `value` and `name` positionally and `owner` by keyword,
    so the public `DocumentPDF.add_page_link()` domain is unchanged.
  - `_coerce_pdf_link_rect()` line 413 changed the parameter separator from
    keyword-only `*` to positional-only `/` for `rect`. Public callers pass
    `rect` positionally and `canvas_width`/`canvas_height` by keyword, so the
    public `DocumentPDF.add_page_link()` domain is unchanged.
  - `DocumentPDF.add_page_link()` line 1683 changed the separator before
    `left`, `top`, and `zoom` from keyword-only `*` to positional-only `/`.
    Existing tests and intended public use call destination values by keyword;
    the mutation does not alter runtime behavior for the declared call domain.
  - `_shift_pdf_page_metadata_for_removal()` line 1809 changed
    `link.page_number > page_number` to `>=`. The comprehension filters
    `link.page_number != page_number` before evaluating the output expression,
    so equality is excluded from the expression domain.
  - `_shift_pdf_page_metadata_for_removal()` line 1811 changed
    `link.target_page_number > page_number` to `>=`. The comprehension filters
    `link.target_page_number != page_number` before evaluating the output
    expression, so equality is excluded from the expression domain.
  - `to_pdf_bytes()` line 2085 changed `zip(..., strict=True)` to
    `strict=False`. `annotation_ids` is constructed from
    `len(page_annotations)`, so it has exactly the same length as the annotation
    sequence.
- Gate result: pass with documented equivalent survivors.

Current result after the named destination update:

- Tool: Cosmic Ray 8.4.6.
- Config: `tests/mutation/pdf_document_named_destination_cosmic_ray.toml`.
- Filter: `tests/mutation/filter_pdf_document_named_destination_work_items.py`.
- Test selection: focused PDF document, factory payload, and PDF generator tests.
- Raw work items: 4111.
- Proof-critical work items after filter: 147.
- Killed mutants: 142.
- Equivalent survivors: 5.
- Surviving equivalent mutations:
  - `_coerce_pdf_destination_number()` line 414 changed the separator before
    `owner` from keyword-only `*` to positional-only `/` for `value` and `name`.
    Public callers pass `value` and `name` positionally and `owner` by keyword,
    so the public named-destination domain is unchanged.
  - `_coerce_pdf_link_rect()` line 446 changed the parameter separator from
    keyword-only `*` to positional-only `/` for `rect`. Public callers pass
    `rect` positionally and `canvas_width`/`canvas_height` by keyword, so the
    public `DocumentPDF.add_named_destination_link()` domain is unchanged.
  - `DocumentPDF.add_named_destination()` line 1745 changed the separator before
    `left`, `top`, and `zoom` from keyword-only `*` to positional-only `/`.
    Existing tests and intended public use call destination values by keyword;
    the mutation does not alter runtime behavior for the declared call domain.
  - `_shift_pdf_page_metadata_for_removal()` line 1928 changed
    `destination.page_number > page_number` to `>=`. The comprehension filters
    `destination.page_number != page_number` before evaluating the output
    expression, so equality is excluded from the expression domain.
  - `_shift_pdf_page_metadata_for_removal()` line 1938 changed
    `link.page_number > page_number` to `>=`. The comprehension filters
    `link.page_number != page_number` before evaluating the output expression,
    so equality is excluded from the expression domain.
- Gate result: pass with documented equivalent survivors.

Current result after the nested outline update:

- Tool: Cosmic Ray 8.4.6.
- Config: `tests/mutation/pdf_document_nested_outline_cosmic_ray.toml`.
- Filter: `tests/mutation/filter_pdf_document_nested_outline_work_items.py`.
- Test selection: focused PDF document, factory payload, and PDF generator tests.
- Proof-critical work items after filter: 245.
- Killed mutants: 233.
- Equivalent survivors: 12.
- Surviving equivalent mutations:
  - `_coerce_pdf_destination_number()` line 415 changed the separator before
    `owner` from keyword-only `*` to positional-only `/` for `value` and `name`.
    Public callers pass `value` and `name` positionally and `owner` by keyword,
    so the public outline destination domain is unchanged.
  - `_shift_pdf_page_metadata_for_removal()` line 1894 changed page-label
    `index > page_number` to `>=`. The comprehension filters
    `index != page_number` before evaluating the expression, so equality is
    excluded from the expression domain.
  - `_shift_pdf_page_metadata_for_removal()` line 1897 made the same equivalent
    page-box `>` to `>=` change with the same pre-filter.
  - `_shift_pdf_page_metadata_for_removal()` line 1902 changed
    `outline.page_number > page_number` to `>=`. The comprehension filters
    `outline.page_number != page_number` before evaluating the expression, so
    equality is excluded from the expression domain.
  - `_outline_objects()` line 2018 changed `zip(..., strict=True)` to
    `strict=False`. `outline_item_ids` is constructed from the outline count, so
    it has exactly the same length as the outline sequence.
  - `_outline_objects()` line 2028 changed `sibling_position > 0` to
    `sibling_position != 0`. `list.index()` returns non-negative indices, so the
    predicates are equivalent for every sibling position.
  - `_outline_objects()` line 2029 changed
    `sibling_position + 1 < len(siblings)` to
    `sibling_position + 1 != len(siblings)`. In the loop domain,
    `sibling_position + 1 <= len(siblings)` always holds, so the predicates are
    equivalent.
  - `to_pdf_bytes()` line 2331 produced five equivalent mutations in the
    post-outline object-id increment. No later indirect objects are allocated
    after outlines in the current writer path, so the increment value has no
    observable serialized effect.
- Gate result: pass with documented equivalent survivors.

Current result after the outline expansion-state update:

- Tool: Cosmic Ray 8.4.6.
- Config: `tests/mutation/pdf_document_outline_state_cosmic_ray.toml`.
- Filter: `tests/mutation/filter_pdf_document_outline_state_work_items.py`.
- Test selection: focused PDF document, factory payload, and PDF generator tests.
- Raw work items: 4300.
- Proof-critical work items after filter: 12.
- Killed mutants: 12.
- Surviving mutants: 0.
- Gate result: pass.

Current result after the deep outline tree update:

- Tool: Cosmic Ray 8.4.6.
- Config: `tests/mutation/pdf_document_deep_outline_cosmic_ray.toml`.
- Filter: `tests/mutation/filter_pdf_document_deep_outline_work_items.py`.
- Test selection: focused PDF document, factory payload, and PDF generator tests.
- Raw work items: 4325.
- Proof-critical work items after filter: 89.
- Killed mutants: 82.
- Equivalent survivors: 7.
- Surviving equivalent mutations:
  - `_outline_objects()` line 2126 changed the private defensive parent-count
    check from `len(parent_indices) != 1` to `> 1` and `< 1`. The public
    `add_outline(parent=...)` boundary admits only exactly-one parent matches,
    and `DocumentPDF.create_from_dict()` delegates to that same boundary, so the
    malformed internal states are outside the live public domain.
  - `_outline_objects()` line 2128 changed `parent_indices[0]` to
    `parent_indices[-1]` while the same public invariant guarantees the list has
    exactly one element.
  - `_outline_objects()` line 2132 changed `zip(..., strict=True)` to
    `strict=False`. `outline_item_ids` is constructed from the outline count, so
    it has exactly the same length as the outline sequence.
  - `_outline_objects()` line 2138 changed `outline_indices_by_title[parent][0]`
    to `[-1]`. Public parent validation guarantees one matching parent index.
  - `_outline_objects()` line 2143 changed `sibling_position > 0` to
    `sibling_position != 0`. `list.index()` returns non-negative indices, so the
    predicates are equivalent for every sibling position.
  - `_outline_objects()` line 2144 changed
    `sibling_position + 1 < len(siblings)` to
    `sibling_position + 1 != len(siblings)`. In the loop domain,
    `sibling_position + 1 <= len(siblings)` always holds, so the predicates are
    equivalent.
- Gate result: pass with documented equivalent survivors.

Current result after the text annotation update:

- Tool: Cosmic Ray 8.4.6.
- Config: `tests/mutation/pdf_document_text_annotation_cosmic_ray.toml`.
- Filter: `tests/mutation/filter_pdf_document_text_annotation_work_items.py`.
- Test selection: focused PDF document, factory payload, and PDF generator tests.
- Proof-critical work items after filter: 117.
- Killed mutants: 114.
- Equivalent survivors: 3.
- Surviving equivalent mutations:
  - `_coerce_pdf_link_rect()` line 478 changed the parameter separator from
    keyword-only `*` to positional-only `/` for `rect`. Public callers enter
    through `DocumentPDF.add_text_annotation()`, which passes `rect`
    positionally and page dimensions by keyword, so the text annotation domain is
    unchanged.
  - `_shift_pdf_page_metadata_for_removal()` line 2031 changed
    `annotation.page_number > page_number` to `>=`. The comprehension filters
    `annotation.page_number != page_number` before evaluating the output
    expression, so equality is excluded from the expression domain.
  - `to_pdf_bytes()` line 2431 changed `zip(..., strict=True)` to
    `strict=False`. `annotation_ids` is constructed from
    `len(page_annotations)`, so it has exactly the same length as the annotation
    sequence.
- Gate result: pass with documented equivalent survivors.

Current result after the highlight annotation update:

- Tool: Cosmic Ray 8.4.6.
- Config: `tests/mutation/pdf_document_highlight_annotation_cosmic_ray.toml`.
- Filter:
  `tests/mutation/filter_pdf_document_highlight_annotation_work_items.py`.
- Test selection: focused PDF document, factory payload, and PDF generator tests.
- Raw work items: 4780.
- Proof-critical work items after filter: 162.
- Killed mutants: 160.
- Equivalent survivors: 2.
- Surviving equivalent mutations:
  - `_shift_pdf_page_metadata_for_removal()` line 2180 changed
    `annotation.page_number > page_number` to `>=`. The comprehension filters
    `annotation.page_number != page_number` before evaluating the output
    expression, so equality is excluded from the expression domain.
  - `_coerce_pdf_annotation_color()` line 515 changed the blue-channel slice
    from `[5:7]` to `[5:8]`. The exact `len(value) != 7` guard guarantees the
    admitted string ends at index 7, so both slices return the same two
    characters for every admitted input.
- Gate result: pass with documented equivalent survivors.

Current result after the square annotation update:

- Tool: Cosmic Ray 8.4.6.
- Config: `tests/mutation/pdf_document_square_annotation_cosmic_ray.toml`.
- Filter:
  `tests/mutation/filter_pdf_document_square_annotation_work_items.py`.
- Test selection: focused PDF document, factory payload, and PDF generator tests.
- Raw work items: 5132.
- Proof-critical work items after filter: 165.
- Killed mutants: 163.
- Equivalent survivors: 2.
- Surviving equivalent mutations:
  - `_coerce_pdf_annotation_color()` line 568 changed the blue-channel slice
    from `[5:7]` to `[5:8]`. The exact `len(value) != 7` guard guarantees the
    admitted string ends at index 7, so both slices return the same two
    characters for every admitted input.
  - `_shift_pdf_page_metadata_for_removal()` line 2378 changed
    `annotation.page_number > page_number` to `>=`. The comprehension filters
    `annotation.page_number != page_number` before evaluating the output
    expression, so equality is excluded from the expression domain.
- Gate result: pass with documented equivalent survivors.

Current result after the circle annotation update:

- Tool: Cosmic Ray 8.4.6.
- Config: `tests/mutation/pdf_document_circle_annotation_cosmic_ray.toml`.
- Filter:
  `tests/mutation/filter_pdf_document_circle_annotation_work_items.py`.
- Test selection: focused PDF document, factory payload, and PDF generator tests.
- Raw work items: 5399.
- Proof-critical work items after filter: 145.
- Killed mutants: 143.
- Equivalent survivors: 2.
- Surviving equivalent mutations:
  - `_shift_pdf_page_metadata_for_removal()` line 2542 changed
    `annotation.page_number > page_number` to `>=`. The comprehension filters
    `annotation.page_number != page_number` before evaluating the output
    expression, so equality is excluded from the expression domain.
  - `to_pdf_bytes()` line 3061 changed `zip(annotation_ids, page_annotations,
    strict=True)` to `strict=False`. `annotation_ids` is constructed from
    `len(page_annotations)` immediately before the loop, so both sequences have
    the same length by construction in the closed page-plan path.
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

## PO-PDFDOC-010: Flat PDF Outlines Emit And Round Trip

### Claim

`DocumentPDF` emits deterministic flat PDF outline objects, links outline items
with `/Prev` and `/Next`, targets existing page objects with `/Dest`, escapes
titles, and round-trips outlines through `parameters` and `create_from_dict()`.

### Proof Method

`add_outline()` validates title, page number, and destination numbers before
storing a `_PDFOutlineEntry`. `to_pdf_bytes()` allocates one outline root object
and one item object per outline after page objects exist, then writes catalog
`/Outlines` and `/PageMode /UseOutlines` entries. Tests parse PDF objects,
verify root `/First`, `/Last`, and `/Count`, item title escaping, parent/next/prev
links, exact `/XYZ` destination tokens, deterministic bytes, and serialization
round-trip equality.

### Counterexamples And Exclusions

Deeper outline trees, remote destinations, named destinations, and non-Latin-1
titles are excluded from this outline slice. One-level expansion state is
covered by PO-PDFDOC-028 through PO-PDFDOC-030.

### Conclusion

Proven for top-level Latin-1 outlines in the declared PDF document domain.

## PO-PDFDOC-011: Outline Targets Follow Page Index Mutations

### Claim

When pages are inserted or removed, outline page targets stay aligned with the
same logical page after the mutation, and outlines targeting a removed page are
deleted.

### Proof Method

`DocumentPDF.add_page()` and `DocumentPDF.remove_page()` already route through
the PDF metadata shift helpers. The outline update extends those helpers to
increment targets at or after insertion points, decrement targets after removed
pages, and drop outlines that target removed pages. Tests add middle and tail
outlines, insert before them, remove a targeted page, then remove an earlier page
and check serialized outline targets after each step.

### Conclusion

Proven for page indices admitted by the `DocumentPDF` public page mutation
methods, with the equivalent mutation survivor documented above.

## PO-PDFDOC-012: Serialized Outline Metadata Fails Explicitly

### Claim

Malformed serialized `outlines` payloads are rejected during
`DocumentPDF.create_from_dict()` before any rendered PDF can be produced from bad
outline metadata.

### Proof Method

`create_from_dict()` reads optional outline sequences through
`_pdf_optional_sequence()`, requires each entry to be a mapping, requires `title`
and `page_number`, and delegates to `add_outline()` for title, page, and
destination validation. Tests mutate a valid payload into non-sequence outline
containers, non-mapping entries, missing required fields, empty titles, missing
pages, and invalid destination values.

### Conclusion

Proven for serialized top-level outlines in the declared payload domain.

## PO-PDFDOC-022: Nested PDF Outlines Emit And Prune Orphans

### Claim

`DocumentPDF` emits deterministic nested PDF outlines with root-level sibling
links, parent child links, child sibling links, and valid `/Dest` arrays. When
page removal deletes a parent outline, surviving children of that parent are
pruned rather than emitted as orphaned outline objects.

### Proof Method

`add_outline(parent=...)` stores an optional parent title after validating that
the parent is exactly one earlier outline, and rejects later duplicates that
would make existing child relationships ambiguous.
`_outline_objects()` derives top-level and child sibling chains from the ordered
outline list, emits
`/First`, `/Last`, `/Prev`, `/Next`, `/Parent`, and `/Count` relationships, and
uses `_outline_destination()` for every item. Page-removal tests cover children
whose page survives while the parent page is removed, proving orphan pruning.

### Counterexamples And Exclusions

Remote destinations and named destination outline targets are excluded from this
nested outline slice. Deep outline recursion is covered by PO-PDFDOC-031 through
PO-PDFDOC-033. Expansion state is covered by PO-PDFDOC-028 through
PO-PDFDOC-030.

### Conclusion

Proven for nested Latin-1 outlines in the declared PDF document domain, with the
equivalent mutation survivors documented above.

## PO-PDFDOC-023: Nested Outline Parents Fail Explicitly

### Claim

`DocumentPDF.add_outline(parent=...)` rejects missing, ambiguous, non-Latin-1,
and non-string parents before mutating PDF outline metadata. It also rejects a
later top-level outline title that would make an existing child parent
ambiguous.

### Proof Method

The public boundary coerces parent titles through the same Latin-1 outline-title
validator used for outline titles, then matches all existing outlines by title
value. Tests cover missing parents, duplicate parent titles, value equality for
an independently constructed matching string, and invalid object parents. Tests
also cover a later duplicate after a child exists. Serialized-payload tests cover
malformed `parent` values and serialized duplicate-after-child ambiguity through
`DocumentPDF.create_from_dict()`.

### Conclusion

Proven for parent validation at the public API and serialized payload boundary.

## PO-PDFDOC-024: Nested Outline Serialization Preserves Parents

### Claim

Child outline parent metadata is preserved in `DocumentPDF.parameters`,
`DocumentPDF.outlines()`, and `DocumentPDF.create_from_dict()`.

### Proof Method

`_outline_entry_payload()` includes `parent` only for child outlines.
`create_from_dict()` reads optional `parent` values and delegates to
`add_outline()` in serialized order so parents must exist before children.
Behavioral tests assert exact `outlines()` payloads and byte-for-byte equality
between the original document and a document recreated from parameters.

### Conclusion

Proven for serialized nested outlines in the declared payload domain.

## PO-PDFDOC-028: Collapsed PDF Outline Parents Emit Negative Child Counts

### Claim

`DocumentPDF` emits positive descendant `/Count` values for expanded parent
outlines and negative descendant `/Count` values for collapsed parent outlines.

### Proof Method

`add_outline(expanded=...)` validates a strict boolean and stores it on
`_PDFOutlineEntry`. `_outline_objects()` derives each parent's child list and
uses `_outline_descendant_count()` to compute `/Count` magnitude recursively.
Expanded parents emit positive counts and collapsed parents emit negative counts.
Behavioral tests render expanded and collapsed parents, parse the outline
objects, assert exact positive and negative count bytes, and verify deterministic
serialization round-trip equality.

### Counterexamples And Exclusions

Leaf outline items do not emit `/Count` because they have no children.

### Conclusion

Proven for Latin-1 outline parents in the declared PDF document domain, with
mutation verification documented above.

## PO-PDFDOC-029: Outline Expansion State Follows Page Mutations

### Claim

When pages are inserted or removed, outline expansion state stays attached to
the same logical outline entry while page targets shift or deleted targets are
removed.

### Proof Method

`DocumentPDF.add_page()` and `DocumentPDF.remove_page()` route through the PDF
metadata shift helpers. The outline expansion update extends both
`_PDFOutlineEntry` reconstructions to preserve `expanded`. Tests add a collapsed
middle parent, insert a page before it, and assert the shifted outline keeps
`expanded: false`; subsequent removal of that parent also proves orphan pruning
does not leak collapsed state into surviving children.

### Conclusion

Proven for page indices admitted by the `DocumentPDF` public page mutation
methods, with mutation verification documented above.

## PO-PDFDOC-030: Serialized Outline Expansion State Fails Explicitly

### Claim

Malformed serialized outline `expanded` values are rejected during
`DocumentPDF.create_from_dict()`, while omitted values default to expanded.

### Proof Method

`create_from_dict()` reads optional `expanded` values with a default of `True`
and delegates to `add_outline()`, which rejects non-boolean values. Tests mutate
a valid serialized outline to use integer `expanded`, prove rejection, then
hydrate a payload with `expanded: false` and missing `left` to prove both the
existing default-left behavior and collapsed-state preservation.

### Conclusion

Proven for serialized outline expansion state in the declared payload domain,
with mutation verification documented above.

## PO-PDFDOC-031: Deep PDF Outlines Emit Recursive Links

### Claim

`DocumentPDF` emits deterministic recursive outline dictionaries for children at
any depth, including parent links, sibling links, child links, and descendant
`/Count` values.

### Proof Method

`_outline_objects()` maps outline titles to insertion indices, resolves each
child's parent to exactly one existing outline, builds child lists by parent
index, and emits `/Parent`, `/Prev`, `/Next`, `/First`, `/Last`, and `/Count`
links from those lists. The deep-outline behavioral test renders a root,
section, collapsed topic, leaf, sibling, and second top-level outline; it parses
object ids and asserts exact recursive links, descendant counts, collapsed
counts, deterministic bytes, and serialized round-trip equality.

### Conclusion

Proven for arbitrary-depth Latin-1 outline trees admitted by the public
`DocumentPDF.add_outline()` boundary.

## PO-PDFDOC-032: Deep Outline Parent Ambiguity Fails Explicitly

### Claim

Deep outline parent references fail before mutation or rendering when the parent
title is missing, malformed, or ambiguous.

### Proof Method

`add_outline(parent=...)` validates parent titles and requires exactly one
existing outline with the requested title. Tests create duplicate candidate
parents and prove a deeper child cannot select between them. Tests also prove a
later duplicate of a title already used as a parent is rejected so stored child
relationships remain deterministic.

### Conclusion

Proven for title-based deep parent references at the public API and serialized
payload boundary.

## PO-PDFDOC-033: Deep Outline Page Removal Prunes Descendants

### Claim

When page removal deletes an outline in the middle of a hierarchy, descendants
whose parent chain no longer resolves are pruned.

### Proof Method

`_shift_pdf_page_metadata_for_removal()` first removes outlines targeting the
deleted page, then calls `_outlines_with_valid_parent_chains()`. That helper
retains only outlines whose parent is absent or already retained earlier in the
serialized insertion order. The deep page-removal test deletes a nested branch
and proves its surviving grandchild is pruned while a sibling with a still-valid
parent remains and shifts page number.

### Conclusion

Proven for deep outline hierarchies whose page targets are admitted by
`DocumentPDF.remove_page()`.

## PO-PDFDOC-013: URI Link Annotations Emit And Round Trip

### Claim

`DocumentPDF` emits deterministic PDF link annotations, stores every same-page
link in the page `/Annots` array, escapes literal URI strings, and round-trips
URI links through `parameters` and `create_from_dict()`.

### Proof Method

`add_uri_link()` validates page number, rectangle bounds, and URI string before
storing a `_PDFUriLinkAnnotation`. `to_pdf_bytes()` groups URI links by page,
allocates one annotation object per link, wires page `/Annots` arrays, and emits
`/Subtype /Link` dictionaries with `/S /URI` actions. Tests parse PDF objects,
verify same-page annotation arrays, exact rectangle bytes, URI escaping,
deterministic repeated rendering, and serialization round-trip equality.

### Counterexamples And Exclusions

Rich annotation appearances, generic annotation subtypes, and non-Latin-1 URI
strings are excluded from this flat URI link slice.

### Conclusion

Proven for Latin-1 URI link annotations in the declared PDF document domain,
with the equivalent mutation survivors documented above.

## PO-PDFDOC-014: URI Link Targets Follow Page Index Mutations

### Claim

When pages are inserted or removed, URI link page targets stay aligned with the
same logical page after the mutation, and links targeting a removed page are
deleted.

### Proof Method

`DocumentPDF.add_page()` and `DocumentPDF.remove_page()` route through the PDF
metadata shift helpers. The URI link update extends those helpers to increment
targets at or after insertion points, decrement targets after removed pages, and
drop links that target removed pages. Tests add front, middle, and tail links,
insert before the middle link, remove the middle target, then remove an earlier
page and check serialized link targets after each step.

### Conclusion

Proven for page indices admitted by the `DocumentPDF` public page mutation
methods, with the equivalent mutation survivor documented above.

## PO-PDFDOC-015: Serialized URI Link Metadata Fails Explicitly

### Claim

Malformed serialized `uri_links` payloads are rejected during
`DocumentPDF.create_from_dict()` before any rendered PDF can be produced from
bad URI link metadata.

### Proof Method

`create_from_dict()` reads optional URI link sequences through
`_pdf_optional_sequence()`, requires each entry to be a mapping, requires
`page_number`, `rect`, and `uri`, and delegates to `add_uri_link()` for page,
rectangle, and URI validation. Tests mutate a valid payload into non-sequence
containers, non-mapping entries, missing required fields, missing pages, invalid
rectangles, and empty URI strings.

### Conclusion

Proven for serialized URI link annotations in the declared payload domain, with
mutation verification documented above.

## PO-PDFDOC-016: Internal Page Link Annotations Emit And Round Trip

### Claim

`DocumentPDF` emits deterministic internal page link annotations, stores every
same-page link in the page `/Annots` array, targets existing PDF page objects
with `/Dest`, and round-trips internal page links through `parameters` and
`create_from_dict()`.

### Proof Method

`add_page_link()` validates source page number, target page number, rectangle
bounds, and destination numbers before storing a `_PDFPageLinkAnnotation`.
`to_pdf_bytes()` groups page links by source page, performs two-pass page object
allocation so later page IDs are available to earlier annotations, wires page
`/Annots` arrays, and emits `/Subtype /Link` dictionaries with direct `/Dest`
arrays. Tests parse PDF objects, verify same-page annotation arrays, exact
rectangle bytes, destination page object IDs, `/XYZ` destination tokens,
deterministic repeated rendering, and serialization round-trip equality.

### Counterexamples And Exclusions

Remote destinations, non-`/XYZ` destination modes, rich annotation appearances,
and generic annotation subtypes are excluded from this internal page link slice.

### Conclusion

Proven for internal `/XYZ` page link annotations in the declared PDF document
domain, with the equivalent mutation survivors documented above.

## PO-PDFDOC-017: Internal Page Links Follow Source And Target Page Mutations

### Claim

When pages are inserted or removed, internal page link source and target pages
stay aligned with the same logical pages after the mutation, and links whose
source or target page is removed are deleted.

### Proof Method

`DocumentPDF.add_page()` and `DocumentPDF.remove_page()` route through the PDF
metadata shift helpers. The internal page link update extends those helpers to
increment source and target pages at or after insertion points, decrement source
and target pages after removed pages, and drop links whose source or target page
matches the removed page. Tests include links before, on, and after the mutation
point, including a non-target link after a removed page to prove source-page
decrement, and a large page-number removal case to prove value equality rather
than object identity.

### Conclusion

Proven for page indices admitted by the `DocumentPDF` public page mutation
methods, with the equivalent mutation survivors documented above.

## PO-PDFDOC-018: Serialized Internal Page Link Metadata Fails Explicitly

### Claim

Malformed serialized `page_links` payloads are rejected during
`DocumentPDF.create_from_dict()` before any rendered PDF can be produced from
bad internal page link metadata.

### Proof Method

`create_from_dict()` reads optional page link sequences through
`_pdf_optional_sequence()`, requires each entry to be a mapping, requires
`page_number`, `rect`, and `target_page_number`, defaults missing `left` to
`0.0`, and delegates to `add_page_link()` for source page, target page,
rectangle, and destination validation. Tests mutate a valid payload into
non-sequence containers, non-mapping entries, missing required fields, missing
source/target pages, invalid rectangles, and invalid destination values.

### Conclusion

Proven for serialized internal page link annotations in the declared payload
domain, with mutation verification documented above.

## PO-PDFDOC-019: Named Destinations Emit And Round Trip

### Claim

`DocumentPDF` emits deterministic PDF named destinations through the catalog
`/Names` dictionary, stores every same-page named-destination link in page
`/Annots` arrays, targets destination names with literal-string `/Dest` values,
and round-trips named destinations and links through `parameters` and
`create_from_dict()`.

### Proof Method

`add_named_destination()` validates destination names, target page numbers, and
destination numbers before storing a `_PDFNamedDestination`.
`add_named_destination_link()` validates source pages, destination existence,
and link rectangles before storing a `_PDFNamedDestinationLinkAnnotation`.
`to_pdf_bytes()` emits deterministic `/Names << /Dests << /Names [...] >> >>`
catalog entries sorted by destination name and emits named-destination link
annotations after URI and internal page links for each page. Tests parse PDF
objects, verify name-tree ordering, escaped destination names, exact page object
targets, named `/Dest` annotations, deterministic repeated rendering, and
serialization round-trip equality.

### Counterexamples And Exclusions

Nested name trees, remote destinations, non-`/XYZ` destination modes, rich
annotation appearances, and generic annotation subtypes are excluded from this
named destination slice.

### Conclusion

Proven for flat catalog named destinations and named-destination links in the
declared PDF document domain, with the equivalent mutation survivors documented
above.

## PO-PDFDOC-020: Named Destinations Follow Page Mutations

### Claim

When pages are inserted or removed, named destination page targets and
named-destination link source pages stay aligned with the same logical pages,
and destinations or links tied to removed pages are deleted.

### Proof Method

`DocumentPDF.add_page()` and `DocumentPDF.remove_page()` route through the PDF
metadata shift helpers. The named destination update extends those helpers to
increment destination targets and link source pages at or after insertion
points, decrement them after removed pages, remove destinations targeting
removed pages, and remove named-destination links whose source page or
destination name has been removed. Tests include links before, on, and after the
mutation point, plus a large page-number removal case to prove value equality
rather than object identity.

### Conclusion

Proven for page indices admitted by the `DocumentPDF` public page mutation
methods, with the equivalent mutation survivors documented above.

## PO-PDFDOC-021: Serialized Named Destination Metadata Fails Explicitly

### Claim

Malformed serialized `named_destinations` and `named_destination_links` payloads
are rejected during `DocumentPDF.create_from_dict()` before any rendered PDF can
be produced from bad named-destination metadata.

### Proof Method

`create_from_dict()` reads optional named destination and named-destination link
sequences through `_pdf_optional_sequence()`, requires each entry to be a
mapping, requires destination/link fields, defaults missing destination `left`
to `0.0`, and delegates to `add_named_destination()` and
`add_named_destination_link()` for name, page, rectangle, and destination
validation. Tests mutate a valid payload into non-sequence containers,
non-mapping entries, missing required fields, missing pages, invalid destination
names, invalid rectangles, invalid destination values, and links to missing
destination names.

### Conclusion

Proven for serialized named destinations and named-destination links in the
declared payload domain, with mutation verification documented above.

## PO-PDFDOC-025: PDF Text Annotations Emit And Round Trip

### Claim

`DocumentPDF` emits deterministic PDF text annotations, stores every same-page
text annotation in the page `/Annots` array after existing link annotations,
escapes literal contents and title strings, preserves deterministic bytes, and
round-trips text annotations through `parameters` and `create_from_dict()`.

### Proof Method

`add_text_annotation()` validates page number, rectangle bounds, contents, title,
and open state before storing a `_PDFTextAnnotation`. `to_pdf_bytes()` groups
text annotations by page, allocates one annotation object per entry, appends
their IDs to page `/Annots` arrays after URI/page/named-destination links, and
emits `/Subtype /Text` dictionaries with `/Contents`, optional `/T`, and
optional `/Open true`. Tests parse PDF objects, verify same-page annotation
arrays, exact rectangle bytes, escaped contents/title strings, deterministic
repeated rendering, and serialization round-trip equality.

### Counterexamples And Exclusions

Rich appearance streams, annotation replies, file attachments, stamps,
highlights, widgets, other non-text annotation subtypes, and non-Latin-1 strings
are excluded from this text annotation slice.

### Conclusion

Proven for Latin-1 PDF text annotations in the declared PDF document domain,
with mutation verification documented above.

## PO-PDFDOC-026: PDF Text Annotations Follow Page Mutations

### Claim

When pages are inserted or removed, text annotation source pages stay aligned
with the same logical pages after the mutation, and annotations tied to removed
pages are deleted.

### Proof Method

`DocumentPDF.add_page()` and `DocumentPDF.remove_page()` route through the PDF
metadata shift helpers. The text annotation update extends those helpers to
increment source pages at or after insertion points, decrement source pages
after removed pages, and drop annotations whose source page matches the removed
page. Tests include annotations before, on, and after the mutation point, plus a
large page-number removal case to prove value equality rather than object
identity.

### Conclusion

Proven for page indices admitted by the `DocumentPDF` public page mutation
methods, with mutation verification documented above.

## PO-PDFDOC-027: Serialized Text Annotation Metadata Fails Explicitly

### Claim

Malformed serialized `text_annotations` payloads are rejected during
`DocumentPDF.create_from_dict()` before any rendered PDF can be produced from
bad text annotation metadata.

### Proof Method

`create_from_dict()` reads optional text annotation sequences through
`_pdf_optional_sequence()`, requires each entry to be a mapping, requires
`page_number`, `rect`, and `contents`, defaults missing `open` to `False`, and
delegates to `add_text_annotation()` for page, rectangle, contents, title, and
open-state validation. Tests mutate a valid payload into non-sequence
containers, non-mapping entries, missing required fields, missing pages, invalid
rectangles, empty contents, invalid titles, and non-boolean open states. A
separate test proves missing optional title/open values hydrate with defaults.

### Conclusion

Proven for serialized text annotations in the declared payload domain, with
mutation verification documented above.

## PO-PDFDOC-034: PDF Highlight Annotations Emit And Round Trip

### Claim

`DocumentPDF` emits deterministic PDF highlight annotations, stores every
same-page highlight annotation in the page `/Annots` array after existing link
and text annotations, derives `/QuadPoints` from the rectangle, preserves
deterministic bytes, and round-trips highlight annotations through `parameters`
and `create_from_dict()`.

### Proof Method

`add_highlight_annotation()` validates page number, rectangle bounds, color, and
optional contents before storing a `_PDFHighlightAnnotation`. `to_pdf_bytes()`
groups highlights by page, allocates one annotation object per entry, appends
their IDs to page `/Annots` arrays after URI/page/named-destination links and
text annotations, and emits `/Subtype /Highlight` dictionaries with `/Rect`,
`/QuadPoints`, `/C`, and optional `/Contents`. Tests parse PDF objects, verify
same-page annotation ordering, exact rectangle bytes, quad-point bytes, color
bytes, escaped contents strings, deterministic repeated rendering, and
serialization round-trip equality.

### Counterexamples And Exclusions

Multi-quad highlights, rich appearance streams, annotation replies, widgets,
other annotation subtypes, and non-Latin-1 contents are excluded from this
highlight annotation slice.

### Conclusion

Proven for rectangular Latin-1 PDF highlight annotations in the declared PDF
document domain, with mutation verification documented above.

## PO-PDFDOC-035: PDF Highlight Annotations Follow Page Mutations

### Claim

When pages are inserted or removed, highlight annotation source pages stay
aligned with the same logical pages after the mutation, and annotations tied to
removed pages are deleted.

### Proof Method

`DocumentPDF.add_page()` and `DocumentPDF.remove_page()` route through the PDF
metadata shift helpers. The highlight annotation update extends those helpers to
increment source pages at or after insertion points, decrement source pages
after removed pages, and drop annotations whose source page matches the removed
page. Tests include annotations before, on, and after the mutation point, plus a
large page-number removal case to prove value equality rather than object
identity.

### Conclusion

Proven for page indices admitted by the `DocumentPDF` public page mutation
methods, with mutation verification documented above.

## PO-PDFDOC-036: Serialized Highlight Annotation Metadata Fails Explicitly

### Claim

Malformed serialized `highlight_annotations` payloads are rejected during
`DocumentPDF.create_from_dict()` before any rendered PDF can be produced from
bad highlight annotation metadata.

### Proof Method

`create_from_dict()` reads optional highlight annotation sequences through
`_pdf_optional_sequence()`, requires each entry to be a mapping, requires
`page_number`, `rect`, and `color`, and delegates to
`add_highlight_annotation()` for page, rectangle, color, and contents
validation. Tests mutate a valid payload into non-sequence containers,
non-mapping entries, missing required fields, missing pages, invalid rectangles,
invalid colors, and empty contents. A separate test proves missing optional
contents hydrate with defaults.

### Conclusion

Proven for serialized highlight annotations in the declared payload domain, with
mutation verification documented above.

## PO-PDFDOC-037: PDF Square Annotations Emit And Round Trip

### Claim

`DocumentPDF` emits deterministic PDF square annotations, stores every same-page
square annotation in the page `/Annots` array after existing link, text, and
highlight annotations, preserves deterministic bytes, and round-trips square
annotations through `parameters` and `create_from_dict()`.

### Proof Method

`add_square_annotation()` validates page number, rectangle bounds, border color,
and optional contents before storing a `_PDFSquareAnnotation`. `to_pdf_bytes()`
groups squares by page, allocates one annotation object per entry, appends their
IDs to page `/Annots` arrays after URI/page/named-destination links, text
annotations, and highlight annotations, and emits `/Subtype /Square`
dictionaries with `/Rect`, `/C`, `/Border [0 0 1]`, and optional `/Contents`.
Tests parse PDF objects, verify same-page annotation ordering, exact rectangle
bytes, color bytes, border bytes, escaped contents strings, deterministic
repeated rendering, and serialization round-trip equality.

### Counterexamples And Exclusions

Rich appearance streams, fill colors, custom border styles, annotation replies,
widgets, other annotation subtypes, tagged PDF structure, and non-Latin-1
contents are excluded from this square annotation slice.

### Conclusion

Proven for rectangular Latin-1 PDF square annotations in the declared PDF
document domain, with mutation verification documented above.

## PO-PDFDOC-038: PDF Square Annotations Follow Page Mutations

### Claim

When pages are inserted or removed, square annotation source pages stay aligned
with the same logical pages after the mutation, and annotations tied to removed
pages are deleted.

### Proof Method

`DocumentPDF.add_page()` and `DocumentPDF.remove_page()` route through the PDF
metadata shift helpers. The square annotation update extends those helpers to
increment source pages at or after insertion points, decrement source pages
after removed pages, and drop annotations whose source page matches the removed
page. Tests include annotations before, on, and after the mutation point, plus a
large page-number removal case to prove value equality rather than object
identity.

### Conclusion

Proven for page indices admitted by the `DocumentPDF` public page mutation
methods, with mutation verification documented above.

## PO-PDFDOC-039: Serialized Square Annotation Metadata Fails Explicitly

### Claim

Malformed serialized `square_annotations` payloads are rejected during
`DocumentPDF.create_from_dict()` before any rendered PDF can be produced from
bad square annotation metadata.

### Proof Method

`create_from_dict()` reads optional square annotation sequences through
`_pdf_optional_sequence()`, requires each entry to be a mapping, requires
`page_number`, `rect`, and `color`, and delegates to `add_square_annotation()`
for page, rectangle, color, and contents validation. Tests mutate a valid
payload into non-sequence containers, non-mapping entries, missing required
fields, missing pages, invalid rectangles, invalid colors, and empty contents. A
separate test proves missing optional contents hydrate with defaults.

### Conclusion

Proven for serialized square annotations in the declared payload domain, with
mutation verification documented above.

## PO-PDFDOC-040: PDF Circle Annotations Emit And Round Trip

### Claim

`DocumentPDF` emits deterministic PDF circle annotations, stores every same-page
circle annotation in the page `/Annots` array after existing link, text,
highlight, and square annotations, preserves deterministic bytes, and
round-trips circle annotations through `parameters` and `create_from_dict()`.

### Proof Method

`add_circle_annotation()` validates page number, rectangle bounds, border color,
and optional contents before storing a `_PDFCircleAnnotation`. `to_pdf_bytes()`
groups circles by page, allocates one annotation object per entry, appends their
IDs to page `/Annots` arrays after URI/page/named-destination links, text
annotations, highlight annotations, and square annotations, and emits
`/Subtype /Circle` dictionaries with `/Rect`, `/C`, `/Border [0 0 1]`, and
optional `/Contents`. Tests parse PDF objects, verify same-page annotation
ordering, exact rectangle bytes, color bytes, border bytes, escaped contents
strings, deterministic repeated rendering, and serialization round-trip
equality.

### Counterexamples And Exclusions

Rich appearance streams, fill colors, custom border styles, annotation replies,
widgets, other annotation subtypes, tagged PDF structure, and non-Latin-1
contents are excluded from this circle annotation slice.

### Conclusion

Proven for rectangular Latin-1 PDF circle annotations in the declared PDF
document domain, with mutation verification documented above.

## PO-PDFDOC-041: PDF Circle Annotations Follow Page Mutations

### Claim

When pages are inserted or removed, circle annotation source pages stay aligned
with the same logical pages after the mutation, and annotations tied to removed
pages are deleted.

### Proof Method

`DocumentPDF.add_page()` and `DocumentPDF.remove_page()` route through the PDF
metadata shift helpers. The circle annotation update extends those helpers to
increment source pages at or after insertion points, decrement source pages
after removed pages, and drop annotations whose source page matches the removed
page. Tests include annotations before, on, and after the mutation point, plus a
large page-number removal case to prove value equality rather than object
identity.

### Conclusion

Proven for page indices admitted by the `DocumentPDF` public page mutation
methods, with the equivalent mutation survivor documented above.

## PO-PDFDOC-042: Serialized Circle Annotation Metadata Fails Explicitly

### Claim

Malformed serialized `circle_annotations` payloads are rejected during
`DocumentPDF.create_from_dict()` before any rendered PDF can be produced from
bad circle annotation metadata.

### Proof Method

`create_from_dict()` reads optional circle annotation sequences through
`_pdf_optional_sequence()`, requires each entry to be a mapping, requires
`page_number`, `rect`, and `color`, and delegates to `add_circle_annotation()`
for page, rectangle, color, and contents validation. Tests mutate a valid
payload into non-sequence containers, non-mapping entries, missing required
fields, missing pages, invalid rectangles, invalid colors, and empty contents. A
separate test proves missing optional contents hydrate with defaults.

### Conclusion

Proven for serialized circle annotations in the declared payload domain, with
mutation verification documented above.
