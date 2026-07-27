# PDF Text Boundary Unit Contract

Condition: `TEXT-BOUNDARY-UNITS-P1`

## Claim

`TextPDF` outlines and fallback geometry consume the same numeric canvas-unit
font size as PDF text operators. `Layer.add_component_group()` accepts PDF
text whose ink is inside the canvas and continues to reject real overflow.
Generic, SVG, DXF, table, and document-flow point conversions are unchanged.

## Dependency And Contract Review

- `TextComponent.points`, `bbox`, and `convex_hull` feed component-group
  boundary and collision checks.
- `Layer.add_component_group()` calls `Canvas.boundary_check(group.points)`.
- `TextSVG`, `TextPDF`, and DXF `TEXT` materialize neutral `TextDrawing`, but
  their output formats have different established unit conversions.
- ADR-0028 requires PDF component operators to remain in canvas units and
  inherit the page scale once.
- SVG uses CSS-pixel conversion, DXF uses point-to-millimetre conversion, and
  SVG table metrics use point-to-millimetre conversion.
- Paragraph and document outputs consume `TextStyle.font.size` as points.
- No import, package, serialization, or registry dependency changes.

## Three-Level Proof

- **Structural:** `TextComponent` owns a size-conversion hook and `TextPDF`
  overrides it with raw PDF canvas units.
- **Behavioral:** the 6.75-unit DejaVu Sans probe matches a direct outline,
  empty/minimum PDF fallback boundaries are exact, generic fallback retains
  point conversion, and SVG/DXF emission values remain unchanged.
- **Functional:** the former 4/3 probe passes through
  `Layer.add_component_group()` on a canvas 0.5 unit wider than rendered ink;
  a canvas 0.5 unit narrower still raises `ComponentGroupOffCanvas`.

## Counterexamples

Pre-change measurement for `A email@yourbusinessname.co.nz`:

- component width: 153.812988
- direct 6.75-unit outline width: 115.359741
- ratio: 1.333333
- 115.859741-unit canvas result: rejected

The condition test reproduces that boundary and passes after the fix.

## Mutation Evidence

The final scoped Cosmic Ray v3 campaign covers the base conversion/fallback
arithmetic and the PDF-specific outline hook. All 91 workers completed
normally: 90 mutations were killed and one survived. The database SHA-256 is
`5E9921FB5B28290303DDD27B1802EDF4C05ACAB46DC585B5AE6A43A002277F0E`.

The survivor changes the fallback height floor from `0.5` to `-0.5`.
`Font.size` normalizes every accepted numeric or named input to at least
`1.0`, so both floors return the same reachable height. Property and named
domain tests pin that equivalence. `test_text_boundary_unit_mutation_evidence.py`
also pins the database digest, outcome counts, and survivor identity.

## Residuals

Text fitting's explicit `size_px` API remains pixel-based. SVG and DXF retain
their established output-specific conversions rather than sharing a universal
drawing-text unit. Global style and component-group names remain registered
identities; probes must use unique names.
