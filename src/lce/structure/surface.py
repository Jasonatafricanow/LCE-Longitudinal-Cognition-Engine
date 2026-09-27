"""Optional higher-order Surface discovery over real Line branch paths.

Surface discovery is deliberately opt-in. The structural contract is stable,
but the line-relation scoring operator is still replaceable and requires
real-embedding calibration.

No Surface output is Raw Evidence or an independent support source.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from datetime import datetime
from lce.cognition.line_graph import LineGraphStore, LineGraphView
from lce.reference_memory.contracts import ReferenceMemorySubstratePort


def _cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    ln = math.sqrt(sum(value * value for value in left))
    rn = math.sqrt(sum(value * value for value in right))
    if ln == 0.0 or rn == 0.0:
        return 0.0
    return dot / (ln * rn)


def _distance(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right):
        raise ValueError("vector dimensions differ")
    return math.sqrt(
        sum((a - b) ** 2 for a, b in zip(left, right, strict=True))
    )


def _resample(
    points: tuple[tuple[float, ...], ...],
    *,
    samples: int,
) -> tuple[tuple[float, ...], ...]:
    if len(points) < 2:
        return points
    dimension = len(points[0])
    if not dimension or any(len(point) != dimension for point in points):
        raise ValueError("path vectors must have one nonzero dimension")

    cumulative = [0.0]
    for index in range(len(points) - 1):
        cumulative.append(
            cumulative[-1] + _distance(points[index], points[index + 1])
        )
    total = cumulative[-1]
    if total == 0.0:
        return tuple(points[0] for _ in range(samples))

    output: list[tuple[float, ...]] = []
    segment = 0
    for sample_index in range(samples):
        target = total * sample_index / (samples - 1)
        while (
            segment < len(points) - 2
            and cumulative[segment + 1] < target
        ):
            segment += 1
        start = cumulative[segment]
        end = cumulative[segment + 1]
        ratio = 0.0 if end == start else (target - start) / (end - start)
        output.append(
            tuple(
                points[segment][axis]
                + (points[segment + 1][axis] - points[segment][axis])
                * ratio
                for axis in range(dimension)
            )
        )
    return tuple(output)


def _shape_signature(
    points: tuple[tuple[float, ...], ...],
    *,
    samples: int,
) -> tuple[float, ...]:
    resampled = _resample(points, samples=samples)
    if not resampled:
        return ()
    origin = resampled[0]
    flattened = tuple(
        coordinate - origin[axis]
        for point in resampled
        for axis, coordinate in enumerate(point)
    )
    norm = math.sqrt(sum(value * value for value in flattened))
    if norm == 0.0:
        return tuple(0.0 for _ in flattened)
    return tuple(value / norm for value in flattened)


@dataclass(frozen=True, slots=True)
class SurfaceConfig:
    min_lines: int = 3
    min_path_nodes: int = 3
    min_shape_similarity: float = 0.95
    resample_points: int = 17
    max_paths_per_line: int = 32
    max_path_nodes: int = 64
    max_candidates: int = 64

    def __post_init__(self) -> None:
        if self.min_lines < 2 or self.min_path_nodes < 2:
            raise ValueError("Surface support minima must be >= 2")
        if not 0.0 <= self.min_shape_similarity <= 1.0:
            raise ValueError("min_shape_similarity must be within [0, 1]")
        if self.resample_points < 2:
            raise ValueError("resample_points must be >= 2")
        if (
            self.max_paths_per_line < 1
            or self.max_path_nodes < self.min_path_nodes
            or self.max_candidates < 1
        ):
            raise ValueError("Surface bounds are inconsistent")


@dataclass(frozen=True, slots=True)
class LinePathView:
    view_id: str
    line_id: str
    node_ids: tuple[str, ...]
    state_ids: tuple[str, ...]
    raw_evidence_ids: tuple[str, ...]
    shape_signature: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class SurfaceCandidate:
    surface_id: str
    views: tuple[LinePathView, ...]
    min_pairwise_similarity: float
    mean_pairwise_similarity: float
    raw_evidence_ids: tuple[str, ...]


class SurfaceRuntime:
    """Discover overlapping higher-order relations without Line cloning."""

    def __init__(
        self,
        *,
        memory: ReferenceMemorySubstratePort,
        line_store: LineGraphStore,
        config: SurfaceConfig,
    ) -> None:
        self.memory = memory
        self.store = line_store
        self.view = LineGraphView(memory=memory, store=line_store)
        self.config = config

    def _line_path_views(
        self,
        *,
        knowledge_cutoff: datetime,
    ) -> tuple[LinePathView, ...]:
        output: list[LinePathView] = []
        for line in self.store.list_lines():
            paths = self.view.paths_to_frontier(
                line.line_id,
                knowledge_cutoff=knowledge_cutoff,
                max_paths=self.config.max_paths_per_line,
                max_nodes=self.config.max_path_nodes,
            )
            for node_ids in paths:
                if len(node_ids) < self.config.min_path_nodes:
                    continue
                states = []
                vectors = []
                raw_ids: set[str] = set()
                valid = True
                for node_id in node_ids:
                    node = self.store.get_node(node_id)
                    block = self.view.state_for_node_at_cutoff(
                        node_id,
                        knowledge_cutoff=knowledge_cutoff,
                    )
                    if block is None or block.state_id is None:
                        valid = False
                        break
                    try:
                        vector = self.memory.get_vector(
                            node.block_id,
                            state_id=block.state_id,
                        ).values
                    except KeyError:
                        valid = False
                        break
                    states.append(block.state_id)
                    vectors.append(vector)
                    raw_ids.update(block.raw_evidence_ids)
                if not valid:
                    continue
                signature = _shape_signature(
                    tuple(vectors),
                    samples=self.config.resample_points,
                )
                if not signature or not any(signature):
                    continue
                digest = hashlib.sha256(
                    (
                        line.line_id
                        + "|"
                        + "|".join(node_ids)
                        + "|"
                        + "|".join(states)
                    ).encode()
                ).hexdigest()[:24]
                output.append(
                    LinePathView(
                        view_id=f"lineview_{digest}",
                        line_id=line.line_id,
                        node_ids=node_ids,
                        state_ids=tuple(states),
                        raw_evidence_ids=tuple(sorted(raw_ids)),
                        shape_signature=signature,
                    )
                )
        return tuple(sorted(output, key=lambda item: item.view_id))

    def discover(
        self,
        *,
        knowledge_cutoff: datetime,
    ) -> tuple[SurfaceCandidate, ...]:
        views = self._line_path_views(knowledge_cutoff=knowledge_cutoff)
        if len({view.line_id for view in views}) < self.config.min_lines:
            return ()

        by_id = {view.view_id: view for view in views}
        adjacency: dict[str, set[str]] = {
            view.view_id: set() for view in views
        }
        similarity: dict[tuple[str, str], float] = {}
        for left_index, left in enumerate(views):
            for right in views[left_index + 1 :]:
                if left.line_id == right.line_id:
                    continue
                score = _cosine(
                    left.shape_signature,
                    right.shape_signature,
                )
                pair = (
                    (left.view_id, right.view_id)
                    if left.view_id <= right.view_id
                    else (right.view_id, left.view_id)
                )
                similarity[pair] = score
                if score >= self.config.min_shape_similarity:
                    adjacency[left.view_id].add(right.view_id)
                    adjacency[right.view_id].add(left.view_id)

        maximal: list[tuple[str, ...]] = []

        def expand(
            clique: tuple[str, ...],
            candidates: tuple[str, ...],
        ) -> None:
            if len(maximal) >= self.config.max_candidates:
                return
            owners = {by_id[view_id].line_id for view_id in clique}
            viable = tuple(
                view_id
                for view_id in candidates
                if by_id[view_id].line_id not in owners
                and all(
                    view_id in adjacency[member_id]
                    for member_id in clique
                )
            )
            if not viable:
                if len(clique) >= self.config.min_lines:
                    maximal.append(clique)
                return
            for index, view_id in enumerate(viable):
                expand((*clique, view_id), viable[index + 1 :])
                if len(maximal) >= self.config.max_candidates:
                    return

        expand((), tuple(sorted(by_id)))

        output: list[SurfaceCandidate] = []
        seen_groups: set[tuple[str, ...]] = set()
        for group in maximal:
            normalized = tuple(sorted(group))
            if normalized in seen_groups:
                continue
            seen_groups.add(normalized)
            pair_scores = []
            for left_index, left_id in enumerate(normalized):
                for right_id in normalized[left_index + 1 :]:
                    pair = (
                        (left_id, right_id)
                        if left_id <= right_id
                        else (right_id, left_id)
                    )
                    pair_scores.append(similarity[pair])
            member_views = tuple(by_id[view_id] for view_id in normalized)
            raw_ids = {
                raw_id
                for view in member_views
                for raw_id in view.raw_evidence_ids
            }
            digest = hashlib.sha256(
                "|".join(normalized).encode()
            ).hexdigest()[:24]
            output.append(
                SurfaceCandidate(
                    surface_id=f"surface_{digest}",
                    views=member_views,
                    min_pairwise_similarity=min(pair_scores),
                    mean_pairwise_similarity=(
                        sum(pair_scores) / len(pair_scores)
                    ),
                    raw_evidence_ids=tuple(sorted(raw_ids)),
                )
            )
        return tuple(sorted(output, key=lambda item: item.surface_id))


__all__ = [
    "LinePathView",
    "SurfaceCandidate",
    "SurfaceConfig",
    "SurfaceRuntime",
]
