# SemanticBlock v0.2 Benchmark Evaluation Report (B / C / E)

**Date:** 2026-09-24  
**Git HEAD:** `11bac4a8a822c69a60b9607f86d17f79ddd960ab` (`research/semantic-block-issue-20`)  
**Gold Corpus:** `C:\projects\semantic_block_v0_2_adjudication\gold_v0_2.jsonl` (Adjudicated, 24 cases / 26 cutoffs)  
**Gold SHA-256:** `7d43bda833d521968893b6a97032c1326e1adb3a3a9121763bc739b41e6ec1a8`  
**Input SHA-256:** `44fcc4a8247106033edc31874eb9ecc8ce292270bee5db3956123b77189d6041`  
**Probe SHA-256:** `3df68318302822129827b8fdbe7dcd53aab3d30b362dec17ce18059edf84af83`  
**Model Family:** `gemini-3.1-flash-lite` (Seed: 42, Temperature: 0.0)  
**Embedding Model:** `gemini-embedding-001`  
**Overall Pre-Registered Verdict:** **`BLOCKED / INCONCLUSIVE`** (No production promotion authorized)

---

## 1. Executive Summary & Arm Verdicts

Per `BENCHMARK_V02_PROTOCOL.md` and `ROUTE_E_DESIGN.md`, this benchmark evaluates whether Route E (B's one-pass semantics + deterministic fail-closed admission gates + selective cross-block linker) resolves the fundamental architectural dilemma between Arm B (one-pass, high recall but prone to dangling endpoints and ungrounded assertions) and Arm C (two-pass, disciplined relations but high latency and token cost).

All 26 cutoff evaluations across 12 unseen scenario families (`U01`–`U12`) were executed under the exact frozen candidate inputs and adjudicated gold.

| Arm | Description | Micro Field Acc | Macro Family Acc | Exact Block Count | Relations F1 | Hard Gate Status | Exploratory Verdict |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **B** | One-pass structured proposal + minimal validator | 53.50% | 53.45% | 61.5% | 80.0% | FAIL (41 violations, 2 invalid endpoints) | **`BLOCKED`** |
| **C** | Two-pass proposal + full normalization + typed linker | 57.09% | 56.92% | 61.5% | 61.5% | FAIL (37 violations, 0 invalid endpoints) | **`BLOCKED`** |
| **E** | B one-pass semantics + fail-closed gates + selective linker | 35.90% | 33.89% | 34.6% | 30.8% | FAIL (33 violations, 0 invalid endpoints) | **`BLOCKED`** |
| **E (no linker)** | Paired ablation: B first-pass + gates only (linker disabled) | 35.90% | 33.89% | 34.6% | 0.0% | FAIL (28 violations, 0 invalid endpoints) | **`BLOCKED`** |

> [!IMPORTANT]
> **Production Decision:** All three arms are **`BLOCKED`** from production promotion. 
> 1. None of the arms achieved the pre-registered accuracy ceiling (>= 90%) or clean safety gate status.
> 2. Pervasive silent holder flips (`user/narrator -> user`) affect the base LLM prompt in 33+ cases across all arms.
> 3. Route E successfully eliminated runtime invalid relation endpoints (0 in E vs 2 in B) and called the second-pass linker in only 2 of 26 cases (7.7% invocation rate, saving 18 LLM calls and 10,890 tokens vs Arm C).
> 4. However, Route E's strict non-mutating Gate 4 (`modal_or_conditional_marker_promoted_to_asserted`) rejected 11 candidate blocks entirely rather than repairing them, causing field recall to drop sharply on counterfactual and deontic families (`U02`, `U04`, `U09`, `U12`).

---

## 2. Comparative Benchmark Matrix (26 Cutoffs / 12 Unseen Families)

| Metric | Arm B | Arm C | Arm E | E (no linker ablation) | Delta (E vs B) | Delta (E vs C) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Micro Field Accuracy** | 53.50% (313/585) | **57.09%** (334/585) | 35.90% (210/585) | 35.90% (210/585) | -17.60% | -21.19% |
| **Macro Family Accuracy** | 53.45% | **56.92%** | 33.89% | 33.89% | -19.56% | -23.03% |
| **Exact Block Count Match** | **61.5%** (16/26) | **61.5%** (16/26) | 34.6% (9/26) | 34.6% (9/26) | -26.9% | -26.9% |
| **Account Exact Match** | **4.4%** (2/45) | **4.4%** (2/45) | 0.0% (0/45) | 0.0% (0/45) | -4.4% | -4.4% |
| **Relations TP** | **6** | 4 | 2 | 0 | -4 | -2 |
| **Relations FP** | **0** | **0** | 2 | **0** | +2 | +2 |
| **Relations FN** | **3** | 5 | 7 | 9 | +4 | +2 |
| **Relations Precision** | **100.0%** | **100.0%** | 50.0% | 0.0% | -50.0% | -50.0% |
| **Relations Recall** | **66.7%** | 44.4% | 22.2% | 0.0% | -44.5% | -22.2% |
| **Relations F1** | **80.0%** | 61.5% | 30.8% | 0.0% | -49.2% | -30.7% |
| **Invalid Relation Endpoints** | 2 (V2-002, V2-003) | **0** | **0** | **0** | **-2 (Fixed)** | 0 |
| **Total Hard Failures** | 41 | 37 | **33** | **28** | **-8** | **-4** |
| **Forbidden Violations** | **0** | **0** | **0** | **0** | 0 | 0 |
| **Total LLM Calls** | 26 | 46 | 28 | **26** | +2 | **-18 (-39.1%)** |
| **Linker Invocations** | 0 (one-pass) | 20 (76.9%) | 2 (7.7%) | 0 | +2 | **-18 (-90.0%)** |
| **Total Tokens** | **54,553** | 68,418 | 57,528 | 54,553 | +2,975 (+5.5%) | **-10,890 (-15.9%)** |
| **Prompt Tokens** | **39,212** | 53,654 | 41,619 | 39,212 | +2,407 | -12,035 |
| **Completion Tokens** | 15,341 | **14,764** | 15,909 | 15,341 | +568 | +1,145 |
| **Median Latency (ms)** | **16,373** | 111,548 | 16,637 | 16,373 | +264 (+1.6%) | **-94,911 (-85.1%)** |
| **P95 Latency (ms)** | **50,332** | 909,034 | 71,479 | 50,332 | +21,147 | **-837,555 (-92.1%)** |

---

## 3. Scenario Family Breakdown (U01 – U12)

The 24 evaluation cases were mapped to 12 unseen scenario families. Across 8 of the 12 families, Route E achieved field accuracy matching Arm B:

| Family ID | Scenario Family Description | Arm B Field Acc | Arm C Field Acc | Arm E Field Acc | Arm B EBC | Arm C EBC | Arm E EBC |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **U01** | `U01_nested_report_chain` | 51.3% | 53.8% | 51.3% | 50% | 50% | 50% |
| **U02** | `U02_counterfactual_world` | 43.6% | 48.7% | 7.7% | 50% | 50% | 0% |
| **U03** | `U03_negated_causal_scope` | 46.2% | 53.8% | 46.2% | 0% | 0% | 0% |
| **U04** | `U04_deontic_requirement` | 51.9% | 55.8% | 13.5% | 100% | 100% | 0% |
| **U05** | `U05_quantifier_exception` | 64.1% | 64.1% | 64.1% | 50% | 50% | 50% |
| **U06** | `U06_recurrence_cardinality` | 56.4% | 56.4% | 56.4% | 50% | 50% | 50% |
| **U07** | `U07_source_retraction` | 42.3% | 47.4% | 42.3% | 50% | 50% | 50% |
| **U08** | `U08_quantity_precision` | 33.3% | 35.9% | 33.3% | 100% | 100% | 100% |
| **U09** | `U09_reciprocal_roles` | 96.2% | 92.3% | 0.0% | 100% | 100% | 0% |
| **U10** | `U10_passive_agent` | 42.3% | 42.3% | 42.3% | 50% | 50% | 50% |
| **U11** | `U11_disjunctive_failure` | 56.4% | 56.4% | 56.4% | 50% | 50% | 50% |
| **U12** | `U12_timezone_day_boundary` | 73.1% | 88.5% | 0.0% | 100% | 100% | 0% |

### Key Family Analysis
1. **Identical Performance in Regular Discourse (U01, U05, U06, U07, U08, U10, U11):**  
   In all 7 regular discourse and quantifier families, Route E admitted 100% of B's valid proposed blocks without false rejections, preserving B's exact field accuracy and exact block count rates.
2. **Epistemic Divergence (U02, U04, U09, U12):**  
   In counterfactuals (`U02`), deontic requirements (`U04`), reciprocal interactions (`U09`), and cross-timezone statements (`U12`), the first-pass model emitted `modality: "asserted"`. Route E's Gate 4 flagged conditional/modal cues in the text ("would", "should", "required to") and fail-closed rejected 11 blocks. Because Route E is non-rewriting by design, rejecting the blocks sacrificed recall against gold states that required those blocks.

---

## 4. Field-by-Field Accuracy Comparison

Accuracy across all 13 semantic fields over the 45 gold visible states:

| Semantic Field | Arm B Correct / Total | Arm C Correct / Total | Arm E Correct / Total | Arm B Acc | Arm C Acc | Arm E Acc |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **availability** | 45 / 45 | 45 / 45 | 34 / 45 | **100.0%** | **100.0%** | 75.6% |
| **modality** | 40 / 45 | 40 / 45 | 31 / 45 | **88.9%** | **88.9%** | 68.9% |
| **polarity** | 39 / 45 | 39 / 45 | 29 / 45 | **86.7%** | **86.7%** | 64.4% |
| **attribution_mode** | 35 / 45 | 37 / 45 | 26 / 45 | 77.8% | **82.2%** | 57.8% |
| **epistemic_hedge** | 33 / 45 | 33 / 45 | 22 / 45 | **73.3%** | **73.3%** | 48.9% |
| **utterer** | 25 / 45 | 25 / 45 | 16 / 45 | **55.6%** | **55.6%** | 35.6% |
| **canonical_content** | 21 / 45 | 25 / 45 | 11 / 45 | 46.7% | **55.6%** | 24.4% |
| **provenance** | 21 / 45 | 29 / 45 | 12 / 45 | 46.7% | **64.4%** | 26.7% |
| **participants** | 17 / 45 | 23 / 45 | 11 / 45 | 37.8% | **51.1%** | 24.4% |
| **predicate_kind** | 14 / 45 | 14 / 45 | 8 / 45 | **31.1%** | **31.1%** | 17.8% |
| **holder** | 12 / 45 | 13 / 45 | 6 / 45 | 26.7% | **28.9%** | 13.3% |
| **entity_status_uncertainty** | 9 / 45 | 9 / 45 | 4 / 45 | **20.0%** | **20.0%** | 8.9% |
| **valid_time_precision** | 2 / 45 | 2 / 45 | 0 / 45 | **4.4%** | **4.4%** | 0.0% |

---

## 5. Critical F8 Retrieval Sentinel Results

The F8 probe suite tests vector-only vs. vector + traversable relation graph retrieval on unseen family `U03` (`V2-005` positive causal chain and `V2-006` negative control):

| Probe ID | Type / Fixture | Arm | Extraction Path Gate | Retrieval Budget Gate (k=3) | Before Bridge Detected | Vector Only (P / R) | Vector + Graph (P / R) | F8 Gate Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **U03-positive-V2-005** | Positive Causal Chain | **B** | **PASS** | **PASS** | **CLEAN (False)** | 0.33 / 0.50 | **0.67 / 1.00** | **`PASS`** |
| **U03-negative-V2-006** | Negative Temporal Control | **B** | **PASS** | **PASS** | **CLEAN (False)** | 0.33 / 0.50 | 0.33 / 0.50 | **`PASS`** |
| **U03-positive-V2-005** | Positive Causal Chain | **C** | **PASS** | **PASS** | **CLEAN (False)** | 0.67 / 1.00 | **0.67 / 1.00** | **`PASS`** |
| **U03-negative-V2-006** | Negative Temporal Control | **C** | **PASS** | **PASS** | **CLEAN (False)** | 0.33 / 0.50 | 0.33 / 0.50 | **`PASS`** |
| **U03-positive-V2-005** | Positive Causal Chain | **E** | **PASS** | **PASS** | **CLEAN (False)** | 0.33 / 0.50 | **0.67 / 1.00** | **`PASS`** |
| **U03-negative-V2-006** | Negative Temporal Control | **E** | **PASS** | **PASS** | **CLEAN (False)** | 0.33 / 0.50 | 0.33 / 0.50 | **`PASS`** |

### Key F8 Findings
1. **Graph Retrieval Gain Confirmed:** Under strict $k=3$ candidate budget clipping, graph augmentation along valid directed `CAUSE` edges improved relevant recall from 50.0% to 100.0% in Arms B and E, doubling precision from 0.33 to 0.67.
2. **Zero False BEFORE Bridges:** In all three arms, `BEFORE` edges strictly enforced `traversal_allowed=False`. Zero generic before-bridge candidate states were proposed, passing the negative sentinel cleanly.
3. **Route E Linker Selectivity:** In `V2-005`, Route E's candidate screening detected valid cross-block causal cue spans, triggered the selective linker, admitted the true causal edges, and achieved identical 100% recall to Arm B and Arm C without invoking the linker across unpromising cases.

---

## 6. Route E Gate Trace & Linker Selectivity Analysis

Detailed trace analysis from `E_gate_trace.json`:
- **First-Pass Block Candidates:** 58 candidates across 26 cutoffs.
- **Admitted Blocks:** 47 (81.0% admission rate).
- **Rejected Blocks:** 11 (19.0% rejection rate).
  - All 11 rejections were triggered by **Gate 4**: `modal_or_conditional_marker_promoted_to_asserted`.
  - Zero rejections for invalid evidence ID, coordinate mismatch, or duplicate authority.
- **Cross-Block Screening & Linker Decisions:**
  - Linker Called: **2 / 26 cutoffs (7.7%)** (`V2-005`, `V2-006`).
  - Linker Abstained: **24 / 26 cutoffs (92.3%)**.
  - Screened Candidate Pairs: 9 total (4 in `V2-005`, 5 in `V2-006`).
  - Admitted Relations: 7 total (2 `CAUSE` in `V2-005`, 5 `BEFORE` in `V2-006`).
  - Candidate Capping: Strict 8-pair ceiling was never exceeded (max observed: 5 pairs in `V2-006`).
  - Transitive Shortcut Suppression: 0 transitive direct shortcuts generated.

---

## 7. Pre-Registered Reproducibility Manifest

```json
{
  "benchmark_version": "v0.2",
  "created_at_utc": "2026-09-24T10:46:40Z",
  "git_head": "11bac4a8a822c69a60b9607f86d17f79ddd960ab",
  "git_branch": "research/semantic-block-issue-20",
  "gold_sha256": "7d43bda833d521968893b6a97032c1326e1adb3a3a9121763bc739b41e6ec1a8",
  "input_sha256": "44fcc4a8247106033edc31874eb9ecc8ce292270bee5db3956123b77189d6041",
  "probe_sha256": "3df68318302822129827b8fdbe7dcd53aab3d30b362dec17ce18059edf84af83",
  "prompt_sha256": {
    "B_semantic": "23b94fdb06a2573bcc7391a9763ca463677225dc7855daa588d850a73721b36c",
    "C_semantic": "78e8b8d52f339ec8487a139a27daeed7213b73a144f632062f675a799943457d",
    "C_linker": "0d479caa650264e65a9cb3d554398dc90e7858cf5e78d1c1454a746d52f1af5a",
    "E_semantic_equals_B": "23b94fdb06a2573bcc7391a9763ca463677225dc7855daa588d850a73721b36c",
    "E_linker": "78fcb12db6eb5824a3f5937a338d89e63b78bc7ca99d9bdb677b08e1dfabd96f"
  },
  "model": "gemini-3.1-flash-lite",
  "embedding_model": "gemini-embedding-001",
  "temperature": 0.0,
  "seed": 42
}
```

---

## 8. Conclusion & Production Decision

1. **Production Verdict: `BLOCKED`**  
   Neither Arm B, Arm C, nor Route E meets the threshold for production compiler design on v0.2 unseen families. The presence of 33+ hard safety failures across all arms (primarily silent holder flips in prompt output) and field accuracies below 60% indicate that compiler prompt representations require systematic revision before production graduation.
2. **Validation of Route E Invariants:**  
   Route E successfully validated its core architectural hypotheses:
   - **Zero Invalid Endpoints:** Completely eliminated Arm B's dangling relation defect through deterministic endpoint closure.
   - **Selective Linker Efficiency:** Reduced linker LLM calls by 90% (2 vs 20) and total tokens by 15.9% compared to Arm C, while preserving graph retrieval efficacy in F8.
   - **Traversal Safety:** Enforced `traversal_allowed=False` on `BEFORE` edges and suppressed direct transitive causal shortcuts.
3. **The Non-Rewriting Gate Dilemma:**  
   Route E's adherence to the strict non-rewriting policy exposed a critical design tension: rejecting ungrounded modal assertions avoids corrupting canonical state, but sacrifices block recall when the underlying factual statement was genuine. Future work should investigate calibrated fallback to `UNKNOWN` or bounded entity re-annotation rather than outright block rejection.
