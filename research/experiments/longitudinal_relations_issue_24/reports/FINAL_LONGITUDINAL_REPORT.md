# Validation of Time-First Longitudinal Relations Above SemanticBlock — Final Benchmark Report

**Issue:** #24  
**Date:** 2026-09-25  
**Status:** Milestone Passed — First Longitudinal Layer Verified  
**Authority:**  
- `docs/architecture/SEMANTIC_BLOCK_DESIGN_FREEZE_2026-09-25.md`  
- Issue #24: `[EXP: Validate time-first longitudinal relations above SemanticBlock]`

---

## 1. Executive Summary & Core Verdict

### Central Finding:
> **Time ordering acts as a decisive deterministic constraint, but time alone cannot manufacture knowledge.**  
> By pairing deterministic chronological precedence with **cognitive boundary projections (L2)**, the system reduces candidate search space by **93.5%** while achieving **100.0% recall** of true longitudinal transitions. Selective adjudication (L3) achieves **97.0% Dev accuracy** and **94.7% Held-Out accuracy**, with **0.0% confusion** between real-world state change and cognitive retraction.

All five pre-registered critical falsification tests (**F1 – F5**) passed unequivocally:
1. **F1 (Time Insufficiency):** 100% of temporally adjacent unrelated blocks were correctly rejected.
2. **F2 (No Retrospective Mutation):** 0 SemanticBlock content mutations across all 62 blocks (`SHA-256` identity preserved).
3. **F3 (Evidence-Driven Unknown Closure):** 0 unsupported unknown closures when time elapsed without new evidence.
4. **F4 (State Change vs Correction):** 0.0% confusion rate across all contrastive pairs.
5. **F5 (Sparse Candidate Formation):** 93.5% reduction vs all-pairs space with 100.0% candidate recall.

---

## 2. Experimental Progression: Candidate Formation (L0 $	o$ L1 $	o$ L2)

Evaluating over all 62 SemanticBlocks (1891 possible forward pairs):

| Level | Search Space / Method | Candidates Produced | Candidate Reduction | True Relation Recall | False Candidate Rate | Candidates / Block |
|---|---|---|---|---|---|---|
| **L0** | Time Only (Chronological Sequence) | 1889 | 0.1% | **100.0%** | 97.8% | 30.5 |
| **L1** | Time + Core Dense Embedding Sim ($\ge 0.65$) | 223 | 88.2% | 92.9% | 82.5% | 3.6 |
| **L2** | Time + Cognitive Boundary Projections | **123** | **93.5%** | **100.0%** | **65.9%** | **2.0** |

### Key Insight:
- **L0 (Time Only)** suffers from massive candidate explosion (1889 pairs, 97.8% noise). Pure time proximity provides no semantic filter.
- **L1 (Core Similarity)** filters out cross-domain noise but drops true recall to **92.9%** (88.9% on Dev) because structural transitions with low surface lexical overlap (e.g. cancellations or outcome statements) fall below dense thresholds.
- **L2 (Projections)** utilizes entity anchors, action/state transitions, localized unknowns, and revision cues to eliminate **93.5% of pairs** while retaining **100.0% recall** of true relations.

---

## 3. Selective Adjudication (L3) Across Dev and Held-Out Splits

| Metric | Dev Split (6 Domains, 33 Pairs) | Held-Out Split (4 Domains, 19 Pairs) | Benchmark Total |
|---|---|---|---|
| **Overall Accuracy** | **97.0%** | **94.7%** | **96.2%** |
| **Uncertainty Resolution Acc** | 100.0% (12/12) | 100.0% (5/5) | 100.0% (17/17) |
| **State Change Acc** | 100.0% (5/5) | 75.0% (3/4) | 88.9% (8/9) |
| **Correction / Retraction Acc** | 100.0% (5/5) | 100.0% (4/4) | 100.0% (9/9) |
| **State Change vs Correction Confusion** | **0.0%** | **0.0%** | **0.0%** |
| **Persistence Confirmation Acc** | 100.0% (4/4) | 100.0% (2/2) | 100.0% (6/6) |
| **Unrelated Rejection Acc** | 100.0% (6/6) | 100.0% (4/4) | 100.0% (10/10) |
| **SemanticBlock Content Mutations** | **0** | **0** | **0** |

---

## 4. Critical Falsification Verdicts

| ID | Falsification Assertion | Benchmark Evidence | Verdict |
|---|---|---|---|
| **F1** | **Time is necessary but insufficient** | Tested 10 unrelated temporal neighbors; 100.0% rejected as UNRELATED. | **PASSED** |
| **F2** | **Future evidence does not rewrite earlier truth** | 62 SemanticBlocks checked; 0 mutations; SHA-256 100% matched. | **PASSED** |
| **F3** | **UNKNOWN only closes with new evidence** | Audited elapsed-time probes; 0 unsupported closures; unknown kept open. | **PASSED** |
| **F4** | **State change != correction** | Evaluated 18 hard contrastive pairs; confusion between the two is 0.0%. | **PASSED** |
| **F5** | **Sparse candidate formation** | L2 candidate reduction is 93.5% vs all-pairs; true relation recall is 100.0%. | **PASSED** |

---

## 5. Cost and Operational Efficiency

- **Total LLM Adjudication Calls:** 52 (restricted strictly to bounded candidate pairs).
- **Adjudication Calls / Block:** 0.84 calls per SemanticBlock (no all-pairs comparison).
- **Tokens / Accepted Relation:** 2212.0 tokens.
- **Average Latency:** 4829.0 ms per candidate adjudication.

---

## 6. Architectural Conclusion

With Issue #24 validated:
- LCE has officially entered the **Longitudinal** layer.
- Local SemanticBlocks remain clean, unmutated local truths.
- Time provides deterministic authority.
- Bounded cognitive projections allow sparse candidate formation without graph bloat or pairwise brute-force reasoning.
