"""Decentralized evidence convergence for derived cognition.

Raw Evidence remains the only independent factual authority. This module does
not assign a scalar confidence score and does not let derived projections vote
themselves into authority. It only records auditable structural support and
compares competing derived candidates by explicit evidence dimensions.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from lce.reference_memory.contracts import ReferenceMemorySubstratePort

Polarity = Literal["support", "contradict"]
DecisionStatus = Literal["CONVERGED", "UNRESOLVED"]


def _require_utc(value: datetime, name: str) -> None:
    if value.tzinfo != UTC:
        raise ValueError(f"{name} must be an aware UTC datetime")


def _require_nonempty(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty")
    return value.strip()


def _evidence_valid_at(
    memory: ReferenceMemorySubstratePort,
    evidence_id: str,
    cutoff: datetime,
) -> bool:
    reader = getattr(memory, "evidence_valid_at", None)
    if callable(reader):
        return bool(reader(evidence_id, cutoff))
    item = memory.get_evidence(evidence_id)
    return item.effective_known_at <= cutoff and item.current_valid


@dataclass(frozen=True, slots=True)
class AuthoritySignal:
    """One source-grounded signal for one derived candidate.

    `raw_evidence_ids` is the independent authority closure. Replaying or
    re-projecting the same closure may add derivation-stability observations,
    but it cannot increase independent support.

    `context_id` is optional and must be supplied by an upstream source-aware
    layer. This module never invents fixed context buckets.
    """

    decision_key: str
    candidate_id: str
    raw_evidence_ids: tuple[str, ...]
    derivation_variant_id: str
    known_at: datetime
    polarity: Polarity = "support"
    reciprocal: bool = False
    context_id: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty(self.decision_key, "decision_key")
        _require_nonempty(self.candidate_id, "candidate_id")
        _require_nonempty(
            self.derivation_variant_id,
            "derivation_variant_id",
        )
        if (
            not isinstance(self.raw_evidence_ids, tuple)
            or not self.raw_evidence_ids
        ):
            raise ValueError("raw_evidence_ids must be a nonempty tuple")
        if len(set(self.raw_evidence_ids)) != len(self.raw_evidence_ids):
            raise ValueError("raw_evidence_ids must be unique")
        for evidence_id in self.raw_evidence_ids:
            _require_nonempty(evidence_id, "raw_evidence_id")
        _require_utc(self.known_at, "known_at")
        if self.polarity not in {"support", "contradict"}:
            raise ValueError("polarity must be support or contradict")
        if type(self.reciprocal) is not bool:
            raise TypeError("reciprocal must be bool")
        if self.context_id is not None:
            _require_nonempty(self.context_id, "context_id")

    @property
    def support_group_id(self) -> str:
        payload = json.dumps(
            tuple(sorted(self.raw_evidence_ids)),
            separators=(",", ":"),
        )
        return "rawgrp_" + hashlib.sha256(
            payload.encode()
        ).hexdigest()[:24]

    @property
    def signal_id(self) -> str:
        payload = json.dumps(
            {
                "decision": self.decision_key,
                "candidate": self.candidate_id,
                "support_group": self.support_group_id,
                "variant": self.derivation_variant_id,
                "polarity": self.polarity,
                "reciprocal": self.reciprocal,
                "context": self.context_id,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return "authsig_" + hashlib.sha256(
            payload.encode()
        ).hexdigest()[:24]


@dataclass(frozen=True, slots=True)
class AuthorityConfig:
    """Admission floors for structural convergence, never weighted scoring."""

    min_independent_support: int = 2
    min_reciprocal_support: int = 0
    min_context_support: int = 0
    min_derivation_stability: int = 1
    min_variant_independent_support: int = 2

    def __post_init__(self) -> None:
        for name, value in (
            ("min_independent_support", self.min_independent_support),
            ("min_reciprocal_support", self.min_reciprocal_support),
            ("min_context_support", self.min_context_support),
            ("min_derivation_stability", self.min_derivation_stability),
            (
                "min_variant_independent_support",
                self.min_variant_independent_support,
            ),
        ):
            if not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a nonnegative integer")
        if self.min_independent_support < 1:
            raise ValueError("min_independent_support must be positive")
        if self.min_derivation_stability < 1:
            raise ValueError("min_derivation_stability must be positive")
        if self.min_variant_independent_support < 1:
            raise ValueError(
                "min_variant_independent_support must be positive"
            )


@dataclass(frozen=True, slots=True)
class AuthorityProfile:
    candidate_id: str
    independent_support: int
    reciprocal_support: int
    context_support: int
    derivation_stability: int
    contradiction_pressure: int
    support_group_ids: tuple[str, ...]
    contradiction_group_ids: tuple[str, ...]
    context_ids: tuple[str, ...]
    stable_variant_ids: tuple[str, ...]

    @property
    def positive_dimensions(self) -> tuple[int, int, int, int]:
        return (
            self.independent_support,
            self.reciprocal_support,
            self.context_support,
            self.derivation_stability,
        )


@dataclass(frozen=True, slots=True)
class AuthorityDecision:
    decision_key: str
    status: DecisionStatus
    winner_id: str | None
    eligible_candidate_ids: tuple[str, ...]
    undominated_candidate_ids: tuple[str, ...]
    profiles: tuple[AuthorityProfile, ...]

    def profile_for(self, candidate_id: str) -> AuthorityProfile | None:
        return next(
            (
                profile
                for profile in self.profiles
                if profile.candidate_id == candidate_id
            ),
            None,
        )


def _profile(
    candidate_id: str,
    signals: tuple[AuthoritySignal, ...],
    *,
    config: AuthorityConfig,
) -> AuthorityProfile:
    support = tuple(
        signal for signal in signals if signal.polarity == "support"
    )
    contradict = tuple(
        signal for signal in signals if signal.polarity == "contradict"
    )
    support_groups = {signal.support_group_id for signal in support}
    contradiction_groups = {
        signal.support_group_id for signal in contradict
    }
    reciprocal_groups = {
        signal.support_group_id
        for signal in support
        if signal.reciprocal
    }

    contexts_by_group: dict[str, set[str]] = {}
    for signal in support:
        if signal.context_id is None:
            continue
        contexts_by_group.setdefault(
            signal.support_group_id,
            set(),
        ).add(signal.context_id)
    stable_contexts = {
        next(iter(contexts))
        for contexts in contexts_by_group.values()
        if len(contexts) == 1
    }

    variant_groups: dict[str, set[str]] = {}
    for signal in support:
        variant_groups.setdefault(
            signal.derivation_variant_id,
            set(),
        ).add(signal.support_group_id)
    stable_variants = {
        variant_id
        for variant_id, groups in variant_groups.items()
        if len(groups) >= config.min_variant_independent_support
    }

    return AuthorityProfile(
        candidate_id=candidate_id,
        independent_support=len(support_groups),
        reciprocal_support=len(reciprocal_groups),
        context_support=len(stable_contexts),
        derivation_stability=len(stable_variants),
        contradiction_pressure=len(contradiction_groups),
        support_group_ids=tuple(sorted(support_groups)),
        contradiction_group_ids=tuple(sorted(contradiction_groups)),
        context_ids=tuple(sorted(stable_contexts)),
        stable_variant_ids=tuple(sorted(stable_variants)),
    )


def _eligible(
    profile: AuthorityProfile,
    config: AuthorityConfig,
) -> bool:
    return (
        profile.independent_support >= config.min_independent_support
        and profile.reciprocal_support >= config.min_reciprocal_support
        and profile.context_support >= config.min_context_support
        and profile.derivation_stability
        >= config.min_derivation_stability
    )


def _dominates(
    left: AuthorityProfile,
    right: AuthorityProfile,
) -> bool:
    """Pareto dominance without a hidden exchange rate between dimensions."""

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
    return (
        no_worse_positive
        and no_worse_contradiction
        and strictly_better
    )


def evaluate_convergence(
    decision_key: str,
    signals: tuple[AuthoritySignal, ...],
    *,
    config: AuthorityConfig | None = None,
) -> AuthorityDecision:
    """Converge only when exactly one eligible candidate is undominated."""

    _require_nonempty(decision_key, "decision_key")
    policy = config or AuthorityConfig()
    scoped = tuple(
        signal
        for signal in signals
        if signal.decision_key == decision_key
    )
    candidate_ids = tuple(
        sorted({signal.candidate_id for signal in scoped})
    )
    profiles = tuple(
        _profile(
            candidate_id,
            tuple(
                signal
                for signal in scoped
                if signal.candidate_id == candidate_id
            ),
            config=policy,
        )
        for candidate_id in candidate_ids
    )
    eligible = tuple(
        profile
        for profile in profiles
        if _eligible(profile, policy)
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
    winner = (
        undominated[0].candidate_id
        if len(undominated) == 1
        else None
    )
    return AuthorityDecision(
        decision_key=decision_key,
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


class AuthorityLedger:
    """Durable, bitemporal-aware ledger of source-grounded signals."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(
            str(self.root / "authority_convergence.sqlite")
        )
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS authority_signals (
                signal_id TEXT PRIMARY KEY,
                decision_key TEXT NOT NULL,
                candidate_id TEXT NOT NULL,
                raw_evidence_ids_json TEXT NOT NULL,
                derivation_variant_id TEXT NOT NULL,
                known_at TEXT NOT NULL,
                polarity TEXT NOT NULL,
                reciprocal INTEGER NOT NULL,
                context_id TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_authority_decision_time
                ON authority_signals(decision_key, known_at);
            CREATE INDEX IF NOT EXISTS idx_authority_candidate
                ON authority_signals(decision_key, candidate_id);
            """
        )
        self.conn.commit()

    def record(self, signal: AuthoritySignal, *, commit: bool = True) -> bool:
        result = self.conn.execute(
            """
            INSERT OR IGNORE INTO authority_signals (
                signal_id,
                decision_key,
                candidate_id,
                raw_evidence_ids_json,
                derivation_variant_id,
                known_at,
                polarity,
                reciprocal,
                context_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                signal.signal_id,
                signal.decision_key,
                signal.candidate_id,
                json.dumps(
                    tuple(sorted(signal.raw_evidence_ids)),
                    separators=(",", ":"),
                ),
                signal.derivation_variant_id,
                signal.known_at.isoformat(),
                signal.polarity,
                1 if signal.reciprocal else 0,
                signal.context_id,
            ),
        )
        if commit:
            self.conn.commit()
        return result.rowcount > 0

    def record_many(
        self,
        signals: tuple[AuthoritySignal, ...],
    ) -> int:
        added = 0
        with self.conn:
            for signal in signals:
                added += int(self.record(signal, commit=False))
        return added

    def signals(
        self,
        decision_key: str,
        *,
        knowledge_cutoff: datetime,
        memory: ReferenceMemorySubstratePort,
    ) -> tuple[AuthoritySignal, ...]:
        _require_nonempty(decision_key, "decision_key")
        _require_utc(knowledge_cutoff, "knowledge_cutoff")
        rows = self.conn.execute(
            """
            SELECT
                decision_key,
                candidate_id,
                raw_evidence_ids_json,
                derivation_variant_id,
                known_at,
                polarity,
                reciprocal,
                context_id
            FROM authority_signals
            WHERE decision_key = ? AND known_at <= ?
            ORDER BY candidate_id, known_at, signal_id
            """,
            (decision_key, knowledge_cutoff.isoformat()),
        ).fetchall()
        output: list[AuthoritySignal] = []
        for row in rows:
            raw_ids = tuple(json.loads(str(row[2])))
            try:
                if not all(
                    _evidence_valid_at(
                        memory,
                        evidence_id,
                        knowledge_cutoff,
                    )
                    for evidence_id in raw_ids
                ):
                    continue
            except KeyError:
                continue
            output.append(
                AuthoritySignal(
                    decision_key=str(row[0]),
                    candidate_id=str(row[1]),
                    raw_evidence_ids=raw_ids,
                    derivation_variant_id=str(row[3]),
                    known_at=datetime.fromisoformat(str(row[4])),
                    polarity=str(row[5]),  # type: ignore[arg-type]
                    reciprocal=bool(row[6]),
                    context_id=(
                        str(row[7]) if row[7] is not None else None
                    ),
                )
            )
        return tuple(output)

    def evaluate(
        self,
        decision_key: str,
        *,
        knowledge_cutoff: datetime,
        memory: ReferenceMemorySubstratePort,
        config: AuthorityConfig | None = None,
    ) -> AuthorityDecision:
        return evaluate_convergence(
            decision_key,
            self.signals(
                decision_key,
                knowledge_cutoff=knowledge_cutoff,
                memory=memory,
            ),
            config=config,
        )

    def decision_keys(self) -> tuple[str, ...]:
        rows = self.conn.execute(
            "SELECT DISTINCT decision_key FROM authority_signals "
            "ORDER BY decision_key"
        ).fetchall()
        return tuple(str(row[0]) for row in rows)

    def close(self) -> None:
        self.conn.close()
