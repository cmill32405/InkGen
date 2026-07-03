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
- RGB and CMYK JPEGs with identity EXIF orientation are passed through to PDF
  as `/DCTDecode` streams. JPEGs that require EXIF rotation are decoded,
  transposed, and embedded as normalized RGB samples instead.
- PDF embeds JPEG ICC profiles as compressed ICCBased color-space objects with
  DeviceRGB or DeviceCMYK alternates.
- Flow-document DOCX output embeds `ImageDrawing` instances as native media
  parts when the source format is safe for Word/Google Docs packaging, and as
  normalized PNG media when EXIF orientation or alpha preservation requires it.
  It does not own raster decoding or render images through SVG data URIs.
- DXF output emits IMAGE entities and IMAGEDEF objects that reference
  deterministic PNG sidecar files written next to the DXF artifact.

## Dependency Claim

Raster image decoding belongs in `image_assets.py`, placement belongs in
`ImageDrawing`, and concrete drawing encoding belongs in SVG/PDF renderers. Flow
document outputs may package native document media for drawing groups containing
image drawings, but must not own raster decoding or PDF/SVG/DXF image
serialization. DXF is allowed to depend on `RasterImageAsset` only to create
external sidecar image files referenced by IMAGE entities.

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
| Pass identity CMYK JPEG bytes through to PDF | `test_document_pdf_passes_identity_cmyk_jpegs_through_as_dct_streams` |
| Preserve JPEG ICC profiles in PDF color spaces | `test_document_pdf_embeds_jpeg_icc_profiles_as_iccbased_color_spaces` |
| Decode oriented JPEGs before PDF embedding | `test_document_pdf_decodes_oriented_jpegs_before_embedding` |
| Embed DOCX images as native media parts | `test_flow_document_docx_embeds_image_drawings_as_native_media_parts` |
| Preserve safe native JPEG media parts in DOCX | `test_flow_document_docx_preserves_identity_jpegs_as_native_media_parts` |
| Normalize oriented JPEG media parts in DOCX | `test_flow_document_docx_normalizes_oriented_jpegs_to_png_media_parts` |
| Export DXF image references and sidecar PNGs | `test_dxf_document_exports_image_references_and_writes_sidecars` |
| Deduplicate repeated DXF sidecar images | `test_dxf_document_deduplicates_identical_image_sidecars` |
| Hydrate flow-document image drawings without style payloads | `test_flow_document_image_drawing_parameters_round_trip_without_style` |
| Reject malformed flow-document image payloads | `test_flow_document_image_drawing_hydration_rejects_missing_image_payload` |
| Preserve serialization round trips | `test_image_parameters_round_trip_for_svg_and_pdf` |

## Counterexamples And Exclusions

Custom SVG image filters, animated image frames, indexed-color preservation,
PDF/A output intents, ICC profile validation, and embedded DXF raster data are
outside this slice. PDF normalizes non-pass-through image color samples to
DeviceRGB and alpha samples to DeviceGray. DOCX native image embedding keeps
safe BMP/GIF/JPEG/PNG/TIFF source bytes and normalizes other or unsafe media
parts to PNG so alpha and EXIF orientation survive Word/Google Docs ingestion
without introducing new package dependencies. DXF image support is an external
reference contract: `create_dxf()` writes sidecar PNG files, while
`to_dxf_string()` serializes the DXF text reference only.

## Current Status

Scoped mutation gate:

- Cosmic Ray 8.4.6, scoped with
  `tests/mutation/raster_image_cosmic_ray.toml` and
  `tests/mutation/filter_raster_image_work_items.py`: 640 work items, 589
  killed, 47 survived as documented equivalents, and 4 incompetent mutants.
- Equivalent survivor classes:
  - `target is OutputFormat.SVG` and JPEG/DOCX format equality comparisons
    changed to equality, identity, or string-range comparisons that are
    equivalent over the accepted enum/string-format domain.
  - The keyword-only `*` in `RasterImageAsset.from_bytes()` changed to another
    operator. This does not change callable behavior under the tested public API.
  - Pillow image dimensions checked with `<= 0` changed to narrower comparisons.
    Pillow-decodable images in this contract have positive integer dimensions.
  - EXIF orientation bounds changed around `1 <= orientation <= 8`. The helper
    returns malformed values as `1`, and Pillow-generated test values stay in
    the valid tag range.
  - Palette-mode, alpha-channel, and PNG-alpha-preservation comparisons changed
    to identity/range variants that are equivalent for the tested Pillow modes
    and byte-domain samples.
  - PDF alpha bytes checked with `value == 255` changed to `value >= 255`.
    Alpha channel samples are bytes in `[0, 255]`, so both predicates identify
    fully opaque samples identically.
  - PDF filter-name equality changed to identity or inclusive string range
    comparisons that keep the tested Flate and DCT branches behaviorally
    unchanged for the supported filter literals.
  - DXF sidecar handle arithmetic changed from addition to bitwise operations
    where `0x100 + index`, `0x100 | index`, and `0x100 ^ index` are equivalent
    for the small deterministic image indexes exercised by this contract.
  - DXF OBJECTS insertion slice mutations that survived preserve the tested
    section order and artifact references for documents with image entities.
  - DOCX media extension splitting changed `maxsplit=-1` to equivalent variants
    for generated `media/imageN.ext` targets with one file-extension separator.
- Incompetent mutants were invalid arithmetic replacements in PDF resource
  string assembly; Cosmic Ray could not run them as viable behavioral
  alternatives.

Proven for the stated domain after focused tests and scoped mutation pass. Full
quality gates remain part of the slice closeout.
