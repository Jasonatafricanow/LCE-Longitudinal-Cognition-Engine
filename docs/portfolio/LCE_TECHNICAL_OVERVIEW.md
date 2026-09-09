# LCE V1 — Technical Overview

## Scope

LCE V1 is a standalone runtime for bounded longitudinal understanding. It
turns caller-supplied evidence into durable, provenance-bearing Baseline
revisions without making the derived result factual Memory or a current-turn
agent.

Frozen implementation: `808b148960f8ae5852cd78a7b8343611539631b2`
Release tag: `v1.0.0`
Release record: [`LCE_V1_RELEASE_RECORD.md`](../../LCE_V1_RELEASE_RECORD.md)

This overview describes implemented V1 behavior. Research experiments and
future architecture are called out rather than silently treated as runtime
capability.

## Authority model

```text
Memory
  what happened; factual/canonical source material

LCE
  what was learned longitudinally; derived Baseline revisions and provenance

current-turn model / Body
  what reasons and acts now; outside standalone LCE V1
```

The important non-symmetry is intentional:

- Memory owns source points and their validity/provenance.
- LCE may derive and accept longitudinal understanding over authorized source
  IDs.
- A Baseline does not become Evidence, Observation, Memory, C10, Intent,
  Appraisal, or Action.
- The read API does not call an LLM, mutate HEAD, promote an OPEN Worktree, or
  write factual evidence.
- Optional MR binding is one-way and production-off by default. It is separate
  from standalone V1 closure.

## Runtime pipeline

```text
Raw Evidence
  ↓ validity, stable IDs, provenance, supersession
Semantic Block compiler
  ↓ immutable block states; NEW / CONTINUE / MERGE / SPLIT / AUXILIARY / RECAP
Vector projection
  ↓ rebuildable state-bound vectors
Cutoff Structure Snapshot
  ↓ local stability, overlap, multi-point structure, temporal evolution
Bounded higher-order candidate
  ↓ structure → block/state/source closure
Bounded interpreter
  ↓ checked interpretation + selected immutable support
Cognition Worktree
  ↓ OPEN / MERGED / DROPPED; support observations; durable stages
Existing LCE Core / SQLite Baseline store
  ↓ immutable revision + previous_baseline_id + HEAD
Accepted/current-valid read API
```

### Stage responsibilities

| Stage | Owns | Does not own |
|---|---|---|
| Reference Memory | Evidence, validity, provenance, immutable Semantic Block states, vectors, checkpoints | Canonical MR Memory or accepted LCE Baselines |
| Semantic compiler | Semantic boundaries and recap handling | Truth judgment or arbitrary Memory retrieval |
| Vector projection | Rebuildable representation over block state | Semantic quality certification |
| Structure snapshot | Derived local observations and diffs | Canonical clustering or factual authority |
| Higher-order candidate | One bounded structure-level proposal | Unlimited recursive cognition |
| Bounded interpreter | Bounded semantic interpretation over an authorized package | Memory search, evidence writes, promotion, truth authority |
| Cognition Worktree | Durable candidate support and status | Accepted HEAD/history authority |
| LCE Core / Baseline store | Immutable accepted revisions, provenance, HEAD/history | Factual Memory ownership |
| Read API | Deterministic current-valid accepted views | Read-time LLM reasoning or mutation |

## Core V0 versus standalone V1

Core V0 and V1 are related but not interchangeable.

### Core V0

`fa492f9` and `d1eb5f6` established:

- `MemorySubstratePort`;
- `SemanticConsolidatorPort`;
- `BaselineStorePort`;
- immutable Baseline revisions;
- SQLite HEAD/history;
- provenance and normalized equivalence;
- linear revision semantics.

V0 does not own a local Memory/vector backend, point discovery, Semantic Block
compilation, snapshot structures, Worktrees, or higher-order V1 behavior.

### Standalone V1

V1 adds a minimal replaceable Reference Memory substrate and composes the full
bounded pipeline around the frozen Core. The substrate makes standalone
installation and restart/recovery testing possible without MR. It does not
change the Core's ownership model.

### Optional MR binding

MR commit `930d7f06dc9b8fd4b99ac60bcb4985061ad00e4c` implements an optional
one-way adapter:

```text
MR canonical Memory
  → explicit stable Memory IDs
  → frozen LCE MemorySubstratePort
  → LCE Baseline revisions
```

The adapter preserves MR content and evidence provenance, rejects invalid or
unauthorized selections fail-closed, and keeps production Memory admission,
retrieval, and LCE invocation OFF by default. It is not part of standalone V1
release closure.

## Key correctness invariants

### Semantic and authority invariants

1. Raw evidence remains available for provenance and correction but is not
   automatically the cognition point.
2. Semantic Blocks are semantic units, not day/time buckets.
3. Derived structures can overlap and evolve; they do not become canonical
   facts.
4. The interpreter receives only an authorized bounded package.
5. Reads are model-free and non-mutating.

### Provenance invariants

1. An interpreted historical block state is not replaced by the latest live
   state during promotion or read.
2. Selected `(block_id, state_id)` pairs retain exact ownership, ordering,
   cardinality, and source validity.
3. A later continuation/recap cannot leak newer evidence into an earlier
   cutoff-bound acceptance.

### Support invariants

1. Provenance identity and qualifying cognition-support identity are separate.
2. Pure recap, duplicate source, replay, unrelated cutoff churn, and duplicate
   local observations do not create new qualifying support.
3. Genuine candidate-relevant semantic or structural change may advance
   support and conservative promotion.
4. The support fingerprint has canonical ordering independent of recency or
   provenance ordering.

### Recovery invariants

1. Before a durable cognition effect, interpreter retry may be allowed.
2. After a durable Worktree/support/promotion effect, recovery reuses the
   committed effect rather than invoking interpretation again.
3. Missing downstream progress markers resume bookkeeping without creating a
   second cognition effect.
4. Restart/replay preserves blocks, immutable states, vectors, snapshots,
   support, Worktree status, accepted content, and revision ancestry.

## Why the structure layer is intentionally derived

The research path tested several tempting abstractions:

- raw point clouds formed giant or semantically false regions;
- exclusive clustering could not represent multi-membership;
- INSPIRATION-05 showed a sustained-support noise floor and a giant region;
- STRUCTURE-06R found useful local multi-scale signals but only partial
  structure↔structure semantics;
- H1/TDA was observed but did not provide useful semantic signal in the tested
  space.

V1 therefore stores structure observations as rebuildable derived material. It
can produce a bounded higher-order candidate, but it does not install a
canonical graph ontology or recursive cognition loop.

## Research scale versus runtime verification scale

These numbers answer different questions and should not be conflated:

| Area | Verified scale/result |
|---|---|
| Semantic Cloud-02 | 91 raw units → 667 first-pass artifacts → 129 Semantic Blocks |
| BLOCK-03 | 129 → 179 semantic-stream blocks; recap-aware boundary correction |
| INSPIRATION-05 | 179 → 302 → 489 blocks in one frozen 3072-dimensional space |
| STRUCTURE-06R | 489-block space; 97 `k=16` groups; 74 blocks with multi-membership |
| Final V1 tests | 139 full-suite tests; 14 closure invariants; 32 recovery tests |
| Final recovery | Normalized 30/30 matrix; retained regressions + E2E: 21 passed |
| Standalone packaging | Exact-HEAD isolated install/import/smoke passed |

The research counts describe experiment objects and structural observations.
The final test counts describe software correctness gates. Neither is a
semantic-model quality score.

## Adversarial verification path

Ordinary green tests repeatedly failed to detect correctness defects. The
independent audit sequence made the following cases executable:

| Discovery | Repair/test consequence |
|---|---|
| Invalidation copied old understanding. | Require loss-of-support suppression and supported replacement only. |
| Historical promotion used latest state. | Carry immutable selected state through package, Worktree, Baseline, and read. |
| Protocol-conforming replacement backend failed real processing. | Run an independent substrate through the complete pipeline. |
| Reference interpreter hid repeated recovery effects. | Use a package-sensitive interpreter and compare durable state/calls. |
| `state_id` made pure recap look like new support. | Separate provenance identity from qualifying support identity. |
| Oldest recap permuted selected order and still inflated support. | Add permutation-sensitive permanent regression; canonicalize support fingerprint order. |

This progression is the core engineering evidence: model-assisted review was
used to discover invariants, then deterministic tests became the authority.

## Verification record

Final frozen implementation:

```text
808b148960f8ae5852cd78a7b8343611539631b2
```

Recorded final gates:

```text
closure invariants: 14 passed
recovery suite: 32 passed
normalized recovery matrix: 30/30
retained regressions + E2E: 21 passed
full suite: 139 passed
mypy src/lce: clean
Ruff src tests: clean
isolated exact-HEAD install/import/smoke: passed
```

The full closure narrative is in
[`LCE_V1_CLOSURE_HISTORY.md`](../history/LCE_V1_CLOSURE_HISTORY.md), and the
decision rationale is in [`LCE_DECISION_EVOLUTION.md`](../history/LCE_DECISION_EVOLUTION.md).

## Explicit non-claims

V1 does not establish:

- AGI, personhood, or general machine cognition;
- autonomous truth judgment;
- production semantic quality of deterministic reference embeddings or
  rule-based interpreters;
- unlimited recursive cognition;
- solved higher-order precision, thresholds, or model quality;
- MR/Body production integration;
- current-turn reasoning or execution inside LCE.

Those are boundaries of the artifact, not hidden gaps in the release claim.
