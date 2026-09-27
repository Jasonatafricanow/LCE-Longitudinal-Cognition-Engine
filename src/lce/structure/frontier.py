"""Frontier-first longitudinal candidate discovery.

Accepted Baselines and OPEN Worktrees form a rebuildable cognition frontier.
New Semantic Blocks are compared with that frontier before the legacy
structure↔structure supplier is consulted.  The frontier never becomes source
authority; it only proposes bounded candidates over already-authorized blocks.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime

from lce.cognition.worktree import DraftRevisionStore
from lce.reference_memory.contracts import (
    AuthorizedSelectedSupport,
    ReferenceMemorySubstratePort,
    SemanticBlock,
)
from lce.store.interface import BaselineStorePort
from lce.structure.contracts import (
    StructureRelationCandidate,
    StructureSnapshot,
)


def _cosine(
    left: tuple[float, ...],
    right: tuple[float, ...],
) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return max(0.0, min(1.0, numerator / (left_norm * right_norm)))


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.casefold(), flags=re.UNICODE))


def _lexical_overlap(left: str, right: str) -> float:
    a, b = _tokens(left), _tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _centroid(vectors: tuple[tuple[float, ...], ...]) -> tuple[float, ...]:
    if not vectors:
        return ()
    dimension = len(vectors[0])
    if any(len(vector) != dimension for vector in vectors):
        return ()
    return tuple(
        sum(vector[index] for vector in vectors) / len(vectors)
        for index in range(dimension)
    )


@dataclass(frozen=True, slots=True)
class FrontierDiscoveryConfig:
    """Replaceable policy for frontier candidate generation."""

    enabled: bool = True
    direct_weight: float = 0.45
    support_weight: float = 0.30
    lexical_weight: float = 0.15
    temporal_weight: float = 0.10
    min_absorption_score: float = 0.62
    branch_rescue_similarity: float = 0.82
    boundary_min_component: float = 0.40
    boundary_sum_threshold: float = 1.08
    temporal_half_life_days: float = 180.0
    temporal_floor: float = 0.35
    max_absorption_candidates: int = 2
    max_frontier_support_blocks: int = 8
    algorithm_version: str = "frontier-01-v1"

    def __post_init__(self) -> None:
        if type(self.enabled) is not bool:
            raise TypeError("enabled must be bool")
        weights = (
            self.direct_weight,
            self.support_weight,
            self.lexical_weight,
            self.temporal_weight,
        )
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or value < 0
            for value in weights
        ):
            raise ValueError("frontier weights must be nonnegative numbers")
        if not math.isclose(sum(weights), 1.0, abs_tol=1e-9):
            raise ValueError("frontier weights must sum to 1")
        for value, name in (
            (self.min_absorption_score, "min_absorption_score"),
            (self.branch_rescue_similarity, "branch_rescue_similarity"),
            (self.boundary_min_component, "boundary_min_component"),
            (self.temporal_floor, "temporal_floor"),
        ):
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")
        if not 0.0 <= self.boundary_sum_threshold <= 2.0:
            raise ValueError("boundary_sum_threshold must be in [0, 2]")
        if self.temporal_half_life_days <= 0:
            raise ValueError("temporal_half_life_days must be positive")
        if (
            type(self.max_absorption_candidates) is not int
            or self.max_absorption_candidates < 1
        ):
            raise ValueError("max_absorption_candidates must be positive")
        if (
            type(self.max_frontier_support_blocks) is not int
            or self.max_frontier_support_blocks < 1
        ):
            raise ValueError("max_frontier_support_blocks must be positive")
        if not self.algorithm_version.strip():
            raise ValueError("algorithm_version must be nonempty")


@dataclass(frozen=True, slots=True)
class _FrontierItem:
    region_id: str
    frontier_ref: str
    kind: str
    content: str
    support_blocks: tuple[SemanticBlock, ...]
    occurred_end: datetime


@dataclass(frozen=True, slots=True)
class _Match:
    item: _FrontierItem
    current_block_id: str
    score: float
    direct_similarity: float
    support_similarity: float
    lexical_overlap: float
    temporal_prior: float
    selected_support_ids: tuple[str, ...]
    rescued: bool


class FrontierCandidateDiscovery:
    """Generate candidates from existing compiled cognition before raw structure."""

    def __init__(
        self,
        *,
        memory: ReferenceMemorySubstratePort,
        baselines: BaselineStorePort,
        worktrees: DraftRevisionStore,
        config: FrontierDiscoveryConfig | None = None,
    ) -> None:
        self.memory = memory
        self.baselines = baselines
        self.worktrees = worktrees
        self.config = config or FrontierDiscoveryConfig()

    def candidates(
        self,
        snapshot: StructureSnapshot,
        *,
        current_block_ids: tuple[str, ...],
    ) -> tuple[StructureRelationCandidate, ...]:
        if not self.config.enabled or not current_block_ids:
            return ()
        block_by_id = {
            block.block_id: block
            for block in snapshot.block_states
        }
        current_blocks = tuple(
            block_by_id[block_id]
            for block_id in dict.fromkeys(current_block_ids)
            if block_id in block_by_id
        )
        if not current_blocks:
            return ()

        frontier = self._frontier(block_by_id)
        if not frontier:
            return ()

        matches: list[_Match] = []
        for block in current_blocks:
            for item in frontier:
                match = self._score(snapshot, block, item, block_by_id)
                if match is not None:
                    matches.append(match)

        absorptions = self._absorption_candidates(snapshot, matches)
        boundary = self._boundary_candidate(snapshot, matches)
        if boundary is None:
            return absorptions
        return (*absorptions, boundary)

    def _frontier(
        self,
        block_by_id: dict[str, SemanticBlock],
    ) -> tuple[_FrontierItem, ...]:
        open_by_region = {
            item.region_id: item
            for item in self.worktrees.list(status="OPEN")
            if item.supporting_block_ids
        }
        items: list[_FrontierItem] = []

        for region_id, worktree in sorted(open_by_region.items()):
            support_blocks = self._resolve_support_blocks(
                selected=worktree.selected_support,
                fallback_block_ids=worktree.supporting_block_ids,
                block_by_id=block_by_id,
            )
            frontier_item = self._make_item(
                region_id=region_id,
                frontier_ref=f"worktree:{worktree.worktree_id}",
                kind="worktree",
                content=worktree.candidate_content,
                support_blocks=support_blocks,
            )
            if frontier_item is not None:
                items.append(frontier_item)

        for region_id in self.baselines.list_regions():
            if region_id in open_by_region:
                continue
            baseline = self.baselines.get_head(region_id)
            if baseline is None:
                continue
            support_blocks = self._resolve_support_blocks(
                selected=baseline.selected_support,
                fallback_block_ids=baseline.supporting_memory_ids,
                block_by_id=block_by_id,
            )
            frontier_item = self._make_item(
                region_id=region_id,
                frontier_ref=f"baseline:{baseline.baseline_id}",
                kind="baseline",
                content=baseline.content,
                support_blocks=support_blocks,
            )
            if frontier_item is not None:
                items.append(frontier_item)

        return tuple(items)

    def _resolve_support_blocks(
        self,
        *,
        selected: tuple[AuthorizedSelectedSupport, ...],
        fallback_block_ids: tuple[str, ...],
        block_by_id: dict[str, SemanticBlock],
    ) -> tuple[SemanticBlock, ...]:
        blocks: list[SemanticBlock] = []
        if selected:
            for item in selected:
                try:
                    block = self.memory.get_semantic_block_state(
                        item.state_id
                    )
                except KeyError:
                    return ()
                if block.block_id != item.block_id:
                    return ()
                if not self._state_is_current(block):
                    return ()
                blocks.append(block)
            return tuple(blocks)

        # Legacy baselines/worktrees without frozen state IDs can still be
        # consumed, but only through the visible no-future snapshot state.
        for block_id in fallback_block_ids:
            block = block_by_id.get(block_id)
            if block is not None and self._state_is_current(block):
                blocks.append(block)
        return tuple(blocks)

    def _state_is_current(self, block: SemanticBlock) -> bool:
        try:
            return all(
                self.memory.get_evidence(evidence_id).current_valid
                for evidence_id in block.raw_evidence_ids
            )
        except KeyError:
            return False

    @staticmethod
    def _make_item(
        *,
        region_id: str,
        frontier_ref: str,
        kind: str,
        content: str,
        support_blocks: tuple[SemanticBlock, ...],
    ) -> _FrontierItem | None:
        if not support_blocks:
            return None
        occurred_end = max(
            block.occurred_end for block in support_blocks
        )
        return _FrontierItem(
            region_id=region_id,
            frontier_ref=frontier_ref,
            kind=kind,
            content=content,
            support_blocks=support_blocks,
            occurred_end=occurred_end,
        )

    def _temporal_prior(
        self,
        current: SemanticBlock,
        frontier: _FrontierItem,
    ) -> float:
        age_days = max(
            0.0,
            (current.occurred_end - frontier.occurred_end).total_seconds()
            / 86400.0,
        )
        decay = math.exp(
            -math.log(2.0)
            * age_days
            / self.config.temporal_half_life_days
        )
        return self.config.temporal_floor + (
            1.0 - self.config.temporal_floor
        ) * decay

    def _vector_for_support(
        self,
        snapshot: StructureSnapshot,
        block: SemanticBlock,
    ) -> tuple[float, ...] | None:
        if block.state_id is not None:
            try:
                return self.memory.get_vector(
                    block.block_id,
                    state_id=block.state_id,
                ).values
            except KeyError:
                return None
        return snapshot.vectors.get(block.block_id)

    def _score(
        self,
        snapshot: StructureSnapshot,
        current: SemanticBlock,
        frontier: _FrontierItem,
        block_by_id: dict[str, SemanticBlock],
    ) -> _Match | None:
        # A future-created frontier must never participate in historical replay.
        if frontier.occurred_end > current.occurred_end:
            return None
        current_vector = snapshot.vectors.get(current.block_id)
        if current_vector is None:
            return None

        support_pairs = []
        for block in frontier.support_blocks:
            vector = self._vector_for_support(snapshot, block)
            if vector is not None:
                support_pairs.append((block, vector))
        if not support_pairs:
            return None

        support_vectors = tuple(vector for _, vector in support_pairs)
        direct_similarity = _cosine(
            current_vector,
            _centroid(support_vectors),
        )
        ranked_support = sorted(
            (
                (
                    _cosine(current_vector, vector),
                    block,
                )
                for block, vector in support_pairs
            ),
            key=lambda item: (
                -item[0],
                item[1].block_id,
                item[1].state_version,
            ),
        )
        support_similarity = ranked_support[0][0]
        selected_support_blocks = tuple(
            block
            for _, block in ranked_support[
                : self.config.max_frontier_support_blocks
            ]
        )
        selected_support_ids = tuple(
            block.block_id for block in selected_support_blocks
        )
        support_text = " ".join(
            block.content for block in selected_support_blocks
        )
        lexical = max(
            _lexical_overlap(current.content, frontier.content),
            _lexical_overlap(current.content, support_text),
        )
        temporal = self._temporal_prior(current, frontier)
        score = (
            self.config.direct_weight * direct_similarity
            + self.config.support_weight * support_similarity
            + self.config.lexical_weight * lexical
            + self.config.temporal_weight * temporal
        )
        rescued = (
            support_similarity
            >= self.config.branch_rescue_similarity
        )
        return _Match(
            item=frontier,
            current_block_id=current.block_id,
            score=min(1.0, score),
            direct_similarity=direct_similarity,
            support_similarity=support_similarity,
            lexical_overlap=lexical,
            temporal_prior=temporal,
            selected_support_ids=selected_support_ids,
            rescued=rescued,
        )

    def _absorption_candidates(
        self,
        snapshot: StructureSnapshot,
        matches: list[_Match],
    ) -> tuple[StructureRelationCandidate, ...]:
        eligible = [
            match
            for match in matches
            if match.score >= self.config.min_absorption_score
            or match.rescued
        ]
        eligible.sort(
            key=lambda match: (
                -match.score,
                -match.support_similarity,
                match.item.region_id,
                match.current_block_id,
            )
        )
        selected: list[_Match] = []
        seen_regions: set[str] = set()
        for match in eligible:
            if match.item.region_id in seen_regions:
                continue
            selected.append(match)
            seen_regions.add(match.item.region_id)
            if len(selected) >= self.config.max_absorption_candidates:
                break

        return tuple(
            self._candidate(
                snapshot=snapshot,
                relation_type="frontier_absorption",
                matches=(match,),
                target_region_id=match.item.region_id,
            )
            for match in selected
        )

    def _boundary_candidate(
        self,
        snapshot: StructureSnapshot,
        matches: list[_Match],
    ) -> StructureRelationCandidate | None:
        best_by_region: dict[str, _Match] = {}
        for match in matches:
            previous = best_by_region.get(match.item.region_id)
            if previous is None or (
                match.score,
                match.support_similarity,
            ) > (
                previous.score,
                previous.support_similarity,
            ):
                best_by_region[match.item.region_id] = match

        ranked = sorted(
            best_by_region.values(),
            key=lambda match: (
                -match.score,
                -match.support_similarity,
                match.item.region_id,
            ),
        )
        if len(ranked) < 2:
            return None
        left, right = ranked[:2]
        if (
            left.score < self.config.boundary_min_component
            or right.score < self.config.boundary_min_component
        ):
            return None
        if (
            left.score + right.score
            < self.config.boundary_sum_threshold
            and not (left.rescued and right.rescued)
        ):
            return None
        return self._candidate(
            snapshot=snapshot,
            relation_type="frontier_boundary",
            matches=(left, right),
            target_region_id=None,
        )

    def _candidate(
        self,
        *,
        snapshot: StructureSnapshot,
        relation_type: str,
        matches: tuple[_Match, ...],
        target_region_id: str | None,
    ) -> StructureRelationCandidate:
        frontier_refs = tuple(
            dict.fromkeys(match.item.frontier_ref for match in matches)
        )
        region_ids = tuple(
            dict.fromkeys(match.item.region_id for match in matches)
        )
        block_ids: list[str] = []
        for match in matches:
            block_ids.extend(match.selected_support_ids)
            block_ids.append(match.current_block_id)
        support = tuple(dict.fromkeys(block_ids))
        identity = {
            "algorithm": self.config.algorithm_version,
            "snapshot": snapshot.snapshot_id,
            "relation": relation_type,
            "frontier_refs": frontier_refs,
            "current_blocks": tuple(
                match.current_block_id for match in matches
            ),
        }
        candidate_id = "frontier_" + hashlib.sha256(
            json.dumps(identity, sort_keys=True).encode()
        ).hexdigest()[:20]
        immutable_frontier_support = tuple(
            {
                "block_id": block.block_id,
                "state_id": block.state_id,
            }
            for match in matches
            for block in match.item.support_blocks
            if block.state_id is not None
        )
        metadata: dict[str, object] = {
            "supplier": self.config.algorithm_version,
            "frontier_refs": frontier_refs,
            "frontier_region_ids": region_ids,
            "frontier_selected_support": immutable_frontier_support,
            "current_block_ids": tuple(
                match.current_block_id for match in matches
            ),
            "scores": tuple(
                {
                    "region_id": match.item.region_id,
                    "frontier_kind": match.item.kind,
                    "score": match.score,
                    "direct_similarity": match.direct_similarity,
                    "support_similarity": match.support_similarity,
                    "lexical_overlap": match.lexical_overlap,
                    "temporal_prior": match.temporal_prior,
                    "branch_rescue": match.rescued,
                }
                for match in matches
            ),
        }
        if target_region_id is not None:
            metadata["target_region_id"] = target_region_id
        return StructureRelationCandidate(
            candidate_id=candidate_id,
            snapshot_id=snapshot.snapshot_id,
            supporting_structure_ids=(),
            supporting_block_ids=support,
            relation_type=relation_type,
            strength=sum(match.score for match in matches) / len(matches),
            metadata=metadata,
        )
