"""Zero-LLM structural Line expansion for AML Path-B v0.

Anchor extraction is deliberately outside this module. The AML adapter may use
existing facts, NER, noun phrases, or another frozen extractor, but E1 receives
only explicit anchor terms and tests whether Line membership itself adds recall.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class BenchmarkUnit:
    unit_id: str
    occurred_at: datetime
    session_id: str
    anchor_terms: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StructuralLine:
    line_id: str
    anchor_term: str
    member_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RankedHit:
    unit_id: str
    rank: int


@dataclass(frozen=True, slots=True)
class ExpandedCandidate:
    unit_id: str
    source_line_ids: tuple[str, ...]
    best_seed_rank: int
    distance: int
    score: float


def build_anchor_lines(
    units: Sequence[BenchmarkUnit],
    *,
    min_members: int = 3,
    min_sessions: int = 2,
) -> tuple[StructuralLine, ...]:
    """Build time-ordered anchor Lines without a fixed temporal window."""

    by_anchor: dict[str, list[BenchmarkUnit]] = defaultdict(list)
    for unit in units:
        for raw_anchor in unit.anchor_terms:
            anchor = raw_anchor.strip().casefold()
            if anchor:
                by_anchor[anchor].append(unit)

    lines: list[StructuralLine] = []
    for anchor in sorted(by_anchor):
        unique_by_id = {unit.unit_id: unit for unit in by_anchor[anchor]}
        members = sorted(
            unique_by_id.values(),
            key=lambda unit: (unit.occurred_at, unit.unit_id),
        )
        if len(members) < min_members:
            continue
        if len({unit.session_id for unit in members}) < min_sessions:
            continue
        lines.append(
            StructuralLine(
                line_id=f"anchor:{anchor}",
                anchor_term=anchor,
                member_ids=tuple(unit.unit_id for unit in members),
            )
        )
    return tuple(lines)


def expand_from_ranked_hits(
    hits: Sequence[RankedHit],
    lines: Sequence[StructuralLine],
    *,
    radius: int = 1,
    rrf_k: int = 60,
) -> tuple[ExpandedCandidate, ...]:
    """Expand baseline hits to temporal neighbours on the same Lines.

    Seeds are never returned as expansion candidates. A candidate can be
    proposed by multiple Lines/seeds; its score is the sum of rank-decayed
    contributions, while distance records the closest temporal-neighbour hop.
    """

    if radius < 1:
        raise ValueError("radius must be >= 1")
    if rrf_k < 0:
        raise ValueError("rrf_k must be >= 0")

    seed_ranks = {hit.unit_id: hit.rank for hit in hits}
    if any(rank <= 0 for rank in seed_ranks.values()):
        raise ValueError("hit ranks must be positive")

    memberships: dict[str, list[tuple[StructuralLine, int]]] = defaultdict(list)
    for line in lines:
        for index, unit_id in enumerate(line.member_ids):
            memberships[unit_id].append((line, index))

    scores: dict[str, float] = defaultdict(float)
    source_lines: dict[str, set[str]] = defaultdict(set)
    best_seed_rank: dict[str, int] = {}
    best_distance: dict[str, int] = {}

    for seed_id, seed_rank in seed_ranks.items():
        for line, index in memberships.get(seed_id, ()):
            start = max(0, index - radius)
            stop = min(len(line.member_ids), index + radius + 1)
            for neighbour_index in range(start, stop):
                candidate_id = line.member_ids[neighbour_index]
                if candidate_id in seed_ranks:
                    continue
                distance = abs(neighbour_index - index)
                if distance == 0:
                    continue
                scores[candidate_id] += 1.0 / (rrf_k + seed_rank + distance)
                source_lines[candidate_id].add(line.line_id)
                best_seed_rank[candidate_id] = min(
                    best_seed_rank.get(candidate_id, seed_rank),
                    seed_rank,
                )
                best_distance[candidate_id] = min(
                    best_distance.get(candidate_id, distance),
                    distance,
                )

    ordered = sorted(
        scores,
        key=lambda unit_id: (
            -scores[unit_id],
            best_seed_rank[unit_id],
            best_distance[unit_id],
            unit_id,
        ),
    )
    return tuple(
        ExpandedCandidate(
            unit_id=unit_id,
            source_line_ids=tuple(sorted(source_lines[unit_id])),
            best_seed_rank=best_seed_rank[unit_id],
            distance=best_distance[unit_id],
            score=scores[unit_id],
        )
        for unit_id in ordered
    )


def evidence_recall_at_k(
    ranked_unit_ids: Sequence[str],
    gold_unit_ids: Iterable[str],
    *,
    k: int,
) -> float:
    """Return evidence recall in [0, 1] for one question."""

    if k < 0:
        raise ValueError("k must be >= 0")
    gold = set(gold_unit_ids)
    if not gold:
        return 1.0
    recalled = set(ranked_unit_ids[:k]) & gold
    return len(recalled) / len(gold)
