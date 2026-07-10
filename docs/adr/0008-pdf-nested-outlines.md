# ADR-0008: PDF Nested Outlines

## Status

Accepted.

## Context

InkGen already supports deterministic top-level PDF outlines for synthetic PDF
fixtures. Parser-facing document fixtures also need simple outline hierarchy, but
the current PDF backend does not need arbitrary bookmark trees, remote
destinations, or non-Latin-1 title encoding.

## Decision

`DocumentPDF.add_outline()` accepts an optional `parent` argument for one-level
children. ADR-0011 extends the same title-based model to arbitrary-depth outline
trees.

- `parent=None` creates a top-level outline.
- `parent="<top-level title>"` creates a one-level child under an earlier unique
  top-level outline with the same exact title value.
- A later top-level outline whose title matches an existing child parent is
  rejected because it would make the child-parent relationship ambiguous.
- Parent titles use the same non-empty Latin-1 validation as outline titles.
- Missing, ambiguous, non-string, and non-Latin-1 parent values fail at the
  `DocumentPDF` boundary.
- `DocumentPDF.outlines()` and `DocumentPDF.parameters` include `parent` only
  for child entries.
- `DocumentPDF.create_from_dict()` restores outlines in serialized order, so a
  child can only hydrate after its parent.
- Page insertion/removal keeps outline page targets aligned and prunes children
  when their parent outline is removed.
- `DocumentPDF.to_pdf_bytes()` emits deterministic `/Outlines`, `/First`,
  `/Last`, `/Prev`, `/Next`, `/Parent`, `/Count`, and `/Dest` relationships for
  the root, top-level entries, and one-level child entries.

## Out Of Scope

- Grandchildren and arbitrary-depth outline trees were out of scope for this
  decision and are covered by ADR-0011.
- Arbitrary-depth expansion/collapse state was out of scope for this decision
  and is covered by ADR-0011.
- Remote destinations.
- Named destinations as outline targets.
- Non-Latin-1 outline titles or parent names.

## Proof Obligations

- `PO-PDFDOC-022`: Nested PDF outlines emit and prune orphans.
- `PO-PDFDOC-023`: Nested outline parents fail explicitly.
- `PO-PDFDOC-024`: Nested outline serialization preserves parents.

## Affected Contracts

- `src/InkGen/pdf_generator.py`
- `tests/test_pdf_document_contract.py`
- `docs/pdf-generation.md`
- `docs/proofs/pdf-document-contract.md`

## Related Decisions

- ADR-0003: PDF page structure metadata.
- ADR-0004: PDF flat outlines.
- ADR-0006: PDF internal page links.
- ADR-0007: PDF named destinations.
- ADR-0010: PDF outline expansion state.
- ADR-0011: PDF deep outline trees.
