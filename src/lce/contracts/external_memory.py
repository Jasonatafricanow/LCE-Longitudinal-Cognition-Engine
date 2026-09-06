"""Read-only external memory substrate contracts for LCE.

LCE does NOT own raw memory items or vector coordinates.
This module defines the consumer-side dependency contract required by LCE
to inspect externally supplied memories and their stable identities.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class MemoryItemView:
    """Read-only view of an externally owned Memory item.

    Hard invariants:
      - memory_id: Stable, unique identifier of the memory item.
      - content: Textual representation of the proposition/memory.
      - source_refs: Immutable references to original Evidence / provenance.
      - retrieval_metadata: Optional transient retrieval attributes (e.g.
        similarity score, vector distance, cluster tag). Transient metadata
        MUST NOT become the durable identity of Baseline support.
    """

    memory_id: str
    content: str
    source_refs: tuple[str, ...]
    retrieval_metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.memory_id, str) or not self.memory_id.strip():
            raise ValueError("memory_id must be a non-empty string")
        if not isinstance(self.content, str) or not self.content.strip():
            raise ValueError("content must be a non-empty string")
        if not isinstance(self.source_refs, tuple):
            raise TypeError("source_refs must be a tuple of strings")
        if not self.source_refs:
            raise ValueError("source_refs must not be empty (provenance required)")
        for ref in self.source_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise ValueError("each source_ref must be a non-empty string")
        if not isinstance(self.retrieval_metadata, Mapping):
            raise TypeError("retrieval_metadata must be a Mapping")


@runtime_checkable
class MemorySubstratePort(Protocol):
    """Consumer-side protocol for accessing externally discovered memory items.

    Point cloud / similarity neighborhood discovery is performed by the external
    vector/memory substrate; LCE receives the identified memory IDs and resolves
    their read-only views via this port.
    """

    def get_by_ids(self, memory_ids: tuple[str, ...]) -> tuple[MemoryItemView, ...]:
        """Fetch memory item views for the specified stable memory IDs.

        Returns only the items that exist in the substrate. Order may vary.
        """
        ...
