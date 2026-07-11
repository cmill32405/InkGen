# ADR-0021: PDF FreeText Annotations

## Status

Accepted

## Context

InkGen's PDF backend supports deterministic page annotation arrays for links,
sticky text notes, highlights, square markup, circle markup, and line markup.
The PDF capability roadmap still listed other annotation subtypes as a document
structure gap. FreeText annotations are a bounded next subtype because they
place visible annotation text in a page rectangle without requiring a new
renderer-neutral drawing primitive or generic raw annotation dictionaries.

## Decision

`DocumentPDF.add_free_text_annotation()` adds deterministic PDF
`/Subtype /FreeText` annotations:

- The annotation targets an existing one-based page.
- The rectangle uses the existing finite positive-area PDF annotation rectangle
  validator and must fit inside the page MediaBox.
- Contents are non-empty Latin-1 strings.
- Text color uses the existing strict RGB annotation color contract.
- Font size is a finite positive number.
- The object emits a deterministic `/DA` default appearance using `/Helv` and
  a local `/DR` Helvetica resource dictionary.
- `free_text_annotations()` returns serialized entries in insertion order.
- `clear_free_text_annotations()` removes all FreeText entries.
- `DocumentPDF.parameters` and `DocumentPDF.create_from_dict()` preserve and
  validate FreeText entries.
- Page insertions and removals shift or delete FreeText annotations with the
  affected page indices.
- Rendered `/Annots` arrays emit FreeText after sticky text annotations and
  before highlight, square, circle, and line markup annotations.

## Out Of Scope

Rich text strings, appearance streams, author/title metadata, callouts,
rotation, border styles, background fill, opacity, replies, widgets, tagged PDF
structure, and raw generic annotation dictionaries remain out of scope.

## Proof Obligations

Proof obligations `PO-PDFDOC-046` through `PO-PDFDOC-048` in
`docs/proofs/pdf-document-contract.md` cover:

- FreeText annotation object and page `/Annots` array emission,
- rectangle, contents, color, and font-size validation,
- deterministic serialization round trips,
- page insertion/removal shifts,
- serialized payload rejection.

## Consequences

The PDF document annotation surface grows by one explicit public subtype without
adding dependencies or allowing arbitrary PDF dictionaries into the document
model.
