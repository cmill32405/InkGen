# Raster Image Contract Proof

## Scope

This proof covers the renderer-neutral raster image slices:

- `RasterImageAsset` accepts Pillow-decodable raster bytes and records format,
  EXIF-normalized dimensions, mode, orientation, and transparency metadata.
- `ImageDrawing` materializes to `ImageSVG` and `ImagePDF`.
- `ImageSVG` embeds a PNG data URI so every accepted raster input has one stable
  SVG representation.
- `ImagePDF` draws image XObject resources through `DocumentPDF.to_pdf_bytes()`.
- PDF alpha is preserved with an `/SMask`; transparent pixels are not flattened
  to white or any other background color.
- RGB JPEGs with identity EXIF orientation are passed through to PDF as
  `/DCTDecode` streams. JPEGs that require EXIF rotation are decoded,
  transposed, and embedded as normalized RGB samples instead.
- Flow-document DOCX output embeds `ImageDrawing` instances as native PNG media
  parts with DrawingML relationships. It does not own raster decoding or render
  images through SVG data URIs.
- DXF raster image export is intentionally unsupported for this slice because
  DXF image entities are external references rather than embedded drawing
  primitives.

## Dependency Claim

Raster image decoding belongs in `image_assets.py`, placement belongs in
`ImageDrawing`, and concrete drawing encoding belongs in SVG/PDF renderers. Flow
document outputs may package native document media for drawing groups containing
image drawings, but must not own raster decoding or PDF/SVG image serialization.

## Proof Obligations

| Obligation | Evidence |
|---|---|
| Accept supported raster inputs | `test_raster_image_asset_accepts_pillow_decodable_formats_and_preserves_alpha_metadata` |
| Reject malformed bytes | `test_raster_image_asset_rejects_malformed_bytes` |
| Preserve renderer-neutral geometry | `test_image_drawing_materializes_svg_and_pdf_components` |
| Normalize SVG output to embedded PNG | `test_image_svg_embeds_png_data_uri_for_supported_input_formats` |
| Preserve PDF alpha with soft mask | `test_document_pdf_embeds_image_xobject_with_alpha_soft_mask` |
| Avoid unnecessary soft masks for opaque images | `test_image_pdf_opaque_images_do_not_emit_soft_masks` |
| Apply EXIF orientation to decoded image surfaces | `test_raster_image_asset_applies_exif_orientation_to_decoded_surface` |
| Pass identity RGB JPEG bytes through to PDF | `test_document_pdf_passes_identity_rgb_jpegs_through_as_dct_streams` |
| Decode oriented JPEGs before PDF embedding | `test_document_pdf_decodes_oriented_jpegs_before_embedding` |
| Embed DOCX images as native media parts | `test_flow_document_docx_embeds_image_drawings_as_native_media_parts` |
| Hydrate flow-document image drawings without style payloads | `test_flow_document_image_drawing_parameters_round_trip_without_style` |
| Reject malformed flow-document image payloads | `test_flow_document_image_drawing_hydration_rejects_missing_image_payload` |
| Preserve serialization round trips | `test_image_parameters_round_trip_for_svg_and_pdf` |

## Counterexamples And Exclusions

Custom SVG image filters, ICC profiles, animated image frames, indexed-color
preservation, CMYK JPEG pass-through, and DXF referenced images are outside this
slice. PDF normalizes non-pass-through image color samples to DeviceRGB and
alpha samples to DeviceGray. DOCX native image embedding normalizes media parts
to PNG so alpha and EXIF orientation survive Word/Google Docs ingestion without
introducing new package dependencies.

## Current Status

Scoped mutation gate:

- Cosmic Ray 8.4.6, scoped with
  `tests/mutation/raster_image_cosmic_ray.toml` and
  `tests/mutation/filter_raster_image_work_items.py`: 441 work items, 412
  killed, 19 survived as documented equivalents, and 10 incompetent mutants.
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
  - JPEG pass-through equality comparisons changed to inclusive range
    comparisons where the surviving branch still rejects the tested oriented
    and CMYK JPEG cases and accepts only the tested identity RGB JPEG case.
  - PDF alpha bytes checked with `value == 255` changed to `value >= 255`.
    Alpha channel samples are bytes in `[0, 255]`, so both predicates identify
    fully opaque samples identically.
  - PDF filter-name equality changed to identity or inclusive string range
    comparisons that keep the tested Flate and DCT branches behaviorally
    unchanged for the two supported filter names.
  - DOCX media content-type equality changed to identity/inclusive string range
    comparisons. The registry produces the interned literal `image/png` for
    every supported DOCX media part in this slice, so these mutations do not
    change public behavior.
- Incompetent mutants were invalid arithmetic replacements in PDF content
  string assembly and page-resource string assembly; Cosmic Ray could not run
  them as viable behavioral alternatives.

Proven for the stated domain after focused tests and scoped mutation pass. Full
quality gates remain part of the slice closeout.
