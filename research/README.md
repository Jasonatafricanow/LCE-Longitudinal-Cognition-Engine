# LCE Research

This directory contains public research surfaces for LCE. They are deliberately separate from LCE Core authority and from the private historical corpus that motivated some design changes.

For the broader development reasoning, start with:

- [`docs/RESEARCH_OVERVIEW.md`](../docs/RESEARCH_OVERVIEW.md) — problem framing, failed assumptions, architecture pivots, and correction methodology;
- [`docs/research/FINDINGS.md`](../docs/research/FINDINGS.md) — claim-by-claim evidence, limits, status, and negative results;
- [`docs/PUBLIC_EVIDENCE_MATRIX.md`](../docs/PUBLIC_EVIDENCE_MATRIX.md) — which findings are publicly reproducible today and which evidence classes are still missing;
- [`docs/history/LCE_DECISION_EVOLUTION.md`](../docs/history/LCE_DECISION_EVOLUTION.md) — detailed `problem → evidence → failed assumption → decision → consequence` record;
- [`docs/history/LCE_MASTER_TIMELINE.md`](../docs/history/LCE_MASTER_TIMELINE.md) — reconstructed research / architecture / implementation / audit chronology.

## Two different public research surfaces

### 1. Small synthetic boundary experiments

The existing experiments are small, offline, and reproducible:

- [Semantic neighbourhood](experiments/semantic_neighbourhood/README.md): similarity discovers candidates, not truth.
- [Region discovery](experiments/region_discovery/README.md): candidate structure should remain inspectable and preserve weak / isolated evidence.
- [Temporal cutoff](experiments/temporal_cutoff/README.md): longitudinal evaluation must enforce no-future visibility.

These experiments support selected boundaries. They deliberately do **not** reproduce the complete POINTCLOUD-01 → SEMANTIC-CLOUD-02 → BLOCK-03 → TREND-04 → INSPIRATION-05 → STRUCTURE-06R historical research corpus.

### 2. Semantic replication harness

[`replication/`](replication/) provides a provider-agnostic harness that consumes **precomputed semantic vectors** plus temporal metadata and replays neighbourhood structure across no-future prefixes.

The harness exists so public replication can use a real embedding model without adding a model SDK or network dependency to `src/lce`.

Current status:

```text
replication harness            = available
synthetic contract fixture     = available
real public semantic run       = NOT YET ESTABLISHED
PUBLIC-SEMANTIC-REPLICATION    = NOT YET ESTABLISHED
```

Do not treat the hand-authored example vectors as semantic validation. A public semantic replication is earned only after a real public/sanitized corpus, named embedding provider/model/version, reproducible input manifest, and raw replay artifacts are committed.

## Historical evidence is a different class

The broader research sequence is documented in `docs/history/`, but some original lab corpus/artifacts are not public. Those records can explain why the architecture changed; they do not by themselves give an external reviewer an independently reproducible semantic experiment.

Use [`docs/PUBLIC_EVIDENCE_MATRIX.md`](../docs/PUBLIC_EVIDENCE_MATRIX.md) to distinguish:

```text
PRIVATE-HISTORICAL
PUBLIC-SYNTHETIC
PUBLIC-SEMANTIC-REPLICATION
RUNTIME-REGRESSION
EXTERNAL-ADVERSARIAL-AUDIT
```

## Authority boundary

Research results do not define canonical cognition, replace LCE Core authority, or make an interpretation automatically canonical.

In particular:

```text
similarity / region / cutoff observation
→ candidate or evaluation evidence
!= factual Memory
!= accepted Understanding by itself
```

The conceptual path from candidate similarity through longitudinal structure to the LCE Core authority boundary is summarized in [`docs/research/research-map.md`](../docs/research/research-map.md).

## Run

Synthetic boundary experiments:

```text
python -m pytest tests/research -q
```

Canonical repository-wide public verification:

```text
python scripts/verify.py
```

See [`docs/VERIFICATION.md`](../docs/VERIFICATION.md) for the pinned toolchain and exact gate semantics.
