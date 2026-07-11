# ADR-0020: PDF Line Annotations

## Status

Accepted.

## Context

InkGen's PDF backend supports explicit link, text, highlight, square, and circle
annotation APIs for deterministic parser and review fixtures. Line annotations
are a standard PDF markup primitive for callouts, leaders, and review marks
that should not alter the underlying page content stream.

The PDF renderer remains dependency-free and closed. A generic raw annotation
API would expose unproven PDF dictionary surface and weaken the renderer
contract. A dedicated line annotation API gives callers one bounded markup
primitive while preserving deterministic serialization local to `DocumentPDF`.

## Decision

`DocumentPDF` supports PDF line annotations through `add_line_annotation()`:

- each line targets an existing page;
- each endpoint is a finite point inside the target page MediaBox, using the
  same bottom-left page coordinate frame as existing annotation rectangles;
- endpoints must be distinct;
- the PDF `/Rect` is derived internally as a positive-area envelope around the
  line segment, clamped to the page MediaBox;
- border color is accepted as `#rrggbb` or a serialized RGB channel triple with
  values from 0.0 through 1.0;
- optional contents are non-empty Latin-1 literal PDF strings;
- rendered objects use `/Subtype /Line`, `/L`, and `/Border [0 0 1]`;
- lines are serialized in `DocumentPDF.parameters` and hydrate through
  `DocumentPDF.create_from_dict()`;
- page insertions and removals shift or delete line metadata with the page
  indices;
- rendered `/Annots` arrays emit lines after links, text annotations,
  highlight annotations, square annotations, and circle annotations.

## Out Of Scope

- Rich appearance streams.
- Arrowheads, leader lines, captions, interior colors, and custom border
  styles.
- Annotation replies, review states, popups, widgets, stamps, attachments, and
  arbitrary raw annotation dictionaries.
- Tagged PDF structure.
- Unicode annotation strings beyond the current Latin-1 literal-string policy.

## Proof Obligations

- `PO-PDFDOC-043`: PDF line annotations emit deterministic `/Line` annotation
  objects and round-trip through parameters.
- `PO-PDFDOC-044`: line annotation page indices follow insertions and removals.
- `PO-PDFDOC-045`: malformed serialized line annotation payloads fail before
  rendering.

## Affected Contracts

- `DocumentPDF.add_line_annotation()`
- `DocumentPDF.clear_line_annotations()`
- `DocumentPDF.line_annotations()`
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
- ADR-0019: PDF circle annotations.
