# Engineering Challenges and Cognition Boundaries

Status: current V1 assessment + retrospective architecture synthesis + owner-frozen research scope

This document exists to prevent two opposite reading errors:

1. treating already-implemented LCE mechanisms as if they were only future recommendations;
2. treating deliberately unresolved research boundaries as if they were missing design work.

LCE is not trying to maximize the number of cognitive claims it can produce. It is trying to make longitudinal understanding inspectable, revisable, and bounded by the evidence that actually exists.

The central distinction is:

```text
implemented mechanism
!= solved universal cognition problem

deliberate stop boundary
!= forgotten feature
```

## 1. Engineering challenge matrix

| Challenge | LCE V1 answer | Current status |
| --- | --- | --- |
| **Cognitive intermediate representation (IR)** | Natural-language semantic payload inside a deterministic envelope of immutable IDs, revision lineage, selected support, source closure, lifecycle state, and bounded model trace | **Implemented direction; universal semantic ontology intentionally not claimed** |
| **Belief revision / reconciliation** | Immutable Baseline revision history, `previous_baseline_id`, OPEN/MERGED/DROPPED Worktrees, source invalidation propagation, rebuild/correction flow, conservative promotion | **Revision mechanics implemented; universal semantic contradiction oracle not claimed** |
| **AOT batch vs JIT / nearline compilation** | Historical batch and nearline material enter the same `LceRuntime.process()` ontology/state transitions; compiler/vector/snapshot/worktree/promotion are separate durable stages | **Core processing semantics implemented; latency scheduling and provisional serving policy remain outside standalone V1** |
| **Deterministic vs probabilistic authority** | Models may perform bounded semantic extraction/interpretation; deterministic code owns state identity, source validity, support qualification, revision lineage, promotion, recovery, and read behavior | **Implemented architecture boundary** |
| **Benchmark deficit** | No-future cutoff, chronological replay, shuffle/negative controls, preserved misses, adversarial RED→GREEN regressions, package-sensitive recovery matrix, durable-state equivalence | **Internal falsification/evaluation discipline implemented; standardized external benchmark remains open** |
| **External consumption** | Deterministic `AcceptedUnderstandingReadAPI` exposes accepted Understanding plus revision/support/source provenance without read-time reasoning or mutation | **Implemented read contract; MCP / generic Agent adapters remain open** |
| **Temporal sufficiency** | Temporal ordering is treated as part of longitudinal evidence. LCE does not claim a reasoning trajectory when temporal placement itself is underdetermined | **Frozen research/product boundary** |
| **Meaning under uncertainty** | A temporal/structural pattern may remain an `UNKNOWN` derived candidate when evidence is insufficient to authorize a higher-order interpretation | **Frozen epistemic boundary** |

The table is deliberately precise about scope. For example, saying that revision mechanics are implemented does not mean LCE claims to solve general belief revision in arbitrary natural-language worlds. Saying that internal evaluation exists does not mean LCE claims a standard scientific benchmark.

## 2. Cognitive IR: semantic flexibility inside a deterministic envelope

A common failure mode for long-term cognition systems is to choose between two extremes:

```text
free-form summaries
  -> flexible semantics
  -> weak state identity / weak lifecycle guarantees

heavy ontology / predicate graph
  -> strong formal structure
  -> expensive schema evolution / brittle semantic alignment
```

LCE V1 takes a middle path.

The semantic payload remains open enough to be expressed in natural language, while the state around it is explicit and deterministic.

A Baseline carries, among other fields:

```text
baseline_id
region_id
revision_number
content
content_hash
supporting_memory_ids
supporting_state_ids
selected_support
previous_baseline_id
model_trace
```

A cognition Worktree carries, among other fields:

```text
worktree_id
base_baseline_id
base_revision
candidate_content
supporting_block_ids
supporting_structure_ids
status = OPEN / MERGED / DROPPED
applicability
unresolved
selected_support
processing_input_id
needs_rebuild
```

The point is not that these exact fields are a universal Cognitive IR. The stronger architectural claim is narrower:

> **Keep open-ended semantics in a replaceable payload, but make identity, provenance, support, revision, lifecycle, and authority deterministic.**

This allows the semantic front end to evolve with model capability without allowing model text to silently redefine runtime authority.

Primary implementation references:

- [`src/lce/contracts/baseline.py`](../src/lce/contracts/baseline.py)
- [`src/lce/cognition/worktree.py`](../src/lce/cognition/worktree.py)
- [`docs/architecture/LCE_V1_RUNTIME.md`](architecture/LCE_V1_RUNTIME.md)

## 3. Belief revision: revision mechanics without a universal contradiction oracle

LCE already implements a substantial part of the mechanics often described as belief revision:

```text
accepted Baseline rev N
  -> new bounded candidate
  -> OPEN Worktree against a known base revision
  -> additional qualified support / review
  -> MERGED or DROPPED
  -> accepted Baseline rev N+1 when promotion succeeds
```

History is immutable. New accepted understanding does not overwrite the previous revision in place.

When source evidence becomes invalid or is superseded, LCE propagates dependency impact through affected Semantic Blocks, snapshots, Worktrees, and Baselines. Affected cognition is rebuilt rather than silently preserved from invalid support.

What V1 deliberately does **not** claim is a universal semantic contradiction oracle.

The system does not assume that an unrestricted LLM saying "these two things conflict" is sufficient authority to rewrite durable cognition. Source validity belongs to Memory authority. Semantic interpretation is bounded. Promotion is a separate policy decision.

Therefore:

```text
revision / invalidation mechanics = implemented
universal contradiction meaning = not claimed
```

Primary references:

- [`src/lce/cognition/invalidation.py`](../src/lce/cognition/invalidation.py)
- [`src/lce/cognition/worktree.py`](../src/lce/cognition/worktree.py)
- [`docs/architecture/LCE_V1_RUNTIME.md`](architecture/LCE_V1_RUNTIME.md)

## 4. Batch vs nearline: one cognition ontology, not two systems

LCE V1 does not define one cognition model for historical batch work and another for nearline input.

Both modes enter the same runtime path:

```text
historical sequence
  -> run_batch()
  -> process(..., mode="batch")

nearline material
  -> process(..., mode="nearline")
```

The ontology and state transitions do not change.

The runtime also separates durable progress across compiler, vector, snapshot/discovery, Worktree/support, promotion, and completion stages. A restart therefore does not imply "run cognition again from the beginning" after an already-durable cognition effect.

This addresses the core consistency problem between historical and nearline compilation.

It does **not** claim that standalone V1 has solved every serving-latency question. In particular, a product may still choose a hot provisional overlay or other immediate-serving policy before full longitudinal compilation completes. That is an integration/serving design question, not a reason to fork LCE's cognition ontology.

Primary reference: [`docs/architecture/LCE_V1_RUNTIME.md`](architecture/LCE_V1_RUNTIME.md).

## 5. Benchmark deficit: evaluation is part of the research

There is no widely accepted benchmark for "longitudinal cognition trajectory correctness" comparable to conventional retrieval metrics.

LCE therefore does not treat a lack of public benchmark as permission for subjective evaluation. Instead, the project progressively constructed falsification-oriented internal evaluation:

```text
no-future cutoff
chronological replay
shuffle / negative controls
preserved real misses
bounded evidence packages
RED-before-GREEN adversarial regressions
package-sensitive legal interpreter variation
durable-state recovery equivalence
selected-state / support-identity checks
```

A notable productization lesson was that a reference interpreter could produce an apparent `30/30` recovery result while a legal package-sensitive interpreter exposed `24/30`. That changed the correctness model instead of being explained away as an inconvenient test.

The remaining open problem is **external validation**:

- cross-corpus generalization;
- standardized longitudinal tasks;
- domain-independent scoring for trajectory fidelity and revision correctness;
- comparison against alternative long-term cognition architectures.

One particularly relevant future validation surface is architecture evolution itself: feed versioned design discussions, commits, audit rejects, and repair records into LCE, then compare the recovered decision trajectory with independently reconstructed project history. That would test whether LCE can recover why a system changed, not merely retrieve related documents.

Primary references:

- [`docs/research/FINDINGS.md`](research/FINDINGS.md)
- [`LCE_V1_CLOSURE_TEST_SUITE_REPORT.md`](../LCE_V1_CLOSURE_TEST_SUITE_REPORT.md)
- [`docs/history/LCE_DECISION_EVOLUTION.md`](history/LCE_DECISION_EVOLUTION.md)

## 6. Temporal ordering is evidence, not metadata

This is a critical research boundary.

BLOCK-03 established that arbitrary time buckets must **not** define semantic identity. That does not make time unimportant. The opposite conclusion was retained:

```text
semantic continuity
  -> defines the cognition unit

temporal order
  -> constrains sequence, visibility, replay, change, and falsification
```

For longitudinal cognition, the order in which evidence actually appeared is part of what the system is trying to explain.

A trajectory such as:

```text
A at t1
  -> B at t2
  -> C at t3
  -> D at t4
```

supports bounded questions such as:

- Was B visible only after A?
- Did C continue, narrow, contradict, or supersede earlier understanding?
- At which cutoff did a direction first become visible?
- Did an isolated point reconnect only after later evidence arrived?
- Does the apparent progression survive no-future and shuffle controls?

Removing temporal ordering and then asking the system to reconstruct the "true" logic is a materially different problem:

```text
A   B   C   D

-> infer which one caused which
-> infer which was premise vs consequence
-> infer which ordering a rational reasoner would have followed
```

That task introduces a much larger hypothesis space and requires substantially more world knowledge, causal assumptions, semantic completion, and general reasoning priors.

LCE deliberately does not use "erase the timeline and reconstruct the reasoning path" as a required proof of longitudinal cognition.

This is not an attempt to make evaluation easier. It is scope control:

> **Do not remove a real domain constraint merely to prove a more general intelligence capability than the product requires.**

For the target class of long-running agent systems, interactions, events, decisions, versions, and memory records are usually naturally ordered. Temporal structure is therefore a legitimate product signal, not a form of benchmark leakage.

## 7. Temporal Sufficiency Boundary

The previous section leads to an explicit policy for evidence whose time position is missing or uncertain.

### Case A — reliable temporal placement exists

```text
reliable source timestamp / event order / version order
  -> normal longitudinal pipeline
```

The evidence may participate in cutoff-bound snapshots and trajectory claims subject to the normal source/semantic rules.

### Case B — no explicit timestamp, but temporal placement can be recovered reliably

A caller/import layer may recover ordering from sufficiently strong evidence such as:

- version ancestry;
- explicit before/after references;
- source sequence with stable ordering semantics;
- event dependencies that determine relative order.

If temporal placement is recovered, that recovery should remain inspectable rather than silently invented.

### Case C — temporal placement remains underdetermined

```text
temporal position UNKNOWN
  -> retain as ordinary evidence/reference when otherwise valid
  -> do not use it to support trajectory / emergence / evolution claims
```

The correct behavior is to **give up the longitudinal claim**, not to fill the missing order with a plausible story.

This is the first `UNKNOWN` boundary in this document:

> **Temporal UNKNOWN means the system does not know where the evidence belongs in the longitudinal sequence well enough to infer a trajectory.**

This policy is partly a product/import boundary rather than a claim that standalone V1 automatically reconstructs all missing timestamps.

## 8. Epistemic Stop Boundary: observed change does not imply known meaning

A second, different `UNKNOWN` exists after temporal sufficiency has already been established.

Suppose LCE can validly observe:

```text
local stability
reconnection
growth
loss
overlap
reorganization
persistence across cutoffs
```

Those observations can justify attention without authorizing a high-level semantic story.

STRUCTURE-06R was important precisely because several attractive higher-order signals were weak:

- H1 had no useful semantic signal;
- thousands of overlap events sat near a noise floor;
- only 2 of 6 reviewed structure pairs were worth attention;
- recursive cognition was not implemented.

The architecture therefore permits:

```text
observed temporal / structural change
  -> bounded higher-order candidate
  -> UNKNOWN derived proposal
```

until a bounded interpretation has enough authorized support to proceed.

This is the second `UNKNOWN` boundary:

> **Semantic UNKNOWN means the system knows that a longitudinal/structural pattern exists, but does not yet know what higher-order meaning is justified.**

The two UNKNOWN states must not be conflated:

| UNKNOWN type | What is missing | Allowed behavior |
| --- | --- | --- |
| **Temporal UNKNOWN** | reliable placement/order of evidence | no trajectory/evolution claim |
| **Semantic UNKNOWN** | justified meaning of an observed ordered pattern | keep bounded candidate/observation; do not invent higher-order meaning |

These are different failure surfaces with different consequences.

## 9. Why the two stop boundaries matter

Without the temporal boundary, an LCE-like system can drift into unconstrained reconstruction:

```text
unordered evidence
-> plausible causal ordering
-> plausible reasoning trajectory
-> inferred cognition history
```

Without the semantic boundary, it can drift into recursive self-interpretation:

```text
ordered structural observation
-> speculative meaning
-> speculative higher-order structure
-> reuse speculation as support
-> self-amplifying cognition
```

Both paths expand the hypothesis space faster than the available evidence constrains it.

LCE's response is not "never reason." The response is to keep durable longitudinal claims inside an evidence regime that can be inspected and falsified.

```text
Can temporal placement be established?

NO
  -> Temporal UNKNOWN
  -> no longitudinal trajectory claim

YES
  -> observe cutoff-bound temporal / structural change
  -> is higher-order semantic interpretation sufficiently bounded?

     NO
       -> Semantic UNKNOWN
       -> valid stopping point

     YES
       -> bounded interpretation / Worktree / promotion path
```

## 10. Probabilistic front end, deterministic authority core

A useful summary of the V1 architecture is:

```text
probabilistic / replaceable
─────────────────────────
semantic segmentation
embedding
candidate interpretation
model/provider choice

bounded deterministic runtime
─────────────────────────
source validity
immutable state identity
selected support
cutoff visibility
revision lineage
Worktree lifecycle
support qualification
promotion
recovery
accepted read
```

This is not a claim that every semantic operation can be made deterministic. It is a statement about where uncertainty is allowed to enter and where it is not allowed to silently become authority.

## 11. External consumption boundary

LCE already exposes a deterministic accepted-Understanding read surface through `AcceptedUnderstandingReadAPI`.

A consumer can receive accepted content together with revision identity and source/support provenance without causing new reasoning, promotion, or Memory writes at read time.

What remains future integration work is protocol packaging such as MCP or a generic Agent adapter. That should be treated as an interface layer over the existing authority semantics, not a redesign of LCE's cognition core.

Primary reference: [`src/lce/read_api.py`](../src/lce/read_api.py).

## 12. What V1 deliberately does not claim

LCE V1 does not claim to solve:

- universal natural-language belief revision;
- reconstruction of the correct reasoning order from arbitrary unordered evidence;
- a complete ontology of cognition;
- recursive cognition over cognition-derived evidence;
- standardized scientific benchmarking of longitudinal cognition;
- production-optimal latency scheduling for every host Agent;
- generic MCP/Agent ecosystem integration.

These are not all equivalent kinds of future work. Some are open implementation opportunities. Others are deliberate scope boundaries whose removal would require a new research question and new evaluation authority.

## 13. Architecture revalidation rule

A useful question for every future extension is:

> Does this extension solve a demonstrated LCE problem, or does it broaden LCE into a more general reasoning system because the broader problem is intellectually attractive?

If the latter, the project should stop and revalidate the problem statement before adding ontology, recursive cognition, causal reconstruction, or new model authority.

Related documents:

- [`ARCHITECTURE_REVALIDATION.md`](ARCHITECTURE_REVALIDATION.md)
- [`RESEARCH_OVERVIEW.md`](RESEARCH_OVERVIEW.md)
- [`research/FINDINGS.md`](research/FINDINGS.md)
- [`architecture/LCE_V1_BOUNDARIES.md`](architecture/LCE_V1_BOUNDARIES.md)
- [`architecture/LCE_V1_RUNTIME.md`](architecture/LCE_V1_RUNTIME.md)
