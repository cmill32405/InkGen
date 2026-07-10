# ADR-0016: PDF Square Annotations

## Status

Accepted.

## Context

InkGen's PDF backend supports links, text annotations, and highlight annotations
for deterministic parser and review fixtures. Square annotations are a standard
PDF markup primitive for drawing bounded rectangular review regions without
changing the underlying page content stream.

The PDF renderer remains dependency-free and closed. A generic raw annotation
API would expose unproven PDF dictionary surface and weaken the renderer
contract. A dedicated square annotation API gives callers one bounded markup
primitive while preserving deterministic serialization local to `DocumentPDF`.

## Decision

`DocumentPDF` supports rectangular PDF square annotations through
`add_square_annotation()`:

- each square targets an existing page;
- each rectangle is finite, positive-area, and inside the target page MediaBox;
- border color is accepted as `#rrggbb` or a serialized RGB channel triple with
  values from 0.0 through 1.0;
- optional contents are non-empty Latin-1 literal PDF strings;
- rendered objects use `/Subtype /Square` and `/Border [0 0 1]`;
- squares are serialized in `DocumentPDF.parameters` and hydrate through
  `DocumentPDF.create_from_dict()`;
- page insertions and removals shift or delete square metadata with the page
  indices;
- rendered `/Annots` arrays emit squares after links, text annotations, and
  highlight annotations.

## Out Of Scope

- Rich appearance streams.
- Fill colors and custom border styles.
- Annotation replies, review states, popups, widgets, stamps, attachments, and
  arbitrary raw annotation dictionaries.
- Tagged PDF structure.
- Unicode annotation strings beyond the current Latin-1 literal-string policy.

## Proof Obligations

- `PO-PDFDOC-037`: PDF square annotations emit deterministic `/Square`
  annotation objects and round-trip through parameters.
- `PO-PDFDOC-038`: square annotation page indices follow insertions and
  removals.
- `PO-PDFDOC-039`: malformed serialized square annotation payloads fail before
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
- ADR-0013: PDF highlight annotations.
