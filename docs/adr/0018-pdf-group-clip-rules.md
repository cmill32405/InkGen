# ADR-0018: PDF Group Clip Rules

## Status

Accepted.

## Context

InkGen's PDF backend supports rectangular and closed path group clipping. PDF
has two clipping operators: nonzero winding (`W`) and even-odd (`W*`). The
backend previously emitted only `W`, which limited fixtures that need holes or
self-intersecting clipped regions.

Clip fill rule is PDF graphics-state metadata. It should remain local to
`ComponentGroupPDF` rather than moving into shared `DrawingStyle` or
renderer-neutral drawing recipes.

## Decision

`ComponentGroupPDF` supports group clip-rule selection:

- `set_clip_rule(rule)` accepts `nonzero`, `nonzero-winding`, `winding`,
  `evenodd`, and `even-odd` spellings;
- `None` and `clear_clip_rule()` reset the rule to `nonzero`;
- default `nonzero` is not serialized;
- non-default `evenodd` serializes as `clip_rule: "evenodd"`;
- `ComponentGroupPDF.create_from_dict()` validates serialized clip rules before
  returning a group;
- `generate_pdf()` emits `W*` for every configured group clip when the rule is
  `evenodd`, and emits `W` for the default rule.

## Out Of Scope

- Per-clip fill-rule selection inside one group.
- SVG, DXF, DOCX, or neutral recipe clipping rules.
- Text clipping and raw PDF clipping operators.
- Opacity groups, gradients, and patterns.

## Proof Obligations

- `PO-PDFGROUP-020`: even-odd clip rules emit `W*` for rectangular and path
  group clips.
- `PO-PDFGROUP-021`: non-default clip rules round-trip through group parameters
  and default rules remain unserialized.
- `PO-PDFGROUP-022`: malformed clip rules fail before state mutation or
  hydration returns a group.

## Affected Contracts

- `src/InkGen/pdf_generator.py`
- `tests/test_pdf_generator.py`
- `docs/proofs/pdf-group-factory-payload-contract.md`
- `docs/pdf-generation.md`

## Related Decisions

- ADR-0002: Closed PDF renderer domain.
- ADR-0014: PDF group clip rectangles.
- ADR-0017: PDF group clip paths.
