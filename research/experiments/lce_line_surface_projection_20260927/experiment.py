"""Line -> Surface projection experiment.

Purpose:
- detect a higher-order relation from trajectory shape, not raw point similarity;
- keep the relation as a derived projection whose evidence closes to Raw Evidence;
- allow the callable surface to be useful for cross-line queries without
  displacing local line projections for concrete queries;
- preserve rollback: if one contributing line is recompiled into a materially
  different trajectory, the prior surface can become unresolved.

No abstraction-level taxonomy is assigned.
"""

from __future__ import annotations

import itertools
import json
import math
from dataclasses import dataclass
from typing import Iterable

from research.experiments.lce_callable_projection_20260927.experiment import (
    Projection,
    ProjectionGraph,
    RawEvidence,
    rank_callable_projections,
)


UNKNOWN = "UNKNOWN"
SUPPORTED = "SUPPORTED"


@dataclass(frozen=True, slots=True)
class Line:
    line_id: str
    raw_ids: tuple[str, ...]
    vectors: tuple[tuple[float, ...], ...]
    domain_features: frozenset[str]


@dataclass(frozen=True, slots=True)
class SurfaceCandidate:
    line_ids: tuple[str, ...]
    min_pairwise_shape_similarity: float
    mean_pairwise_shape_similarity: float


def cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def trajectory_shape(line: Line) -> tuple[float, ...]:
    """Translation-invariant flattened local displacement sequence."""

    values: list[float] = []
    for left, right in zip(line.vectors, line.vectors[1:]):
        values.extend(right_value - left_value for left_value, right_value in zip(left, right))

    norm = math.sqrt(sum(value * value for value in values))
    if not norm:
        return tuple(0.0 for _ in values)
    return tuple(value / norm for value in values)


def shape_similarity(left: Line, right: Line) -> float:
    return cosine(trajectory_shape(left), trajectory_shape(right))


def raw_cross_line_similarity(left: Line, right: Line) -> dict[str, float]:
    values = [
        cosine(left_point, right_point)
        for left_point in left.vectors
        for right_point in right.vectors
    ]
    return {
        "max": max(values) if values else 0.0,
        "mean": sum(values) / len(values) if values else 0.0,
    }


def shape_tokens(line: Line, *, buckets: int = 6) -> frozenset[str]:
    """Small callable representation derived from transition geometry.

    Tokens are operator scaffolding, not semantic categories. They encode the
    relative direction of the final two trajectory dimensions for this fixture.
    """

    tokens: set[str] = set()
    for index, (left, right) in enumerate(zip(line.vectors, line.vectors[1:])):
        dx = right[-2] - left[-2]
        dy = right[-1] - left[-1]
        total = abs(dx) + abs(dy)
        if total == 0:
            bucket = 0
        else:
            share = dy / total
            bucket = int(round(share * buckets))
        tokens.add(f"shape:{index}:{bucket}")
    return frozenset(tokens)


def discover_surfaces(
    lines: tuple[Line, ...],
    *,
    min_lines: int = 3,
    min_shape_similarity: float = 0.95,
) -> tuple[SurfaceCandidate, ...]:
    """Enumerate maximal overlapping cliques in line-shape similarity space."""

    by_id = {line.line_id: line for line in lines}
    valid_groups: list[tuple[str, ...]] = []

    for size in range(min_lines, len(lines) + 1):
        for combo in itertools.combinations(lines, size):
            similarities = [
                shape_similarity(left, right)
                for left, right in itertools.combinations(combo, 2)
            ]
            if similarities and min(similarities) >= min_shape_similarity:
                valid_groups.append(tuple(sorted(line.line_id for line in combo)))

    maximal = [
        group
        for group in valid_groups
        if not any(set(group) < set(other) for other in valid_groups)
    ]

    output: list[SurfaceCandidate] = []
    for group in sorted(set(maximal)):
        similarities = [
            shape_similarity(by_id[left_id], by_id[right_id])
            for left_id, right_id in itertools.combinations(group, 2)
        ]
        output.append(
            SurfaceCandidate(
                line_ids=group,
                min_pairwise_shape_similarity=min(similarities),
                mean_pairwise_shape_similarity=sum(similarities) / len(similarities),
            )
        )
    return tuple(output)


def _line_vectors(
    anchor: tuple[float, float, float, float],
    states: tuple[tuple[float, float], ...],
) -> tuple[tuple[float, ...], ...]:
    return tuple(
        (
            anchor[0],
            anchor[1],
            anchor[2],
            anchor[3],
            state[0],
            state[1],
        )
        for state in states
    )


SHARED_STATES = (
    (0.0, 0.0),
    (0.5, 0.1),
    (1.0, 0.5),
    (1.5, 1.2),
)

DISTRACTOR_STATES = (
    (0.0, 0.0),
    (0.1, 0.5),
    (0.2, 1.0),
    (0.4, 1.5),
)


def fixture_lines() -> tuple[Line, ...]:
    return (
        Line(
            "line_trading",
            tuple(f"trade_{index}" for index in range(4)),
            _line_vectors((10.0, 0.0, 0.0, 0.0), SHARED_STATES),
            frozenset({"trading", "execution", "timing"}),
        ),
        Line(
            "line_engineering",
            tuple(f"eng_{index}" for index in range(4)),
            _line_vectors((0.0, 10.0, 0.0, 0.0), SHARED_STATES),
            frozenset({"engineering", "architecture", "boundary"}),
        ),
        Line(
            "line_writing",
            tuple(f"write_{index}" for index in range(4)),
            _line_vectors((0.0, 0.0, 10.0, 0.0), SHARED_STATES),
            frozenset({"writing", "argument", "causal_density"}),
        ),
        Line(
            "line_distractor",
            tuple(f"other_{index}" for index in range(4)),
            _line_vectors((0.0, 0.0, 0.0, 10.0), DISTRACTOR_STATES),
            frozenset({"other_domain", "routine", "preference"}),
        ),
    )


def build_projection_graph(lines: tuple[Line, ...]) -> ProjectionGraph:
    graph = ProjectionGraph()

    line_text = {
        "line_trading": "Compiled trading trajectory.",
        "line_engineering": "Compiled engineering trajectory.",
        "line_writing": "Compiled writing trajectory.",
        "line_distractor": "Unrelated compiled trajectory.",
    }

    for line in lines:
        for index, raw_id in enumerate(line.raw_ids):
            graph.add_raw(
                RawEvidence(
                    raw_id,
                    line.domain_features
                    | frozenset({f"stage_{index}", f"source:{line.line_id}"}),
                    f"{line.line_id} raw stage {index}",
                )
            )

        graph.add_projection(
            Projection(
                line.line_id,
                line.domain_features | shape_tokens(line),
                line.raw_ids,
                line_text[line.line_id],
            )
        )
    return graph


def add_surface_projection(
    graph: ProjectionGraph,
    candidate: SurfaceCandidate,
    lines_by_id: dict[str, Line],
    *,
    projection_id: str = "surface_shared_trajectory",
) -> None:
    member_tokens = [
        shape_tokens(lines_by_id[line_id])
        for line_id in candidate.line_ids
    ]
    shared = frozenset.intersection(*member_tokens)
    graph.add_projection(
        Projection(
            projection_id,
            shared,
            candidate.line_ids,
            "Derived surface over a shared trajectory shape.",
        )
    )


def callable_routing_scenario() -> dict[str, object]:
    lines = fixture_lines()
    by_id = {line.line_id: line for line in lines}
    surfaces = discover_surfaces(lines)
    if len(surfaces) != 1:
        raise AssertionError(f"expected one surface, got {surfaces!r}")

    surface = surfaces[0]
    graph = build_projection_graph(lines)
    add_surface_projection(graph, surface, by_id)

    candidates = tuple(line.line_id for line in lines) + ("surface_shared_trajectory",)

    local_queries = {
        "trading": frozenset({"trading", "execution", "timing"}),
        "engineering": frozenset({"engineering", "architecture", "boundary"}),
        "writing": frozenset({"writing", "argument", "causal_density"}),
    }

    local_results: dict[str, object] = {}
    for name, query in local_queries.items():
        ranked = rank_callable_projections(graph, query, candidate_ids=candidates)
        local_results[name] = {
            "top": ranked[0][0],
            "surface_rank": next(
                index
                for index, (projection_id, _score) in enumerate(ranked, start=1)
                if projection_id == "surface_shared_trajectory"
            ),
            "surface_score": next(
                score
                for projection_id, score in ranked
                if projection_id == "surface_shared_trajectory"
            ),
            "ranking": [
                {"projection_id": projection_id, "score": score}
                for projection_id, score in ranked
            ],
        }

    cross_domain_query = graph.projections["surface_shared_trajectory"].features
    reflective_ranked = rank_callable_projections(
        graph,
        cross_domain_query,
        candidate_ids=candidates,
    )

    return {
        "surface": {
            "line_ids": list(surface.line_ids),
            "min_pairwise_shape_similarity": surface.min_pairwise_shape_similarity,
            "mean_pairwise_shape_similarity": surface.mean_pairwise_shape_similarity,
            "raw_closure": sorted(graph.raw_closure("surface_shared_trajectory")),
            "feature_count": len(graph.projections["surface_shared_trajectory"].features),
        },
        "local_queries": local_results,
        "reflective_query": {
            "features": sorted(cross_domain_query),
            "top": reflective_ranked[0][0],
            "ranking": [
                {"projection_id": projection_id, "score": score}
                for projection_id, score in reflective_ranked
            ],
        },
    }


def geometry_scenario() -> dict[str, object]:
    lines = fixture_lines()
    primary = lines[:3]
    distractor = lines[3]

    raw_pairs = {}
    shape_pairs = {}
    for left, right in itertools.combinations(primary, 2):
        key = f"{left.line_id}__{right.line_id}"
        raw_pairs[key] = raw_cross_line_similarity(left, right)
        shape_pairs[key] = shape_similarity(left, right)

    distractor_shape = {
        line.line_id: shape_similarity(line, distractor)
        for line in primary
    }

    surfaces = discover_surfaces(lines)

    return {
        "raw_cross_line_similarity": raw_pairs,
        "shape_similarity": shape_pairs,
        "distractor_shape_similarity": distractor_shape,
        "surfaces": [
            {
                "line_ids": list(surface.line_ids),
                "min_pairwise_shape_similarity": surface.min_pairwise_shape_similarity,
            }
            for surface in surfaces
        ],
    }


def rollback_scenario() -> dict[str, object]:
    lines = fixture_lines()
    aligned = lines[:3]
    initial_surfaces = discover_surfaces(aligned)

    corrected_trading = Line(
        "line_trading",
        aligned[0].raw_ids,
        _line_vectors((10.0, 0.0, 0.0, 0.0), DISTRACTOR_STATES),
        aligned[0].domain_features,
    )
    corrected = (corrected_trading, aligned[1], aligned[2])
    after_correction = discover_surfaces(corrected)

    graph = build_projection_graph(lines)
    by_id = {line.line_id: line for line in lines}
    add_surface_projection(graph, initial_surfaces[0], by_id)

    historical_raw_closure = graph.raw_closure("surface_shared_trajectory")

    for raw_id in aligned[0].raw_ids:
        graph.invalidate_raw(raw_id)

    current_valid_closure = graph.valid_raw_closure("surface_shared_trajectory")

    current_status = (
        SUPPORTED
        if after_correction
        else UNKNOWN
    )

    return {
        "initial_surface_count": len(initial_surfaces),
        "after_corrected_line_surface_count": len(after_correction),
        "current_status": current_status,
        "historical_raw_closure_count": len(historical_raw_closure),
        "current_valid_raw_closure_count": len(current_valid_closure),
        "invalidated_line_raw_ids": list(aligned[0].raw_ids),
    }


def report() -> dict[str, object]:
    return {
        "experiment": "lce-line-to-surface-projection",
        "geometry": geometry_scenario(),
        "callable_routing": callable_routing_scenario(),
        "rollback": rollback_scenario(),
        "non_claims": [
            "trajectory-shape operator is synthetic",
            "shape tokens are fixture scaffolding, not semantic ontology",
            "no production threshold or abstraction taxonomy is proposed",
            "real SemanticBlock embeddings are not tested here",
        ],
    }


def main() -> None:
    print(json.dumps(report(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
