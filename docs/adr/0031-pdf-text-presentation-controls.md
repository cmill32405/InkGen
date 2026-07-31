# ADR-0031: PDF Text Presentation Controls

## Status

Accepted.

## Context

Document-recreation workflows sometimes preserve a chart or figure as raster
pixels while still needing its labels in the searchable PDF text layer. A
visible replacement run damages the preserved pixels. InkGen therefore needs a
text run that remains extractable but paints no glyphs.

Font substitution also creates cumulative advance-width error. Changing font
size can match either the original height or width, but not both. PDF character
spacing can correct the run width without changing the selected face or em size.

`TextStyle` is the shared owner of text presentation. `TextPDF` is the concrete
owner of PDF operators. Boundary and collision geometry depends on the same
style and must not ignore spacing that changes rendered width.

## Decision

- `TextStyle.visible` is a validated boolean and defaults to `True`.
- `TextStyle.character_spacing` is a validated finite signed number and
  defaults to `0.0`.
- Both fields serialize. Older payloads that omit them hydrate with their
  defaults.
- `TextPDF` emits `3 Tr` only when `visible` is false.
- `TextPDF` emits `Tc` only when character spacing is nonzero.
- Operators remain scoped inside the component's `q`/`Q` and `BT`/`ET` pairs.
- PDF alignment width includes one spacing interval between adjacent
  characters, never one after the final character.
- Text bounds conservatively extend right for positive spacing and left for
  negative spacing, using the largest interval count of any normalized line.
- Default styles emit no new operators, preserving existing PDF bytes.

## Consequences

- Searchable invisible overlays can coexist with frozen chart pixels.
- Per-run tracking can match source width while retaining height-true font size.
- Mutating character spacing invalidates cached text geometry.
- Invisible text still has geometry and participates in canvas-boundary checks;
  visibility controls paint, not document structure or placement.
- PDF interprets character spacing in the same canvas units as its text size,
  consistent with ADR-0030 and the page transform from ADR-0028.
- SVG, DXF, DOCX, HTML, RTF, Markdown, and plain-text mappings are unchanged.
  They do not yet consume these two presentation fields.
- No package dependency is added.

## Proof And Verification

Condition `PDF-TEXT-PRESENTATION-P3` is specified in
`docs/proofs/pdf-text-presentation-contract.md` and exercised by
`tests/test_pdf_text_presentation_contract.py`.

## Related Decisions

- ADR-0002: Closed PDF renderer domain.
- ADR-0023: PDF text encoding boundary.
- ADR-0028: PDF standard page coordinate scaling.
- ADR-0030: PDF text outlines use canvas-unit sizing.
