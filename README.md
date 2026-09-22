# LCE — Longitudinal Cognition Engine

LCE is a Python research system for building and revising longitudinal summaries from historical evidence.

The current pipeline is deliberately split into several inspectable stages:

```text
source evidence
   |
   v
semantic blocks
   |
   v
vector projection
   |
   v
local overlapping structures
   |
   v
candidate relations / interpretations
   |
   v
draft revision
   |
   v
accepted revision
   |
   v
read-only query API
```

Each stage can be rebuilt or invalidated without rewriting the source evidence.

## Current pipeline

### 1. Semantic blocks

Raw historical items are first compiled into semantic blocks under `src/lce/semantic/`.

The compiler keeps block identity, source references, timestamps, and validity information so later stages can be traced back to the original evidence.

### 2. Vector projection and local structure

Vectors are rebuildable. They are used for neighborhood/structure discovery rather than stored as the source of truth.

`src/lce/structure/` builds local, overlapping structures at several neighborhood sizes. A single block may participate in more than one local structure.

### 3. Structure changes and relation candidates

Snapshots and diffs record how local structures change across cutoffs.

Candidate relations are derived from those structures and may remain `UNKNOWN`; the pipeline does not require every stable geometric pattern to receive a semantic interpretation.

### 4. Draft and accepted revisions

The current implementation stores provisional interpretations separately from accepted revisions.

Existing code names these objects `CognitionWorktree` and `Baseline`; mechanically, they are:

```text
draft candidate
  -> support/recovery checks
  -> accepted immutable revision
  -> latest accepted revision for that region
```

Accepted revisions keep explicit source support, revision numbers, hashes, and predecessor links.

### 5. Read API

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

## Research / verification tools

The public verification gate is:

```bash
python -m pip install -e . -r requirements-verification.txt
python scripts/verify.py
```

The repository currently includes:

- 142-test verification coverage;
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
