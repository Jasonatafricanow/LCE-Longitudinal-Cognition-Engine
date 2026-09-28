"""Research-only candidate convergence without a scalar confidence authority.

The experiment asks whether ambiguous structural interpretations can converge by
accumulating independent evidence and surviving derivation perturbations rather
than by asking one scorer/model to emit a weighted confidence value.

This module is intentionally not wired into the production trajectory runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Polarity = Literal["support", "contradict"]


@dataclass(frozen=True, slots=True)
class CandidateSignal:
    """One auditable structural signal for one candidate interpretation.

    support_group_id identifies the independent Raw-Evidence/provenance group.
    Repeated derived projections must reuse the same support_group_id so they do
    not manufacture additional evidence authority.

    context_id is supplied by the caller; this experiment deliberately does not
    invent fixed time buckets. derivation_variant_id identifies an algorithm /
    parameter perturbation under which the same candidate survived.
    """

    candidate_id: str
    support_group_id: str
    context_id: str
    derivation_variant_id: str
    polarity: Polarity = "support"
    reciprocal: bool = True

    def __post_init__(self) -> None:
        for name, value in (
            ("candidate_id", self.candidate_id),
            ("support_group_id", self.support_group_id),
            ("context_id", self.context_id),
            ("derivation_variant_id", self.derivation_variant_id),
        ):
            if not value.strip():
                raise ValueError(f"{name} must be nonempty")
        if self.polarity not in {"support", "contradict"}:
            raise ValueError("polarity must be support or contradict")


@dataclass(frozen=True, slots=True)
class SupportProfile:
    candidate_id: str
    independent_support: int
    reciprocal_support: int
    context_support: int
    derivation_stability: int
    contradiction_pressure: int
    support_group_ids: tuple[str, ...]
    contradiction_group_ids: tuple[str, ...]

    @property
    def positive_dimensions(self) -> tuple[int, int, int, int]:
        return (
            self.independent_support,
            self.reciprocal_support,
            self.context_support,
            self.derivation_stability,
        )


@dataclass(frozen=True, slots=True)
class ConvergenceConfig:
    """Evidentiary admission floor, not a weighted confidence formula."""

    min_independent_support: int = 2
    min_context_support: int = 2
    min_derivation_stability: int = 1

    def __post_init__(self) -> None:
        if self.min_independent_support < 1:
            raise ValueError("min_independent_support must be positive")
        if self.min_context_support < 1:
            raise ValueError("min_context_support must be positive")
        if self.min_derivation_stability < 1:
            raise ValueError("min_derivation_stability must be positive")


@dataclass(frozen=True, slots=True)
class ConvergenceDecision:
    status: Literal["CONVERGED", "UNRESOLVED"]
    winner_id: str | None
    eligible_candidate_ids: tuple[str, ...]
    undominated_candidate_ids: tuple[str, ...]
    profiles: tuple[SupportProfile, ...]


def _profile(candidate_id: str, signals: tuple[CandidateSignal, ...]) -> SupportProfile:
    support = tuple(signal for signal in signals if signal.polarity == "support")
    contradict = tuple(signal for signal in signals if signal.polarity == "contradict")

    support_groups = {signal.support_group_id for signal in support}
    contradiction_groups = {signal.support_group_id for signal in contradict}
    reciprocal_groups = {
        signal.support_group_id for signal in support if signal.reciprocal
    }
    contexts = {signal.context_id for signal in support}
    derivation_variants = {
        signal.derivation_variant_id for signal in support
    }

    return SupportProfile(
        candidate_id=candidate_id,
        independent_support=len(support_groups),
        reciprocal_support=len(reciprocal_groups),
        context_support=len(contexts),
        derivation_stability=len(derivation_variants),
        contradiction_pressure=len(contradiction_groups),
        support_group_ids=tuple(sorted(support_groups)),
        contradiction_group_ids=tuple(sorted(contradiction_groups)),
    )


def _eligible(profile: SupportProfile, config: ConvergenceConfig) -> bool:
    return (
        profile.independent_support >= config.min_independent_support
        and profile.context_support >= config.min_context_support
        and profile.derivation_stability >= config.min_derivation_stability
    )


def _dominates(left: SupportProfile, right: SupportProfile) -> bool:
    """Pareto dominance: no hidden scalarization or cross-dimension tradeoff."""

    no_worse_positive = all(
        left_value >= right_value
        for left_value, right_value in zip(
            left.positive_dimensions,
            right.positive_dimensions,
            strict=True,
        )
    )
    no_worse_contradiction = (
        left.contradiction_pressure <= right.contradiction_pressure
    )
    strictly_better = (
        any(
            left_value > right_value
            for left_value, right_value in zip(
                left.positive_dimensions,
                right.positive_dimensions,
                strict=True,
            )
        )
        or left.contradiction_pressure < right.contradiction_pressure
    )
    return no_worse_positive and no_worse_contradiction and strictly_better


def evaluate_convergence(
    signals: tuple[CandidateSignal, ...],
    *,
    config: ConvergenceConfig | None = None,
) -> ConvergenceDecision:
    """Return a unique structurally dominant candidate or remain unresolved."""

    policy = config or ConvergenceConfig()
    candidate_ids = tuple(sorted({signal.candidate_id for signal in signals}))
    profiles = tuple(
        _profile(
            candidate_id,
            tuple(
                signal for signal in signals if signal.candidate_id == candidate_id
            ),
        )
        for candidate_id in candidate_ids
    )
    eligible = tuple(
        profile for profile in profiles if _eligible(profile, policy)
    )
    undominated = tuple(
        profile
        for profile in eligible
        if not any(
            other.candidate_id != profile.candidate_id
            and _dominates(other, profile)
            for other in eligible
        )
    )
    winner = undominated[0].candidate_id if len(undominated) == 1 else None
    return ConvergenceDecision(
        status="CONVERGED" if winner is not None else "UNRESOLVED",
        winner_id=winner,
        eligible_candidate_ids=tuple(
            profile.candidate_id for profile in eligible
        ),
        undominated_candidate_ids=tuple(
            profile.candidate_id for profile in undominated
        ),
        profiles=profiles,
    )
