# SVG Utilities Contract Proof Obligations

This note applies the InkGen Definition of Done to the SVG-UTILS-P1 external SVG
flattening slice. It covers style metadata extraction, length parsing, bbox
collection, no-geometry failure behavior, path normalization, and the
`SVGComponent` live path.

## Scope

The slice covers:

- `FlattenedPath`
- `FlattenedSVG`
- `_style_from_attributes()`
- `_parse_length()`
- `_collect_bbox()`
- `flatten_svg()`
- `SVGComponent(filepath=...)` as the live consumer

## Architecture Impact

Affected surface:

- `src/InkGen/svg_utils.py`: fixed empty/all-invalid bbox detection by comparing
  infinity by value instead of object identity.
- `tests/test_svg_utils_contract.py`: SVG-UTILS-P1 condition tests.
- `tests/mutation/svg_utils_cosmic_ray.toml`: scoped mutation gate.
- `tests/mutation/filter_svg_utils_work_items.py`: proof-critical mutation
  filter.
- `docs/proofs/svg-utils-contract.md`: proof note.

Incoming dependencies:

- `SVGComponent` consumes `flatten_svg()` for external SVG embedding.
- Public API docs expose `flatten_svg()` under utilities.
- SVG generator tests and downstream synthetic asset workflows rely on finite
  normalized geometry.

Outgoing dependencies:

- `svg_utils.py` depends on `svgpathtools.Path` and `svg2paths2`.
- No dependency was added.

Before/after edge changes:

- No dependency edge changed.
- Before this slice, `_collect_bbox([])` returned `((inf, inf), (-inf, -inf))`
  because it compared `min_x is float("inf")`.
- After this slice, empty or all-invalid path iterables return
  `((0.0, 0.0), (0.0, 0.0))`.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced.
- Layer check: SVG utility parsing remains in the text/layout utility layer
  consumed by the SVG renderer.
- Coupling check: no PDF/DXF/document dependency was added.
- Redundancy check: `flatten_svg()` remains the single external-SVG flattening
  helper.

ADR/rule impact:

- No new ADR is required. The slice keeps `SVGComponent` SVG-only, consistent
  with `docs/pdf-generation.md`.

## Domain Definitions

- A flattened SVG path is a path string plus optional style metadata.
- A valid contributing path is a `svgpathtools.Path` whose `.bbox()` call does
  not raise `ValueError`.
- Empty or all-invalid path collections have a finite zero bbox:
  `((0.0, 0.0), (0.0, 0.0))`.
- Length metadata is parsed by retaining digits, `.`, `-`, `e`, and `E`; invalid
  values return `None`.
- If an SVG element has an explicit `style` attribute, it takes precedence over
  individual fill/stroke attributes.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Explicit style attribute | Preserve exactly and ignore decomposed attributes | PO-SVGUTILS-001 | style parsing test | killed |
| Fill/stroke attributes | Join in deterministic order | PO-SVGUTILS-001 | style parsing test | killed |
| Numeric SVG lengths | Parse px/mm/scientific-like numeric values | PO-SVGUTILS-002 | length parsing test | killed |
| Invalid or missing lengths | Return `None` | PO-SVGUTILS-002 | length parsing test | killed |
| Empty/all-invalid path bboxes | Return finite zero bbox | PO-SVGUTILS-003 | bbox empty/invalid test | equivalent survivor |
| Valid path bboxes | Return finite min/max bbox | PO-SVGUTILS-003 | line bbox test | killed |
| External SVG file with paths | Normalize geometry and preserve metadata | PO-SVGUTILS-004 | flattening test | killed |
| SVG file with no vector paths | Fail loudly | Failure-mode test | no-path test | killed |
| `SVGComponent(filepath=...)` | Consumes flattened output in live path | PO-SVGUTILS-005 | live path test and existing SVG generator tests | killed |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Helper functions are deterministic. | `tests/test_svg_utils_contract.py` |
| Behavioral/condition | yes | The slice defines SVG-UTILS-P1 flattening behavior. | Tests are marked `@pytest.mark.condition("SVG-UTILS-P1")`. |
| Failure-mode | yes | SVG files without vector paths and empty bbox collections must fail or degrade safely. | no-path and bbox tests |
| Integration/live-path | yes | `SVGComponent` consumes `flatten_svg()` output. | live path test and existing SVG generator tests |
| Contract/API compatibility | yes | `FlattenedSVG` fields and utility parsing behavior are pinned. | contract tests |
| Property/fuzz | limited yes | Bounded deterministic partitions cover style, length, bbox, and flattening domains. | SVG-UTILS-P1 tests |
| Mutation | yes | Empty bbox detection and parsing branches are proof-critical. | Cosmic Ray result below |
| Security/adversarial | limited yes | The slice reads local SVG files but adds no network, subprocess, SQL, templates, or active content. | no-path failure test |
| Performance/resource | no | Flattening is linear over parsed paths. | Not applicable |
| Concurrency/race | no | No shared mutable global state is added. | Not applicable |
| Golden artifact/visual | yes | Flattened path strings and SVGComponent generated markup are text artifacts. | path/style/live markup tests |
| Regression | yes | This closes the empty/all-invalid bbox infinity regression. | `_collect_bbox([])` test and mutation |

## Mutation Testing Gate

Current result:

- Tool: Cosmic Ray 8.4.6.
- Environment: WSL Python 3.12 virtualenv.
- Raw work items: 79.
- Proof-critical work items after filter: 36.
- Killed mutants: 35.
- Equivalent survivors: 1.
- Surviving equivalent mutation:
  - `_collect_bbox()` changed `min_x == float("inf")` to
    `min_x >= float("inf")`. For the proven domain, `min_x` is either finite
    after at least one contributing path or positive infinity when no path
    contributes, so both predicates return the same result.
- Gate result: pass with documented equivalent survivor.

## PO-SVGUTILS-001: Style Metadata Is Deterministic

### Claim

Style metadata is preserved deterministically.

### Proof Method

Tests verify explicit `style` precedence, deterministic individual attribute
join order, and `None` for missing style metadata.

### Conclusion

Proven for the declared attribute set.

## PO-SVGUTILS-002: Length Parsing Is Stable

### Claim

SVG width/height metadata parses numeric content and returns `None` for missing
or invalid values.

### Proof Method

Tests cover `None`, ordinary decimals, negative values, scientific notation, and
invalid strings.

### Conclusion

Proven for the declared parsing behavior.

## PO-SVGUTILS-003: BBox Collection Is Finite

### Claim

Path bbox collection returns finite zero bounds when no path contributes
geometry, and finite min/max bounds when valid paths are present.

### Proof Method

Tests cover an empty iterable, an empty `Path()` that raises `ValueError` from
`.bbox()`, and a valid `Line` path. Mutation kills the previous identity-check
regression.

### Conclusion

Proven for empty, invalid, and valid path partitions.

## PO-SVGUTILS-004: Flattened SVG Geometry Is Normalized

### Claim

`flatten_svg()` normalizes external SVG path geometry to a finite origin-based
bbox and preserves path style and size metadata.

### Proof Method

Tests write a temporary SVG with multiple paths and metadata, call
`flatten_svg()`, and assert the normalized bbox, path strings, style order, and
parsed width/height.

### Conclusion

Proven for SVG files parsed by `svgpathtools.svg2paths2()` in the tested domain.

## PO-SVGUTILS-005: SVGComponent Uses Flattened Output

### Claim

`SVGComponent(filepath=...)` consumes flattened SVG paths in the live render
path.

### Proof Method

Tests construct `SVGComponent` from a temporary SVG file, then assert scaled
points, preserved width/height metadata, and generated SVG markup style.

### Conclusion

Proven for the live SVG embedding path.
