"""Tests for the AML Path-B v0 falsification policy."""

from research.experiments.aml_path_b_v0.benchmark import (
    ArmMetrics,
    BenchmarkBudget,
    FalsificationPolicy,
    evaluate_path_b_v0,
)


def arm(
    *,
    overall: float,
    target: float,
    recall: float,
    single: float = 80.0,
    safety: float = 80.0,
    tokens: float = 1000.0,
) -> ArmMetrics:
    return ArmMetrics(
        overall_score=overall,
        target_score=target,
        distributed_failure_recall_at_k=recall,
        single_hop_score=single,
        adversarial_or_abstention_score=safety,
        query_context_tokens=tokens,
    )


def test_supports_h1_h2_when_line_beats_summary_and_recovers_distributed_evidence():
    verdict = evaluate_path_b_v0(
        baseline_d=arm(overall=60, target=40, recall=20),
        line_e1=arm(overall=62, target=47, recall=27),
        line_e2=arm(overall=63, target=50, recall=30),
        summary_f=arm(overall=62, target=47, recall=24),
        budget=BenchmarkBudget(corpus_tokens=100_000, compile_tokens=20_000),
    )

    assert verdict.h1_supported is True
    assert verdict.h2_supported is True
    assert verdict.kill is False
    assert verdict.best_line_arm == "E2"


def test_kills_when_line_does_not_beat_budget_matched_summary():
    verdict = evaluate_path_b_v0(
        baseline_d=arm(overall=60, target=40, recall=20),
        line_e1=arm(overall=62, target=45, recall=26),
        line_e2=arm(overall=63, target=46, recall=27),
        summary_f=arm(overall=63, target=45, recall=25),
        budget=BenchmarkBudget(corpus_tokens=100_000, compile_tokens=20_000),
    )

    assert verdict.h1_supported is False
    assert verdict.kill is True
    assert any("H1 failed" in reason for reason in verdict.reasons)


def test_low_gain_high_cost_is_a_kill():
    verdict = evaluate_path_b_v0(
        baseline_d=arm(overall=60, target=40, recall=20, tokens=1000),
        line_e1=arm(overall=60.4, target=42, recall=22, tokens=1300),
        line_e2=arm(overall=60.5, target=43, recall=23, tokens=1300),
        summary_f=arm(overall=60, target=39, recall=20),
        budget=BenchmarkBudget(corpus_tokens=100_000, compile_tokens=60_000),
    )

    assert verdict.kill is True
    assert any("Low-gain/high-cost" in reason for reason in verdict.reasons)


def test_regression_over_one_point_is_a_kill_without_repair_gate():
    verdict = evaluate_path_b_v0(
        baseline_d=arm(overall=60, target=40, recall=20, single=85, safety=90),
        line_e1=arm(overall=63, target=47, recall=27, single=82, safety=90),
        line_e2=arm(overall=64, target=50, recall=30, single=83, safety=88),
        summary_f=arm(overall=62, target=47, recall=24, single=85, safety=90),
        budget=BenchmarkBudget(corpus_tokens=100_000, compile_tokens=20_000),
    )

    assert verdict.kill is True
    assert any("Regression kill" in reason for reason in verdict.reasons)


def test_repair_gate_can_allow_predeclared_regression_mitigation():
    verdict = evaluate_path_b_v0(
        baseline_d=arm(overall=60, target=40, recall=20, single=85, safety=90),
        line_e1=arm(overall=63, target=47, recall=27, single=82, safety=90),
        line_e2=arm(overall=64, target=50, recall=30, single=83, safety=88),
        summary_f=arm(overall=62, target=47, recall=24, single=85, safety=90),
        budget=BenchmarkBudget(corpus_tokens=100_000, compile_tokens=20_000),
        regression_gate_repaired=True,
    )

    assert verdict.kill is False


def test_e2_only_gain_is_not_credited_to_structure_if_it_cannot_beat_f():
    verdict = evaluate_path_b_v0(
        baseline_d=arm(overall=60, target=40, recall=20),
        line_e1=arm(overall=60, target=40, recall=20),
        line_e2=arm(overall=63, target=45, recall=28),
        summary_f=arm(overall=63, target=44, recall=26),
        budget=BenchmarkBudget(corpus_tokens=100_000, compile_tokens=20_000),
    )

    assert verdict.kill is True
    assert any("Structure-no-gain" in reason for reason in verdict.reasons)


def test_zero_corpus_budget_handles_nonzero_compile_as_infinite_ratio():
    budget = BenchmarkBudget(corpus_tokens=0, compile_tokens=1)
    assert budget.compile_ratio == float("inf")


def test_policy_is_configurable_without_changing_evaluation_code():
    strict = FalsificationPolicy(h1_vs_summary_min_pt=4.0)
    verdict = evaluate_path_b_v0(
        baseline_d=arm(overall=60, target=40, recall=20),
        line_e1=arm(overall=62, target=47, recall=27),
        line_e2=arm(overall=63, target=50, recall=30),
        summary_f=arm(overall=62, target=47, recall=24),
        budget=BenchmarkBudget(corpus_tokens=100_000, compile_tokens=20_000),
        policy=strict,
    )

    assert verdict.h1_supported is False
    assert verdict.kill is True
