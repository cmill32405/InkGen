# Document Model Contract Proof Obligations

This note applies the InkGen Definition of Done to the DOCUMENT-MODEL-P1,
DOCUMENT-MODEL-PAYLOAD-P2, DOCUMENT-MODEL-STYLES-MAPPING-P2, and
DOCUMENT-LOAD-STYLE-PREPASS-P2 document model slices. It focuses on one-based
page indexing, page insertion and removal boundaries, page canvas
compatibility, serialized page hydration, serialized payload envelope
validation, style-cache validation, YAML load delegation, identifier lookup
boundaries, and live use through PDF rendering.

## Scope

The slice covers:

- `Layers.create_from_dict()`
- `Layer.create_from_dict()`
- `Document.create_from_dict()`
- `Document.add_page()`
- `Document.remove_page()`
- `Document.page()`
- `Document._validate_insert_position()`
- `Document._validate_existing_position()`
- `Document._page_canvas_compatibility()`
- `Layer.remove_component_group()`
- `Layer.group()`
- `Layers._layer_identification_lookup()`

## Architecture Impact

Affected surface:

- `src/InkGen/document.py`: page validation, page insertion/removal, and
  serialized document/layer hydration.
- `docs/api-reference.md`, `docs/components/document-structure.md`, and
  `docs/examples.md`: one-based page examples.
- `tests/test_document_model_contract.py`: DOCUMENT-MODEL-P1 behavioral and
  live-path tests.
- `tests/mutation/document_model_cosmic_ray.toml`: scoped mutation gate.
- `tests/mutation/filter_document_model_work_items.py`: proof-critical mutation
  filter.
- `tests/mutation/filter_document_model_payload_work_items.py`:
  DOCUMENT-MODEL-PAYLOAD-P2 mutation filter.
- `tests/mutation/filter_document_load_style_prepass_work_items.py`:
  DOCUMENT-LOAD-STYLE-PREPASS-P2 mutation filter.

Incoming dependencies:

- `DocumentSVG` and `DocumentPDF` inherit the base document page model.
- SVG and PDF renderers iterate pages from `1` through `self.pages`.
- Existing examples, recipes, and tests use `Document.page()` and
  `Document.add_page()`.
- YAML round trips hydrate pages through `Document.create_from_dict()` and
  `Layers.create_from_dict()`.

Outgoing dependencies:

- The document model depends on `Canvas`, `Layer`, `Layers`, `ComponentGroup`,
  and project exceptions.
- PDF live-path proof depends on `DocumentPDF`, `ComponentGroupPDF`, and
  built-in PDF components.
- No renderer-specific dependency was added to `document.py`.

Before/after edge changes:

- Before this slice, page positions `0`, booleans, and invalid negative values
  could reach internal page mutation or lookup paths.
- Before this slice, `Document.add_page()` accepted `Layers` objects with
  incompatible canvases.
- Before this slice, `Layers.create_from_dict()` built a default base layer and
  then added serialized layers, leaving a hidden extra layer in hydrated pages.
- Before DOCUMENT-MODEL-PAYLOAD-P2, malformed `Layer`, `Layers`, and `Document`
  serialized roots and collection fields could fail through incidental lookup,
  subscription, or downstream iteration errors.
- Before DOCUMENT-MODEL-PAYLOAD-P2, `Layer.create_from_dict()` could begin
  component-group hydration before proving every serialized group had matching
  collision settings.
- Before DOCUMENT-MODEL-STYLES-MAPPING-P2, malformed document-model `styles`
  caches could fail through incidental `.keys()` lookups inside component-group
  hydration.
- After this slice, page positions are explicitly one-based, `-1` remains the
  append sentinel, inserted pages must share the document canvas contract, and
  hydrated layers match serialized layers without a constructor-created ghost
  layer.
- After DOCUMENT-MODEL-PAYLOAD-P2, document-model hydration validates payload
  envelopes and collection types before nested object construction.
- After DOCUMENT-MODEL-STYLES-MAPPING-P2, `Layer.create_from_dict()`,
  `Layers.create_from_dict()`, `Document.create_from_dict()`, and
  `Document.load()` require the style cache to be a mutable mapping or `None`
  before component-group hydration can mutate it.
- Before DOCUMENT-LOAD-STYLE-PREPASS-P2, `Document.load()` ran a legacy
  `_iterdict()` style prepass before `Document.create_from_dict()`. The prepass
  raw-indexed nested style envelopes, missed valid saved-document style
  payloads, and attempted dynamic module dispatch outside the existing
  hardened component/style factory path.
- Before DOCUMENT-MODEL-IDENTIFIER-P2, layer and component-group lookup/removal
  identifiers used Python `int` checks that accepted booleans, so `True` could
  alias integer id `1`.
- After DOCUMENT-LOAD-STYLE-PREPASS-P2, `Document.load()` reads YAML, validates
  the optional caller style cache, and delegates the loaded object directly to
  `Document.create_from_dict()`, so malformed YAML roots fail at the documented
  document factory boundary and valid nested style hydration remains owned by
  `ComponentGroup.create_from_dict()` and style factories.
- After DOCUMENT-MODEL-IDENTIFIER-P2, public layer and component-group
  identifier paths reject booleans before integer-id lookup or removal.

Cycle/layer/coupling/redundancy result:

- Cycle check: no cycle is introduced.
- Layer check: page/layer ownership remains in `document.py`; renderers only
  consume the document contract.
- Coupling check: no new renderer edge is added to the document model.
- Redundancy check: shared position validation helpers avoid duplicate
  add/remove/page checks.

ADR/rule impact:

- No new ADR is required. This reinforces the dependency-map rule that document
  model code owns pages, layers, containment, and boundary contracts.

## Domain Definitions

- InkGen document pages are one-based.
- `Document.add_page(position=-1)` appends.
- `Document.add_page(position=n)` inserts before existing page `n` where
  `1 <= n <= pages`.
- `Document.remove_page(n)` and `Document.page(n)` require an existing page
  where `1 <= n <= pages`.
- Booleans are not page numbers.
- Booleans are not layer ids or component-group ids.
- Inserted `Layers` pages must have the same canvas height, width, and units as
  the document.
- Serialized layers hydrate exactly the layers in the payload.
- Serialized `Layer`, `Layers`, and `Document` roots must be mappings with
  `Layer`, `Layers`, and `Document` mapping payloads.
- `Document.pages` and `Layer.component_groups` must be non-string sequences.
- `Layers.layers` and `Layer.group_collision_settings` must be mappings.
- `Layer.group_collision_settings` must include every serialized component
  group label.
- Each layer collision-setting entry must be a mapping with `allow_collision`
  and `strict` fields.

## Fix Log

- Added page insertion and existing-page validation helpers.
- Hardened add/remove/lookup page paths against zero, booleans, non-integers,
  and invalid negative values.
- Added document-page canvas compatibility validation.
- Simplified page removal into one shifting algorithm for all valid positions.
- Removed the auto-created base layer during `Layers.create_from_dict()` before
  hydrating serialized layers.
- Updated docs examples from zero-based page access to one-based page access.
- For DOCUMENT-MODEL-PAYLOAD-P2, added shared serialized payload helpers,
  explicit root/collection validation for `Layer`, `Layers`, and `Document`,
  and a layer collision-setting completeness check.
- For DOCUMENT-MODEL-STYLES-MAPPING-P2, added `_style_cache()` to validate
  mutable style caches at every document-model hydration entry point.
- For DOCUMENT-LOAD-STYLE-PREPASS-P2, removed the legacy `_iterdict()` style
  prepass and dynamic dispatch from `Document.load()`.
- For DOCUMENT-MODEL-IDENTIFIER-P2, added explicit boolean rejection to layer
  and component-group identifier lookups before Python integer aliasing can
  select or remove the wrong object.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid append and insertion | Preserve one-based order | PO-DOCM-001 | `test_document_page_insert_rejects_invalid_positions_and_booleans` | killed |
| Invalid insert positions | Reject zero, invalid negatives, booleans, and non-integers | PO-DOCM-002 | `test_document_page_insert_rejects_invalid_positions_and_booleans` | killed |
| Invalid remove/lookup positions | Reject missing and malformed page numbers | PO-DOCM-003 | `test_document_page_remove_and_lookup_reject_invalid_positions` | killed |
| Incompatible page canvas | Reject mismatched width, height, or units | PO-DOCM-004 | `test_document_rejects_pages_with_incompatible_canvas` | killed |
| Serialized page/layer hydration | Preserve payload layers without ghost base layers | PO-DOCM-005 | `test_document_serialization_preserves_one_based_page_order` | killed |
| PDF live path | Render through one-based document page contract | PO-DOCM-006 | `test_document_page_contract_remains_live_through_pdf_render_path` | behavioral evidence |
| Serialized document/layer payload envelopes | Reject malformed roots and collection fields before downstream hydration | PO-DOCM-007 | `test_document_model_hydration_rejects_malformed_payload_envelopes`, `test_layer_hydration_requires_collision_settings_for_each_group` | killed |
| Style cache boundary | Reject non-mutable `styles` caches before component-group hydration | PO-DOCM-008 | `test_document_model_hydration_rejects_malformed_style_caches`, `test_document_load_rejects_malformed_style_cache` | killed |
| YAML load style prepass | Delegate YAML payloads directly to hardened document hydration and avoid dynamic style prepass dispatch | PO-DOCM-009 | `test_document_load_populates_styles_through_validated_hydration`, `test_document_load_delegates_malformed_yaml_to_document_factory` | mutation target |
| Layer and group identifier boundaries | Reject boolean ids before Python integer aliasing can select or remove layers/groups | PO-DOCM-010 | `test_layer_rejects_boolean_component_group_identifiers_before_integer_aliasing`, `test_layer_rejects_malformed_component_group_lookup_identifiers`, `test_layers_rejects_boolean_layer_identifiers_before_integer_aliasing` | killed |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Page validation and canvas compatibility are deterministic. | DOCUMENT-MODEL-P1 tests |
| Behavioral/condition | yes | DOCUMENT-MODEL-P1 defines public document model behavior. | Tests are marked `@pytest.mark.condition("DOCUMENT-MODEL-P1")`, `@pytest.mark.condition("DOCUMENT-MODEL-PAYLOAD-P2")`, `@pytest.mark.condition("DOCUMENT-MODEL-STYLES-MAPPING-P2")`, and `@pytest.mark.condition("DOCUMENT-LOAD-STYLE-PREPASS-P2")`. |
| Failure-mode | yes | Bad page numbers, incompatible pages, malformed payloads, malformed YAML roots, and malformed style caches must fail before mutation/rendering/hydration. | Invalid position, incompatible canvas, payload, load-delegation, and style-cache tests |
| Integration/live-path | yes | `DocumentPDF` consumes the base document page contract. | PDF live-path test |
| Contract/API compatibility | yes | Existing document, SVG, and PDF tests must continue passing. | Focused gate includes existing tests |
| Property/fuzz | no | This slice covers finite page-index partitions directly. | Not applicable |
| Mutation | yes | Page guards, shifting, hydration, and canvas checks are proof-critical. | Mutation result recorded below |
| Security/adversarial | no | No new file path, network, subprocess, auth, SQL, template, or active-content surface is added. | Not applicable |
| Performance/resource | no | Page shifting is linear in page count and unchanged in complexity. | Code inspection |
| Concurrency/race | no | No shared state, background workers, locks, or temp files are added. | Not applicable |
| Golden artifact/visual | yes | PDF rendering must still emit a valid page from the one-based path. | PDF byte prefix and page-object assertion |
| Regression | yes | This closes page-zero corruption and serialized ghost-layer behavior. | DOCUMENT-MODEL-P1 tests |
| Serialized payload adversarial input | yes | Malformed public hydration payloads must fail before incidental downstream errors. | DOCUMENT-MODEL-PAYLOAD-P2 tests |
| Style-cache adversarial input | yes | Non-mutable style caches must fail before incidental downstream `.keys()` or item-assignment errors. | DOCUMENT-MODEL-STYLES-MAPPING-P2 tests |
| YAML load adversarial input | yes | `Document.load()` must not run a separate raw-indexing style prepass before the hardened document factory. | DOCUMENT-LOAD-STYLE-PREPASS-P2 tests |
| Identifier adversarial input | yes | Python booleans are integers and can alias ids without explicit rejection. | DOCUMENT-MODEL-IDENTIFIER-P2 tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Allowing invalid page positions must fail position-boundary tests.
- Breaking page insertion shifting must fail page-order tests.
- Breaking page removal shifting must fail remove/lookup tests.
- Weakening page canvas compatibility must fail mismatch tests.
- Keeping the constructor-created base during hydration must fail serialized
  round-trip tests.
- Weakening layer or component-group boolean identifier rejection must fail
  identifier-boundary tests.

Current result:

- Cosmic Ray 8.4.6, scoped to executable DOCUMENT-MODEL-P1 rows: 137 work
  items, 134 killed, and 3 documented equivalent survivors.
- Equivalent survivors:
  - `add_page`: `page_number == -1` changed to `page_number is -1`.
  - `add_page`: `page_number == -1` changed to `page_number <= -1`.
  - `_validate_insert_position`: `position == -1` changed to
    `position is -1`.
- Equivalence proof: `_validate_insert_position()` returns only `-1` or a
  positive integer in `[1, pages]`; all other negative values are rejected
  before `add_page()` branches. Therefore `== -1`, `is -1` on CPython's small
  integer sentinel, and `<= -1` are behaviorally identical inside the declared
  add-page branch domain.

DOCUMENT-MODEL-PAYLOAD-P2 current result:

- Cosmic Ray 8.4.6, scoped to executable DOCUMENT-MODEL-PAYLOAD-P2 rows: 24
  work items, 24 killed, 0 survivors.
- Focused dependent-path tests:
  `python -m pytest -q tests\test_document_model_contract.py tests\test_document.py tests\test_pdf_generator.py tests\test_svg_generator.py`
  returned `96 passed`.
- Full coverage gate:
  `python -m pytest --cov=src/InkGen --cov-branch --cov-report=term -q`
  returned `609 passed` with `93%` coverage.
- Ruff lint and format passed for touched Python files.
- MkDocs strict build passed.

DOCUMENT-MODEL-STYLES-MAPPING-P2 current result:

- Focused tests: `102 passed`.
- Mutation: `4` proof-critical work items, `4 killed`, `0 survivors`.
- Full coverage gate: `822 passed`, total coverage `94%`.
- Ruff lint and format passed for touched Python files.

DOCUMENT-LOAD-STYLE-PREPASS-P2 current result:

- Focused tests before full gate: `48 passed`.
- Mutation: `4` proof-critical work items, `4 killed`, `0 survivors`.
- Full coverage gate: `1424 passed`, total coverage `95%`.
- Mutation config: `tests/mutation/document_load_style_prepass_cosmic_ray.toml`.
- Mutation filter:
  `tests/mutation/filter_document_load_style_prepass_work_items.py`.

DOCUMENT-MODEL-IDENTIFIER-P2 current result:

- Cosmic Ray 8.4.6, scoped to layer and component-group boolean identifier
  guards: 5 work items, 5 killed, 0 survivors.

## PO-DOCM-001: Valid Page Insertions Preserve One-Based Order

### Claim

Appending and inserting pages preserves one-based page order.

### Domain

`Document.add_page(position=-1)` and `Document.add_page(position=n)` where
`1 <= n <= pages`.

### Proof Method

The validation helper constrains valid insert positions. The focused test
inserts at the first, middle, and current last positions and checks page order.

### Conclusion

Proven for the stated domain after tests and mutation pass with documented
equivalent survivors.

## PO-DOCM-002: Invalid Insert Positions Fail

### Claim

`Document.add_page()` rejects page positions outside `-1` or existing one-based
positions.

### Domain

Public add-page calls with zero, invalid negative values, booleans,
non-integers, and out-of-range positive positions.

### Proof Method

`_validate_insert_position()` rejects malformed values before `_pages` is
mutated. Focused tests assert invalid values fail and valid values preserve
order.

### Conclusion

Proven for the stated domain after tests and mutation pass with documented
equivalent survivors.

## PO-DOCM-003: Existing Page Operations Require Existing Pages

### Claim

`Document.page()` and `Document.remove_page()` reject missing or malformed page
positions and preserve order after removal.

### Domain

Public lookup and removal calls.

### Proof Method

`_validate_existing_position()` rejects malformed values before lookup or
shifting. Page removal uses one shifting path for first, middle, and last page
positions.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-DOCM-004: Inserted Pages Must Share The Document Canvas

### Claim

`Document.add_page(page=...)` rejects `Layers` pages whose canvas height, width,
or units differ from the document canvas.

### Domain

Explicit `Layers` pages passed into `Document.add_page()`.

### Proof Method

`_page_canvas_compatibility()` compares `(height, width, units)` tuples before
storing the page. Focused tests cover width, height, and unit mismatches.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-DOCM-005: Hydrated Layers Match Serialized Layers

### Claim

`Layers.create_from_dict()` hydrates exactly the serialized layers and does not
retain an automatically created constructor layer.

### Domain

Serialized `Layers.parameters` payloads created by InkGen.

### Proof Method

Hydration constructs a temporary `Layers` object, removes its default layer,
and then adds only payload layers. The focused round-trip test checks page order
and exact parameters.

### Conclusion

Proven for the stated domain after tests and mutation pass.

## PO-DOCM-006: PDF Rendering Uses The Page Contract

### Claim

`DocumentPDF` renders through the one-based base document page path.

### Domain

Documents containing PDF-native component groups.

### Proof Method

The live-path test adds a page, inserts a PDF group through `page(1)`, and
checks generated PDF bytes.

### Conclusion

Supported by behavioral evidence for the stated domain.

## PO-DOCM-007: Serialized Payload Envelopes Fail Explicitly

### Claim

`Layer.create_from_dict()`, `Layers.create_from_dict()`, and
`Document.create_from_dict()` reject malformed serialized roots and collection
fields before downstream hydration can produce incidental errors.

### Domain

Public hydration calls with non-mapping roots, missing root keys, non-mapping
payloads, string or non-sequence page/group collections, non-mapping layer maps,
and incomplete layer collision settings.

### Proof Method

Shared helpers validate payload root shape, required fields, mapping fields, and
non-string sequence fields before nested object construction. Focused condition
tests cover malformed roots, malformed collection fields, and missing collision
settings for a serialized component group.

### Conclusion

Supported by focused dependent-path tests, mutation testing, full coverage
tests, and MkDocs strict build for the stated domain.

## PO-DOCM-008: Style Caches Are Mutable Mappings

### Claim

Document-model hydration rejects malformed `styles` caches before
component-group hydration can use `.keys()` or item assignment.

### Domain

Public `Layer.create_from_dict(data, styles=...)`,
`Layers.create_from_dict(data, styles=...)`, `Document.create_from_dict(data,
styles=...)`, and `Document.load(filepath, styles=...)` calls where `styles` is
`None`, a mutable mapping, or a malformed non-mutable value.

### Proof Method

Each public document-model hydration entry point calls `_style_cache()` before
delegating into nested layer or component-group hydration. `_style_cache()`
creates a fresh dictionary for `None`, accepts mutable mappings, and rejects
arbitrary objects, strings, bytes, sets, and sequences before any downstream
style lookup or cache mutation. Focused condition tests cover direct
`Layer`/`Layers`/`Document` hydration and YAML `Document.load()`.

### Counterexamples And Exclusions

Validation of individual style payload shapes remains owned by component-group
and style factory contracts. Private mutation of the style cache after
validation is outside the public hydration boundary.

### Conclusion

Supported by focused document-model and renderer-path tests, scoped mutation
testing, and the full coverage gate for the stated style-cache boundary.

## PO-DOCM-009: Document Load Delegates To Hardened Hydration

### Claim

`Document.load()` does not run a separate raw-indexing or dynamic-dispatch style
prepass before document hydration. Loaded YAML payloads are delegated to
`Document.create_from_dict()` after style-cache validation.

### Domain

Public `Document.load(filepath, styles=...)` calls for YAML files that parse to
valid saved InkGen documents, malformed non-mapping roots, and mapping roots
that are not `Document` payloads.

### Proof Method

`Document.load()` reads the YAML file, calls `_style_cache()` on the optional
style cache, and then calls `Document.create_from_dict(document_data, styles)`.
The removed `_iterdict()` prepass no longer performs raw nested style-envelope
indexing or dynamic `getattr()` dispatch. Focused condition tests prove valid
documents still round-trip and populate styles through nested component-group
hydration, while malformed YAML roots now fail with the same explicit
document-factory errors as direct `Document.create_from_dict()` calls.

### Counterexamples And Exclusions

YAML parser syntax errors, file-not-found errors, and private mutation of the
returned style cache are outside this load-delegation slice. Individual nested
style payload validation remains owned by component-group and style factory
contracts.

### Conclusion

Supported by focused load-delegation tests, scoped mutation evidence, and the
full coverage gate for the stated load-delegation domain.

## PO-DOCM-010: Layer And Group Identifiers Reject Boolean Aliases

### Claim

Layer and component-group identifier APIs reject booleans before Python's
`bool`-is-`int` relationship can select or remove an object by integer id.

### Domain

Public `Layer.group(group_id)`, `Layer.remove_component_group(group_id)`,
`Layers.layer(identifier)`, and `Layers.remove_layer(identifier)` calls.

### Dependencies

- `Layer.remove_component_group()`
- `Layer.group()`
- `Layers._layer_identification_lookup()`
- `Layers.layer()`
- `Layers.remove_layer()`

### Proof Method

`Layer.group()` rejects values that are not non-boolean integers before reading
`_component_groups`. `Layer.remove_component_group()` rejects boolean values
before string-label resolution or integer-id removal. `Layers` centralizes
lookup for `layer()` and `remove_layer()` through
`_layer_identification_lookup()`, which now rejects booleans before name/id
matching. Focused tests prove booleans fail without removing existing objects,
malformed group lookup identifiers fail before dictionary lookup, and valid
integer/name identifiers continue to work.

### Counterexamples And Exclusions

This proof does not change the public contract that component-group labels and
layer names are strings. Missing integer ids still raise the existing invalid-id
errors. Document page positions are covered separately by PO-DOCM-001 through
PO-DOCM-003.

### Conclusion

Focused tests and mutation cover the boolean aliasing partitions. Full
coverage, lint, docs, and diff hygiene remain release-gate checks for the
slice.
