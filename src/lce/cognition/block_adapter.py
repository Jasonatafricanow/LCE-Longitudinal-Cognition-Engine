"""Adapter from canonical Semantic Blocks to the existing LCE Core port."""

from __future__ import annotations

from lce.contracts.external_memory import MemoryItemView, MemorySubstratePort
from lce.reference_memory.contracts import AuthorizedSelectedSupport, SemanticBlockPort


class SemanticBlockMemoryAdapter(MemorySubstratePort):
    def __init__(
        self,
        memory: SemanticBlockPort,
        *,
        selected_support: tuple[AuthorizedSelectedSupport, ...] = (),
    ) -> None:
        self.memory = memory
        self.selected_support = tuple(selected_support)
        self._selected_by_block = {item.block_id: item for item in self.selected_support}
        if len(self._selected_by_block) != len(self.selected_support):
            raise ValueError("selected support contains duplicate block IDs")

    def get_by_ids(self, memory_ids: tuple[str, ...]) -> tuple[MemoryItemView, ...]:
        items: list[MemoryItemView] = []
        for block_id in memory_ids:
            try:
                selected = self._selected_by_block.get(block_id)
                block = (
                    self.memory.get_semantic_block_state(selected.state_id)
                    if selected is not None
                    else self.memory.get_semantic_block(block_id)
                )
            except KeyError:
                continue
            if block.block_id != block_id:
                raise ValueError("selected state does not belong to the requested Semantic Block")
            if not all(self.memory.get_evidence(evidence_id).current_valid for evidence_id in block.raw_evidence_ids):
                continue
            items.append(
                MemoryItemView(
                    memory_id=block.block_id,
                    content=block.content,
                    source_refs=block.raw_evidence_ids,
                    retrieval_metadata={
                        "kind": "semantic_block",
                        "compiler_version": block.compiler_version,
                        "state_id": block.state_id,
                    },
                )
            )
        return tuple(items)
