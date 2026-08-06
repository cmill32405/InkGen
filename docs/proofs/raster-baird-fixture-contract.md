# Raster-Baird PDF Fixture Contract Proof

Condition: `RASTER-BAIRD-E2E-P19`.

## Claim

For the declared fixture domain, fixed render inputs, fixed Baird parameters,
seed, explicit substrate, installed font, and runtime versions,
`build_raster_baird_pdf_fixture()` deterministically returns:

1. a full-canvas clean RGBA PNG containing clipped text/vector/alpha evidence;
2. an opaque RGB Baird PNG whose transparent regions depend on the named
   substrate; and
3. a one-page image-only PDF embedding exactly those degraded RGB samples.

## Domain And Assumptions

- Renderer and degradation inputs satisfy their existing public contracts.
- The fixture canvas is 120 by 80 mm and the PDF image is inset by 0.1 mm.
- The same installed sans-serif font, Pillow, NumPy, and Python runtime are used
  for deterministic byte comparisons.
- PDF image payloads use the established opaque RGB Flate path.
- Hostile private mutation and cross-version font/raster byte identity are
  excluded.

## Composition Proof

Let `R(d, c)` be the proven raster renderer for drawing `d` and render controls
`c`. Let `B(a, p, s, b)` be the proven Baird asset transform for raster asset
`a`, parameters `p`, seed `s`, and substrate `b`. Let `I(a)` be neutral
`ImageDrawing` materialization to `ImagePDF`, and let `P(i)` be deterministic
`DocumentPDF` serialization of image `i`.

The builder is the direct composition:

```text
F(d, c, p, s, b) = (R(d, c), B(R(d, c).asset, p, s, b),
                     P(I(B(R(d, c).asset, p, s, b).asset)))
```

For two equal input tuples, determinism of `R` gives equal clean bytes and
manifests. Substitution into deterministic `B` gives equal degraded bytes and
manifests. Substitution of that asset into deterministic `I` and `P` gives
equal PDF bytes. Therefore the complete result and nested manifest are equal.

The raster surface is allocated only over the finite canvas pixel lattice.
The source rectangle intersects negative coordinates, while observed alpha
begins at output coordinate `(0, 0)` and no output coordinate exists outside
the declared dimensions. Thus visible source geometry is clipped to the canvas
without cropping or resizing the output asset.

For every transparent clean pixel with source alpha `a`, explicit substrate
`b` participates in source-over composition before Baird. Choosing substrates
with different channel means produces different clean-profile grayscale scan
pixels while leaving the RGBA source bytes unchanged. Therefore the substrate
is neither ignored nor replaced with implicit white.

The PDF dependent-path test proves that the sole `ImagePDF` owns the exact
degraded asset object and that one decompressed PDF image stream contains its
complete RGB sample sequence. The PDF has no text operators, so rasterized
fixture text cannot accidentally become extractable PDF text.

## Comprehensiveness Matrix

| Domain class | Handling | Evidence |
|---|---|---|
| Fixed valid inputs | return clean, degraded, and PDF artifacts | repeated public-build test |
| Omitted Baird parameters | select canonical `BairdParams()` defaults | default-profile test |
| Fixed source recipe | preserve exact geometry and presentation | structural source-drawing test |
| Text and vector geometry | paint into clean alpha surface | occupied text/vector pixel regions |
| Partial transparency | preserve nonzero, nonopaque clean alpha | top-left RGBA pixel assertion |
| Off-canvas source geometry | clip to finite full-size canvas | alpha bounds and output dimensions |
| Colored substrate | explicitly affect opaque scan only | two-substrate differential test |
| PNG image output | expose RGBA clean and RGB degraded assets | mode, dimensions, and byte checks |
| PDF image embedding | preserve degraded RGB samples | object identity and decompressed stream test |
| Image-only PDF | omit live text operators | PDF operator assertions |
| Truth/provenance | emit known-fixture records and nested manifest | truth and exact-manifest tests |
| Invalid controls | delegate to established owners | params, substrate, DPI, and signature failures |
| Invalid result envelope | reject unrelated types | constructor failure tests |
| Cross-runtime byte identity | excluded | installed-font/runtime assumption |

## Test Applicability

| Test class | Status | Evidence or exclusion |
|---|---|---|
| Unit/condition | required | result and manifest contracts |
| Failure mode | required | delegated invalid controls and envelope types |
| Integration/live path | required | neutral drawing through raster, Baird, and PDF |
| Determinism | required | repeated PNG, PDF, and manifest equality |
| Golden/artifact | required | pixel regions and decompressed PDF samples |
| Mutation | required | proof-critical composition and manifest paths |
| Security/adversarial | not applicable | no paths, archives, active content, network, or subprocess input |
| Performance/resource | inherited | renderer and Baird allocation bounds remain authoritative |

## Residual Risk

The fixture proves canvas-edge clipping, not an arbitrary user-defined clip
window. Installed-font and raster-library changes can intentionally change
artifact bytes; semantic assertions remain the portability boundary.

## Verification Status

- Focused P19 condition tests: 8 passed.
- Related raster, Baird, image, truth, and public API tests: 228 passed.
- Full branch-aware regression gate: 2,399 passed with 97% total package
  coverage.
- Cosmic Ray 8.4.6: 165 generated candidates, 11 postponed-annotation-only
  mutants excluded, 154 runtime mutants killed, zero survivors, errors, or
  timeouts; effective mutation coverage is 100%.
- Full-repository Ruff lint, touched-file Ruff formatting, Python bytecode
  compilation, strict MkDocs, and an isolated PEP 517 wheel build passed.
- `pip check` reports the host environment's pre-existing `sse-starlette 3.3.3`
  / `starlette 0.46.2` conflict. P19 does not change InkGen dependency
  declarations.
- Clean and degraded PNGs were visually inspected. The PDF image payload is
  checked byte-for-byte through its decompressed RGB stream because Poppler is
  unavailable in the local Windows and WSL environments.
