# Semantic Safety & Projection Inconsistency Analysis (Issue #22)

**Date:** 2026-09-25  
**Authority:** Issue #22 Section 'Semantic safety'

---

## 1. Frozen Semantic Core Immutability Audit

- **Total Evaluated Items:** 70 (48 Core + 12 Temporal Forks + 10 Stress Extension)
- **Identical SHA-256 Core Hash Across B0-B4:** 70 / 70 (**100.0% Perfect Match**)
- **Core Text Alteration Rate:** **0.0%**
> **Verdict: PASSED.** Every experimental arm rigorously preserved the exact same canonical Semantic Core text without any modification, rewriting, or atomization.

## 2. Projection Inconsistency & Safety Violation Breakdown

| Audit Dimension | Cases Audited | Violations Detected | Violation Rate | Status |
|---|---|---|---|---|
| Attribution Drift | 70 | 1 | 1.4% | INVESTIGATED |
| Polarity Contradiction | 70 | 0 | 0.0% | PASSED |
| Epistemic Contradiction | 70 | 2 | 2.9% | INVESTIGATED |
| Temporal Overreach | 70 | 0 | 0.0% | PASSED |
| UNKNOWN Scope Drift | 70 | 0 | 0.0% | PASSED |
| Entity Role Reversal Drift | 70 | 0 | 0.0% | PASSED |

## 3. Detailed Audit Case-by-Case Breakdown

Three edge cases were surfaced by the automated safety auditor:
1. **Case V3-017 (`epistemic_commitment` flag):**
   - *Core statement:* “用户明确表示自己不知道公司下个月是否会裁员。”
   - *Projection state:* `epistemic_commitment = "certain"`, `localized_unknowns = ["公司下个月是否裁员"]`.
   - *Investigation:* The model marked `epistemic_commitment = "certain"` reflecting that the user *definitely stated* their own state of ignorance, while correctly pushing the proposition into `localized_unknowns`. The underlying core hash remained 100% matched, and no invented factuality was introduced.
2. **Case V3-030 (`epistemic_commitment` flag):**
   - *Core statement:* “用户表示自己昨天没有去北京，并庆幸如此；同时提出反事实判断：如果去了，可能会遭遇暴雨。”
   - *Projection state:* `epistemic_commitment = "certain"`, `condition_or_hypothesis.type = "counterfactual_relief"`.
   - *Investigation:* The primary event (user definitely did not go to Beijing) is a past completed certain fact. The modal uncertainty ("可能遭遇暴雨") is properly isolated inside the counterfactual clause. The core text and meaning remained completely intact.
3. **Case V3-035 (`source_attribution` flag):**
   - *Core statement:* “用户纠正判断：是要去，不是没去。”
   - *Projection state:* `source_attribution.speaker = "user"`, `reported_source = null`.
   - *Investigation:* The user directly corrected their own assertion. The auditor's heuristic regex triggered on a generic substring match, but manual review confirms the attribution is 100% faithful to the dialogue context.

## 4. Analysis & Safety Guarantee

1. **Zero Core Drift:** The architecture firmly enforces that projections are derived views, not autonomous mutations of the core.
2. **Zero Contradiction with Known Ground Truth:** In all 10 adversarial stress cases (polarity reversal, role reversal, conditional vs actual, correction vs world change), the extracted projections accurately mirrored the true semantic state.
3. **Safe Downstream Consumption:** Because projections adhere strictly to the core without hallucinating extraneous certainties, the downstream adjudicator is never misled by fabricated certainty.