"""Scriptable fake consolidator for deterministic LCE tests."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from lce.contracts.baseline import Baseline
from lce.contracts.consolidation import CandidateBaseline, SemanticConsolidatorPort
from lce.contracts.external_memory import MemoryItemView


class ScriptableFakeConsolidator(SemanticConsolidatorPort):
    """Test consolidator with scripted responses or deterministic fallback."""

    def __init__(self) -> None:
        self._queue: list[CandidateBaseline] = []
        self._calls: list[dict[str, Any]] = []

    def queue_response(self, candidate: CandidateBaseline) -> None:
        """Queue a specific CandidateBaseline for the next consolidate() call."""
        self._queue.append(candidate)

    @property
    def calls(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._calls)

    def consolidate(
        self,
        *,
        memories: tuple[MemoryItemView, ...],
        previous_baseline: Baseline | None,
        context: Mapping[str, object] | None = None,
    ) -> CandidateBaseline:
        self._calls.append(
            {
                "memories": memories,
                "previous_baseline": previous_baseline,
                "context": context,
            }
        )

        if self._queue:
            return self._queue.pop(0)

        # Deterministic default compression:
        # Concatenate unique propositions in memory order
        all_ids = tuple(m.memory_id for m in memories)
        compressed_text = " | ".join(m.content for m in memories)
        return CandidateBaseline(
            content=compressed_text,
            supporting_memory_ids=all_ids,
            model_trace={"model": "fake-consolidator", "version": "1.0"},
        )
