"""Intake for already-reasoned cognition over external Memory.

This path is deliberately separate from Semantic Block structure discovery.
It records the supplied cognition as a durable DraftRevision first, then
promotes it through LCE Core without invoking another semantic model.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from lce.cognition.worktree import DraftRevision, DraftRevisionStore
from lce.contracts.baseline import Baseline
from lce.contracts.consolidation import CandidateBaseline, ConsolidationResult
from lce.contracts.external_memory import MemoryItemView, MemorySubstratePort
from lce.core.engine import LceCore
from lce.core.equivalence import is_content_equivalent
from lce.store.interface import BaselineStorePort


@dataclass(frozen=True, slots=True)
class PrecomputedDraftInput:
    """One bounded interpretation already formed by an upstream working layer."""

    region_id: str
    content: str
    supporting_memory_ids: tuple[str, ...]
    processing_input_id: str
    context: Mapping[str, object] = field(default_factory=dict)

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
        )


class PrecomputedDraftIntake:
    """Persist an upstream interpretation as OPEN draft before Baseline promotion."""

    def __init__(
        self,
        *,
        memory_substrate: MemorySubstratePort,
        baseline_store: BaselineStorePort,
        draft_store: DraftRevisionStore,
    ) -> None:
        self.memory_substrate = memory_substrate
        self.baseline_store = baseline_store
        self.draft_store = draft_store

    def stage_and_promote(self, draft: PrecomputedDraftInput) -> ConsolidationResult:
        if not isinstance(draft, PrecomputedDraftInput):
            raise TypeError("draft must be PrecomputedDraftInput")

        # Resolve first so no draft is persisted for unauthorized support.
        memories = self.memory_substrate.get_by_ids(draft.supporting_memory_ids)
        resolved_ids = {memory.memory_id for memory in memories}
        expected_ids = set(draft.supporting_memory_ids)
        if resolved_ids != expected_ids or len(memories) != len(expected_ids):
            raise ValueError("external Memory support is incomplete or unauthorized")

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
            or existing.supporting_block_ids != draft.supporting_memory_ids
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
