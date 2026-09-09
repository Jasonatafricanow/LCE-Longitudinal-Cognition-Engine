"""Conservative worktree promotion through the existing LCE Core."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from lce.cognition.block_adapter import SemanticBlockMemoryAdapter
from lce.cognition.worktree import CognitionWorktree, CognitionWorktreeStore
from lce.contracts.baseline import Baseline
from lce.contracts.consolidation import CandidateBaseline, ConsolidationResult
from lce.contracts.external_memory import MemoryItemView
from lce.core.engine import LceCore
from lce.reference_memory.contracts import SemanticBlock, SemanticBlockPort
from lce.store.interface import BaselineStorePort
from lce.structure.contracts import HigherOrderCandidate, StructureObservation


@runtime_checkable
class PromotionPolicy(Protocol):
    def should_promote(self, worktree: CognitionWorktree, support_cycles: int) -> bool:
        ...


@dataclass(frozen=True, slots=True)
class BoundedInterpretationPackage:
    """The complete, caller-resolved package visible to an interpreter."""

    candidate: HigherOrderCandidate
    structures: tuple[StructureObservation, ...]
    semantic_blocks: tuple[SemanticBlock, ...]
    authorized_source_refs: tuple[str, ...]
    previous_baseline: Baseline | None = None
    context: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BoundedInterpretation:
    content: str | None
    supporting_block_ids: tuple[str, ...]
    status: str = "PROPOSED"
    model_trace: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in {"PROPOSED", "UNKNOWN", "REJECTED"}:
            raise ValueError("bounded interpretation status must be PROPOSED, UNKNOWN, or REJECTED")
        if self.status == "PROPOSED" and (self.content is None or not self.content.strip()):
            raise ValueError("a proposed interpretation requires content")
        if len(self.supporting_block_ids) != len(set(self.supporting_block_ids)):
            raise ValueError("bounded interpretation block IDs must be unique")


@runtime_checkable
class BoundedInterpreter(Protocol):
    def interpret(self, package: BoundedInterpretationPackage) -> BoundedInterpretation:
        """Interpret only the exact bounded package supplied by LCE."""
        ...


class RuleBasedBoundedInterpreter:
    """Deterministic reference interpreter over the supplied bounded package only."""

    def interpret(self, package: BoundedInterpretationPackage) -> BoundedInterpretation:
        if not package.semantic_blocks or not package.structures:
            return BoundedInterpretation(
                content=None,
                supporting_block_ids=(),
                status="UNKNOWN",
                model_trace={"provider": "reference-bounded-interpreter", "model": "rule-based-v1"},
            )
        fragments = tuple(dict.fromkeys(block.content.strip() for block in package.semantic_blocks))
        content = "Longitudinal relation supported by: " + "; ".join(fragments)
        return BoundedInterpretation(
            content=content,
            supporting_block_ids=package.candidate.supporting_block_ids,
            model_trace={"provider": "reference-bounded-interpreter", "model": "rule-based-v1"},
        )


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
    def __init__(self, interpretation: BoundedInterpretation, fallback_block_ids: tuple[str, ...]) -> None:
        self.interpretation = interpretation
        self.fallback_block_ids = fallback_block_ids

    def consolidate(
        self,
        *,
        memories: tuple[MemoryItemView, ...],
        previous_baseline: Baseline | None,
        context: Mapping[str, object] | None = None,
    ) -> CandidateBaseline:
        if self.interpretation.content is None:
            raise ValueError("cannot consolidate an interpretation without content")
        return CandidateBaseline(
            content=self.interpretation.content,
            supporting_memory_ids=self.interpretation.supporting_block_ids or self.fallback_block_ids,
            model_trace=self.interpretation.model_trace,
            supporting_state_ids=tuple(
                str(memory.retrieval_metadata["state_id"])
                for memory in memories
                if memory.retrieval_metadata.get("state_id")
            ),
        )


class UnderstandingPromoter:
    def __init__(
        self,
        *,
        memory: SemanticBlockPort,
        baseline_store: BaselineStorePort,
        worktree_store: CognitionWorktreeStore,
        policy: PromotionPolicy,
    ) -> None:
        self.memory = memory
        self.baseline_store = baseline_store
        self.worktree_store = worktree_store
        self.policy = policy

    def evaluate(
        self, worktree_id: str, *, interpretation: BoundedInterpretation | None = None
    ) -> ConsolidationResult | None:
        worktree = self.worktree_store.get(worktree_id)
        if worktree.status != "OPEN":
            return None
        if interpretation is None:
            interpretation = BoundedInterpretation(
                content=worktree.candidate_content,
                supporting_block_ids=worktree.supporting_block_ids,
                model_trace=worktree.interpretation_trace,
            )
        if interpretation.status != "PROPOSED":
            return None
        authorized = set(worktree.supporting_block_ids)
        if not set(interpretation.supporting_block_ids).issubset(authorized):
            raise ValueError("bounded interpretation referenced an unauthorized Semantic Block")
        if not self.policy.should_promote(worktree, self.worktree_store.support_cycle_count(worktree_id)):
            return None
        core = LceCore(
            memory_substrate=SemanticBlockMemoryAdapter(self.memory),
            baseline_store=self.baseline_store,
            consolidator=_CandidateConsolidator(interpretation, worktree.supporting_block_ids),
        )
        result = core.consolidate(worktree.region_id, worktree.supporting_block_ids)
        self.worktree_store.set_status(worktree_id, "MERGED", merged_baseline_id=result.baseline.baseline_id)
        return result
