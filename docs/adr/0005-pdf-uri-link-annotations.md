# ADR-0005: PDF URI Link Annotations

## Status

Accepted

## Context

InkGen's PDF backend creates deterministic synthetic drawings and document
fixtures. Some generated parser fixtures need active external references, such
as a drawing note or document region linked to a URI. PDF link annotations are
page metadata and should remain owned by `DocumentPDF`, not by drawing
components or document-output adapters.

The immediate need is external URI links. Internal page links, named
destinations, generic annotation subtypes, and rich annotation appearances add
more PDF semantics than the current fixture need requires.

## Decision

`DocumentPDF` supports flat URI link annotations:

- `add_uri_link(page_number, rect, uri)` appends one URI link annotation on an
  existing page.
- `uri_links()` returns serialized URI link entries in insertion order.
- `clear_uri_links()` removes all URI link entries.
- `to_pdf_bytes()` emits page `/Annots` arrays and `/Subtype /Link` annotation
  objects with `/A << /S /URI /URI (...) >>` actions.
- `parameters` and `create_from_dict()` preserve URI links.
- Page insertions and removals shift or remove URI link page targets.

URI strings are non-empty Latin-1 strings. Annotation rectangles must be finite
positive-area rectangles inside the target page MediaBox, expressed in PDF
bottom-left page coordinates.

Internal links, named destinations, non-URI actions, visual annotation
appearances, generic annotation types, and non-Latin-1 URI strings are out of
scope.

## Consequences

- The PDF backend gains practical external link fixtures without adding
  dependencies.
- The public API remains small and deterministic.
- Link metadata follows the same page mutation and serialization model as page
  labels, page boxes, and flat outlines.
- Broader annotation support remains deferred until there is a concrete
  Document Intelligence fixture need.

## Proof And Verification

Proof obligations `PO-PDFDOC-013` through `PO-PDFDOC-015` in
`docs/proofs/pdf-document-contract.md` cover:

- link annotation object and page `/Annots` array emission,
- rectangle and URI validation,
- deterministic serialization round trips,
- page insertion/removal target shifts,
- malformed serialized URI link rejection.

Behavioral coverage is marked with `PDF-DOC-LINK-P3`.

## Affected Contracts

- `src/InkGen/pdf_generator.py`
- `tests/test_pdf_document_contract.py`
- `docs/pdf-generation.md`
- `docs/proofs/pdf-document-contract.md`

## Related Decisions

- ADR-0003: PDF Page Structure Metadata
- ADR-0004: PDF Flat Outlines
