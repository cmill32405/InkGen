# Document Model Contract Proof Obligations

This note applies the InkGen Definition of Done to the DOCUMENT-MODEL-P1
document model slice. It focuses on one-based page indexing, page insertion and
removal boundaries, page canvas compatibility, serialized page hydration, and
live use through PDF rendering.

## Scope

The slice covers:

- `Layers.create_from_dict()`
- `Document.add_page()`
- `Document.remove_page()`
- `Document.page()`
- `Document._validate_insert_position()`
- `Document._validate_existing_position()`
- `Document._page_canvas_compatibility()`

## Architecture Impact

Affected surface:

- `src/InkGen/document.py`: page validation, page insertion/removal, and
  serialized layer hydration.
- `docs/api-reference.md`, `docs/components/document-structure.md`, and
  `docs/examples.md`: one-based page examples.
- `tests/test_document_model_contract.py`: DOCUMENT-MODEL-P1 behavioral and
  live-path tests.
- `tests/mutation/document_model_cosmic_ray.toml`: scoped mutation gate.
- `tests/mutation/filter_document_model_work_items.py`: proof-critical mutation
  filter.

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
- After this slice, page positions are explicitly one-based, `-1` remains the
  append sentinel, inserted pages must share the document canvas contract, and
  hydrated layers match serialized layers without a constructor-created ghost
  layer.

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
- Inserted `Layers` pages must have the same canvas height, width, and units as
  the document.
- Serialized layers hydrate exactly the layers in the payload.

## Fix Log

- Added page insertion and existing-page validation helpers.
- Hardened add/remove/lookup page paths against zero, booleans, non-integers,
  and invalid negative values.
- Added document-page canvas compatibility validation.
- Simplified page removal into one shifting algorithm for all valid positions.
- Removed the auto-created base layer during `Layers.create_from_dict()` before
  hydrating serialized layers.
- Updated docs examples from zero-based page access to one-based page access.

## Comprehensiveness Matrix

| Domain class | Handling | Proof obligation | Test evidence | Mutation status |
|---|---|---|---|---|
| Valid append and insertion | Preserve one-based order | PO-DOCM-001 | `test_document_page_insert_rejects_invalid_positions_and_booleans` | killed |
| Invalid insert positions | Reject zero, invalid negatives, booleans, and non-integers | PO-DOCM-002 | `test_document_page_insert_rejects_invalid_positions_and_booleans` | killed |
| Invalid remove/lookup positions | Reject missing and malformed page numbers | PO-DOCM-003 | `test_document_page_remove_and_lookup_reject_invalid_positions` | killed |
| Incompatible page canvas | Reject mismatched width, height, or units | PO-DOCM-004 | `test_document_rejects_pages_with_incompatible_canvas` | killed |
| Serialized page/layer hydration | Preserve payload layers without ghost base layers | PO-DOCM-005 | `test_document_serialization_preserves_one_based_page_order` | killed |
| PDF live path | Render through one-based document page contract | PO-DOCM-006 | `test_document_page_contract_remains_live_through_pdf_render_path` | behavioral evidence |

## Test Applicability Matrix

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| Unit | yes | Page validation and canvas compatibility are deterministic. | DOCUMENT-MODEL-P1 tests |
| Behavioral/condition | yes | DOCUMENT-MODEL-P1 defines public document model behavior. | Tests are marked `@pytest.mark.condition("DOCUMENT-MODEL-P1")`. |
| Failure-mode | yes | Bad page numbers and incompatible pages must fail before mutation/rendering. | Invalid position and incompatible canvas tests |
| Integration/live-path | yes | `DocumentPDF` consumes the base document page contract. | PDF live-path test |
| Contract/API compatibility | yes | Existing document, SVG, and PDF tests must continue passing. | Focused gate includes existing tests |
| Property/fuzz | no | This slice covers finite page-index partitions directly. | Not applicable |
| Mutation | yes | Page guards, shifting, hydration, and canvas checks are proof-critical. | Mutation result recorded below |
| Security/adversarial | no | No new file path, network, subprocess, auth, SQL, template, or active-content surface is added. | Not applicable |
| Performance/resource | no | Page shifting is linear in page count and unchanged in complexity. | Code inspection |
| Concurrency/race | no | No shared state, background workers, locks, or temp files are added. | Not applicable |
| Golden artifact/visual | yes | PDF rendering must still emit a valid page from the one-based path. | PDF byte prefix and page-object assertion |
| Regression | yes | This closes page-zero corruption and serialized ghost-layer behavior. | DOCUMENT-MODEL-P1 tests |

## Mutation Testing Gate

Proof-critical mutation targets:

- Allowing invalid page positions must fail position-boundary tests.
- Breaking page insertion shifting must fail page-order tests.
- Breaking page removal shifting must fail remove/lookup tests.
- Weakening page canvas compatibility must fail mismatch tests.
- Keeping the constructor-created base during hydration must fail serialized
  round-trip tests.

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
