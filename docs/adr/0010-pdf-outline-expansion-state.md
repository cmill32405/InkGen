# ADR-0010: PDF Outline Expansion State

## Status

Accepted.

## Context

InkGen supports deterministic top-level and one-level nested PDF outlines.
Synthetic fixtures need to represent whether a parent bookmark is initially
expanded or collapsed because PDF parsers and viewers expose this through the
sign of the outline item's `/Count` value. This can be added inside the existing
outline metadata model without adding dependencies or changing the drawing
component architecture.

## Decision

`DocumentPDF.add_outline()` accepts an `expanded` keyword argument:

- `expanded=True` is the default.
- `expanded=False` marks a parent outline as collapsed.
- `expanded` is a strict boolean; truthy or falsy stand-ins are rejected.
- `DocumentPDF.outlines()` and `DocumentPDF.parameters` include
  `expanded=False` only for collapsed outline entries. Expanded entries omit the
  field for backward-compatible serialization.
- `DocumentPDF.create_from_dict()` restores missing `expanded` values as `True`
  and validates provided values through the public boundary.
- Page insertion/removal preserves each outline's expansion state.
- `DocumentPDF.to_pdf_bytes()` emits positive child `/Count` values for expanded
  one-level parents and negative child `/Count` values for collapsed one-level
  parents.

## Out Of Scope

- Arbitrary-depth outline trees.
- Viewer-specific bookmark UI behavior beyond the PDF `/Count` sign.
- Remote destinations.
- Named destinations as outline targets.
- Non-Latin-1 outline titles or parent names.

## Proof Obligations

- `PO-PDFDOC-028`: Collapsed PDF outline parents emit negative child counts.
- `PO-PDFDOC-029`: Outline expansion state follows page mutations.
- `PO-PDFDOC-030`: Serialized outline expansion state fails explicitly.

## Affected Contracts

- `src/InkGen/pdf_generator.py`
- `tests/test_pdf_document_contract.py`
- `docs/pdf-generation.md`
- `docs/proofs/pdf-document-contract.md`

## Related Decisions

- ADR-0004: PDF flat outlines.
- ADR-0008: PDF nested outlines.
