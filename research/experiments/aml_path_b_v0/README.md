# AML Path-B v0 falsification harness

Status: research-only benchmark adapter. This is **not** full LCE validation and
does not authorize production integration.

## Scope

This package freezes the acceptance/kill criteria for testing two residual Path-B
claims after subtracting capabilities already covered by ordinary retrieval and
precomputed summarization:

- **H1 — temporal directed Line structure adds value beyond a budget-matched
  generic summary baseline (F).**
- **H2 — Line expansion recovers low-similarity, cross-session evidence that the
  strongest non-LCE baseline (D) misses.**

The benchmark arms are:

- **D**: strongest non-LCE baseline.
- **E1**: D + zero-LLM Line-member structural expansion.
- **E2**: D + Line-card retrieval.
- **F**: D + budget-matched generic precomputed summaries.

AML may feed existing chunks/fact units directly into this benchmark adapter.
That exception tests the retrieval mechanism only; it does **not** validate the
production Raw -> Point -> SemanticBlock -> LCE path.

## Frozen decision rules

Defaults follow the 2026-10-06 engineering audit and are intentionally explicit:

- H1 requires the best Line arm to beat F by at least **+2 pt** on target
  categories.
- H2 requires at least **+5 pt** evidence R@K improvement on the subset where D
  failed and evidence spans >=2 sessions.
- Low gain is grounds for killing Path B only when both overall gain is **<+1
  pt** and target-category gain is **<+5 pt**, while compilation exceeds
  **0.5x corpus tokens** or per-query context rises by **>20%**.
- Any **>1 pt** regression on single-hop or adversarial/abstention is a kill
  unless repaired by a predeclared gate.
- If E1 adds no measurable value while E2 adds value, the result is attributed
  to precomputed summarization unless E2 still clears the F comparison.

Thresholds are benchmark policy, not architectural constants.
