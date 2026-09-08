# LCE V1 Runtime

LCE V1 uses one cognition pipeline for historical and nearline material:

```text
Raw Evidence
  -> Reference Memory validity/provenance
  -> semantic-stream Semantic Blocks
  -> rebuildable Semantic Block vectors
  -> cutoff-bounded structure snapshots
  -> higher-order candidate
  -> bounded interpretation in an OPEN cognition worktree
  -> conservative promotion through Baseline/HEAD
  -> accepted Understanding read API
```

`LceRuntime.process(material)` is the single entry point. `run_batch()` only
orders a historical sequence and calls that same method with `mode="batch"`.
Nearline callers use `mode="nearline"`; the ontology and state transitions do
not change.

## State and restart

Reference Memory stores Raw Evidence, Semantic Blocks, compiler checkpoints,
and idempotency records in SQLite. A provider failure happens before the
checkpoint advances. Retrying the same stable evidence ID reuses the recorded
block IDs and does not create duplicate blocks.

Vectors and structure snapshots are derived artifacts. They can be deleted and
rebuilt from current-valid Semantic Blocks and their occurrence times. A
snapshot cutoff excludes blocks after that cutoff, so future material cannot
leak into an earlier structure state.

## Structures

The production baseline observes local neighbourhood stability, local overlap,
multi-point participation, and temporal evolution across lightweight k-scale
point-centric observations. A point may belong to multiple observations. A
snapshot diff reports membership growth/loss, stronger support, reconnection,
reorganization, and linked observations.

Higher-order candidates are bounded at one level: multiple existing structures
may relate to one candidate. Candidates retain supporting structure IDs and
can expand to Semantic Blocks and Raw Evidence. They are `UNKNOWN` derived
proposals, never Evidence or accepted Understanding by themselves.

## Promotion and correction

An OPEN worktree records candidate text, Baseline ancestry, supporting blocks,
supporting structures, and repeated snapshot support. Promotion is a policy
decision using multi-point and repeated support; one cosine score or one model
confidence cannot merge it. Content-equivalent candidates do not create a new
Baseline revision.

When Memory invalidates or supersedes evidence, LCE receives the dependency
change, identifies affected blocks/snapshots/worktrees/Baselines, rebuilds the
affected derived slice, and may create a correction worktree. It does not
re-decide whether the source was factual.
