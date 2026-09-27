"""Mutual-neighbour trajectory supplier and production Line runtime.

This is the production counterpart of the A4-R experiments. It deliberately
keeps the replaceable operator narrow:

- local mutual-neighbour evidence proposes structure;
- strict logical ordering orients only unambiguous edges;
- paths may overlap and share points;
- there is no global pairwise-cohesion gate;
- there are no hard time-span or time-bucket admission gates;
- persistent identity decisions are delegated to LineAssembler.

The supplier is derived cognition only. It never writes Raw Evidence.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from datetime import datetime

from lce.cognition.line_graph import (
    LineApplyResult,
    LineAssembler,
    LineAssemblerConfig,
    LineGraphStore,
)
from lce.reference_memory.contracts import (
    ReferenceMemorySubstratePort,
    SemanticBlock,
)


def _cosine(
    left: tuple[float, ...],
    right: tuple[float, ...],
) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


@dataclass(frozen=True, slots=True)
class TrajectoryConfig:
    """Replaceable local-geometry policy.

    Defaults are intentionally conservative and are not research claims. Real
    deployments should calibrate them against their embedding model and held-out
    data without changing the structural contracts.
    """

    k: int = 4
    min_similarity: float = 0.55
    min_support: int = 3
    max_paths: int = 256
    max_path_length: int = 64
    algorithm_version: str = "trajectory-mutual-knn-v1"

    def __post_init__(self) -> None:
        if self.k < 1:
            raise ValueError("k must be positive")
        if not 0.0 <= self.min_similarity <= 1.0:
            raise ValueError("min_similarity must be within [0, 1]")
        if self.min_support < 2:
            raise ValueError("min_support must be >= 2")
        if self.max_paths < 1 or self.max_path_length < self.min_support:
            raise ValueError("path limits are inconsistent")
        if not self.algorithm_version.strip():
            raise ValueError("algorithm_version must be nonempty")


@dataclass(frozen=True, slots=True)
class TrajectoryPath:
    path_id: str
    block_ids: tuple[str, ...]
    state_ids: tuple[str, ...]
    edge_similarities: tuple[float, ...]

    @property
    def mean_local_similarity(self) -> float:
        if not self.edge_similarities:
            return 0.0
        return sum(self.edge_similarities) / len(self.edge_similarities)

    @property
    def min_local_similarity(self) -> float:
        return min(self.edge_similarities, default=0.0)


@dataclass(frozen=True, slots=True)
class TrajectoryRuntimeResult:
    knowledge_cutoff_iso: str
    candidate_paths: tuple[TrajectoryPath, ...]
    line_updates: tuple[LineApplyResult, ...]


class MutualKnnTrajectorySupplier:
    """Propose overlapping trajectory paths from local reciprocal neighbours."""

    def __init__(
        self,
        *,
        memory: ReferenceMemorySubstratePort,
        config: TrajectoryConfig | None = None,
    ) -> None:
        self.memory = memory
        self.config = config or TrajectoryConfig()

    @staticmethod
    def _precedes(left: SemanticBlock, right: SemanticBlock) -> bool:
        # A partial order: overlapping or same-time points are not forced into
        # a sequence merely to make the graph easier to traverse.
        return (
            left.occurred_start < right.occurred_start
            and left.occurred_end <= right.occurred_start
        )

    def _vectors(
        self,
        blocks: tuple[SemanticBlock, ...],
    ) -> dict[str, tuple[float, ...]]:
        vectors: dict[str, tuple[float, ...]] = {}
        for block in blocks:
            if block.state_id is None:
                continue
            try:
                vectors[block.block_id] = self.memory.get_vector(
                    block.block_id,
                    state_id=block.state_id,
                ).values
            except KeyError:
                continue
        return vectors

    def _mutual_edges(
        self,
        blocks: tuple[SemanticBlock, ...],
        vectors: dict[str, tuple[float, ...]],
    ) -> dict[tuple[str, str], float]:
        neighbours: dict[str, tuple[str, ...]] = {}
        scores: dict[tuple[str, str], float] = {}

        for block in blocks:
            left = vectors.get(block.block_id)
            if left is None:
                continue
            ranked: list[tuple[float, str]] = []
            for other in blocks:
                if other.block_id == block.block_id:
                    continue
                right = vectors.get(other.block_id)
                if right is None:
                    continue
                similarity = _cosine(left, right)
                if similarity < self.config.min_similarity:
                    continue
                ranked.append((similarity, other.block_id))
                scores[(block.block_id, other.block_id)] = similarity
            ranked.sort(key=lambda item: (-item[0], item[1]))
            neighbours[block.block_id] = tuple(
                block_id for _score, block_id in ranked[: self.config.k]
            )

        mutual: dict[tuple[str, str], float] = {}
        for left_id, right_ids in neighbours.items():
            for right_id in right_ids:
                if left_id not in neighbours.get(right_id, ()):
                    continue
                pair = tuple(sorted((left_id, right_id)))
                mutual[pair] = min(
                    scores[(left_id, right_id)],
                    scores[(right_id, left_id)],
                )
        return mutual

    def _directed_graph(
        self,
        blocks: tuple[SemanticBlock, ...],
        mutual: dict[tuple[str, str], float],
    ) -> tuple[
        dict[str, tuple[str, ...]],
        dict[tuple[str, str], float],
    ]:
        by_id = {block.block_id: block for block in blocks}
        outgoing: dict[str, list[str]] = {
            block.block_id: [] for block in blocks
        }
        edge_scores: dict[tuple[str, str], float] = {}

        for (left_id, right_id), score in mutual.items():
            left = by_id[left_id]
            right = by_id[right_id]
            parent_id: str | None = None
            child_id: str | None = None
            if self._precedes(left, right):
                parent_id, child_id = left_id, right_id
            elif self._precedes(right, left):
                parent_id, child_id = right_id, left_id
            if parent_id is None or child_id is None:
                continue
            outgoing[parent_id].append(child_id)
            edge_scores[(parent_id, child_id)] = score

        return (
            {
                block_id: tuple(
                    sorted(
                        dict.fromkeys(children),
                        key=lambda child_id: (
                            by_id[child_id].occurred_start,
                            child_id,
                        ),
                    )
                )
                for block_id, children in outgoing.items()
            },
            edge_scores,
        )

    def _paths(
        self,
        blocks: tuple[SemanticBlock, ...],
        outgoing: dict[str, tuple[str, ...]],
        edge_scores: dict[tuple[str, str], float],
    ) -> tuple[TrajectoryPath, ...]:
        by_id = {block.block_id: block for block in blocks}
        indegree = {block.block_id: 0 for block in blocks}
        for children in outgoing.values():
            for child_id in children:
                indegree[child_id] += 1

        starts = tuple(
            sorted(
                (
                    block_id
                    for block_id, degree in indegree.items()
                    if degree == 0 and outgoing.get(block_id)
                ),
                key=lambda block_id: (
                    by_id[block_id].occurred_start,
                    block_id,
                ),
            )
        )

        raw_paths: list[tuple[str, ...]] = []

        def walk(path: tuple[str, ...]) -> None:
            if len(raw_paths) >= self.config.max_paths:
                return
            if len(path) >= self.config.max_path_length:
                raw_paths.append(path)
                return
            children = outgoing.get(path[-1], ())
            if not children:
                raw_paths.append(path)
                return
            extended = False
            for child_id in children:
                if child_id in path:
                    continue
                extended = True
                walk((*path, child_id))
                if len(raw_paths) >= self.config.max_paths:
                    return
            if not extended:
                raw_paths.append(path)

        for start in starts:
            walk((start,))
            if len(raw_paths) >= self.config.max_paths:
                break

        # A directed subgraph may have no indegree-zero node after filtering
        # only if input is malformed. Strict logical ordering should keep it
        # acyclic; still, fall back to each node to avoid silently losing data.
        if not raw_paths:
            for block_id in sorted(outgoing):
                if outgoing[block_id]:
                    walk((block_id,))
                    if len(raw_paths) >= self.config.max_paths:
                        break

        eligible = [
            path for path in raw_paths if len(path) >= self.config.min_support
        ]

        # Drop strict prefix/subpath duplicates while preserving divergent
        # branches. Set containment alone is intentionally not used because
        # longitudinal order is part of the candidate identity.
        maximal: list[tuple[str, ...]] = []
        for path in sorted(
            set(eligible),
            key=lambda value: (-len(value), value),
        ):
            if any(
                len(path) < len(other)
                and all(
                    item in other for item in path
                )
                for other in maximal
            ):
                continue
            maximal.append(path)

        output: list[TrajectoryPath] = []
        for path in sorted(maximal):
            state_ids: list[str] = []
            similarities: list[float] = []
            valid = True
            for block_id in path:
                state_id = by_id[block_id].state_id
                if state_id is None:
                    valid = False
                    break
                state_ids.append(state_id)
            if not valid:
                continue
            for parent_id, child_id in zip(path, path[1:], strict=True):
                similarities.append(edge_scores[(parent_id, child_id)])
            digest = hashlib.sha256(
                "|".join(state_ids).encode()
            ).hexdigest()[:24]
            output.append(
                TrajectoryPath(
                    path_id=f"traj_{digest}",
                    block_ids=path,
                    state_ids=tuple(state_ids),
                    edge_similarities=tuple(similarities),
                )
            )
        return tuple(output)

    def propose(
        self,
        blocks: tuple[SemanticBlock, ...],
    ) -> tuple[TrajectoryPath, ...]:
        ordered = tuple(
            sorted(
                blocks,
                key=lambda block: (
                    block.occurred_start,
                    block.occurred_end,
                    block.block_id,
                ),
            )
        )
        if len(ordered) < self.config.min_support:
            return ()
        vectors = self._vectors(ordered)
        if len(vectors) < self.config.min_support:
            return ()
        mutual = self._mutual_edges(ordered, vectors)
        outgoing, edge_scores = self._directed_graph(ordered, mutual)
        return self._paths(ordered, outgoing, edge_scores)


class TrajectoryRuntime:
    """Observe current knowledge and increment stable Line DAGs conservatively."""

    def __init__(
        self,
        *,
        memory: ReferenceMemorySubstratePort,
        line_store: LineGraphStore,
        trajectory_config: TrajectoryConfig | None = None,
        assembler_config: LineAssemblerConfig | None = None,
    ) -> None:
        self.memory = memory
        self.supplier = MutualKnnTrajectorySupplier(
            memory=memory,
            config=trajectory_config,
        )
        self.assembler = LineAssembler(
            memory=memory,
            store=line_store,
            config=assembler_config,
        )

    def observe(
        self,
        *,
        knowledge_cutoff: datetime,
        current_block_ids: tuple[str, ...],
    ) -> TrajectoryRuntimeResult:
        blocks = self.memory.list_semantic_blocks_at_knowledge_cutoff(
            knowledge_cutoff,
            current_valid_only=True,
        )
        by_id = {block.block_id: block for block in blocks}
        paths = self.supplier.propose(blocks)
        current = set(current_block_ids)
        relevant = tuple(
            path
            for path in paths
            if current & set(path.block_ids)
        )

        # Prefer longer / stronger paths first. If they share a real trunk,
        # LineAssembler absorbs later paths into the same stable Line; weak
        # overlap does not clone a new Line.
        ordered = tuple(
            sorted(
                relevant,
                key=lambda path: (
                    -len(path.block_ids),
                    -path.mean_local_similarity,
                    path.path_id,
                ),
            )
        )
        updates: list[LineApplyResult] = []
        for path in ordered:
            path_blocks = tuple(
                by_id[block_id] for block_id in path.block_ids
            )
            updates.append(self.assembler.apply_path(path_blocks))

        return TrajectoryRuntimeResult(
            knowledge_cutoff_iso=knowledge_cutoff.isoformat(),
            candidate_paths=ordered,
            line_updates=tuple(updates),
        )
