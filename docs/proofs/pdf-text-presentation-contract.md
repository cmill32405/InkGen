# PDF Text Presentation Contract

Condition: `PDF-TEXT-PRESENTATION-P3`

## Claim

For every valid `TextStyle`, PDF text visibility and character spacing are
deterministic, serialized, extraction-safe, and wired through the public
`DocumentPDF` path. Default styles preserve prior PDF operator output.

## Dependency And Contract Review

- `style.py` owns validation, defaults, and serialized `TextStyle` state.
- `component.py` owns text points, bounding boxes, convex hulls, and the cache
  consumed by placement, collision, and canvas-boundary checks.
- `drawing_components.py` carries the same style through neutral `TextDrawing`
  materialization.
- `pdf_generator.py` owns `Tr`, `Tc`, alignment-width calculations, and page
  content-stream emission.
- `document.py` rejects component groups whose adjusted points are off canvas.
- Existing SVG, DXF, and flow-document renderers import `TextStyle` but do not
  consume these new fields. Their output contracts remain unchanged.
- No new module edge, package dependency, font contract, or PDF encoding domain
  is introduced.

## Contract Partitions

| Partition | Required result |
|---|---|
| Default style | `visible=True`, `character_spacing=0.0`, no `Tr` or `Tc` operator |
| Invisible style | Emit `3 Tr`; text remains extractable and paints no pixels |
| Positive spacing | Emit positive `Tc`; extracted span width and conservative bounds expand |
| Negative spacing | Emit negative `Tc`; extracted span contracts while conservative bounds extend left |
| Center/end alignment | Include exactly `max(len(line)-1, 0)` spacing intervals |
| Multiline text | Normalize CRLF/CR/LF and use the largest line-local interval count for bounds |
| Empty/single-character text | Apply zero spacing intervals |
| Legacy payload | Hydrate missing fields to visible/zero-spacing defaults |
| Invalid values | Reject non-boolean visibility and boolean, nonnumeric, or nonfinite spacing |
| Style mutation | Recompute cached text bounds before the next geometry read |

## Three-Level Proof

- **Structural:** `TextStyle` exposes validated fields; `TextPDF.generate_pdf()`
  maps them to `Tr` and `Tc`; `TextComponent` incorporates spacing into cached
  bounds.
- **Behavioral:** 26 condition tests cover defaults, malformed values,
  hydration, exact operators, exact interval arithmetic, positive/negative and
  multiline bounds, fallback geometry, cache invalidation, neutral
  materialization, and equivalent-survivor domains.
- **Functional:** a public `DocumentPDF` is parsed and rendered with PyMuPDF.
  Invisible text is extracted verbatim while every rendered pixel stays white;
  the visible control paints nonwhite pixels. Positive and negative `Tc` values
  change the extracted run width in the required direction.

## Mutation Evidence

The source-and-test-fresh Cosmic Ray v4 campaign contains 271 scoped mutants.
All workers completed normally: 268 were killed and three survived as exact
equivalents. Database SHA-256:
`55DC8A415B47FFFF03141CF972D8CB607781B47A324B8D9513B77278E548261D`.

The survivors are pinned by job id in
`test_pdf_text_presentation_mutation_evidence.py`:

1. `_apply_character_spacing_bounds`: replacing the no-span `or` with `and` is
   equivalent because horizontal and vertical helpers inspect the same four
   supported surfaces. The test exhausts all 16 surface-presence subsets.
2. `_pdf_text_aligned_x` center equality versus lexical `<=` is equivalent over
   the validated domain `{start, center, end}`.
3. The end comparison is reached only for `{start, end}` after the center
   branch; equality and lexical `<=` are identical on that set.

The evidence manifest records source/config/test hashes, timestamps, database
identity, all work-item outcomes, and survivor diffs in
`tests/mutation/pdf_text_presentation_v4_evidence.json`.

## Verification Gate

- Focused style, text, PDF, and mutation-evidence gate: 201 passed.
- Full repository branch-coverage gate: 1,924 passed.
- Aggregate branch coverage: 96.46%, above the enforced 95% threshold.
- Ruff lint, scoped format checks, Python compilation, strict MkDocs build, and
  changed-scope `git diff --check` passed.
- InkGen does not provide a `traceability_report.py` command; condition markers,
  proof notes, ADR-0031, and pinned mutation manifests provide traceability for
  this slice.

## Mathematical Invariants

For a line of `n` characters, font-size estimate `s`, and character spacing
`c`, InkGen's PDF alignment model is:

`width(n, s, c) = 0.6 * n * s + max(n - 1, 0) * c`

Therefore the spacing contribution is zero for `n` in `{0, 1}`, applies only
between glyphs, and is linear in both interval count and spacing. Center origin
is `anchor_x - width/2`; end origin is `anchor_x - width`.

Conservative geometry uses `d = c * max_line(max(n - 1, 0))`. It expands the
base horizontal interval `[left, right]` to
`[left + min(d, 0), right + max(d, 0)]`. This contains the original interval
and the maximal cumulative spacing displacement for every finite signed `d`.

## Residuals

- Visibility suppresses glyph paint but intentionally does not remove bounds or
  bypass normal canvas checks.
- One `TextStyle` represents one presentation run. Documents needing different
  tracking values create distinct styles/runs.
- The current PDF text encoding remains WinAnsi as defined by ADR-0023/0024.
- Other output backends do not yet map visibility or character spacing.
