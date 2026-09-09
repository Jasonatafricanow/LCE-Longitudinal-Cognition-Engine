# Architecture Revalidation

Status: retrospective engineering synthesis

This document describes a development pattern visible across the LCE research and productization history. It is **not** presented as a doctrine that was written down before the project began. The pattern is reconstructed from repeated design reversals, negative experiments, audit failures, and later runtime repairs.

The central principle is:

> **Be persistent about the problem, constraints, correctness, and verification; remain willing to replace the implementation, model, prompt, framework, or even yesterday's abstraction.**

A component does not earn permanent status because it was expensive to build. It remains justified only while the problem and constraints still require it.

## 1. Why architecture needs revalidation

Most engineering feedback loops assume the design is already accepted:

```text
design
  -> implementation
  -> bug
  -> implementation fix
```

That loop is necessary, but it is not sufficient for systems built on fast-changing model capabilities and uncertain cognition abstractions.

A system can be implemented correctly and still solve the wrong problem. A module can be internally coherent and still sit at the wrong abstraction layer. A workaround can be useful today and become unnecessary when the underlying model improves.

LCE therefore exposed a second loop:

```text
build / experiment / use
  -> observe a failure, mismatch, or surprising success
  -> step outside the current abstraction
  -> ask whether the abstraction still deserves to exist
  -> keep / demote / replace / delete
  -> preserve the surviving constraint as an explicit boundary
```

This is **architecture revalidation**.

It is different from uncontrolled churn. A pivot should be tied to a changed problem statement, falsifying evidence, an authority violation, a model-capability change, or a clearer invariant. Novelty alone is not a reason to redesign.

## 2. Three levels of correction

When something feels wrong, the first task is to classify the failure.

### Level 1 — Implementation correction

Question:

> Is the accepted design correct, but the code or operational behavior wrong?

Typical signals:

- incorrect state transition;
- broken idempotency;
- missing persistence marker;
- wrong ordering;
- incomplete error handling;
- a test fixture that fails to exercise a legal runtime path.

Response: repair the implementation and preserve the failure as a regression when it represents a durable correctness boundary.

### Level 2 — Architecture correction

Question:

> Is the implementation behaving as designed, but the module boundary, representation, authority flow, or data model wrong?

Typical signals:

- a graph repeatedly collapses into giant/noisy structures;
- a representation mixes distinct semantic matters;
- one component has to infer information that belongs to another authority;
- repeated patches are compensating for the same abstraction mismatch;
- a supposedly local mechanism needs global knowledge to work correctly.

Response: change the abstraction rather than continue patching symptoms.

### Level 3 — Problem correction

Question:

> Even if the current architecture were implemented perfectly, would it solve the original problem?

This is the most important revalidation question.

A system can accumulate increasingly rigorous schemas, provenance rules, prompts, and state machines while still optimizing the wrong objective. When that happens, the correct response is not another layer of implementation detail. The problem statement itself must be restated.

This level is especially important in model-centric systems because an architecture can quietly become a sophisticated wrapper around repeated model inference while claiming to provide durable cognition.

A related failure mode is **problem expansion by constraint removal**: a project deliberately removes real information that its target product naturally has, then judges itself against a much more general task. That may be a valid new research program, but it is not automatically a better test of the original system.

## 3. What should stay stable and what should remain replaceable

The method distinguishes **stable constraints** from **replaceable mechanisms**.

A useful three-layer model is:

```text
Stable invariants
────────────────────────────────
authority / provenance
source validity
semantic and temporal boundaries
contradiction / supersession
verification / recovery
anti-self-pollution

Replaceable mechanisms
────────────────────────────────
retrieval strategies
semantic extraction
candidate generation
compilation mechanisms
review / routing
plasticity mechanisms
thresholds / local algorithms

Frontier model capability
────────────────────────────────
model family
prompting strategy
tool-use behavior
reasoning capability
context capacity
```

The bottom layer changes fastest. The middle layer should be cheap to replace when model capability or evidence changes. The upper layer should only be frozen when the project has evidence that the constraint survives changes in mechanism.

This means LCE should not preserve an extractor, classifier, graph construction rule, prompt, or model simply because it once solved a practical limitation.

The stronger question is:

> If the underlying model became dramatically more capable tomorrow, which parts of this component would still be necessary for correctness, auditability, recoverability, or authority separation?

What survives that question is a candidate runtime primitive. What does not survive is likely scaffolding.

## 4. What the architect must not outsource

LLMs can be used aggressively as engineering leverage. They can search a repository, implement code, generate alternatives, run experiments, inspect failures, and help construct adversarial tests.

The important boundary is not whether the model writes code. It is whether the system owner delegates the judgments that define the system.

Three judgments remain central:

```text
Problem framing
  -> What problem is actually being solved?

Abstraction selection
  -> At which layer should that problem be solved?

Evaluation
  -> What evidence would demonstrate that the solution works or fails?
```

A model can propose answers to all three. It should not silently become the final authority for them.

This is why code authorship is a weak measure of architecture ownership. The stronger evidence is visible in how a project defines constraints, designs falsification, reacts to negative results, and decides what not to build.

## 5. Revalidation triggers

Architecture revalidation should be explicit when one or more of these conditions appear:

1. **Perfect-implementation doubt** — the team realizes that even a bug-free version may not solve the intended problem.
2. **Patch accumulation** — multiple local fixes compensate for the same underlying mismatch.
3. **Authority leakage** — a derived artifact begins acting like evidence, truth, or a different subsystem's authority.
4. **Evaluation mismatch** — a green test suite or convenient oracle does not exercise the state permutations that matter.
5. **Real-use mismatch** — the system is technically active but the intended behavioral effect is absent or weak.
6. **Negative research result** — an attractive abstraction fails under bounded experiments or negative controls.
7. **Model capability shift** — a mechanism exists mainly because a previous model could not perform a task reliably.
8. **Complexity without new explanatory power** — additional state, fields, prompts, or agents increase rigor without improving the system's actual objective.
9. **Constraint-erasure scope expansion** — a proposed test removes legitimate product/domain information and thereby changes the task into a broader reasoning problem.

A trigger does not automatically imply redesign. It means the current abstraction must justify itself again.

## 6. The revalidation questions

When a trigger appears, review the design in this order:

### Problem

- What user/system failure caused this component to exist?
- Is that failure still real?
- Has the actual objective changed since the component was introduced?
- If the component worked perfectly, would the user-visible or runtime problem disappear?
- Is a proposed benchmark still testing the product problem, or has it removed a real domain constraint and created a different task?

### Abstraction

- Is this problem being solved at the correct layer?
- Is the component representing evidence, interpretation, authority, or projection — and are those roles mixed?
- Does the abstraction explain the negative result, or only hide it?
- Are several patches preserving an ontology that should instead be replaced?
- Does an `UNKNOWN` represent missing temporal placement or missing semantic meaning, and are those two cases being kept separate?

### Capability

- Does this mechanism encode a stable requirement or compensate for current model weakness?
- If a stronger model removed the need for the mechanism, what invariant would remain?
- Can the model/provider/prompt be swapped without changing authority semantics?

### Evaluation

- What would falsify the current abstraction?
- Does the test/evaluation prevent hindsight and self-support?
- Are misses and negative results preserved?
- Is the oracle strong enough to exercise all legal behaviors?
- Does recovery produce the same durable cognition result after restart?
- Are we measuring longitudinal cognition, or silently asking the system to solve unconstrained causal/logical reconstruction?

### Decision

Choose one explicitly:

```text
KEEP
  the abstraction still expresses a necessary constraint

DEMOTE
  useful as a heuristic or derived observation, but not authority

REPLACE
  the problem is valid, but the current abstraction is wrong

DELETE
  the component primarily encodes obsolete scaffolding or solves a superseded problem
```

The output of a revalidation is not necessarily new code. A deletion, a narrower boundary, a rejected hypothesis, or a new regression invariant can be the correct engineering result.

## 7. LCE examples

The LCE history contains several concrete instances of this pattern.

### Raw point cloud -> Semantic Block

**Mechanism under review:** raw historical text as the vector-space cognition point.

**Why it was revalidated:** POINTCLOUD-01 collapsed 91 points into one propagated label; POINTCLOUD-01R still produced a large connected component and semantically mixed region.

**Decision:** replace the representation.

**Discarded mechanism:** raw text as cognition point.

**Surviving constraint:** similarity can propose relatedness, but semantic identity must not be inferred from geometry alone.

### Day-batch segmentation -> semantic-stream segmentation

**Mechanism under review:** time/day boundaries as block boundaries.

**Why it was revalidated:** BLOCK-03 showed mixed matters and false regions were better explained by semantic switches than by clock boundaries.

**Decision:** replace the segmentation boundary.

**Discarded mechanism:** arbitrary time bucket as point identity.

**Surviving constraint:** temporal order matters for longitudinal evaluation, while semantic continuity defines the cognition unit.

### Chronological evidence -> do not erase time to prove a different intelligence capability

**Mechanism under review:** using real temporal order as a first-class longitudinal signal.

**Proposed challenge:** remove or scramble temporal placement and ask the system to recover the latent logical/reasoning trajectory from semantic content alone.

**Why it was revalidated:** once time is removed, the system must infer premise/consequence, causal direction, likely reasoning order, and missing transitions from a much larger hypothesis space. That is no longer merely a harder version of the same longitudinal task; it becomes open-ended reasoning reconstruction.

**Decision:** keep temporal ordering as evidence. Do not make unordered reasoning reconstruction a V1 proof obligation.

**Rejected scope expansion:** treating product-native chronology as "cheating" and deleting it to force a more general intelligence benchmark.

**Surviving constraint:** temporal ordering is evidence, not disposable metadata. If reliable temporal placement cannot be established, the system must stop the longitudinal claim rather than invent an order.

### Model-led trend discovery -> structural discovery before interpretation

**Mechanism under review:** an LLM-led loop that could both propose a longitudinal direction and judge its own supporting evidence.

**Why it was revalidated:** TREND-04 exposed hindsight/evaluation risks and retained a real miss; INSPIRATION-05 then exposed giant-region and noise-floor failures in the structural layer itself.

**Decision:** demote model interpretation and move structural discovery earlier.

**Discarded assumption:** a capable model should be allowed to search freely for the evidence that justifies its own interpretation.

**Surviving constraint:** interpretation must consume a bounded evidence package and longitudinal evaluation must enforce no-future visibility.

### Higher-order signal -> preserve semantic UNKNOWN

**Mechanism under review:** automatically assigning high-level meaning to persistent or higher-order temporal structure.

**Why it was revalidated:** STRUCTURE-06R retained weak H1 semantics, a large overlap noise floor, only 2/6 structure pairs worth attention, and no clear common pattern. Recursive cognition had no adequate evidence basis.

**Decision:** demote structural persistence to bounded candidate evidence and allow `UNKNOWN` to remain terminal when higher-order meaning is not justified.

**Discarded assumption:** persistent structure must have a nameable cognition meaning.

**Surviving constraint:** observation authority and interpretation authority are distinct.

### Exclusive clustering -> overlapping local structures

**Mechanism under review:** one cognition point belongs to one stable cluster/category.

**Why it was revalidated:** STRUCTURE-06R showed legitimate multi-membership and weak higher-order signals.

**Decision:** replace exclusive structure with overlapping, local, scale-dependent derived observations; keep higher-order cognition bounded.

**Discarded mechanism:** exclusive cluster ontology.

**Surviving constraint:** structural observations are derived and may overlap; they do not become factual authority.

### Green recovery suite -> stronger correctness model

**Mechanism under review:** the existing recovery oracle and broad green test suite.

**Why it was revalidated:** a package-sensitive legal interpreter changed an apparent `30/30` result to `24/30`, exposing durable cognition effects that earlier fixtures did not observe.

**Decision:** replace the weak evaluation model and promote discovered failure modes into runtime contracts.

**Discarded assumption:** broad green coverage is sufficient evidence of recovery correctness.

**Surviving constraints:** exact selected provenance, qualifying support identity, effect-aware recovery, and adversarial fixture variation.

## 8. Negative results are architectural assets

The implementation itself is replaceable. The most durable asset produced by a failed implementation is often the constraint discovered through its failure.

Examples:

```text
giant component
  -> not merely "bad clustering"
  -> similarity is insufficient cognition authority

unordered temporal evidence
  -> not merely "harder trend detection"
  -> removing chronology changes the task into open-ended reasoning reconstruction

persistent structure with weak semantics
  -> not merely "interpretation model too weak"
  -> observed structure may legitimately remain Semantic UNKNOWN

recap support inflation
  -> not merely "wrong counter"
  -> provenance identity and qualifying cognition-support identity are different

recovery 30/30 -> 24/30
  -> not merely "missing retry condition"
  -> correctness depends on durable cognition effects and oracle strength
```

This is why failed experiments and audit rejects remain visible in the repository. Removing them would make the final design look cleaner while erasing the evidence that explains why the boundaries exist.

## 9. The anti-sunk-cost rule

A component is not justified by the cost already spent building it.

The review question is:

> Does the current problem and its verified constraints still require this component?

If not, prior implementation effort is not evidence for keeping it.

This is especially important in AI systems. Model capability moves quickly enough that today's necessary scaffold may become tomorrow's accidental complexity.

The architecture should therefore make change cheap where change is expected, while keeping stable authority and correctness semantics explicit.

## 10. What architecture revalidation is not

Architecture revalidation is not permission to redesign continuously.

It does not mean:

- every failing test implies an ontology problem;
- every new model release requires replacing the stack;
- novelty is preferable to stable code;
- an elegant abstraction should be discarded without evidence;
- implementation detail is unimportant;
- removing more domain constraints automatically creates a better benchmark.

Implementation detail remains critical. Z0–R3 exists precisely because correct high-level architecture can still fail through persistence, ordering, identity, and recovery details.

The distinction is narrower:

> **Do not confuse implementation effort with architectural necessity, and do not confuse a broader research question with a better test of the original one.**

When evidence points to an implementation bug, fix the implementation. When evidence points to an abstraction error, change the abstraction. When the abstraction works but the system still does not solve the intended problem, restate the problem. When a proposed test removes product-native evidence and expands the task into general reasoning, treat it as a new research question rather than silently moving the goalposts.

## 11. Practical checkpoint

Before freezing or extending a major component, ask:

```text
[ ] What exact problem does this component solve?
[ ] If implemented perfectly, does it solve that problem?
[ ] Is the failure implementation-level, architecture-level, or problem-level?
[ ] Which part is a stable invariant and which part is current-model scaffolding?
[ ] What evidence would falsify the abstraction?
[ ] Can a stronger model/provider replace the mechanism without changing authority semantics?
[ ] Are negative results and real misses preserved?
[ ] Does repeated use create evidence or support that was not actually earned?
[ ] Does restart/replay preserve the same durable result?
[ ] Does this evaluation preserve legitimate product/domain constraints?
[ ] If temporal placement is unknown, are we refusing the trajectory claim rather than inventing order?
[ ] If temporal structure is visible but meaning is uncertain, are we preserving Semantic UNKNOWN rather than inventing ontology?
[ ] Should the outcome be KEEP, DEMOTE, REPLACE, or DELETE?
```

The purpose of the checkpoint is not to make the architecture static. It is to ensure that every retained abstraction continues to earn its place.

## Related documents

- [`ENGINEERING_CHALLENGES_AND_BOUNDARIES.md`](ENGINEERING_CHALLENGES_AND_BOUNDARIES.md) — current challenge/status matrix, temporal sufficiency, and the two UNKNOWN boundaries.
- [`RESEARCH_OVERVIEW.md`](RESEARCH_OVERVIEW.md) — experiment-driven architecture evolution.
- [`research/FINDINGS.md`](research/FINDINGS.md) — findings, evidence limits, and architecture consequences.
- [`history/LCE_DECISION_EVOLUTION.md`](history/LCE_DECISION_EVOLUTION.md) — detailed problem -> evidence -> failed assumption -> decision history.
- [`architecture/LCE_V1_BOUNDARIES.md`](architecture/LCE_V1_BOUNDARIES.md) — frozen V1 ownership and authority boundaries.
- [`architecture/LCE_V1_RUNTIME.md`](architecture/LCE_V1_RUNTIME.md) — final standalone runtime pipeline and correction semantics.
