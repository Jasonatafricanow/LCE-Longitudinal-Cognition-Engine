# LCE V1 — Longitudinal Cognition Engine

**A research-engineering system for durable longitudinal understanding.**

LCE investigates a narrower problem than "general memory":

> Can an AI system form, inspect, falsify, revise, and reuse understanding across time without allowing model inference, vector similarity, or derived structure to become factual authority?

The current architecture is the result of failed assumptions, bounded experiments, negative controls, adversarial review, and runtime repair. The research record is part of the project: rejected ideas are preserved because they explain why the current boundaries exist.

## Portfolio role

```text
Historical evidence
       |
       v
       LCE
 longitudinal structure
       |
       | derived cognition only
       v
optional consumer / Mind Runtime boundary

Mind Runtime asks:
"What state is authorized now?"

LCE asks:
"What structure is justified across this history?"
```

LCE is independent from [Mind Runtime](https://github.com/Jasonatafricanow/Mind-Runtime). MR may consume LCE output through a narrow adapter, but LCE does not automatically acquire runtime authority.

## The problem

A long-running agent can retrieve old records and ask a foundation model to reconstruct what changed. That works, but it repeatedly spends model inference on the same longitudinal interpretation and makes several concepts easy to conflate:

```text
what happened
what is similar
what changed
what was inferred
what is currently accepted
```

LCE separates these into different artifacts and different authorities.

A useful shorthand is:

```text
Memory = what happened
LCE = what was learned longitudinally
Current-turn model = what reasons and acts now
```

## How the research evolved

The project did not start with the final pipeline.

### 1. Raw point clouds failed as cognition

Early experiments treated raw text units plus semantic similarity as candidate cognition structure.

They produced giant connected regions and mixed unrelated objects. The failure showed that semantic proximity at raw-text granularity was too weak a unit for longitudinal cognition.

**Correction:** raw text remains evidence; semantic segmentation happens before vector projection.

### 2. Time buckets failed as semantic boundaries

Grouping by day or fixed time window reduced implementation complexity but merged unrelated thoughts and split coherent ones.

**Correction:** temporal order remains essential for longitudinal reasoning, but semantic continuity — not the clock — defines a cognition block.

### 3. Model-led trend discovery created circularity

A model that both searches for a trajectory and judges whether the trajectory exists can manufacture coherence.

**Correction:** no-future cutoffs, replay, negative controls, and bounded evidence packages were introduced so later evidence cannot leak into earlier claims.

### 4. Global clustering hid multi-membership

One exclusive cluster per item was too strong an assumption. Longitudinal evidence can belong to several local structures at different scales.

**Correction:** derived structure became local, overlapping, and scale-dependent.

### 5. Attractive higher-order signals were not automatically useful

Some structural signals were mathematically real but semantically weak or unstable.

**Correction:** higher-order structure remains observation until bounded evidence justifies interpretation. `UNKNOWN` is an acceptable outcome.

### 6. Green tests still allowed authority bugs

Productization exposed another class of failure: provenance inflation, repeated consumption manufacturing support, recovery faults, and test oracles that were too weak.

**Correction:** immutable revisions, selected support identity, effect-aware recovery, adversarial regression fixtures, and explicit runtime contracts became part of V1.

## Research method

The recurring method is:

```text
narrow hypothesis
    |
    v
bounded experiment / adversarial probe
    |
    v
preserve misses and negative results
    |
    v
classify failure:
algorithm / representation / authority
    |
    v
change the smallest abstraction that explains it
    |
    v
encode the boundary as contract + regression
```

The implementation is allowed to change. The constraint learned from a failure is often the more durable result.

## Key design decisions

### Similarity discovers candidates, not cognition

Embeddings and neighborhoods are useful search instruments. They do not create semantic or factual authority.

### Semantic structure precedes vector structure

The project pays for semantic segmentation before projection rather than asking geometry to recover all meaning later.

### Longitudinal claims require temporal sufficiency

If the order of evidence cannot be established, LCE does not invent a reasoning trajectory.

### Derived structure is never its own evidence

Regions, snapshots, higher-order candidates, Worktrees, and accepted Baselines remain derived cognition artifacts. They cannot recursively become factual Memory.

### Read-time access is deterministic

Reading accepted understanding does not invoke a model, promote a Worktree, or mutate evidence.

### Uncertainty is a valid stop

Two different unknowns remain explicit:

```text
Temporal UNKNOWN
  -> order is not justified
  -> no longitudinal trajectory claim

Semantic UNKNOWN
  -> ordered structure exists
  -> higher-order meaning is not justified
```

## Current V1 pipeline

```text
Raw Evidence
  -> Reference Memory validity / provenance
  -> Semantic Blocks
  -> rebuildable vectors
  -> cutoff-bounded local structures
  -> bounded higher-order candidates
  -> OPEN cognition Worktree
  -> conservative Baseline / HEAD promotion
  -> deterministic accepted Understanding read
```

Each arrow is a transformation boundary, not an automatic promotion in authority.

## Current V1 scope

LCE V1 includes:

- Semantic Blocks compiled from authorized evidence;
- derived vectors and local structure snapshots;
- overlapping local structure;
- bounded higher-order candidates;
- durable `OPEN / MERGED / DROPPED` cognition Worktrees;
- immutable accepted Baseline revisions and HEAD;
- invalidation / rebuild / correction mechanics;
- deterministic accepted-Understanding reads;
- no-future replay and negative controls;
- recovery and adversarial regression suites;
- a provider-agnostic semantic replication surface.

It does not require Mind Runtime to operate as a standalone system.

## Public evidence boundary

Some historical observations were produced from private longitudinal material. That corpus is not published.

The public repository instead exposes:

- implementation and contracts;
- synthetic boundary experiments;
- research history and negative results;
- verification tooling;
- replication interfaces for public/sanitized corpora;
- an external audit protocol.

The principle is:

> Public reproducibility requires a reproducible method; it does not require disclosure of private source material.

No public real-corpus replication or protocol-compliant independent external audit is claimed unless one is actually recorded.

## Verification

The canonical public gate is:

```bash
python -m pip install -e . -r requirements-verification.txt
python scripts/verify.py
```

The current public verification record documents 142 tests, strict mypy over `src/lce`, and Ruff checks over source/tests. These verify software and runtime contracts; they do not establish scientific generalization or universal embedding quality.

Useful records:

- [Research overview](docs/RESEARCH_OVERVIEW.md)
- [Findings and negative results](docs/research/FINDINGS.md)
- [Decision evolution](docs/history/LCE_DECISION_EVOLUTION.md)
- [Master timeline](docs/history/LCE_MASTER_TIMELINE.md)
- [Architecture revalidation](docs/ARCHITECTURE_REVALIDATION.md)
- [Engineering challenges and boundaries](docs/ENGINEERING_CHALLENGES_AND_BOUNDARIES.md)
- [Public evidence matrix](docs/PUBLIC_EVIDENCE_MATRIX.md)
- [Verification](docs/VERIFICATION.md)
- [Portfolio case study](docs/portfolio/LCE_CASE_STUDY.md)

## Boundaries and non-claims

LCE V1 does **not** claim:

- a solved general cognition model;
- recovery of one uniquely correct reasoning trajectory from arbitrary unordered evidence;
- automatic production authority inside MR;
- universal embedding or clustering quality;
- universal contradiction resolution;
- independently validated scientific superiority.

Its strongest claim is narrower: it implements and tests a disciplined boundary for longitudinal derived cognition without letting that derived cognition silently become factual truth.

## Stack

Python 3.12+ · pytest · mypy · Ruff · deterministic runtime contracts · replaceable embedding/model surfaces

## Architecture revalidation

LCE periodically asks a second-order question:

> If the underlying model became dramatically more capable tomorrow, which parts of this architecture would still be required for correctness, auditability, recovery, or authority separation?

A component can therefore be:

```text
KEEP     — expresses a durable constraint
DEMOTE   — useful heuristic, not authority
REPLACE  — problem remains, abstraction is wrong
DELETE   — obsolete scaffolding
```

This prevents current model limitations from being mistaken for permanent architecture.

## Repository history

The public repository preserves the research and productization record but does not publish the private longitudinal corpus used in some historical experiments.

## Engineering philosophy

The objective is not to make every hypothesis survive.

A research architecture becomes stronger when failed ideas leave behind explicit constraints, and when attractive derived structure is allowed to remain uncertain instead of being promoted for narrative convenience.