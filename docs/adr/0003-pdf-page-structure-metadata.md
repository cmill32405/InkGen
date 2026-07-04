# ADR-0003: PDF Page Structure Metadata

## Status

Accepted

## Context

InkGen's PDF backend is used to create deterministic synthetic drawings and
document fixtures. Some parser-facing PDF fixtures need document-level structure
that is not part of the drawing primitive model, including human page labels and
PDF page boxes such as CropBox, BleedBox, TrimBox, and ArtBox.

This metadata belongs to the PDF page dictionary and catalog. It should not be
owned by flow-document outputs or renderer-neutral drawing components because
those layers consume drawing primitives rather than rendering PDF dictionaries.

## Decision

`DocumentPDF` owns PDF-specific page-structure metadata:

- `set_page_label(page_number, label)` sets or clears a non-empty Latin-1 page
  label for an existing page.
- `page_label(page_number)` returns the explicit label for an existing page.
- `set_page_box(page_number, box_name, box)` sets or clears a CropBox, BleedBox,
  TrimBox, or ArtBox for an existing page.
- `page_box(page_number, box_name)` returns the explicit box for an existing
  page.

Page labels are emitted as a PDF `/PageLabels` number tree in the catalog. Page
boxes are emitted directly on page dictionaries in bottom-left page coordinates.
Both labels and boxes are included in `DocumentPDF.parameters` and restored by
`DocumentPDF.create_from_dict()`.

`DocumentPDF.add_page()` and `DocumentPDF.remove_page()` shift or remove
page-specific PDF metadata so labels and boxes remain aligned with page indices.

## Consequences

- PDF page metadata remains local to the PDF renderer boundary.
- Renderer-neutral drawing classes stay reusable across SVG, PDF, and DXF.
- Flow-document outputs can embed drawing primitives without owning PDF page
  dictionary concerns.
- Page labels are limited to Latin-1 until the backend defines a Unicode PDF
  string policy.
- Page boxes are validated for allowed names, finite numeric coordinates,
  positive area, and MediaBox containment; semantic nesting among boxes is not
  enforced.

## Proof And Verification

Proof obligations `PO-PDFDOC-006` through `PO-PDFDOC-009` in
`docs/proofs/pdf-document-contract.md` cover:

- emitted and escaped page labels,
- emitted allowed page boxes,
- page insertion/removal metadata shifts,
- serialization round trips,
- malformed serialized metadata rejection.

Behavioral coverage is marked with `PDF-DOC-STRUCT-P3`.

## Affected Contracts

- `src/InkGen/pdf_generator.py`
- `tests/test_pdf_document_contract.py`
- `docs/pdf-generation.md`
- `docs/proofs/pdf-document-contract.md`

## Related Decisions

- ADR-0001: PDF Grammar Truth Annotations
- ADR-0002: Closed PDF Renderer Domain
