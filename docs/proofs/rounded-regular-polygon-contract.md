# Rounded Regular Polygon Contract Proof

Condition: `RASTER-ROUNDED-POLYGON-P9`.

## Claim

For every validated regular polygon with `n >= 3`, circumradius `R > 0`, and
`0 < corner_radius <= R / 2`, InkGen constructs one non-overlapping circular
corner tangent to both incident edges at every vertex. SVG, PDF, DXF, and
standalone raster output consume that canonical geometry; radius zero preserves
the established sharp backend paths.

## Pre-Change Dependency And Contract Review

- `RegularPolygonDrawingComponent` owns the sharp control vertices and validates
  `sides`, `radius`, `angle`, and `corner_radius`.
- Neutral `RegularPolygonDrawing` passes the same values to SVG and PDF; DXF
  intentionally obtains its control vertices through PDF materialization.
- Before P9, every concrete renderer ignored nonzero `corner_radius`; raster
  alone rejected it explicitly. A legacy SVG test passed radius one while
  asserting sharp vertices, confirming the silent contract defect.
- P9 puts tangent-circle geometry in `component.py`, below all concrete
  renderers. No renderer imports another renderer for the new geometry, no
  dependency cycle is introduced, and no package dependency changes.
- ADR-0034 continues to require direct neutral raster rendering and the existing
  Pillow dependency only.

## Mathematical Proof

For a regular `n`-gon, the interior angle at each vertex is

```text
alpha = pi - 2*pi/n.
```

Let `rho` be the requested corner radius. A circle tangent to both rays of an
angle `alpha` has tangent distance from the vertex

```text
d = rho / tan(alpha/2)
```

and center distance along the interior angle bisector

```text
h = rho / sin(alpha/2).
```

P9 constructs the entry and exit points by moving distance `d` from the vertex
along the unit vectors to the previous and next vertices. It constructs the
center by moving distance `h` along their normalized sum. Right-triangle
trigonometry then gives distance `rho` from the center to both tangent points,
and each radius is perpendicular to its incident edge. Thus the arc has the
requested radius and joins both straight edges tangentially.

The polygon side length is `s = 2*R*sin(pi/n)`. Since
`alpha/2 = pi/2 - pi/n`, the largest permitted tangent distance satisfies

```text
d <= (R/2)*tan(pi/n).
```

Comparing it with half an edge gives

```text
d / (s/2) <= 1 / (2*cos(pi/n)) <= 1  for n >= 3.
```

Therefore adjacent tangent points cannot cross. Equality occurs only for the
three-sided maximum-radius boundary. The signed corner sweep is the exterior
angle `2*pi/n`, whose magnitude is less than `pi`, so every corner is the unique
minor arc selected by the control-polygon orientation.

DXF and raster sample each arc with

```text
segments = ceil(abs(sweep) / (pi/8)).
```

Apart from a tolerance that prevents floating-point integer-boundary inflation,
each sample span is therefore at most `pi/8` (22.5 degrees). Entry and exit
points are included exactly. SVG represents the same endpoint, radius, and
sweep as a native `A` command. PDF has no circular-arc operator, so it uses the
standard tangent cubic control distance

```text
k = (4/3)*rho*tan(abs(sweep)/4).
```

This preserves both endpoints and both tangent directions; PDF circularity is
the conventional cubic approximation rather than an exact-arc claim.

## Comprehensiveness Matrix

| Domain class | Required result | Evidence |
|---|---|---|
| `n = 3, 4, 5, 8, 17` | requested radius and edge tangency | parameterized geometry test |
| `rho = R/2` | no adjacent-corner overlap | maximum-boundary geometry test |
| Reversed orientation | equal negative minor sweeps | reversal geometry test |
| Radius zero | unchanged sharp SVG/PDF/raster paths | legacy and P9 sharp controls |
| Malformed radius/points/step | fail explicitly | failure-mode test |
| Floating normalized dot outside `[-1, 1]` | clamp before `acos` | deterministic upper/lower overshoot tests |
| Sampled outline | exact endpoints and bounded angular steps | sampling test |
| Tiny positive sweep | retain one arc segment | direct sampling boundary test |
| SVG | one native arc per corner | backend contract test |
| PDF | tangent cubic corner and closed path | backend contract test |
| DXF/raster | identical canonical sampled points | live backend test |
| Positive radius below one | rounded dispatch in DXF/raster | sub-unit live-path test |
| More than 256 sides | numeric last-corner detection | 300-side SVG/PDF regression |
| Raster pixels and alpha | center painted, removed vertex transparent | public pixel test |
| Baird composition | clean RGBA feeds degradation | public integration test |
| Hostile live mutation | reject before allocation | pre-allocation failure test |

## Test Applicability

Unit, condition, failure-mode, property-partition, integration, live-path,
contract, regression, pixel, mutation, and resource-bound checks apply.
Security, concurrency, and external-I/O checks do not apply because P9 adds no
file, network, process, active-content, or shared-state boundary.

## Mutation Gate

Cosmic Ray 8.4.6 generated 17,546 candidates from the five changed source
modules. The proof-critical filter selected 770 work items. Isolated WSL
workers completed all 770 without errors or timeouts: 753 were killed and 17
survived. Each survivor is equivalent in the declared regular-polygon domain:

- two shoelace-index mutants compute exactly half the regular polygon's signed
  double area, preserving finiteness, zero status, and orientation;
- one area-sign comparison is equal because zero area is rejected first;
- six endpoint-comparison mutants are equal over nonnegative lengths, bounded
  half angles, nonzero regular-polygon sweeps, and the proven non-overlap bound;
- two corner-join mutants replace `< length` with `!= length`, which is equal
  for `enumerate` indices; a separate 300-side test kills identity comparison;
- five renderer branch mutants are equal over the validated nonnegative corner
  radius domain; and
- one PDF direction mutant is equal because canonical corner sweeps are never
  zero.

The machine-readable job IDs, hashes, late-kill witnesses, and individual
proofs are in
`tests/mutation/rounded_regular_polygon_p9_evidence.json`. Raw mutation
coverage is 97.79%; effective coverage after the equivalent-mutant proofs is
100%. A post-campaign Ruff normalization changed only line wrapping in the
raster helper; the manifest records identical pre/post Python AST hashes and
the normalized source byte hash.

Because P9 extends modules covered by older text mutation certificates, the
final gate also regenerated those certificates instead of weakening their
freshness checks. The boundary-unit campaign selected 91 work items and killed
90, with one equivalent survivor. The PDF text-presentation campaign selected
304 work items and killed 301, with three equivalent survivors. A new
multiline-baseline witness killed nine arithmetic survivors exposed by the
expanded campaign. Certificate freshness now checks each recorded mutation
hunk against current source while retaining whole-file hashes for immutable
evidence inputs and source files without scoped work items.

## Verification Status

- Focused P9 conditions: 32 passed.
- Renderer/dependency regression selection: 347 passed.
- Mutation: 753 killed, 17 proven equivalent, effective coverage 100%.
- Historical mutation-certificate and freshness regression: 16 passed.
- Exact index-only full regression: 2,181 passed in three shards (902, 544,
  and 735).
- Branch coverage: 98.29% overall; changed-source coverage was 98% for
  `component.py`, 98% for `pdf_generator.py`, 99% for `dxf_generator.py`,
  100% for `raster_renderer.py`, and 91% for `svg_generator.py`.
- Ruff lint: all P9 and certificate-refresh Python files passed.
- Ruff formatting: all new files and the changed raster helper passed. The
  established whole-file exceptions in legacy component/generator modules and
  `test_svg_generator.py` remain outside this slice; the P9 hunks in those
  files were kept formatter-conformant without unrelated rewrites.
- Bytecode compilation: passed for `src/InkGen` and the new evidence helpers.
- Documentation: strict MkDocs build passed.
- Evidence manifests: all three JSON documents parsed successfully.
- Patch hygiene: the exact staged patch passed `git diff --cached --check`.
