"""AML Path-B v0 falsification policy.

This module intentionally contains no retrieval implementation. It freezes the
comparison contract before AML adapters, Line builders, rerankers, or summary
generators are tuned against the benchmark.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ArmMetrics:
    """Score/cost-relevant metrics for one benchmark arm.

    All score-like fields are percentage points (0..100), not fractions.
    distributed_failure_recall_at_k is measured only on questions where
    baseline D failed and gold evidence spans at least two sessions.
    """

    overall_score: float
    target_score: float
    distributed_failure_recall_at_k: float
    single_hop_score: float
    adversarial_or_abstention_score: float
    query_context_tokens: float


@dataclass(frozen=True, slots=True)
class BenchmarkBudget:
    corpus_tokens: int
    compile_tokens: int

    @property
    def compile_ratio(self) -> float:
        if self.corpus_tokens <= 0:
            return 0.0 if self.compile_tokens <= 0 else float("inf")
        return self.compile_tokens / self.corpus_tokens


@dataclass(frozen=True, slots=True)
class FalsificationPolicy:
    h1_vs_summary_min_pt: float = 2.0
    h2_recall_min_pt: float = 5.0
    overall_gain_min_pt: float = 1.0
    target_gain_min_pt: float = 5.0
    compile_ratio_max: float = 0.5
    query_context_increase_max_pct: float = 20.0
    regression_max_pt: float = 1.0
    structural_gain_epsilon_pt: float = 0.0


@dataclass(frozen=True, slots=True)
class PathBV0Verdict:
    h1_supported: bool
    h2_supported: bool
    kill: bool
    best_line_arm: str
    reasons: tuple[str, ...]


def _delta(new: float, base: float) -> float:
    return new - base


def _query_increase_pct(new_tokens: float, base_tokens: float) -> float:
    if base_tokens <= 0:
        return 0.0 if new_tokens <= 0 else float("inf")
    return (new_tokens - base_tokens) / base_tokens * 100.0


def evaluate_path_b_v0(
    *,
    baseline_d: ArmMetrics,
    line_e1: ArmMetrics,
    line_e2: ArmMetrics,
    summary_f: ArmMetrics,
    budget: BenchmarkBudget,
    policy: FalsificationPolicy = FalsificationPolicy(),
    regression_gate_repaired: bool = False,
) -> PathBV0Verdict:
    """Apply the frozen H1/H2 and kill rules."""

    if line_e2.target_score > line_e1.target_score:
        best_name = "E2"
        best = line_e2
    else:
        best_name = "E1"
        best = line_e1

    h1_delta = _delta(best.target_score, summary_f.target_score)
    h2_delta = _delta(
        best.distributed_failure_recall_at_k,
        baseline_d.distributed_failure_recall_at_k,
    )
    h1_supported = h1_delta >= policy.h1_vs_summary_min_pt
    h2_supported = h2_delta >= policy.h2_recall_min_pt

    reasons: list[str] = []

    if not h1_supported:
        reasons.append(
            f"H1 failed: {best_name} target delta vs F is {h1_delta:.2f} pt "
            f"(< {policy.h1_vs_summary_min_pt:.2f})."
        )

    overall_gain = _delta(best.overall_score, baseline_d.overall_score)
    target_gain = _delta(best.target_score, baseline_d.target_score)
    query_increase = _query_increase_pct(
        best.query_context_tokens,
        baseline_d.query_context_tokens,
    )
    excessive_cost = (
        budget.compile_ratio > policy.compile_ratio_max
        or query_increase > policy.query_context_increase_max_pct
    )
    if (
        overall_gain < policy.overall_gain_min_pt
        and target_gain < policy.target_gain_min_pt
        and excessive_cost
    ):
        reasons.append(
            "Low-gain/high-cost kill: "
            f"overall={overall_gain:.2f} pt, target={target_gain:.2f} pt, "
            f"compile_ratio={budget.compile_ratio:.3f}, "
            f"query_increase={query_increase:.2f}%."
        )

    single_hop_regression = _delta(
        baseline_d.single_hop_score,
        best.single_hop_score,
    )
    safety_regression = _delta(
        baseline_d.adversarial_or_abstention_score,
        best.adversarial_or_abstention_score,
    )
    if (
        not regression_gate_repaired
        and (
            single_hop_regression > policy.regression_max_pt
            or safety_regression > policy.regression_max_pt
        )
    ):
        reasons.append(
            "Regression kill: "
            f"single_hop={single_hop_regression:.2f} pt, "
            f"adversarial/abstention={safety_regression:.2f} pt."
        )

    e1_target_gain = _delta(line_e1.target_score, baseline_d.target_score)
    e2_target_gain = _delta(line_e2.target_score, baseline_d.target_score)
    if (
        e1_target_gain <= policy.structural_gain_epsilon_pt
        and e2_target_gain > policy.structural_gain_epsilon_pt
        and not h1_supported
    ):
        reasons.append(
            "Structure-no-gain kill: E1 adds no target-category value while E2 "
            "does; E2 also fails the budget-matched F comparison."
        )

    return PathBV0Verdict(
        h1_supported=h1_supported,
        h2_supported=h2_supported,
        kill=bool(reasons),
        best_line_arm=best_name,
        reasons=tuple(reasons),
    )
