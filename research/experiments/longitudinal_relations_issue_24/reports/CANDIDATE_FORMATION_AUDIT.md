# Candidate Formation Audit: L0 vs L1 vs L2

**Issue:** #24  
**Date:** 2026-09-25

---

## 1. Candidate Generation Comparison

### Total Benchmark (62 Blocks, 1,891 Possible Forward Pairs):
- **L0 (Time Only):**
  - Generated: 1889 pairs
  - Candidate Reduction: 0.1%
  - True Relation Recall: 100.0%
  - False Candidate Rate: 97.8%
  - Pairs per Block: 30.5
- **L1 (Time + Core Similarity $\ge 0.65$):**
  - Generated: 223 pairs
  - Candidate Reduction: 88.2%
  - True Relation Recall: 92.9%
  - False Candidate Rate: 82.5%
  - Pairs per Block: 3.6
- **L2 (Time + Cognitive Boundary Projections):**
  - Generated: 123 pairs
  - Candidate Reduction: **93.5%**
  - True Relation Recall: **100.0%**
  - False Candidate Rate: **65.9%**
  - Pairs per Block: **2.0**

### Per-Split Breakdown:
| Split | Level | Total Possible | Candidates | Reduction | Recall | False Cand Rate |
|---|---|---|---|---|---|---|
| **Dev** | L0 | 741 | 739 | 0.3% | 100.0% | 96.3% |
| **Dev** | L1 | 741 | 119 | 83.9% | 88.9% | 79.8% |
| **Dev** | L2 | 741 | 78 | **89.5%** | **100.0%** | **65.4%** |
| **Held-Out** | L0 | 253 | 253 | 0.0% | 100.0% | 94.1% |
| **Held-Out** | L1 | 253 | 50 | 80.2% | 100.0% | 70.0% |
| **Held-Out** | L2 | 253 | 45 | **82.2%** | **100.0%** | **66.7%** |

## 2. Qualitative Analysis

1. **Why Dense Vector Baseline (L1) Misses True Transitions:**
   - In cases of external cancellation (e.g. `B_FLIGHT_01` vs `B_FLIGHT_02_CANCEL`), the surface vocabulary shifts from user intentions ("必须赶飞机") to weather/operational statements ("暴雨该航班已被官方取消"). Dense embeddings score lower similarity (~0.62), dropping below threshold.
2. **Why Cognitive Boundary Projections (L2) Excel:**
   - Instead of lexical similarity, L2 uses structural hooks:
     - `localized_unknowns` in $t_1$ ("是否顺利起飞") matched to $t_2$'s cancelled status.
     - Entity anchor overlap on key entities ("航班").
     - State transition cues (`current_requirement_obligation` $	o$ `cancelled_retracted`).
   - This recovers 100% of true relations while rejecting 93.5% of unrelated pairs.
