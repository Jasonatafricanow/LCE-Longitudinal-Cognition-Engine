# LCE Research

This directory contains small, reproducible experiments that support selected LCE design decisions. They are deliberately independent from the LCE Core implementation and use only synthetic, offline inputs.

These experiments are the **public reproducibility surface for selected boundaries**. They are not the full historical research sequence that led to LCE V1.

For the broader development reasoning, start with:

- [`docs/RESEARCH_OVERVIEW.md`](../docs/RESEARCH_OVERVIEW.md) — problem framing, failed assumptions, architecture pivots, and correction methodology;
- [`docs/research/FINDINGS.md`](../docs/research/FINDINGS.md) — claim-by-claim evidence, limits, status, and negative results;
- [`docs/history/LCE_DECISION_EVOLUTION.md`](../docs/history/LCE_DECISION_EVOLUTION.md) — detailed `problem → evidence → failed assumption → decision → consequence` record;
- [`docs/history/LCE_MASTER_TIMELINE.md`](../docs/history/LCE_MASTER_TIMELINE.md) — reconstructed research / architecture / implementation / audit chronology.

## Reproducible boundary experiments

The experiments record falsifiable boundaries rather than presenting a large collection of historical runners:

- [Semantic neighbourhood](experiments/semantic_neighbourhood/README.md): similarity discovers candidates, not truth.
- [Region discovery](experiments/region_discovery/README.md): candidate structure should remain inspectable and preserve weak / isolated evidence.
- [Temporal cutoff](experiments/temporal_cutoff/README.md): longitudinal evaluation must enforce no-future visibility.

They deliberately do **not** reproduce the complete POINTCLOUD-01 → SEMANTIC-CLOUD-02 → BLOCK-03 → TREND-04 → INSPIRATION-05 → STRUCTURE-06R historical research corpus. That broader sequence is documented in the history and overview files above.

## Authority boundary

These experiments do not define canonical cognition, replace LCE Core authority, or claim that any interpretation is automatically canonical.

In particular:

```text
similarity / region / cutoff observation
→ candidate or evaluation evidence
!= factual Memory
!= accepted Understanding by itself
```

The conceptual path from candidate similarity through longitudinal structure to the LCE Core authority boundary is summarized in [`docs/research/research-map.md`](../docs/research/research-map.md).

## Run

From the repository root:

```text
python -m pytest tests/research -q
```
