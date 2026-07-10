# ADR-0013: PDF Highlight Annotations

## Status

Accepted.

## Context

InkGen's PDF backend already supports link annotations and text annotations for
synthetic review and parser fixtures. Highlight annotations are a common PDF
markup primitive and are useful for drawing attention to parser-facing regions
without changing the underlying page content stream.

The PDF renderer remains dependency-free and closed. Adding a generic raw
annotation API would expose unsupported PDF dictionary surface and weaken the
renderer contract. A dedicated highlight API gives callers a bounded fixture
primitive while keeping annotation serialization deterministic and local to
`DocumentPDF`.

## Decision

`DocumentPDF` supports rectangular PDF highlight annotations through
`add_highlight_annotation()`:

- each highlight targets an existing page;
- each rectangle is finite, positive-area, and inside the target page MediaBox;
- color is accepted as `#rrggbb` or a serialized RGB channel triple with values
  from 0.0 through 1.0;
- optional contents are non-empty Latin-1 literal PDF strings;
- `/QuadPoints` are derived from the rectangle corners;
- highlights are serialized in `DocumentPDF.parameters` and hydrate through
  `DocumentPDF.create_from_dict()`;
- page insertions and removals shift or delete highlight metadata with the page
  indices;
- rendered `/Annots` arrays emit highlights after links and text annotations.

## Out Of Scope

- Multi-quad text-selection highlights.
- Rich appearance streams.
- Annotation replies, review states, popups, widgets, stamps, attachments, and
  arbitrary raw annotation dictionaries.
- Tagged PDF structure.
- Unicode annotation strings beyond the current Latin-1 literal-string policy.

## Proof Obligations

- `PO-PDFDOC-034`: PDF highlight annotations emit deterministic `/Highlight`
  annotation objects and round-trip through parameters.
- `PO-PDFDOC-035`: highlight annotation page indices follow insertions and
  removals.
- `PO-PDFDOC-036`: malformed serialized highlight annotation payloads fail before
  rendering.

## Affected Contracts

- `src/InkGen/pdf_generator.py`
- `tests/test_pdf_document_contract.py`
- `docs/proofs/pdf-document-contract.md`
- `docs/pdf-generation.md`

## Related Decisions

- ADR-0002: Closed PDF renderer domain.
- ADR-0005: PDF URI link annotations.
- ADR-0006: PDF internal page links.
- ADR-0007: PDF named destinations.
- ADR-0009: PDF text annotations.
