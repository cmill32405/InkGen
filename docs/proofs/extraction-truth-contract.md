# Extraction Truth Contract Proof Obligations

This note applies the InkGen Definition of Done to the PDF-P2 extraction-truth
slice. It separates the extraction-truth schema, PDF coordinate theorem,
deterministic serialization, parameter round trip, and rendered-byte
noninterference proof obligations. It also covers serialized annotation
payload validation at restore boundaries and finite/non-boolean bbox coordinate
normalization. Grammar-truth obligations that share this truth-emitter layer
are recorded here when no separate grammar-truth proof note exists.

## Scope

The slice covers:

- `ExtractionTruthAnnotation`
- `ExtractionTruthRecord`
- `annotate_extraction_truth()`
- `records_for_annotated_target()`
- `bbox_to_pdf_points()` and `normalize_bbox()`
- `sort_extraction_truth_records()` and `extraction_truth_json()`
- `DocumentPDF.extraction_truth()` and `DocumentPDF.extraction_truth_json()`
- PDF parameter serialization and restore for document, group, and component
  annotations

Renderer-specific drawing bytes are in scope only for proving that extraction
truth does not change `DocumentPDF.to_pdf_bytes()`.

## Architecture Impact

Affected surface:

- `src/InkGen/extraction_truth.py`: annotation validation and truth-record
  helpers.
- `src/InkGen/grammar_truth.py`: grammar annotation validation, deterministic
  value sorting, and grammar truth JSON helpers.
- `src/InkGen/pdf_generator.py`: existing live-path extraction-truth emission
  and parameter round trip.
- `tests/test_extraction_truth.py`: PDF-P2 condition tests for direct helper
  and live PDF behavior.
- `tests/mutation/extraction_truth_cosmic_ray.toml`: scoped mutation gate.
- `tests/mutation/filter_extraction_truth_work_items.py`: proof-critical
  mutation filter.

Incoming dependencies:

- `DocumentPDF.extraction_truth()` depends on extraction-truth helpers for
  parser-facing records.
- `grammar_truth.py` reuses `BODY_SOURCE_CHANNEL`, `COORDINATE_FRAME_PDF`, and
  `bbox_to_pdf_points()`, so coordinate regressions can affect PDF-P3.
- Downstream Document Intelligence checks rely on stable records in
  `pdf_points_bottom_left`.

Outgoing dependencies:

- `extraction_truth.py` depends only on standard-library dataclasses, JSON, and
  object attributes.
- No dependency was added.

Before/after edge changes:

- No dependency edge changed.
- Annotation validation is stricter for `is_truth` and `instance_id`, matching
  the declared generated-data schema instead of silently accepting arbitrary
  objects.
- Before TRUTH-ANNOTATION-PAYLOAD-P2, `ExtractionTruthAnnotation.from_dict()`
  stringified malformed serialized `field_name`, `value`, `role`,
  `source_channel`, and `instance_id` fields.
- After TRUTH-ANNOTATION-PAYLOAD-P2, serialized extraction-truth annotation
  payloads must be mappings with required string fields and optional string
  fields before restore can attach them to a target.
- Before TRUTH-BBOX-FINITE-P2, bbox normalization treated booleans as numbers
  and could pass `nan` or infinity into parser-facing PDF coordinates.
- After TRUTH-BBOX-FINITE-P2, bbox coordinate candidates must be non-boolean
  finite integers or floats before they can contribute to an emitted bbox.
- Before GRAMMAR-TRUTH-VALUE-JSON-P2, grammar truth accepted arbitrary Python
  objects as values, sorted them through fallback stringification, then failed
  later during JSON export.
- After GRAMMAR-TRUTH-VALUE-JSON-P2, grammar truth values must be deterministic
  standard JSON values before annotations or records can be constructed.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced.
- Layer check: truth annotations remain independent of concrete renderers.
- Coupling check: renderers consume truth helpers, but truth helpers do not call
  renderers.
- Redundancy check: PDF coordinate conversion remains centralized in
  `bbox_to_pdf_points()` and shared with grammar truth.

ADR/rule impact:

- No new ADR is required. This slice reinforces the dependency-map rule that
  truth emitters may read annotation attributes and geometry but must not alter
  rendered output.

## Domain Definitions

- `BODY_SOURCE_CHANNEL` is the string `"body"`.
- `COORDINATE_FRAME_PDF` is the string `"pdf_points_bottom_left"`.
- A valid extraction annotation has non-empty string `field_name`, `value`,
  `role`, and `source_channel`, a boolean `is_truth`, and `instance_id` as
  `None` or a string.
- A normalizable bbox is either:
  - a 4-item tuple/list of numbers `[a, b, c, d]`, or
  - a tuple/list of point-like tuple/list values where each point has numeric
    `x` and `y` values in positions 0 and 1.
- `normalize_bbox(bbox)` returns `(min_x, min_y, max_x, max_y)` for a
  normalizable bbox and `None` otherwise.
- An extraction annotation is body-sourced when
  `source_channel == BODY_SOURCE_CHANNEL`.
- A valid grammar truth value is `None` or a standard JSON value accepted by
  `json.dumps(..., sort_keys=True, allow_nan=False)`.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Body annotation with normalizable bbox | Emit page-local PDF bbox | PO-ET-001 | `test_document_pdf_emits_group_truth_in_pdf_coordinates`, `test_extraction_truth_bbox_property_cases_emit_pdf_coordinates` | killed |
| Body annotation without usable bbox | Preserve record with `bbox is None` | PO-ET-001 exclusion path | `test_body_annotation_without_bbox_emits_none_bbox` | killed |
| Non-body annotation | Emit page `0` and `bbox is None` | PO-ET-002 | `test_document_pdf_emits_component_and_out_of_band_truth`, `test_non_body_source_channels_suppress_page_and_bbox_regardless_of_sort_order` | killed |
| Valid generated annotations | Round-trip through dicts and PDF parameters | PO-ET-003 | `test_extraction_truth_round_trips_with_document_pdf_parameters`, `test_extraction_truth_annotation_property_cases_round_trip_and_sort_deterministically` | killed |
| Malformed serialized annotation payloads | Reject before stringifying schema fields during direct restore | PO-ET-005 | `test_extraction_truth_from_dict_rejects_malformed_serialized_fields`, `test_restore_extraction_truth_rejects_malformed_serialized_annotations`, `test_extraction_truth_from_dict_preserves_default_truth_flag` | killed |
| Invalid schema fields | Fail near annotation boundary | Constructor invariant | `test_extraction_truth_rejects_empty_required_fields`, `test_extraction_truth_rejects_invalid_optional_fields` | one equivalent survivor |
| Malformed bbox shapes | Ignore malformed entries or return `None` without partial coercion | Defensive invariant | `test_extraction_truth_bbox_normalization_rejects_malformed_shapes` | killed |
| Boolean or non-finite bbox coordinates | Ignore malformed point entries or suppress malformed rectangular bboxes before PDF conversion | PO-ET-006 | `test_extraction_truth_bbox_normalization_rejects_bool_and_nonfinite_coordinates` | killed |
| Grammar truth JSON value domain | Reject arbitrary objects, non-serializable nested values, and `nan`/infinity before sort/export | PO-GT-001 | `test_grammar_truth_rejects_non_json_serializable_values`, `test_grammar_truth_from_dict_rejects_malformed_serialized_fields` | killed |
| Unannotated legacy PDF parameters | Preserve prior parameter shape | Compatibility invariant | `test_unannotated_pdf_parameters_do_not_gain_extraction_truth_keys` | killed |
| Extraction annotations only | Do not affect rendered PDF bytes | PO-ET-004 | `test_extraction_truth_annotations_do_not_change_pdf_bytes` | killed |
| Sorting and JSON serialization | Emit deterministic order and compact sorted-key JSON | Determinism invariant | sorting and JSON tests | killed |
| Monkey-patched renderers, hostile private mutation beyond tested public paths, non-generated dictionaries with intentionally coerced string fields | Excluded from proven domain | Explicit exclusions | none | out of scope |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Annotation, bbox, sorting, and JSON helpers are deterministic units. | `tests/test_extraction_truth.py` |
| Behavioral/condition | yes | The slice defines PDF-P2 extraction-truth behavior. | Tests are marked `@pytest.mark.condition("PDF-P2")`. |
| Failure-mode | yes | Empty fields, malformed serialized annotation payloads, invalid optional types, missing geometry, malformed/boolean/non-finite bboxes, and positional contract misuse must fail or degrade safely. | invalid-field, serialized-payload, no-bbox, malformed-bbox, finite-bbox, and keyword-only tests |
| Integration/live-path | yes | Truth must be reachable through `DocumentPDF`, groups, and components. | Document PDF emission, round-trip, and byte-stability tests |
| Contract/API compatibility | yes | Public helper signatures, parameter shape, and deterministic JSON are protected. | keyword-only, unannotated parameters, round-trip, and JSON tests |
| Property/fuzz | limited yes | InkGen has no property-test dependency, so bounded deterministic partitions cover coordinate and annotation domains. | bbox and annotation property-case tests |
| Mutation | yes | The emitter and coordinate conversion are proof-critical. | Cosmic Ray result below |
| Security/adversarial | limited yes | No network, auth, SQL, subprocess, or active content surface is added; invalid schema values and malformed geometry are rejected or ignored. | invalid-field and malformed-bbox tests |
| Performance/resource | no | The slice adds constant-time validation and existing linear record walks. | Not applicable |
| Concurrency/race | no | No shared mutable global state is added. | Not applicable |
| Golden artifact/visual | yes | PDF bytes and parser-facing truth records must be deterministic. | byte-stability, JSON, sorting, and round-trip tests |
| Regression | yes | The slice protects the PDF-P2 truth path used by downstream parser validation and PDF-P3 grammar conversion. | focused gate includes extraction, grammar, and PDF tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Weakening annotation field validation must fail invalid-schema tests.
- Weakening serialized annotation payload validation must fail from-dict and
  restore tests.
- Changing body/non-body channel branching must fail page/bbox tests.
- Changing `bbox_to_pdf_points()` from bottom-left conversion must fail
  coordinate theorem tests.
- Weakening bbox normalization must fail malformed-shape and property-case
  tests.
- Weakening finite/non-boolean coordinate validation must fail
  `test_extraction_truth_bbox_normalization_rejects_bool_and_nonfinite_coordinates`.
- Removing serialization, sorting, or JSON determinism must fail round-trip and
  deterministic-output tests.

Current result:

- Tool: Cosmic Ray 8.4.6.
- Environment: WSL Python 3.12 virtualenv.
- Raw work items: 272.
- Proof-critical work items after filter: 105.
- Killed mutants: 104.
- Equivalent survivors: 1.
- Surviving equivalent mutation:
  - `value == ""` changed to `value <= ""` inside the guarded string-validation
    branch. For Python strings in the proven domain, only the empty string is
    less than or equal to the empty string, so the accepted/rejected set is
    unchanged.
- Gate result: pass with documented equivalent survivor.

TRUTH-ANNOTATION-PAYLOAD-P2 current result:

- Focused tests: `77 passed`.
- Mutation: `23` proof-critical work items across extraction and grammar truth,
  `23 killed`, `0 survivors`.
- Full coverage gate: `841 passed`, total coverage `94%`.
- Ruff lint and format passed for touched Python files.

TRUTH-BBOX-FINITE-P2 current result:

- Focused tests: `87 passed`.
- Mutation: `35` proof-critical work items, `35 killed`, `0 survivors`.
- Full coverage gate: `876 passed`, total coverage `94%`.
- Ruff lint and format passed for touched Python files.

## PO-ET-001: PDF BBox Conversion

### Claim

Body-sourced extraction truth emits bboxes in PDF bottom-left coordinates.

### Domain

All extraction annotations attached to targets where:

- `source_channel == "body"`.
- `getattr(target, "bbox", None)` is normalizable.
- `canvas_height` is a number.

### Theorem

For all normalizable bboxes whose normalized form is `(x0, y0, x1, y1)` and all
canvas heights `H`, the emitted extraction-truth bbox is:

```text
[x0, H - y1, x1, H - y0]
```

### Proof Method

1. `records_for_annotated_target()` calls `bbox_to_pdf_points()` only for
   body-sourced annotations.
2. `bbox_to_pdf_points()` calls `normalize_bbox()`.
3. For normalizable inputs, `normalize_bbox()` returns
   `(x0, y0, x1, y1)`.
4. `bbox_to_pdf_points()` returns `[x0, H - y1, x1, H - y0]`.
5. `ExtractionTruthRecord.from_annotation()` copies that bbox into the record.

### Conclusion

Proven for the stated domain by algebraic reasoning, focused tests, and
mutation.

## PO-ET-002: Non-Body Records Have No BBox

### Claim

Non-body extraction annotations emit document-level records.

### Domain

All extraction annotations where `source_channel != "body"`.

### Theorem

Every emitted non-body extraction record has:

```text
page == 0
bbox is None
```

### Proof Method

1. `records_for_annotated_target()` initializes `bbox = None`.
2. The only bbox assignment is guarded by
   `annotation.source_channel == BODY_SOURCE_CHANNEL`.
3. In this domain, the guard is false, so `bbox` remains `None`.
4. `record_page` is assigned to `0` for the same false branch.
5. `ExtractionTruthRecord.from_annotation()` copies `page` and `bbox`.

### Conclusion

Proven for the stated domain by static reasoning, focused tests, and mutation.

## PO-ET-003: Annotation Serialization Round Trip

### Claim

Generated extraction annotations round-trip through `to_dict()` and
`from_dict()`.

### Domain

All `ExtractionTruthAnnotation` instances satisfying the constructor schema.

### Theorem

For every annotation `A` in the domain:

```text
ExtractionTruthAnnotation.from_dict(A.to_dict()) == A
```

### Proof Method

1. `to_dict()` emits every constructor field under stable keys.
2. `from_dict()` reads the same keys, preserving generated string, bool, and
   optional string values.
3. The frozen dataclass equality compares field values.
4. Therefore the reconstructed annotation equals the original annotation.

### Conclusion

Proven for the generated-data domain by tests, PDF parameter round trip, and
mutation.

## PO-ET-004: Extraction Truth Does Not Change PDF Bytes

### Claim

Adding extraction annotations does not alter rendered PDF bytes.

### Domain

- `DocumentPDF` instances containing valid `ComponentGroupPDF` groups and
  built-in PDF components.
- Extraction annotations are stored only in `_extraction_truth_annotations`.
- Rendering is performed through `DocumentPDF.to_pdf_bytes()`.

### Proof Method

1. `DocumentPDF.to_pdf_bytes()` renders page content through PDF groups and
   components.
2. Built-in PDF component `generate_pdf()` methods compute output from
   geometry, style, text, path commands, and render context.
3. `DocumentPDF.to_pdf_bytes()` does not call extraction-truth helpers.
4. Therefore changing only extraction-truth annotation state cannot affect the
   rendered byte path.

### Conclusion

Proven for the stated domain by static path review and byte-stability tests.

## PO-ET-005: Serialized Extraction Annotation Payloads Are Validated

### Claim

`ExtractionTruthAnnotation.from_dict()` rejects malformed serialized annotation
payloads before schema fields can be stringified.

### Domain

Serialized extraction-truth annotation dictionaries supplied to direct
`from_dict()` calls or restore through `restore_extraction_truth_annotations()`.

### Proof Method

`from_dict()` first requires the payload to be a mapping. It then requires
`field_name` and `value` to exist and be strings, validates optional `role` and
`source_channel` as strings when present, and validates `instance_id` as a
string or `None`. The dataclass constructor retains the non-empty string and
boolean checks. Focused tests cover non-mapping payloads, missing required
fields, malformed required fields, malformed optional fields, and the restore
path.

### Counterexamples And Exclusions

The `value` field is intentionally still a string for extraction truth.
Generated dictionaries produced by `to_dict()` remain in the valid round-trip
domain covered by PO-ET-003.

### Conclusion

Supported by focused extraction/grammar/PDF tests, scoped mutation testing, and
the full coverage gate for the stated serialized annotation payload boundary.

## PO-ET-006: BBox Coordinates Are Finite Non-Boolean Numbers

### Claim

Extraction truth bbox normalization does not emit parser-facing coordinates
from booleans, `nan`, or infinite values.

### Domain

Rectangular bbox tuples/lists and point-list bbox shapes passed to
`normalize_bbox()` and `records_for_annotated_target()`.

### Proof Method

`normalize_bbox()` accepts a rectangular bbox only when all four values satisfy
`_is_number()`. Point-list bboxes ignore any point whose x/y values do not
satisfy `_is_number()`. `_is_number()` rejects booleans, non-number objects,
`nan`, and infinity before conversion to PDF bottom-left coordinates. Focused
tests cover rectangular bbox suppression and point-list degradation where
malformed points are ignored while valid points still emit deterministic PDF
coordinates.

### Counterexamples And Exclusions

This proof does not validate semantic correctness of a caller-provided finite
bbox. It only proves the numeric domain accepted by the truth emitter.

### Conclusion

Supported by focused extraction/grammar/PDF tests, scoped mutation testing, and
the full coverage gate for the stated finite bbox boundary.

## PO-GT-001: Grammar Truth Values Are Deterministic JSON

### Claim

Grammar truth annotations and emitted records reject values that cannot be
serialized into deterministic standard JSON.

### Domain

Public `GrammarTruthAnnotation(...)`, `annotate_grammar_truth(..., value=...)`,
`GrammarTruthAnnotation.from_dict(...)`, and `GrammarTruthRecord(...)` calls.

### Dependencies

- `GrammarTruthAnnotation.__post_init__()`
- `GrammarTruthRecord.__post_init__()`
- `_stable_value()`
- `_require_json_serializable_value()`
- `sort_grammar_truth_records()`
- `grammar_truth_json()`

### Proof Method

`GrammarTruthAnnotation.__post_init__()` and
`GrammarTruthRecord.__post_init__()` both route `value` through
`_require_json_serializable_value()`. The helper calls `json.dumps()` with
sorted keys, compact separators, and `allow_nan=False`, so arbitrary objects,
non-serializable nested values, and non-standard floating values fail before
truth records can enter the sort/export path. `_stable_value()` uses the same
helper, so deterministic sorting and JSON export share the same value domain.

### Counterexamples And Exclusions

Semantically validating the meaning of a JSON value is outside this proof; the
proof only establishes that accepted values have a deterministic JSON artifact
representation. Raw dictionaries passed directly to `grammar_truth_json()` are
outside annotation construction and remain ordinary JSON serialization inputs.

### Conclusion

Focused tests cover direct annotation, public helper, from-dict, emitted record,
and nested invalid value paths. Full coverage, mutation, lint, docs, and diff
hygiene remain release-gate checks for the slice.
