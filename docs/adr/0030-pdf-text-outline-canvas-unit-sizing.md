# ADR-0030: PDF Text Outlines Use Canvas-Unit Sizing

## Status

Accepted.

## Context

`DocumentPDF` applies the page unit scale to component content once, as
required by ADR-0028. A drawing `Font(size=6.75)` therefore renders as
6.75 canvas units before the PDF page transform.

`TextComponent._compute_outline()` instead converted that value from points to
CSS pixels by multiplying it by `96 / 72`. The resulting component geometry
was exactly 4/3 wider than the PDF ink. `Layer.add_component_group()` consumed
the inflated points and rejected text that remained inside the canvas.

SVG and DXF have established point-based conversion contracts. Changing those
contracts caused DXF text-height and SVG table-layout regressions, so this
decision is limited to the PDF boundary where content operators already use
canvas units.

## Decision

- `TextComponent` provides an overridable outline-size conversion hook.
- Generic, SVG, DXF, and document-flow text retain their established
  point-based conversion contracts.
- `TextPDF` overrides the hook so precise and fallback outlines use the same
  raw canvas-unit size as its PDF `Tf` operator.
- PDF text operators continue to inherit the document page transform once.
- No dependency or serialized field is added.

## Consequences

- PDF text bounds describe the ink emitted by `TextPDF`.
- Canvas boundary and collision checks no longer reject in-canvas PDF text due
  to a 4/3 outline inflation.
- SVG, DXF, table, and document-flow output dimensions remain compatible.
- Subclasses can define an output-specific outline unit without duplicating
  shaping and fallback logic.
