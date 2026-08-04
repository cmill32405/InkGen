# Multiline Text Contract Proof

Conditions: `TEXT-MULTILINE-P11` and `RASTER-TEXT-MULTILINE-P11`.

## Claim

For every text value and `TextStyle` in the declared shared backend domain,
PDF, SVG, and standalone raster output consume the same ordered normalized line
tuple. SVG and raster materialize every line with deterministic spacing and
alignment, existing single-line bytes remain unchanged, and malformed live
raster text or spacing fails before surface allocation.

## Domain

- Stored text is a string accepted by `TextDrawing` and the current PDF text
  encoding contract.
- CRLF, CR, and LF are line boundaries; empty and trailing lines are values.
- `TextStyle.line_spacing` is finite and nonnegative.
- `TextStyle.text_align` is `start`, `center`, or `end`.
- Raster text otherwise remains in `RASTER-TEXT-P3`: zero character spacing,
  no super/subscript, and a resolvable font file.
- Pixel determinism is scoped to the same font bytes and Pillow runtime.

Automatic wrapping, tabs, columns, text outside the current PDF encoding
domain, bidirectional shaping, and complex-script layout are outside this
proof.

## Dependency And Contract Review

The source-backed dependency path is:

```text
TextDrawing/TextStyle -> normalize_text_lines
                       -> TextPDF
                       -> TextSVG
                       -> raster_renderer -> RasterImageAsset -> Baird
```

The normalizer owns no concrete renderer imports. PDF, SVG, and raster already
depend on neutral drawing contracts, so the shared helper adds no reverse edge
or third-party package. DXF keeps its documented single-entity newline-flatten
policy and is not changed by this slice. ADR-0035 records the cross-output
contract.

## Mathematical Proof

Define line normalization `N` as replacement of CRLF by LF, replacement of
remaining CR by LF, and exact splitting on LF. Python's string replacement and
split operations are deterministic, ordered, and preserve empty fields between
or after delimiters. Therefore, for every string `t`, all consumers receive the
same finite tuple `N(t)`.

For raster output, let `i` be a zero-based line index, `f > 0` the font size in
points, `q = dpi * supersample / 72 > 0`, `l >= 0` the line-spacing factor,
`c > 0` the canvas-unit pixel scale, and `(x, y)` the finite neutral baseline.
The renderer uses:

```text
X(i) = round(x * c)
Y(i) = round(y * c + i * f * q * l)
```

`X` is invariant across lines. Before allocation, validation proves every term
is finite and `l` is nonnegative. For adjacent lines before rounding, baseline
delta is exactly `f * q * l`; zero spacing overlaps by contract and positive
spacing never reverses line order. Each alignment has an exhaustive Pillow
baseline-anchor mapping: `start -> ls`, `center -> ms`, and `end -> rs`.

For SVG, the first line owns absolute `y`; every later line owns relative
`dy=l em`. Because `em` is the current text font size, adjacent unrounded
baseline delta is also `f * l` in SVG font space. Repeating parent `x` and the
alignment style makes line alignment independent rather than dependent on the
previous line width.

PDF's established proof remains unchanged: it positions every normalized line
at `y + i * f * l` and calculates each aligned x from that line's width. The
only PDF code change substitutes `N(t)` for the identical inline normalization.

## Comprehensiveness Matrix

| Domain class | Required result | Evidence |
|---|---|---|
| LF, CR, and CRLF | identical ordered line tuple | neutral normalization test |
| Empty and trailing lines | preserve fields and baseline advancement | neutral, SVG, and raster call tests |
| Start/center/end | same anchor for every line | exhaustive raster test; SVG style test |
| Zero/fractional spacing | overlap or proportional forward spacing | style boundary plus exact baseline tests |
| XML-special characters | escape each SVG line | multiline SVG test |
| Single-line input | preserve established output | existing exact SVG/PDF/raster tests |
| Public raster/Baird path | produce clean and degraded assets | integration test |
| Live non-string text | reject before surface allocation | allocation sentinel test |
| Live bool/string/NaN/Inf/negative spacing | reject before allocation | exhaustive failure-mode test |
| Tracking/super/subscript | remain explicit raster failures | existing P3 tests |
| Automatic wrapping/complex shaping | excluded | documented boundary |

## Mutation Gate

Cosmic Ray 8.4.6 targets `normalize_text_lines()`, the P11 portion of
`TextSVG.generate_svg()`, `_validated_raster_text()`, `_render_text()`, and the
pre-allocation live-path call. Exact campaign counts and any equivalent-mutant
proofs are recorded in `tests/mutation/multiline_text_p11_evidence.json` and
enforced by an executable manifest test.

The final isolated campaign generated 7,872 module candidates and selected 113
P11 work items. All 113 completed with normal worker outcomes: 111 were killed
and two survived. Both survivors replace `index == 0` with `index <= 0` in the
SVG first-line `y` and ID-suffix branches. Because the index is produced only
by `enumerate(lines)`, it is a nonnegative integer; therefore the predicates
are equivalent. Raw mutation coverage is 98.23%, and effective coverage after
the equivalence proof is 100%.

## Verification Status

- Focused text/SVG/PDF/raster and evidence suite: 133 passed (Clarvis artifact
  9410).
- P11 mutation: 113/113 normal worker outcomes, 111 killed, and two proven
  equivalent, for 100% effective mutation coverage (Clarvis artifact 9385).
- Dependent retained proofs were rerun against the P11 source: text-boundary
  90 killed/one equivalent (artifact 9397), PDF presentation 301 killed/three
  equivalent (artifacts 9398 and 9400), and raster gradient 298 killed/13
  equivalent (artifacts 9396, 9399, and 9402). The gradient refresh exposed
  and killed one non-equivalent exact-tile-boundary survivor.
- Changed-line coverage: 34/34 executable production lines, 100% (artifact
  9410 plus the staged-diff correlation check).
- Exact-index full regression: 2,228 passed in deterministic shards of 947,
  653, and 628 tests (Clarvis artifacts 9411, 9412, and 9413).
- Ruff lint, scoped formatter checks, Python compilation, all mutation-evidence
  JSON parsing, strict MkDocs, and staged patch whitespace checks passed.
- `pdf_generator.py` and `svg_generator.py` retain pre-existing whole-file
  Ruff formatter debt; P11 keeps both diffs minimal and lint-clean. All other
  touched Python files are formatter-clean.
- Dependency manifests are unchanged; no package dependency was added.
