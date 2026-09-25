# Report Inconsistency Audit: Root Cause Accounting (Issue #23)

**Date:** 2026-09-25  
**Audit Target:** Inconsistencies between narrative summaries and raw data tables in Issue #22 benchmark reports:
1. `research/experiments/semantic_block_issue_22/reports/FINAL_BENCHMARK_REPORT.md`
2. `research/experiments/semantic_block_issue_22/reports/CANDIDATE_COST_REPORT.md`
**Source Code Inspected:** `research/experiments/semantic_block_issue_22/generate_reports.py`

---

## 1. Executive Accounting Summary

Our deterministic audit revealed a clear pattern:
- **All Markdown tables** in the reports were dynamically generated from `held_out_results.json` and `cost_summary.json`. Their values are 100% faithful to the underlying benchmark execution.
- **The narrative prose sections** (Executive Summary, Decision Logic Assessment, and Cost Analysis Conclusion) were written as **static, hardcoded text strings** in `generate_reports.py`.
- These hardcoded strings originated from early design drafts, hypothetical expectations, or uncalibrated early prototypes and were never updated to match the final execution data.

Below is the line-by-line reconciliation of every identified discrepancy.

---

## 2. Inconsistency 1: B0 Baseline Performance (Recall@5 & Rank Metrics)

### The Discrepancy
- **Narrative Claim (`FINAL_BENCHMARK_REPORT.md` Section 1, lines 19–20):**
  > *"On Held-Out (K=5), B0 achieves 83.3% Recall@5, but only 58.3% Recall@1, with a high 25.0% hard-negative false presence rate and 66.7% final accepted target recall due to candidates missing narrow budgets."*
- **Report Table 1 (`FINAL_BENCHMARK_REPORT.md` line 41):**
  - Arm B0 Method R0: Recall@5 = **100.0%**, First Rank = **1.17**, HN Presence = **75.0%**, Adj Precision = **91.7%**, Final Accepted Recall = **88.5%**.

### Raw Execution Ground Truth (`results/held_out_results.json`)
- **Recall@5:** $12 / 12 = \mathbf{100.0\%}$. Every single one of the 12 held-out queries retrieved at least one true target in top 5 candidates.
- **Recall@1:** 10 out of 12 queries retrieved a true target at Rank 1. Thus Recall@1 is $10 / 12 = \mathbf{83.3\%}$ (Mean First Rank = $14 / 12 = 1.167$), not 58.3%.
- **Hard Negative Presence Rate:** 9 out of 12 queries contained a hard negative in the top 5 candidates ($9 / 12 = \mathbf{75.0\%}$), not 25.0%.
- **Final Accepted Target Recall:** $(10 \times 1.0 + 1 \times 0.0 + 1 \times 0.625) / 12 = 85 / 96 = \mathbf{88.54\%}$, not 66.7%.

### Root Cause in Source Code
In `generate_reports.py`, lines 61–62:
```python
lines.append(
    "1. **Core-Vector Baseline (B0 / R0) has Solid Broad Recall but Severe"
    " Discrimination Gaps Under Same-Surface/Different-Meaning Pressure:**"
)
lines.append(
    "   - On Held-Out (K=5), B0 achieves 83.3% Recall@5, but only 58.3%"
    " Recall@1, with a high **25.0% hard-negative false presence rate** and"
    " 66.7% final accepted target recall due to candidates missing narrow"
    " budgets."
)
```
The report author manually typed `83.3% Recall@5` (which was actually the `Recall@1` metric!) and invented `58.3%`, `25.0%`, and `66.7%` as hypothetical text prior to executing the benchmark.

---

## 3. Inconsistency 2: B4 Budget K=3 Recall Discrepancy

### The Discrepancy
- **Narrative Claim (`FINAL_BENCHMARK_REPORT.md` Section 3, line 90):**
  > *"Under B2/B4 with R1/R3 reranking and soft expansion, Recall@3 reaches 91.7% (target miss rate 8.3%). Targets that fell to ranks 4-6 under pure lexical/dense similarity were recovered into top 3."*
- **Report Table 3 (`CANDIDATE_COST_REPORT.md` line 30):**
  - Arm B4 Method R1 Budget K=3: Recall@K = **100.0%**, Mean Rank = **1.33**, Adj Precision = **100.0%**.

### Raw Execution Ground Truth (`results/held_out_results.json`)
- In `held_out_results.json` under `evaluations.B4.R1.k_3`:
  - `mean_recall_at_k`: **1.0** ($12 / 12 = 100.0\%$).
  - `target_miss_rate`: **0.0** ($0 / 12 = 0.0\%$).
  - `mean_first_target_rank`: **1.3333**.
  - Across all 12 held-out queries, at least one target was present in the top 3 candidates. No query missed top-3 recall.

### Root Cause in Source Code
In `generate_reports.py`, line 124:
```python
lines.append(
    "   - **YES.** On Held-Out with narrow budget K=3, B0/R0 Recall@3 is only"
    " 66.7% (target miss rate 33.3%). Under B2/B4 with R1/R3 reranking and soft"
    " expansion, Recall@3 reaches **91.7%** (target miss rate 8.3%). Targets"
    " that fell to ranks 4-6 under pure lexical/dense similarity were recovered"
    " into top 3."
)
```
The author hardcoded `91.7%` (presumably 11/12) based on an early expectation that one query would miss top-3 candidates, but in the final run, all 12 queries retrieved targets within top 3.

---

## 4. Inconsistency 3: Hard Negative Presence Rate 75.0% Across All Columns

### The Discrepancy
- **Observation:** In `FINAL_BENCHMARK_REPORT.md` Table 1, the `(2) HN Presence` column is exactly **75.0%** for all 18 rows (B0 through B4, R0 through R3).
- **Narrative Claim (`FINAL_BENCHMARK_REPORT.md` lines 23 and 96):**
  - Line 23: *"0.0% Hard Negative intrusion at rank 1"*
  - Line 96: *"R1 decisively beat R2 by -16.7% HN presence"*

### Raw Execution Ground Truth (`results/held_out_results.json`)
- **Metric Definition in Code:**
  `hard_negative_present = any(cand.item_id in q.get("hard_negative_case_ids", []) for cand in cands_5)`
  This metric measures candidate presence *anywhere in the top 5*, NOT intrusion at rank 1.
- **Per-Query Presence Breakdown:**
  - Queries `RQ-H01` through `RQ-H09` (9 queries): Hard negatives have high lexical similarity with the query (sharing words, entities, topics) and are pulled into the top 5 by dense vector retrieval.
  - Queries `RQ-H10` through `RQ-H12` (3 queries): Hard negatives are ranked below rank 5.
  - Fraction: $9 / 12 = \mathbf{75.0\%}$.
- **Why It Repeats Across All Arms:**
  Because the primary candidate pool is established by dense retrieval, all 5 candidates are retained in budget $K=5$. Reranking reorders candidates within the top 5, but soft reranking does not prune or discard items. Thus, if a hard negative entered the top 5 during broad retrieval, it remains in the top 5 regardless of reranking arm.
- **The Narrative Error:**
  The author confused "hard negative ranked at rank 1" (which was indeed prevented by reranking) with "hard negative present in candidate package" (which stayed at 75%). The claim of "-16.7% HN presence" was pure fiction written in the narrative template.

---

## 5. Inconsistency 4: Token Cost Expansion Arithmetic

### The Discrepancy
- **Narrative Claim (`CANDIDATE_COST_REPORT.md` Section 3, line 34):**
  > *"Cost Analysis Conclusion: Expanding projections increases candidate package prompt tokens by ~35% (from 410 tokens in B0 to ~550 tokens in B4)..."*
- **Report Table 2 (`CANDIDATE_COST_REPORT.md` lines 20–24):**
  - Arm B0: Mean Candidate Tokens = **206.8**, Adjudicator Prompt Tokens = **808.9**.
  - Arm B1: Mean Candidate Tokens = **730.3**, Adjudicator Prompt Tokens = **1199.7**.
  - Arm B2: Mean Candidate Tokens = **1046.3**, Adjudicator Prompt Tokens = **1407.8**.
  - Arm B3: Mean Candidate Tokens = **1629.0**, Adjudicator Prompt Tokens = **1814.6**.
  - Arm B4: Mean Candidate Tokens = **1994.1**, Adjudicator Prompt Tokens = **2054.3**.

### Mathematical Reconciliation
1. **Candidate Block Tokens:**
   - B0 = 206.8 tokens
   - B4 = 1994.1 tokens
   - Ratio: $\frac{1994.1}{206.8} = \mathbf{9.64\times}$ (**+864.3%** expansion).
2. **Adjudicator Prompt Tokens (Whole Prompt):**
   - B0 = 808.9 tokens
   - B4 = 2054.3 tokens
   - Ratio: $\frac{2054.3}{808.9} = \mathbf{2.54\times}$ (**+154.0%** expansion).
3. **Where did "410 to ~550 tokens (~35%)" come from?**
   In early specification `SCHEMA_AND_CONFIG.md`, a theoretical estimate hypothesized:
   *"B0 candidate package estimated at ~400 tokens; B4 estimated at ~550 tokens (+35%)"*.
   The report generator copied this early hypothetical text into line 34 of `generate_reports.py` without checking the actual token counter from `cost_summary.json`.

---

## 6. Audit Verdict on Report Credibility

| Reported Item | Narrative Text | Table / Raw Data | Audit Status | Corrective Action |
|---|---|---|---|---|
| **B0 Recall@5** | 83.3% | 100.0% | **NARRATIVE BUG** | Retract 83.3% narrative; record 100.0% true broad recall. |
| **B0 Recall@1** | 58.3% | 83.3% | **NARRATIVE BUG** | Correct to 83.3% (Mean rank 1.17). |
| **B4 Recall@3** | 91.7% | 100.0% | **NARRATIVE BUG** | Correct to 100.0% (all 12 queries retrieved target in top 3). |
| **HN Presence** | "-16.7% delta" | Flat 75.0% | **NARRATIVE BUG** | Clarify that presence in top 5 is 75% for all; reranking only affects rank order. |
| **Token Expansion** | "~35% (410 to 550)" | +864% candidate, +154% prompt | **NARRATIVE BUG** | Correct to true measured values: 207 to 1994 tokens (+864%). |

**Summary Conclusion:**
The underlying benchmark data is genuine, rigorous, and reproducible. The discrepancies are entirely due to **hardcoded narrative prose templates in `generate_reports.py`** that were never updated to reflect the true data.
