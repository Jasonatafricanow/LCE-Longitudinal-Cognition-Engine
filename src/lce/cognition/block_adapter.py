"""Adapter from canonical Semantic Blocks to the existing LCE Core port."""

from __future__ import annotations

from lce.contracts.external_memory import MemoryItemView, MemorySubstratePort
from lce.reference_memory.sqlite import ReferenceMemoryStore


class SemanticBlockMemoryAdapter(MemorySubstratePort):
    def __init__(self, memory: ReferenceMemoryStore) -> None:
        self.memory = memory

    def get_by_ids(self, memory_ids: tuple[str, ...]) -> tuple[MemoryItemView, ...]:
        items: list[MemoryItemView] = []
        for block_id in memory_ids:
            try:
                block = self.memory.get_semantic_block(block_id)
            except KeyError:
                continue
            if not all(self.memory.get_evidence(evidence_id).current_valid for evidence_id in block.raw_evidence_ids):
                continue
            items.append(
                MemoryItemView(
                    memory_id=block.block_id,
                    content=block.content,
                    source_refs=block.raw_evidence_ids,
                    retrieval_metadata={"kind": "semantic_block", "compiler_version": block.compiler_version},
                )
            )
        return tuple(items)
