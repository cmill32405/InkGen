# ADR-0003: PDF Page Structure Metadata

## Status

Accepted

## Context

InkGen's PDF backend is used to create deterministic synthetic drawings and
document fixtures. Some parser-facing PDF fixtures need document-level structure
that is not part of the drawing primitive model, including human page labels,
page dictionary rotation, and PDF page boxes such as CropBox, BleedBox, TrimBox,
and ArtBox.

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
- `set_page_rotation(page_number, rotation)` sets or clears an explicit PDF page
  `/Rotate` value for an existing page. Rotation is an integer multiple of
  90 degrees, normalized to `0`, `90`, `180`, or `270`; normalized zero is
  treated as no explicit page rotation.
- `page_rotation(page_number)` returns the explicit nonzero page rotation for an
  existing page.

Page labels are emitted as a PDF `/PageLabels` number tree in the catalog. Page
boxes and page rotations are emitted directly on page dictionaries. Page box
coordinates remain in bottom-left page coordinates; page rotation is viewer
metadata and does not mutate component geometry or truth coordinates. Labels,
boxes, and rotations are included in `DocumentPDF.parameters` and restored by
`DocumentPDF.create_from_dict()`.

`DocumentPDF.add_page()` and `DocumentPDF.remove_page()` shift or remove
page-specific PDF metadata so labels, boxes, and rotations remain aligned with
page indices.

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
- Page rotations are metadata only. Automatic coordinate remapping for rotated
  truth records and rotated appearance streams remains out of scope.

## Proof And Verification

Proof obligations `PO-PDFDOC-006` through `PO-PDFDOC-009` in
`docs/proofs/pdf-document-contract.md`, plus `PO-PDFDOC-049`, cover:

- emitted and escaped page labels,
- emitted allowed page boxes,
- emitted page rotations,
- page insertion/removal metadata shifts,
- serialization round trips,
- malformed serialized metadata rejection.

Behavioral coverage is marked with `PDF-DOC-STRUCT-P3` and
`PDF-DOC-PAGE-ROTATION-P3`.

## Affected Contracts

- `src/InkGen/pdf_generator.py`
- `tests/test_pdf_document_contract.py`
- `docs/pdf-generation.md`
- `docs/proofs/pdf-document-contract.md`

## Related Decisions

- ADR-0001: PDF Grammar Truth Annotations
- ADR-0002: Closed PDF Renderer Domain
