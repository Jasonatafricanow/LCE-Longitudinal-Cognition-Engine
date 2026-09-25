# SemanticBlock v0.3 — Dev Benchmark Report

**Date:** 2026-09-25
**Dataset:** 32 Core Cases + 6 Temporal Fork Branches (Total = 38 items)
**Status:** Complete Dev Run (Phase C)

---

## 1. Summary of Experimental Arms on Dev

| Metric | P0 (Raw Text) | P1 (Canonical Account) | P2 (Minimal Structured) | P3 (Atomized Control) | P4 (Legacy V1 Reference) |
|---|---|---|---|---|---|
| Must-Preserve Recall | 97.8% | 96.3% | 97.8% | 73.0% | 98.7% |
| Forbidden-Claim Rate | 0.9% | 2.2% | 6.1% | 7.5% | 0.0% |
| UNKNOWN Localization Acc | 73.2% | 74.0% | 82.1% | 48.7% | 82.1% |
| Attribution Fidelity | 100.0% | 100.0% | 100.0% | 81.6% | 100.0% |
| Temporal Locality | 98.7% | 98.7% | 97.4% | 84.2% | 100.0% |
| Full Case Equivalence | 79.0% | 76.3% | 84.2% | 47.4% | 84.2% |
| Severe Contamination Rate | 23.7% | 26.3% | 15.8% | 34.2% | 15.8% |
| Severe Contamination Count | 9 | 10 | 6 | 13 | 6 |
| Trivial Non-Structure Count | 38 | 0 | 0 | 0 | 0 |

## 2. Contrastive Structure Performance (Dev)

| Metric | P0 | P1 | P2 | P3 | P4 |
|---|---|---|---|---|---|
| Equivalence Cosine Sim | 0.9541 | 0.9455 | 0.9697 | 0.7556 | 0.9715 |
| Hard Negative Cosine Sim | 0.8444 | 0.7899 | 0.8437 | 0.8645 | 0.9058 |
| Separation Margin (EQ - HN) | +0.1097 | +0.1556 | +0.1259 | -0.1089 | +0.0657 |
| Equivalence Top-1 Recall | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% |
| Granularity Collapse Rate | 1.5% | 1.5% | 1.5% | 89.5% | 1.5% |

## 3. Retrieval Recall Utility (Dev)

| Metric | P0 | P1 | P2 | P3 | P4 |
|---|---|---|---|---|---|
| Recall@1 | 91.7% | 100.0% | 100.0% | 58.3% | 91.7% |
| Recall@5 | 100.0% | 100.0% | 100.0% | 75.0% | 100.0% |
| MRR | 0.9583 | 1.0000 | 1.0000 | 0.6466 | 0.9583 |
| HN False Retrieval Rate | 0.0% | 0.0% | 0.0% | 33.3% | 0.0% |
| Distractor Rate (Top 3) | 27.8% | 27.8% | 27.8% | 33.3% | 22.2% |

## 4. Stage D2: Structure-Only Ablation on P2 (Dev)

- **Separation Margin without Natural Language Account:** +0.0993
- **Equivalence Top-1 Recall without NL Account:** 100.0%
- **Retrieval MRR without NL Account:** 0.8500
- **Retrieval Recall@5 without NL Account:** 100.0%

## 5. Temporal Fork Consistency on Dev

Prefix dialogue compiled strictly at prefix cutoff turn. Verified that future outcomes were not injected into cutoff.
- **TF-01-FLIGHT** (branches: ['TF-01-A', 'TF-01-B', 'TF-01-C']): 100% uniform prefix gold across branches.
- **TF-02-REPORT** (branches: ['TF-02-A', 'TF-02-B', 'TF-02-C']): 100% uniform prefix gold across branches.