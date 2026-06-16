# ADR-0001: PDF Grammar Truth Annotations

## Status

Accepted

## Context

InkGen is used to generate synthetic drawings and documents for downstream
Document Intelligence parser work. Extraction truth already records semantic
field/value annotations in rendered PDF coordinates. The parser also needs
grammar-level truth for document structure, including cues, constructs, links,
and document-level assessments.

The grammar truth system must be useful to downstream scoring without making
InkGen depend on a DocInt registry or changing rendered PDF bytes.

## Decision

InkGen will provide registry-agnostic grammar truth annotations for PDF
fixtures.

The public grammar truth API is:

- `GrammarTruthAnnotation`
- `GrammarTruthRecord`
- `annotate_grammar_truth()`
- `DocumentPDF.grammar_truth()`
- `DocumentPDF.grammar_truth_json()`

Grammar truth kinds are intentionally limited to:

- `cue`
- `construct`
- `link`
- `assessment`

InkGen validates only the local record shape:

- `condition_id` is a non-empty string.
- `kind` is one of the accepted local kinds.
- `source_channel` is a non-empty string.
- `links_to` is `None` or a string.
- `instance_id` is `None` or a string.

Body-sourced records use the same `pdf_points_bottom_left` coordinate frame as
extraction truth. Non-body records, including document-level assessments, emit
`page: 0` and `bbox: None`.

Grammar annotations are serialized in `DocumentPDF` and `ComponentGroupPDF`
parameters, including component-level annotations, so fixture recipes can
round-trip without losing parser-facing truth.

## Consequences

- InkGen remains registry-agnostic. DocInt owns the semantic interpretation of
  `condition_id` and `value`.
- Grammar truth can be emitted without changing PDF render bytes.
- Grammar truth depends on the extraction-truth coordinate conversion helper.
  Changes to that helper must consider both extraction and grammar truth.
- Future grammar truth kinds require updating the local accepted-kind set,
  public docs, tests, and proof obligations.

## Proof And Verification

Proof obligations are recorded in `docs/proofs/grammar-truth.md`.

Behavioral coverage:

- Grammar truth emits body bboxes in PDF bottom-left coordinates.
- Metadata assessments emit `page: 0` and `bbox: None`.
- Link records preserve `links_to`.
- Annotations round-trip through `DocumentPDF.parameters`.
- Invalid condition IDs and kinds fail loudly.

## Affected Contracts

- `src/InkGen/grammar_truth.py`
- `src/InkGen/pdf_generator.py`
- `src/InkGen/drawing_components.py`
- `docs/proofs/grammar-truth.md`
- `docs/pdf-generation.md`
- `docs/api-reference.md`

## Related Decisions

- ADR-0002: Closed PDF Renderer Domain
