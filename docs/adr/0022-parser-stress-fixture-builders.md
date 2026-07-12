# ADR-0022: Parser Stress Fixture Builders

## Status

Accepted.

## Context

Document Intelligence needs repeatable PDF fixtures that exercise parser-facing
surfaces such as title blocks, BOM tables, rotated pages, transparency, page
boxes, and truth records. Ad hoc test construction can drift from the public
InkGen authoring contract or accidentally reach into renderer internals.

## Decision

InkGen exposes `ParserStressFixtureSpec`, `ParserStressBOMRow`, and
`build_parser_stress_pdf()` from a new `parser_stress_fixtures.py` module. It
also exposes `ScannedParserStressFixtureSpec` and
`build_scanned_parser_stress_pdf()` for scan-like image-only PDF fixtures. The
builders compose existing public PDF primitives, raster image assets, page
metadata APIs, and extraction/grammar truth helpers. They do not add a
dependency and do not own PDF serialization behavior.

The fixture builder uses deterministic geometry and content. Because InkGen
styles currently require globally unique names, the builder allocates unique
style names when the same fixture is built repeatedly in one Python process;
rendered PDF bytes and emitted truth records remain stable.

## Consequences

- Parser fixture authoring has a named public boundary.
- Renderer internals remain owned by `pdf_generator.py`.
- Document outputs do not own drawing rendering.
- Future parser-stress variants should extend this module or add sibling
  fixture modules that compose public authoring APIs.
- Image-only scan fixtures are represented as PDF image XObjects through the
  normal `RasterImageAsset` and `ImagePDF` live path, not as custom PDF writer
  objects.
