# ADR-0007: PDF Named Destinations

## Status

Accepted

## Context

InkGen's PDF backend creates deterministic synthetic drawings and document
fixtures. Direct internal page links cover active regions that target one page
object. Some fixtures also need reusable destination names so multiple links can
target a stable symbolic destination in the same PDF.

Named destinations are document metadata. They should remain owned by
`DocumentPDF`, not by drawing components or document-output adapters.

## Decision

`DocumentPDF` supports flat named destinations and links to those destinations:

- `add_named_destination(name, page_number, left=0.0, top=None, zoom=None)` adds
  or replaces one named destination targeting an existing page.
- `named_destinations()` returns serialized destinations sorted by destination
  name.
- `clear_named_destinations()` removes all named destinations and links that
  target them.
- `add_named_destination_link(page_number, rect, destination_name)` appends one
  link annotation from an existing source page to an existing destination name.
- `named_destination_links()` returns serialized named-destination links in
  insertion order.
- `clear_named_destination_links()` removes only named-destination link
  annotations.
- `to_pdf_bytes()` emits catalog `/Names << /Dests << /Names [...] >> >>`
  entries and page `/Subtype /Link` annotations with literal-string `/Dest`
  names.
- `parameters` and `create_from_dict()` preserve named destinations and links.
- Page insertions and removals shift or remove destination page targets and link
  source pages.

Destination names are non-empty Latin-1 strings. Destination numbers must be
finite when provided. Omitted `top` and `zoom` values are emitted as PDF `null`
tokens. Link rectangles must be finite positive-area rectangles inside the
source page MediaBox.

Nested name trees, remote destinations, non-`/XYZ` destination modes, visual
annotation appearances, and generic annotation types are out of scope.

## Consequences

- The PDF backend gains reusable symbolic navigation fixtures without adding
  dependencies.
- The public API remains deterministic and page-mutation aware.
- Name-tree emission is flat and sorted; large hierarchical name trees remain
  deferred until there is a concrete fixture need.
- Broader annotation support remains deferred until there is a concrete
  Document Intelligence fixture need.

## Proof And Verification

Proof obligations `PO-PDFDOC-019` through `PO-PDFDOC-021` in
`docs/proofs/pdf-document-contract.md` cover:

- catalog `/Names` `/Dests` emission,
- named-destination link annotation emission,
- deterministic serialization round trips,
- destination name, page, rectangle, and destination validation,
- page insertion/removal target and source shifts,
- malformed serialized named-destination rejection.

Behavioral coverage is marked with `PDF-DOC-NAMED-DEST-P3`.

## Affected Contracts

- `src/InkGen/pdf_generator.py`
- `tests/test_pdf_document_contract.py`
- `docs/pdf-generation.md`
- `docs/proofs/pdf-document-contract.md`

## Related Decisions

- ADR-0003: PDF Page Structure Metadata
- ADR-0004: PDF Flat Outlines
- ADR-0005: PDF URI Link Annotations
- ADR-0006: PDF Internal Page Links
