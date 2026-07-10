# ADR-0011: PDF Deep Outline Trees

## Status

Accepted.

## Context

InkGen supports flat PDF outlines, one-level nested outlines, and outline
expansion state. Synthetic document fixtures can require deeper bookmark
hierarchies to represent sections, subsections, and leaf topics without adding a
PDF dependency.

The existing outline model stores parent references by title. That model can
support deeper trees if parent resolution stays deterministic and ambiguous
title references continue to fail before rendering.

## Decision

`DocumentPDF.add_outline(parent=...)` supports arbitrary-depth outline trees:

- `parent=None` creates a top-level outline.
- `parent="<title>"` creates a child under an earlier outline whose title
  matches exactly one existing outline.
- Duplicate flat titles remain valid, but a duplicate title cannot be used as a
  parent because the reference is ambiguous.
- A later outline whose title matches an existing parent title is rejected
  because it would make already-stored child references ambiguous.
- `DocumentPDF.to_pdf_bytes()` emits deterministic `/Parent`, `/Prev`, `/Next`,
  `/First`, `/Last`, and `/Count` links for every depth.
- Parent `/Count` magnitude is the total number of descendant outline items.
  Expanded parents use a positive count; collapsed parents use a negative count.
- Page removal prunes any descendants whose parent chain no longer resolves.
- `DocumentPDF.outlines()` and `DocumentPDF.parameters` keep the existing flat
  insertion-ordered serialization shape.

## Out Of Scope

- Remote destinations.
- Named destinations as outline targets.
- Non-Latin-1 outline titles or parent names.
- Viewer-specific bookmark behavior beyond PDF outline dictionary links and the
  `/Count` sign.

## Proof Obligations

- `PO-PDFDOC-031`: Deep PDF outlines emit recursive parent, sibling, and child
  links.
- `PO-PDFDOC-032`: Deep outline parent references fail explicitly when
  ambiguous.
- `PO-PDFDOC-033`: Page removal prunes orphaned deep descendants.

## Affected Contracts

- `src/InkGen/pdf_generator.py`
- `tests/test_pdf_document_contract.py`
- `docs/pdf-generation.md`
- `docs/proofs/pdf-document-contract.md`

## Related Decisions

- ADR-0004: PDF flat outlines.
- ADR-0008: PDF nested outlines.
- ADR-0010: PDF outline expansion state.
