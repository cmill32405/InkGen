# Raster Text Contract Proof

Condition: `RASTER-TEXT-P3`.

## Claim

For valid single-line neutral text in the declared P3 presentation domain,
the standalone raster renderer selects InkGen's resolved font file, converts
font points independently from canvas coordinate units, maps the neutral
baseline alignment to the corresponding Pillow baseline anchor, and produces
a clean RGBA asset that remains valid input to the Baird composition path.

## Domain

- The component is a valid `TextDrawing` with a finite baseline position.
- Text contains no carriage return or line feed.
- `TextStyle.character_spacing` is zero and super/subscript are false.
- Font size, color, visibility, and alignment satisfy `TextStyle` and `Font`.
- Canvas, DPI, supersampling, background, and runtime satisfy
  `RASTER-RENDERER-P1`.
- Pixel and byte determinism are scoped to the same resolved font file and
  Pillow runtime.

## Mathematical Proof

Let `d` be positive DPI, `s` the integer supersampling factor, `f` the positive
font size in points, and `(x, y)` the text baseline in canvas units. Define:

```text
q(d, s) = d * s / 72
n(f, d, s) = max(1, round(f * q(d, s)))
T(x, y) = (round(x * p * s), round(y * p * s))
```

where `p = d` for inches and `p = d / 25.4` for millimeters, as established by
`RASTER-RENDERER-P1`. The renderer passes the exact resolved `font_file` and
integer size `n` to Pillow, then emits one text operation at `T(x, y)`.
Therefore font size depends only on points, DPI, and supersampling, not on the
canvas coordinate unit. Position depends on the existing physical coordinate
transform exactly once.

The normalized alignment set is finite. Exhaustive dispatch is:

```text
start  -> ls
center -> ms
end    -> rs
```

All three Pillow anchors share the supplied baseline `y`; only horizontal
anchoring changes. For fixed text, font-file bytes, size, position, color,
anchor, and Pillow runtime, the emitted draw call is identical. Ordered source-
over compositing and clean-to-Baird validity then follow from the P1 and Baird
composition proofs.

## Comprehensiveness Matrix

| Domain class | Handling | Evidence |
|---|---|---|
| Visible single-line text | render resolved font at physical point size | public scan-path test |
| Start/center/end alignment | map to `ls`/`ms`/`rs` | exhaustive parameterized test |
| Inch versus millimeter canvas | keep point scale independent | exact public-call test |
| Empty/invisible/no-color text | transparent no-op | boundary tests |
| Multiline/tracking/super/subscript | reject before surface allocation | failure-mode tests |
| Font backend failure | raise renderer-specific `ValueError` | dependency-failure test |
| Complex-script semantic equivalence | excluded from P3 proof | documented residual boundary |

## Verification Status

- Text condition tests: 16 passed.
- Combined raster/curve/text/composition focused gate: 60 passed.
- `raster_renderer.py` statement and branch coverage: 100%.
- Exact staged mutation: 993 generated candidates, 45 contract-relevant work
  items, 45 killed, and zero survivors, worker errors, or timeouts.
- Exact staged-snapshot regression: 2,049 passed.
- Working-tree regression, including unrelated local tests outside this slice:
  2,063 passed.
- Ruff lint and format checks, strict MkDocs build, mutation-evidence hash
  correlation, and cached-diff hygiene passed for the staged slice.
