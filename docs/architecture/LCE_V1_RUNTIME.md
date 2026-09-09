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

The injected Reference Memory substrate stores Raw Evidence, immutable Semantic
Block states, compiler checkpoints, stage progress, and idempotency records in
the default SQLite implementation. A provider failure creates a durable
earliest-input barrier; later material cannot cross it. Retrying the same
stable evidence ID reuses the recorded block IDs and does not create duplicate
blocks. Compiler completion and vector/snapshot/worktree/promotion completion
are separate durable stages, so compiler replay resumes downstream work.

Vectors and structure snapshots are derived artifacts. They can be deleted and
rebuilt from current-valid Semantic Block states and their occurrence times. A
snapshot records the visible state and state-bound vector used for each point;
its identity includes those inputs and the algorithm/config versions. A
snapshot cutoff excludes blocks after that cutoff, so future material cannot
leak into an earlier structure state.

## Structures

The production baseline observes local neighbourhood stability, local overlap,
multi-point participation, and temporal evolution across lightweight k-scale
point-centric observations. A point may belong to multiple observations. A
snapshot diff reports membership growth/loss, stronger support, reconnection,
reorganization, and linked observations.

Higher-order candidates are bounded at one level: multiple existing structures
may relate to one candidate. Equivalent center/k observations with the same
effective member support are one local structure for higher-order purposes,
while overlapping non-equivalent observations remain available. Candidates
retain supporting structure IDs and can expand through the snapshot to
Semantic Blocks and Raw Evidence. They are `UNKNOWN` derived proposals, never
Evidence or accepted Understanding by themselves.

## Promotion and correction

An OPEN worktree records candidate text, Baseline ancestry, supporting blocks,
supporting structures, and repeated snapshot support. Promotion is a policy
decision using multi-point and repeated support; one cosine score or one model
confidence cannot merge it. Content-equivalent candidates do not create a new
Baseline revision.

When Memory invalidates or supersedes evidence, LCE receives the dependency
change, identifies affected blocks/snapshots/worktrees/Baselines, rebuilds the
affected derived slice, and may create a correction worktree only after a new
bounded interpretation has normal structural support. Until then the affected
HEAD is not served. LCE does not copy old text, relax policy, or re-decide
whether the source was factual.
