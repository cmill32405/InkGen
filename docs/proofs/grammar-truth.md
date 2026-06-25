# Grammar Truth Proof Obligations

This note applies ADR-0001 and ADR-0002 to the PDF-P3 grammar-truth slice. It
separates mathematical proof obligations from engineering evidence.

## Scope

The slice adds grammar cue, construct, link, and assessment annotations that can
be attached to InkGen PDF documents, component groups, and components. The
public output is `DocumentPDF.grammar_truth()` and
`DocumentPDF.grammar_truth_json()`. It also covers serialized grammar
annotation payload validation at restore boundaries.

## Architecture Impact

This report applies the Architecture Impact Done gate for the grammar-truth/PDF
slice.

Affected surface:

- `src/InkGen/grammar_truth.py`: grammar annotation and record contracts.
- `src/InkGen/pdf_render_contract.py`: closed PDF renderer guard contracts.
- `src/InkGen/pdf_generator.py`: PDF grammar-truth emission, parameter
  round-trip, and render-path guard use.
- `src/InkGen/drawing_components.py`: renderer-neutral annotation propagation
  to concrete PDF groups and components.
- `tests/test_grammar_truth.py` and `tests/test_pdf_generator.py`: behavioral,
  compatibility, live-path, and guard coverage.
- `tests/mutation/grammar_truth_cosmic_ray.toml`: mutation gate for
  proof-critical grammar emitter and PDF render-contract logic.
- `docs/dependency-map.md`, ADR-0001, ADR-0002, and this proof note:
  architecture, decision, and proof evidence.

Incoming dependencies:

- Downstream Document Intelligence parser validation relies on stable
  grammar-truth records, PDF coordinate frames, and deterministic parser-facing
  fixture output.
- Public callers rely on `DocumentPDF.grammar_truth()`,
  `DocumentPDF.grammar_truth_json()`, `parameters`, and `create_from_dict()`
  preserving annotated and unannotated recipes.
- Renderer-neutral drawing recipes rely on `DrawingComponentGroup.to_group()`
  to materialize annotations onto concrete output-format objects.
- PDF noninterference proof obligations rely on `DocumentPDF.to_pdf_bytes()`
  rendering through the closed built-in PDF component domain.

Outgoing dependencies:

- `grammar_truth.py` depends on extraction-truth constants and bbox conversion
  semantics for `body` source records in the `pdf_points_bottom_left` coordinate
  frame.
- `pdf_generator.py` depends on grammar-truth serialization helpers and
  `pdf_render_contract.py` guard functions.
- `pdf_render_contract.py` depends only on component abstractions and runtime
  type checks; it must remain small enough to mutation-test directly.
- `drawing_components.py` depends on concrete renderer materialization through
  `to_component(output_format)` and copies annotation state onto the concrete
  target.

Before/after edge changes:

- The slice intentionally added the known cross-layer edge
  `pdf_generator.py -> grammar_truth.py` so PDF documents can emit
  parser-facing grammar records.
- The slice intentionally added the edge
  `pdf_generator.py -> pdf_render_contract.py` so the proof-critical closed PDF
  renderer domain is enforced by a small guard module.
- The slice reused the existing
  `drawing_components.py -> pdf_generator.py` materialization edge and added
  grammar annotation propagation across that boundary.
- No new third-party dependency edge was introduced.
- Before TRUTH-ANNOTATION-PAYLOAD-P2, `GrammarTruthAnnotation.from_dict()`
  stringified malformed serialized `condition_id`, `kind`, `links_to`,
  `source_channel`, and `instance_id` fields.
- After TRUTH-ANNOTATION-PAYLOAD-P2, serialized grammar-truth annotation
  payloads must be mappings with required string fields and optional string
  fields before restore can attach them to a target.

Cycle/layer/coupling/redundancy result:

- Cycle check: no intended cycle is introduced. Truth emitters do not import
  PDF renderers; renderers consume truth emitters.
- Layer check: concrete PDF renderers may depend on truth emitters and render
  contracts according to `docs/dependency-map.md`.
- Coupling check: proof-critical renderer-domain checks are isolated in
  `pdf_render_contract.py` instead of broadening `grammar_truth.py` or making
  the truth emitter own PDF rendering.
- Redundancy check: grammar truth reuses extraction-truth coordinate constants
  and conversion semantics rather than introducing a second PDF coordinate
  convention.

Evidence source and freshness:

- Source-backed: `src/InkGen/grammar_truth.py`,
  `src/InkGen/pdf_render_contract.py`, `src/InkGen/pdf_generator.py`, and
  `src/InkGen/drawing_components.py` were the implementation files changed for
  the slice.
- Test-backed: `tests/test_grammar_truth.py`, `tests/test_pdf_generator.py`,
  and the Cosmic Ray report listed below cover the affected live paths and
  proof-critical guards.
- Design-backed: `docs/dependency-map.md`, ADR-0001, and ADR-0002 define the
  intended dependency direction and accepted boundary changes.
- No architecture claim in this section relies only on stale memory.

ADR/rule impact:

- ADR-0001 accepts registry-agnostic PDF grammar truth annotations and the
  grammar-truth public API.
- ADR-0002 accepts the closed PDF renderer domain needed for PO-GT-004.
- `docs/dependency-map.md` records the new known cross-layer edges and public
  contracts to protect.
- No further ADR is required for this slice unless a future change adds a new
  grammar kind, extends the built-in PDF component set, changes the coordinate
  frame, or reopens arbitrary custom PDF rendering.

## Domain Definitions

- `BODY_SOURCE_CHANNEL` is the string `"body"`.
- `COORDINATE_FRAME_PDF` is the string `"pdf_points_bottom_left"`.
- A valid grammar kind is one of `cue`, `construct`, `link`, or `assessment`.
- A normalizable bbox is either:
  - a 4-item tuple/list of numbers `[a, b, c, d]`, or
  - a tuple/list of point-like tuple/list values where each point has numeric
    `x` and `y` values in positions 0 and 1.
- `normalize_bbox(bbox)` returns `(min_x, min_y, max_x, max_y)` for a
  normalizable bbox and `None` otherwise.
- A grammar annotation is body-sourced when `source_channel == "body"`.

## Comprehensiveness Matrix

The proof set is comprehensive only for the following declared partitions.

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Body-sourced annotation on a target with a normalizable bbox | Emit page-local PDF bbox | PO-GT-001 | `test_document_pdf_emits_grammar_truth_in_pdf_coordinates` | Must be killed or proven equivalent |
| Body-sourced annotation on a target without a usable bbox | Emit body record with `bbox is None` | PO-GT-001 exclusion path | `test_body_annotation_without_bbox_emits_none_bbox` | Must be killed or proven equivalent |
| Non-body annotation | Emit document-level record with `page == 0` and `bbox is None` | PO-GT-002 | `test_document_pdf_emits_assessment_and_link_truth` | Must be killed or proven equivalent |
| Valid grammar kinds: `cue`, `construct`, `link`, `assessment` | Accept and serialize | PO-GT-003 | grammar-truth happy path, link/assessment, and neutral propagation tests | Must be killed or proven equivalent |
| Invalid grammar kind or empty condition id | Reject near annotation boundary | Constructor invariant | `test_grammar_truth_rejects_empty_condition_and_invalid_kind` | Must be killed or proven equivalent |
| Invalid optional reference fields or empty source channel | Reject near annotation boundary | Constructor invariant | `test_grammar_truth_rejects_invalid_optional_fields` | Must be killed or proven equivalent |
| Malformed serialized annotation payloads | Reject before stringifying schema fields during direct restore | PO-GT-006 | `test_grammar_truth_from_dict_rejects_malformed_serialized_fields`, `test_restore_grammar_truth_rejects_malformed_serialized_annotations` | killed |
| Annotation serialization from InkGen-generated dictionaries | Round-trip exactly under equality assumptions | PO-GT-003 | `test_grammar_truth_round_trips_with_document_pdf_parameters` | Must be killed or proven equivalent |
| Unannotated legacy PDF parameters | Preserve prior parameter shape; no grammar keys appear | Compatibility invariant | `test_unannotated_pdf_parameters_do_not_gain_grammar_truth_keys` | Must be killed or proven equivalent |
| Grammar annotations only | Do not affect rendered PDF bytes | PO-GT-004 | `test_grammar_truth_annotations_do_not_change_pdf_bytes` | Must be killed or proven equivalent |
| Unsupported custom PDF component through public add path | Reject before insertion | PO-GT-004 domain guard | `test_component_group_pdf_rejects_non_pdf_components` | Must be killed or proven equivalent |
| Unsupported custom PDF component inserted by private mutation | Reject before render | PO-GT-004 domain guard | `test_component_group_pdf_rejects_non_pdf_components` | Must be killed or proven equivalent |
| Non-`ComponentGroupPDF` group on a PDF page | Reject before rendering | PO-GT-004 domain guard | `test_document_pdf_rejects_non_pdf_child_in_standard_group` | Must be killed or proven equivalent |
| Renderer-neutral drawing annotations converted to PDF | Copy annotations onto concrete PDF group/components | PO-GT-005 | `test_neutral_drawing_annotations_materialize_to_pdf_grammar_truth` | Must be killed or proven equivalent |
| Monkey-patched renderers, hostile private mutation beyond tested guards, non-reflexive annotation values, and future components not added to the closed tuple/proof note | Excluded from proven domain | Explicit exclusions in PO-GT-003 through PO-GT-005 | none | Out of scope |

## Test Applicability Matrix

This report applies the Test Applicability Done gate for the grammar-truth/PDF
slice.

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Grammar annotations, record serialization, sorting, helper contracts, and render-contract guards are small deterministic units. | `tests/test_grammar_truth.py`; `test_pdf_render_contract_helpers_keep_keyword_only_message` |
| Behavioral/condition | yes | The slice implements PDF-P3 grammar-truth behavior. | All grammar-truth tests are marked `@pytest.mark.condition("PDF-P3")`; PDF guard tests use PDF-P1/PDF-P3 markers where the guard crosses the existing PDF backend. |
| Failure-mode | yes | Invalid condition ids, invalid kinds, malformed serialized annotation payloads, invalid optional fields, unsupported components, non-PDF groups, and bad file paths must fail loudly. | `test_grammar_truth_rejects_empty_condition_and_invalid_kind`; `test_grammar_truth_from_dict_rejects_malformed_serialized_fields`; `test_restore_grammar_truth_rejects_malformed_serialized_annotations`; `test_grammar_truth_rejects_invalid_optional_fields`; `test_component_group_pdf_rejects_non_pdf_components`; `test_document_pdf_rejects_non_pdf_child_in_standard_group`; existing `test_document_pdf_create_pdf_writes_bytes_and_rejects_missing_directory` |
| Integration/live-path | yes | Grammar truth must be reachable through public PDF document and renderer-neutral drawing paths, not only helper calls. | `test_document_pdf_emits_grammar_truth_in_pdf_coordinates`; `test_grammar_truth_round_trips_with_document_pdf_parameters`; `test_neutral_drawing_annotations_materialize_to_pdf_grammar_truth`; `test_grammar_truth_annotations_do_not_change_pdf_bytes` |
| Contract/API compatibility | yes | Public grammar APIs, `DocumentPDF.parameters`, legacy unannotated parameters, and closed PDF component contracts changed. | `test_grammar_truth_round_trips_with_document_pdf_parameters`; `test_unannotated_pdf_parameters_do_not_gain_grammar_truth_keys`; `test_grammar_truth_public_helpers_keep_keyword_only_contracts`; PDF round-trip tests in `tests/test_pdf_generator.py` |
| Property/fuzz | yes | Coordinate conversion, sorting determinism, and serialization have invariant-like behavior. InkGen does not currently include a property-test dependency, so this slice uses deterministic bounded property-style tests over declared domain partitions rather than randomized fuzzing. | PO-GT-001 through PO-GT-005; `test_grammar_truth_bbox_property_cases_emit_pdf_coordinates`; `test_grammar_truth_annotation_property_cases_round_trip_and_sort_deterministically`; sorting tests for `None` and dictionary values. |
| Mutation | yes | Grammar emitter and render-contract guards are proof-critical. | Cosmic Ray 8.4.6 report below: 203 work items, 115 killed, 88 deterministic annotation-only skips, 0 survived. |
| Security/adversarial | limited yes | The slice does not add network, auth, deserialization of untrusted formats, subprocesses, SQL, templates, fonts, images, or active generated content. It does touch user-visible values, file output paths through existing PDF generation, and unsupported renderer injection boundaries. | Invalid schema tests; unsupported-component rejection tests; existing bad-directory PDF write test; no new dependency files or active-content surface. |
| Performance/resource | no | Grammar annotation emission walks existing document/group/component structures and adds no unbounded parser, search, cache, network, or large-input algorithm beyond normal PDF generation. | Not applicable for this slice; no performance budget changed. |
| Concurrency/race | no | The slice adds no shared mutable global state, sessions, background workers, locks, queues, caches, temp-file coordination, or parallel generation behavior. | Not applicable for this slice. |
| Golden artifact/visual | yes | PDF bytes and parser-facing truth records must remain deterministic and inspectable. | `test_grammar_truth_annotations_do_not_change_pdf_bytes`; `test_document_pdf_is_deterministic_and_flips_page_coordinates_once`; `test_document_pdf_round_trips_parameters_and_bytes`; deterministic JSON/sorting tests. |
| Regression | yes | The slice was driven by downstream parser-proof needs and mutation-discovered risk around equality, ordering, contracts, and PDF noninterference. | `test_body_source_channel_uses_value_equality_not_identity`; `test_non_body_source_channels_suppress_page_and_bbox_regardless_of_sort_order`; mutation gate listed below. |

## Invariants, Preconditions, And Postconditions

Invariants:

- Grammar annotation state is stored separately from geometry, style, text, and
  PDF render state.
- The public grammar-truth schema contains deterministic keys:
  `condition_id`, `kind`, `page`, `bbox`, `value`, `links_to`,
  `source_channel`, `instance_id`, and `coordinate_frame`.
- Unannotated documents and groups do not gain grammar-truth parameter keys.
- PDF rendering remains deterministic when only grammar annotations change.
- `ComponentGroupPDF` renders only the closed set of built-in PDF component
  classes named in ADR-0002 and PO-GT-004.

Preconditions:

- Callers use `annotate_grammar_truth()` or serialized dictionaries produced by
  InkGen to attach grammar annotations.
- `condition_id` and `source_channel` are non-empty strings.
- `kind` is one of the four grammar truth kinds.
- `links_to` and `instance_id` are strings or `None`.
- Body-sourced bbox semantics require a target bbox in InkGen top-left canvas
  coordinates.

Postconditions:

- Invalid annotation schema fields fail at annotation construction or restore.
- Non-body records are document-level records with no bbox.
- Body records use PDF bottom-left coordinates when the target bbox is
  normalizable.
- Body records with no normalizable bbox preserve the record and emit
  `bbox is None`.
- `DocumentPDF.grammar_truth_json()` emits deterministic compact JSON for the
  sorted grammar-truth record list.

## Mutation Testing Gate

Proof-critical mutation targets:

- Removing the `source_channel == BODY_SOURCE_CHANNEL` branch in
  `records_for_annotated_target()` should fail body/non-body bbox tests.
- Changing `bbox_to_pdf_points()` from `H - y1, H - y0` to top-left coordinates
  should fail `test_document_pdf_emits_grammar_truth_in_pdf_coordinates`.
- Removing the exact-type guards in `ComponentGroupPDF.add_component()` or
  `ComponentGroupPDF.generate_pdf()` should fail
  `test_component_group_pdf_rejects_non_pdf_components`.
- Removing the `ensure_pdf_group()` guard in `DocumentPDF._render_page_content()`
  should fail `test_document_pdf_rejects_non_pdf_child_in_standard_group`.
- Weakening `ensure_builtin_pdf_component()` or `ensure_pdf_group()` should fail
  the PDF render-contract helper tests and the live PDF render-path tests.
- Removing grammar annotation restore/serialization from PDF parameter handling
  should fail `test_grammar_truth_round_trips_with_document_pdf_parameters`.
- Weakening serialized annotation payload validation should fail from-dict and
  restore tests.

The gate is automated. Manual perturbation or LLM-as-judge review cannot pass
this slice. Current command sequence:

```bash
cosmic-ray baseline tests/mutation/grammar_truth_cosmic_ray.toml
cosmic-ray init tests/mutation/grammar_truth_cosmic_ray.toml grammar_truth_cosmic_ray.sqlite
cr-filter-operators grammar_truth_cosmic_ray.sqlite tests/mutation/grammar_truth_cosmic_ray.toml
cosmic-ray exec tests/mutation/grammar_truth_cosmic_ray.toml grammar_truth_cosmic_ray.sqlite
```

The checked-in config is `tests/mutation/grammar_truth_cosmic_ray.toml`. It is
scoped to the proof-critical grammar emitter and closed PDF render-contract
guards:

- `src/InkGen/grammar_truth.py`
- `src/InkGen/pdf_render_contract.py`

and focused pytest selection:

- `tests/test_grammar_truth.py`
- `tests/test_pdf_generator.py`

Current result:

- Tool: Cosmic Ray 8.4.6.
- Environment: WSL Python 3.12 virtualenv.
- Work items: 203.
- Killed mutants: 115.
- Deterministically skipped mutants: 88
  `core/ReplaceBinaryOperator_BitOr_.*` mutations in postponed type
  annotations.
- Surviving mutants: 0.
- Mutated modules:
  - `src/InkGen/grammar_truth.py`: 178 mutants.
  - `src/InkGen/pdf_render_contract.py`: 25 mutants.
- Gate result: pass.

TRUTH-ANNOTATION-PAYLOAD-P2 current result:

- Focused tests: `77 passed`.
- Mutation: `23` proof-critical work items across extraction and grammar truth,
  `23 killed`, `0 survivors`.
- Full coverage gate: `841 passed`, total coverage `94%`.
- Ruff lint and format passed for touched Python files.

## PO-GT-001: PDF BBox Conversion

### Claim

Body-sourced grammar truth emits bboxes in PDF bottom-left coordinates.

### Domain

All grammar annotations attached to targets where:

- `source_channel == "body"`.
- `getattr(target, "bbox", None)` is normalizable.
- `canvas_height` is a number.

### Assumptions

- Python arithmetic and `min`/`max` have their standard meanings for numeric
  inputs.
- The target bbox is expressed in InkGen's top-left canvas coordinate frame.

### Theorem

For all normalizable bboxes whose normalized form is `(x0, y0, x1, y1)` and all
canvas heights `H`, the emitted grammar-truth bbox is:

```text
[x0, H - y1, x1, H - y0]
```

### Proof Method

Algebraic reasoning over the implementation.

1. `records_for_annotated_target()` sets `bbox = None`.
2. Because `source_channel == "body"`, it assigns:

   ```text
   bbox = bbox_to_pdf_points(getattr(target, "bbox", None), H)
   ```

3. By the domain definition, the target bbox is normalizable, so
   `normalize_bbox()` returns `(x0, y0, x1, y1)`.
4. `bbox_to_pdf_points()` assigns `x0, y0, x1, y1 = normalized`.
5. `bbox_to_pdf_points()` returns `[x0, H - y1, x1, H - y0]`.
6. Therefore the emitted record bbox is `[x0, H - y1, x1, H - y0]`.

### Counterexamples And Exclusions

- If the target bbox is not normalizable, the theorem does not apply.
- If the target uses a coordinate frame other than InkGen top-left canvas
  coordinates, the theorem does not establish semantic correctness.
- Non-body annotations are covered by PO-GT-002.

### Conclusion

Proven for the stated domain.

## PO-GT-002: Non-Body Records Have No BBox

### Claim

Non-body grammar annotations emit document-level records.

### Domain

All grammar annotations attached to any target where
`source_channel != "body"`.

### Assumptions

- `records_for_annotated_target()` is the only emitter used for individual
  grammar annotations.

### Theorem

For all grammar annotations where `source_channel != "body"`, the emitted record
has:

```text
page == 0
bbox is None
```

### Proof Method

Algebraic/static reasoning over the implementation.

1. `records_for_annotated_target()` initializes `bbox = None`.
2. The only assignment that can change `bbox` is guarded by:

   ```text
   if annotation.source_channel == BODY_SOURCE_CHANNEL
   ```

3. In this domain, `annotation.source_channel != BODY_SOURCE_CHANNEL`, so that
   guarded assignment does not execute and `bbox` remains `None`.
4. `record_page` is assigned by:

   ```text
   page if annotation.source_channel == BODY_SOURCE_CHANNEL else 0
   ```

5. In this domain, the condition is false, so `record_page == 0`.
6. `GrammarTruthRecord.from_annotation()` copies the supplied `page` and `bbox`
   into the record.
7. Therefore every emitted non-body record has `page == 0` and `bbox is None`.

### Counterexamples And Exclusions

- If a different emitter bypasses `records_for_annotated_target()`, this proof
  does not apply.

### Conclusion

Proven for the stated domain.

## PO-GT-003: Annotation Serialization Round Trip

### Claim

Grammar annotations round-trip through `to_dict()` and `from_dict()`.

### Domain

All `GrammarTruthAnnotation` instances where:

- `condition_id`, `kind`, and `source_channel` are valid by constructor rules.
- `links_to` is `None` or a string.
- `instance_id` is `None` or a string.
- `value` is any Python object that is compared by normal Python equality.

### Assumptions

- Dictionary key lookup returns the value stored under that key.
- `str(x) == x` for fields already constrained to strings.

### Theorem

For every annotation `A` in the domain:

```text
GrammarTruthAnnotation.from_dict(A.to_dict()) == A
```

### Proof Method

Algebraic reasoning over field mappings.

1. `A.to_dict()` emits exactly these keys:
   `condition_id`, `kind`, `value`, `links_to`, `source_channel`, and
   `instance_id`.
2. `from_dict()` reads the same keys.
3. `condition_id`, `kind`, and `source_channel` are strings by the domain, so
   wrapping them with `str(...)` preserves their values.
4. `links_to` and `instance_id` are either `None` or strings by the domain, so
   the `None` checks and `str(...)` conversions preserve their values.
5. `value` is copied from `data.get("value")` without conversion.
6. The reconstructed dataclass has the same field values as `A`.
7. Frozen dataclass equality compares field values.
8. Therefore `from_dict(A.to_dict()) == A`.

### Counterexamples And Exclusions

- If `value` has non-reflexive equality, such as `float("nan")`, ordinary
  dataclass equality may not report equality. That case is excluded from this
  theorem.
- If a dictionary not produced by `to_dict()` is supplied, this theorem does not
  apply.

### Conclusion

Proven for the stated domain.

## PO-GT-004: Grammar Truth Does Not Change PDF Bytes

### Claim

Adding grammar annotations does not alter rendered PDF bytes.

### Domain

- `DocumentPDF` instances containing only `ComponentGroupPDF` groups.
- `ComponentGroupPDF` instances containing only built-in PDF component types:
  `RectanglePDF`, `LinePDF`, `ArcPDF`, `QuadraticBezierPDF`, `CubicBezierPDF`,
  `PathPDF`, `RegularPolygonPDF`, `PolygonalPDF`, `CirclePDF`, and `TextPDF`.
- Grammar annotations are stored only in `_grammar_truth_annotations`.
- Rendering is performed through `DocumentPDF.to_pdf_bytes()`.

### Assumptions

- The closed renderer-domain checks in `DocumentPDF._render_page_content()`,
  `ComponentGroupPDF.add_component()`, and `ComponentGroupPDF.generate_pdf()`
  are not bypassed by direct mutation of private attributes.
- No caller monkey-patches rendering methods or built-in component classes.
- Built-in component `generate_pdf()` methods are the implementations in
  `pdf_generator.py`.

### Theorem

For every document in the intended domain, adding, removing, or replacing only
grammar annotations does not change `to_pdf_bytes()`.

### Proof Method

Static path proof over the closed built-in renderer domain.

The rendering path is:

```text
DocumentPDF.to_pdf_bytes()
  -> DocumentPDF._render_page_content()
  -> ComponentGroupPDF.generate_pdf()
  -> component.generate_pdf()
```

1. `DocumentPDF._render_page_content()` calls `ensure_pdf_group()` and rejects
   every group that is not a `ComponentGroupPDF`.
2. `ComponentGroupPDF.add_component()` calls
   `ensure_builtin_pdf_component()` and rejects every component whose exact type
   is not in the closed built-in PDF component tuple.
3. `ComponentGroupPDF.generate_pdf()` calls
   `ensure_builtin_pdf_component()` before rendering, so direct private mutation
   is detected at render time.
4. Therefore the only component `generate_pdf()` implementations reachable
   through the public PDF render path are the built-in implementations in
   `pdf_generator.py`, assuming private mutation and monkey-patching are
   excluded.
5. The built-in `generate_pdf()` implementations compute output from geometry,
   style, text, path commands, and the render context. They do not read
   `_grammar_truth_annotations`, `get_grammar_truth_annotations()`, or any
   grammar-truth helper.
6. `DocumentPDF.to_pdf_bytes()` and `_render_page_content()` do not read
   grammar-truth state.
7. Therefore changing only grammar-truth annotation state cannot affect any
   value read by the closed rendering path.
8. Therefore changing only grammar-truth annotation state cannot change
   `to_pdf_bytes()`.

### Counterexamples And Exclusions

- Direct mutation of private `_components` can insert unsupported components,
  but `ComponentGroupPDF.generate_pdf()` rejects them before rendering. Private
  mutation is outside the public construction contract.
- Monkey-patched methods or classes are excluded.
- Future built-in PDF components must extend the closed component tuple and this
  proof obligation together.

### Conclusion

Proven for the stated closed built-in renderer domain.

## PO-GT-005: Renderer-Neutral Annotation Propagation

### Claim

Renderer-neutral drawing annotations materialize to concrete PDF annotations.

### Domain

All `DrawingComponentGroup` instances whose components implement
`to_component(output_format)` and where `output_format == "pdf"`.

### Assumptions

- `copy_grammar_truth_annotations()` is the only propagation mechanism.
- The component's `to_component("pdf")` returns the concrete component that will
  be inserted into the output group.

### Theorem

For every annotated group and annotated component in the domain,
`DrawingComponentGroup.to_group("pdf")` copies the same grammar annotations onto
the concrete `ComponentGroupPDF` and concrete PDF components.

### Proof Method

Static reasoning over `DrawingComponentGroup.to_group()`:

1. The method creates a `ComponentGroupPDF` for `OutputFormat.PDF`.
2. It calls `copy_grammar_truth_annotations(self, group)` before returning the
   group.
3. For every component in `self.components`, it calls
   `component.to_component(target)` and stores the result in `concrete`.
4. It calls `copy_grammar_truth_annotations(component, concrete)`.
5. It adds `concrete` to the output group.
6. Therefore every annotation visible through `get_grammar_truth_annotations()`
   on the neutral group or component is copied to the corresponding concrete
   group or component.

### Counterexamples And Exclusions

- Components that mutate their annotation state during `to_component()` are
  outside the proof.
- Components that return a proxy instead of the actual inserted component are
  outside the proof.

### Conclusion

Proven for the stated domain, assuming well-behaved `to_component()` methods.

## PO-GT-006: Serialized Grammar Annotation Payloads Are Validated

### Claim

`GrammarTruthAnnotation.from_dict()` rejects malformed serialized annotation
payloads before schema fields can be stringified.

### Domain

Serialized grammar-truth annotation dictionaries supplied to direct
`from_dict()` calls or restore through `restore_grammar_truth_annotations()`.

### Proof Method

`from_dict()` first requires the payload to be a mapping. It then requires
`condition_id` and `kind` to exist and be strings, validates optional
`source_channel` as a string when present, and validates `links_to` and
`instance_id` as strings or `None`. The dataclass constructor retains the
non-empty string and allowed-kind checks. Focused tests cover non-mapping
payloads, missing required fields, malformed required fields, malformed
optional fields, and the restore path.

### Counterexamples And Exclusions

The `value` field intentionally remains open-ended because grammar assessments
may contain structured JSON-like values. Generated dictionaries produced by
`to_dict()` remain in the valid round-trip domain covered by PO-GT-003.

### Conclusion

Supported by focused extraction/grammar/PDF tests, scoped mutation testing, and
the full coverage gate for the stated serialized annotation payload boundary.

## Current Slice Decision

The slice has mathematical proof for PO-GT-001 through PO-GT-005 under stated
domains and assumptions.

The main design constraint added by this proof is that the PDF render path is a
closed built-in component domain. Arbitrary custom PDF components are not part of
the proven renderer contract.
