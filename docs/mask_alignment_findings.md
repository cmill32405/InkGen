# Mask Alignment Findings

## Background
- `TextFitter.fit()` centres each line inside the target shape, jitters the placement, and recomputes the convex hull from glyph outlines.  
- The exported SVG stores those hull coordinates in `_mask_override`; masking layers reuse them verbatim.  
- Despite identical coordinates between fitter logs, YAML snapshots, and SVG `<path>` data, major viewers (Edge, Firefox, Inkscape) showed the text offset from its hull.

## Instrumentation & Experiments
- Added temporary bbox logging via `debug_print_text_coords()` and a mask logger inside `_add_modeling_layer()` to verify hull serialization.  
- Captured per-style YAML snapshots containing label positions and mask polygons.  
- Inserted fixed reference labels: one left anchored, one centre anchored, and one routed through the fitter. This allowed us to compare viewer behaviour without fitter jitter.  
- Exposed toggles (`EMIT_TEXT_OUTLINES`, `CONVERT_TEXT_TO_PATH`) to compare native `<text>` rendering with glyph-outline paths.

## Observations
1. Hull coordinates exported to SVG and YAML always matched the fitter’s stored geometry.  
2. Misalignment appeared only for `<text>` elements using `text-anchor="middle"` / `dominant-baseline="central"`. A manually placed centre/middle label outside the fitter drifted the same way, confirming the viewer was recentering glyphs using its own metrics.  
3. The drift direction depended on the text (sometimes left, sometimes right), demonstrating that per-string glyph bearings and kerning influence the viewer’s centre calculation.  
4. Converting labels to outline paths (`CONVERT_TEXT_TO_PATH=True`) removed the discrepancy across all viewers because glyph positioning then bypassed the SVG text layout engine.  
5. Simply switching fitted labels to `text-anchor="start"` aligned them visually, but jitter assumed symmetric slack around the centre and began to push text outside irregular polygons.

## Mitigation Implemented
- The fitter still evaluates positions using centre/middle anchors. After the final placement is known, we sample the glyph outlines again to recover the exact left edge and baseline implied by those outlines.  
- At export time we switch the rendered `<text>` elements to `text-anchor="start"` and reuse the outline-derived start position while keeping the baseline unchanged. This preserves editability/searchability of `<text>` while honouring the hull geometry that the fitter saw.  
- The `CONVERT_TEXT_TO_PATH` toggle remains available for scenarios requiring fully deterministic layout with no viewer involvement.

## Remaining Considerations
- Viewer behaviour appears consistent across major engines, but additional spot checks are recommended when introducing new fonts or languages.  
- If future work re-enables jitter symmetry assumptions, ensure any new layout logic also records the derived start/baseline so the export stays aligned.  
- If perfect fidelity is required for archival output, path conversion is still the safest option; keep both pathways tested.  
- The temporary loggers used during this investigation have been removed from the codebase now that the behaviour is understood.
