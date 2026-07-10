# ADR-0017: PDF Group Clip Paths

## Status

Accepted.

## Context

InkGen's PDF backend already supports rectangular group clipping. Technical
drawing fixtures sometimes need non-rectangular clipped regions, but clipping is
PDF graphics-state metadata and should not move into shared `DrawingStyle` or
renderer-neutral drawing recipes.

The PDF renderer remains dependency-free and closed. A raw PDF clipping API
would expose unvalidated PDF operators. A bounded `PathCommand`-based clip-path
API reuses InkGen's existing path validation and PDF path conversion while
keeping the state local to `ComponentGroupPDF`.

## Decision

`ComponentGroupPDF` supports optional closed path clipping through
`set_clip_path()`:

- callers pass a non-empty sequence of `PathCommand` objects or serialized path
  command mappings;
- commands are cloned before storage so later caller mutation cannot alter group
  state;
- the path must start with `M` and end with `Z`;
- supported commands are the same SVG-style commands accepted by `PathPDF`;
- command arity is validated before state mutation;
- the path is serialized as `clip_path` in `ComponentGroupPDF.parameters`;
- hydration validates serialized `clip_path` before returning a group;
- rendering emits the path operators followed by `W` and `n` before child
  operators;
- path clipping composes with rectangular clipping and blend modes inside one
  group graphics-state wrapper.

## Out Of Scope

- Raw PDF clipping operators.
- Style-owned clipping state.
- SVG, DXF, DOCX, or neutral recipe clipping.
- Open clipping paths.
- Fill-rule selection, even-odd clipping, and text clipping.
- Clip paths constrained to a specific page MediaBox.

## Proof Obligations

- `PO-PDFGROUP-016`: configured clip paths emit deterministic PDF clipping
  operators before child component operators.
- `PO-PDFGROUP-017`: clip paths round-trip through group parameters and
  `ComponentGroupPDF.create_from_dict()`.
- `PO-PDFGROUP-018`: malformed clip paths fail before state mutation or
  hydration returns a group.
- `PO-PDFGROUP-019`: path clipping composes with rectangular clipping and blend
  state on the `DocumentPDF` live path.

## Affected Contracts

- `src/InkGen/pdf_generator.py`
- `tests/test_pdf_generator.py`
- `tests/test_pdf_component_factory_payload_contract.py`
- `docs/proofs/pdf-group-factory-payload-contract.md`
- `docs/pdf-generation.md`

## Related Decisions

- ADR-0002: Closed PDF renderer domain.
- ADR-0012: PDF smooth path commands.
- ADR-0014: PDF group clip rectangles.
- ADR-0015: PDF group blend modes.
