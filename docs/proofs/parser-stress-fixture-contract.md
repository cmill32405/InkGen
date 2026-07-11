# Parser Stress Fixture Contract Proof Obligations

This note applies the Definition of Done to the parser stress PDF fixture
builder.

## Scope

- `ParserStressBOMRow`
- `ParserStressFixtureSpec`
- `build_parser_stress_pdf()`

## Dependency Review

Incoming dependencies:

- Document Intelligence fixture generation can call `build_parser_stress_pdf()`
  to obtain a deterministic `DocumentPDF` with title-block, BOM-table,
  transparency, rotated-page, page-box, extraction-truth, and grammar-truth
  cues.
- Package-root callers can import the builder and spec classes from `InkGen`.

Outgoing dependencies:

- The builder depends on public InkGen primitives: `Canvas`, `DocumentPDF`,
  `ComponentGroupPDF`, `RectanglePDF`, `LinePDF`, `TextPDF`, `DrawingStyle`,
  `TextStyle`, `Font`, `annotate_extraction_truth()`, and
  `annotate_grammar_truth()`.
- It does not depend on PDF object writer internals, document output exporters,
  private renderer helpers, or new third-party packages.

Contract edge:

- The fixture layer composes drawing primitives and truth helpers. It must not
  become the owner of PDF serialization or document-output rendering.

## Structural Proof

- The public API exports `ParserStressBOMRow`, `ParserStressFixtureSpec`, and
  `build_parser_stress_pdf()`.
- The dependency map documents fixture builders as an authoring layer above PDF
  primitives and truth annotations.

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

## Functional Proof

- The builder returns a live `DocumentPDF`; no renderer bypass is introduced.
- `DocumentPDF.to_pdf_bytes()`, `DocumentPDF.extraction_truth()`, and
  `DocumentPDF.grammar_truth()` exercise the same live paths used by normal PDF
  documents.

## Mutation Gate

`tests/mutation/parser_stress_fixtures_cosmic_ray.toml` scopes mutation testing
to the new fixture module. Equivalent survivors must be documented in the slice
report.

Current scoped result: 73 proof-critical work items, 72 killed, 1 documented
equivalent survivor. The survivor changes `rotation % 90 != 0` to
`rotation % 90 > 0`; Python modulo by a positive integer returns values in
`0..89`, so the predicates are equivalent for all integer rotations.
