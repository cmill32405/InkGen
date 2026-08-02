# Standalone SVG Region Emission Proof Obligations

This note applies the Definition of Done to condition `SVG-REGION-P1`.
The class and dependency flow is recorded in
[`region-emission.mmd`](../diagrams/region-emission.mmd).

## Scope

- `SvgClipWindow`
- `PositionedTextRun`
- `emit_svg_region()`
- `outline_for_text_bytes()`

## Dependency Review

Incoming dependencies:

- Document verification and recreation callers can pass parser-extracted
  embedded font bytes, positioned text, neutral InkGen primitives, and a source
  bounding box.
- Package-root callers import the complete region API from `InkGen`.

Outgoing dependencies:

- `region_svg.py` depends on `drawing_components.OutputFormat` only to
  materialize existing neutral recipes as SVG components.
- It depends on `component.TextComponent` to reject system-font-dependent text
  at the composition boundary.
- It depends on `text_outline.outline_for_text()` and
  `outline_for_text_bytes()` for shaping and glyph geometry.
- `outline_for_text_bytes()` uses the already approved HarfBuzz and fontTools
  dependencies through the same implementation as the file-path API.
- XML validation uses the Python standard library. No dependency was added.

Contract edge:

- The region layer composes generated fragments but does not own primitive
  geometry, SVG component rendering, PDF parsing, font discovery, or raster
  rendering.
- `document_outputs.py` is not involved. Document outputs may consume drawing
  primitives; they do not own standalone drawing rendering.

## Preconditions And Invariants

| ID | Obligation | Failure behavior |
|---|---|---|
| SR-001 | Clip coordinates are finite and dimensions are positive. | Construction raises before XML emission. |
| SR-002 | Each text run has exactly one readable font path or nonempty byte program. | Construction raises; no system-font fallback occurs. |
| SR-003 | Font bytes and the same source file produce identical path geometry. | Behavioral comparison detects divergence. |
| SR-004 | The viewport and clip rectangle describe the same user-space window. | XML contract assertions detect coordinate drift. |
| SR-005 | Text is represented by glyph paths, never SVG `<text>`. | Text components fail closed and output inspection detects regressions. |
| SR-006 | Output has no network-dependent resource. | External href, CSS URL, script, import, or foreign-object content is rejected. |
| SR-007 | Neutral primitives use their live SVG materialization path. | A real `RectangleDrawing` is asserted in complete parsed output. |
| SR-008 | Text and attribute metacharacters cannot change XML structure. | Parsed title and path assertions cover escaped content. |

For a validated window `(x, y, w, h)`, `w > 0` and `h > 0`. The root
`viewBox` and clip rectangle are both exactly `(x, y, w, h)`. Therefore every
painted point visible in the returned viewport is constrained to the requested
window by the SVG clip operation. This proof is conditional on conforming SVG
viewer semantics; it does not prove a particular viewer implementation.

## Behavioral And Functional Proof

`tests/test_region_svg_contract.py` exercises:

- a real installed TrueType font through both file and byte APIs;
- a real neutral rectangle through `to_component(OutputFormat.SVG)`;
- complete XML parsing, viewport identity, clipping, outlined Unicode source
  metadata, background paint, and absence of `<text>`;
- empty, non-finite, and non-positive clip geometry;
- missing, duplicate, and empty font sources;
- rejection of ordinary neutral text, external image/CSS references, active
  content, and XML processing instructions.
- a Hypothesis property test over 100 finite windows proving serialized
  viewport and clip tuples remain identical.

The package root exports all four public surfaces. The live function invokes
the established SVG primitive renderer and text-outline implementation rather
than a test-only adapter.

## Mutation Gate

Scoped Cosmic Ray configuration and work-item filtering cover
`region_svg.py` and the new byte-font branch in `text_outline.py`. Equivalent
survivors, if any, must be documented before the slice is reported complete.

Current scoped result: Cosmic Ray 8.4.6 generated 818 candidates and the
proof-critical filter selected 297 work items. All 297 were killed; no survivor
or equivalent exclusion remains. The run used a disposable Git worktree and
the focused region, outline, and public-API tests.
