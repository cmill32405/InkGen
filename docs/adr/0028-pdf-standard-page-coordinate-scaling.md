# ADR-0028: PDF Standard Page Coordinate Scaling

## Status

Accepted. Supersedes ADR-0027's `/UserUnit` serialization mechanism while
retaining its canvas-unit public contract.

## Context

ADR-0027 used PDF 1.6 `/UserUnit` so page dictionaries and content operators
could retain canvas-valued numbers. Standards-compliant readers such as
PyMuPDF apply that entry, but browser PDF renderers and lightweight parsers can
ignore it. Such consumers read the raw `MediaBox`, making a millimeter document
appear smaller by a factor of `72 / 25.4`.

PDF content-stream matrices do not transform page dictionaries, annotations,
or destinations. Replacing `/UserUnit` therefore requires an explicit
coordinate partition rather than changing only the page size.

## Decision

`DocumentPDF` continues to store public document parameters in canonical
canvas units. At PDF serialization:

- `MediaBox`, Crop/Bleed/Trim/Art boxes, annotation rectangles and points,
  destination coordinates, annotation border widths, and FreeText font sizes
  are multiplied by the page's point scale;
- each content stream begins with a uniform scale `cm`, followed by the
  existing top-left-to-bottom-left coordinate transform;
- component content operators remain in canvas units and inherit the scale
  exactly once from the content matrix;
- extraction and grammar truth bboxes remain explicitly converted to physical
  PDF points;
- zoom factors, colors, page rotations, object identifiers, and other
  dimensionless values are not scaled;
- `/UserUnit` is not emitted, and the dependency-free writer returns to PDF
  version 1.4.

## Consequences

- Consumers that read standard point-valued page dictionaries report the
  intended physical page size without implementing `/UserUnit`.
- PyMuPDF and a lightweight parser that reads only `MediaBox` plus content
  operators agree on page dimensions and the page-scale transform.
- Stored parameters and `create_from_dict()` round trips retain canvas units;
  the conversion remains an output-boundary concern.
- Metadata serializers have explicit conversion paths because content matrices
  cannot affect PDF dictionaries.
- Callers must continue to avoid pre-scaling input geometry.
- No package dependency or public model field is added.
