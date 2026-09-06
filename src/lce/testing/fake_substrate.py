"""Fake in-memory implementation of MemorySubstratePort for tests."""

from __future__ import annotations

from collections.abc import Mapping

from lce.contracts.external_memory import MemoryItemView, MemorySubstratePort


class FakeMemorySubstrate(MemorySubstratePort):
    """In-memory fake substrate simulating external memory points.

    Hard boundary: this class is strictly a test fixture. It does NOT
    implement a fake embedding model or vector database.
    """

    def __init__(self) -> None:
        self._memories: dict[str, MemoryItemView] = {}

    def add_memory(
        self,
        memory_id: str,
        content: str,
        source_refs: tuple[str, ...],
        retrieval_metadata: Mapping[str, object] | None = None,
    ) -> MemoryItemView:
        """Helper to register an externally owned memory item."""
        view = MemoryItemView(
            memory_id=memory_id,
            content=content,
            source_refs=source_refs,
            retrieval_metadata=retrieval_metadata or {},
        )
        self._memories[memory_id] = view
        return view

    def add_item(self, item: MemoryItemView) -> None:
        """Register a pre-constructed MemoryItemView."""
        self._memories[item.memory_id] = item

    def update_metadata(
        self, memory_id: str, retrieval_metadata: Mapping[str, object]
    ) -> None:
        """Simulate change in vector coordinates or similarity scores (T12)."""
        if memory_id not in self._memories:
            raise KeyError(f"memory_id '{memory_id}' not found in fake substrate")
        current = self._memories[memory_id]
        self._memories[memory_id] = MemoryItemView(
            memory_id=current.memory_id,
            content=current.content,
            source_refs=current.source_refs,
            retrieval_metadata=retrieval_metadata,
        )

    def get_by_ids(self, memory_ids: tuple[str, ...]) -> tuple[MemoryItemView, ...]:
        """Resolve memory views by their stable IDs."""
        results: list[MemoryItemView] = []
        for m_id in memory_ids:
            if m_id in self._memories:
                results.append(self._memories[m_id])
        return tuple(results)
