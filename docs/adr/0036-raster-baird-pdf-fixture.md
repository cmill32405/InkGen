# ADR-0036: Raster-Baird PDF Fixture Composition

## Status

Accepted for `RASTER-BAIRD-E2E-P19`.

## Context

InkGen separately proved neutral drawing rasterization, Baird degradation,
raster image materialization, and PDF image embedding. Document Intelligence
still lacked one reusable fixture that traversed all of those public boundaries
and made text, vector geometry, transparency, canvas clipping, colored paper,
and image-only PDF output observable together.

Putting fixture policy into `raster_renderer.py`, `baird.py`, or
`pdf_generator.py` would mix orchestration with an algorithm or serializer.
Routing through a rendered PDF or SVG would also reverse the standalone
renderer boundary and reintroduce an external rasterizer requirement.

## Decision

Add `raster_baird_fixtures.py` as a thin public composition layer. Its fixed
neutral source drawing includes installed-font text, vector geometry, a
translucent fill, and a rectangle crossing the top-left canvas boundary.
`build_raster_baird_pdf_fixture()` calls
`render_and_degrade_drawing_group()` directly, then materializes the resulting
opaque `RasterImageAsset` through `ImageDrawing` and the existing `ImagePDF`
path. The PDF page contains one image XObject and no live PDF text.

The builder accepts only the existing Baird parameters, seed, substrate, DPI,
and render supersampling controls. Their validation remains owned by the
existing public renderer and degradation boundaries. A 0.1 mm PDF placement
inset preserves the document model's strict page-boundary contract without
changing the full-canvas raster dimensions.

`RasterBairdPDFFixture` returns the clean RGBA asset, opaque degraded RGB
asset, image-only `DocumentPDF`, and a nested deterministic manifest. External
truth annotations identify the known image-only fixture without changing PDF
bytes.

## Dependencies And Contracts

| Dependency | Consumed contract | Failure if changed |
|---|---|---|
| `drawing_components.py` | Neutral text, vector, image, and group materialization | Fixture stops exercising the public authoring path |
| `raster_renderer.py` | Full-canvas RGBA output, clipping, physical sizing, and Baird composition | Clean pixels, dimensions, or scan provenance drift |
| `baird.py` | Seeded degradation and explicit RGB substrate | Scan bytes or reproducibility change |
| `pdf_generator.py` | Opaque `ImagePDF` XObject embedding and deterministic PDF bytes | The degraded image is altered or live text appears |
| Truth annotations | Out-of-band known-fixture records | Downstream fixture discovery loses provenance |

The new dependency direction is one-way from fixture composition to existing
public authoring, renderer, degradation, truth, and PDF APIs. No lower layer
depends on the fixture module, and no dependency or output format is added.

## Consequences

- Document Intelligence receives one deterministic reusable end-to-end fixture.
- Clean and degraded PNGs remain directly inspectable alongside the PDF.
- Colored paper is explicit and recorded; alpha is never silently flattened.
- Canvas clipping is exercised without adding a new clipping API.
- The PDF serializer remains a terminal container rather than a raster source.
- Font-dependent byte determinism is scoped to the same installed font and
  Pillow/NumPy runtime, matching the raster text contract.

## Alternatives Rejected

- **Extend the raster renderer with PDF output:** crosses renderer ownership.
- **Render an InkGen PDF back to pixels:** requires a PDF reader/rasterizer and
  violates the standalone path.
- **Put the fixture in Document Intelligence:** duplicates InkGen authoring and
  artifact contracts downstream.
- **Replace the existing scanned fixture:** changes a stable parser fixture
  instead of adding a separately proven composition path.
