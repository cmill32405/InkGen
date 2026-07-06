# ADR-0009: PDF Text Annotations

## Status

Accepted.

## Context

InkGen's PDF backend already emits deterministic page annotation arrays for URI
links, internal page links, and named-destination links. Synthetic document
fixtures also need simple review/comment markers that PDF parsers can encounter
without requiring appearance streams, widgets, embedded files, or active content.

## Decision

`DocumentPDF.add_text_annotation()` adds deterministic PDF `/Subtype /Text`
annotations:

- The annotation targets an existing one-based page.
- The rectangle is a finite positive-area rectangle inside the page MediaBox.
- `contents` is a required non-empty Latin-1 literal string.
- `title` is optional; when present it is a non-empty Latin-1 literal string.
- `open` is a strict boolean. False is the default and is omitted from the
  serialized PDF object; true emits `/Open true`.
- `text_annotations()` and `DocumentPDF.parameters` preserve insertion order.
- `DocumentPDF.create_from_dict()` restores text annotations through the same
  public validation boundary.
- Page insertions/removals shift or delete text annotations with the affected
  page index.
- `to_pdf_bytes()` appends text annotations to each page's `/Annots` array after
  URI, internal page, and named-destination link annotations.

## Out Of Scope

- Rich appearance streams.
- Annotation replies and threading.
- File attachments, stamps, highlights, widgets, movies, sounds, and other
  non-text annotation subtypes.
- Non-Latin-1 annotation strings.

## Proof Obligations

- `PO-PDFDOC-025`: PDF text annotations emit and round-trip.
- `PO-PDFDOC-026`: PDF text annotations follow page mutations.
- `PO-PDFDOC-027`: Serialized text annotations fail explicitly.

## Affected Contracts

- `src/InkGen/pdf_generator.py`
- `tests/test_pdf_document_contract.py`
- `docs/pdf-generation.md`
- `docs/proofs/pdf-document-contract.md`

## Related Decisions

- ADR-0005: PDF URI link annotations.
- ADR-0006: PDF internal page links.
- ADR-0007: PDF named destinations.
