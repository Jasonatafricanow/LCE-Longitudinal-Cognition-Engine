"""LCE Core engine orchestrating baseline formation, revision, and audit."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime

from lce.contracts.baseline import (
    Baseline,
    BaselineHistory,
    compute_content_hash,
)
from lce.contracts.consolidation import (
    ConsolidationResult,
    EmptyNeighborhoodError,
    SemanticConsolidatorPort,
    UnauthorizedSourceError,
)
from lce.contracts.external_memory import MemorySubstratePort
from lce.core.equivalence import is_content_equivalent
from lce.store.interface import BaselineStorePort


class LceCore:
    """Minimal Longitudinal Logical Understanding Core.

    Orchestrates the lifecycle of learned long-term Baselines over
    externally discovered Memory point clouds without owning raw Memory
    or vector infrastructure.
    """

    def __init__(
        self,
        *,
        memory_substrate: MemorySubstratePort,
        baseline_store: BaselineStorePort,
        consolidator: SemanticConsolidatorPort,
    ) -> None:
        self._memory_substrate = memory_substrate
        self._baseline_store = baseline_store
        self._consolidator = consolidator

    def consolidate(
        self,
        region_id: str,
        memory_ids: tuple[str, ...],
        context: Mapping[str, object] | None = None,
    ) -> ConsolidationResult:
        """Consolidate related memories into a durable learned baseline.

        Steps:
          1. Resolve memory item views via MemorySubstratePort.
          2. Fetch current HEAD baseline.
          3. Produce candidate baseline via SemanticConsolidatorPort.
          4. Validate supporting references (fail closed if unknown source).
          5. Check normalized content equivalence against current baseline.
          6. Atomically persist new revision if meaningfully updated.
        """
        if not isinstance(region_id, str) or not region_id.strip():
            raise ValueError("region_id must be a non-empty string")
        if not isinstance(memory_ids, tuple) or not memory_ids:
            raise EmptyNeighborhoodError("memory_ids must be a non-empty tuple")

        # 1. Fetch authorized views
        memories = self._memory_substrate.get_by_ids(memory_ids)
        if not memories:
            raise EmptyNeighborhoodError(
                f"None of the supplied memory_ids were found in substrate: {memory_ids}"
            )

        authorized_memory_ids = {m.memory_id for m in memories}

        # 2. Fetch current HEAD
        current_head = self._baseline_store.get_head(region_id)

        # 3. Request candidate understanding from consolidator
        candidate = self._consolidator.consolidate(
            memories=memories,
            previous_baseline=current_head,
            context=context,
        )

        # 4. Enforce fail-closed source validation
        candidate_source_set = set(candidate.supporting_memory_ids)
        unauthorized = candidate_source_set - authorized_memory_ids
        if unauthorized:
            raise UnauthorizedSourceError(
                f"Candidate baseline referenced unauthorized memory IDs: {sorted(unauthorized)} "
                f"(authorized input set: {sorted(authorized_memory_ids)})"
            )

        # 5. Evaluate content equivalence if previous baseline exists
        if current_head is not None and is_content_equivalent(
            candidate.content, current_head.content
        ):
            return ConsolidationResult(
                baseline=current_head,
                revised=False,
                reason="NO_SEMANTIC_CHANGE",
            )

        # 6. Build new revision
        baseline_id = f"base_{uuid.uuid4().hex}"
        revision_number = 1 if current_head is None else current_head.revision_number + 1
        previous_baseline_id = None if current_head is None else current_head.baseline_id
        content_hash = compute_content_hash(candidate.content)
        created_at = datetime.now(UTC)

        new_baseline = Baseline(
            baseline_id=baseline_id,
            region_id=region_id,
            revision_number=revision_number,
            content=candidate.content,
            content_hash=content_hash,
            supporting_memory_ids=candidate.supporting_memory_ids,
            created_at=created_at,
            previous_baseline_id=previous_baseline_id,
            model_trace=candidate.model_trace,
            supporting_state_ids=candidate.supporting_state_ids,
            selected_support=candidate.selected_support,
        )

        # Atomically commit revision and advance HEAD
        self._baseline_store.save_revision(new_baseline)

        reason = "INITIAL_CREATION" if current_head is None else "MEANINGFUL_UPDATE"
        return ConsolidationResult(
            baseline=new_baseline,
            revised=True,
            reason=reason,
        )

    def get_current_baseline(self, region_id: str) -> Baseline | None:
        """Fetch current HEAD baseline for the region."""
        return self._baseline_store.get_head(region_id)

    def get_history(self, region_id: str, limit: int | None = None) -> BaselineHistory:
        """Fetch historical revisions for audit and inspection."""
        return self._baseline_store.get_history(region_id, limit=limit)
