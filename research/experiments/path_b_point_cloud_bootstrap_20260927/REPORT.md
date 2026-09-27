# Path B Point-Cloud Bootstrap Algorithm Bakeoff

**Date:** 2026-09-27  
**Branch:** `verification/path-b-point-cloud-bootstrap-20260927`  
**Base:** `925d599c2df4f283df4b1739e07dbdcfe1061223`  
**Frozen A4 algorithm commit:** `c57a39b98c9c71cc7505243c3900349577477012`  
**Fresh holdout added after freeze:** `e5e824fc065bc64c2ae7840387349aa28f08def2`  
**Evaluated implementation:** `8c9d08608d1ab0602407c2f6bd7e9af6f1f5f7c7`

GitHub Actions evidence:
- Path B Point Cloud Bootstrap run `36311496331`: PASS
- Public Verification run `36311496370`: PASS

## Question

Standalone Path B should not infer longitudinal cognition from one isolated raw text.

The tested question is:

> As many local SemanticBlock-like semantic points accumulate over time, does a stable latent structure become easier to discover, and can that structure seed a Worktree without an upstream MR Thread?

The structural algorithms never read gold trend labels.

## Development corpus

152 points over 316 days:

- 108 points belonging to six persistent latent trends;
- 20 points in five short coherent bursts;
- 24 sparse one-off noise points.

Two separate trends share each broad domain, so domain similarity by itself is not enough.

### Algorithms

- **A0 Pair Components:** threshold graph over pairwise semantic similarity.
- **A1 Mutual-kNN:** static mutual-neighbour graph.
- **A2 Recurrent Density:** local density + temporal recurrence.
- **A3 Multiscale Recurrent:** recurrent-density candidates must survive multiple scales.
- **A4 Persistent Mutual-kNN:** mutual-kNN components are emitted only if they have enough support, temporal recurrence, time-bucket coverage, and semantic cohesion.

A2/A3 achieved high recall early but emitted dozens of overlapping candidates and fragmented one true trend into many candidate structures. They are useful evidence suppliers, but poor direct Worktree-seed suppliers in this form.

A1 had low fragmentation, but around half its full-history candidates were false seeds.

A4 kept A1's low-fragmentation geometry while using time and cohesion to reject transient/broad components.

## A4 development curve

Frozen operating point:

```text
k = 4
min_similarity = 0.10
min_support = 4
min_span_days = 42
min_time_buckets = 3
bucket_days = 45
min_cohesion = 0.15
```

| Visible points | Trend recall | Candidates | False seed rate | Fragmentation |
|---:|---:|---:|---:|---:|
| 40 | 0% | 0 | 0% | 0 |
| 70 | 66.7% | 4 | 0% | 1.0 |
| 100 | 100% | 6 | 0% | 1.0 |
| 130 | 100% | 6 | 0% | 1.0 |
| 152 | 100% | 6 | 0% | 1.0 |

The data-volume effect is explicit: A4 emits nothing when evidence is too sparse, then recovers more trends as the point cloud fills out.

The full dev corpus initially produced one false six-point component made only from recurring broad one-off noise. Its mean pairwise semantic cohesion was `0.1404`, while the six true full-history components were `0.2529..0.3152`. A development sweep showed `min_cohesion = 0.15..0.25` preserved 100% trend recall and removed that false component. The lower edge `0.15` was frozen before the holdout corpus was added.

A4 was also stable at `k=4` and `k=5` across minimum span settings of 30/60/90 days. `k=6` merged too aggressively and dropped recall to 66.7%.

## Temporal negative control

The true-trend semantics/cardinality were preserved, but each long-lived trend was compressed into a short temporal episode.

Development corpus:

```text
normal:    recall 100%, 6 candidates, 0% false
collapsed: recall   0%, 0 candidates
```

This indicates A4 is not merely clustering static semantic geometry; the seed requires persistence through time.

## Fresh frozen-A4 holdout

The holdout was written after A4 was frozen.

130 points:

- 84 trend points;
- 16 short-burst decoys;
- 30 one-off noise points;
- six new latent trends with different feature pools and more cross-context overlap.

No A4 parameter was changed after the holdout was created.

### Holdout recall curve

| Visible points | A4 trend recall | Candidates | False seed rate | Purity | Fragmentation |
|---:|---:|---:|---:|---:|---:|
| 40 | 0% | 0 | 0% | — | 0 |
| 70 | 33.3% | 2 | 0% | 100% | 1.0 |
| 100 | 83.3% | 5 | 0% | 100% | 1.0 |
| 130 | 100% | 6 | 0% | 100% | 1.0 |

For comparison at 130 points:

- A0 Pair Components: 100% recall, 26.7% false candidates, 1.83 fragments per discovered trend.
- A1 Mutual-kNN: 100% recall, 57.1% false candidates, 1.0 fragmentation.
- A4 Persistent Mutual-kNN: 100% recall, 0% false candidates, 1.0 fragmentation.

Holdout temporal-collapse control:

```text
normal:    recall 100%, 6 candidates, 0% false
collapsed: recall   0%, 0 candidates
```

## How much evidence was required?

On the fresh holdout, the first valid Worktree seed appeared at different evidence volumes depending on how semantically coherent the latent trend was:

| Trend | Total visible history when first discovered | Supporting points from that trend |
|---|---:|---:|
| VISUAL_REALISM | 34 | 4 |
| ENGINEERING_MINIMAL_CORE | 69 | 8 |
| TRADING_WAIT_FOR_EDGE | 71 | 8 |
| WRITING_CAUSAL_DENSITY | 72 | 8 |
| LONGITUDINAL_MEMORY_ARCH | 74 | 8 |
| META_UNCERTAINTY_DISCIPLINE | 117 | 13 |

This is the strongest result of the experiment.

There is no single universal "four points create cognition" rule. Some coherent structures emerge quickly; a diffuse cross-context tendency needed 13 independent local points before the same frozen algorithm could distinguish it cleanly.

That behaviour matches the intended Point Cloud concept better than per-message relation discovery.

## Interpretation

The evidence currently supports this mechanism:

```text
many local SemanticBlocks
        ↓
semantic neighbourhood geometry
        ↓
persistent mutual connectivity
        +
longitudinal recurrence
        +
minimum semantic cohesion
        ↓
Worktree seed
        ↓
existing Worktree / Snake continuation
```

Time is not a maximum-age filter. Old evidence remains usable. Time contributes evidence that a semantic structure is persistent rather than a short coherent burst.

The important empirical shape is:

```text
more relevant history
→ latent structure becomes separable
→ recall rises
→ Worktree appears
```

rather than:

```text
one new point
→ search one old point
→ invent cognition immediately
```

## What this does not prove

This experiment uses structured semantic feature fixtures as a stand-in for production SemanticBlock representations. It therefore tests **point-cloud structure discovery**, not language understanding or production embedding quality.

The 100% final recall is not a production recall claim.

A production-equivalent next test would keep A4 structurally frozen and replace the hand-authored semantic feature sets with real SemanticBlock embeddings/projections from a larger corpus. The main quantities to preserve are the history-size recall curve, false Worktree seed rate, seed latency, temporal-collapse sensitivity, and branch fragmentation.

## Current conclusion

**SUPPORTED as a standalone Path B bootstrap mechanism candidate.**

More specifically:

- static point similarity alone finds trends but admits too much noise;
- local recurrent-density suppliers recall aggressively but fragment badly;
- persistent mutual-kNN + semantic cohesion produces a much cleaner Worktree-seed boundary on both development and fresh holdout corpora;
- discovery recall increases materially with accumulated data;
- diffuse cross-context cognition requires substantially more evidence than narrow coherent cognition;
- none of this is required for the MR production path, where mature Thread already supplies the seed.
