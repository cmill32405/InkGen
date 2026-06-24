# Path Renderer Contract Proof Obligations

This note applies the InkGen Definition of Done to the PATH-P1 generic path
renderer-contract slice. It focuses on command validation, deterministic PDF
operator output, explicit failure for unsupported PDF path semantics,
renderer-neutral materialization, SVG preservation, and DXF polyline export.

## Scope

The slice covers generic path command handling in `src/InkGen/component.py`,
PDF path rendering in `src/InkGen/pdf_generator.py`, renderer-neutral
materialization in `src/InkGen/drawing_components.py`, SVG path serialization
in `src/InkGen/svg_generator.py`, and DXF path export in
`src/InkGen/dxf_generator.py`.

The public behavior under review is:

- `PathCommand.__init__()`
- `PathCommand.type`
- `PathCommand.points`
- `PathCommand.add_point()`
- `Path.add_command()`
- `Path.points`
- `PathPDF.generate_pdf()`
- `PathSVG.generate_svg()`
- `PathDrawing.__post_init__()`
- `PathDrawing.to_component(OutputFormat.SVG/PDF)`
- `DXFDocument.add_group()` for `PathDrawing`

## Architecture Impact

Affected surface:

- `src/InkGen/component.py`: neutral path command validation and point
  aggregation.
- `src/InkGen/pdf_generator.py`: concrete PDF path command conversion.
- `src/InkGen/svg_generator.py`: SVG path data serialization.
- `src/InkGen/drawing_components.py`: neutral path recipe materialization.
- `src/InkGen/dxf_generator.py`: path export as `LWPOLYLINE` entities.
- `tests/test_path_contract.py`: validation, renderer, and dependency-path
  evidence.

Incoming dependencies:

- Synthetic drawing fixtures rely on `PathCommand` accepting SVG-style commands
  while normalizing command names and coordinate precision.
- PDF fixture consumers rely on `PathPDF.generate_pdf()` emitting deterministic
  PDF path operators or failing when the command cannot be represented.
- SVG consumers rely on smooth SVG commands such as `S` and `T` remaining valid
  path data.
- Renderer-neutral drawing callers rely on `PathDrawing` accepting command
  collections that contain `PathCommand` objects and failing before concrete
  renderer construction when the command collection is malformed.
- DXF consumers rely on `PathDrawing` producing a polyline with a closure flag
  derived from a terminal `Z` command.

Outgoing dependencies:

- `PathCommand` depends on local `PRECISION` for coordinate rounding.
- `Path` depends on `PathCommand` and shared `DrawingComponent` style handling.
- `PathPDF` depends on `PathComponent`, `_quadratic_to_cubic()`, `_number()`,
  and `_drawing_pdf()`.
- `PathSVG` depends on shared SVG style serialization and command coordinate
  formatting.
- `PathDrawing` depends on `PathCommand`, validates its public command
  collection boundary, depends on `normalize_output_format()`, and
  materializes to `PathSVG` or `PathPDF`.
- `DXFDocument` depends on `PathDrawing.to_component(OutputFormat.PDF)` for
  flattened point extraction and on `_lwpolyline_entity()` for DXF group codes.

Before/after edge changes:

- Before this slice, `PathPDF` silently omitted valid SVG commands `S` and `T`.
- Before this slice, `PathPDF` silently truncated incomplete `C` and `Q`
  command point groups.
- After this slice, those unsupported or incomplete PDF render cases raise
  `ValueError` before emitting partial geometry.
- Before `PATH-DRAWING-COMMANDS-P2`, direct `PathDrawing` construction could
  store malformed command collections such as raw strings and fail later inside
  concrete renderers.
- After `PATH-DRAWING-COMMANDS-P2`, `PathDrawing` accepts only `None` or a
  non-string sequence of `PathCommand` objects and normalizes accepted
  sequences to a list.
- No new dependency edge or third-party dependency was introduced.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced. Neutral components still do not import
  concrete renderers at module load time.
- Layer check: concrete renderers and DXF output depend on neutral recipes
  according to `docs/dependency-map.md`.
- Coupling check: PDF explicitly rejects smooth SVG commands until their
  previous-control-point semantics are implemented.
- Redundancy check: the slice avoids adding a second path parser or curve
  engine.

Evidence source and freshness:

- Source-backed: `component.py`, `pdf_generator.py`, `svg_generator.py`,
  `drawing_components.py`, and `dxf_generator.py` were read before editing.
- Test-backed: focused tests in `test_path_contract.py` exercise validation,
  PDF operators, failure paths, neutral materialization, SVG preservation, and
  live DXF export.
- Design-backed: `docs/dependency-map.md` records renderer-neutral
  materialization into concrete drawing components.
- No architecture claim in this section relies only on stale memory.

ADR/rule impact:

- No new ADR is required because the slice preserves the existing closed PDF
  renderer boundary from ADR-0002. Unsupported SVG smooth commands are rejected
  rather than approximated by a new path engine.
- A future change that implements full `S`/`T` PDF semantics should add or
  update an ADR because it changes the PDF path capability boundary.

## Domain Definitions

- A path command is defined by an uppercase SVG command type from
  `PathCommand.VALID_COMMANDS` and zero or more coordinate pairs.
- `PathPDF` supports `M`, `L`, `H`, `V`, `C`, `Q`, `A`, and `Z` with the
  existing approximation rule that `A` is rendered as a line to the command end
  point.
- `PathPDF` does not support smooth commands `S` and `T`.
- `PathPDF` requires `C` points in groups of three and `Q` points in groups of
  two.
- `PathSVG` preserves the supported SVG path command strings.
- `PathDrawing.commands` is `None` or a non-string sequence containing only
  `PathCommand` objects. Direct dictionary command payloads are outside this
  constructor contract; flow-document hydration converts serialized mappings to
  `PathCommand` before constructing `PathDrawing`.
- `DXFDocument` represents neutral paths as `LWPOLYLINE` entities using the
  neutral point list and a closed flag when the last command is `Z`.

## Fix Log

- `PathPDF._command_operators()` now raises `ValueError` for unsupported
  smooth commands `S` and `T`.
- `PathPDF._command_operators()` now raises `ValueError` for incomplete `C`
  and `Q` curve point groups instead of silently truncating the command.
- `PathPDF._command_operators()` now raises `ValueError` for `A` commands
  without an endpoint instead of silently omitting the command.
- `PathDrawing.__post_init__()` now rejects malformed command collections at
  the renderer-neutral boundary before SVG/PDF materialization.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid command names | Normalize whitespace/case and preserve supported command type | PO-PATH-001 | `test_path_command_normalizes_and_rejects_invalid_inputs` | Must be killed or proven equivalent |
| Invalid command names and non-string types | Reject at command construction | PO-PATH-001 | `test_path_command_normalizes_and_rejects_invalid_inputs` | Must be killed or proven equivalent |
| Malformed coordinate arity | Reject at command construction or point append | PO-PATH-001 | `test_path_command_normalizes_and_rejects_invalid_inputs` | Must be killed or proven equivalent |
| Path point aggregation | Preserve command order and reject bad additions | PO-PATH-002 | `test_path_collects_command_points_and_rejects_bad_additions` | Must be killed or proven equivalent |
| Supported PDF commands | Emit exact PDF operators for `M/L/H/V/Q/C/A/Z` | PO-PATH-003 | `test_path_pdf_emits_supported_commands_as_exact_operators` | Must be killed or proven equivalent |
| Unsupported PDF commands | Reject `S/T` instead of losing geometry | PO-PATH-004 | `test_path_pdf_rejects_commands_it_cannot_render` | Must be killed or proven equivalent |
| Incomplete curve groups | Reject incomplete `C/Q` groups instead of partial output | PO-PATH-005 | `test_path_pdf_rejects_incomplete_curve_segments` | Must be killed or proven equivalent |
| SVG smooth commands | Preserve `S/T` as valid SVG path data | PO-PATH-006 | `test_path_svg_preserves_smooth_commands_that_pdf_rejects` | Must be killed or proven equivalent |
| Neutral path materialization | Materialize to `PathSVG` or `PathPDF` with matching commands | PO-PATH-007 | `test_path_drawing_materializes_svg_and_pdf_components` | Must be killed or proven equivalent |
| DXF path output | Emit `LWPOLYLINE` vertices and closure flag through live document path | PO-PATH-008 | `test_dxf_path_drawing_reuses_pdf_points_and_closure_flag` | Must be killed or proven equivalent |
| Neutral path command collection boundary | Accept `None` or non-string sequences of `PathCommand`; reject raw strings, bytes, non-sequences, and non-command members before renderer materialization | PO-PATH-009 | `test_path_drawing_accepts_command_sequences_before_materialization`; `test_path_drawing_rejects_malformed_command_collections` | 7 validation mutants killed; 0 validation survivors |
| Full SVG arc geometry, smooth-control reflection, fill-rule semantics, and Bézier-to-DXF curve fidelity | Excluded from proven domain | Explicit exclusions in PO-PATH-003 through PO-PATH-008 | existing tests only | Out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Command validation and PDF operator generation are deterministic. | PATH-P1 tests named above |
| Behavioral/condition | yes | PATH-P1 defines expected path behavior across command, SVG, PDF, and DXF paths. PATH-DRAWING-COMMANDS-P2 defines the neutral path command collection boundary. | Tests are marked `@pytest.mark.condition("PATH-P1")` or `@pytest.mark.condition("PATH-DRAWING-COMMANDS-P2")`. |
| Failure-mode | yes | Unsupported smooth commands, incomplete curve groups, and malformed direct `PathDrawing` command collections must fail loudly. | `test_path_pdf_rejects_commands_it_cannot_render`; `test_path_pdf_rejects_incomplete_curve_segments`; `test_path_drawing_rejects_malformed_command_collections` |
| Integration/live-path | yes | DXF must exercise the public neutral group path, not just `_lwpolyline_entity()`. | `test_dxf_path_drawing_reuses_pdf_points_and_closure_flag` calls `DXFDocument.add_group()`. |
| Contract/API compatibility | yes | SVG keeps smooth commands while PDF rejects commands it cannot faithfully render. | `test_path_svg_preserves_smooth_commands_that_pdf_rejects`; `test_path_pdf_rejects_commands_it_cannot_render` |
| Property/fuzz | limited | This slice proves representative command classes rather than arbitrary SVG path grammar. | Exact operator and failure tests over declared command partitions. |
| Mutation | yes | Validation, failure branches, operator output, materialization, and DXF closure are proof-critical. | Mutation run result recorded below. |
| Security/adversarial | no | The slice adds no file path, network, subprocess, auth, secrets, SQL, template, deserialization, font, image, or active-content surface. | Not applicable. |
| Performance/resource | no | The slice adds no unbounded loop or cache. | Not applicable. |
| Concurrency/race | no | The slice adds no shared mutable global state, background workers, sessions, locks, queues, or temp-file coordination. | Not applicable. |
| Observability/logging | no | The slice adds no state-changing service, background work, external call, or recovery path. | Not applicable. |
| Golden artifact/visual | yes | PDF and DXF generated geometry must be stable enough for synthetic fixtures. | PDF operator test and DXF polyline test. |
| Regression | yes | This slice closes silent path command loss in PDF output. | Failure-mode tests named above. |

## Invariants, Preconditions, And Postconditions

Invariants:

- Path command type is uppercase and belongs to `PathCommand.VALID_COMMANDS`.
- Path command points contain exactly two numeric coordinates after public
  construction or append.
- `Path.points` preserves command order.
- `PathPDF` never silently drops `S` or `T`.
- `PathPDF` never silently truncates incomplete `C` or `Q` point groups.
- `PathSVG` preserves `S` and `T` command data.
- `PathDrawing.commands` is `None` or a list of `PathCommand` objects after
  construction.
- DXF path export sets group code `70` to `1` only when the last command is
  `Z`.

Preconditions:

- Callers provide path commands through `PathCommand` or dictionaries accepted
  by `Path.add_command()`.
- Direct `PathDrawing` callers provide `PathCommand` sequences; serialized
  dictionary payloads must be converted before construction.
- PDF callers use only the declared supported PDF path command subset.
- Callers do not monkey-patch renderer classes or mutate inherited private
  fields.

Postconditions:

- `PathPDF.generate_pdf()` emits deterministic operators for supported commands.
- `PathPDF.generate_pdf()` raises `ValueError` for unsupported smooth commands
  and incomplete curve groups.
- `PathSVG.generate_svg()` serializes the path command list as SVG path data.
- `PathDrawing.__post_init__()` rejects malformed command collections before
  concrete renderer materialization.
- `PathDrawing.to_component(OutputFormat.SVG)` returns `PathSVG`.
- `PathDrawing.to_component(OutputFormat.PDF)` returns `PathPDF`.
- `DXFDocument.add_group()` emits one `LWPOLYLINE` entity for each neutral
  `PathDrawing`.

## Mutation Testing Gate

Proof-critical mutation targets:

- Weakening command type or point validation should fail invalid-input tests.
- Changing command point aggregation should fail path point tests.
- Changing PDF coordinate operators, quadratic conversion output, close-path
  output, or paint output should fail PDF operator tests.
- Removing unsupported-command or incomplete-curve validation should fail
  failure-mode tests.
- Weakening `PathDrawing` command collection validation should fail direct
  constructor failure-mode tests.
- Redirecting `PathDrawing.to_component()` should fail materialization tests.
- Changing DXF closure flags or vertices should fail DXF live-path tests.

Current result:

- Tool and version: Cosmic Ray 8.4.6 in WSL.
- Mutated source paths: `src/InkGen/component.py`,
  `src/InkGen/drawing_components.py`, `src/InkGen/pdf_generator.py`,
  `src/InkGen/svg_generator.py`, and `src/InkGen/dxf_generator.py`.
- Reproducible setup:
  `cosmic-ray baseline tests/mutation/path_cosmic_ray.toml`,
  `cosmic-ray init tests/mutation/path_cosmic_ray.toml
  /tmp/inkgen_path_mutation.sqlite`, then
  `python3 tests/mutation/filter_path_work_items.py
  /tmp/inkgen_path_mutation.sqlite --clear-results`.
- Test selection:
  `python -m pytest -x tests/test_path_contract.py`.
- Proof-critical work items after filtering: 332.
- Mutants killed: 322.
- Mutants survived: 10.
- Mutants excluded/equivalent: 10 equivalent mutants:

  - `src/InkGen/drawing_components.py:182`: `target is
    OutputFormat.SVG` mutated to `target == OutputFormat.SVG` and
    `target >= OutputFormat.SVG`. Within the declared public domain,
    `normalize_output_format()` returns `OutputFormat.SVG` or
    `OutputFormat.PDF`. For those two string-enum values, identity/equality
    select SVG, and lexical `>= "svg"` is true for SVG and false for PDF.
  - `src/InkGen/dxf_generator.py:108`: terminal path-command comparison
    mutated from `== "Z"` to `>= "Z"`. `PathCommand` normalizes all valid
    command types to one of `A/C/H/L/M/Q/S/T/V/Z`; `Z` is lexically last, so
    the mutated predicate is equivalent over normalized valid command types.
  - `src/InkGen/pdf_generator.py:487`: `command_type == "A"` in the empty-arc
    validation mutated to `command_type <= "A"`. `A` is lexically first in the
    normalized valid command alphabet, so the predicate is equivalent for the
    declared command domain.
  - `src/InkGen/pdf_generator.py:521`: `command_type == "A"` in the arc
    fallback branch mutated to `command_type <= "A"`. All other valid command
    types are lexically greater than `A`, so the predicate is equivalent after
    earlier branches have handled their commands.
  - `src/InkGen/pdf_generator.py:524`: `command_type == "Z"` in the close-path
    branch mutated to `<= "Z"`, `>= "Z"`, and `is not "Z"`. In the declared
    domain, all non-`Z` valid commands either match an earlier branch or are
    rejected before branch dispatch; `Z` is the only remaining command that
    reaches this branch.
  - `src/InkGen/svg_generator.py:643`: `command.type == "V"` mutated to
    `command.type >= "V"`. Within the SVG formatting domain, point-bearing
    valid commands greater than or equal to `V` are `V`; `Z` is treated as a
    no-point close command.
  - `src/InkGen/svg_generator.py:645`: `command.type == "A"` mutated to
    `command.type <= "A"`. `A` is lexically first in the normalized valid
    command alphabet, so the predicate is equivalent for valid command types.

During mutation, real test gaps were found and closed:

- PDF path assertions did not include an `L` command; they now assert complete
  `L` operator lines.
- `M` used only one point, so `points[-1]` index mutations were indistinct;
  the test now uses multiple move points.
- `V` was tested after a state where x and y were equal; the test now uses
  distinct current x/y values.
- PDF arc fallback used two points, making `points[1]` and `points[-1]`
  equivalent; it now uses three points plus a separate one-endpoint case.
- SVG arc formatting now covers default, partial, and empty flag dictionaries.

The companion PATH-FINITE-P2 slice closes the former non-finite coordinate
input exclusion for `PathCommand` and dictionary-sourced `Path.add_command()`
inputs.

Gate result: passed for the declared domain. The mutation report has no
surviving non-equivalent proof-critical mutants.

Additional `PATH-DRAWING-COMMANDS-P2` mutation result:

- Tool and version: Cosmic Ray 8.4.6 in WSL.
- Mutated source path: `src/InkGen/drawing_components.py`.
- Config: `tests/mutation/path_cosmic_ray.toml`.
- Filter: `tests/mutation/filter_path_drawing_commands_work_items.py`.
- Test selection: `python -m pytest -x tests/test_path_contract.py`.
- Proof-critical work items after filtering: 15.
- Mutants killed: 13.
- Mutants survived: 2 equivalent mutants:

  - `src/InkGen/drawing_components.py:197`: `target is OutputFormat.SVG`
    mutated to `target == OutputFormat.SVG`.
  - `src/InkGen/drawing_components.py:197`: `target is OutputFormat.SVG`
    mutated to `target >= OutputFormat.SVG`.

  Within the declared `to_component()` domain, `normalize_output_format()`
  returns either `OutputFormat.SVG` or `OutputFormat.PDF`. For those two
  string-enum values, equality selects the same SVG branch as identity, and
  lexical `>= "svg"` is true for SVG and false for PDF. These are equivalent
  to the original branch for supported output formats.

- New validation guard work items in `PathDrawing.__post_init__()`: 7.
- Validation guard result: 7 killed, 0 survived.
- Gate result: passed for the declared `PATH-DRAWING-COMMANDS-P2` domain. The
  mutation report has no surviving non-equivalent proof-critical mutants.

## PO-PATH-001: Command Validation

### Claim

`PathCommand` accepts declared SVG command names, normalizes them to uppercase,
and rejects invalid command names, non-string command types, and malformed point
arity.

### Domain

All public `PathCommand` constructor calls and `add_point()` calls with ordinary
sequence-like point values.

### Proof Method

`PathCommand.type` checks that command type is a string, strips whitespace,
uppercases it, and requires membership in `VALID_COMMANDS`. `_coerce_point()`
requires exactly two values and converts both to `float`. `points` and
`add_point()` both call `_coerce_point()`.

### Conclusion

Proven for the stated domain.

## PO-PATH-002: Path Aggregates Command Points

### Claim

`Path` preserves command order, accepts `PathCommand` or command dictionaries,
and exposes the concatenated command point list.

### Domain

All public `Path` instances constructed or mutated through `add_command()`.

### Proof Method

`Path.add_command()` appends existing `PathCommand` instances or constructs a
new `PathCommand` from dictionary data. It rejects other inputs with
`TypeError`. `Path.points` iterates through `self.commands` in order and extends
a result list with each command's points.

### Conclusion

Proven for the stated domain.

## PO-PATH-003: Supported PDF Commands Emit Deterministic Operators

### Claim

`PathPDF.generate_pdf()` emits exact PDF path operators for supported commands
`M`, `L`, `H`, `V`, `Q`, `C`, `A`, and `Z`.

### Domain

All `PathPDF` instances whose commands use the supported command subset and
whose `C` and `Q` point counts are complete groups.

### Proof Method

Static path proof over `PathPDF._command_operators()`:

1. `M` emits a PDF `m` operator at the last move point.
2. `L` emits one `l` operator for each point.
3. `H` emits one `l` operator using the new x-coordinate and current y.
4. `V` emits one `l` operator using current x and the new y-coordinate.
5. `Q` converts each control/end pair to one cubic `c` operator through
   `_quadratic_to_cubic()`.
6. `C` emits one cubic `c` operator for each control/control/end triple.
7. `A` emits one line to the command end point under the current approximation
   contract.
8. `Z` emits `h`.
9. `generate_pdf()` wraps those operators with `_drawing_pdf()`.

### Conclusion

Proven for the stated domain.

## PO-PATH-004: Unsupported PDF Smooth Commands Fail

### Claim

`PathPDF.generate_pdf()` raises `ValueError` for `S` and `T` commands instead
of silently omitting their geometry.

### Domain

All `PathPDF` instances containing `S` or `T` commands.

### Proof Method

At the start of each command loop, `_command_operators()` checks
`command_type in {"S", "T"}` and raises `ValueError`. No path operator is
returned for unsupported smooth commands.

### Conclusion

Proven for the stated domain.

## PO-PATH-005: Incomplete Curve Groups Fail

### Claim

`PathPDF.generate_pdf()` raises `ValueError` for incomplete `C` and `Q` point
groups, and for `A` commands without an endpoint, instead of emitting partial
or missing geometry.

### Domain

All `PathPDF` instances containing `C` commands whose point count is not a
multiple of three, `Q` commands whose point count is not a multiple of two, or
`A` commands without an endpoint.

### Proof Method

At the start of each command loop, `_command_operators()` checks `C` point
counts modulo three, `Q` point counts modulo two, and whether `A` has an
endpoint. Any incomplete point group or missing arc endpoint raises
`ValueError` before operator generation.

### Conclusion

Proven for the stated domain.

## PO-PATH-006: SVG Preserves Smooth Commands

### Claim

`PathSVG.generate_svg()` preserves valid smooth commands `S` and `T` as SVG
path data.

### Domain

All `PathSVG` instances containing `S` or `T` commands with ordinary coordinate
pairs.

### Proof Method

`PathSVG._format_command()` uses the generic point formatting path for commands
other than `H`, `V`, and `A`. Therefore `S` and `T` commands are emitted with
their command type and coordinate pairs.

### Conclusion

Proven for the stated domain.

## PO-PATH-007: Neutral Path Materializes To SVG And PDF

### Claim

`PathDrawing.to_component()` materializes neutral path recipes into SVG and PDF
path components without changing the command list.

### Domain

All `PathDrawing` instances with supported output formats `SVG` and `PDF`.

### Proof Method

`PathDrawing.to_component()` normalizes the requested output format. For SVG it
returns `PathSVG(self.style, commands=self.commands)`. For PDF it returns
`PathPDF(self.style, commands=self.commands)`. Therefore the command list is
preserved.

### Conclusion

Proven for the stated domain.

## PO-PATH-008: DXF Uses Path Points And Closure Flag

### Claim

DXF export for a neutral `PathDrawing` emits an `LWPOLYLINE` using the neutral
path points and sets the closure flag when the last command is `Z`.

### Domain

All `PathDrawing` instances exported through `DXFDocument.add_group()` with
ordinary point commands.

### Proof Method

Static path proof over `dxf_generator.py`:

1. `DXFDocument.add_group()` iterates over `group.components`.
2. `_component_to_entities()` matches `PathDrawing`.
3. It materializes a `PathPDF` using `component.to_component(OutputFormat.PDF)`.
4. It computes `closed` from the last neutral command's type.
5. It returns `_lwpolyline_entity(concrete.points, context, closed=closed)`.
6. Therefore DXF output uses the path point list and the terminal `Z` closure
   state.

### Conclusion

Proven for the stated domain.

## PO-PATH-009: PathDrawing Rejects Malformed Command Collections

### Claim

`PathDrawing` accepts `None` or non-string sequences containing only
`PathCommand` objects, normalizes accepted sequences to a list, and rejects
malformed command collections before SVG/PDF renderer materialization.

### Domain

All public `PathDrawing` constructor calls with `commands` supplied as `None`,
a non-string sequence of `PathCommand` objects, a raw string or bytes value, a
non-sequence object, or a sequence containing a non-`PathCommand` member.

### Proof Method

`PathDrawing.__post_init__()` handles all constructor cases by disjoint guards:

1. `None` returns immediately and preserves the empty-command sentinel.
2. Raw strings and bytes are rejected before sequence iteration.
3. Non-sequence objects are rejected before iteration.
4. Accepted sequences are copied to a local list.
5. The copied list is accepted only when every member is a `PathCommand`;
   otherwise `TypeError` is raised.
6. The frozen dataclass state is updated with the normalized list only after
   all validation passes.

Therefore every accepted non-`None` post-construction `commands` value is a
list whose members are all `PathCommand` objects, and malformed public inputs
cannot reach `PathSVG` or `PathPDF` through `PathDrawing.to_component()`.

### Conclusion

Proven for the stated domain.

## Current Slice Decision

The slice treats full SVG path semantics as larger than the current PDF/DXF
scope. It preserves SVG expressiveness while making PDF output fail loudly for
smooth commands and incomplete curve groups that cannot be faithfully rendered
by the current closed PDF renderer.
