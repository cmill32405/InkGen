# ADR-0019: PDF Circle Annotations

## Status

Accepted.

## Context

InkGen's PDF backend supports explicit link, text, highlight, and square
annotation APIs for deterministic parser and review fixtures. Circle
annotations are a standard PDF markup primitive for drawing elliptical review
regions without changing the underlying page content stream.

The PDF renderer remains dependency-free and closed. A generic raw annotation
API would expose unproven PDF dictionary surface and weaken the renderer
contract. A dedicated circle annotation API gives callers one bounded markup
primitive while preserving deterministic serialization local to `DocumentPDF`.

## Decision

`DocumentPDF` supports elliptical PDF circle annotations through
`add_circle_annotation()`:

- each circle targets an existing page;
- each rectangle is finite, positive-area, and inside the target page MediaBox;
- border color is accepted as `#rrggbb` or a serialized RGB channel triple with
  values from 0.0 through 1.0;
- optional contents are non-empty Latin-1 literal PDF strings;
- rendered objects use `/Subtype /Circle` and `/Border [0 0 1]`;
- circles are serialized in `DocumentPDF.parameters` and hydrate through
  `DocumentPDF.create_from_dict()`;
- page insertions and removals shift or delete circle metadata with the page
  indices;
- rendered `/Annots` arrays emit circles after links, text annotations,
  highlight annotations, and square annotations.

## Out Of Scope

- Rich appearance streams.
- Fill colors and custom border styles.
- Annotation replies, review states, popups, widgets, stamps, attachments, and
  arbitrary raw annotation dictionaries.
- Tagged PDF structure.
- Unicode annotation strings beyond the current Latin-1 literal-string policy.

## Proof Obligations

- `PO-PDFDOC-040`: PDF circle annotations emit deterministic `/Circle`
  annotation objects and round-trip through parameters.
- `PO-PDFDOC-041`: circle annotation page indices follow insertions and
  removals.
- `PO-PDFDOC-042`: malformed serialized circle annotation payloads fail before
  rendering.

## Affected Contracts

- `DocumentPDF.add_circle_annotation()`
- `DocumentPDF.clear_circle_annotations()`
- `DocumentPDF.circle_annotations()`
- `DocumentPDF.parameters`
- `DocumentPDF.create_from_dict()`
- `DocumentPDF.to_pdf_bytes()`
- `DocumentPDF.add_page()`
- `DocumentPDF.remove_page()`

## Related Decisions

- ADR-0002: Closed PDF renderer domain.
- ADR-0005: PDF URI link annotations.
- ADR-0006: PDF internal page links.
- ADR-0007: PDF named destinations.
- ADR-0009: PDF text annotations.
- ADR-0013: PDF highlight annotations.
- ADR-0016: PDF square annotations.
