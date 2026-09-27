"""Path B point-cloud bootstrap algorithm bakeoff.

Research-only.  This experiment starts from many local SemanticBlock-like points
and asks when a stable latent trend is strong enough to seed a Worktree.

The structural algorithms never read gold trend labels.  Gold exists only in
the evaluator.

The experiment deliberately separates:
  * static semantic proximity,
  * data-volume-driven density,
  * temporal recurrence,
  * multiscale stability.

No hard temporal window is used.  Time is evidence about recurrence/persistence,
not a rule that old points become unrelated.
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class Point:
    point_id: str
    day: int
    features: frozenset[str]
    gold_trends: frozenset[str] = frozenset()
    decoy_group: str | None = None


@dataclass(frozen=True, slots=True)
class Candidate:
    algorithm: str
    member_ids: frozenset[str]


@dataclass(frozen=True, slots=True)
class TrendSpec:
    name: str
    domain: str
    features: tuple[str, ...]
    width: int


TREND_SPECS: tuple[TrendSpec, ...] = (
    TrendSpec(
        "TR_PRICE_UNCERTAINTY",
        "domain_trading",
        (
            "expectation_gap",
            "priced_certainty",
            "crowding",
            "imagination_space",
            "open_catalyst",
            "narrative_optional",
            "asymmetry",
        ),
        3,
    ),
    TrendSpec(
        "TR_EXECUTION_RISK",
        "domain_trading",
        (
            "timing",
            "position_size",
            "stop_structure",
            "breakout",
            "sector_strength",
            "wait_signal",
            "risk_reward",
        ),
        3,
    ),
    TrendSpec(
        "ENG_BOUNDARY_MINIMALISM",
        "domain_engineering",
        (
            "boundary",
            "interface",
            "reuse",
            "delta_reasoning",
            "minimal_core",
            "authority",
            "lifecycle",
        ),
        3,
    ),
    TrendSpec(
        "ENG_FALSIFICATION",
        "domain_engineering",
        (
            "falsification",
            "negative_case",
            "mutation",
            "invariant",
            "failure_boundary",
            "evidence",
            "regression",
        ),
        3,
    ),
    TrendSpec(
        "WRITE_REASONING_DENSITY",
        "domain_writing",
        (
            "causal_chain",
            "argument_density",
            "strong_judgment",
            "evidence",
            "uncertainty",
            "thesis",
            "continuity",
            "counterexample",
            "mechanism",
        ),
        3,
    ),
    TrendSpec(
        "WRITE_NATIVE_STYLE",
        "domain_writing",
        (
            "native_voice",
            "long_paragraph",
            "avoid_report",
            "avoid_listicle",
            "terminology_restraint",
            "texture",
            "continuity",
            "rhythm",
            "specificity",
        ),
        3,
    ),
)

GENERIC_FEATURES = ("preference", "critique", "decision", "observation", "comparison")


def _trend_points(spec: TrendSpec, trend_index: int) -> list[Point]:
    points: list[Point] = []
    feature_count = len(spec.features)
    for i in range(18):
        # Long-lived evidence: all trends recur through most of the year.
        day = 4 + i * 18 + trend_index * 2
        start = (i * 2 + trend_index) % feature_count
        chosen = {
            spec.features[(start + step * 2) % feature_count]
            for step in range(spec.width)
        }
        chosen.add(spec.domain)
        chosen.add(GENERIC_FEATURES[(i + trend_index) % len(GENERIC_FEATURES)])
        points.append(
            Point(
                point_id=f"t{trend_index}_{i:02d}",
                day=day,
                features=frozenset(chosen),
                gold_trends=frozenset({spec.name}),
            )
        )
    return points


def _decoy_points() -> list[Point]:
    """Short coherent bursts that must not be promoted as longitudinal trends."""

    groups = (
        ("sports_final", 48, ("sports", "score", "team", "match")),
        ("phone_repair", 109, ("device", "battery", "repair", "screen")),
        ("travel_booking", 170, ("travel", "flight", "hotel", "booking")),
        ("food_order", 231, ("food", "delivery", "restaurant", "menu")),
        ("weather_alert", 291, ("weather", "rain", "forecast", "storm")),
    )
    points: list[Point] = []
    for group_index, (group, start_day, pool) in enumerate(groups):
        for i in range(4):
            features = {
                pool[i % len(pool)],
                pool[(i + 1) % len(pool)],
                "observation",
                f"burst_{group_index}",
            }
            points.append(
                Point(
                    point_id=f"d{group_index}_{i}",
                    day=start_day + i,
                    features=frozenset(features),
                    decoy_group=group,
                )
            )
    return points


def _noise_points() -> list[Point]:
    """Sparse one-off material with some generic/domain overlap."""

    domains = ("domain_trading", "domain_engineering", "domain_writing", "daily_life")
    points: list[Point] = []
    for i in range(24):
        day = 7 + i * 13
        features = {
            domains[i % len(domains)],
            GENERIC_FEATURES[(i * 3) % len(GENERIC_FEATURES)],
            f"oneoff_topic_{i}",
            f"oneoff_detail_{(i * 7) % 29}",
        }
        points.append(Point(f"n{i:02d}", day, frozenset(features)))
    return points


def corpus() -> tuple[Point, ...]:
    points: list[Point] = []
    for trend_index, spec in enumerate(TREND_SPECS):
        points.extend(_trend_points(spec, trend_index))
    points.extend(_decoy_points())
    points.extend(_noise_points())
    return tuple(sorted(points, key=lambda p: (p.day, p.point_id)))


def _weights(points: tuple[Point, ...]) -> dict[str, float]:
    df: Counter[str] = Counter()
    for point in points:
        df.update(point.features)
    n = len(points)
    return {
        feature: math.log((n + 1) / (count + 1)) + 1.0
        for feature, count in df.items()
    }


def _weighted_jaccard(left: Point, right: Point, weights: dict[str, float]) -> float:
    union = left.features | right.features
    if not union:
        return 0.0
    inter = left.features & right.features
    return sum(weights[f] for f in inter) / sum(weights[f] for f in union)


def _pairwise_mean(ids: frozenset[str], by_id: dict[str, Point], weights: dict[str, float]) -> float:
    ordered = sorted(ids)
    if len(ordered) < 2:
        return 0.0
    values: list[float] = []
    for i, left_id in enumerate(ordered):
        for right_id in ordered[i + 1 :]:
            values.append(_weighted_jaccard(by_id[left_id], by_id[right_id], weights))
    return sum(values) / len(values) if values else 0.0


def _components(nodes: Iterable[str], edges: Iterable[tuple[str, str]]) -> list[frozenset[str]]:
    parent = {node: node for node in nodes}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for left, right in edges:
        union(left, right)

    groups: dict[str, set[str]] = defaultdict(set)
    for node in parent:
        groups[find(node)].add(node)
    return [frozenset(value) for value in groups.values()]


def pair_components(points: tuple[Point, ...], *, threshold: float = 0.31) -> tuple[Candidate, ...]:
    """A0: direct threshold graph.  Strong baseline, intentionally non-longitudinal."""

    weights = _weights(points)
    edges: list[tuple[str, str]] = []
    for i, left in enumerate(points):
        for right in points[i + 1 :]:
            if _weighted_jaccard(left, right, weights) >= threshold:
                edges.append((left.point_id, right.point_id))
    comps = _components((p.point_id for p in points), edges)
    return tuple(
        Candidate("A0_PAIR_COMPONENTS", comp)
        for comp in comps
        if len(comp) >= 2
    )


def mutual_knn(
    points: tuple[Point, ...],
    *,
    k: int = 4,
    min_similarity: float = 0.10,
) -> tuple[Candidate, ...]:
    """A1: static mutual-kNN connectivity over the whole visible cloud."""

    weights = _weights(points)
    neighbours: dict[str, list[tuple[float, str]]] = {}
    for point in points:
        ranked = sorted(
            (
                (_weighted_jaccard(point, other, weights), other.point_id)
                for other in points
                if other.point_id != point.point_id
            ),
            reverse=True,
        )
        neighbours[point.point_id] = [
            item for item in ranked[:k] if item[0] >= min_similarity
        ]

    lookup = {
        point_id: {other_id for _score, other_id in values}
        for point_id, values in neighbours.items()
    }
    edges: list[tuple[str, str]] = []
    for left_id, values in lookup.items():
        for right_id in values:
            if left_id in lookup.get(right_id, set()) and left_id < right_id:
                edges.append((left_id, right_id))
    comps = _components((p.point_id for p in points), edges)
    return tuple(
        Candidate("A1_MUTUAL_KNN", comp)
        for comp in comps
        if len(comp) >= 3
    )


def _dedupe(candidates: list[frozenset[str]], *, overlap: float = 0.72) -> list[frozenset[str]]:
    ordered = sorted(candidates, key=lambda ids: (-len(ids), tuple(sorted(ids))))
    kept: list[frozenset[str]] = []
    for candidate in ordered:
        duplicate = False
        for existing in kept:
            union = candidate | existing
            score = len(candidate & existing) / len(union) if union else 0.0
            if score >= overlap:
                duplicate = True
                break
        if not duplicate:
            kept.append(candidate)
    return kept


def recurrent_density(
    points: tuple[Point, ...],
    *,
    similarity: float = 0.18,
    min_support: int = 4,
    min_span_days: int = 42,
    min_time_buckets: int = 3,
    bucket_days: int = 45,
    min_cohesion: float = 0.075,
) -> tuple[Candidate, ...]:
    """A2: density must recur across time before a Worktree seed is emitted.

    Each point proposes a local semantic neighbourhood.  A neighbourhood is a
    candidate only when it has enough support, enough temporal spread, enough
    distinct time buckets, and non-trivial internal cohesion.
    """

    weights = _weights(points)
    by_id = {p.point_id: p for p in points}
    raw: list[frozenset[str]] = []

    for anchor in points:
        ids = {
            other.point_id
            for other in points
            if other.point_id == anchor.point_id
            or _weighted_jaccard(anchor, other, weights) >= similarity
        }
        if len(ids) < min_support:
            continue
        days = [by_id[point_id].day for point_id in ids]
        if max(days) - min(days) < min_span_days:
            continue
        buckets = {day // bucket_days for day in days}
        if len(buckets) < min_time_buckets:
            continue
        frozen = frozenset(ids)
        if _pairwise_mean(frozen, by_id, weights) < min_cohesion:
            continue
        raw.append(frozen)

    return tuple(
        Candidate("A2_RECURRENT_DENSITY", ids)
        for ids in _dedupe(raw)
    )



def persistent_mutual_knn(
    points: tuple[Point, ...],
    *,
    k: int = 4,
    min_similarity: float = 0.10,
    min_support: int = 4,
    min_span_days: int = 42,
    min_time_buckets: int = 3,
    bucket_days: int = 45,
) -> tuple[Candidate, ...]:
    """A4: static semantic components must also persist longitudinally.

    This keeps the low-fragmentation geometry of mutual-kNN, then applies time
    as evidence that a component is a recurring trend rather than a short burst.
    No maximum-age cutoff exists.
    """

    base = mutual_knn(points, k=k, min_similarity=min_similarity)
    by_id = {point.point_id: point for point in points}
    kept: list[Candidate] = []
    for candidate in base:
        if len(candidate.member_ids) < min_support:
            continue
        days = [by_id[point_id].day for point_id in candidate.member_ids]
        if max(days) - min(days) < min_span_days:
            continue
        if len({day // bucket_days for day in days}) < min_time_buckets:
            continue
        kept.append(Candidate("A4_PERSISTENT_MUTUAL_KNN", candidate.member_ids))
    return tuple(kept)


def multiscale_recurrent(points: tuple[Point, ...]) -> tuple[Candidate, ...]:
    """A3: keep recurrent structures that survive more than one local scale.

    This is a simple stability supplier: no single similarity threshold can
    create a Worktree seed by itself.
    """

    scales = (0.15, 0.18, 0.21)
    per_scale = [
        [candidate.member_ids for candidate in recurrent_density(points, similarity=scale)]
        for scale in scales
    ]
    all_candidates: list[tuple[int, frozenset[str]]] = [
        (scale_index, ids)
        for scale_index, group in enumerate(per_scale)
        for ids in group
    ]

    accepted: list[frozenset[str]] = []
    for scale_index, candidate in all_candidates:
        supporting_scales: set[int] = {scale_index}
        matched: list[frozenset[str]] = [candidate]
        for other_scale, other in all_candidates:
            if other_scale == scale_index:
                continue
            union = candidate | other
            overlap = len(candidate & other) / len(union) if union else 0.0
            if overlap >= 0.50:
                supporting_scales.add(other_scale)
                matched.append(other)
        if len(supporting_scales) < 2:
            continue

        # Intersection preserves the stable semantic core while still allowing
        # overlapping structures to coexist.
        stable = set(matched[0])
        for item in matched[1:]:
            stable &= set(item)
        if len(stable) >= 4:
            accepted.append(frozenset(stable))

    return tuple(
        Candidate("A3_MULTISCALE_RECURRENT", ids)
        for ids in _dedupe(accepted, overlap=0.65)
    )


ALGORITHMS = {
    "A0_PAIR_COMPONENTS": pair_components,
    "A1_MUTUAL_KNN": mutual_knn,
    "A2_RECURRENT_DENSITY": recurrent_density,
    "A3_MULTISCALE_RECURRENT": multiscale_recurrent,
    "A4_PERSISTENT_MUTUAL_KNN": persistent_mutual_knn,
}


def _evaluate(points: tuple[Point, ...], candidates: tuple[Candidate, ...]) -> dict[str, object]:
    by_id = {point.point_id: point for point in points}
    visible_gold: Counter[str] = Counter()
    for point in points:
        visible_gold.update(point.gold_trends)

    eligible = {
        trend for trend, count in visible_gold.items()
        if count >= 4
    }
    discovered: set[str] = set()
    false_candidates = 0
    aligned_counts: Counter[str] = Counter()
    purities: list[float] = []
    candidate_details: list[dict[str, object]] = []

    for candidate in candidates:
        trend_counts: Counter[str] = Counter()
        decoy_counts: Counter[str] = Counter()
        for point_id in candidate.member_ids:
            point = by_id[point_id]
            trend_counts.update(point.gold_trends)
            if point.decoy_group is not None:
                decoy_counts[point.decoy_group] += 1

        dominant: str | None = None
        dominant_count = 0
        if trend_counts:
            dominant, dominant_count = trend_counts.most_common(1)[0]
        purity = dominant_count / len(candidate.member_ids) if dominant else 0.0
        coverage = (
            dominant_count / visible_gold[dominant]
            if dominant is not None and visible_gold[dominant]
            else 0.0
        )
        qualifies = (
            dominant is not None
            and dominant in eligible
            and purity >= 0.65
            and dominant_count >= 3
            and coverage >= 0.25
        )
        if qualifies:
            discovered.add(dominant)
            aligned_counts[dominant] += 1
            purities.append(purity)
        else:
            false_candidates += 1

        candidate_details.append(
            {
                "size": len(candidate.member_ids),
                "dominant": dominant,
                "purity": purity,
                "coverage": coverage,
                "qualifies": qualifies,
                "decoy_counts": dict(decoy_counts),
            }
        )

    fragmentation = (
        sum(aligned_counts.values()) / len(discovered)
        if discovered else 0.0
    )
    return {
        "visible_points": len(points),
        "eligible_trends": len(eligible),
        "eligible_trend_names": sorted(eligible),
        "discovered_trends": len(discovered),
        "discovered_trend_names": sorted(discovered),
        "trend_recall": len(discovered) / len(eligible) if eligible else None,
        "candidate_count": len(candidates),
        "false_candidates": false_candidates,
        "false_candidate_rate": false_candidates / len(candidates) if candidates else 0.0,
        "mean_qualifying_purity": sum(purities) / len(purities) if purities else None,
        "fragmentation_per_discovered_trend": fragmentation,
        "candidate_details": candidate_details,
    }


def volume_curve() -> dict[str, object]:
    points = corpus()
    cutoffs = (40, 70, 100, 130, len(points))
    results: dict[str, list[dict[str, object]]] = {name: [] for name in ALGORITHMS}

    for cutoff in cutoffs:
        visible = points[:cutoff]
        for name, algorithm in ALGORITHMS.items():
            candidates = algorithm(visible)
            result = _evaluate(visible, candidates)
            result["cutoff"] = cutoff
            results[name].append(result)

    return {
        "corpus_points": len(points),
        "gold_trends": [spec.name for spec in TREND_SPECS],
        "cutoffs": list(cutoffs),
        "algorithms": results,
    }



def temporal_collapse_control() -> dict[str, object]:
    """Collapse each true trend into a short episode while preserving semantics.

    Unlike a plain timestamp shuffle, this specifically destroys long-horizon
    persistence while keeping the same point count and semantic geometry.
    Gold labels are used only to construct this offline negative-control corpus;
    discovery algorithms still never receive them.
    """

    points = corpus()
    trend_base_day = {
        spec.name: 30 + index * 45
        for index, spec in enumerate(TREND_SPECS)
    }
    trend_offsets: Counter[str] = Counter()
    collapsed: list[Point] = []

    for point in points:
        if point.gold_trends:
            trend = sorted(point.gold_trends)[0]
            offset = trend_offsets[trend]
            trend_offsets[trend] += 1
            new_day = trend_base_day[trend] + (offset % 12)
            collapsed.append(
                Point(
                    point.point_id,
                    new_day,
                    point.features,
                    point.gold_trends,
                    point.decoy_group,
                )
            )
        else:
            collapsed.append(point)

    collapsed_points = tuple(sorted(collapsed, key=lambda p: (p.day, p.point_id)))
    report: dict[str, object] = {}
    for name in ("A2_RECURRENT_DENSITY", "A3_MULTISCALE_RECURRENT", "A4_PERSISTENT_MUTUAL_KNN"):
        algorithm = ALGORITHMS[name]
        normal_eval = _evaluate(points, algorithm(points))
        collapsed_eval = _evaluate(collapsed_points, algorithm(collapsed_points))
        report[name] = {
            "normal": {
                "trend_recall": normal_eval["trend_recall"],
                "false_candidate_rate": normal_eval["false_candidate_rate"],
                "candidate_count": normal_eval["candidate_count"],
            },
            "collapsed": {
                "trend_recall": collapsed_eval["trend_recall"],
                "false_candidate_rate": collapsed_eval["false_candidate_rate"],
                "candidate_count": collapsed_eval["candidate_count"],
            },
        }
    return report


def a4_parameter_sweep() -> list[dict[str, object]]:
    """Development sweep for the persistent mutual-kNN supplier.

    This is not held-out confirmation.  It maps the recall/false-seed tradeoff
    so a later untouched corpus can freeze one operating region.
    """

    points = corpus()
    rows: list[dict[str, object]] = []
    for k in (3, 4, 5, 6):
        for min_span_days in (30, 60, 90):
            candidates = persistent_mutual_knn(
                points,
                k=k,
                min_span_days=min_span_days,
            )
            evaluation = _evaluate(points, candidates)
            rows.append(
                {
                    "k": k,
                    "min_span_days": min_span_days,
                    "trend_recall": evaluation["trend_recall"],
                    "candidate_count": evaluation["candidate_count"],
                    "false_candidate_rate": evaluation["false_candidate_rate"],
                    "mean_qualifying_purity": evaluation["mean_qualifying_purity"],
                    "fragmentation_per_discovered_trend": evaluation["fragmentation_per_discovered_trend"],
                }
            )
    return rows


def temporal_shuffle_control() -> dict[str, object]:
    """Preserve semantics/cardinality while destroying longitudinal recurrence."""

    points = corpus()
    # Deterministic permutation: maps day order through a coprime stride.
    days = sorted(point.day for point in points)
    n = len(points)
    shuffled = tuple(
        Point(
            point.point_id,
            days[(index * 47) % n],
            point.features,
            point.gold_trends,
            point.decoy_group,
        )
        for index, point in enumerate(points)
    )
    shuffled = tuple(sorted(shuffled, key=lambda p: (p.day, p.point_id)))

    report: dict[str, object] = {}
    for name in ("A2_RECURRENT_DENSITY", "A3_MULTISCALE_RECURRENT"):
        algorithm = ALGORITHMS[name]
        normal_eval = _evaluate(points, algorithm(points))
        shuffled_eval = _evaluate(shuffled, algorithm(shuffled))
        report[name] = {
            "normal": {
                "trend_recall": normal_eval["trend_recall"],
                "false_candidate_rate": normal_eval["false_candidate_rate"],
                "candidate_count": normal_eval["candidate_count"],
            },
            "shuffled": {
                "trend_recall": shuffled_eval["trend_recall"],
                "false_candidate_rate": shuffled_eval["false_candidate_rate"],
                "candidate_count": shuffled_eval["candidate_count"],
            },
        }
    return report


def report() -> dict[str, object]:
    points = corpus()
    return {
        "experiment": "path-b-point-cloud-bootstrap",
        "architecture_question": (
            "Can many local SemanticBlock points reveal stable trend structure "
            "as history accumulates, before Worktree/Snake continuation begins?"
        ),
        "corpus": {
            "points": len(points),
            "days": max(point.day for point in points) - min(point.day for point in points),
            "true_trends": len(TREND_SPECS),
            "trend_points": sum(bool(point.gold_trends) for point in points),
            "decoy_burst_points": sum(point.decoy_group is not None for point in points),
            "noise_points": sum(not point.gold_trends and point.decoy_group is None for point in points),
        },
        "volume_curve": volume_curve(),
        "temporal_shuffle_control": temporal_shuffle_control(),
        "temporal_collapse_control": temporal_collapse_control(),
        "a4_parameter_sweep": a4_parameter_sweep(),
    }


def main() -> None:
    print(json.dumps(report(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
