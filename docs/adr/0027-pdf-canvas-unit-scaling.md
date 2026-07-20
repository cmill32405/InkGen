# ADR-0027: PDF Canvas Unit Scaling

## Status

Superseded by ADR-0028.

## Context

`Canvas` stores dimensions and geometry in either millimeters or inches. The
SVG backend emits those declared units, but the PDF backend previously wrote
the same numeric values directly into PDF default user space. Because one PDF
default user unit was one point, a 100 mm by 200 mm canvas became a 100 point by
200 point page instead of a 283.46 point by 566.93 point page. Drawing geometry
and parser-facing truth bboxes inherited the same physical-size mismatch.

Downstream code temporarily compensated by multiplying InkGen input geometry by
`72 / 25.4`. Keeping that workaround after this decision would double-scale
millimeter documents.

## Decision

`DocumentPDF` honors the canonical `Canvas.units` contract at the page boundary:

- millimeters use `72 / 25.4` PDF points per canvas unit;
- inches use `72` PDF points per canvas unit;
- each page retains its canvas-valued `MediaBox` and content operators and emits
  the corresponding PDF `/UserUnit` value;
- the PDF header is version 1.6, where `/UserUnit` is defined;
- extraction-truth and grammar-truth bboxes are multiplied by the same factor
  before being labeled `pdf_points_bottom_left`.

The conversion is page-level. Individual components, styles, links,
annotations, page boxes, destinations, and content operators remain in the
shared canvas coordinate system and are therefore scaled exactly once by the
PDF page.

## Consequences

- PDF physical page and drawing sizes now match SVG output for the same canvas.
- Page-level metadata and annotation geometry scale with drawing geometry
  without separate conversion paths.
- Existing callers that pre-scale geometry for PDF output must remove that
  compensation when adopting this InkGen version.
- Generated files require a PDF 1.6-capable reader.
- Deterministic output is preserved; no package dependency or public model
  field is added.

ADR-0028 retains the physical-size contract while replacing `/UserUnit` with
point-valued page dictionaries and a content-stream scale matrix for broader
consumer compatibility.
