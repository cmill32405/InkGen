# ADR-0015: PDF Group Blend Modes

## Status

Accepted.

## Context

InkGen's PDF backend already uses deterministic `/ExtGState` resources for
drawing opacity. Standard PDF blend modes are another graphics-state feature
needed for richer parser-facing synthetic fixtures.

Blend modes are renderer-specific PDF graphics state. Placing them on
`DrawingStyle` would couple shared SVG/PDF/DXF style semantics to a PDF-only
concept, and placing them in document outputs would make document formats own
drawing rendering behavior.

## Decision

`ComponentGroupPDF` owns optional group-local PDF blend mode state:

- callers set it with `set_blend_mode(mode)`;
- callers clear it with `clear_blend_mode()`, `set_blend_mode(None)`, or
  `set_blend_mode("Normal")`;
- accepted non-default modes are the standard PDF names from the PDF graphics
  model;
- common spelling variants such as `soft-light`, `soft_light`, and
  `soft light` normalize to the canonical PDF name;
- the mode is serialized as `blend_mode` in `ComponentGroupPDF.parameters`;
- hydration validates serialized `blend_mode` before rendering;
- `DocumentPDF` emits one deterministic `/ExtGState` object per distinct blend
  mode and applies it with `/GSx gs` before group children.

## Out Of Scope

- SVG, DXF, DOCX, or neutral recipe blend-mode behavior.
- Style-owned blend modes.
- Opacity groups, isolated groups, knockout groups, gradients, and patterns.
- Non-standard or raw PDF blend mode names.

## Proof Obligations

- `PO-PDFGROUP-012`: configured blend modes emit deterministic `/ExtGState`
  resources and group content-stream `gs` operators on the `DocumentPDF` live
  path.
- `PO-PDFGROUP-013`: blend modes round-trip through group parameters and
  `ComponentGroupPDF.create_from_dict()`.
- `PO-PDFGROUP-014`: malformed blend modes fail before state mutation or
  hydration returns a group.
- `PO-PDFGROUP-015`: blend modes compose with existing group clipping without
  adding another group wrapper.

## Affected Contracts

- `src/InkGen/pdf_generator.py`
- `tests/test_pdf_generator.py`
- `docs/proofs/pdf-group-factory-payload-contract.md`
- `docs/pdf-generation.md`

## Related Decisions

- ADR-0002: Closed PDF renderer domain.
- ADR-0014: PDF group clip rectangles.
