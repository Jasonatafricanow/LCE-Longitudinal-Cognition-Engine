# LCE V1 — Portfolio Case Study

## Executive summary

LCE V1 explores a practical problem in agent systems: prior history is often
handed back to a Foundation Model, which must reconstruct longitudinal meaning
again during a later interaction. LCE asks a narrower engineering question:

> Can already-formed longitudinal understanding become a reusable runtime asset
> instead of repeated probabilistic reconstruction?

The result is not a claim to have solved machine cognition. It is a bounded,
standalone V1 that compiles supplied evidence into Semantic Blocks, observes
derived local structures, interprets bounded candidate packages, tracks
candidate cognition in a durable Worktree, promotes only supported changes into
immutable Baseline revisions, and exposes a read API that does not reinterpret
history with an LLM.

The credible part of the project is the engineering path: research findings
changed the representation, rejected attractive abstractions, independent
audits rejected green-but-incorrect implementations, and each important audit
discovery became a deterministic executable invariant.

## The problem and the boundary

Many agent designs repeatedly place the same historical material in front of a
model and ask it to reconstruct what matters. That can be useful, but it
mixes factual memory, longitudinal interpretation, and current-turn reasoning
in one probabilistic step.

LCE separates those responsibilities:

```text
Memory
= what happened

LCE
= what was learned longitudinally

current-turn model / Body
= what reasons and acts now
```

In V1, LCE is not a truth judge, a current-turn agent, a general RAG layer, a
knowledge graph, or a replacement for a Foundation Model. It accepts bounded
source material, preserves provenance, derives candidate structure, and stores
accepted longitudinal understanding as a separate revisioned artifact.

## What was built

The standalone V1 runtime is:

```text
Raw Evidence
  → Semantic Blocks
  → derived local structures
  → bounded interpretation
  → Cognition Worktree
  → accepted immutable Baseline revisions
  → read API
```

The major runtime responsibilities are:

- a replaceable standalone Reference Memory substrate for evidence, validity,
  provenance, immutable Semantic Block states, vectors, and checkpoints;
- semantic-stream compilation rather than day-batch grouping;
- rebuildable vector projection and cutoff-bound structure snapshots;
- overlapping, derived local structure and a bounded higher-order candidate
  detector;
- a bounded interpreter that receives an authorized package and cannot search
  Memory, write evidence, or promote itself;
- durable `OPEN → MERGED` / `DROPPED` Cognition Worktrees;
- promotion through the existing LCE Core and SQLite Baseline/HEAD history;
- a current-valid read API with no read-time model call or state mutation.

The standalone Reference Memory substrate is a V1 product composition choice.
It does not rewrite Core V0 into a Memory owner, and it is not MR's canonical
Memory.

## Research changed the architecture

The architecture was not invented fully formed. It emerged through negative
controls and boundary corrections.

| Research observation | What it ruled out | Resulting decision |
|---|---|---|
| Raw diary units formed narrow-cone similarity and giant regions. | Raw text as the cognition point. | Preserve raw evidence for provenance; pay semantic cost before embedding. |
| Day-batch blocks mixed unrelated matters and hid recap repetition. | Time/day as the primary cognition boundary. | Semantic Block is a semantic unit, not a time unit. |
| TREND-04 could test no-future longitudinal discovery but still used an LLM-led candidate loop. | Model-led discovery as the sole evidence selector. | Move toward vector-first replay and LLM-last bounded interpretation. |
| INSPIRATION-05 reconnected old points but produced giant regions and a support noise floor. | One binary graph or sustained count as canonical structure. | Observe multiple local scales and keep structures derived. |
| STRUCTURE-06R found multi-membership but only partial structure↔structure signal. | Exclusive clustering and unlimited recursive cognition. | Allow overlapping observations and keep higher-order behavior bounded. |

The experiments were concrete. Semantic Cloud-02 went from 91 raw units to
667 first-pass artifacts and 129 Semantic Blocks. BLOCK-03 changed the output
to 179 semantic-stream blocks. INSPIRATION-05 replayed 179 → 302 → 489 blocks
in one frozen 3072-dimensional space. STRUCTURE-06R observed 97 `k=16`
groups, with 74 blocks participating in multiple groups. H1/TDA was tested,
but its signal was not promoted into core authority. Structure-to-structure
signals were partial, so higher-order architecture stayed conservative.

The detailed source-grounded history is in
[`LCE_MASTER_TIMELINE.md`](../history/LCE_MASTER_TIMELINE.md).

## High-signal architecture decisions

### 1. Semantic Block as the cognition point

**Problem.** Raw text was too granular and semantically mixed for reliable
vector structure.

**Decision.** Compile bounded semantic artifacts into Semantic Blocks before
embedding. A block retains raw and artifact references, but raw text is not
silently promoted to cognition.

**Why alternatives failed.** POINTCLOUD-01/01R showed that raw similarity
produced a narrow cone, a giant component, and false regions.

**Runtime consequence.** Later vectors and structures reference immutable block
states while raw evidence remains available for audit and correction.

### 2. Overlapping derived structures, not canonical clusters

**Problem.** A point can participate in several evolving local structures.

**Decision.** Derive local stability, overlap, multi-point participation, and
temporal change without making one exclusive category tree authoritative.

**Why alternatives failed.** INSPIRATION-05 exposed giant-region and sustained-
support noise; STRUCTURE-06R found 74 multi-member blocks across 97 `k=16`
groups and only partial higher-order semantic signal.

**Runtime consequence.** Structures are rebuildable observations that can
propose candidates, not canonical facts.

### 3. Worktree versus accepted Baseline

**Problem.** A candidate understanding needs support, retry, invalidation, and
drop semantics before acceptance.

**Decision.** Keep derived Cognition Worktrees separate from accepted immutable
Baseline revisions.

**Why alternatives failed.** Z0 found copied invalidation conclusions, mutable
historical state, incomplete replay, and support inflation when candidate and
accepted paths were not faithfully separated.

**Runtime consequence.** A candidate can remain `OPEN`, become `MERGED` only
under conservative policy, or be `DROPPED`; accepted history remains on the
existing Core/SQLite authority path.

### 4. Memory remains factual authority

**Problem.** Derived understanding must not turn itself into evidence.

**Decision.** Memory owns what happened; LCE owns derived Baseline revisions
over caller-authorized source IDs.

**Why alternatives failed.** A derived structure or Baseline has no independent
authority to create facts, and model output cannot be its own evidence.

**Runtime consequence.** Baselines do not become Evidence, Observation, Memory,
C10, Intent, Appraisal, or Action. The optional MR binding is one-way and
default-off.

### 5. Bounded interpreter without truth or promotion authority

**Problem.** Interpretation is useful, but an interpreter that searches Memory
or promotes its own output becomes an uncontrolled truth path.

**Decision.** Pass a bounded package containing authorized structures, immutable
block states, source closure, and previous accepted context. Validate returned
support against that package.

**Why alternatives failed.** Z0 found the interpretation seam absent; later
audits required strict subset/reorder validation and zero read-time calls.

**Runtime consequence.** The interpreter can classify or propose bounded
meaning. It cannot fetch new evidence, write Memory, mutate HEAD, or promote a
Worktree.

### 6. Immutable selected-state provenance

**Problem.** An interpretation of an earlier cutoff can be corrupted if
promotion looks up the latest live block state.

**Decision.** Carry exact `(block_id, state_id)` selection through package,
Worktree, Baseline, restart, read, and invalidation.

**Why alternatives failed.** Z1 reproduced source/state mismatch and positional
subset mapping defects; later state versions leaked into older conclusions.

**Runtime consequence.** Historical acceptance remains tied to the state that
was actually interpreted, not whatever state happens to be latest.

### 7. Qualifying support identity separate from provenance identity

**Problem.** A pure recap can add provenance without adding cognition-relevant
support.

**Decision.** Preserve exact immutable state for provenance, but compute
qualifying support from semantic content and effective structure membership.

**Why alternatives failed.** Z2 found a `state_id` leak. Z3 then found a second
order/recency leak after `state_id` was removed.

**Runtime consequence.** The final repair canonicalizes fingerprint order while
preserving selected provenance order:

```text
provenance ordering
≠
qualifying cognition-support canonical identity
```

### 8. Recovery reuses durable cognition effects

**Problem.** A crash after a Worktree or Baseline effect is committed can cause
replay to invoke a legal interpreter again and create duplicate cognition.

**Decision.** Retry interpretation only before a durable cognition effect;
afterward reuse the committed effect and resume downstream bookkeeping.

**Why alternatives failed.** A reference interpreter passed `30/30`, but a
package-sensitive interpreter exposed `24/30` repeated-effect failures.

**Runtime consequence.** Processing-input identity, selected support, Worktree
status, and durable stage markers make recovery idempotent across restart.

## Verification was part of the product

The ordinary green suite was insufficient. The independent closure sequence was:

```text
74 tests green → Z0 reject
85 tests green → Z1 reject
93 tests green → Z2 reject
permanent RED suite introduced
135 tests green → Z3 permutation blind spot
139 tests + canonical-order regression → closure
```

The important defects were not cosmetic:

- invalidation could preserve a copied conclusion after support loss;
- historical promotion could use latest state instead of selected state;
- a replacement backend could satisfy a protocol but fail the actual pipeline;
- compiler/recovery stages could be durable without the whole cognition effect
  being replay-safe;
- recap provenance could inflate support;
- a pure recap of the oldest selected block could change recency order and
  falsely promote despite unchanged semantic content and structures.

The final permanent authority contains 14 closure-invariant tests and 32
recovery tests, with a normalized 30/30 recovery matrix. The frozen V1 gates
also recorded 21 retained regressions plus E2E, 139 full-suite tests, clean
mypy/Ruff, and isolated exact-HEAD installation/import/smoke.

The verification history is documented in
[`LCE_V1_CLOSURE_HISTORY.md`](../history/LCE_V1_CLOSURE_HISTORY.md).

## AI-assisted engineering workflow

The division of labor was deliberately asymmetric.

The human engineering role was to:

- formulate the product problem and keep its claims bounded;
- challenge representation and authority assumptions;
- design and interpret research experiments;
- freeze the Memory/LCE/Body boundaries;
- dispatch implementation and research agents in isolated scopes;
- require independent review rather than trusting implementer summaries;
- convert reviewer discoveries into permanent deterministic tests;
- decide when a result was a reject, a repair, a readiness gate, or closure;
- stop work when a proposed expansion would exceed the authorized boundary.

LLMs contributed substantial leverage in:

- implementing bounded pipeline components and test fixtures;
- inspecting large source and artifact surfaces;
- executing experiments and extracting comparisons;
- writing independent adversarial probes;
- reviewing repair diffs against original call paths;
- producing and checking the archive documentation.

The engineering skill demonstrated is therefore not raw code generation. It is
problem framing, architecture judgment, experiment design, invariant
selection, reviewer orchestration, and deciding what not to build.

## What V1 does not claim

LCE V1 does not claim:

- solved AGI, personhood, or general machine cognition;
- autonomous truth judgment or factual Memory ownership;
- unlimited recursive higher-order cognition;
- production-quality semantic performance from deterministic fallback
  embeddings, rule-based semantic providers, or the reference interpreter;
- that thresholds, embedding quality, or higher-order precision are solved;
- MR/Body integration as part of standalone closure;
- that LCE performs current-turn reasoning or execution.

Those limits make the implemented claim more credible: V1 is an engineering-
closed standalone runtime for bounded longitudinal understanding, not a proof
that the broader research problem is solved.

## Frozen result

The implementation froze at `808b148960f8ae5852cd78a7b8343611539631b2`.
Release tag `v1.0.0` resolves to metadata commit `047cf4e...`; the release
record is [`LCE_V1_RELEASE_RECORD.md`](../../LCE_V1_RELEASE_RECORD.md).

The portfolio package treats the release as an engineering artifact with a
traceable history, not as an AI-generated demo.
