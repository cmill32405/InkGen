# Baird Degradation Contract

## Conditions

### BAIRD-P1: Core Model

`BairdParams` represents the canonical defect controls. `baird_degrade()`
accepts a finite normalized grayscale or RGB array, preserves its spatial
dimensions, does not mutate it, and returns bounded replicated float32
luminance channels. Seeded generators produce deterministic results.

### BAIRD-P2: Raster Asset Bridge

`baird_degrade_asset()` decodes a `RasterImageAsset`, requires an explicit
substrate for alpha input, emits a renderer-ready RGB PNG, and returns the seed,
parameters, and substrate in a deterministic manifest.

### BAIRD-P3: Physical Blur Conversion

For finite `sigma >= 0` and finite `dpi > 0`:

```text
sigma_um_to_px(sigma, dpi) = sigma * dpi / 25400
sigma_px_to_um(px, dpi) = px * 25400 / dpi
```

Therefore:

```text
sigma_px_to_um(sigma_um_to_px(sigma, dpi), dpi)
= (sigma * dpi / 25400) * 25400 / dpi
= sigma
```

The cancellation is valid because `dpi > 0`. This proves round-trip identity
over real arithmetic in the stated domain. Floating-point execution is
supported by 100 generated counterexample-search cases at `1e-12` tolerance.

## Comprehensiveness Matrix

| Domain class | Handling | Evidence | Status |
|---|---|---|---|
| Valid grayscale/RGB float raster | normalize and degrade | core behavioral tests | covered |
| Seeded stochastic stages | deterministic generator state | repeated-output test | covered |
| Blur, sensitivity, threshold, scale, jitter | preserve documented direction | parameter-effect test | covered |
| Former OpenCV implementation | compare fixed reference statistics | compatibility test | supported by evidence |
| Invalid shape, emptiness, NaN, infinity, out-of-range intensity | reject | parameterized failure tests | covered |
| Invalid parameter type/range | reject at construction | parameterized failure tests | covered |
| Oversized intermediate prototype | reject before allocation | resource-bound test | covered |
| Opaque raster asset | emit RGB PNG and manifest | live asset test | covered |
| Alpha raster asset | require explicit substrate | alpha-policy test | covered |
| Invalid seed/background/result envelope | reject | failure tests | covered |
| Physical blur conversion | algebraic inverse | proof above plus property test | proven over real arithmetic; float execution evidenced |
| PDF/vector input | excluded; caller supplies clean raster | ADR-0033 | excluded |
| Non-Baird structural/transport defects | separate future stages | ADR-0033 | excluded |

## Dependency Review

- Incoming: package-root exports, neutral raster rendering, synthetic fixture
  builders, and existing `RasterImageAsset` output consumers.
- Outgoing: NumPy, Pillow, and `image_assets.py` only.
- New edge: `baird.py -> image_assets.py`.
- No renderer, document output, PDF parser, font engine, network, file-writing,
  or OpenCV dependency is introduced.
- The returned asset follows the existing image contract, so SVG/PDF/DXF/DOCX
  paths remain downstream consumers rather than degradation owners.

## Verification Evidence

- Condition tests: `tests/test_baird_degradation_contract.py`.
- Property search: 100 generated physical-conversion cases.
- Focused branch coverage: 100% for `src/InkGen/baird.py`.
- Compatibility probe against the original OpenCV-backed implementation:
  correlation `0.99999918`, mean absolute error `0.000155`, maximum absolute
  error `0.002741` for a seeded mixed-parameter case.
- Mutation evidence: 1,496 generated candidates, 894 selected proof-critical
  work items, and 894/894 killed with no survivors or timeouts. The retained
  record is `tests/mutation/baird_degradation_v1_evidence.json`.

## Residual Risk

Numerical kernels can differ slightly across NumPy versions and CPU platforms.
The contract promises model semantics and bounded reference compatibility, not
cross-platform byte identity for array output. PNG bytes are deterministic for
the tested environment and identical calls.
