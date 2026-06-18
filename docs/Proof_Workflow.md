# Proof Workflow

This document explains how to execute the Development Standard and Definition
of Done during an InkGen slice. The standard says what must be true before work
is done. This workflow says how to get there without relying on memory,
optimism, or a happy-path test.

The goal is to force each implementation into a shape where the claim is small,
the domain is explicit, dependencies are understood, and failures are caught
before the slice is called complete.

## Core Rule

Do not start by coding. Start by turning the requested work into a proof
obligation.

Every slice should answer:

1. What exact result are we trying to guarantee?
2. For which inputs, states, formats, and callers does that guarantee apply?
3. What is excluded?
4. What dependencies and contracts can this change break?
5. What evidence or proof would catch the old behavior if it returned?

If those answers are not clear, the slice is not ready for implementation.

## Stage 1: Select The Slice

Pick one bounded behavior, not a broad subsystem. A good slice has a clear
public contract and a clear blast radius.

Examples:

- `TEXT-P1`: text position and renderer output contract.
- `TABLE-P1`: table numeric geometry and table renderer contract.
- `FLOW-DOCUMENT-P1`: flow-document block ordering and deterministic DOCX
  output.

For each slice, write a short scope statement:

```text
Slice:
- TABLE-P1

Intent:
- Tables must reject invalid geometry before SVG or document export.

Out of scope:
- Table auto-layout algorithm redesign.
- New document formats.
```

## Stage 2: Read Before Acting

Before editing files, read the source and tests that define the current
contract. Do not trust memory, generated docs, or a prior agent summary when a
direct read is possible.

Read at least:

- The implementation file being changed.
- Existing tests for that behavior.
- Public exports or factory paths.
- Renderers, serializers, parsers, or downstream consumers that depend on the
  contract.
- Architecture docs, dependency maps, and ADRs that constrain the area.

Record the read list in the proof note or report-out. This matters because many
agent failures come from changing a helper without checking who depends on it.

## Stage 3: Dependency And Contract Review

Before implementation, map the dependency impact.

Use this template:

```text
Dependency review:
- Affected surface:
- Incoming dependencies:
- Outgoing dependencies:
- Public contract:
- Serialized/artifact contract:
- Before/after edge changes:
- Cycle/layer/coupling/redundancy result:
- ADR/rule impact:
- Expected blast radius:
```

Key questions:

- Who imports, calls, serializes, renders, parses, or documents this artifact?
- What behavior, input shape, output shape, exception, side effect, coordinate
  frame, or file format does each caller rely on?
- Does the change move responsibility across a layer boundary?
- Does it duplicate an existing rule or create a second source of truth?
- Would saved parameters, fixture bytes, truth records, or public examples
  change?

If a dependency is affected, add at least one dependent-path test. Testing only
the changed helper is not enough.

## Stage 4: Define Proof Obligations

A proof obligation is a precise claim that must be supported or proven before
the slice is done.

Use this format:

```text
PO-ID:
- PO-TABLE-003

Claim:
- Row heights and column widths are finite non-negative numbers.

Domain:
- Table.add_row(), Table.add_column(), Row.height, Column.width, and table
  hydration through create_from_dict().

Assumptions:
- Python float conversion is the numeric coercion boundary.
- Boolean values are excluded even though bool subclasses int.

Theorem:
- For all values accepted by the public table dimension boundaries, stored
  dimensions are finite floats greater than or equal to zero. All other tested
  malformed, boolean, negative, and non-finite values raise.

Proof method:
- Boundary validation in one shared helper.
- Behavioral tests over valid and invalid domain partitions.
- Mutation testing over proof-critical validation branches.

Counterexamples and exclusions:
- Hostile private mutation of internal attributes is excluded.
```

Do not call a test result a proof by itself. A test result is evidence.
Mathematical proof requires a universal claim over a stated domain and a proof
method that covers every case in that domain.

## Stage 5: Partition The Domain

Comprehensive testing starts with naming the domain partitions. For most InkGen
slices, use these default partitions:

| Partition | Examples |
|---|---|
| Normal valid values | Typical geometry, text, styles, tables, documents |
| Minimum valid values | Zero width when allowed, empty text when allowed, first page |
| Boundary values | Page height flips, bbox edges, enum transitions, padding length |
| Invalid types | `None`, `object()`, strings, booleans where numeric values are expected |
| Invalid numeric values | `nan`, `inf`, negative values, zero when positive is required |
| Serialization | `parameters`, `create_from_dict`, JSON/truth records |
| Dependent path | SVG, PDF, DXF, DOCX, parser, or flow-document path |
| Legacy compatibility | Existing tests and examples that must keep working |
| Exclusions | Private mutation, unsupported formats, hostile monkey-patching |

Then map every partition:

```text
Comprehensiveness:
- Valid table geometry: preserved; live SVG and FlowDocument test.
- Invalid origins: rejected; TABLE-P1 failure test.
- Invalid dimensions: rejected; TABLE-P1 failure test and mutation.
- Private _width mutation: excluded; private state is not public API.
```

The goal is not infinite tests. The goal is no silent assumptions.

## Stage 6: Implement The Smallest Contract Change

Make the proof smaller by making the code simpler.

Preferred implementation shape:

- One validation helper for one repeated rule.
- Public constructors and setters share that helper.
- Renderers consume authoring-model contracts instead of duplicating them.
- Error behavior is explicit and tested.
- No new dependency is introduced unless approved.
- No unrelated formatting or refactor churn is mixed into the slice.

When a proof is hard, first ask whether the code can be simplified until the
proof is easy. Complex code is often a sign that the claim is too broad or the
responsibility is in the wrong place.

## Stage 7: Write Tests By Risk Surface

Every slice needs condition-marked behavioral tests. Other test classes depend
on the change surface.

| Test class | Use when | Expected evidence |
|---|---|---|
| Unit | Pure helper, validation, value object, deterministic calculation | Direct normal and invalid cases |
| Behavioral/condition | Any design condition or proof obligation changes | `@pytest.mark.condition("ID")` |
| Failure-mode | Bad input, missing dependency, unsupported option, malformed payload | Exception, log, or preserved-state assertion |
| Integration/live-path | Behavior crosses modules or output formats | Public caller or downstream path test |
| Contract/API compatibility | Public signatures, serialized data, fixture bytes, or old behavior could break | Round trip, old-caller regression, existing tests |
| Property/fuzz | Broad numeric, parser, geometry, ordering, or invariant space | Property test or exhaustive finite-domain proof |
| Mutation | Proof-critical guards, formulas, dispatch, serialization, or truth output changed | Automated mutation report |
| Security/adversarial | Untrusted input, paths, archives, subprocesses, active content, secrets | Security regression or explicit exclusion |
| Performance/resource | Large documents, many components, caches, loops | Bound, benchmark, timeout, or reasoned exclusion |
| Golden artifact/visual | SVG, PDF, DXF, DOCX, JSON truth, diagrams | Deterministic artifact or parsed output comparison |

For a narrow code slice, the test file should prove:

- The new valid behavior works.
- The old broken behavior fails.
- The failure mode fails at the correct boundary.
- At least one real dependent path still works.

## Stage 8: Mutation Testing

Run mutation testing on proof-critical code, not necessarily the entire repo.

Mutation is required when the slice changes:

- Validation guards.
- Coordinate or geometry formulas.
- Dispatch rules.
- Serialization or hydration.
- Deterministic output.
- Parser/generator truth data.
- Any branch used by a proof obligation.

The workflow:

1. Create a mutation config for the touched source paths.
2. Filter work items to proof-critical rows.
3. Run the normal focused tests as the mutation test command.
4. Classify every survivor:
   - Test gap: add a test and rerun.
   - Equivalent: document why it is equivalent within the declared domain.
   - Out of scope: point to the domain exclusion.
   - Tool/config invalid: fix the config and rerun.

The gate passes only when no proof-critical, non-equivalent survivor remains.

Report mutation like this:

```text
Mutation:
- Tool/version: Cosmic Ray 8.4.6
- Mutated source paths: src/InkGen/table.py, src/InkGen/svg_generator.py
- Test selection: TABLE-P1 focused tests plus dependent table/render/document tests
- Work items: 47
- Killed: 47
- Survived: 0
- Excluded/equivalent: type-annotation-only mutants excluded
- Gate result: PASS
```

## Stage 9: Write The Proof Note

Every completed proof slice should have a proof note under `docs/proofs/`.

Use this structure:

1. Title and purpose.
2. Scope.
3. Public behavior under review.
4. Architecture impact.
5. Domain definitions.
6. Fix log.
7. Comprehensiveness matrix.
8. Test applicability matrix.
9. Mutation testing gate.
10. One section per proof obligation.
11. Residual risk.

The proof note is not a narrative justification after the fact. It is the
traceable record connecting contract, dependencies, tests, mutation, and
remaining risk.

## Stage 10: Run The Gate

Run the smallest focused gate first, then the full gate.

Typical focused gate:

```powershell
python -m pytest tests\test_table_contract.py tests\test_table.py -q
python -m ruff check <touched-python-files>
python -m ruff format --check <new-or-format-clean-python-files>
```

Typical full gate:

```powershell
python -m pytest --cov=src\InkGen --cov-branch -q
mkdocs build --strict
git -c safe.directory=C:/Users/chris/Documents/Code/InkGen diff --check
```

When `mkdocs build --strict` regenerates `site/`, restore generated output
before staging unless the generated files are intentionally part of the change:

```powershell
git -c safe.directory=C:/Users/chris/Documents/Code/InkGen restore -- site
```

If legacy files fail formatter checks because the whole file predates the
formatter, do not silently reformat the world. Either keep the change scoped and
report the legacy format exception, or explicitly choose a formatting-only slice.

## Stage 11: Final Report

The report should be factual, evidence-based, and specific. Use PASS/FAIL, not
vague confidence language.

Example:

```text
- PASS: Pre-change dependency/contract review
- PASS: TABLE-P1 condition tests added
- PASS: Failure-mode tests for malformed, boolean, non-finite, and negative geometry
- PASS: Shared Table/TableSVG padding contract tested
- PASS: Serialized table hydration rejects invalid geometry
- PASS: SVG and flow-document live paths tested
- PASS: Mutation testing: 47 mutants, 47 killed, 0 survived
- PASS: Full tests: 351 passed
- PASS: Coverage: 92%
- PASS: Ruff lint for touched Python files
- PASS: MkDocs strict build
- PASS: git diff --check
```

If a check did not run, say so. If a check failed and was waived, say who waived
it and what residual risk remains.

## Stage 12: Commit, Push, And Record

Before committing:

- Review `git status --short`.
- Stage only files in the slice.
- Do not stage unrelated handoff files, generated output, cache files, or user
  work.
- Check `git diff --cached --stat`.

After committing:

- Push the branch.
- Record the proof result in Clarvis or the project notes with:
  - Slice ID.
  - Commit hash.
  - Files changed.
  - Test count and coverage.
  - Mutation result.
  - Residual risks.

## Control-Agent Checklist

Use this checklist when reviewing another agent's work:

- Is the slice small enough to reason about?
- Did the agent read the actual code and dependency docs before editing?
- Are incoming and outgoing dependencies listed?
- Is the public contract explicit?
- Are proof obligations stated as universal claims over a domain?
- Are exclusions named instead of implied?
- Do tests cover the failure mode, not just the happy path?
- Is there at least one dependent-path test when a contract changes?
- Did mutation testing run on proof-critical logic?
- Are survivors classified correctly?
- Does the proof note match the code and tests?
- Did full tests, coverage, lint, docs, and whitespace checks run?
- Is the final report honest about exceptions and residual risk?

## Performance-Agent Checklist

Use this checklist while implementing:

- Declare scope and assumptions before editing.
- Read the implementation and existing tests.
- Search callers and serialized/documented contracts.
- Add or update condition-marked tests.
- Keep implementation small and dependency-neutral.
- Run focused tests after each meaningful edit.
- Run mutation before claiming proof-critical logic is done.
- Update proof docs before full-gate verification.
- Run full gate.
- Commit only the slice.

## What Not To Do

- Do not claim proof from source existence.
- Do not claim proof from one happy-path test.
- Do not use manual perturbation instead of mutation testing for proof-critical
  logic.
- Do not let an LLM judge replace executable checks.
- Do not add dependencies to make a test easy without approval.
- Do not make private assumptions about downstream callers; read them.
- Do not hide a failed or skipped gate in a summary.
- Do not mix cleanup/refactor/formatting churn with a proof slice unless that is
  the declared slice.
