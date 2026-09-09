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
from lce.core.equivalence import is_content_equivalent
from lce.reference_memory.contracts import (
    AuthorizedSelectedSupport,
    SemanticBlock,
    SemanticBlockPort,
)
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
    selected_support: tuple[AuthorizedSelectedSupport, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in {"PROPOSED", "UNKNOWN", "REJECTED"}:
            raise ValueError("bounded interpretation status must be PROPOSED, UNKNOWN, or REJECTED")
        if self.status == "PROPOSED" and (self.content is None or not self.content.strip()):
            raise ValueError("a proposed interpretation requires content")
        if len(self.supporting_block_ids) != len(set(self.supporting_block_ids)):
            raise ValueError("bounded interpretation block IDs must be unique")
        if len({item.block_id for item in self.selected_support}) != len(self.selected_support):
            raise ValueError("bounded interpretation selected support contains duplicate block IDs")
        if self.selected_support and tuple(item.block_id for item in self.selected_support) != self.supporting_block_ids:
            raise ValueError("bounded interpretation selected support must align with block IDs")


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
    def __init__(
        self,
        interpretation: BoundedInterpretation,
        fallback_block_ids: tuple[str, ...],
        selected_support: tuple[AuthorizedSelectedSupport, ...],
    ) -> None:
        self.interpretation = interpretation
        self.fallback_block_ids = fallback_block_ids
        self.selected_support = selected_support

    def consolidate(
        self,
        *,
        memories: tuple[MemoryItemView, ...],
        previous_baseline: Baseline | None,
        context: Mapping[str, object] | None = None,
    ) -> CandidateBaseline:
        if self.interpretation.content is None:
            raise ValueError("cannot consolidate an interpretation without content")
        supporting_memory_ids = (
            tuple(item.block_id for item in self.selected_support)
            or self.interpretation.supporting_block_ids
            or self.fallback_block_ids
        )
        selected_support = self.selected_support
        if not selected_support:
            selected_by_id = {memory.memory_id: memory for memory in memories}
            selected_support = tuple(
                AuthorizedSelectedSupport(
                    block_id=block_id,
                    state_id=str(selected_by_id[block_id].retrieval_metadata["state_id"]),
                )
                for block_id in supporting_memory_ids
                if block_id in selected_by_id and selected_by_id[block_id].retrieval_metadata.get("state_id")
            )
        return CandidateBaseline(
            content=self.interpretation.content,
            supporting_memory_ids=supporting_memory_ids,
            model_trace=self.interpretation.model_trace,
            supporting_state_ids=tuple(item.state_id for item in selected_support),
            selected_support=selected_support,
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

    def reconcile_committed(self, worktree_id: str) -> ConsolidationResult | None:
        """Repair only the derived worktree status after an already committed result."""

        worktree = self.worktree_store.get(worktree_id)
        if worktree.status != "OPEN":
            return None
        head = self.baseline_store.get_head(worktree.region_id)
        if head is None or not is_content_equivalent(head.content, worktree.candidate_content):
            return None
        expected_blocks = tuple(item.block_id for item in worktree.selected_support) or worktree.supporting_block_ids
        if head.supporting_memory_ids != expected_blocks:
            return None
        if worktree.selected_support and head.selected_support != worktree.selected_support:
            return None
        self.worktree_store.set_status(worktree_id, "MERGED", merged_baseline_id=head.baseline_id)
        return ConsolidationResult(head, revised=False, reason="POST_COMMIT_RECONCILED")

    def _resolve_selected_support(
        self,
        worktree: CognitionWorktree,
        interpretation: BoundedInterpretation,
    ) -> tuple[AuthorizedSelectedSupport, ...]:
        requested_ids = interpretation.supporting_block_ids
        if interpretation.selected_support:
            selected = interpretation.selected_support
            if tuple(item.block_id for item in selected) != requested_ids:
                raise ValueError("selected support and interpreter block order do not match")
        elif worktree.selected_support:
            by_block = {item.block_id: item for item in worktree.selected_support}
            selected = tuple(by_block[block_id] for block_id in requested_ids if block_id in by_block)
            if len(selected) != len(requested_ids):
                raise ValueError("interpreter selected a block without an authorized immutable state")
        else:
            selected_list: list[AuthorizedSelectedSupport] = []
            for block_id in requested_ids:
                block = self.memory.get_semantic_block(block_id)
                if block.state_id is None:
                    raise ValueError("Semantic Block has no immutable state ID")
                selected_list.append(AuthorizedSelectedSupport(block_id=block_id, state_id=block.state_id))
            selected = tuple(selected_list)

        authorized = set(worktree.supporting_block_ids)
        if any(item.block_id not in authorized for item in selected):
            raise ValueError("bounded interpretation referenced an unauthorized Semantic Block")
        for item in selected:
            state = self.memory.get_semantic_block_state(item.state_id)
            if state.block_id != item.block_id:
                raise ValueError("selected immutable state belongs to another Semantic Block")
            if not all(self.memory.get_evidence(evidence_id).current_valid for evidence_id in state.raw_evidence_ids):
                raise ValueError("selected immutable state is no longer current-valid")
        return selected

    def evaluate(
        self, worktree_id: str, *, interpretation: BoundedInterpretation | None = None
    ) -> ConsolidationResult | None:
        worktree = self.worktree_store.get(worktree_id)
        if worktree.status != "OPEN":
            return None
        reconciled = self.reconcile_committed(worktree_id)
        if reconciled is not None:
            return reconciled
        if interpretation is None:
            requested_block_ids = (
                tuple(item.block_id for item in worktree.selected_support)
                or worktree.supporting_block_ids
            )
            interpretation = BoundedInterpretation(
                content=worktree.candidate_content,
                supporting_block_ids=requested_block_ids,
                model_trace=worktree.interpretation_trace,
                selected_support=worktree.selected_support,
            )
        if interpretation.status != "PROPOSED":
            return None
        selected_support = self._resolve_selected_support(worktree, interpretation)
        interpretation = BoundedInterpretation(
            content=interpretation.content,
            supporting_block_ids=tuple(item.block_id for item in selected_support),
            status=interpretation.status,
            model_trace=interpretation.model_trace,
            selected_support=selected_support,
        )
        if not self.policy.should_promote(worktree, self.worktree_store.support_cycle_count(worktree_id)):
            return None
        core = LceCore(
            memory_substrate=SemanticBlockMemoryAdapter(self.memory, selected_support=selected_support),
            baseline_store=self.baseline_store,
            consolidator=_CandidateConsolidator(interpretation, worktree.supporting_block_ids, selected_support),
        )
        result = core.consolidate(worktree.region_id, tuple(item.block_id for item in selected_support))
        self.worktree_store.set_status(worktree_id, "MERGED", merged_baseline_id=result.baseline.baseline_id)
        return result
