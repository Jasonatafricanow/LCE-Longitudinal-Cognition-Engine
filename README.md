# LCE — Longitudinal Cognition Engine

LCE is a Python research system for building and revising longitudinal summaries from historical evidence.

The current runtime keeps source authority separate from two derived cognition paths:

```text
source evidence
   |
   v
semantic blocks
   |
   v
vector projection
   |
   +--> trajectory runtime (Path B)
   |      slow point-cloud bootstrap
   |      -> stable overlapping Lines / branch DAG
   |      -> nearline growth
   |      -> bounded callable Line views
   |      -> optional cross-Line Surface discovery
   |
   +--> compatibility cognition path
          Frontier / 06R
          -> draft revision
          -> accepted Baseline
          -> read-only query API
```

Both paths remain derived from the same Raw Evidence authority. Derived Line,
Surface, Worktree, and Baseline objects never become new factual evidence merely
because they are persisted or reused.

## Open research

LCE is a research repository, not a claim that longitudinal cognition is a solved problem.

> We do not know the right way to compile longitudinal cognition yet. This repository is where we test it.

The preferred contribution unit is a **falsifiable research question**:

```text
question
-> baseline
-> controlled fixture
-> metric
-> failure boundary / kill criterion
-> SUPPORTED / NOT SUPPORTED / INCONCLUSIVE
```

Negative results are first-class results. If a more complex method adds no useful information beyond a simpler baseline, the expected outcome is to record that result and remove the unnecessary method from the roadmap.

Current public research tasks are indexed in [Open Research](docs/research/OPEN_RESEARCH.md). See [CONTRIBUTING.md](CONTRIBUTING.md) for the experiment and pull-request protocol.

## Current pipeline

### 1. Semantic blocks

Raw historical items are first compiled into semantic blocks under `src/lce/semantic/`.

The compiler keeps block identity, source references, timestamps, and validity information so later stages can be traced back to the original evidence.

### 2. Trajectory runtime (Path B)

The production trajectory runtime implements the A4-R research direction under
`src/lce/structure/trajectory.py` and `src/lce/cognition/line_graph.py`.

Slow-path bootstrap operates on accumulated Semantic Blocks:

```text
point cloud
  -> local mutual-kNN relations
  -> logically ordered overlapping trajectory proposals
  -> conservative stable Line admission
```

It deliberately does not use fixed time buckets, minimum age/span gates, global
pairwise cohesion, or exclusive connected components. One Semantic Block may
support multiple Lines.

A stable Line keeps one identity while allowing internal branch and explicitly
authorized conjunctive rejoin structure. Line membership and edges are
knowledge-time revisioned, so corrections rebuild the current derived relation
without rewriting what was visible at an earlier epistemic cutoff.

Nearline processing does not rescan the full history. Current Semantic Blocks are
routed only against already-stable Lines; ambiguous identity remains `UNKNOWN`
rather than being auto-merged or cloned. Full point-cloud bootstrap is explicit
or batch/periodic.

Consumer-facing Line projections are bounded content views with exact Raw
provenance closure. Surface discovery is optional and operates only across real
paths owned by different Lines.

See [Trajectory Runtime V1](docs/architecture/LCE_TRAJECTORY_RUNTIME_V1.md).

### 3. Compatibility Baseline path

#### Frontier-first longitudinal discovery

Vectors are rebuildable and state-bound. For each newly compiled Semantic Block, LCE first compares the arriving edge with the current cognition frontier: accepted Baseline HEADs plus OPEN Worktrees.

The frontier supplier uses an additive combination of vector similarity, nearest supporting-state similarity, lexical overlap, and a soft temporal prior. Old cognition is never hard-expired only because of age. A strong match to one frozen support state can rescue a branch even when a centroid is weak; two moderate frontier matches can propose a bounded cross-frontier boundary candidate.

Frontier scoring uses the immutable `selected_support.state_id` recorded when a Baseline/Worktree was formed, so later Semantic Block continuation cannot leak future text backward into an earlier cognition state.

#### Local structure fallback

If no frontier candidate is semantically accepted for the arriving input, the existing multi-scale 06R local-structure supplier remains the fallback. It builds overlapping k-neighbourhood observations, cutoff snapshots, diffs, and bounded structure↔structure candidates.

This makes the two mechanisms directly ablatable: frontier discovery can be disabled without removing the legacy structural baseline.

#### Bounded interpretation and revisions

Both frontier and structure candidates remain derived proposals and may return `UNKNOWN`. A bounded interpreter sees only authorized Semantic Block states, source references, and the previous accepted Baseline where applicable.

Frontier absorption updates an existing region. A new cross-frontier boundary remains provisional and requires repeated support before promotion.

#### Draft and accepted revisions

The current implementation stores provisional interpretations separately from accepted revisions.

Existing code names these objects `CognitionWorktree` and `Baseline`; mechanically, they are:

```text
draft candidate
  -> support/recovery checks
  -> accepted immutable revision
  -> latest accepted revision for that region
```

Accepted revisions keep explicit source support, revision numbers, hashes, and predecessor links.

#### Read API

`src/lce/read_api.py` serves only accepted revisions whose supporting semantic blocks and underlying evidence are still valid.

Reads do not invoke a model or silently promote a draft.

## Why the pipeline changed

The research directory keeps experiments that failed or forced changes in representation.

### Raw text similarity

Early experiments connected raw text units directly by similarity. Large mixed regions formed too easily, so semantic segmentation moved before vector projection.

### Fixed time buckets

Day/window grouping merged unrelated material and split coherent material. Time is still used for ordering and cutoffs, but it is not the primary semantic boundary.

### Model-led trend discovery

Using the same model to discover and judge a trend made evaluation circular. Temporal cutoffs, replay, and negative controls were added so later evidence cannot leak into earlier claims.

### Exclusive clustering

One-cluster-per-item lost legitimate multi-membership. The current structure discovery is local and overlapping.

### Green tests with weak oracles

Productization exposed provenance, recovery, and repeated-support bugs that broad happy-path tests had missed. Recovery matrices, invalidation tests, and stricter source-support checks were added afterward.

## Engineering surface vs research claim

The repository separates **implemented pipeline mechanics** from **open empirical claims**.

Implemented mechanics include source-linked semantic blocks, bitemporal Raw-Evidence
visibility, rebuildable vector/structure artifacts, overlapping trajectory proposals,
stable revisioned Line identity, branch/rejoin DAG structure, bounded provenance-safe
Line projections, optional cross-Line Surface discovery, draft-versus-accepted legacy
revisions, invalidation/rebuild, immutable revision lineage, and read-only access to
accepted revisions. Those behaviors are executable and regression-tested.

What remains open is whether the current representations and discovery methods recover
useful longitudinal cognition broadly enough on external real-world corpora. A compact
implementation of the pipeline is therefore not evidence that the research problem is
"small" or solved; conversely, adding more abstraction or code would not count as stronger
research evidence. External empirical replication is the missing evidence.

## Research / verification tools

The public verification gate is:

```bash
python -m pip install -e . -r requirements-verification.txt
python scripts/verify.py
```

The repository currently includes:

- canonical pytest verification plus focused trajectory, bitemporal, Line-graph, and Surface regression suites;
- strict mypy checks over `src/lce`;
- Ruff checks over source/tests;
- temporal-cutoff experiments;
- region/neighborhood experiments;
- negative-control and replay fixtures;
- invalidation/rebuild tests;
- recovery fault matrices;
- a semantic replication harness.

Useful entry points:

- [Research overview](docs/RESEARCH_OVERVIEW.md)
- [Findings / negative results](docs/research/FINDINGS.md)
- [Decision history](docs/history/LCE_DECISION_EVOLUTION.md)
- [Verification](docs/VERIFICATION.md)
- [Architecture boundaries](docs/architecture/LCE_V1_BOUNDARIES.md)
- [Trajectory Runtime V1](docs/architecture/LCE_TRAJECTORY_RUNTIME_V1.md)

## Repository layout

```text
src/lce/
  semantic/            semantic block compilation
  structure/           local structure discovery/snapshots/diffs
  cognition/           draft revision + promotion code
  contracts/           accepted revision/consolidation contracts
  reference_memory/    source evidence access/validity
  store/               SQLite-backed stores
  read_api.py           accepted-revision reads

research/
  experiments/         bounded research experiments
  replication/         replay/replication helpers

tests/                 runtime, recovery, invalidation, research tests
docs/                  reports, decisions, research records
```

## Scope

LCE does not claim to recover one uniquely correct reasoning trajectory from arbitrary history.

It currently implements a testable pipeline for deriving, revising, invalidating, and reading longitudinal structures while preserving links back to source evidence.

Some historical experiments used private longitudinal material; the public repository provides synthetic fixtures and replication interfaces instead of that private corpus.

## Stack

Python 3.12+ · SQLite · pytest · mypy · Ruff · replaceable embedding/model providers