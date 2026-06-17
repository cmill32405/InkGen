# Arc Renderer Contract Proof Obligations

This note applies the InkGen Definition of Done to the ARC-P1 arc
renderer-contract slice. It focuses on elliptical arc sampling, radius
validation, and the dependency path from renderer-neutral drawing recipes into
PDF and DXF output.

## Scope

The slice covers arc geometry owned by `src/InkGen/component.py`, sampled
polyline rendering in `src/InkGen/pdf_generator.py`, renderer-neutral
materialization in `src/InkGen/drawing_components.py`, and DXF curve export in
`src/InkGen/dxf_generator.py`.

The public behavior under review is:

- `Arc._validate_radius()`
- `Arc.points`
- `ArcPDF.generate_pdf()`
- `ArcDrawing.to_component(OutputFormat.PDF)`
- `DXFDocument.add_group()` for `ArcDrawing`

## Architecture Impact

Affected surface:

- `src/InkGen/component.py`: source of sampled elliptical arc geometry and
  radius validation.
- `src/InkGen/pdf_generator.py`: PDF arc rendering as an open sampled path.
- `src/InkGen/drawing_components.py`: neutral arc recipe materialization to
  concrete renderers.
- `src/InkGen/dxf_generator.py`: DXF polyline output that intentionally reuses
  PDF-materialized sampled points for curves.
- `tests/test_curve_contract.py`: math, validation, renderer, and
  dependency-path evidence.

Incoming dependencies:

- SVG/PDF/DXF renderers, labels, masks, truth emitters, generated fixtures, and
  synthetic drawing consumers rely on stable arc `points`, `bbox`, and
  `convex_hull` semantics.
- PDF fixture consumers rely on `ArcPDF.generate_pdf()` emitting an open path
  whose vertices match `Arc.points`.
- DXF export relies on `ArcDrawing.to_component(OutputFormat.PDF)` returning a
  concrete component whose sampled `points` represent the neutral arc.

Outgoing dependencies:

- `Arc` depends only on numeric center/radii/angle inputs, `DrawingStyle`,
  `math`, and the shared `PRECISION` / `DEFAULT_CURVE_SAMPLES` constants.
- `ArcPDF` depends on the shared `Arc.points` geometry contract and the local
  `_path_from_points()` / `_drawing_pdf()` helpers.
- `DXFDocument` depends on renderer-neutral drawing recipes and intentionally
  materializes curve-like drawings through the PDF path for sampled geometry.

Before/after edge changes:

- No new production dependency edge was added in this slice.
- The existing edge
  `dxf_generator.py -> component.to_component(OutputFormat.PDF)` for sampled
  geometry is now explicitly tested for `ArcDrawing`.
- The existing neutral recipe edge `ArcDrawing -> ArcPDF` is now explicitly
  tested for PDF output.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced. Components do not import PDF or DXF.
- Layer check: concrete renderers depend on component geometry and neutral
  recipes according to `docs/dependency-map.md`.
- Coupling check: DXF's reuse of PDF sampled points is explicit and tested.
- Redundancy check: the slice avoids introducing a second arc sampling
  implementation for PDF or DXF.

Evidence source and freshness:

- Source-backed: `component.py`, `pdf_generator.py`, `drawing_components.py`,
  and `dxf_generator.py` were read before adding tests.
- Test-backed: focused tests in `test_curve_contract.py` exercise the math,
  validation, and live dependency paths.
- Design-backed: `docs/dependency-map.md` already records the DXF-to-PDF
  sampled geometry edge as intentional.
- No architecture claim in this section relies only on stale memory.

ADR/rule impact:

- No new ADR is required because no new architecture decision was made.
- A future change that replaces PDF or DXF sampled arc rendering with native
  PDF/DXF arc entities should add or update an ADR because it changes the
  generated-artifact contract and dependency direction.

## Domain Definitions

- An arc is defined by numeric `center`, positive `radius_x`, positive
  `radius_y`, `start_angle`, `end_angle`, and `rotation`, with angles in
  degrees.
- `DEFAULT_CURVE_SAMPLES` is the positive integer number of sample intervals.
- `PRECISION` is the number of decimal places used by InkGen component point
  output.
- Non-zero-span `Arc.points` returns sample points for
  `angle = start_angle + (end_angle - start_angle) * i / DEFAULT_CURVE_SAMPLES`,
  for integer `i` from `0` through `DEFAULT_CURVE_SAMPLES`, rounded to
  `PRECISION`.
- Zero-span arcs, where start and end angles are close after radian conversion,
  return one sampled point.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid numeric center/radii/angles without rotation | Emit sampled points from the unrotated ellipse formula, rounded to `PRECISION` | PO-ARC-001 | `test_arc_samples_follow_ellipse_rotation_formula` | Must be killed or proven equivalent |
| Valid numeric center/radii/angles with rotation | Apply the standard 2D rotation matrix before translating to center | PO-ARC-001 | `test_arc_samples_follow_ellipse_rotation_formula` | Must be killed or proven equivalent |
| Reverse angle direction | Preserve the caller's start-to-end interpolation direction | PO-ARC-001 | `test_arc_samples_follow_ellipse_rotation_formula` | Must be killed or proven equivalent |
| Equal start and end angles | Emit exactly one sampled point | PO-ARC-001 | `test_arc_equal_start_and_end_angle_emits_single_sample` | Must be killed or proven equivalent |
| Non-positive radii | Reject at construction and setter boundaries with `ValueError` | PO-ARC-002 | `test_arc_rejects_non_positive_radii` | Must be killed or proven equivalent |
| PDF arc rendering | Emit an open sampled PDF path from `Arc.points` with stroke-only painting | PO-ARC-003 | `test_arc_pdf_emits_sampled_open_polyline` | Must be killed or proven equivalent |
| Renderer-neutral arc drawing exported to DXF | Materialize to PDF and emit DXF polyline vertices from the same sampled points | PO-ARC-004 | `test_arc_drawing_materializes_pdf_component`; `test_dxf_arc_drawing_reuses_pdf_sample_points` | Must be killed or proven equivalent |
| Non-numeric center/angles, non-finite values, hostile mutation of private fields, monkey-patched renderers, non-default sample counts, and native PDF/DXF arc entities | Excluded from proven domain | Explicit exclusions in PO-ARC-001 through PO-ARC-004 | none | Out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Arc sampling and radius validation are deterministic math/validation units. | `test_arc_samples_follow_ellipse_rotation_formula`; `test_arc_rejects_non_positive_radii` |
| Behavioral/condition | yes | ARC-P1 defines expected arc behavior across component, PDF, neutral recipe, and DXF paths. | New tests are marked `@pytest.mark.condition("ARC-P1")`. |
| Failure-mode | yes | Non-positive radii are invalid construction/setter inputs. | `test_arc_rejects_non_positive_radii` |
| Integration/live-path | yes | DXF must exercise the public neutral group path, not just a helper. | `test_dxf_arc_drawing_reuses_pdf_sample_points` calls `DXFDocument.add_group()`. |
| Contract/API compatibility | yes | Existing point and parameter contracts must remain stable. | Existing arc parameter tests plus ARC-P1 point tests. |
| Property/fuzz | yes | Arc sampling has a deterministic formula over sampled angles. | Deterministic bounded property-style tests plus algebraic proof below. |
| Mutation | yes | Arc sampling, radius validation, renderer dispatch, and PDF/DXF path generation are proof-critical. | Mutation run result recorded below. |
| Security/adversarial | no | The slice adds no file path, network, subprocess, auth, secrets, SQL, template, deserialization, font, image, or active-content surface. | Not applicable. |
| Performance/resource | no | The slice uses fixed `DEFAULT_CURVE_SAMPLES` and adds no unbounded loop or cache. | Not applicable. |
| Concurrency/race | no | The slice adds no shared mutable global state, background workers, sessions, locks, queues, or temp-file coordination. | Not applicable. |
| Observability/logging | no | The slice adds no state-changing service, background work, external call, or recovery path. | Not applicable. |
| Golden artifact/visual | yes | PDF and DXF generated geometry must be stable enough for synthetic fixtures. | PDF operator/path test and DXF vertex test. |
| Regression | yes | This slice extends the prior curve-proof pattern to a similar renderer dependency path before a defect is reported. | ARC-P1 tests named above. |

## Invariants, Preconditions, And Postconditions

Invariants:

- Arc sampled points are computed from the ellipse formula, rotated by the
  standard 2D rotation matrix, translated by center, and rounded to
  `PRECISION`.
- The first sampled point is the rotated start-angle point and the last sampled
  point is the rotated end-angle point for non-zero-span arcs.
- Equal start/end angles emit one sampled point.
- Radius values are strictly positive after construction and after setter
  calls.
- PDF and DXF arc output use the same sampled points as the component geometry.

Preconditions:

- Center is a two-item numeric tuple/list accepted by `Arc`.
- Radius values are numeric and greater than zero.
- Angles are finite numeric values in degrees.
- Callers do not monkey-patch curve classes or mutate private fields.

Postconditions:

- Non-zero-span `Arc.points` returns `DEFAULT_CURVE_SAMPLES + 1` sampled points.
- Zero-span `Arc.points` returns one sampled point.
- `ArcPDF.generate_pdf()` emits an open PDF path from those points and uses
  stroke-only painting for arcs.
- `DXFDocument.add_group()` emits an open `LWPOLYLINE` whose vertices match the
  PDF-materialized arc sample points.

## Mutation Testing Gate

Proof-critical mutation targets:

- Changing any ellipse, interpolation, rotation, translation, or rounding term
  in `Arc.points` should fail formula and endpoint tests.
- Changing radius validation from strict positive should fail invalid-radius
  tests.
- Closing or filling PDF arc paths should fail PDF operator tests.
- Redirecting DXF arc export away from `component.to_component(OutputFormat.PDF).points`
  without preserving vertices should fail the DXF dependency-path test.

Current result:

- Tool and version: Cosmic Ray 8.4.6 in WSL.
- Mutated source paths: `src/InkGen/component.py`,
  `src/InkGen/drawing_components.py`, `src/InkGen/pdf_generator.py`, and
  `src/InkGen/dxf_generator.py`.
- Reproducible setup:
  `cosmic-ray baseline tests/mutation/arc_cosmic_ray.toml`,
  `cosmic-ray init tests/mutation/arc_cosmic_ray.toml
  /tmp/inkgen_arc_mutation.sqlite`, then
  `python tests/mutation/filter_arc_work_items.py
  /tmp/inkgen_arc_mutation.sqlite --clear-results`.
- Test selection:
  `python -m pytest -x tests/test_curve_contract.py
  tests/test_drawing_components.py tests/test_pdf_generator.py
  tests/test_dxf_generator.py`.
- Proof-critical work items after filtering: 195.
- Mutants killed: 191.
- Mutants survived: 4.
- Mutants excluded/equivalent: 4 equivalent mutants:

  - `src/InkGen/component.py:1367`: `range(self._samples | 1)` and
    `range(self._samples ^ 1)`. Within the declared public domain,
    `Arc.__init__()` assigns `_samples = max(1, DEFAULT_CURVE_SAMPLES)` and
    `DEFAULT_CURVE_SAMPLES == 32`, so:

    ```text
    _samples + 1 == 33
    _samples | 1 == 33
    _samples ^ 1 == 33
    ```

  - `src/InkGen/drawing_components.py:120`: `target == OutputFormat.SVG` and
    `target >= OutputFormat.SVG`. Within the declared public domain,
    `normalize_output_format()` returns one of exactly two string-enum values:
    `OutputFormat.SVG == "svg"` or `OutputFormat.PDF == "pdf"`. Therefore:

    ```text
    OutputFormat.SVG is OutputFormat.SVG => true
    OutputFormat.SVG == OutputFormat.SVG => true
    OutputFormat.SVG >= OutputFormat.SVG => true
    OutputFormat.PDF is OutputFormat.SVG => false
    OutputFormat.PDF == OutputFormat.SVG => false
    OutputFormat.PDF >= OutputFormat.SVG => false, because "pdf" < "svg"
    ```

    If a future output format is added, this equivalence must be revisited.

  Direct mutation of `_samples`, non-default sample counts, and output formats
  beyond SVG/PDF are excluded from this proof.
- Gate result: passed for the declared domain. The mutation report has no
  surviving non-equivalent proof-critical mutants.

During the first mutation pass, a real test gap was found in the zero-span
tolerance boundary: a mutant widening `abs_tol=1e-9` to approximately `1.0`
collapsed a tiny non-zero arc to one point. The
`test_arc_tiny_nonzero_angle_span_still_samples_curve` regression now kills
that mutant.

## PO-ARC-001: Rotated Ellipse Sample Formula

### Claim

`Arc.points` emits points from the rotated ellipse formula rounded to InkGen
`PRECISION`.

### Domain

All arc components with finite numeric center, strictly positive radii, finite
numeric angles, and the default positive sample interval count.

### Assumptions

- Python `math.sin`, `math.cos`, and `math.radians` have their standard
  meanings for finite numeric values.
- `round(value, PRECISION)` is the public point precision contract for InkGen
  components.

### Theorem

For every non-zero-span sample index `i` where
`0 <= i <= DEFAULT_CURVE_SAMPLES`, with:

```text
theta = radians(start_angle + (end_angle - start_angle) * i / DEFAULT_CURVE_SAMPLES)
phi = radians(rotation)
x = radius_x * cos(theta)
y = radius_y * sin(theta)
```

the emitted point is:

```text
round(center.x + x*cos(phi) - y*sin(phi), PRECISION)
round(center.y + x*sin(phi) + y*cos(phi), PRECISION)
```

For zero-span arcs, the single emitted point uses `theta = radians(start_angle)`.

### Proof Method

Static/algebraic reasoning over `Arc.points`:

1. The method converts start/end angles to radians.
2. If start and end are close, it uses a one-item list containing start.
3. Otherwise, it iterates `step` from `0` through `_samples` and assigns
   `theta = start + (end - start) * (step / _samples)`.
4. It converts rotation to radians and computes `cos(rotation)` and
   `sin(rotation)`.
5. For every `theta`, it computes unrotated ellipse coordinates
   `radius_x*cos(theta)` and `radius_y*sin(theta)`.
6. It applies the standard rotation matrix and translates by center.
7. It appends each coordinate rounded to `PRECISION`.
8. Therefore every emitted point matches the theorem.

### Counterexamples And Exclusions

- Non-finite numeric values are outside the proof.
- Direct mutation of `_samples` to a non-positive or non-default value is outside
  the public construction contract.
- Rounding can move a value by up to the precision unit; exact unrounded ellipse
  membership is not claimed for serialized points.

### Conclusion

Proven for the stated domain.

## PO-ARC-002: Strict Positive Radius Boundary

### Claim

Arc radii are strictly positive after construction and after public setter
calls.

### Domain

All public construction and setter calls for `radius_x` and `radius_y`.

### Proof Method

Construction calls `_validate_radius()` for both radii, and both setters call
the same helper. `_validate_radius()` converts the value to float and raises
`ValueError` when the radius is less than or equal to zero. Therefore no
public construction or setter path can store a non-positive radius.

### Conclusion

Proven for the stated domain.

## PO-ARC-003: PDF Arc Uses Open Sampled Path

### Claim

`ArcPDF.generate_pdf()` emits an open, stroke-only PDF path from `Arc.points`.

### Domain

All `ArcPDF` instances in the stated arc domain.

### Proof Method

`ArcPDF.generate_pdf()` calls `_path_from_points(list(self.points), close=False)`
and passes the resulting path to `_drawing_pdf(..., fill=False)`. Therefore the
path starts at the first sampled point, emits one line operator for each
remaining sampled point, does not append a close-path operator, and uses
stroke-only painting.

### Conclusion

Proven for the stated domain.

## PO-ARC-004: DXF Reuses PDF-Sampled Neutral Arc Geometry

### Claim

DXF export for a neutral `ArcDrawing` emits vertices from the same sampled
points as the neutral arc's PDF materialization.

### Domain

All `ArcDrawing` instances exported through `DXFDocument.add_group()`.

### Proof Method

Static path proof over `drawing_components.py` and `dxf_generator.py`:

1. `ArcDrawing.to_component(OutputFormat.PDF)` returns an `ArcPDF`.
2. `DXFDocument.add_group()` iterates over `group.components`.
3. `_component_to_entities()` matches `ArcDrawing` in the curve branch.
4. That branch assigns `concrete = component.to_component(OutputFormat.PDF)`.
5. It returns `_lwpolyline_entity(concrete.points, context, closed=False)`.
6. `_lwpolyline_entity()` emits one vertex for each supplied point.
7. Therefore the generated vertices are the PDF-materialized sampled points,
   transformed only by `DXFRenderContext.point()`.

### Counterexamples And Exclusions

- Native DXF spline/entity output is not part of the current contract.
- If DXF changes to a native curve representation, this proof must be replaced
  and an ADR should record the new dependency direction.

### Conclusion

Proven for the stated domain.

## Current Slice Decision

The slice has mathematical proof for rotated ellipse sampling, strict radius
validation, and sampled open-path rendering, plus live-path evidence for neutral
recipe and DXF dependency propagation.

The main design constraint is that PDF and DXF arc export intentionally depend
on sampled component points, not native arc entities. That edge is now explicit
and tested.
