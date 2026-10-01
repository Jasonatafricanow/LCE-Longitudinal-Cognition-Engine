"""Intake for already-reasoned cognition over external Memory.

This path is deliberately separate from Semantic Block structure discovery.
It records the supplied cognition as a durable DraftRevision first, then
promotes it through LCE Core without invoking another semantic model.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from lce.cognition.rejection import DerivedProposalRejectionStore
from lce.cognition.worktree import DraftRevision, DraftRevisionStore
from lce.contracts.baseline import Baseline
from lce.contracts.consolidation import CandidateBaseline, ConsolidationResult
from lce.contracts.external_memory import MemoryItemView, MemorySubstratePort
from lce.core.engine import LceCore
from lce.core.equivalence import (
    is_content_equivalent,
    is_support_equivalent,
)
from lce.reference_memory.contracts import AuthorizedSelectedSupport, SemanticBlockPort
from lce.store.interface import BaselineStorePort


@dataclass(frozen=True, slots=True)
class PrecomputedDraftInput:
    """One bounded interpretation already formed by an upstream working layer."""

    region_id: str
    content: str
    supporting_memory_ids: tuple[str, ...]
    processing_input_id: str
    context: Mapping[str, object] = field(default_factory=dict)
    selected_support: tuple[AuthorizedSelectedSupport, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.region_id, str) or not self.region_id.strip():
            raise ValueError("region_id must be non-empty")
        if not isinstance(self.content, str) or not self.content.strip():
            raise ValueError("content must be non-empty")
        if (
            not isinstance(self.supporting_memory_ids, tuple)
            or not self.supporting_memory_ids
        ):
            raise ValueError("supporting_memory_ids must be a non-empty tuple")
        if len(set(self.supporting_memory_ids)) != len(self.supporting_memory_ids):
            raise ValueError("supporting_memory_ids must be unique")
        if any(
            not isinstance(memory_id, str) or not memory_id.strip()
            for memory_id in self.supporting_memory_ids
        ):
            raise ValueError("supporting_memory_ids entries must be non-empty")
        if (
            not isinstance(self.processing_input_id, str)
            or not self.processing_input_id.strip()
        ):
            raise ValueError("processing_input_id must be non-empty")
        if not isinstance(self.context, Mapping):
            raise TypeError("context must be a Mapping")
        if self.selected_support and tuple(item.block_id for item in self.selected_support) != self.supporting_memory_ids:
            raise ValueError("selected semantic states must align with support IDs")


class _PrecomputedConsolidator:
    def __init__(self, draft: PrecomputedDraftInput) -> None:
        self._draft = draft

    def consolidate(
        self,
        *,
        memories: tuple[MemoryItemView, ...],
        previous_baseline: Baseline | None,
        context: Mapping[str, object] | None = None,
    ) -> CandidateBaseline:
        del previous_baseline, context
        supplied = {memory.memory_id for memory in memories}
        expected = set(self._draft.supporting_memory_ids)
        if supplied != expected or len(memories) != len(expected):
            raise ValueError("resolved external Memory does not match draft support")
        return CandidateBaseline(
            content=self._draft.content,
            supporting_memory_ids=self._draft.supporting_memory_ids,
            model_trace={},
            supporting_state_ids=tuple(item.state_id for item in self._draft.selected_support),
            selected_support=self._draft.selected_support,
        )


class RejectedDerivedProposalError(ValueError):
    """An unchanged source closure cannot reactivate a rejected interpretation."""


class PrecomputedDraftIntake:
    """Persist an upstream interpretation as OPEN draft before Baseline promotion."""

    def __init__(
        self,
        *,
        memory_substrate: MemorySubstratePort,
        baseline_store: BaselineStorePort,
        draft_store: DraftRevisionStore,
        rejection_store: DerivedProposalRejectionStore | None = None,
        semantic_substrate: SemanticBlockPort | None = None,
    ) -> None:
        self.memory_substrate = memory_substrate
        self.baseline_store = baseline_store
        self.draft_store = draft_store
        self.rejection_store = rejection_store
        self.semantic_substrate = semantic_substrate

    def stage_and_promote(self, draft: PrecomputedDraftInput) -> ConsolidationResult:
        if not isinstance(draft, PrecomputedDraftInput):
            raise TypeError("draft must be PrecomputedDraftInput")

        # Resolve first so no draft is persisted for unauthorized support.
        memories = self.memory_substrate.get_by_ids(draft.supporting_memory_ids)
        resolved_ids = {memory.memory_id for memory in memories}
        expected_ids = set(draft.supporting_memory_ids)
        if resolved_ids != expected_ids or len(memories) != len(expected_ids):
            raise ValueError("external Memory support is incomplete or unauthorized")
        if self.semantic_substrate is not None:
            if not draft.selected_support:
                raise ValueError("semantic handoff requires exact immutable selected states")
            views = {memory.memory_id: memory for memory in memories}
            for selected in draft.selected_support:
                block = self.semantic_substrate.get_semantic_block_state(selected.state_id)
                current = self.semantic_substrate.get_semantic_block(selected.block_id)
                if block.block_id != selected.block_id or current.state_id != selected.state_id:
                    raise ValueError("semantic handoff selected state is stale or misaligned")
                view = views[selected.block_id]
                if view.content != block.content or set(view.source_refs) != set(block.raw_evidence_ids):
                    raise ValueError("semantic handoff disagrees with canonical block")
                if not all(self.semantic_substrate.get_evidence(ref).current_valid for ref in block.raw_evidence_ids):
                    raise ValueError("semantic handoff source is no longer current-valid")
        elif draft.selected_support:
            raise ValueError("selected semantic states require a validating semantic substrate")
        if self.rejection_store is not None:
            refs = tuple(sorted({ref for memory in memories for ref in memory.source_refs}))
            if not refs:
                raise ValueError("external interpretation must close over native sources")
            if self.rejection_store.active_match(
                region_id=draft.region_id, content=draft.content, source_refs=refs,
            ) is not None:
                raise RejectedDerivedProposalError("unchanged external interpretation was rejected")

        existing = self.draft_store.find_by_region_and_input(
            draft.region_id, draft.processing_input_id
        )
        if existing is not None:
            self._require_replay_equivalence(existing, draft)
            reconciled = self._reconcile_committed(existing)
            if reconciled is not None:
                return reconciled
        else:
            existing = self.draft_store.create(
                region_id=draft.region_id,
                candidate_content=draft.content,
                supporting_block_ids=draft.supporting_memory_ids,
                supporting_structure_ids=(),
                base_baseline=self.baseline_store.get_head(draft.region_id),
                interpretation_trace={},
                processing_input_id=draft.processing_input_id,
                support_kind="external_memory",
                selected_support=draft.selected_support,
            )

        core = LceCore(
            memory_substrate=self.memory_substrate,
            baseline_store=self.baseline_store,
            consolidator=_PrecomputedConsolidator(draft),
        )
        result = core.consolidate(
            draft.region_id,
            draft.supporting_memory_ids,
            context=draft.context,
        )
        self.draft_store.set_status(
            existing.worktree_id,
            "MERGED",
            merged_baseline_id=result.baseline.baseline_id,
        )
        return result

    def _require_replay_equivalence(
        self, existing: DraftRevision, draft: PrecomputedDraftInput
    ) -> None:
        if existing.support_kind != "external_memory":
            raise ValueError("processing_input_id collides with another draft support kind")
        if (
            existing.candidate_content != draft.content
            or not is_support_equivalent(
                left_memory_ids=existing.supporting_block_ids,
                right_memory_ids=draft.supporting_memory_ids,
                left_state_ids=tuple(item.state_id for item in existing.selected_support),
                right_state_ids=tuple(item.state_id for item in draft.selected_support),
                left_selected_support=existing.selected_support,
                right_selected_support=draft.selected_support,
            )
        ):
            raise ValueError("processing_input_id was reused with conflicting draft content")

    def _reconcile_committed(
        self, existing: DraftRevision
    ) -> ConsolidationResult | None:
        head = self.baseline_store.get_head(existing.region_id)
        if head is None:
            if existing.status == "MERGED":
                raise ValueError("merged external draft has no Baseline HEAD")
            return None
        if not is_content_equivalent(head.content, existing.candidate_content):
            if existing.status == "MERGED":
                raise ValueError("merged external draft disagrees with Baseline HEAD")
            return None
        if not is_support_equivalent(
            left_memory_ids=head.supporting_memory_ids,
            right_memory_ids=existing.supporting_block_ids,
            left_state_ids=head.supporting_state_ids,
            right_state_ids=tuple(item.state_id for item in existing.selected_support),
            left_selected_support=head.selected_support,
            right_selected_support=existing.selected_support,
        ):
            if existing.status == "MERGED":
                raise ValueError("merged external draft support disagrees with Baseline HEAD")
            return None
        if existing.status == "OPEN":
            self.draft_store.set_status(
                existing.worktree_id,
                "MERGED",
                merged_baseline_id=head.baseline_id,
            )
        return ConsolidationResult(
            baseline=head,
            revised=False,
            reason="PRECOMPUTED_DRAFT_RECONCILED",
        )
