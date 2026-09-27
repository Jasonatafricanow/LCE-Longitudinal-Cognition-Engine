# Path B point-cloud bootstrap algorithm bakeoff

This experiment tests the standalone-LCE question that remains after the MR
Thread -> LCE production path is already available:

> Given enough local SemanticBlocks, can latent longitudinal structure emerge
> from the point cloud strongly enough to seed Worktrees without an upstream
> Thread?

It does **not** test single-message relation extraction.  The independent
variable is history volume.

## Corpus

The deterministic corpus contains:

- six long-lived latent trends;
- two trends in each of three broad semantic domains, so same-domain similarity
  alone is insufficient;
- five short coherent bursts that look locally dense but should not become
  long-term cognition;
- sparse one-off noise;
- roughly a year of chronology.

Each true trend rotates through a semantic feature pool, so no single phrase or
feature is present in every point.  The gold trend labels are evaluation-only
and are never read by any discovery algorithm.

## Algorithms

- **A0 Pair Components** — threshold graph over point-to-point similarity.
- **A1 Mutual-kNN** — static local-connectivity baseline.
- **A2 Recurrent Density** — a semantic neighbourhood must recur across enough
  support, temporal span, time buckets, and internal cohesion before it can
  seed cognition.
- **A3 Multiscale Recurrent** — A2-like candidates must survive more than one
  semantic similarity scale before being emitted.
- **A4 Persistent Mutual-kNN** — keep the low-fragmentation mutual-kNN
  components, but emit a Worktree seed only when that component recurs across
  enough support, temporal span, and time buckets.

None of the algorithms uses a maximum-age / hard temporal cutoff.

## Evaluation

The same algorithms run at increasing history sizes.  For every cutoff the
experiment records:

- eligible latent trends;
- discovered trend recall;
- candidate volume;
- false candidate rate;
- qualifying cluster purity;
- fragmentation per discovered trend.

A temporal-shuffle control preserves semantic points and cardinality while
destroying their original chronology.  This checks whether recurrent suppliers
actually use longitudinal recurrence rather than only static geometry.

Pytest enforces mechanism invariants, not a desired research verdict.  Raw
benchmark output is printed by GitHub Actions.


## Negative controls

Two time controls are reported separately:

- timestamp shuffle: preserves cardinality and semantic points while scrambling
  exact chronology;
- temporal collapse: compresses each true long-lived trend into a short episode
  while preserving its semantic geometry.  A genuinely longitudinal bootstrap
  supplier should lose support under the collapse control.

A4 also runs a development-only parameter sweep over `k = 3..6` and minimum
temporal span of 30/60/90 days.  This sweep is for mechanism selection only and
must not be described as held-out confirmation.
