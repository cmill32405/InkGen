# ADR-0002: Closed PDF Renderer Domain

## Status

Accepted

## Context

The grammar truth proof requires a noninterference claim: changing only grammar
annotation state must not change rendered PDF bytes. That claim cannot be proven
while `DocumentPDF` dynamically renders arbitrary objects with a callable
`generate_pdf()` method, because a custom object could read grammar annotation
state during rendering.

InkGen's PDF backend is intended to be deterministic, dependency-free, and
proof-friendly. The renderer contract should therefore favor a closed,
explicitly reviewed component set over arbitrary dynamic extension.

## Decision

`DocumentPDF` will render only `ComponentGroupPDF` groups.

`ComponentGroupPDF` will accept and render only the built-in PDF component
classes:

- `RectanglePDF`
- `LinePDF`
- `ArcPDF`
- `QuadraticBezierPDF`
- `CubicBezierPDF`
- `PathPDF`
- `RegularPolygonPDF`
- `PolygonalPDF`
- `CirclePDF`
- `TextPDF`

`ComponentGroupPDF.add_component()` rejects components outside this closed set.
`ComponentGroupPDF.generate_pdf()` repeats the same check before rendering so
private `_components` mutation fails before unsupported dynamic code runs.

Custom dynamic `generate_pdf()` components are outside the supported and proven
PDF renderer contract.

## Consequences

- The PDF render path is small enough to support static path proof for grammar
  truth noninterference.
- Adding a new built-in PDF component requires updating the closed component
  tuple, tests, docs, and proof obligations together.
- The PDF backend gives up arbitrary renderer extension through duck typing.
- Renderer-neutral drawing recipes remain the preferred extension surface for
  synthetic drawing construction.

## Proof And Verification

Proof obligation `PO-GT-004` in `docs/proofs/grammar-truth.md` depends on this
decision.

Behavioral coverage:

- `ComponentGroupPDF.add_component()` rejects custom PDF-like components.
- `ComponentGroupPDF.generate_pdf()` rejects private mutation with unsupported
  components.
- `DocumentPDF.to_pdf_bytes()` rejects non-`ComponentGroupPDF` groups.
- Existing built-in PDF components still render and round-trip.

## Affected Contracts

- `src/InkGen/pdf_generator.py`
- `tests/test_pdf_generator.py`
- `docs/proofs/grammar-truth.md`
- `docs/dependency-map.md`
- `docs/pdf-generation.md`

## Related Decisions

- ADR-0001: PDF Grammar Truth Annotations
