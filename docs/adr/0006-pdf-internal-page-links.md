# ADR-0006: PDF Internal Page Links

## Status

Accepted

## Context

InkGen's PDF backend creates deterministic synthetic drawings and document
fixtures. After URI link annotations, the next narrow navigation gap is an
active region on one PDF page that jumps to another page in the same document.
This is page metadata and should remain owned by `DocumentPDF`, not by drawing
components or document-output adapters.

The immediate need is direct page-object destinations. Named destinations,
remote destinations, generic annotation subtypes, and rich annotation
appearances add more PDF semantics than the current fixture need requires.

## Decision

`DocumentPDF` supports flat internal page link annotations:

- `add_page_link(page_number, rect, target_page_number, left=0.0, top=None,
  zoom=None)` appends one link annotation from an existing source page to an
  existing target page.
- `page_links()` returns serialized page link entries in insertion order.
- `clear_page_links()` removes all page link entries.
- `to_pdf_bytes()` emits page `/Annots` arrays and `/Subtype /Link` annotation
  objects with direct `/Dest [page 0 R /XYZ left top zoom]` arrays.
- `parameters` and `create_from_dict()` preserve page links.
- Page insertions and removals shift or remove both source and target page
  numbers.

Annotation rectangles must be finite positive-area rectangles inside the source
page MediaBox, expressed in PDF bottom-left page coordinates. Destination
numbers must be finite when provided. Omitted `top` and `zoom` values are
emitted as PDF `null` tokens.

Named destinations, remote destinations, non-`/XYZ` destination modes, visual
annotation appearances, and generic annotation types are out of scope.

## Consequences

- The PDF backend gains practical internal navigation fixtures without adding
  dependencies.
- The public API remains small and deterministic.
- `DocumentPDF.to_pdf_bytes()` plans page object IDs before writing annotations
  so links can target later pages.
- Broader annotation and named-destination support remains deferred until there
  is a concrete Document Intelligence fixture need.

## Proof And Verification

Proof obligations `PO-PDFDOC-016` through `PO-PDFDOC-018` in
`docs/proofs/pdf-document-contract.md` cover:

- link annotation object and page `/Annots` array emission,
- source page, target page, rectangle, and destination validation,
- deterministic serialization round trips,
- page insertion/removal source and target shifts,
- malformed serialized page link rejection.

Behavioral coverage is marked with `PDF-DOC-PAGE-LINK-P3`.

## Affected Contracts

- `src/InkGen/pdf_generator.py`
- `tests/test_pdf_document_contract.py`
- `docs/pdf-generation.md`
- `docs/proofs/pdf-document-contract.md`

## Related Decisions

- ADR-0003: PDF Page Structure Metadata
- ADR-0004: PDF Flat Outlines
- ADR-0005: PDF URI Link Annotations
