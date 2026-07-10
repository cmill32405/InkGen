# ADR-0012: PDF Smooth Path Commands

## Status

Accepted.

## Context

InkGen `PathCommand` already accepts SVG-style smooth path commands `S` and
`T`, and SVG output preserves them. Earlier PDF output rejected those commands
because the smooth-control reflection semantics were not implemented.

Synthetic drawing fixtures benefit from preserving the same neutral path command
surface across SVG and PDF when the conversion is deterministic and local.

## Decision

`PathPDF` supports SVG smooth path commands:

- `S` commands consume points in `(control_2, end)` pairs and emit PDF cubic
  `c` operators.
- `T` commands consume one endpoint per segment and emit PDF cubic `c`
  operators by converting the reflected quadratic control point to cubic
  controls.
- A smooth cubic segment reflects the previous cubic command's second control
  point when the previous segment was `C` or `S`; otherwise the current point is
  used as the first cubic control.
- A smooth quadratic segment reflects the previous quadratic command's control
  point when the previous segment was `Q` or `T`; otherwise the current point is
  used as the quadratic control.
- Multiple `S` or `T` segments inside one command reflect from the immediately
  preceding segment.
- `S` with an odd number of points and `T` with no endpoints fail explicitly
  before PDF bytes are emitted.

## Out Of Scope

- Full SVG elliptical arc geometry; `A` remains the existing endpoint-line
  fallback.
- SVG fill-rule semantics.
- Bézier-to-DXF curve fidelity changes.

## Proof Obligations

- `PO-PATH-013`: PDF smooth cubic and quadratic path commands emit reflected
  cubic operators.
- `PO-PATH-014`: Malformed smooth path commands fail explicitly before partial
  PDF output.

## Affected Contracts

- `src/InkGen/pdf_generator.py`
- `tests/test_path_contract.py`
- `docs/proofs/path-renderer-contract.md`

## Related Decisions

- ADR-0002: Closed PDF renderer domain.
