"""Pure accepted Understanding read API."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from lce.reference_memory.sqlite import ReferenceMemoryStore
from lce.store.interface import BaselineStorePort


@dataclass(frozen=True, slots=True)
class UnderstandingView:
    content: str
    baseline_id: str
    region_id: str
    revision_number: int
    supporting_semantic_block_ids: tuple[str, ...]
    supporting_source_refs: tuple[str, ...]
    applicability: str | None = None
    unresolved: str | None = None
    status: str = "ACCEPTED"
    worktree_status: str | None = None


class AcceptedUnderstandingReadAPI:
    """Read-only, no-reasoning view over current-valid Baseline HEADs."""

    def __init__(self, *, memory: ReferenceMemoryStore, baseline_store: BaselineStorePort) -> None:
        self.memory = memory
        self.baseline_store = baseline_store

    def query(self, current_context: str | Mapping[str, object] | None) -> tuple[UnderstandingView, ...]:
        query_text = current_context if isinstance(current_context, str) else json_context(current_context)
        tokens = set(re.findall(r"\w+", query_text.casefold()))
        views: list[UnderstandingView] = []
        for region_id in self.baseline_store.list_regions():
            baseline = self.baseline_store.get_head(region_id)
            if baseline is None:
                continue
            blocks = []
            valid = True
            source_refs: set[str] = set()
            for block_id in baseline.supporting_memory_ids:
                try:
                    block = self.memory.get_semantic_block(block_id)
                except KeyError:
                    valid = False
                    break
                if not all(self.memory.get_evidence(evidence_id).current_valid for evidence_id in block.raw_evidence_ids):
                    valid = False
                    break
                blocks.append(block)
                source_refs.update(block.raw_evidence_ids)
            if not valid or not blocks:
                continue
            searchable = " ".join([baseline.content, *(block.content for block in blocks)]).casefold()
            if tokens and not (tokens & set(re.findall(r"\w+", searchable))):
                continue
            views.append(
                UnderstandingView(
                    content=baseline.content,
                    baseline_id=baseline.baseline_id,
                    region_id=baseline.region_id,
                    revision_number=baseline.revision_number,
                    supporting_semantic_block_ids=baseline.supporting_memory_ids,
                    supporting_source_refs=tuple(sorted(source_refs)),
                )
            )
        return tuple(sorted(views, key=lambda view: (view.region_id, view.revision_number)))


def json_context(context: Mapping[str, object] | None) -> str:
    if context is None:
        return ""
    return " ".join(str(value) for value in context.values())
