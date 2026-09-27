"""Path B A4-R trajectory bootstrap experiment.

This experiment keeps A4's mutual-neighbour point-cloud supplier, but removes
three assumptions that conflict with frozen LCE boundaries:

1. no fixed temporal admission window/bucket;
2. knowledge time (when LCE learned evidence) is distinct from logical time
   (where the evidence belongs in the reconstructed cognition trajectory);
3. connected components are not treated as exclusive cognition boundaries.

The operator remains deliberately synthetic: gold labels are evaluation-only.
"""

from __future__ import annotations

import json
import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class Point:
    point_id: str
    known_at: int
    logical_at: int
    features: frozenset[str]
    knowledge_event: str
    gold_lines: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class TrajectoryCandidate:
    ordered_ids: tuple[str, ...]
    transition_scores: tuple[float, ...]

    @property
    def member_ids(self) -> frozenset[str]:
        return frozenset(self.ordered_ids)

    @property
    def mean_local_similarity(self) -> float:
        if not self.transition_scores:
            return 0.0
        return sum(self.transition_scores) / len(self.transition_scores)


def visible_at(points: Iterable[Point], cutoff: int) -> tuple[Point, ...]:
    """Knowledge-time visibility. Logical placement never grants early visibility."""
    return tuple(
        sorted(
            (point for point in points if point.known_at <= cutoff),
            key=lambda point: (point.logical_at, point.point_id),
        )
    )


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
    return sum(weights[item] for item in inter) / sum(weights[item] for item in union)


def _pairwise_mean(points: tuple[Point, ...]) -> float:
    if len(points) < 2:
        return 0.0
    weights = _weights(points)
    values = [
        _weighted_jaccard(left, right, weights)
        for index, left in enumerate(points)
        for right in points[index + 1 :]
    ]
    return sum(values) / len(values) if values else 0.0


def mutual_knn_edges(
    points: tuple[Point, ...],
    *,
    k: int = 4,
    min_similarity: float = 0.10,
) -> tuple[dict[tuple[str, str], float], dict[str, float]]:
    """A4 core: reciprocal local semantic neighbourhoods.

    The inverted feature index is exact for weighted Jaccard with a positive
    minimum similarity: pairs sharing no feature have similarity zero and
    cannot become neighbours.
    """

    weights = _weights(points)
    by_id = {point.point_id: point for point in points}
    feature_index: dict[str, set[str]] = defaultdict(set)
    for point in points:
        for feature in point.features:
            feature_index[feature].add(point.point_id)

    neighbours: dict[str, list[tuple[float, str]]] = {}
    for point in points:
        candidate_ids: set[str] = set()
        for feature in point.features:
            candidate_ids.update(feature_index[feature])
        candidate_ids.discard(point.point_id)

        ranked = sorted(
            (
                (_weighted_jaccard(point, by_id[other_id], weights), other_id)
                for other_id in candidate_ids
            ),
            reverse=True,
        )
        neighbours[point.point_id] = [
            item for item in ranked[:k] if item[0] >= min_similarity
        ]

    lookup = {
        point_id: {other_id: score for score, other_id in values}
        for point_id, values in neighbours.items()
    }
    edges: dict[tuple[str, str], float] = {}
    for left_id, values in lookup.items():
        for right_id, score in values.items():
            if left_id in lookup.get(right_id, {}):
                edge = tuple(sorted((left_id, right_id)))
                edges[edge] = min(score, lookup[right_id][left_id])
    return edges, weights


def trajectory_candidates(
    points: tuple[Point, ...],
    *,
    k: int = 4,
    min_similarity: float = 0.10,
    min_support: int = 3,
    beam_width: int = 16,
) -> tuple[TrajectoryCandidate, ...]:
    """A4-R: overlapping logical-time paths through reciprocal local structure.

    Time is not an admission gate. `logical_at` only orients progression.
    Same-logical-time neighbours remain useful local observations, but are not
    forced into a before/after sequence.

    Multiple maximal paths may share support, which preserves branching rather
    than converting the cloud into one exclusive connected component.
    """

    if not points:
        return ()

    edges, _weights_map = mutual_knn_edges(
        points,
        k=k,
        min_similarity=min_similarity,
    )
    by_id = {point.point_id: point for point in points}
    predecessors: dict[str, list[tuple[str, float]]] = defaultdict(list)

    for (left_id, right_id), score in edges.items():
        left = by_id[left_id]
        right = by_id[right_id]
        if left.logical_at == right.logical_at:
            continue
        if left.logical_at < right.logical_at:
            predecessors[right_id].append((left_id, score))
        else:
            predecessors[left_id].append((right_id, score))

    best_ending_at: dict[
        str,
        list[tuple[tuple[str, ...], tuple[float, ...]]],
    ] = {}
    raw: list[tuple[tuple[str, ...], tuple[float, ...]]] = []

    for point in sorted(points, key=lambda item: (item.logical_at, item.point_id)):
        proposals: list[tuple[tuple[str, ...], tuple[float, ...]]] = [
            ((point.point_id,), ())
        ]
        for predecessor_id, score in predecessors.get(point.point_id, []):
            predecessor_paths = best_ending_at.get(
                predecessor_id,
                [((predecessor_id,), ())],
            )
            for ordered_ids, transition_scores in predecessor_paths:
                if point.point_id in ordered_ids:
                    continue
                proposals.append(
                    (
                        ordered_ids + (point.point_id,),
                        transition_scores + (score,),
                    )
                )

        def rank(
            item: tuple[tuple[str, ...], tuple[float, ...]]
        ) -> tuple[float, int, float]:
            ordered_ids, transition_scores = item
            mean_score = (
                sum(transition_scores) / len(transition_scores)
                if transition_scores
                else 0.0
            )
            return (
                mean_score + 0.025 * len(ordered_ids),
                len(ordered_ids),
                mean_score,
            )

        proposals.sort(key=rank, reverse=True)
        kept: list[tuple[tuple[str, ...], tuple[float, ...]]] = []
        seen: set[tuple[str, ...]] = set()
        for proposal in proposals:
            if proposal[0] in seen:
                continue
            seen.add(proposal[0])
            kept.append(proposal)
            if len(kept) >= beam_width:
                break
        best_ending_at[point.point_id] = kept
        raw.extend(item for item in kept if len(item[0]) >= min_support)

    raw.sort(
        key=lambda item: (
            len(item[0]),
            sum(item[1]) / len(item[1]) if item[1] else 0.0,
        ),
        reverse=True,
    )

    maximal: list[TrajectoryCandidate] = []
    for ordered_ids, transition_scores in raw:
        member_ids = set(ordered_ids)
        if any(member_ids < set(existing.ordered_ids) for existing in maximal):
            continue
        near_duplicate = False
        for existing in maximal:
            existing_ids = set(existing.ordered_ids)
            union = member_ids | existing_ids
            overlap = len(member_ids & existing_ids) / len(union) if union else 0.0
            if overlap >= 0.90:
                near_duplicate = True
                break
        if near_duplicate:
            continue
        maximal.append(TrajectoryCandidate(ordered_ids, transition_scores))

    return tuple(maximal)


def candidate_diagnostics(
    candidate: TrajectoryCandidate,
    points: tuple[Point, ...],
) -> dict[str, object]:
    by_id = {point.point_id: point for point in points}
    selected = [by_id[point_id] for point_id in candidate.ordered_ids]
    logical_times = [point.logical_at for point in selected]
    known_times = [point.known_at for point in selected]
    return {
        "ordered_ids": list(candidate.ordered_ids),
        "support": len(candidate.ordered_ids),
        "mean_local_similarity": candidate.mean_local_similarity,
        "logical_span": max(logical_times) - min(logical_times),
        "knowledge_span": max(known_times) - min(known_times),
        "independent_knowledge_events": len(
            {point.knowledge_event for point in selected}
        ),
        "global_pairwise_cohesion": _pairwise_mean(tuple(selected)),
    }


def _best_for_line(
    points: tuple[Point, ...],
    candidates: tuple[TrajectoryCandidate, ...],
    line: str,
) -> dict[str, object] | None:
    gold_ids = {
        point.point_id for point in points if line in point.gold_lines
    }
    if not gold_ids:
        return None

    ranked: list[tuple[float, float, TrajectoryCandidate]] = []
    for candidate in candidates:
        member_ids = set(candidate.ordered_ids)
        overlap = len(member_ids & gold_ids)
        if not overlap:
            continue
        purity = overlap / len(member_ids)
        coverage = overlap / len(gold_ids)
        ranked.append((coverage, purity, candidate))

    if not ranked:
        return None

    coverage, purity, candidate = max(
        ranked,
        key=lambda item: (item[0], item[1], len(item[2].ordered_ids)),
    )
    return {
        "coverage": coverage,
        "purity": purity,
        "candidate": candidate_diagnostics(candidate, points),
    }


def _components(nodes: Iterable[str], edges: Iterable[tuple[str, str]]) -> list[frozenset[str]]:
    parent = {node: node for node in nodes}

    def find(item: str) -> str:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(left: str, right: str) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for left, right in edges:
        union(left, right)

    groups: dict[str, set[str]] = defaultdict(set)
    for node in parent:
        groups[find(node)].add(node)
    return [frozenset(group) for group in groups.values()]


def legacy_a4_like(
    points: tuple[Point, ...],
    *,
    axis: str,
    k: int = 4,
    min_similarity: float = 0.10,
    min_support: int = 4,
    min_span: int = 42,
    bucket_size: int = 45,
    min_buckets: int = 3,
    min_cohesion: float = 0.15,
) -> tuple[frozenset[str], ...]:
    """The previous A4 shape, parameterized by one time axis for comparison."""

    if axis not in {"known", "logical"}:
        raise ValueError("axis must be 'known' or 'logical'")
    edges, weights = mutual_knn_edges(
        points,
        k=k,
        min_similarity=min_similarity,
    )
    by_id = {point.point_id: point for point in points}
    output: list[frozenset[str]] = []
    for component in _components(
        (point.point_id for point in points),
        edges.keys(),
    ):
        if len(component) < min_support:
            continue
        times = [
            (
                by_id[point_id].known_at
                if axis == "known"
                else by_id[point_id].logical_at
            )
            for point_id in component
        ]
        if max(times) - min(times) < min_span:
            continue
        if len({time // bucket_size for time in times}) < min_buckets:
            continue

        ordered = sorted(component)
        values = [
            _weighted_jaccard(by_id[left_id], by_id[right_id], weights)
            for index, left_id in enumerate(ordered)
            for right_id in ordered[index + 1 :]
        ]
        cohesion = sum(values) / len(values) if values else 0.0
        if cohesion < min_cohesion:
            continue
        output.append(component)
    return tuple(output)


def sparse_longitudinal_fixture(noise_points: int = 5000) -> tuple[Point, ...]:
    """Four relevant points over ~8 years inside a large irrelevant history."""

    points: list[Point] = []
    feature_steps = (
        {"s0", "s1", "s2", "axis_sparse"},
        {"s1", "s2", "s3", "axis_sparse"},
        {"s2", "s3", "s4", "axis_sparse"},
        {"s3", "s4", "s5", "axis_sparse"},
    )
    times = (0, 800, 1700, 2900)
    for index, (time, features) in enumerate(zip(times, feature_steps)):
        points.append(
            Point(
                f"sparse_{index}",
                time,
                time,
                frozenset(features),
                f"sparse_observation_{index}",
                frozenset({"SPARSE_LINE"}),
            )
        )

    rng = random.Random(20260927)
    for index in range(noise_points):
        logical_at = rng.randrange(0, 3000)
        points.append(
            Point(
                f"noise_{index}",
                logical_at,
                logical_at,
                frozenset(
                    {
                        f"noise_domain_{index % 500}",
                        f"noise_detail_{index}",
                        f"noise_mode_{(index * 17) % 997}",
                    }
                ),
                f"noise_observation_{index}",
            )
        )
    return tuple(points)


def drift_fixture() -> tuple[Point, ...]:
    """A line with strong local continuity but weak all-pairs cohesion."""

    feature_steps = (
        {"phase0", "a", "b", "drift_axis_0"},
        {"a", "b", "c", "drift_axis_1"},
        {"b", "c", "d", "drift_axis_2"},
        {"c", "d", "e", "drift_axis_3"},
        {"d", "e", "f", "drift_axis_4"},
        {"e", "f", "g", "drift_axis_5"},
    )
    return tuple(
        Point(
            f"drift_{index}",
            index * 500,
            index * 500,
            frozenset(features),
            f"drift_observation_{index}",
            frozenset({"DRIFT_LINE"}),
        )
        for index, features in enumerate(feature_steps)
    )


def retroactive_fixture() -> tuple[Point, ...]:
    """One 2021 state is only learned in 2026."""

    years = (2020, 2021, 2022, 2023)
    known_years = (2020, 2026, 2022, 2023)
    feature_steps = (
        {"retro_a", "retro_b", "retro_c"},
        {"retro_b", "retro_c", "retro_d"},
        {"retro_c", "retro_d", "retro_e"},
        {"retro_d", "retro_e", "retro_f"},
    )
    return tuple(
        Point(
            f"retro_{year}",
            known_year,
            year,
            frozenset(features),
            f"knowledge_{known_year}_{year}",
            frozenset({"RETRO_LINE"}),
        )
        for year, known_year, features in zip(years, known_years, feature_steps)
    )


def branching_fixture() -> tuple[Point, ...]:
    """Shared trunk, then two mutually exclusive/alternative continuations."""

    rows = (
        ("trunk_0", 0, {"core", "x", "y", "root"}, {"BRANCH_A", "BRANCH_B"}),
        ("trunk_1", 100, {"core", "y", "z", "root"}, {"BRANCH_A", "BRANCH_B"}),
        ("a_2", 200, {"core", "z", "a1", "a2"}, {"BRANCH_A"}),
        ("a_3", 300, {"core", "a1", "a2", "a3"}, {"BRANCH_A"}),
        ("a_4", 400, {"core", "a2", "a3", "a4"}, {"BRANCH_A"}),
        ("b_2", 200, {"core", "z", "b1", "b2"}, {"BRANCH_B"}),
        ("b_3", 300, {"core", "b1", "b2", "b3"}, {"BRANCH_B"}),
        ("b_4", 400, {"core", "b2", "b3", "b4"}, {"BRANCH_B"}),
    )
    return tuple(
        Point(
            point_id,
            logical_at,
            logical_at,
            frozenset(features),
            point_id,
            frozenset(lines),
        )
        for point_id, logical_at, features, lines in rows
    )


def burst_and_sparse_fixture() -> tuple[Point, ...]:
    """Same local geometry, very different longitudinal evidence shape."""

    base = (
        {"p0", "p1", "p2", "axis"},
        {"p1", "p2", "p3", "axis"},
        {"p2", "p3", "p4", "axis"},
        {"p3", "p4", "p5", "axis"},
    )
    points: list[Point] = []
    for index, features in enumerate(base):
        points.append(
            Point(
                f"burst_{index}",
                100 + index,
                100 + index,
                frozenset({f"burst_{feature}" for feature in features}),
                "one_burst_episode",
                frozenset({"BURST"}),
            )
        )
    for index, (logical_at, features) in enumerate(zip((0, 800, 1700, 2900), base)):
        points.append(
            Point(
                f"spread_{index}",
                logical_at,
                logical_at,
                frozenset({f"spread_{feature}" for feature in features}),
                f"spread_episode_{index}",
                frozenset({"SPREAD"}),
            )
        )
    return tuple(points)


def retrieval_surface_scores() -> dict[str, float]:
    """Lower-bound test: a mature line exposes more anchors without one centroid."""

    points = drift_fixture()
    earliest = points[0]
    late_query = Point(
        "late_query",
        4000,
        4000,
        frozenset({"e", "f", "g", "drift_axis_5"}),
        "query",
    )
    unrelated = Point(
        "unrelated_query",
        4000,
        4000,
        frozenset({"restaurant", "menu", "delivery"}),
        "query",
    )
    weights = _weights(points + (late_query, unrelated))

    return {
        "single_earliest_to_late": _weighted_jaccard(earliest, late_query, weights),
        "mature_multi_anchor_to_late": max(
            _weighted_jaccard(point, late_query, weights) for point in points
        ),
        "mature_multi_anchor_to_unrelated": max(
            _weighted_jaccard(point, unrelated, weights) for point in points
        ),
    }


def report() -> dict[str, object]:
    sparse = sparse_longitudinal_fixture()
    sparse_candidates = trajectory_candidates(sparse)
    sparse_best = _best_for_line(sparse, sparse_candidates, "SPARSE_LINE")

    drift = drift_fixture()
    drift_candidates = trajectory_candidates(drift, k=3, min_similarity=0.08)
    drift_best = _best_for_line(drift, drift_candidates, "DRIFT_LINE")
    drift_legacy = legacy_a4_like(
        drift,
        axis="logical",
        k=3,
        min_similarity=0.08,
    )

    retro = retroactive_fixture()
    pre_cutoff = visible_at(retro, 2025)
    post_cutoff = visible_at(retro, 2026)
    pre_candidates = trajectory_candidates(
        pre_cutoff,
        k=3,
        min_similarity=0.08,
        min_support=2,
    )
    post_candidates = trajectory_candidates(
        post_cutoff,
        k=3,
        min_similarity=0.08,
        min_support=2,
    )

    branching = branching_fixture()
    branch_candidates = trajectory_candidates(
        branching,
        k=3,
        min_similarity=0.08,
    )

    temporal_shape = burst_and_sparse_fixture()
    temporal_candidates = trajectory_candidates(
        temporal_shape,
        k=3,
        min_similarity=0.08,
    )
    burst_best = _best_for_line(temporal_shape, temporal_candidates, "BURST")
    spread_best = _best_for_line(temporal_shape, temporal_candidates, "SPREAD")

    return {
        "experiment": "path-b-a4r-trajectory-bootstrap",
        "a4r_contract": {
            "kept": [
                "mutual semantic neighbourhood",
                "local point-cloud structure",
            ],
            "removed_as_hard_gates": [
                "minimum chronological span",
                "fixed time buckets",
                "global connected-component equals cognition",
            ],
            "time_model": {
                "known_at": "visibility / no-future authority",
                "logical_at": "placement and trajectory ordering",
            },
        },
        "sparse_longitudinal": {
            "points": len(sparse),
            "relevant_points": 4,
            "best": sparse_best,
        },
        "dynamic_drift": {
            "global_pairwise_cohesion": _pairwise_mean(drift),
            "a4r_best": drift_best,
            "legacy_a4_like_candidates": [sorted(ids) for ids in drift_legacy],
        },
        "dual_time_retroactive": {
            "cutoff_2025_visible": [point.point_id for point in pre_cutoff],
            "cutoff_2026_visible": [point.point_id for point in post_cutoff],
            "cutoff_2025_paths": [
                list(candidate.ordered_ids) for candidate in pre_candidates
            ],
            "cutoff_2026_paths": [
                list(candidate.ordered_ids) for candidate in post_candidates
            ],
        },
        "branching": {
            "paths": [list(candidate.ordered_ids) for candidate in branch_candidates],
            "branch_a": _best_for_line(branching, branch_candidates, "BRANCH_A"),
            "branch_b": _best_for_line(branching, branch_candidates, "BRANCH_B"),
        },
        "time_as_evidence_not_gate": {
            "burst": burst_best,
            "sparse": spread_best,
        },
        "mature_retrieval_surface": retrieval_surface_scores(),
    }


def main() -> None:
    print(json.dumps(report(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
