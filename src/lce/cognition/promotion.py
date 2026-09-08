"""Conservative worktree promotion through the existing LCE Core."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from lce.contracts.baseline import Baseline
from lce.contracts.consolidation import CandidateBaseline, ConsolidationResult
from lce.contracts.external_memory import MemoryItemView
from lce.cognition.block_adapter import SemanticBlockMemoryAdapter
from lce.cognition.worktree import CognitionWorktree, CognitionWorktreeStore
from lce.core.engine import LceCore
from lce.reference_memory.sqlite import ReferenceMemoryStore
from lce.store.interface import BaselineStorePort


@runtime_checkable
class PromotionPolicy(Protocol):
    def should_promote(self, worktree: CognitionWorktree, support_cycles: int) -> bool:
        ...


@dataclass(frozen=True, slots=True)
class ConservativePromotionPolicy:
    min_blocks: int = 2
    min_structures: int = 2
    min_support_cycles: int = 2

    def should_promote(self, worktree: CognitionWorktree, support_cycles: int) -> bool:
        return (
            len(worktree.supporting_block_ids) >= self.min_blocks
            and len(worktree.supporting_structure_ids) >= self.min_structures
            and support_cycles >= self.min_support_cycles
        )


class _CandidateConsolidator:
    def __init__(self, content: str, block_ids: tuple[str, ...]) -> None:
        self.content = content
        self.block_ids = block_ids

    def consolidate(
        self,
        *,
        memories: tuple[MemoryItemView, ...],
        previous_baseline: Baseline | None,
        context: Mapping[str, object] | None = None,
    ) -> CandidateBaseline:
        return CandidateBaseline(
            content=self.content,
            supporting_memory_ids=self.block_ids,
            model_trace={"provider": "lce-bounded-interpreter", "model": "bounded-v1"},
        )


class UnderstandingPromoter:
    def __init__(
        self,
        *,
        memory: ReferenceMemoryStore,
        baseline_store: BaselineStorePort,
        worktree_store: CognitionWorktreeStore,
        policy: PromotionPolicy,
    ) -> None:
        self.memory = memory
        self.baseline_store = baseline_store
        self.worktree_store = worktree_store
        self.policy = policy

    def evaluate(self, worktree_id: str) -> ConsolidationResult | None:
        worktree = self.worktree_store.get(worktree_id)
        if worktree.status != "OPEN":
            return None
        if not self.policy.should_promote(worktree, self.worktree_store.support_cycle_count(worktree_id)):
            return None
        core = LceCore(
            memory_substrate=SemanticBlockMemoryAdapter(self.memory),
            baseline_store=self.baseline_store,
            consolidator=_CandidateConsolidator(worktree.candidate_content, worktree.supporting_block_ids),
        )
        result = core.consolidate(worktree.region_id, worktree.supporting_block_ids)
        self.worktree_store.set_status(worktree_id, "MERGED", merged_baseline_id=result.baseline.baseline_id)
        return result
