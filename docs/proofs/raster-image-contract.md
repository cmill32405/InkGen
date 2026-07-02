# Raster Image Contract Proof

## Scope

This proof covers the first renderer-neutral raster image slice:

- `RasterImageAsset` accepts Pillow-decodable raster bytes and records format,
  dimensions, mode, and transparency metadata.
- `ImageDrawing` materializes to `ImageSVG` and `ImagePDF`.
- `ImageSVG` embeds a PNG data URI so every accepted raster input has one stable
  SVG representation.
- `ImagePDF` draws image XObject resources through `DocumentPDF.to_pdf_bytes()`.
- PDF alpha is preserved with an `/SMask`; transparent pixels are not flattened
  to white or any other background color.
- DXF raster image export is intentionally unsupported for this slice because
  DXF image entities are external references rather than embedded drawing
  primitives.

## Dependency Claim

Raster image decoding belongs in `image_assets.py`, placement belongs in
`ImageDrawing`, and concrete encoding belongs in SVG/PDF renderers. Flow document
outputs may consume drawing groups containing image drawings, but must not own
raster decoding or PDF/SVG image serialization.

## Proof Obligations

| Obligation | Evidence |
|---|---|
| Accept supported raster inputs | `test_raster_image_asset_accepts_pillow_decodable_formats_and_preserves_alpha_metadata` |
| Reject malformed bytes | `test_raster_image_asset_rejects_malformed_bytes` |
| Preserve renderer-neutral geometry | `test_image_drawing_materializes_svg_and_pdf_components` |
| Normalize SVG output to embedded PNG | `test_image_svg_embeds_png_data_uri_for_supported_input_formats` |
| Preserve PDF alpha with soft mask | `test_document_pdf_embeds_image_xobject_with_alpha_soft_mask` |
| Avoid unnecessary soft masks for opaque images | `test_image_pdf_opaque_images_do_not_emit_soft_masks` |
| Preserve serialization round trips | `test_image_parameters_round_trip_for_svg_and_pdf` |

## Counterexamples And Exclusions

Custom SVG image filters, ICC profiles, EXIF orientation policy, animated image
frames, indexed-color preservation, JPEG pass-through, and DXF referenced images
are outside this slice. PDF currently normalizes image color samples to
DeviceRGB and alpha samples to DeviceGray.

## Current Status

Scoped mutation gate:

- Cosmic Ray 8.4.6, scoped with
  `tests/mutation/raster_image_cosmic_ray.toml` and
  `tests/mutation/filter_raster_image_work_items.py`: 298 work items, 286
  killed, and 12 survived.
- Equivalent survivors:
  - `target is OutputFormat.SVG` changed to equality/range comparisons.
    `normalize_output_format()` returns current `OutputFormat` string-enum
    values, so the tested SVG/PDF branch partition is unchanged.
  - The keyword-only `*` in `RasterImageAsset.from_bytes()` changed to another
    operator. This does not change callable behavior under the tested public API.
  - Pillow image dimensions checked with `<= 0` changed to narrower comparisons.
    Pillow-decodable images in this contract have positive integer dimensions.
  - Palette-mode equality comparisons changed to range/identity comparisons.
    For Pillow palette transparency, `mode == "P"` remains behaviorally
    equivalent over the tested transparent and opaque palette images.
  - PDF alpha bytes checked with `value == 255` changed to `value >= 255`.
    Alpha channel samples are bytes in `[0, 255]`, so both predicates identify
    fully opaque samples identically.

Proven for the stated domain after focused tests and scoped mutation pass. Full
quality gates remain part of the slice closeout.
