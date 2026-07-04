# ADR-0004: PDF Flat Outlines

## Status

Accepted

## Context

InkGen's PDF backend creates deterministic synthetic drawings and document
fixtures. Some generated documents need basic reader navigation, but nested
outline trees add hierarchy semantics, expansion state, and mutation behavior
that are not yet required by Document Intelligence fixtures.

Outlines are PDF document metadata. They should remain owned by `DocumentPDF`,
not by renderer-neutral drawing components or flow-document outputs.

## Decision

`DocumentPDF` supports flat PDF outlines:

- `add_outline(title, page_number, left=0.0, top=None, zoom=None)` appends one
  outline entry targeting an existing page.
- `outlines()` returns serialized outline entries in insertion order.
- `clear_outlines()` removes all outline entries.
- `to_pdf_bytes()` emits a PDF `/Outlines` root, flat linked outline item
  objects, `/Dest` arrays, and `/PageMode /UseOutlines`.
- `parameters` and `create_from_dict()` preserve outlines.
- Page insertions and removals shift or remove outline page targets.

Outline titles are non-empty Latin-1 strings. Destination numbers must be
finite. Omitted `top` and `zoom` values are emitted as PDF `null` tokens.

Nested outline trees, remote destinations, named destinations, and non-Latin-1
outline titles are out of scope.

## Consequences

- The PDF backend gains useful document navigation without adding dependencies.
- The public API remains small and deterministic.
- Nested bookmark behavior is intentionally deferred until there is a concrete
  fixture requirement.
- Unicode title support remains tied to the broader PDF Unicode string policy.

## Proof And Verification

Proof obligations `PO-PDFDOC-010` through `PO-PDFDOC-012` in
`docs/proofs/pdf-document-contract.md` cover:

- flat outline object emission,
- destination and title validation,
- deterministic serialization round trips,
- page insertion/removal target shifts,
- malformed serialized outline rejection.

Behavioral coverage is marked with `PDF-DOC-OUTLINE-P3`.

## Affected Contracts

- `src/InkGen/pdf_generator.py`
- `tests/test_pdf_document_contract.py`
- `docs/pdf-generation.md`
- `docs/proofs/pdf-document-contract.md`

## Related Decisions

- ADR-0003: PDF Page Structure Metadata
