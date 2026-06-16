# Definition of Done Checklist

This document is a working checklist for deciding whether an InkGen change is
actually done. It adapts the Clarvis proof standard to a library context: a
feature is not complete because code exists, or because a happy-path test passes.
It is complete only when the design intent, implementation behavior, failure
modes, live wiring, verification evidence, and proof obligations all line up.

This checklist is a proof-first working standard for this review. Its purpose is
to force code into shapes that are simple, bounded, deterministic,
dependency-aware, and mathematically defensible before the code is accepted.

The checklist is also a draft control surface for a two-agent workflow:

- **Control agent:** owns scope, requirements, review questions, proof quality,
  traceability, and the final done/not-done decision.
- **Performance agent:** owns implementation, local verification runs, evidence
  capture, and fixing issues found by the control agent.

## Evidence And Proof Model

Do not call evidence a proof. Evidence increases confidence that an
implementation works. Proof establishes that a precisely stated result follows
for all cases inside a stated domain under stated assumptions.

The default target is mathematical proof. If the implementation cannot support a
mathematical proof over the intended domain, narrow the claim, simplify the code,
or record the unproven part as residual risk. The preferred design is the one
that makes the proof small.

Use "proven" only when all of these are explicit:

1. **Domain:** the full set of inputs, states, artifacts, or execution paths the
   claim covers.
2. **Assumptions:** external facts the proof relies on, such as a file format
   guarantee, Python language rule, library contract, or bounded input range.
3. **Theorem:** the exact result claimed for every case in the domain.
4. **Proof method:** formal proof, algebraic reasoning, exhaustive enumeration,
   property-based counterexample search over a justified domain, or static path
   proof.
5. **Counterexample handling:** invalid inputs, excluded cases, and known limits
   are named.

If any of these are missing, report the item as "supported by evidence", not
"proven".

| Layer | Question | Output | Is this proof? |
|---|---|---|---|
| Structural evidence | Does the artifact exist? | Source file, class, function, export, docs, diagram | No. It proves only existence. |
| Behavioral evidence | Does it work for named scenarios? | Condition-marked tests | No. It shows examples and regressions. |
| Functional evidence | Is it wired into the real use path? | Integration test, example, public API, or call-path audit | No. It shows reachability. |
| Dependency evidence | Were affected contracts and dependent paths checked? | Dependency map review and dependent-path tests | No. It shows impact was reviewed. |
| Property proof candidate | Does an invariant hold across a broad or generated domain? | Property tests with domain and invariant stated | Sometimes. It is counterexample search unless exhaustive or backed by mathematical reasoning. |
| Static path proof candidate | Can a path-level noninterference or wiring claim be established from code structure? | Call graph or source audit tied to a theorem | Sometimes. It must cover all relevant paths and be stated as a theorem. |
| Formal proof | Can the result be derived from a model? | Z3, theorem prover, algebraic proof, or exhaustive finite-state model | Yes, if the model matches the stated domain. |

For most InkGen work, structural, behavioral, functional, and dependency
evidence are mandatory. Property proof candidates are required when behavior has
invariants such as coordinate transforms, serialization round trips,
deterministic output, geometry bounds, or idempotence. Core behavioral claims
must be rewritten until they are mathematically provable or explicitly accepted
as residual risk.

### Proof Obligation Template

Use this format for every claim described as proven:

```text
Claim:
- <one exact result>

Domain:
- <inputs/states/artifacts/paths covered>

Assumptions:
- <external facts and bounded conditions>

Theorem:
- For all <domain>, <result> holds.

Proof method:
- <formal model, algebraic reasoning, exhaustive enumeration, property search,
  static path proof>

Counterexamples and exclusions:
- <invalid cases, unsupported cases, known limits>

Conclusion:
- proven | supported by evidence | contradicted | unproven
```

Examples:

- "A test passed for three inputs" is behavioral evidence, not proof.
- "For all normalized bboxes `(x0, y0, x1, y1)` and canvas heights `H`, the PDF
  bbox conversion returns `[min_x, H - max_y, max_x, H - min_y]`; verified by
  algebraic reasoning and property tests over generated numeric cases" is a
  proof candidate.
- "Adding annotations does not change PDF bytes" is not proven by one byte
  comparison. It requires either a static path proof that rendering does not
  read annotation state, or a narrower conclusion: "supported by regression
  evidence for the tested document."

## Feature-Level Done

| Check | Control agent asks | Performance agent provides |
|---|---|---|
| Intent is clear | What problem does this solve? What is out of scope? | Short scope statement and exclusions |
| Design surface is identified | Which bounded context, module, API, or output format is affected? | File/module list and impacted public APIs |
| Existing behavior is understood | What code and tests were read before editing? | Read list, relevant findings, assumptions |
| Public contract is explicit | What can callers rely on? What can fail? | Docstrings, docs, examples, error semantics |
| Backward compatibility is considered | What existing users, parameters, files, or serialized data might break? | Compatibility notes and migration behavior |
| Failure modes are named | How does this fail, and what should the caller see? | Failure-mode tests and expected exceptions |
| Happy path is tested | Does the intended scenario work end to end? | Behavioral tests with condition markers |
| Edge cases are tested | What about empty inputs, invalid types, Unicode, bounds, missing files, duplicate names, or unsupported formats? | Targeted edge-case tests |
| Comprehensiveness is mapped | Which domain partitions, invariants, edge cases, and exclusions define "enough" coverage? | Comprehensiveness matrix mapping each class to proof, tests, or out-of-scope status |
| Live path is wired | Is the feature reachable through the real public API, not only by direct helper call? | Integration test, example, or call-path evidence |
| Determinism is checked | Does repeated generation produce stable bytes or stable records where expected? | Determinism test for generated artifacts or JSON |
| Output is inspectable | Can a human inspect the generated artifact or record? | Example output, JSON emit, diagram, or docs |
| No hidden dependency creep | Were new dependencies avoided or explicitly approved? | Dependency diff or statement that no dependency files changed |
| Dependency integrity is checked | What callers, suppliers, contracts, and artifacts can this change affect? | Dependency impact notes and at least one dependent-path test when a contract changes |
| Architecture impact is checked | Did the change add, remove, or redirect dependencies, layers, responsibilities, public contracts, or artifact flows? | Architecture impact notes, graph/source evidence, and updated rule or ADR when needed |
| ADR impact is checked | Does this change create, modify, or contradict an architecture decision? | New/updated ADR or statement that no ADR is affected |
| Complexity is justified | Is this the smallest design that satisfies the proven requirement? | Complexity review notes and any intentional simplicity/deferred-complexity comments |
| Test applicability is explicit | Which test classes are required by this change surface, and which are not applicable? | Test applicability matrix with evidence or reasoned exclusions |
| Verification gate passes | Do tests, lint, format, docs, and coverage pass? | Exact commands and summarized results |
| Residual risk is stated | What remains unproven or intentionally deferred? | Short residual-risk note |

## Dependency Integrity Done

Dependency mistakes are a common way for agents to break working code. A change
is not done until its dependency impact is understood.

| Check | Questions |
|---|---|
| Incoming dependencies | Who calls, imports, subclasses, serializes, parses, or documents this artifact? |
| Outgoing dependencies | What does this artifact call, import, instantiate, serialize, parse, or assume? |
| Contract relied on | What behavior, input shape, output shape, exception, side effect, coordinate frame, or artifact format does the caller rely on? |
| Dependency direction | Does the dependency direction match the intended architecture? |
| Abstraction boundary | Is high-level policy depending on stable abstractions rather than concrete renderer/parser/file-format details? |
| Blast radius | Which tests, examples, docs, generated files, and downstream consumers could be affected? |
| Substitution safety | If this class implements or extends another type, can it still be used anywhere the old contract was expected? |
| Serialization safety | Does the change affect saved parameters, JSON truth records, PDFs, SVG, DXF, DOCX, or fixtures? |
| Cycle check | Does the change introduce a new circular import, conceptual cycle, or bidirectional ownership? |
| Dependent-path proof | Was a real dependent caller tested, not only the changed helper in isolation? |
| Contract regression | Is there a test that would fail if the broken dependency contract returned? |

For InkGen, use these default dependency rules unless an ADR says otherwise:

| Layer | Dependency rule |
|---|---|
| Geometry/components | Own geometry and state; must not know concrete output formats. |
| Renderer backends | Depend on component contracts; must not mutate component semantics. |
| Document/page/layer model | Own containment and ordering; must preserve serialization contracts. |
| Truth emitters | Depend on annotations and rendered geometry; must not change rendered bytes. |
| Flow documents | Depend on paragraph, table, and drawing recipe contracts; should avoid renderer-specific coupling unless converting deliberately. |
| Downstream parser fixtures | Depend on stable bytes, coordinate frames, and truth schemas. |

### SOLID As Review Heuristics

SOLID is useful engineering guidance, not a rigid acceptance rule. Use it to
find dependency risks and then decide based on the local design.

| Principle | Dependency review question |
|---|---|
| Single Responsibility | Does this artifact have one reason to change, or is it mixing unrelated contracts? |
| Open/Closed | Can new supported formats or cases be added without editing stable callers? |
| Liskov Substitution | Can subclasses or implementations be used through the base contract without surprising callers? |
| Interface Segregation | Are callers forced to depend on methods, fields, or formats they do not use? |
| Dependency Inversion | Do high-level policies depend on abstractions instead of concrete low-level details? |

Violating a SOLID heuristic is not automatically wrong. It is a prompt to either
improve the design or document why the tradeoff is acceptable.

## Architecture Impact Done

Dependency evidence identifies edges. Architecture impact evidence decides
whether those edges still form the intended system. A change is not done until
its structural blast radius is bounded by source evidence, tests, and design
rules or ADRs.

| Check | Questions |
|---|---|
| Affected surface | Which modules, classes, functions, public APIs, docs, generated artifacts, fixtures, and tests are in the blast radius? |
| Incoming graph | Who imports, calls, subclasses, serializes, parses, renders, documents, or otherwise depends on this artifact? |
| Outgoing graph | What modules, types, files, formats, external libraries, and runtime assumptions does this artifact rely on? |
| Before/after structure | Did the change add an edge, remove an edge, move responsibility, redirect a public path, or alter layer direction? |
| Cycle check | Did the change introduce an import cycle, conceptual cycle, bidirectional ownership, or mutually dependent format contract? |
| Layer/forbidden-edge check | Does any dependency violate the dependency map, ADRs, or an explicit renderer/document/parser boundary? |
| Coupling/hub check | Did one module, class, or renderer become a high-degree hub, god object, or dumping ground for unrelated decisions? |
| Redundancy check | Did the change duplicate an existing component, rule, serializer, truth emitter, coordinate transform, or output contract? |
| Test-gap/hotspot check | Did the change touch weakly tested, frequently changed, proof-critical, security-sensitive, or parser-facing code? |
| Evidence source | Which edges came from AST/imports, direct code reads, tests, search, diagrams, memory, or inference? |
| Confidence/freshness | Are graph facts current and source-backed, or stale/inferred and therefore requiring a direct code read? |
| Rule/ADR update | Should a recurring architecture constraint become an executable check, or should an ADR be added, updated, superseded, or rejected? |

Report architecture impact with:

```text
Architecture impact:
- Affected surface:
- Incoming dependencies:
- Outgoing dependencies:
- Before/after edge changes:
- Cycle/layer/coupling/redundancy result:
- Evidence source and freshness:
- ADR/rule impact:
```

## Comprehensiveness Done

A proof or test set is comprehensive only relative to a declared domain. A
change is not done until the domain is partitioned and every meaningful class is
mapped to proof, test evidence, or explicit exclusion.

| Check | Questions |
|---|---|
| Domain inventory | What inputs, states, artifacts, public paths, external contracts, and caller behaviors are accepted? |
| Out-of-scope boundary | What inputs, formats, subclassing behavior, monkey-patching, private mutation, or hostile data are excluded? |
| Equivalence classes | What normal, empty, minimum, maximum, invalid, mixed, serialized, dependency-failure, and legacy classes exist? |
| Boundary values | Where do coordinates, sizes, page numbers, enums, strings, object identity, or ordering change behavior? |
| Invariants | What must remain true after construction, mutation, serialization, rendering, and round trip? |
| Preconditions | What must callers provide before a function or class is valid to call? |
| Postconditions | What result, side effect, exception, or unchanged state does the code guarantee? |
| Defensive coding | Are bad states impossible by construction, or rejected near the boundary with explicit exceptions? |
| Assertion use | Are `assert` statements reserved for internal impossibility rather than data validation? |
| Edge/adversarial tests | Is every meaningful boundary or invalid class tested, proven impossible, or excluded by contract? |
| Proof coverage matrix | Does every proof obligation map to code, tests, covered domain, assumptions, exclusions, and residual risk? |
| Mutation testing | Did an automated mutation tool run against proof-critical source paths, and were all surviving proof-critical mutants killed, proven equivalent, or excluded by the declared domain? |

Use this matrix when reporting comprehensiveness:

| Domain class | Handling | Proof obligation | Test evidence | Status |
|---|---|---|---|---|
| `<class of input/state>` | reject / normalize / preserve / emit / ignore | `<PO id or none>` | `<test or none>` | covered / proven / excluded / residual risk |

Comprehensiveness does not mean "we tested everything." It means the finite set
of meaningful partitions has been named, and none are silently assumed.

### Mutation Testing Requirement

Manual perturbation is not an acceptable substitute for mutation testing on
proof-critical logic. LLM or reviewer judgment may help interpret a mutation
report, but cannot pass the gate.

Mutation testing is required when a change includes any of these:

- A mathematical proof obligation.
- A public contract guard, validation branch, dispatch constraint, or coordinate
  formula.
- Serialization, deserialization, deterministic output, or noninterference
  behavior.
- Parser/generator truth data consumed by downstream tests.

The mutation gate passes only when the report shows no surviving
non-equivalent proof-critical mutants. Surviving mutants must be classified as:

| Classification | Requirement |
|---|---|
| Equivalent mutant | Provide a written proof or executable equivalence check showing the mutation is behaviorally identical within the declared domain. |
| Out-of-scope mutant | Point to the exact domain exclusion or non-proof-critical path. |
| Test gap | Add or strengthen tests until the mutant is killed. |
| Tool/config invalid | Capture the tool output and rerun with corrected configuration before claiming done. |

For Python/pytest projects, prefer `mutmut` unless the project has a better
approved mutation runner. On Windows, run `mutmut` inside WSL because current
`mutmut` requires fork support.

Report mutation testing with:

```text
Mutation:
- Tool and version:
- Mutated source paths:
- Test selection:
- Mutants killed:
- Mutants survived:
- Mutants excluded/equivalent:
- Gate result:
```

## Test Applicability Done

Not every slice needs every kind of test, but every slice must make that
decision explicit. "Not applicable" is acceptable only when the change surface
does not expose that risk or the exclusion is already part of the declared
domain.

| Test class | Required when | Evidence |
|---|---|---|
| Unit | Pure functions, value objects, small class contracts, validation branches, or deterministic helpers changed. | Direct tests for normal, invalid, and boundary behavior. |
| Behavioral/condition | A design condition, user-visible feature, parser-facing behavior, or proof obligation changed. | Condition-marked test tied to the requirement. |
| Failure-mode | Invalid state, malformed input, unsupported option, missing file, dependency failure, or external tool failure is possible. | Negative test asserting exception, log, preserved state, or recovery behavior. |
| Integration/live-path | Behavior crosses modules, public APIs, renderers, parsers, file formats, storage, subprocesses, or other IO boundaries. | Test through the public path a caller or downstream system uses. |
| Contract/API compatibility | Public signatures, serialized parameters, truth schemas, generated artifacts, fixtures, or backwards-compatible behavior changed. | Compatibility, round-trip, legacy fixture, or old-caller regression test. |
| Property/fuzz | Behavior has broad input spaces, parsers, coordinate math, geometry, layout, serialization, normalization, ordering, or invariant claims. | Property test, fuzz test, exhaustive finite-domain test, or mathematical proof. |
| Mutation | Proof-critical logic, guards, dispatch rules, formulas, serialization, or parser/generator truth logic changed. | Automated mutation report with no surviving non-equivalent proof-critical mutants. |
| Security/adversarial | Code handles untrusted input, paths, filenames, archives, templates, fonts, images, subprocesses, network, secrets, auth, deserialization, or generated active content. | Security regression test, adversarial fixture, scanner result, or explicit non-applicability note. |
| Performance/resource | Code can process large documents, many components, repeated renders, caches, recursive structures, loops, or user-sized inputs. | Budgeted regression test, benchmark, timeout/memory guard, or documented bound. |
| Concurrency/race | Shared mutable state, caches, sessions, background workers, temp files, locks, or parallel generation are involved. | Race/concurrency test, lock-path test, or proof that state is isolated. |
| Golden artifact/visual | SVG, PDF, DXF, DOCX, JSON truth, diagrams, or UI-like visual artifacts are generated. | Deterministic artifact check, parser round trip, visual/render inspection, or fixture comparison. |
| Regression | A bug, incident, surviving mutant, user report, or production failure motivated the change. | Named regression test that fails on the old behavior. |

Use this matrix in report-outs:

| Test class | Applicable? | Reason | Evidence |
|---|---|---|---|
| `<class>` | yes / no | `<risk surface or exclusion>` | `<test, proof, scanner, or none>` |

## Complexity Done

Senior engineers reduce moving parts. Agents often add them. A change is not
done if it solves the problem by adding avoidable concepts, files, dependencies,
abstractions, configuration, or explanatory machinery.

Use this ladder before adding code:

1. Does this need to exist at all?
2. Can existing InkGen code already do it?
3. Can the Python standard library do it?
4. Can a native file format, browser, OS, or downstream tool do it?
5. Can an already-installed dependency do it without expanding the dependency surface?
6. Can the requirement be met with a smaller local change?
7. Only then add the minimum new code that satisfies the requirement and proof gates.

The first safe rung that satisfies the requirement is preferred. "Safe" means it
does not remove required validation, data-loss protection, security boundaries,
accessibility, determinism, dependency integrity, or proof evidence.

| Check | Questions |
|---|---|
| YAGNI | Is this behavior required now, or speculative support for a possible future? |
| Existing code | Is there already a class, helper, renderer, serializer, or test pattern that covers this? |
| Standard library | Is this hand-rolling something Python already provides? |
| Native capability | Is this rebuilding a capability the target format/platform already has? |
| Installed dependency | Is an existing dependency enough, without adding another? |
| New dependency | If a new dependency is proposed, is it explicitly approved and better than a small owned implementation? |
| New abstraction | Does this interface, protocol, base class, factory, registry, or layer have at least two real uses or an explicit boundary reason? |
| New file | Does this deserve a file, or does locality make the code easier to understand? |
| New config | Who sets this option today? What fails if it is a constant? |
| Boilerplate | Is this code serving behavior, or just a framework shape no caller needs? |
| Indirection | Can a reader follow the behavior without jumping through unnecessary wrappers? |
| Duplication | Is repeated code actual duplication, or clearer local repetition? |
| Line count | Can the same behavior and proof be delivered with fewer branches, objects, or files? |
| Explanation burden | Does the design need a long explanation because it is too complex? |

Complexity review findings should use these tags:

| Tag | Meaning | Replacement |
|---|---|---|
| `delete` | Code or feature is unnecessary. | Nothing. |
| `stdlib` | Custom code duplicates Python standard library behavior. | Name the stdlib feature. |
| `native` | Custom code or dependency duplicates a platform/file-format capability. | Name the native capability. |
| `existing` | New code duplicates local project code. | Name the existing API. |
| `yagni` | Abstraction, config, or extension point has no current caller. | Inline or remove until needed. |
| `shrink` | Same behavior can be expressed with less code or fewer concepts. | Show the smaller shape. |

Intentional simplicity is allowed, but it must be explicit when it has a known
ceiling. Use a short comment near the tradeoff:

```python
# simplicity: linear scan is enough for fixture-sized documents; add an index if records exceed 10k.
```

The comment must name:

- The simplification.
- The known ceiling or risk.
- The trigger for upgrading.

Do not add a simplicity comment for ordinary clear code. Comments are for
intentional tradeoffs that a future agent might otherwise "fix" into bloat.

### Complexity Control-Agent Questions

1. What can be deleted?
2. What can be reused?
3. What can be handled by stdlib, native platform behavior, or an existing dependency?
4. Which new abstractions are justified by real callers or explicit boundaries?
5. Which config/options are actually set by a caller today?
6. Does the implementation introduce a framework shape around a small behavior?
7. Is the shorter design still correct on edge cases?
8. Does the simpler design preserve proof evidence?
9. Are intentional shortcuts documented with a ceiling and upgrade trigger?
10. Is the final diff smaller than the first workable design?

### Maintainability Tripwires

Complexity should be reviewed both qualitatively and quantitatively. Metrics are
not proof by themselves, but they are useful tripwires that force a review before
code becomes hard to change.

Use these maintainability qualities when reviewing a class, function, or module:

| Quality | Control question |
|---|---|
| Modularity | Can this part change without forcing unrelated parts to change? |
| Analyzability | Can a reviewer quickly determine impact, dependencies, and failure causes? |
| Modifiability | Can the behavior be changed without introducing defects or degrading other qualities? |
| Testability | Can the behavior be tested directly and through at least one live path? |
| Reusability | Is reuse intentional and real, not speculative abstraction? |

Use these measurable tripwires:

| Tripwire | Action |
|---|---|
| A function gains multiple nested branches or loops | Ask whether it should be split, simplified, or table-driven. |
| A function's cyclomatic complexity is high or increasing | Add tests for each meaningful branch or simplify before accepting. |
| A class gains unrelated reasons to change | Split responsibility or document why the cohesion tradeoff is acceptable. |
| A module gains broad imports across layers | Recheck dependency direction and coupling. |
| A change adds more code than the behavior appears to require | Run a complexity review using `delete`, `stdlib`, `native`, `existing`, `yagni`, and `shrink` tags. |

For safety-critical or core infrastructure code, treat high cyclomatic
complexity as a blocker until either simplified or explicitly justified. For
ordinary library code, treat it as a control-agent review trigger rather than a
hard fail.

## Class-Level Done

A senior engineer should be able to read the class and answer these questions
without guessing.

| Check | Questions |
|---|---|
| Responsibility | Does the class have one clear reason to exist? |
| Domain name | Does the class name match the project language and avoid implementation-only jargon? |
| Boundary | Does the class know too much about another layer, renderer, file format, or context? |
| Constructor | Are required inputs explicit, validated, and minimally sufficient? |
| Invariants | What must always be true after construction and after each public method? |
| State ownership | Which fields are owned, borrowed, cached, derived, or externally mutable? |
| Mutability | Is mutation intentional, visible, and tested? Could a frozen/dataclass/value object be simpler? |
| Public API | Are public methods cohesive and named for caller intent rather than implementation steps? |
| Error behavior | Does invalid state fail loudly with specific exceptions? |
| Serialization | If parameters or JSON are emitted, are they deterministic and round-trippable? |
| Equality/identity | Does identity matter? Are IDs, names, and labels stable enough for callers? |
| Extension path | If the class is meant to be extended, is the extension point explicit and tested? |
| Coupling | Does the class import or instantiate concrete collaborators that should be injected or kept renderer-neutral? |
| Minimality | Does the class need to exist, or could existing objects/functions own the behavior more simply? |
| Performance | Are expensive computations cached only when correctness and invalidation are clear? |
| Observability | If the class performs state-changing or external work, does it expose enough evidence to debug failures? |
| Tests | Are there tests for construction, normal use, invalid inputs, edge cases, and round trip if relevant? |
| Documentation | Does the docstring describe what the class represents, not how it happens to be implemented? |

## Function-Level Done

A function is done when its contract is obvious, narrow, and tested.

| Check | Questions |
|---|---|
| Purpose | Can its behavior be summarized in one sentence? |
| Signature | Are all parameters and the return value typed? |
| Naming | Does the name describe the observable result or command? |
| Inputs | Are accepted types, units, coordinate frames, and optional values clear? |
| Outputs | Is the return shape stable and documented? |
| Side effects | Does the function mutate state, write files, perform IO, or depend on time/randomness? |
| Failure behavior | What exceptions or error values are possible, and are they deliberate? |
| Edge cases | What happens for empty input, None, zero sizes, reversed coordinates, out-of-bounds values, duplicate keys, and unsupported options? |
| Determinism | Does the same input produce the same output where expected? |
| Idempotence | If called twice, does the second call change anything unexpectedly? |
| Boundaries | Does it cross a module, file, renderer, parser, or network boundary? |
| Complexity | Is the function small enough to review? If not, is there a meaningful decomposition? |
| Minimality | Is this helper needed by more than one caller, or does it clarify a real concept? |
| Hidden assumptions | Does it assume sorted input, valid geometry, existing directories, loaded fonts, or global state? |
| Tests | Is there a happy-path test, a failure-mode test, and at least one edge-case test? |
| Functional wiring | Is it exercised through a real caller, not only direct unit tests? |

## Generated Artifact Done

InkGen often produces SVG, PDF, DXF, DOCX, JSON truth, diagrams, or docs. These
outputs need artifact-specific checks.

| Check | Questions |
|---|---|
| Coordinate frame | Are origin, units, page height, and axis direction explicit? |
| Round trip | Can the artifact be serialized and recreated without losing intent? |
| Deterministic output | Are object ordering, timestamps, generated IDs, and JSON ordering stable? |
| Inspectability | Can the artifact be opened or parsed by the expected consumer? |
| Minimal dependencies | Is the artifact produced without adding unapproved libraries? |
| Parser compatibility | Does the downstream parser or reader recover the intended structure? |
| Truth alignment | If truth records are emitted, do bboxes and labels match the rendered artifact? |
| Legacy safety | Do unannotated or older artifacts keep their prior serialization shape? |

## Test Done

Every meaningful feature should have tests that prove behavior, not just import
or existence.

| Check | Questions |
|---|---|
| Condition marker | Does each behavioral test carry `@pytest.mark.condition(...)`? |
| Real scenario | Does at least one test use the public path a caller will use? |
| Failure mode | Is the most likely or costly failure directly tested? |
| Edge case | Is one non-trivial boundary case tested? |
| Regression target | Would the test fail if the bug or design concern returned? |
| Assertion quality | Are assertions about observable behavior, not implementation trivia? |
| No over-mocking | Are real value objects and serializers used where practical? |
| Stable fixtures | Are generated fixtures deterministic and protected from EOL or timestamp churn? |
| Applicability matrix | Are integration, contract, security, property/fuzz, mutation, performance, concurrency, golden artifact, and regression tests marked applicable or not applicable? |
| Coverage | Does coverage show the new code is executed? |
| Isolation | Do tests avoid relying on global state, current time, random names, or machine-specific paths unless controlled? |

## Documentation Done

| Check | Questions |
|---|---|
| API docs | Is the public API discoverable from docs or examples? |
| Design rationale | Is the reason for the approach captured when alternatives were plausible? |
| ADR coverage | Is an ADR added or updated for non-obvious dependency direction, public contract changes, format decisions, or accepted SOLID tradeoffs? |
| ADR contradiction check | Do existing ADRs say the opposite? If so, was the contradiction resolved by superseding, revising, or rejecting one decision? |
| Limits | Are unsupported formats, partial support, and residual risks explicit? |
| Examples | Is there a minimal example that follows the real public API? |
| Diagrams | If design structure changed, are Mermaid diagrams updated or explicitly deferred? |
| Consumer contract | Are output schemas, coordinate frames, and compatibility promises documented? |

## ADR Done

Architecture Decision Records are the memory of why dependency and contract
decisions were made. They prevent agents from rediscovering or contradicting old
decisions.

Create or update an ADR when a change:

- Changes dependency direction between modules, renderers, document models, or
  parser-facing artifacts.
- Adds or removes a public API contract.
- Changes serialization, generated artifact shape, coordinate frame, or truth
  schema.
- Adds a dependency or intentionally avoids one.
- Accepts a SOLID tradeoff, such as concrete coupling for pragmatic reasons.
- Supersedes a prior architecture decision.

An ADR is done when it states:

- Decision.
- Context.
- Alternatives considered.
- Consequences.
- Affected dependencies/contracts.
- Status: proposed, accepted, superseded, or rejected.
- Supersedes/superseded-by links when applicable.

Before accepting a new ADR, run an ADR contradiction check:

1. Search existing ADRs and design docs for the same module, contract, format, or
   dependency direction.
2. Identify decisions that conflict with the new one.
3. Resolve the conflict explicitly: keep old, revise new, supersede old, or
   record a scoped exception.
4. Add a test or checklist item if the contradiction represents a recurring
   agent failure mode.

## Review Questions For The Control Agent

Use these as the first pass before accepting a change:

1. What is the smallest claim the performance agent is making?
2. What evidence proves that claim at structural, behavioral, and functional layers?
3. What failure would be expensive if missed?
4. Is that failure directly tested?
5. Is the feature reachable through the same path the user or downstream system will use?
6. Did the implementation add coupling, global state, hidden IO, or unapproved dependencies?
7. Which callers or downstream artifacts depend on this contract?
8. Was at least one dependent path tested?
9. Did it preserve old behavior for callers outside the change?
10. Does an ADR already decide this dependency or contract differently?
11. Are generated records or artifacts deterministic and inspectable?
12. What remains unproven?
13. Should the answer be "done", "done with residual risk", or "not done"?

## Report-Out Template

Use this format when a feature is claimed complete:

```text
Scope:
- <what changed>

Proof:
- Evidence:
  - Structural: <files/classes/functions/docs added or changed>
  - Behavioral: <tests and condition ids>
  - Functional: <public path or integration path exercised>
  - Dependency: <callers/suppliers/contracts checked>
  - Architecture: <affected surface, edge changes, cycle/layer/coupling/redundancy result>
  - Complexity: <what was reused, avoided, deleted, or intentionally simplified>
  - Comprehensiveness: <domain partitions, edge classes, invariants, and exclusions mapped>
  - Test applicability: <test classes required, excluded, and evidence for each>
  - Mutation: <tool, source paths, killed/survived/equivalent/excluded, gate result>
- Proof obligations:
  - <claim>: <proven | supported by evidence | contradicted | unproven>
  - Domain: <covered cases>
  - Assumptions: <external facts and limits>
  - Method: <formal, algebraic, exhaustive, property search, static path proof>

Verification:
- <command>: <result>
- <command>: <result>

ADRs:
- <new/updated ADRs or "no ADR impact">

Residual risk:
- <known gap or "none known">
```
