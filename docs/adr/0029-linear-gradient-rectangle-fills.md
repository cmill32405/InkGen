# ADR-0029: Linear-Gradient Rectangle Fills

## Status

Accepted.

## Context

Document Intelligence reconstructs detected page panels from measured geometry
and colors. Solid panels can already be emitted as InkGen rectangles, but a
gradient panel otherwise falls back to raster/vector tracing and can acquire
visible posterization bands.

A linear gradient depends on both style data and the geometry receiving the
paint. Adding a gradient value directly to `DrawingStyle.fill` would imply that
every drawing primitive and output backend supports gradient paint. That would
create silent or inconsistent behavior in paths that currently accept only
solid colors.

Earlier PDF graphics-state ADRs list gradients as outside their individual
scopes. They do not prohibit a later dedicated gradient contract, so this ADR
does not supersede them.

## Decision

- Add immutable `GradientStop` and `LinearGradientFill` values in
  `InkGen.gradients`.
- Attach the optional `fill_gradient` to rectangle components and the
  renderer-neutral `RectangleDrawing`, rather than widening the general
  `DrawingStyle.fill` contract.
- Require at least two strictly increasing stops. Offsets are finite values in
  `[0, 1]`; colors use the explicit `#rrggbb` form; angles are finite and
  normalized to `[0, 360)`.
- Define angles counter-clockwise from the visual horizontal. InkGen's
  top-left/y-down canvas therefore uses direction
  `(cos(angle), -sin(angle))`.
- Compute a user-space axis that spans the extreme projection of every
  rectangle corner. This preserves the requested physical angle for
  non-square rectangles.
- Emit SVG `<linearGradient>` paint servers with
  `gradientUnits="userSpaceOnUse"` and a `fill:url(...)` reference.
- Emit PDF axial shading dictionaries (`/ShadingType 2`). Two-stop gradients
  use a type-2 interpolation function; N-stop gradients use a type-3 stitching
  function composed of adjacent type-2 functions.
- Clip PDF shading to the rectangle path, including rounded corners, and paint
  the stroke separately.
- Preserve gradient data in rectangle serialization and in the optional
  `parameters` member of extraction-truth records for annotated gradient
  rectangles.
- Keep legacy solid rectangle payloads byte-shape compatible by omitting
  `fill_gradient` when absent.
- Reject gradient rectangles in DXF rather than flattening them to a solid
  HATCH.

## Alternatives Considered

### Put gradients in `DrawingStyle.fill`

Rejected. It broadens every primitive and renderer contract even though the
gradient axis requires component geometry and DXF has no equivalent contract.

### Rasterize gradients

Rejected. It loses parametric intent, introduces resolution concerns, and does
not solve Document Intelligence's posterization failure.

### Limit gradients to two stops

Rejected. Two stops cover the current corpus, but accepting ordered N-stop data
costs little and prevents another public schema migration.

### Approximate gradients with many solid bands

Rejected. Banding is the defect this feature is intended to remove.

## Consequences

- SVG, PDF, neutral rectangle, serialization, and extraction-truth contracts
  gain one opt-in field.
- Existing solid drawings and styles remain unchanged.
- PDF gains a deterministic shading resource registry but no package
  dependency.
- Flow-document parameters can preserve neutral gradient data. Output formats
  without a defined gradient renderer are not promised to reproduce it.
- DXF callers receive an explicit error for gradient rectangles.
- Radial gradients, mesh gradients, patterns, per-stop opacity, and
  non-rectangle gradient fills remain out of scope.
