# Path Renderer Contract Proof Obligations

This note applies the InkGen Definition of Done to the PATH-P1 generic path
renderer-contract slice and later path-boundary hardening slices. It focuses on
command validation, deterministic PDF operator output, smooth SVG path command
conversion, renderer-neutral materialization, SVG preservation, neutral/SVG
command-payload hydration, and DXF polyline export.

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
- `Path.create_from_dict()`
- `Path.points`
- `PathPDF.generate_pdf()`
- `PathSVG.generate_svg()`
- `PathSVG.create_from_dict()`
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
  PDF path operators for the declared SVG-style command subset, including
  smooth `S` and `T` commands.
- SVG consumers rely on smooth SVG commands such as `S` and `T` remaining valid
  path data.
- SVG serialized-payload consumers rely on `PathSVG.create_from_dict()`
  preserving valid command flags and failing before incidental Python
  subscription/attribute errors when command payloads are malformed.
- Renderer-neutral drawing callers rely on `PathDrawing` accepting command
  collections that contain `PathCommand` objects and failing before concrete
  renderer construction when the command collection is malformed.
- Neutral `Path` callers rely on dictionary-sourced commands and serialized
  command payloads being converted to `PathCommand` objects or rejected before
  incidental subscription/attribute errors.
- DXF consumers rely on `PathDrawing` producing a polyline with a closure flag
  derived from a terminal `Z` command.

Outgoing dependencies:

- `PathCommand` depends on local `PRECISION` for coordinate rounding.
- `Path` depends on `PathCommand` and shared `DrawingComponent` style handling.
- `PathPDF` depends on `PathComponent`, `_quadratic_to_cubic()`,
  `_reflect_point()`, `_number()`, and `_drawing_pdf()`.
- `PathSVG` depends on shared SVG style serialization, command coordinate
  formatting, and `PathCommand` for hydrated command validation.
- `PathDrawing` depends on `PathCommand`, validates its public command
  collection boundary, depends on `normalize_output_format()`, and
  materializes to `PathSVG` or `PathPDF`.
- `DXFDocument` depends on `PathDrawing.to_component(OutputFormat.PDF)` for
  flattened point extraction and on `_lwpolyline_entity()` for DXF group codes.

Before/after edge changes:

- Before this slice, `PathPDF` silently omitted valid SVG commands `S` and `T`.
- Before `PATH-SMOOTH-PDF-P3`, `PathPDF` rejected smooth commands `S` and `T`
  after the silent-omission regression was closed.
- Before this slice, `PathPDF` silently truncated incomplete `C` and `Q`
  command point groups.
- After this slice, incomplete PDF render cases raise `ValueError` before
  emitting partial geometry.
- After `PATH-SMOOTH-PDF-P3`, `PathPDF` converts `S` and `T` to deterministic
  cubic PDF operators using SVG reflected-control semantics. Malformed smooth
  command point groups still fail before PDF bytes are emitted.
- Before `PATH-DRAWING-COMMANDS-P2`, direct `PathDrawing` construction could
  store malformed command collections such as raw strings and fail later inside
  concrete renderers.
- After `PATH-DRAWING-COMMANDS-P2`, `PathDrawing` accepts only `None` or a
  non-string sequence of `PathCommand` objects and normalizes accepted
  sequences to a list.
- Before `PATH-DRAWING-LIVE-COMMANDS-P2`, callers could mutate the public
  `PathDrawing.commands` list after construction and bypass the constructor
  command-type guard before SVG/PDF materialization.
- After `PATH-DRAWING-LIVE-COMMANDS-P2`, `PathDrawing.to_component()` reuses
  the same command-list validator used by construction, so mutated public
  command lists fail at the neutral path boundary.
- Before `SVG-PATH-COMMAND-PAYLOAD-P2`, `PathSVG.create_from_dict()` accepted
  raw indexing/subscription paths for malformed command containers and command
  envelopes.
- After `SVG-PATH-COMMAND-PAYLOAD-P2`, `PathSVG.create_from_dict()` requires a
  mapping root, a mapping `PathSVG` payload, a sequence `commands` field when
  present, mapping command entries, and string command types before constructing
  `PathCommand`.
- Before `PATH-COMMAND-PAYLOAD-P2`, neutral `Path.create_from_dict()` and
  dictionary-sourced `Path.add_command()` used raw command indexing and `get()`
  calls.
- After `PATH-COMMAND-PAYLOAD-P2`, neutral `Path` serialized commands require
  sequence containers, mapping command entries, and string command types before
  constructing `PathCommand`.
- No new dependency edge or third-party dependency was introduced.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced. Neutral components still do not import
  concrete renderers at module load time.
- Layer check: concrete renderers and DXF output depend on neutral recipes
  according to `docs/dependency-map.md`.
- Coupling check: PDF smooth command support is implemented locally in
  `PathPDF._command_operators()` and does not add a path parser or curve engine.
- Redundancy check: the slice reuses the existing quadratic-to-cubic conversion
  helper and adds only a local reflection helper.

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

- ADR-0012 records the PDF smooth path command decision because this slice
  changes the PDF path capability boundary from rejection to deterministic
  reflected-control rendering.

## Domain Definitions

- A path command is defined by an uppercase SVG command type from
  `PathCommand.VALID_COMMANDS` and zero or more coordinate pairs.
- Neutral `Path.create_from_dict()` accepts wrapped `Path` payloads, optional
  command sequences, and serialized command mappings with string `type` and
  optional `points`.
- `PathPDF` supports `M`, `L`, `H`, `V`, `C`, `S`, `Q`, `T`, `A`, and `Z` with
  the existing approximation rule that `A` is rendered as a line to the command
  end point.
- `PathPDF` requires `C` points in groups of three, `S` points in groups of two,
  `Q` points in groups of two, and `T` commands to contain at least one
  endpoint.
- `S` reflects the previous `C` or `S` cubic control point around the current
  point; otherwise its first control is the current point.
- `T` reflects the previous `Q` or `T` quadratic control point around the
  current point; otherwise its quadratic control is the current point.
- `PathSVG` preserves the supported SVG path command strings.
- `PathSVG.create_from_dict()` accepts wrapped `PathSVG` payloads, optional
  command sequences, and serialized command mappings with string `type`,
  optional `points`, and optional `flags`.
- `PathDrawing.commands` is `None` or a non-string sequence containing only
  `PathCommand` objects. Direct dictionary command payloads are outside this
  constructor contract; flow-document hydration converts serialized mappings to
  `PathCommand` before constructing `PathDrawing`.
- If callers mutate the public `PathDrawing.commands` list after construction,
  materialization revalidates the current list before SVG/PDF renderer
  construction.
- `DXFDocument` represents neutral paths as `LWPOLYLINE` entities using the
  neutral point list and a closed flag when the last command is `Z`.

## Fix Log

- `PathPDF._command_operators()` now emits deterministic cubic operators for
  smooth commands `S` and `T`.
- `PathPDF._command_operators()` now raises `ValueError` for malformed smooth
  command point groups.
- `PathPDF._command_operators()` now raises `ValueError` for incomplete `C`
  and `Q` curve point groups instead of silently truncating the command.
- `PathPDF._command_operators()` now raises `ValueError` for `A` commands
  without an endpoint instead of silently omitting the command.
- `PathDrawing.__post_init__()` now rejects malformed command collections at
  the renderer-neutral boundary before SVG/PDF materialization.
- `PathDrawing.to_component()` now revalidates the live public `commands` list
  before constructing `PathSVG` or `PathPDF`.
- `PathSVG.create_from_dict()` now rejects malformed roots, malformed command
  collections, non-mapping command entries, missing command types, and
  non-string command types before incidental hydration errors.
- `Path.create_from_dict()` and dictionary-sourced `Path.add_command()` now
  reject malformed command collections, non-mapping command entries, missing
  command types, and non-string command types before incidental hydration
  errors.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid command names | Normalize whitespace/case and preserve supported command type | PO-PATH-001 | `test_path_command_normalizes_and_rejects_invalid_inputs` | Must be killed or proven equivalent |
| Invalid command names and non-string types | Reject at command construction | PO-PATH-001 | `test_path_command_normalizes_and_rejects_invalid_inputs` | Must be killed or proven equivalent |
| Malformed coordinate arity | Reject at command construction or point append | PO-PATH-001 | `test_path_command_normalizes_and_rejects_invalid_inputs` | Must be killed or proven equivalent |
| Path point aggregation | Preserve command order and reject bad additions | PO-PATH-002 | `test_path_collects_command_points_and_rejects_bad_additions` | Must be killed or proven equivalent |
| Supported PDF commands | Emit exact PDF operators for `M/L/H/V/Q/C/S/T/A/Z` | PO-PATH-003 | `test_path_pdf_emits_supported_commands_as_exact_operators` | Must be killed or proven equivalent |
| Smooth PDF commands | Reflect previous cubic/quadratic controls for `S/T` | PO-PATH-013 | `test_path_pdf_reflects_smooth_cubic_and_quadratic_controls` | mutation target |
| Incomplete curve groups | Reject incomplete `C/S/Q/T` groups instead of partial output | PO-PATH-005 and PO-PATH-014 | `test_path_pdf_rejects_incomplete_curve_segments` | Must be killed or proven equivalent |
| SVG smooth commands | Preserve `S/T` as valid SVG path data | PO-PATH-006 | `test_path_svg_preserves_smooth_commands` | Must be killed or proven equivalent |
| Neutral path materialization | Materialize to `PathSVG` or `PathPDF` with matching commands | PO-PATH-007 | `test_path_drawing_materializes_svg_and_pdf_components` | Must be killed or proven equivalent |
| DXF path output | Emit `LWPOLYLINE` vertices and closure flag through live document path | PO-PATH-008 | `test_dxf_path_drawing_reuses_pdf_points_and_closure_flag` | Must be killed or proven equivalent |
| Neutral path command collection boundary | Accept `None` or non-string sequences of `PathCommand`; reject raw strings, bytes, non-sequences, and non-command members before renderer materialization | PO-PATH-009 | `test_path_drawing_accepts_command_sequences_before_materialization`; `test_path_drawing_rejects_malformed_command_collections` | 7 validation mutants killed; 0 validation survivors |
| Live mutated `PathDrawing.commands` list | Reject non-command values before SVG/PDF materialization | PO-PATH-012 | `test_path_drawing_revalidates_mutated_commands_before_materialization`; `test_path_group_materialization_revalidates_mutated_path_commands` | mutation target |
| SVG path command payload boundary | Preserve valid serialized command payloads and flags; reject malformed roots, command collections, command entries, missing command types, and non-string command types | PO-PATH-010 | `test_path_svg_factory_preserves_valid_command_payloads_and_flags`; `test_path_svg_factory_rejects_malformed_payload_roots`; `test_path_svg_factory_rejects_malformed_command_payloads` | 14 validation mutants killed; 0 survivors |
| Neutral path command payload boundary | Preserve valid dictionary-sourced commands; reject malformed serialized command collections, command entries, missing command types, and non-string command types | PO-PATH-011 | `test_path_preserves_valid_command_dictionary_payloads`; `test_path_factory_rejects_malformed_command_payloads`; `test_path_add_command_rejects_malformed_command_dictionaries` | 7 validation mutants killed; 0 survivors |
| Full SVG arc geometry, fill-rule semantics, and Bézier-to-DXF curve fidelity | Excluded from proven domain | Explicit exclusions in PO-PATH-003 through PO-PATH-008 | existing tests only | Out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Command validation and PDF operator generation are deterministic. | PATH-P1 tests named above |
| Behavioral/condition | yes | PATH-P1 defines expected path behavior across command, SVG, PDF, and DXF paths. PATH-DRAWING-COMMANDS-P2 defines the neutral path command collection boundary. PATH-DRAWING-LIVE-COMMANDS-P2 defines the live mutated command-list boundary. SVG-PATH-COMMAND-PAYLOAD-P2 defines the concrete SVG command hydration boundary. PATH-COMMAND-PAYLOAD-P2 defines the neutral `Path` command dictionary/hydration boundary. | Tests are marked `@pytest.mark.condition("PATH-P1")`, `@pytest.mark.condition("PATH-DRAWING-COMMANDS-P2")`, `@pytest.mark.condition("PATH-DRAWING-LIVE-COMMANDS-P2")`, `@pytest.mark.condition("SVG-PATH-COMMAND-PAYLOAD-P2")`, or `@pytest.mark.condition("PATH-COMMAND-PAYLOAD-P2")`. |
| Failure-mode | yes | Incomplete curve groups, malformed direct `PathDrawing` command collections, mutated live `PathDrawing.commands`, malformed `PathSVG` command payloads, and malformed neutral `Path` command payloads must fail loudly. | `test_path_pdf_rejects_incomplete_curve_segments`; `test_path_drawing_rejects_malformed_command_collections`; `test_path_drawing_revalidates_mutated_commands_before_materialization`; `test_path_svg_factory_rejects_malformed_payload_roots`; `test_path_svg_factory_rejects_malformed_command_payloads`; `test_path_factory_rejects_malformed_command_payloads`; `test_path_add_command_rejects_malformed_command_dictionaries` |
| Integration/live-path | yes | DXF must exercise the public neutral group path, not just `_lwpolyline_entity()`. Mutated neutral path commands must also fail through `DrawingComponentGroup.to_group()`, not only direct helper calls. | `test_dxf_path_drawing_reuses_pdf_points_and_closure_flag` calls `DXFDocument.add_group()`; `test_path_group_materialization_revalidates_mutated_path_commands` calls `DrawingComponentGroup.to_group()`. |
| Contract/API compatibility | yes | SVG preserves smooth commands and PDF renders equivalent smooth-command geometry in cubic form. | `test_path_svg_preserves_smooth_commands`; `test_path_pdf_reflects_smooth_cubic_and_quadratic_controls` |
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
- `Path.create_from_dict()` and dictionary-sourced `Path.add_command()` accept
  only mapping command payloads with string command types.
- `PathPDF` never silently drops `S` or `T`; it emits reflected cubic operators.
- `PathPDF` never silently truncates incomplete `C`, `S`, `Q`, or `T` point
  groups.
- `PathSVG` preserves `S` and `T` command data.
- `PathSVG.create_from_dict()` accepts only mapping roots and mapping command
  payloads with string command types.
- `PathDrawing.commands` is `None` or a list of `PathCommand` objects after
  construction.
- `PathDrawing.to_component()` revalidates the current public `commands` value
  before constructing a concrete renderer component.
- DXF path export sets group code `70` to `1` only when the last command is
  `Z`.

Preconditions:

- Callers provide path commands through `PathCommand` or dictionaries accepted
  by `Path.add_command()`.
- Serialized neutral `Path` callers provide a `Path` mapping payload; command
  entries are mappings whose `type` values are real strings.
- Direct `PathDrawing` callers provide `PathCommand` sequences; serialized
  dictionary payloads must be converted before construction.
- Serialized `PathSVG` callers provide a `PathSVG` mapping payload; command
  entries are mappings whose `type` values are real strings.
- PDF callers use the declared supported PDF path command subset.
- Callers do not monkey-patch renderer classes or mutate inherited private
  fields.

Postconditions:

- `PathPDF.generate_pdf()` emits deterministic operators for supported commands,
  including reflected smooth `S` and `T` commands.
- `PathPDF.generate_pdf()` raises `ValueError` for incomplete curve groups.
- `PathSVG.generate_svg()` serializes the path command list as SVG path data.
- `PathSVG.create_from_dict()` hydrates valid serialized commands and flags
  into `PathCommand` objects.
- `PathSVG.create_from_dict()` raises `TypeError` or `ValueError` for malformed
  command payload boundaries before incidental subscription errors.
- `Path.create_from_dict()` and dictionary-sourced `Path.add_command()` hydrate
  valid command mappings into `PathCommand` objects.
- `Path.create_from_dict()` and dictionary-sourced `Path.add_command()` raise
  `TypeError` or `ValueError` for malformed command payload boundaries before
  incidental subscription errors.
- `PathDrawing.__post_init__()` rejects malformed command collections before
  concrete renderer materialization.
- `PathDrawing.to_component()` raises `TypeError` for mutated public command
  lists containing non-`PathCommand` objects before concrete renderer
  materialization.
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
- Removing incomplete-curve validation should fail failure-mode tests.
- Changing smooth-control reflection should fail smooth PDF operator tests.
- Weakening `PathDrawing` command collection validation should fail direct
  constructor failure-mode tests.
- Weakening live `PathDrawing.commands` revalidation should fail direct
  materialization and group materialization tests.
- Weakening `PathSVG.create_from_dict()` root, command collection, command
  entry, command type, or flag-preservation validation should fail SVG payload
  hydration tests.
- Weakening neutral `Path.create_from_dict()` or dictionary-sourced
  `Path.add_command()` command collection, command entry, command type, or
  valid dictionary hydration should fail neutral path payload tests.
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

`SVG-PATH-COMMAND-PAYLOAD-P2` extension result:

- Tool and version: Cosmic Ray 8.4.6 in WSL.
- Mutated source path: `src/InkGen/svg_generator.py`.
- Reproducible setup:
  `cosmic-ray baseline
  tests/mutation/svg_path_command_payload_cosmic_ray.toml`,
  `cosmic-ray init tests/mutation/svg_path_command_payload_cosmic_ray.toml
  svg_path_command_payload_codex_20260625.sqlite`, then
  `python tests/mutation/filter_svg_path_command_payload_work_items.py
  svg_path_command_payload_codex_20260625.sqlite --clear-results`.
- Test selection:
  `python -m pytest -x tests/test_path_contract.py -k
  'path_svg_factory_preserves_valid_command_payloads_and_flags or
  path_svg_factory_rejects_malformed_payload_roots or
  path_svg_factory_rejects_malformed_command_payloads'`.
- Proof-critical work items after filtering: 14.
- Mutants killed: 14.
- Mutants survived: 0.

`PATH-COMMAND-PAYLOAD-P2` extension result:

- Tool and version: Cosmic Ray 8.4.6 in WSL.
- Mutated source path: `src/InkGen/component.py`.
- Reproducible setup:
  `cosmic-ray baseline tests/mutation/path_command_payload_cosmic_ray.toml`,
  `cosmic-ray init tests/mutation/path_command_payload_cosmic_ray.toml
  path_command_payload_codex_20260625.sqlite`, then
  `python tests/mutation/filter_path_command_payload_work_items.py
  path_command_payload_codex_20260625.sqlite --clear-results`.
- Test selection:
  `python -m pytest -x tests/test_path_contract.py -k
  'path_preserves_valid_command_dictionary_payloads or
  path_factory_rejects_malformed_command_payloads or
  path_add_command_rejects_malformed_command_dictionaries'`.
- Proof-critical work items after filtering: 7.
- Mutants killed: 7.
- Mutants survived: 0.

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

Additional `PATH-DRAWING-LIVE-COMMANDS-P2` mutation result:

- Tool and version: Cosmic Ray 8.4.6 in WSL.
- Mutated source path: `src/InkGen/drawing_components.py`.
- Config: `tests/mutation/path_drawing_live_commands_cosmic_ray.toml`.
- Filter: `tests/mutation/filter_path_drawing_live_commands_work_items.py`.
- Test selection: `python -m pytest -x tests/test_path_contract.py` through
  the mutation venv interpreter.
- Proof-critical work items after filtering: 7.
- Mutants killed: 7.
- Mutants survived: 0.
- The first run with the broader legacy path config produced only
  `INCOMPETENT` outcomes because WSL no longer exposed a `python` executable on
  PATH. The slice-specific config uses the known mutation venv interpreter.
- Gate result: passed for the declared `PATH-DRAWING-LIVE-COMMANDS-P2`
  runtime-validation domain.

Additional `PATH-SMOOTH-PDF-P3` mutation result:

- Tool and version: Cosmic Ray 8.4.6 in WSL.
- Mutated source path: `src/InkGen/pdf_generator.py`.
- Config: `tests/mutation/path_smooth_pdf_cosmic_ray.toml`.
- Filter: `tests/mutation/filter_path_smooth_pdf_work_items.py`.
- Test selection:
  `python -m pytest -x tests/test_path_contract.py tests/test_pdf_generator.py`
  through the mutation venv interpreter.
- Raw work items: 4473.
- Proof-critical work items after filtering: 110.
- Mutants killed: 110.
- Mutants survived: 0.
- Gate result: passed for the declared `PATH-SMOOTH-PDF-P3` smooth-command
  rendering and malformed-smooth-command validation domain.

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
`M`, `L`, `H`, `V`, `Q`, `T`, `C`, `S`, `A`, and `Z`.

### Domain

All `PathPDF` instances whose commands use the supported command subset and
whose `C`, `S`, `Q`, and `T` point counts are complete groups.

### Proof Method

Static path proof over `PathPDF._command_operators()`:

1. `M` emits a PDF `m` operator at the last move point.
2. `L` emits one `l` operator for each point.
3. `H` emits one `l` operator using the new x-coordinate and current y.
4. `V` emits one `l` operator using current x and the new y-coordinate.
5. `Q` converts each control/end pair to one cubic `c` operator through
   `_quadratic_to_cubic()`.
6. `T` reflects the previous quadratic control when the previous segment was
   `Q` or `T`, then converts the reflected control/end pair to cubic controls.
7. `C` emits one cubic `c` operator for each control/control/end triple.
8. `S` reflects the previous cubic second control when the previous segment was
   `C` or `S`, then emits one cubic `c` operator for each control/end pair.
9. `A` emits one line to the command end point under the current approximation
   contract.
10. `Z` emits `h`.
11. `generate_pdf()` wraps those operators with `_drawing_pdf()`.

### Conclusion

Proven for the stated domain.

## PO-PATH-013: PDF Smooth Commands Reflect Controls

### Claim

`PathPDF.generate_pdf()` emits deterministic cubic operators for SVG smooth
commands `S` and `T` by reflecting the previous applicable control point.

### Domain

All `PathPDF` instances containing complete `S` or `T` command point groups.

### Proof Method

`PathPDF._command_operators()` tracks the previous command type, previous cubic
second control, and previous quadratic control. `S` reflects the previous cubic
control only after `C` or `S`, otherwise it uses the current point as the first
cubic control. `T` reflects the previous quadratic control only after `Q` or
`T`, otherwise it uses the current point as the quadratic control. Tests assert
exact cubic operators for reflected controls, reset-after-line controls, and
multiple smooth segments inside one command.

### Conclusion

Proven for the stated smooth command domain.

## PO-PATH-005: Incomplete Curve Groups Fail

### Claim

`PathPDF.generate_pdf()` raises `ValueError` for incomplete `C`, `S`, `Q`, and
`T` point groups, and for `A` commands without an endpoint, instead of emitting
partial or missing geometry.

### Domain

All `PathPDF` instances containing `C` commands whose point count is not a
multiple of three, `S` commands whose point count is not a multiple of two, `Q`
commands whose point count is not a multiple of two, `T` commands with no
endpoints, or `A` commands without an endpoint.

### Proof Method

At the start of each command loop, `_command_operators()` checks `C` point
counts modulo three, `S` point counts modulo two, `Q` point counts modulo two,
whether `T` has an endpoint, and whether `A` has an endpoint. Any incomplete
point group or missing endpoint raises `ValueError` before operator generation.

### Conclusion

Proven for the stated domain.

## PO-PATH-014: Malformed Smooth Commands Fail Explicitly

### Claim

Malformed smooth `S` and `T` commands fail before `PathPDF` emits partial PDF
geometry.

### Domain

All `PathPDF` instances containing `S` commands with an odd number of points or
`T` commands without endpoints.

### Proof Method

`PathPDF._command_operators()` validates `S` point counts modulo two before
forming `(control_2, end)` pairs and validates that `T` has at least one
endpoint before reflecting a quadratic control. The failure-mode test includes
both malformed smooth partitions and asserts `ValueError` before output.

### Conclusion

Proven for the declared malformed smooth command partitions.

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

## PO-PATH-012: PathDrawing Revalidates Live Command Lists

### Claim

`PathDrawing.to_component()` rejects malformed values in the current public
`commands` list before constructing `PathSVG` or `PathPDF`.

### Domain

All public `PathDrawing` instances at materialization time, including instances
whose accepted post-construction `commands` list was mutated to include a
non-`PathCommand` object.

### Proof Method

`PathDrawing.to_component()` calls `_normalize_path_drawing_commands()` on the
current `self.commands` value before renderer dispatch. The helper returns
`None` for the empty-command sentinel, rejects raw strings, bytes, and
non-sequence values, copies accepted sequences, and raises `TypeError` unless
every current member is a `PathCommand`. The focused direct test mutates
`drawing.commands` and proves `to_component(OutputFormat.SVG)` fails at the
neutral boundary. The dependent-path test inserts the same mutated path drawing
inside `DrawingComponentGroup` and proves `group.to_group(OutputFormat.PDF)`
consumes the same guard. Mutation testing over the runtime validator and
materialization call killed all proof-critical mutants.

### Counterexamples And Exclusions

Private mutation of `PathCommand` internals and hostile monkey-patching of
renderer classes are outside this public command-list boundary. The public
`commands` list remains mutable for compatibility; the guarantee is fail-fast
materialization, not immutable state.

### Conclusion

Proven for the stated domain after focused tests and mutation pass.

## Current Slice Decision

The slice treats full SVG path semantics as larger than the current PDF/DXF
scope. It preserves SVG expressiveness while making PDF output fail loudly for
smooth commands and incomplete curve groups that cannot be faithfully rendered
by the current closed PDF renderer.
