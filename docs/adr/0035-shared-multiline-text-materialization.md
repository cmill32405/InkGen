# ADR-0035: Shared Multiline Text Materialization

## Status

Accepted for `TEXT-MULTILINE-P11` and `RASTER-TEXT-MULTILINE-P11`.

## Context

InkGen already defines multiline PDF text as CRLF/CR/LF normalization followed
by one aligned text operation per line. The standalone raster renderer rejected
the same neutral text, while SVG placed the complete newline-containing value
inside one `tspan`. That made one `TextDrawing` recipe produce materially
different line structures across output paths.

Line normalization is renderer-neutral. Concrete line placement remains a
renderer concern because PDF uses content-stream coordinates, SVG supports
relative font units, and raster output uses physical point-to-pixel scaling.

## Decision

`drawing_components.normalize_text_lines()` owns lossless line-boundary
normalization. It converts CRLF and CR to LF, splits on LF, and preserves empty
and trailing lines. It accepts only stored string state so hostile post-
construction mutation fails explicitly.

PDF retains its established per-line matrices and width-based alignment, but
consumes the shared normalized tuple. SVG emits one escaped `tspan` per line:
the first uses the text baseline `y`, and later lines use
`dy="<line_spacing>em"`. Every line repeats the parent `x` and alignment style.

Raster validates live text and `line_spacing` before allocating a surface. It
uses one Pillow baseline draw per line. For line index `i`, requested font size
`f` points, point scale `q`, spacing `l`, and logical baseline `(x, y)`, the
supersampled pixel baseline is:

```text
(round(x * canvas_scale), round(y * canvas_scale + i * f * q * l))
```

Line spacing may be zero, matching `TextStyle`; it must otherwise remain finite
and nonnegative. Character spacing and super/subscript remain outside the
standalone raster domain.

DXF behavior is unchanged. Its `TEXT` entity remains a single-line output that
normalizes embedded line breaks to spaces.

## Dependencies And Contracts

| Dependency | Consumed contract | Failure if changed |
|---|---|---|
| `drawing_components.py` | Ordered, lossless normalized line tuple | Renderers disagree about line count or trailing blanks |
| `TextStyle` | Finite nonnegative line spacing and normalized alignment | Baselines or anchors diverge |
| `TextPDF` | Established per-line matrix and width estimate | Existing PDF bytes or extraction positions change |
| `TextSVG` | Escaped tspans, relative `em` spacing, repeated anchor x | Viewers collapse or misalign lines |
| `raster_renderer.py` | Physical point scale and Pillow baseline anchors | Canvas units leak into font spacing or Baird input changes |
| Pillow | Baseline anchor and glyph rasterization for a resolved font | Pixel evidence changes across Pillow/font versions |

No third-party dependency is added. The dependency direction remains concrete
renderers to neutral normalization; neutral recipes still lazy-import concrete
renderers only during materialization.

## Consequences

- Within the current shared PDF/SVG/raster text domain, one neutral text recipe
  has the same normalized line sequence in every backend.
- Empty and trailing lines advance placement without inventing glyphs.
- Existing single-line SVG and PDF output remains unchanged.
- Raster multiline text composes directly with Baird without an SVG or PDF
  intermediary.
- Automatic wrapping, shaping, tracking, and super/subscript remain separate
  capabilities.

## Alternatives Rejected

- **Keep normalization in each renderer:** duplicates a contract that had
  already drifted.
- **Use Pillow `multiline_text()`:** obscures per-line baseline and alignment
  evidence and couples spacing to Pillow-specific layout policy.
- **Rasterize SVG or PDF:** violates the standalone renderer decision and adds
  an unnecessary serialized intermediary.
- **Change DXF to multiple entities in this slice:** expands a separate output
  contract without a defined DXF multiline ownership policy.
