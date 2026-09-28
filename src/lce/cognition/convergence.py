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
    def relation_id(self) -> str:
        """Reusable authority relation identity independent of one decision."""
        payload = json.dumps(
            {
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
        return "authrel_" + hashlib.sha256(
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
                "known_at": self.known_at.isoformat(),
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
            if type(value) is not int or value < 0:
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
    support_component_ids: tuple[str, ...]
    contradiction_component_ids: tuple[str, ...]
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


def _evidence_components(
    signals: tuple[AuthoritySignal, ...],
) -> dict[str, tuple[AuthoritySignal, ...]]:
    """Collapse transitively overlapping Raw closures into one authority unit.

    Exact-closure de-duplication is insufficient: {E1, E2} and {E2, E3} are
    not independent observations. A union-find over shared Raw IDs prevents
    partially overlapping derived views from manufacturing extra authority.
    """
    if not signals:
        return {}

    parent = list(range(len(signals)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    first_by_evidence: dict[str, int] = {}
    for index, signal in enumerate(signals):
        for evidence_id in signal.raw_evidence_ids:
            prior = first_by_evidence.get(evidence_id)
            if prior is None:
                first_by_evidence[evidence_id] = index
            else:
                union(index, prior)

    by_root: dict[int, list[AuthoritySignal]] = {}
    for index, signal in enumerate(signals):
        by_root.setdefault(find(index), []).append(signal)

    output: dict[str, tuple[AuthoritySignal, ...]] = {}
    for component_signals in by_root.values():
        raw_ids = tuple(
            sorted(
                {
                    evidence_id
                    for signal in component_signals
                    for evidence_id in signal.raw_evidence_ids
                }
            )
        )
        payload = json.dumps(raw_ids, separators=(",", ":"))
        component_id = "rawcomp_" + hashlib.sha256(
            payload.encode()
        ).hexdigest()[:24]
        output[component_id] = tuple(component_signals)
    return output


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
    support_components = _evidence_components(support)
    contradiction_components = _evidence_components(contradict)

    reciprocal_components = {
        component_id
        for component_id, component_signals in support_components.items()
        if any(signal.reciprocal for signal in component_signals)
    }

    stable_contexts: set[str] = set()
    for component_signals in support_components.values():
        contexts = {
            signal.context_id
            for signal in component_signals
            if signal.context_id is not None
        }
        if len(contexts) == 1:
            stable_contexts.add(next(iter(contexts)))

    variant_components: dict[str, set[str]] = {}
    for component_id, component_signals in support_components.items():
        for signal in component_signals:
            variant_components.setdefault(
                signal.derivation_variant_id,
                set(),
            ).add(component_id)
    stable_variants = {
        variant_id
        for variant_id, components in variant_components.items()
        if len(components) >= config.min_variant_independent_support
    }

    return AuthorityProfile(
        candidate_id=candidate_id,
        independent_support=len(support_components),
        reciprocal_support=len(reciprocal_components),
        context_support=len(stable_contexts),
        derivation_stability=len(stable_variants),
        contradiction_pressure=len(contradiction_components),
        support_component_ids=tuple(sorted(support_components)),
        contradiction_component_ids=tuple(sorted(contradiction_components)),
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
    """Normalized durable ledger of reusable source-grounded authority.

    Raw closures are stored once as authority materials. Candidate/support
    relations are stored once independently of any one decision. Decisions then
    reference those reusable relations with their own bitemporal known-at.
    """

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

            CREATE TABLE IF NOT EXISTS authority_materials (
                material_id TEXT PRIMARY KEY,
                raw_evidence_ids_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS authority_relations (
                relation_id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                material_id TEXT NOT NULL,
                derivation_variant_id TEXT NOT NULL,
                polarity TEXT NOT NULL,
                reciprocal INTEGER NOT NULL,
                context_id TEXT,
                FOREIGN KEY(material_id)
                    REFERENCES authority_materials(material_id)
            );

            CREATE TABLE IF NOT EXISTS authority_decision_refs (
                decision_key TEXT NOT NULL,
                relation_id TEXT NOT NULL,
                known_at TEXT NOT NULL,
                PRIMARY KEY(decision_key, relation_id),
                FOREIGN KEY(relation_id)
                    REFERENCES authority_relations(relation_id)
            );

            CREATE INDEX IF NOT EXISTS idx_authority_ref_time
                ON authority_decision_refs(decision_key, known_at);
            CREATE INDEX IF NOT EXISTS idx_authority_relation_candidate
                ON authority_relations(candidate_id);

            CREATE TABLE IF NOT EXISTS authority_ledger_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        self._migrate_legacy_signals()
        self.conn.commit()

    def _record_normalized(
        self,
        signal: AuthoritySignal,
        *,
        commit: bool,
    ) -> bool:
        material_id = signal.support_group_id
        raw_json = json.dumps(
            tuple(sorted(signal.raw_evidence_ids)),
            separators=(",", ":"),
        )
        self.conn.execute(
            "INSERT OR IGNORE INTO authority_materials "
            "(material_id, raw_evidence_ids_json) VALUES (?, ?)",
            (material_id, raw_json),
        )
        self.conn.execute(
            """
            INSERT OR IGNORE INTO authority_relations (
                relation_id,
                candidate_id,
                material_id,
                derivation_variant_id,
                polarity,
                reciprocal,
                context_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                signal.relation_id,
                signal.candidate_id,
                material_id,
                signal.derivation_variant_id,
                signal.polarity,
                1 if signal.reciprocal else 0,
                signal.context_id,
            ),
        )
        existing = self.conn.execute(
            "SELECT known_at FROM authority_decision_refs "
            "WHERE decision_key = ? AND relation_id = ?",
            (signal.decision_key, signal.relation_id),
        ).fetchone()
        added = existing is None
        if existing is None:
            self.conn.execute(
                "INSERT INTO authority_decision_refs "
                "(decision_key, relation_id, known_at) VALUES (?, ?, ?)",
                (
                    signal.decision_key,
                    signal.relation_id,
                    signal.known_at.isoformat(),
                ),
            )
        else:
            existing_known_at = datetime.fromisoformat(str(existing[0]))
            if signal.known_at < existing_known_at:
                self.conn.execute(
                    "UPDATE authority_decision_refs SET known_at = ? "
                    "WHERE decision_key = ? AND relation_id = ?",
                    (
                        signal.known_at.isoformat(),
                        signal.decision_key,
                        signal.relation_id,
                    ),
                )
        if commit:
            self.conn.commit()
        return added

    def _migrate_legacy_signals(self) -> None:
        marker = self.conn.execute(
            "SELECT value FROM authority_ledger_metadata "
            "WHERE key = 'normalized_v1'"
        ).fetchone()
        if marker is not None:
            return
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
            ORDER BY known_at, signal_id
            """
        ).fetchall()
        with self.conn:
            for row in rows:
                self._record_normalized(
                    AuthoritySignal(
                        decision_key=str(row[0]),
                        candidate_id=str(row[1]),
                        raw_evidence_ids=tuple(json.loads(str(row[2]))),
                        derivation_variant_id=str(row[3]),
                        known_at=datetime.fromisoformat(str(row[4])),
                        polarity=str(row[5]),  # type: ignore[arg-type]
                        reciprocal=bool(row[6]),
                        context_id=(
                            str(row[7]) if row[7] is not None else None
                        ),
                    ),
                    commit=False,
                )
            self.conn.execute(
                "INSERT OR REPLACE INTO authority_ledger_metadata "
                "(key, value) VALUES ('normalized_v1', '1')"
            )

    def record(self, signal: AuthoritySignal, *, commit: bool = True) -> bool:
        return self._record_normalized(signal, commit=commit)

    def record_many(
        self,
        signals: tuple[AuthoritySignal, ...],
    ) -> int:
        added = 0
        with self.conn:
            for signal in signals:
                added += int(
                    self._record_normalized(signal, commit=False)
                )
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
                relation.candidate_id,
                material.raw_evidence_ids_json,
                relation.derivation_variant_id,
                decision_ref.known_at,
                relation.polarity,
                relation.reciprocal,
                relation.context_id
            FROM authority_decision_refs AS decision_ref
            JOIN authority_relations AS relation
              ON relation.relation_id = decision_ref.relation_id
            JOIN authority_materials AS material
              ON material.material_id = relation.material_id
            WHERE decision_ref.decision_key = ?
              AND decision_ref.known_at <= ?
            ORDER BY
                relation.candidate_id,
                decision_ref.known_at,
                relation.relation_id
            """,
            (decision_key, knowledge_cutoff.isoformat()),
        ).fetchall()
        output: list[AuthoritySignal] = []
        for row in rows:
            raw_ids = tuple(json.loads(str(row[1])))
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
                    decision_key=decision_key,
                    candidate_id=str(row[0]),
                    raw_evidence_ids=raw_ids,
                    derivation_variant_id=str(row[2]),
                    known_at=datetime.fromisoformat(str(row[3])),
                    polarity=str(row[4]),  # type: ignore[arg-type]
                    reciprocal=bool(row[5]),
                    context_id=(
                        str(row[6]) if row[6] is not None else None
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
            "SELECT DISTINCT decision_key FROM authority_decision_refs "
            "ORDER BY decision_key"
        ).fetchall()
        return tuple(str(row[0]) for row in rows)

    def close(self) -> None:
        self.conn.close()
