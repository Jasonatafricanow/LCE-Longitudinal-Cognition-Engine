from __future__ import annotations

from research.experiments.trajectory_convergence import (
    CandidateSignal,
    ConvergenceConfig,
    evaluate_convergence,
)


def _s(
    candidate: str,
    group: str,
    context: str,
    *,
    variant: str = "base",
    polarity: str = "support",
    reciprocal: bool = True,
) -> CandidateSignal:
    return CandidateSignal(
        candidate_id=candidate,
        support_group_id=group,
        context_id=context,
        derivation_variant_id=variant,
        polarity=polarity,
        reciprocal=reciprocal,
    )


def _profile(decision, candidate_id: str):
    return next(
        profile
        for profile in decision.profiles
        if profile.candidate_id == candidate_id
    )


def test_ambiguity_can_converge_after_new_independent_support() -> None:
    initial = (
        _s("line-a", "A1", "ctx-1"),
        _s("line-a", "A2", "ctx-2"),
        _s("line-b", "B1", "ctx-1"),
        _s("line-b", "B2", "ctx-2"),
    )
    first = evaluate_convergence(initial)
    assert first.status == "UNRESOLVED"
    assert first.undominated_candidate_ids == ("line-a", "line-b")

    later = evaluate_convergence(
        (*initial, _s("line-a", "A3", "ctx-3"))
    )
    assert later.status == "CONVERGED"
    assert later.winner_id == "line-a"


def test_repeated_derived_projection_does_not_manufacture_support() -> None:
    signals = tuple(
        _s("line-a", "RAW-1", "ctx-1")
        for _ in range(20)
    )
    decision = evaluate_convergence(
        signals,
        config=ConvergenceConfig(
            min_independent_support=2,
            min_context_support=1,
        ),
    )
    profile = _profile(decision, "line-a")
    assert profile.independent_support == 1
    assert profile.reciprocal_support == 1
    assert decision.status == "UNRESOLVED"


def test_cross_dimension_tradeoff_remains_unresolved_without_scalar_weights() -> None:
    signals = (
        _s("line-a", "A1", "ctx-1"),
        _s("line-a", "A2", "ctx-2"),
        _s("line-a", "A3", "ctx-3"),
        _s("line-a", "A4", "ctx-4"),
        _s("line-a", "AX", "ctx-x", polarity="contradict"),
        _s("line-b", "B1", "ctx-1"),
        _s("line-b", "B2", "ctx-2"),
        _s("line-b", "B3", "ctx-3"),
    )
    decision = evaluate_convergence(signals)
    assert decision.status == "UNRESOLVED"
    assert decision.undominated_candidate_ids == ("line-a", "line-b")


def test_candidate_below_evidentiary_floor_does_not_self_authorize() -> None:
    decision = evaluate_convergence(
        (_s("line-a", "A1", "ctx-1"),)
    )
    assert decision.status == "UNRESOLVED"
    assert decision.eligible_candidate_ids == ()


def test_perturbation_stability_can_break_an_otherwise_equal_tie() -> None:
    base = (
        _s("line-a", "A1", "ctx-1", variant="v1"),
        _s("line-a", "A2", "ctx-2", variant="v1"),
        _s("line-b", "B1", "ctx-1", variant="v1"),
        _s("line-b", "B2", "ctx-2", variant="v1"),
    )
    extra_variants = (
        _s("line-a", "A1", "ctx-1", variant="v2"),
        _s("line-a", "A2", "ctx-2", variant="v2"),
        _s("line-a", "A1", "ctx-1", variant="v3"),
        _s("line-a", "A2", "ctx-2", variant="v3"),
    )
    decision = evaluate_convergence((*base, *extra_variants))
    assert decision.status == "CONVERGED"
    assert decision.winner_id == "line-a"
    assert _profile(decision, "line-a").independent_support == 2
    assert _profile(decision, "line-a").derivation_stability == 3


def test_better_similarity_like_reciprocity_cannot_buy_off_more_contradiction() -> None:
    signals = (
        _s("line-a", "A1", "ctx-1"),
        _s("line-a", "A2", "ctx-2"),
        _s("line-a", "AX", "ctx-x", polarity="contradict"),
        _s("line-b", "B1", "ctx-1", reciprocal=False),
        _s("line-b", "B2", "ctx-2", reciprocal=False),
    )
    decision = evaluate_convergence(signals)
    assert decision.status == "UNRESOLVED"
    assert decision.undominated_candidate_ids == ("line-a", "line-b")
