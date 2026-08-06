# InkGen TODO

This backlog separates outstanding integration work from completed requests and
longer-term product enhancements. Items are not commitments until selected as a
bounded Definition of Done slice.

## DocInt Integration

Completed:

- [x] Emit a clipped, self-contained SVG region from positioned text runs and
  renderer-neutral vector primitives (`46c804c`).
- [x] Accept original embedded font-program bytes for exact glyph-outline
  generation (`46c804c`).
- [x] Provide a standalone Baird document-degradation pipeline without
  PyMuPDF, OpenCV, or new dependencies (`6209121`).

Remaining:

- [x] Add a dependency-free, in-memory raster renderer for InkGen drawing
  primitives and document pages. Preserve alpha until the caller explicitly
  selects a paper/background color.
- [x] Add a renderer-to-Baird composition API so a clean InkGen drawing can be
  rasterized and degraded without writing or rereading a PDF.
- [x] Preserve deterministic seeds, physical resolution, source dimensions,
  background policy, and degradation parameters in the composed result
  manifest.
- [x] Add end-to-end fixtures proving clean drawing -> raster -> Baird
  degradation -> PDF/image embedding, including text, vector geometry,
  transparency, clipping, and colored backgrounds.

## Product Backlog

### Text And PDF Fidelity

- [ ] Add Unicode/CID PDF fonts, deterministic glyph subsetting, UTF-16BE
  document strings, complete `/ToUnicode` maps, and complex-script shaping.
- [ ] Add automatic wrapping, kerning, tabs, columns, and explicit overflow
  policies shared across applicable PDF, SVG, and document outputs.
- [ ] Add parser-hostile synthetic fixtures for unusual CID mappings,
  missing or malformed CMaps, subset fonts, damaged extraction maps, and
  image-only scan pages.

### Graphics And Documents

- [ ] Evaluate radial and mesh gradients, reusable patterns, transparency
  groups, and broader calibrated color-space support as bounded features.
- [ ] Evaluate tagged PDF, archival PDF constraints, richer annotations, and
  document accessibility only when concrete consumers require them.
- [ ] Continue DOCX fidelity work for native images, table merges, paragraph
  styles, and editable drawing output after reconciling the current
  uncommitted DOCX/documentation workstream.

### Maintainability

- [ ] Audit runtime dependencies and classify each as retain, replace with a
  standard-library or InkGen implementation, make optional, or remove. Do not
  add or replace dependencies without explicit approval.
- [ ] Resolve legacy formatting exceptions through isolated, behavior-neutral
  slices rather than broad formatting churn.
- [ ] Keep generated documentation output and local proof artifacts out of
  ordinary source diffs.
- [ ] Add a repeatable dependency/security audit gate and resolve unrelated
  environment conflicts without changing InkGen dependencies incidentally.
