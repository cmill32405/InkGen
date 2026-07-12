# Parser Stress Fixture Contract Proof Obligations

This note applies the Definition of Done to the parser stress PDF fixture
builder.

## Scope

- `ParserStressBOMRow`
- `ParserStressFixtureSpec`
- `ScannedParserStressFixtureSpec`
- `build_parser_stress_pdf()`
- `build_scanned_parser_stress_pdf()`

## Dependency Review

Incoming dependencies:

- Document Intelligence fixture generation can call `build_parser_stress_pdf()`
  to obtain a deterministic `DocumentPDF` with title-block, BOM-table,
  transparency, rotated-page, page-box, extraction-truth, and grammar-truth
  cues.
- Document Intelligence fixture generation can call
  `build_scanned_parser_stress_pdf()` to obtain a deterministic image-only
  `DocumentPDF` that exercises the scan-like parser path where PDF text
  extraction should find no text operators.
- Package-root callers can import the builder and spec classes from `InkGen`.

Outgoing dependencies:

- The builder depends on public InkGen primitives: `Canvas`, `DocumentPDF`,
  `ComponentGroupPDF`, `RectanglePDF`, `LinePDF`, `TextPDF`, `DrawingStyle`,
  `TextStyle`, `Font`, `annotate_extraction_truth()`, and
  `annotate_grammar_truth()`.
- The scanned builder depends on public image/PDF primitives:
  `RasterImageAsset`, `ImagePDF`, `DocumentPDF`, `ComponentGroupPDF`, and the
  same truth helpers. It uses Pillow through InkGen's existing raster-image
  dependency surface to create deterministic PNG bytes.
- It does not depend on PDF object writer internals, document output exporters,
  private renderer helpers, or new third-party packages.

Contract edge:

- The fixture layer composes drawing primitives and truth helpers. It must not
  become the owner of PDF serialization or document-output rendering.
- Scan fixtures must remain image-only at the PDF operator level. Text visible
  inside the scan is raster content and must not be emitted through `TextPDF`.

## Structural Proof

- The public API exports `ParserStressBOMRow`, `ParserStressFixtureSpec`,
  `ScannedParserStressFixtureSpec`, `build_parser_stress_pdf()`, and
  `build_scanned_parser_stress_pdf()`.
- The dependency map documents fixture builders as an authoring layer above PDF
  primitives, raster image assets, and truth annotations.

## Behavioral Proof

- `tests/test_parser_stress_fixtures.py` builds a fixture and asserts rotated
  page metadata, TrimBox metadata, transparency resources, visible title/BOM
  text, extraction-truth records, grammar-truth records, and deterministic JSON
  emit.
- Failure-mode tests reject empty scalar fields, invalid rotations, invalid
  transparency flags, empty/non-row BOM collections, invalid BOM row fields, and
  invalid builder spec objects before rendering.
- Repeated default builds prove the builder works with InkGen's global style
  name uniqueness constraint while preserving rendered bytes and truth records.
- Scanned fixture tests build a PDF and assert the live image XObject path,
  absence of PDF text operators, absence of raw scan text bytes, extraction
  truth for the image and page region, grammar truth for image-only scan
  semantics, deterministic JSON, and repeated-build determinism.
- Scanned fixture failure-mode tests reject empty or non-string scan IDs, page
  labels, source names, and invalid builder spec objects before rendering.

## Functional Proof

- The builder returns a live `DocumentPDF`; no renderer bypass is introduced.
- `DocumentPDF.to_pdf_bytes()`, `DocumentPDF.extraction_truth()`, and
  `DocumentPDF.grammar_truth()` exercise the same live paths used by normal PDF
  documents.
- The scanned builder returns a live `DocumentPDF` whose raster page content is
  emitted by `ImagePDF` and `RasterImageAsset`, the same image path used by
  normal PDF documents.

## Mutation Gate

`tests/mutation/parser_stress_fixtures_cosmic_ray.toml` scopes mutation testing
to the new fixture module. Equivalent survivors must be documented in the slice
report.

Current scoped result: 120 proof-critical work items, 119 killed, 1
documented equivalent survivor. The survivor changes `rotation % 90 != 0` to
`rotation % 90 > 0`; Python modulo by a positive integer returns values in
`0..89`, so the predicates are equivalent for all integer rotations.

The scanned fixture slice runs mutation in a temporary Git worktree so Cosmic
Ray cannot leave a mutant in the active working tree.
