# Baird Degradation

InkGen includes a standalone implementation of H. S. Baird's 1992 document
image defect model. It operates on clean raster images and does not require a
PDF renderer, PyMuPDF, OpenCV, a system font, or a network service.

## Pipeline

```text
clean grayscale or RGB raster
    -> supersampled prototype
    -> Gaussian point-spread blur
    -> skew and width/height sampling geometry
    -> kern, baseline, and per-pixel sampling jitter
    -> sensitivity noise
    -> optional threshold binarization
    -> degraded three-channel raster
```

The public array API uses float images in `[0, 1]`, with white equal to one and
black equal to zero. The output has the same width and height as the input and
contains three replicated luminance channels.

## Array API

```python
import numpy as np

from InkGen import BairdParams, baird_degrade

clean = np.ones((600, 800, 3), dtype=np.float32)
params = BairdParams.sample(np.random.default_rng(7), binarize=False)
degraded = baird_degrade(clean, params, np.random.default_rng(19))
```

Pass an explicit `numpy.random.Generator` whenever reproducibility matters.
Omitting it intentionally creates a fresh generator.

## Raster Asset API

```python
from InkGen import BairdParams, RasterImageAsset, baird_degrade_asset

clean_asset = RasterImageAsset.from_file("clean-page.png")
result = baird_degrade_asset(clean_asset, BairdParams(), seed=41)
result.asset.png_bytes()
result.manifest
```

`BairdDegradationResult.manifest` records the model identifier, seed,
parameters, and alpha-compositing background. The output asset is a normalized
RGB PNG that can be embedded through InkGen's existing SVG, PDF, DXF, and DOCX
image paths.

An alpha-bearing source requires an explicit `background_rgb=(r, g, b)`.
InkGen never silently flattens transparency to white. This is necessary because
Baird models a scanned physical page and therefore has no alpha channel.

## Parameters

| Parameter | Meaning | Unit or domain |
|---|---|---|
| `supersample` | high-resolution prototype ratio | integer 1 through 16 |
| `blur` | Gaussian point-spread sigma | output pixels, nonnegative |
| `threshold` | darkness threshold | `[0, 1]` |
| `binarize` | apply threshold output | boolean |
| `sensitivity` | per-pixel intensity-noise standard deviation | nonnegative |
| `jitter` | sample-center displacement standard deviation | output pixels, nonnegative |
| `skew_deg` | centered rotation | degrees |
| `x_scale` | horizontal stretch | positive multiplier |
| `y_scale` | vertical stretch | positive multiplier |
| `baseline` | vertical sub-pixel placement | output pixels |
| `kern` | horizontal sub-pixel placement | output pixels |

`sigma_um_to_px()` and `sigma_px_to_um()` convert a physical optical sigma
between microns and pixels for DPI studies. DPI is not itself a Baird
parameter.

## Boundaries

- Baird starts with an already-rendered raster. InkGen's raster renderer can
  produce it directly from neutral drawing primitives, and
  `build_raster_baird_pdf_fixture()` proves the complete image-only PDF path.
- PDF grammar faults such as missing `ToUnicode` maps, malformed metrics, and
  unusual stream filters belong to PDF fixture construction, not Baird.
- Shadows, perspective, crop loss, bleed-through, and JPEG transport damage are
  useful additional degradation stages but are not part of Baird's model.
- The NumPy backend preserves the established model and seeded random draw
  order. It is numerically compatible with the earlier OpenCV implementation,
  but output is not claimed to be bit-for-bit identical across numerical
  libraries or platforms.
