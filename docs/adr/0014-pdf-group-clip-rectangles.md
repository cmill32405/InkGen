# ADR-0014: PDF Group Clip Rectangles

## Status

Accepted.

## Context

InkGen's PDF backend now supports enough vector, image, font, annotation, and
graphics-state primitives to build useful synthetic parser fixtures. Clipping is
the next useful graphics-state feature because technical drawings often need a
bounded viewport or cropped callout area.

The PDF renderer remains dependency-free and closed. A raw PDF clipping API or
an arbitrary path clip attached to shared drawing style would expand the proven
surface area and couple renderer-specific state into neutral drawing recipes.

## Decision

`ComponentGroupPDF` owns an optional rectangular clip rectangle:

- callers set it with `set_clip_rect((x, y, width, height))`;
- callers clear it with `clear_clip_rect()`;
- values are finite non-boolean numbers with positive width and height;
- rectangles use InkGen document coordinates, matching child PDF primitives;
- the rectangle is serialized as `clip_rect` in `ComponentGroupPDF.parameters`;
- hydration validates serialized `clip_rect` before rendering;
- rendering wraps group children in `q`, `re`, `W`, `n`, and `Q`.

## Out Of Scope

- Arbitrary path clipping.
- Style-owned clipping state.
- SVG, DXF, DOCX, or neutral recipe clipping.
- Opacity groups, blend modes, gradients, and patterns.
- Clip rectangles constrained to a specific page MediaBox.

## Proof Obligations

- `PO-PDFGROUP-008`: configured clip rectangles emit deterministic PDF clipping
  operators before child component operators.
- `PO-PDFGROUP-009`: clip rectangles round-trip through group parameters and
  `ComponentGroupPDF.create_from_dict()`.
- `PO-PDFGROUP-010`: malformed clip rectangles fail before state mutation or
  hydration returns a group.
- `PO-PDFGROUP-011`: `DocumentPDF` consumes clipped groups on the live page
  content path without relaxing the closed component guard.

## Affected Contracts

- `src/InkGen/pdf_generator.py`
- `tests/test_pdf_generator.py`
- `docs/proofs/pdf-group-factory-payload-contract.md`
- `docs/pdf-generation.md`

## Related Decisions

- ADR-0002: Closed PDF renderer domain.
- ADR-0012: PDF smooth path commands.
