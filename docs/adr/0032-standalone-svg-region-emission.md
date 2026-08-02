# ADR-0032: Standalone SVG Region Emission

## Status

Accepted.

## Context

Document verification, redaction preview, citation evidence, audit trails, and
visual diffs need a faithful view of a bounded source region without requiring
a page rasterizer. InkGen already owns HarfBuzz shaping, fontTools glyph-outline
generation, neutral drawing primitives, and SVG fragment generation. The PDF
parser can expose original embedded font-program bytes, but the existing
`outline_for_text()` API accepted only a filesystem path.

Ordinary SVG `<text>` depends on fonts installed on the viewing system. That
would make the same evidence render differently on different machines and
would weaken read-to-write fidelity.

## Decision

- `outline_for_text_bytes()` accepts an in-memory sfnt-compatible font program
  and shares the existing outline implementation with `outline_for_text()`.
- `PositionedTextRun` requires exactly one explicit font path or font program.
  It never falls back to a system font.
- `emit_svg_region()` converts each positioned run to an SVG path, materializes
  existing neutral primitives through `OutputFormat.SVG`, and applies one
  rectangular user-space clip window.
- The result is a complete SVG document with an explicit viewport, `viewBox`,
  clip path, and optional background.
- Primitive output may refer only to in-document fragment identifiers or
  embedded `data:` resources. Scripts, foreign objects, external references,
  and font-dependent `<text>` fragments fail closed.
- The region layer composes existing renderers. It does not own drawing
  geometry, font shaping, font discovery, PDF parsing, or rasterization.
- No package dependency is added.

## Consequences

- Parser-extracted TrueType/OpenType font bytes can drive exact glyph outlines
  without temporary files.
- Region SVGs render independently of installed fonts and network access.
- The API can also include existing self-contained InkGen image fragments, but
  raster decoding and alpha policy remain owned by `RasterImageAsset`.
- Raw Type 1 and other programs unsupported by `fontTools.ttLib.TTFont` fail
  explicitly. InkGen does not claim universal PDF-font outline support.
- `font_size_px` uses the existing text-outline scale. PDF point sizes must be
  converted by the caller when a one-to-one CSS pixel scale is required.
- Text remains represented by geometry, with the source string retained in an
  SVG `<title>` and `aria-label`; it is not selectable SVG text.

## Proof And Verification

Condition `SVG-REGION-P1` is specified in
`docs/proofs/svg-region-emission-contract.md` and exercised by
`tests/test_region_svg_contract.py`.

## Related Decisions

- ADR-0002: Closed PDF renderer domain.
- ADR-0023: PDF text encoding boundary.
- ADR-0030: PDF text outlines use canvas-unit sizing.
