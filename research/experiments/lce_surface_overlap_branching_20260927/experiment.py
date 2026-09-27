"""Pressure tests for Surface discovery over evolving Line/Worktree projections.

This experiment attacks three failure modes:
1. equivalent trajectories expressed with different numbers of states;
2. only one branch of a Worktree participating in a Surface;
3. one Line legitimately participating in multiple Surfaces through different
   reproducible relation views.

The unit of higher-order comparison is therefore a derived Line/branch view,
not an exclusive whole-Line assignment.
"""

from __future__ import annotations

import itertools
import json
import math
from dataclasses import dataclass

from research.experiments.lce_callable_projection_20260927.experiment import (
    Projection,
    ProjectionGraph,
    RawEvidence,
)


@dataclass(frozen=True, slots=True)
class RelationView:
    view_id: str
    owner_line_id: str
    raw_ids: tuple[str, ...]
    points: tuple[tuple[float, ...], ...]


@dataclass(frozen=True, slots=True)
class Surface:
    view_ids: tuple[str, ...]
    owner_line_ids: tuple[str, ...]
    min_shape_similarity: float


def _cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    ln = math.sqrt(sum(value * value for value in left))
    rn = math.sqrt(sum(value * value for value in right))
    if not ln or not rn:
        return 0.0
    return dot / (ln * rn)


def _distance(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))


def resample_polyline(
    points: tuple[tuple[float, ...], ...],
    *,
    samples: int = 17,
) -> tuple[tuple[float, ...], ...]:
    """Arc-length resampling makes representation robust to point count.

    It does not erase geometry; it only asks whether two polylines trace the
    same normalized path at different sampling densities.
    """

    if len(points) < 2:
        return points

    cumulative = [0.0]
    for left, right in zip(points, points[1:]):
        cumulative.append(cumulative[-1] + _distance(left, right))
    total = cumulative[-1]
    if total == 0.0:
        return tuple(points[0] for _ in range(samples))

    targets = [total * index / (samples - 1) for index in range(samples)]
    output: list[tuple[float, ...]] = []
    segment = 0

    for target in targets:
        while (
            segment < len(points) - 2
            and cumulative[segment + 1] < target - 1e-12
        ):
            segment += 1
        left = points[segment]
        right = points[segment + 1]
        start = cumulative[segment]
        end = cumulative[segment + 1]
        ratio = 0.0 if end == start else (target - start) / (end - start)
        output.append(
            tuple(
                left[index] + (right[index] - left[index]) * ratio
                for index in range(len(left))
            )
        )
    return tuple(output)


def shape_signature(view: RelationView, *, samples: int = 17) -> tuple[float, ...]:
    resampled = resample_polyline(view.points, samples=samples)
    origin = resampled[0]
    flattened: list[float] = []
    for point in resampled:
        flattened.extend(
            point[index] - origin[index]
            for index in range(len(point))
        )

    norm = math.sqrt(sum(value * value for value in flattened))
    if norm == 0.0:
        return tuple(0.0 for _ in flattened)
    return tuple(value / norm for value in flattened)


def shape_similarity(left: RelationView, right: RelationView) -> float:
    return _cosine(shape_signature(left), shape_signature(right))


def discover_surfaces(
    views: tuple[RelationView, ...],
    *,
    min_views: int = 3,
    min_similarity: float = 0.98,
) -> tuple[Surface, ...]:
    """Find maximal overlapping Surface candidates.

    A single Surface cannot count two views from the same owner Line as two
    independent directions. Across Surfaces, however, the same owner Line may
    participate repeatedly through different derived views.
    """

    valid: list[tuple[str, ...]] = []
    by_id = {view.view_id: view for view in views}

    for size in range(min_views, len(views) + 1):
        for combo in itertools.combinations(views, size):
            owners = [view.owner_line_id for view in combo]
            if len(set(owners)) != len(owners):
                continue
            similarities = [
                shape_similarity(left, right)
                for left, right in itertools.combinations(combo, 2)
            ]
            if similarities and min(similarities) >= min_similarity:
                valid.append(tuple(sorted(view.view_id for view in combo)))

    maximal = [
        group
        for group in valid
        if not any(set(group) < set(other) for other in valid)
    ]

    output: list[Surface] = []
    for group in sorted(set(maximal)):
        member_views = [by_id[view_id] for view_id in group]
        similarities = [
            shape_similarity(left, right)
            for left, right in itertools.combinations(member_views, 2)
        ]
        output.append(
            Surface(
                view_ids=group,
                owner_line_ids=tuple(
                    sorted(view.owner_line_id for view in member_views)
                ),
                min_shape_similarity=min(similarities),
            )
        )
    return tuple(output)


def densify(
    vertices: tuple[tuple[float, float], ...],
    *,
    subdivisions: int,
) -> tuple[tuple[float, float], ...]:
    output: list[tuple[float, float]] = []
    for segment_index, (left, right) in enumerate(zip(vertices, vertices[1:])):
        if segment_index == 0:
            output.append(left)
        for step in range(1, subdivisions + 1):
            ratio = step / subdivisions
            output.append(
                (
                    left[0] + (right[0] - left[0]) * ratio,
                    left[1] + (right[1] - left[1]) * ratio,
                )
            )
    return tuple(output)


SHAPE_U = (
    (0.0, 0.0),
    (1.0, 0.2),
    (2.0, 1.0),
    (3.0, 2.4),
)

SHAPE_F = (
    (0.0, 0.0),
    (0.2, 1.0),
    (1.0, 2.0),
    (2.5, 2.4),
)

SHAPE_BRANCH_BAD = (
    (0.0, 0.0),
    (1.0, 0.2),
    (1.2, 1.8),
    (0.3, 3.0),
)


def different_length_fixture() -> tuple[RelationView, ...]:
    return (
        RelationView(
            "u_short",
            "line_short",
            tuple(f"short_{index}" for index in range(4)),
            densify(SHAPE_U, subdivisions=1),
        ),
        RelationView(
            "u_medium",
            "line_medium",
            tuple(f"medium_{index}" for index in range(7)),
            densify(SHAPE_U, subdivisions=2),
        ),
        RelationView(
            "u_long",
            "line_long",
            tuple(f"long_{index}" for index in range(13)),
            densify(SHAPE_U, subdivisions=4),
        ),
    )


def different_length_scenario() -> dict[str, object]:
    views = different_length_fixture()
    pairwise = {
        f"{left.view_id}__{right.view_id}": shape_similarity(left, right)
        for left, right in itertools.combinations(views, 2)
    }
    surfaces = discover_surfaces(views)
    return {
        "point_counts": {
            view.view_id: len(view.points)
            for view in views
        },
        "pairwise_shape_similarity": pairwise,
        "surfaces": [
            {
                "view_ids": list(surface.view_ids),
                "owner_line_ids": list(surface.owner_line_ids),
                "min_shape_similarity": surface.min_shape_similarity,
            }
            for surface in surfaces
        ],
    }


def branching_fixture() -> tuple[RelationView, ...]:
    trunk_raw = ("strategy_t0", "strategy_t1")
    good_raw = trunk_raw + ("strategy_a2", "strategy_a3")
    bad_raw = trunk_raw + ("strategy_b2", "strategy_b3")

    return (
        RelationView(
            "strategy_branch_a",
            "worktree_strategy",
            good_raw,
            SHAPE_U,
        ),
        RelationView(
            "strategy_branch_b",
            "worktree_strategy",
            bad_raw,
            SHAPE_BRANCH_BAD,
        ),
        RelationView(
            "engineering_u",
            "line_engineering",
            tuple(f"eng_{index}" for index in range(7)),
            densify(SHAPE_U, subdivisions=2),
        ),
        RelationView(
            "writing_u",
            "line_writing",
            tuple(f"write_{index}" for index in range(13)),
            densify(SHAPE_U, subdivisions=4),
        ),
    )


def build_branch_projection_graph() -> ProjectionGraph:
    graph = ProjectionGraph()

    raw_ids = {
        "strategy_t0",
        "strategy_t1",
        "strategy_a2",
        "strategy_a3",
        "strategy_b2",
        "strategy_b3",
        *(f"eng_{index}" for index in range(7)),
        *(f"write_{index}" for index in range(13)),
    }
    for raw_id in sorted(raw_ids):
        graph.add_raw(
            RawEvidence(
                raw_id,
                frozenset({raw_id.split("_")[0], "raw"}),
                raw_id,
            )
        )

    graph.add_projection(
        Projection(
            "strategy_branch_a",
            frozenset({"derived", "branch_a"}),
            ("strategy_t0", "strategy_t1", "strategy_a2", "strategy_a3"),
            "Strategy Worktree branch A",
        )
    )
    graph.add_projection(
        Projection(
            "strategy_branch_b",
            frozenset({"derived", "branch_b"}),
            ("strategy_t0", "strategy_t1", "strategy_b2", "strategy_b3"),
            "Strategy Worktree branch B",
        )
    )
    graph.add_projection(
        Projection(
            "engineering_u",
            frozenset({"derived", "engineering"}),
            tuple(f"eng_{index}" for index in range(7)),
            "Engineering line",
        )
    )
    graph.add_projection(
        Projection(
            "writing_u",
            frozenset({"derived", "writing"}),
            tuple(f"write_{index}" for index in range(13)),
            "Writing line",
        )
    )
    return graph


def branching_scenario() -> dict[str, object]:
    views = branching_fixture()
    surfaces = discover_surfaces(views)
    graph = build_branch_projection_graph()

    if len(surfaces) != 1:
        raise AssertionError(f"expected one branch-local surface, got {surfaces!r}")
    surface = surfaces[0]
    graph.add_projection(
        Projection(
            "surface_branch_a",
            frozenset({"derived", "surface"}),
            surface.view_ids,
            "Surface using only the matching Worktree branch.",
        )
    )

    closure = graph.raw_closure("surface_branch_a")
    return {
        "branch_a_similarity": {
            view.view_id: shape_similarity(views[0], view)
            for view in views[2:]
        },
        "branch_b_similarity": {
            view.view_id: shape_similarity(views[1], view)
            for view in views[2:]
        },
        "surface": {
            "view_ids": list(surface.view_ids),
            "owner_line_ids": list(surface.owner_line_ids),
            "raw_closure": sorted(closure),
        },
        "sibling_branch_raw_in_surface": sorted(
            {"strategy_b2", "strategy_b3"} & set(closure)
        ),
        "shared_trunk_raw_in_surface": sorted(
            {"strategy_t0", "strategy_t1"} & set(closure)
        ),
    }


def overlap_fixture() -> tuple[RelationView, ...]:
    # One underlying trading Line exposes two reproducible relational views.
    # The two views share the same Raw support identity but participate in
    # different higher-order structures.
    trade_raw = tuple(f"trade_{index}" for index in range(13))
    return (
        RelationView(
            "trade_view_u",
            "line_trading",
            trade_raw,
            densify(SHAPE_U, subdivisions=4),
        ),
        RelationView(
            "trade_view_f",
            "line_trading",
            trade_raw,
            densify(SHAPE_F, subdivisions=4),
        ),
        RelationView(
            "engineering_view_u",
            "line_engineering",
            tuple(f"eng_u_{index}" for index in range(7)),
            densify(SHAPE_U, subdivisions=2),
        ),
        RelationView(
            "writing_view_u",
            "line_writing",
            tuple(f"write_u_{index}" for index in range(4)),
            densify(SHAPE_U, subdivisions=1),
        ),
        RelationView(
            "product_view_f",
            "line_product",
            tuple(f"product_f_{index}" for index in range(7)),
            densify(SHAPE_F, subdivisions=2),
        ),
        RelationView(
            "learning_view_f",
            "line_learning",
            tuple(f"learn_f_{index}" for index in range(4)),
            densify(SHAPE_F, subdivisions=1),
        ),
    )


def build_overlap_projection_graph(views: tuple[RelationView, ...]) -> ProjectionGraph:
    graph = ProjectionGraph()

    raw_by_owner: dict[str, set[str]] = {}
    for view in views:
        raw_by_owner.setdefault(view.owner_line_id, set()).update(view.raw_ids)

    for owner_line_id, raw_ids in sorted(raw_by_owner.items()):
        for raw_id in sorted(raw_ids):
            if raw_id not in graph.raw:
                graph.add_raw(
                    RawEvidence(
                        raw_id,
                        frozenset({"raw", owner_line_id}),
                        raw_id,
                    )
                )
        graph.add_projection(
            Projection(
                owner_line_id,
                frozenset({"line", owner_line_id}),
                tuple(sorted(raw_ids)),
                f"Compiled owner line {owner_line_id}",
            )
        )

    for view in views:
        graph.add_projection(
            Projection(
                view.view_id,
                frozenset({"relation_view", view.view_id}),
                (view.owner_line_id,),
                f"Reproducible relational view {view.view_id}",
            )
        )
    return graph


def overlap_scenario() -> dict[str, object]:
    views = overlap_fixture()
    surfaces = discover_surfaces(views)
    graph = build_overlap_projection_graph(views)

    if len(surfaces) != 2:
        raise AssertionError(f"expected two overlapping surfaces, got {surfaces!r}")

    for index, surface in enumerate(surfaces):
        graph.add_projection(
            Projection(
                f"surface_{index}",
                frozenset({"derived_surface", str(index)}),
                surface.view_ids,
                f"Surface {index}",
            )
        )

    trading_memberships = [
        {
            "surface_index": index,
            "view_ids": list(surface.view_ids),
            "owner_line_ids": list(surface.owner_line_ids),
        }
        for index, surface in enumerate(surfaces)
        if "line_trading" in surface.owner_line_ids
    ]

    closures = {
        f"surface_{index}": sorted(graph.raw_closure(f"surface_{index}"))
        for index in range(len(surfaces))
    }
    closure_intersection = set(closures["surface_0"]) & set(closures["surface_1"])

    return {
        "surfaces": [
            {
                "view_ids": list(surface.view_ids),
                "owner_line_ids": list(surface.owner_line_ids),
                "min_shape_similarity": surface.min_shape_similarity,
            }
            for surface in surfaces
        ],
        "trading_surface_membership_count": len(trading_memberships),
        "trading_memberships": trading_memberships,
        "surface_raw_closures": closures,
        "shared_raw_closure": sorted(closure_intersection),
        "expected_trading_raw": [f"trade_{index}" for index in range(13)],
        "cross_pattern_similarity": shape_similarity(views[0], views[1]),
    }


def report() -> dict[str, object]:
    return {
        "experiment": "lce-surface-overlap-branching",
        "different_length": different_length_scenario(),
        "branching_worktree": branching_scenario(),
        "overlapping_surfaces": overlap_scenario(),
        "non_claims": [
            "arc-length resampling is an experimental operator, not production policy",
            "relation views are derived projections, not fixed abstraction levels",
            "synthetic shapes do not establish real embedding performance",
        ],
    }


def main() -> None:
    print(json.dumps(report(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
