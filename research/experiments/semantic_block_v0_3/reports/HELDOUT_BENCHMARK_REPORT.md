# SemanticBlock v0.3 — Held-Out One-Shot Benchmark Report

**Date:** 2026-09-25
**Dataset:** 16 Held-Out Core Cases + 6 Held-Out Temporal Fork Branches (Total = 22 items)
**Status:** ONE-SHOT EXECUTION (No Tuning / Frozen Config)

---

## 1. Summary of Experimental Arms on Held-Out

| Metric | P0 (Raw Text) | P1 (Canonical Account) | P2 (Minimal Structured) | P3 (Atomized Control) | P4 (Legacy V1 Reference) |
|---|---|---|---|---|---|
| Must-Preserve Recall | 97.0% | 95.5% | 97.0% | 74.2% | 95.5% |
| Forbidden-Claim Rate | 3.0% | 0.0% | 0.0% | 6.1% | 2.3% |
| UNKNOWN Localization Acc | 76.4% | 81.4% | 75.4% | 40.5% | 80.0% |
| Attribution Fidelity | 100.0% | 100.0% | 100.0% | 79.5% | 99.1% |
| Temporal Locality | 93.2% | 95.5% | 93.2% | 86.4% | 95.5% |
| Full Case Equivalence | 81.8% | 68.2% | 63.6% | 27.3% | 77.3% |
| Severe Contamination Rate | 13.6% | 22.7% | 31.8% | 45.5% | 13.6% |
| Severe Contamination Count | 3 | 5 | 7 | 10 | 3 |
| Trivial Non-Structure Count | 22 | 0 | 0 | 0 | 0 |

## 2. Contrastive Structure Performance (Held-Out)

| Metric | P0 | P1 | P2 | P3 | P4 |
|---|---|---|---|---|---|
| Equivalence Cosine Sim | 0.9461 | 0.9360 | 0.9581 | 0.9901 | 0.9687 |
| Hard Negative Cosine Sim | 0.8601 | 0.8292 | 0.8892 | 0.8992 | 0.9179 |
| Separation Margin (EQ - HN) | +0.0859 | +0.1069 | +0.0689 | +0.0909 | +0.0507 |
| Equivalence Top-1 Recall | 57.1% | 85.7% | 85.7% | 57.1% | 57.1% |
| Granularity Collapse Rate | 17.1% | 12.2% | 12.2% | 14.6% | 17.1% |

## 3. Retrieval Recall Utility (Held-Out)

| Metric | P0 | P1 | P2 | P3 | P4 |
|---|---|---|---|---|---|
| Recall@1 | 75.0% | 66.7% | 91.7% | 75.0% | 91.7% |
| Recall@5 | 100.0% | 100.0% | 100.0% | 83.3% | 100.0% |
| MRR | 0.8750 | 0.8333 | 0.9444 | 0.7825 | 0.9444 |
| HN False Retrieval Rate | 16.7% | 25.0% | 8.3% | 25.0% | 8.3% |
| Distractor Rate (Top 3) | 5.6% | 5.6% | 2.8% | 16.7% | 2.8% |