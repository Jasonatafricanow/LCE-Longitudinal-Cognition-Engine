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
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from itertools import pairwise
from typing import Protocol

from lce.cognition.convergence import (
    AuthorityConfig,
    AuthorityDecision,
    AuthorityLedger,
    AuthoritySignal,
)
from lce.cognition.line_graph import (
    LineApplyResult,
    LineAssembler,
    LineAssemblerConfig,
    LineGraphStore,
    LineGraphView,
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
    max_incremental_parents: int = 1
    line_ambiguity_margin: float = 0.03
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
        if self.max_incremental_parents < 1:
            raise ValueError("max_incremental_parents must be positive")
        if not 0.0 <= self.line_ambiguity_margin <= 1.0:
            raise ValueError("line_ambiguity_margin must be within [0, 1]")
        if not self.algorithm_version.strip():
            raise ValueError("algorithm_version must be nonempty")


class NeighbourCandidateProvider(Protocol):
    """Replaceable neighbour-candidate source for slow-path bootstrap."""

    def candidates(
        self,
        blocks: tuple[SemanticBlock, ...],
        vectors: dict[str, tuple[float, ...]],
        *,
        k: int,
        min_similarity: float,
    ) -> dict[str, tuple[tuple[float, str], ...]]:
        ...


class ExactCosineNeighbourProvider:
    """Zero-dependency reference implementation.

    This implementation is O(N²) and is intended as a correctness/reference
    backend for explicit bootstrap. Large deployments should inject an ANN or
    external-vector-index provider through the same contract.
    """

    derivation_fingerprint = "exact-cosine-v1"

    def candidates(
        self,
        blocks: tuple[SemanticBlock, ...],
        vectors: dict[str, tuple[float, ...]],
        *,
        k: int,
        min_similarity: float,
    ) -> dict[str, tuple[tuple[float, str], ...]]:
        output: dict[str, tuple[tuple[float, str], ...]] = {}
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
                if similarity >= min_similarity:
                    ranked.append((similarity, other.block_id))
            ranked.sort(key=lambda item: (-item[0], item[1]))
            output[block.block_id] = tuple(ranked[:k])
        return output


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
    authority_decisions: tuple[AuthorityDecision, ...] = ()


class MutualKnnTrajectorySupplier:
    """Propose overlapping trajectory paths from local reciprocal neighbours."""

    def __init__(
        self,
        *,
        memory: ReferenceMemorySubstratePort,
        config: TrajectoryConfig | None = None,
        neighbour_provider: NeighbourCandidateProvider | None = None,
    ) -> None:
        self.memory = memory
        self.config = config or TrajectoryConfig()
        self.neighbour_provider = (
            neighbour_provider or ExactCosineNeighbourProvider()
        )

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
        ranked = self.neighbour_provider.candidates(
            blocks,
            vectors,
            k=self.config.k,
            min_similarity=self.config.min_similarity,
        )
        neighbours = {
            block_id: tuple(
                neighbour_id
                for _score, neighbour_id in candidates
            )
            for block_id, candidates in ranked.items()
        }
        scores = {
            (block_id, neighbour_id): score
            for block_id, candidates in ranked.items()
            for score, neighbour_id in candidates
        }

        mutual: dict[tuple[str, str], float] = {}
        for left_id, right_ids in neighbours.items():
            for right_id in right_ids:
                if left_id not in neighbours.get(right_id, ()):
                    continue
                left_score = scores.get((left_id, right_id))
                right_score = scores.get((right_id, left_id))
                if left_score is None or right_score is None:
                    continue
                pair = (
                    (left_id, right_id)
                    if left_id <= right_id
                    else (right_id, left_id)
                )
                mutual[pair] = min(left_score, right_score)
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
        overlap = min(
            max(1, self.config.min_support - 1),
            self.config.max_path_length - 1,
        )

        def enumerate_from(start_id: str) -> None:
            pending: list[tuple[str, ...]] = [(start_id,)]
            while pending and len(raw_paths) < self.config.max_paths:
                path = pending.pop()
                children = outgoing.get(path[-1], ())

                if len(path) >= self.config.max_path_length:
                    raw_paths.append(path)
                    if len(raw_paths) >= self.config.max_paths:
                        return
                    suffix = path[-overlap:]
                    continuation = tuple(
                        child_id
                        for child_id in children
                        if child_id not in suffix
                    )
                    pending.extend(
                        (*suffix, child_id)
                        for child_id in reversed(continuation)
                    )
                    continue

                continuation = tuple(
                    child_id
                    for child_id in children
                    if child_id not in path
                )
                if not continuation:
                    raw_paths.append(path)
                    continue
                pending.extend(
                    (*path, child_id)
                    for child_id in reversed(continuation)
                )

        for start_id in starts:
            enumerate_from(start_id)
            if len(raw_paths) >= self.config.max_paths:
                break

        # A directed subgraph may have no indegree-zero node after filtering
        # only if input is malformed. Strict logical ordering should keep it
        # acyclic; still, fall back to each node to avoid silently losing data.
        if not raw_paths:
            for block_id in sorted(outgoing):
                if outgoing[block_id]:
                    enumerate_from(block_id)
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
                and any(
                    other[index : index + len(path)] == path
                    for index in range(len(other) - len(path) + 1)
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
            for parent_id, child_id in pairwise(path):
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
    """Separate slow Point-Cloud bootstrap from cheap nearline Line growth.

    Nearline observation never rescans the whole Point Cloud. It compares only
    the current SemanticBlocks against existing stable Line nodes. Full
    mutual-kNN discovery is an explicit bootstrap operation intended for batch
    or periodic slow-path execution.
    """

    def __init__(
        self,
        *,
        memory: ReferenceMemorySubstratePort,
        line_store: LineGraphStore,
        trajectory_config: TrajectoryConfig | None = None,
        assembler_config: LineAssemblerConfig | None = None,
        neighbour_provider: NeighbourCandidateProvider | None = None,
        authority_config: AuthorityConfig | None = None,
        authority_ledger: AuthorityLedger | None = None,
    ) -> None:
        self.memory = memory
        self.store = line_store
        self.config = trajectory_config or TrajectoryConfig()
        self.supplier = MutualKnnTrajectorySupplier(
            memory=memory,
            config=self.config,
            neighbour_provider=neighbour_provider,
        )
        self.assembler = LineAssembler(
            memory=memory,
            store=line_store,
            config=assembler_config,
        )
        self.view = LineGraphView(memory=memory, store=line_store)
        self.authority_config = authority_config or AuthorityConfig()
        self.authority = authority_ledger or AuthorityLedger(
            line_store.root / "authority"
        )
        self._owns_authority_ledger = authority_ledger is None
        provider = self.supplier.neighbour_provider
        provider_fingerprint = getattr(
            provider,
            "derivation_fingerprint",
            f"{type(provider).__module__}.{type(provider).__qualname__}",
        )
        variant_payload = {
            "algorithm": asdict(self.config),
            "provider": str(provider_fingerprint),
        }
        self.authority_variant_id = "trajvar_" + hashlib.sha256(
            repr(sorted(variant_payload.items())).encode()
        ).hexdigest()[:24]

    @staticmethod
    def _precedes(left: SemanticBlock, right: SemanticBlock) -> bool:
        return (
            left.occurred_start < right.occurred_start
            and left.occurred_end <= right.occurred_start
        )

    def _vector(self, block: SemanticBlock) -> tuple[float, ...] | None:
        if block.state_id is None:
            return None
        try:
            return self.memory.get_vector(
                block.block_id,
                state_id=block.state_id,
            ).values
        except KeyError:
            return None

    def _line_matches(
        self,
        block: SemanticBlock,
        *,
        knowledge_cutoff: datetime,
    ) -> tuple[tuple[float, str, str], ...]:
        query = self._vector(block)
        if query is None:
            return ()
        matches: list[tuple[float, str, str]] = []
        for line in self.store.list_lines():
            best_score = -1.0
            best_node_id: str | None = None
            for node_id in self.view.visible_node_ids(
                line.line_id,
                knowledge_cutoff=knowledge_cutoff,
            ):
                state = self.view.state_for_node_at_cutoff(
                    node_id,
                    knowledge_cutoff=knowledge_cutoff,
                )
                if state is None:
                    continue
                vector = self._vector(state)
                if vector is None:
                    continue
                score = _cosine(query, vector)
                if score > best_score:
                    best_score = score
                    best_node_id = node_id
            if (
                best_node_id is not None
                and best_score >= self.config.min_similarity
            ):
                matches.append((best_score, line.line_id, best_node_id))
        return tuple(
            sorted(
                matches,
                key=lambda item: (-item[0], item[1], item[2]),
            )
        )

    @staticmethod
    def _authority_context_id(block: SemanticBlock) -> str | None:
        value = block.metadata.get("authority_context_id")
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    @staticmethod
    def _authority_decision_key(
        kind: str,
        state_ids: tuple[str, ...],
        candidate_ids: tuple[str, ...],
    ) -> str:
        payload = "|".join(
            (
                kind,
                *state_ids,
                "--candidates--",
                *sorted(candidate_ids),
            )
        )
        return f"auth_{kind}_" + hashlib.sha256(
            payload.encode()
        ).hexdigest()[:24]

    def set_authority_variant_id(self, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("authority variant id must be nonempty")
        self.authority_variant_id = value.strip()

    def _authority_signal(
        self,
        *,
        decision_key: str,
        candidate_id: str,
        block: SemanticBlock,
        reciprocal: bool,
        knowledge_cutoff: datetime,
    ) -> AuthoritySignal:
        return AuthoritySignal(
            decision_key=decision_key,
            candidate_id=candidate_id,
            raw_evidence_ids=tuple(sorted(block.raw_evidence_ids)),
            derivation_variant_id=self.authority_variant_id,
            known_at=knowledge_cutoff,
            reciprocal=reciprocal,
            context_id=self._authority_context_id(block),
        )

    def _authority_policy(
        self,
        *,
        min_independent_support: int,
    ) -> AuthorityConfig:
        return replace(
            self.authority_config,
            min_independent_support=max(
                self.authority_config.min_independent_support,
                min_independent_support,
            ),
        )

    def _record_authority_candidates(
        self,
        *,
        decision_key: str,
        candidate_support: dict[str, tuple[SemanticBlock, ...]],
        reciprocal: bool,
        knowledge_cutoff: datetime,
        min_independent_support: int,
    ) -> AuthorityDecision:
        signals = tuple(
            self._authority_signal(
                decision_key=decision_key,
                candidate_id=candidate_id,
                block=block,
                reciprocal=reciprocal,
                knowledge_cutoff=knowledge_cutoff,
            )
            for candidate_id, blocks in sorted(candidate_support.items())
            for block in blocks
        )
        self.authority.record_many(signals)
        return self.authority.evaluate(
            decision_key,
            knowledge_cutoff=knowledge_cutoff,
            memory=self.memory,
            config=self._authority_policy(
                min_independent_support=min_independent_support,
            ),
        )

    def converge_path_identity(
        self,
        blocks: tuple[SemanticBlock, ...],
        *,
        knowledge_cutoff: datetime,
    ) -> AuthorityDecision:
        """Source-grounded convergence for Line seed/inheritance identity.

        Local geometry proposes the path. This method decides whether its
        persistent identity has enough independent Raw support, and resolves
        competing existing Lines only by non-scalar Pareto dominance.
        """
        if not blocks:
            raise ValueError("path identity requires at least one block")
        if any(block.state_id is None for block in blocks):
            raise ValueError("path identity requires immutable states")
        state_ids = tuple(
            block.state_id for block in blocks if block.state_id is not None
        )
        candidates = self.assembler.identity_candidates(
            blocks,
            knowledge_cutoff=knowledge_cutoff,
        )
        if candidates:
            decision_key = self._authority_decision_key(
                "line",
                state_ids,
                candidates,
            )
            support = {
                line_id: self.assembler.identity_support_blocks(
                    line_id,
                    blocks,
                    knowledge_cutoff=knowledge_cutoff,
                )
                for line_id in candidates
            }
            return self._record_authority_candidates(
                decision_key=decision_key,
                candidate_support=support,
                reciprocal=True,
                knowledge_cutoff=knowledge_cutoff,
                min_independent_support=(
                    self.assembler.config.min_shared_support
                ),
            )

        seed_id = self.store.line_id_for_seed(
            tuple(block.block_id for block in blocks)
        )
        decision_key = self._authority_decision_key(
            "seed",
            state_ids,
            (seed_id,),
        )
        return self._record_authority_candidates(
            decision_key=decision_key,
            candidate_support={seed_id: blocks},
            reciprocal=True,
            knowledge_cutoff=knowledge_cutoff,
            min_independent_support=max(
                self.config.min_support,
                self.assembler.config.min_seed_support,
            ),
        )

    def _retire_local_membership_relation(
        self,
        line_id: str,
        node_id: str,
        *,
        knowledge_cutoff: datetime,
    ) -> None:
        """Retire only the derived relation touched by a changed block state.

        Stable Line structure is reusable derived authority. A local state
        revision invalidates only this membership revision and its incident
        edges; unrelated nearline growth in the same Line is preserved.
        """
        parents = self.store.parents_at(node_id, knowledge_cutoff)
        children = self.store.children_at(node_id, knowledge_cutoff)
        with self.store.conn:
            for parent_id in parents:
                self.store.retire_edge_from(
                    line_id,
                    parent_id,
                    node_id,
                    knowledge_cutoff,
                    commit=False,
                )
            for child_id in children:
                self.store.retire_edge_from(
                    line_id,
                    node_id,
                    child_id,
                    knowledge_cutoff,
                    commit=False,
                )
            self.store.retire_membership_from(
                node_id,
                knowledge_cutoff,
                commit=False,
            )

    def _existing_relations_still_valid(
    def _existing_relations_still_valid(
        self,
        line_id: str,
        node_id: str,
        previous: SemanticBlock,
        current: SemanticBlock,
        *,
        knowledge_cutoff: datetime,
    ) -> bool:
        """Revalidate only the local persisted relations touched by a revision."""
        current_vector = self._vector(current)
        if current_vector is None:
            return False

        parents = self.store.parents_at(node_id, knowledge_cutoff)
        children = self.store.children_at(node_id, knowledge_cutoff)
        if not parents and not children:
            previous_vector = self._vector(previous)
            return (
                previous_vector is not None
                and _cosine(previous_vector, current_vector)
                >= self.config.min_similarity
            )

        for parent_id in parents:
            parent = self.view.state_for_node_at_cutoff(
                parent_id,
                knowledge_cutoff=knowledge_cutoff,
            )
            if parent is None or not self._precedes(parent, current):
                return False
            parent_vector = self._vector(parent)
            if (
                parent_vector is None
                or _cosine(parent_vector, current_vector)
                < self.config.min_similarity
            ):
                return False

        for child_id in children:
            child = self.view.state_for_node_at_cutoff(
                child_id,
                knowledge_cutoff=knowledge_cutoff,
            )
            if child is None or not self._precedes(current, child):
                return False
            child_vector = self._vector(child)
            if (
                child_vector is None
                or _cosine(current_vector, child_vector)
                < self.config.min_similarity
            ):
                return False

        return True

    def _attachment_neighbours(
        self,
        line_id: str,
        block: SemanticBlock,
        *,
        knowledge_cutoff: datetime,
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        query = self._vector(block)
        if query is None:
            return (), ()
        predecessors: list[tuple[datetime, float, str]] = []
        successors: list[tuple[datetime, float, str]] = []
        visible_ids = self.view.visible_node_ids(
            line_id,
            knowledge_cutoff=knowledge_cutoff,
        )
        frontier = set(
            self.view.frontier(
                line_id,
                knowledge_cutoff=knowledge_cutoff,
            )
        )
        for node_id in visible_ids:
            state = self.view.state_for_node_at_cutoff(
                node_id,
                knowledge_cutoff=knowledge_cutoff,
            )
            if state is None:
                continue
            vector = self._vector(state)
            if vector is None:
                continue
            score = _cosine(query, vector)
            if score < self.config.min_similarity:
                continue
            if self._precedes(state, block):
                predecessors.append(
                    (state.occurred_end, score, node_id)
                )
            elif self._precedes(block, state):
                successors.append(
                    (state.occurred_start, score, node_id)
                )

        # Prefer current frontier parents when growing forward. The default
        # selects one parent only. Multiple candidates are useful only when the
        # injected LineAssemblerConfig explicitly authorizes conjunctive rejoin.
        frontier_predecessors = [
            item for item in predecessors if item[2] in frontier
        ]
        parent_pool = frontier_predecessors or predecessors
        parents = tuple(
            node_id
            for _time, _score, node_id in sorted(
                parent_pool,
                key=lambda item: (-item[0].timestamp(), -item[1], item[2]),
            )[: self.config.max_incremental_parents]
        )

        # For late-known historical evidence, connect to the nearest logical
        # successor(s) while leaving old history intact. This creates another
        # auditable path instead of destructively rewiring the DAG.
        children = tuple(
            node_id
            for _time, _score, node_id in sorted(
                successors,
                key=lambda item: (item[0], -item[1], item[2]),
            )[: self.config.max_incremental_parents]
        )
        return parents, children

    def observe(
        self,
        *,
        knowledge_cutoff: datetime,
        current_block_ids: tuple[str, ...],
    ) -> TrajectoryRuntimeResult:
        """Nearline growth against already-authorized derived Line structure.

        Persisted Line membership/edges are compiled cognition. Ordinary
        nearline processing reuses them directly and performs independent
        relation admission per matching Line; it does not reopen historical
        Raw Evidence to elect one exclusive Line winner.
        """
        visible = {
            block.block_id: block
            for block in self.memory.list_semantic_blocks_at_knowledge_cutoff(
                knowledge_cutoff,
                current_valid_only=True,
            )
        }
        updates: list[LineApplyResult] = []
        for block_id in current_block_ids:
            block = visible.get(block_id)
            if block is None:
                continue

            existing_memberships = tuple(
                line_id
                for line_id in self.store.lines_for_block(block_id)
                if (
                    (node := self.store.node_for_block(line_id, block_id))
                    is not None
                    and self.store.membership_active_at(
                        node.node_id,
                        knowledge_cutoff,
                    )
                )
            )

            retained_memberships: set[str] = set()
            detached_revision = False
            for line_id in existing_memberships:
                node = self.store.node_for_block(line_id, block_id)
                if node is None:
                    continue
                previous = self.view.state_for_node_at_cutoff(
                    node.node_id,
                    knowledge_cutoff=knowledge_cutoff,
                )
                if previous is None:
                    self._retire_local_membership_relation(
                        line_id,
                        node.node_id,
                        knowledge_cutoff=knowledge_cutoff,
                    )
                    detached_revision = True
                    continue
                if previous.state_id == block.state_id:
                    retained_memberships.add(line_id)
                    continue
                if self._existing_relations_still_valid(
                    line_id,
                    node.node_id,
                    previous,
                    block,
                    knowledge_cutoff=knowledge_cutoff,
                ):
                    updates.append(
                        self.assembler.attach_block(
                            line_id,
                            block,
                            knowledge_cutoff=knowledge_cutoff,
                        )
                    )
                    retained_memberships.add(line_id)
                    continue

                self._retire_local_membership_relation(
                    line_id,
                    node.node_id,
                    knowledge_cutoff=knowledge_cutoff,
                )
                detached_revision = True

            if existing_memberships and not detached_revision:
                continue

            matches = self._line_matches(
                block,
                knowledge_cutoff=knowledge_cutoff,
            )
            for _score, line_id, _anchor_id in matches:
                if line_id in retained_memberships:
                    continue
                parents, children = self._attachment_neighbours(
                    line_id,
                    block,
                    knowledge_cutoff=knowledge_cutoff,
                )
                # Similarity alone does not create an isolated membership.
                # A nearline relation needs at least one ordered local witness.
                if not parents and not children:
                    continue
                updates.append(
                    self.assembler.attach_block(
                        line_id,
                        block,
                        parent_node_ids=parents,
                        child_node_ids=children,
                        knowledge_cutoff=knowledge_cutoff,
                    )
                )

        return TrajectoryRuntimeResult(
            knowledge_cutoff_iso=knowledge_cutoff.isoformat(),
            candidate_paths=(),
            line_updates=tuple(updates),
            authority_decisions=(),
        )

    def rebuild_current(
    def rebuild_current(
        self,
        *,
        knowledge_cutoff: datetime,
    ) -> TrajectoryRuntimeResult:
        """Recompile current Line structure with a durable crash marker.

        The marker is committed before destructive retirement. A hard process
        death therefore survives restart and forces the owning core to rebuild
        instead of serving a half-reactivated graph as current.
        """
        self.store.set_metadata(
            "rebuild_in_progress",
            knowledge_cutoff.isoformat(),
        )
        self.store.retire_current_structure(knowledge_cutoff)
        try:
            result = self.bootstrap(
                knowledge_cutoff=knowledge_cutoff,
            )
        except Exception:
            # Leave rebuild_in_progress set. A restart must fail closed and
            # retry instead of accepting this partial generation.
            self.store.retire_current_structure(knowledge_cutoff)
            raise
        self.store.set_metadata("rebuild_in_progress", "")
        return result

    def bootstrap(
        self,
        *,
        knowledge_cutoff: datetime,
    ) -> TrajectoryRuntimeResult:
        """Slow-path Point-Cloud discovery, run explicitly or once per batch."""
        blocks = self.memory.list_semantic_blocks_at_knowledge_cutoff(
            knowledge_cutoff,
            current_valid_only=True,
        )
        by_id = {block.block_id: block for block in blocks}
        paths = self.supplier.propose(blocks)
        ordered = tuple(
            sorted(
                paths,
                key=lambda path: (
                    -len(path.block_ids),
                    by_id[path.block_ids[0]].occurred_start,
                    by_id[path.block_ids[-1]].occurred_end,
                    -path.mean_local_similarity,
                    path.path_id,
                ),
            )
        )
        updates: list[LineApplyResult] = []
        authority_decisions: list[AuthorityDecision] = []
        for path in ordered:
            path_blocks = tuple(
                by_id[block_id] for block_id in path.block_ids
            )
            identity_candidates = self.assembler.identity_candidates(
                path_blocks,
                knowledge_cutoff=knowledge_cutoff,
            )
            decision = self.converge_path_identity(
                path_blocks,
                knowledge_cutoff=knowledge_cutoff,
            )
            authority_decisions.append(decision)
            if decision.status != "CONVERGED" or decision.winner_id is None:
                updates.append(
                    LineApplyResult(
                        line_id=None,
                        created_line=False,
                        added_node_ids=(),
                        added_state_ids=(),
                        added_edges=(),
                        unresolved_reason=(
                            "trajectory identity lacks unique "
                            "source-grounded convergence"
                        ),
                    )
                )
                continue
            resolved_line_id = (
                decision.winner_id if identity_candidates else None
            )
            updates.append(
                self.assembler.apply_path(
                    path_blocks,
                    knowledge_cutoff=knowledge_cutoff,
                    resolved_line_id=resolved_line_id,
                )
            )
        return TrajectoryRuntimeResult(
            knowledge_cutoff_iso=knowledge_cutoff.isoformat(),
            candidate_paths=ordered,
            line_updates=tuple(updates),
            authority_decisions=tuple(authority_decisions),
        )

    def close(self) -> None:
        if self._owns_authority_ledger:
            self.authority.close()
