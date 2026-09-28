from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from lce.cognition.convergence import (
    AuthorityConfig,
    AuthorityLedger,
    AuthoritySignal,
    evaluate_convergence,
)
from lce.reference_memory.contracts import RawEvidence
from lce.testing.reference_memory import InMemoryReferenceMemory


BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _signal(
    decision: str,
    candidate: str,
    raw_id: str,
    *,
    context: str | None = None,
    variant: str = "v1",
    polarity: str = "support",
    reciprocal: bool = True,
    known_at: datetime = BASE,
) -> AuthoritySignal:
    return AuthoritySignal(
        decision_key=decision,
        candidate_id=candidate,
        raw_evidence_ids=(raw_id,),
        derivation_variant_id=variant,
        known_at=known_at,
        polarity=polarity,  # type: ignore[arg-type]
        reciprocal=reciprocal,
        context_id=context,
    )


def _profile(decision, candidate_id: str):
    profile = decision.profile_for(candidate_id)
    assert profile is not None
    return profile


def test_equal_candidates_remain_unresolved() -> None:
    signals = (
        _signal("d", "a", "A1", context="c1"),
        _signal("d", "a", "A2", context="c2"),
        _signal("d", "b", "B1", context="c1"),
        _signal("d", "b", "B2", context="c2"),
    )
    decision = evaluate_convergence("d", signals)
    assert decision.status == "UNRESOLVED"
    assert decision.undominated_candidate_ids == ("a", "b")


def test_new_independent_support_can_create_unique_pareto_winner() -> None:
    initial = (
        _signal("d", "a", "A1", context="c1"),
        _signal("d", "a", "A2", context="c2"),
        _signal("d", "b", "B1", context="c1"),
        _signal("d", "b", "B2", context="c2"),
    )
    assert evaluate_convergence("d", initial).status == "UNRESOLVED"

    later = evaluate_convergence(
        "d",
        (*initial, _signal("d", "a", "A3", context="c3")),
    )
    assert later.status == "CONVERGED"
    assert later.winner_id == "a"


def test_repeated_derived_views_do_not_manufacture_independent_support() -> None:
    signals = tuple(
        _signal("d", "a", "RAW-1", variant=f"v{index}")
        for index in range(1, 8)
    )
    decision = evaluate_convergence(
        "d",
        signals,
        config=AuthorityConfig(
            min_independent_support=2,
            min_derivation_stability=1,
            min_variant_independent_support=1,
        ),
    )
    profile = _profile(decision, "a")
    assert profile.independent_support == 1
    assert profile.derivation_stability == 7
    assert decision.status == "UNRESOLVED"


def test_variant_stability_requires_independent_support_per_variant() -> None:
    config = AuthorityConfig(
        min_independent_support=2,
        min_derivation_stability=2,
        min_variant_independent_support=2,
    )
    weak = (
        _signal("d", "a", "A1", variant="v1"),
        _signal("d", "a", "A2", variant="v1"),
        _signal("d", "a", "A1", variant="v2"),
    )
    weak_decision = evaluate_convergence("d", weak, config=config)
    assert _profile(weak_decision, "a").derivation_stability == 1
    assert weak_decision.status == "UNRESOLVED"

    stable = (*weak, _signal("d", "a", "A2", variant="v2"))
    stable_decision = evaluate_convergence("d", stable, config=config)
    assert _profile(stable_decision, "a").derivation_stability == 2
    assert stable_decision.status == "CONVERGED"


def test_cross_dimension_tradeoff_stays_unresolved() -> None:
    config = AuthorityConfig(min_variant_independent_support=1)
    signals = (
        _signal("d", "a", "A1", context="c1"),
        _signal("d", "a", "A2", context="c1"),
        _signal("d", "a", "A3", context="c1"),
        _signal("d", "b", "B1", context="c1"),
        _signal("d", "b", "B2", context="c2"),
    )
    decision = evaluate_convergence("d", signals, config=config)
    assert decision.status == "UNRESOLVED"
    assert decision.undominated_candidate_ids == ("a", "b")


def test_contradiction_is_not_bought_off_by_more_positive_support() -> None:
    signals = (
        _signal("d", "a", "A1"),
        _signal("d", "a", "A2"),
        _signal("d", "a", "A3"),
        _signal("d", "a", "AX", polarity="contradict"),
        _signal("d", "b", "B1"),
        _signal("d", "b", "B2"),
    )
    decision = evaluate_convergence("d", signals)
    assert decision.status == "UNRESOLVED"
    assert decision.undominated_candidate_ids == ("a", "b")


def test_ledger_replays_historical_authority_after_later_invalidation(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    for evidence_id, day in (("E1", 0), ("E2", 10)):
        memory.add_evidence(
            RawEvidence(
                evidence_id=evidence_id,
                content=evidence_id,
                occurred_at=BASE + timedelta(days=day),
                known_at=BASE + timedelta(days=day),
                provenance={"source": "test", "canonical": True},
            )
        )

    ledger = AuthorityLedger(tmp_path / "authority")
    ledger.record_many(
        (
            _signal("d", "a", "E1", known_at=BASE),
            _signal(
                "d",
                "a",
                "E2",
                known_at=BASE + timedelta(days=10),
            ),
        )
    )
    before = BASE + timedelta(days=20)
    assert ledger.evaluate(
        "d",
        knowledge_cutoff=before,
        memory=memory,
    ).status == "CONVERGED"

    memory.invalidate("E2", reason="later correction")
    after = datetime.now(UTC)
    assert ledger.evaluate(
        "d",
        knowledge_cutoff=after,
        memory=memory,
    ).status == "UNRESOLVED"
    assert ledger.evaluate(
        "d",
        knowledge_cutoff=before,
        memory=memory,
    ).status == "CONVERGED"
    ledger.close()


def test_context_conflict_from_same_raw_group_cannot_multiply_context_support() -> None:
    config = replace(
        AuthorityConfig(),
        min_independent_support=1,
        min_context_support=1,
        min_variant_independent_support=1,
    )
    signals = (
        _signal("d", "a", "A1", context="ctx-a"),
        _signal("d", "a", "A1", context="ctx-b"),
    )
    decision = evaluate_convergence("d", signals, config=config)
    assert _profile(decision, "a").context_support == 0
    assert decision.status == "UNRESOLVED"
