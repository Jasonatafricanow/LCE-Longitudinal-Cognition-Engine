# Critical Falsification Evidence Audit (F1 – F5)

**Issue:** #24  
**Date:** 2026-09-25

---

## Summary of Falsification Tests

| Test | Objective | Status | Evidence |
|---|---|---|---|
| **F1** | Time is necessary but insufficient | **PASSED** | 10/10 unrelated temporal neighbors rejected (100.0% precision). |
| **F2** | Future evidence does not rewrite earlier truth | **PASSED** | 0 content mutations across all 62 SemanticBlocks (100% hash invariant). |
| **F3** | UNKNOWN only closes with new evidence | **PASSED** | 7 elapsed-time cases audited; 0 closed without evidence; unknown kept open. |
| **F4** | State change != correction | **PASSED** | 18 hard contrastive pairs tested; 0 confusions between the two (0.0% error). |
| **F5** | Sparse candidate formation | **PASSED** | 93.5% candidate reduction vs all pairs with 100.0% true relation recall. |

---

## Detailed Falsification Traces

### F1: Time is Necessary But Insufficient
- **Probe Pair `GP_FLIGHT_07`**:
  - $t_1$: "我今天必须赶杭州到北京的飞机。"
  - $t_2$: "下周去上海的高铁票我已经买好了。"
  - Temporal distance: 4 hours apart.
  - **Verdict:** Correctly classified as `UNRELATED`. Temporal proximity did not force a relation.

### F2: No Retrospective Mutation
- Pre-adjudication SHA-256 hashes were recorded for all 62 SemanticBlocks.
- Post-adjudication SHA-256 hashes verified identical:
  - `SHA-256(B_FLIGHT_01)` before = after
  - `SHA-256(B_REPORT_01)` before = after
  - `SHA-256(B_MEETING_01)` before = after
- **Verdict:** PASSED. SemanticBlocks remain immutable.

### F3: UNKNOWN Only Closes With Evidence
- **Probe Pair `GP_FLIGHT_08`**:
  - $t_1$ (2026-10-01): "我今天必须赶杭州到北京的飞机。" (open unknown: whether flight was caught)
  - $t_2$ (2026-10-05): "今天北京的天气据说是晴天。" (4 days later, no mention of flight outcome)
  - **Adjudication Result:** `prior_unknown_resolved = False`, relation = `UNRELATED` / `UNKNOWN_RELATION`.
  - **Verdict:** PASSED. The passage of 4 days did not allow the system to assume the flight was caught or missed.

### F4: State Change != Correction
- See dedicated report `STATE_CHANGE_VS_CORRECTION_ANALYSIS.md`. Confusion is strictly 0.0%.

### F5: Sparse Candidate Formation
- Candidate pairs reduced from 1,891 to 123 (93.5% reduction).
- True relation recall maintained at 100.0%.
- **Verdict:** PASSED.
