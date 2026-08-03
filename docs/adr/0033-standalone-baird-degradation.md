# ADR-0033: Standalone Baird Degradation

## Status

Accepted

## Context

InkGen must create degraded document fixtures without depending on a PDF
rasterizer. The established Document Intelligence synthetic pipeline used
Baird's document image defect model after first rasterizing PDFs through
PyMuPDF. That made the degradation model appear coupled to PyMuPDF even though
the model itself consumes only a raster array.

InkGen already depends on NumPy and Pillow. Adding OpenCV solely for two image
operations would expand dependency ownership and conflict with the project's
dependency-reduction direction.

## Decision

InkGen owns a standalone `baird.py` module with:

- validated immutable `BairdParams`;
- `baird_degrade()` for normalized NumPy raster arrays;
- `baird_degrade_asset()` for `RasterImageAsset` inputs;
- deterministic `BairdDegradationResult` provenance;
- physical blur conversion helpers;
- NumPy bilinear sampling and Gaussian point-spread implementations.

The canonical transform order, parameter distributions, coordinate convention,
and random draw order are retained. InkGen does not add PyMuPDF or OpenCV.

Alpha input must name a physical RGB substrate. The implementation rejects an
implicit white flatten because colored page backgrounds are valid and hidden
flattening destroys information.

The supersampling ratio is bounded to 1 through 16, and the intermediate
prototype is bounded to 64,000,000 pixels. Invalid and unbounded states fail at
the public boundary.

## Consequences

- InkGen can generate scanner-like degradation without another repository.
- The output remains compatible with existing `RasterImageAsset` consumers.
- The neutral primitive raster renderer can feed Baird directly without a PDF
  or SVG intermediary.
- The NumPy implementation is not promised to be bit-identical to OpenCV.
  Reference statistics and parameter-direction tests bound numerical drift.
- Non-Baird defects remain separate named stages and must not be presented as
  part of the Baird model.

## Rejected Alternatives

### Keep Baird only in Document Intelligence

Rejected because InkGen would not be a standalone fixture-generation library.

### Rasterize generated PDFs with PyMuPDF

Rejected because rasterization is unnecessary when InkGen owns the source
primitives and because it adds an unwanted dependency boundary.

### Add OpenCV to InkGen

Rejected because NumPy and Pillow already provide enough capability and the
port demonstrates close numerical agreement without dependency growth.

### Create a generic degradation profile that duplicates Baird

Rejected because two independent implementations would drift. Baird is the
named canonical scanner defect model; additional effects must be explicit
separate stages.
