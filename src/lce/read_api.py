"""Pure accepted Understanding read API."""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass

from lce.cognition.rejection import DerivedProposalRejectionStore
from lce.reference_memory.contracts import AuthorizedSelectedSupport, SemanticBlockPort
from lce.store.interface import BaselineStorePort


def _is_cjk(char: str) -> bool:
    code = ord(char)
    return (
        0x3400 <= code <= 0x4DBF
        or 0x4E00 <= code <= 0x9FFF
        or 0xF900 <= code <= 0xFAFF
    )


def lexical_tokens(text: str) -> tuple[str, ...]:
    """Normalize Latin/digits and expose CJK runs plus overlapping bigrams."""
    normalized = unicodedata.normalize("NFKC", text).casefold()
    tokens: list[str] = []
    word: list[str] = []
    cjk: list[str] = []

    def flush_word() -> None:
        if word:
            tokens.append("".join(word))
            word.clear()

    def flush_cjk() -> None:
        if not cjk:
            return
        run = "".join(cjk)
        if len(run) == 1:
            tokens.append(run)
        else:
            tokens.append(run)
            tokens.extend(
                run[index : index + 2]
                for index in range(len(run) - 1)
            )
        cjk.clear()

    for char in normalized:
        if _is_cjk(char):
            flush_word()
            cjk.append(char)
        elif char.isalnum():
            flush_cjk()
            word.append(char)
        else:
            flush_word()
            flush_cjk()
    flush_word()
    flush_cjk()
    return tuple(tokens)


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
    supporting_semantic_block_state_ids: tuple[str, ...] = ()


class AcceptedUnderstandingReadAPI:
    """Read-only, no-reasoning view over current-valid Baseline HEADs."""

    def __init__(
        self,
        *,
        memory: SemanticBlockPort,
        baseline_store: BaselineStorePort,
        rejection_store: DerivedProposalRejectionStore | None = None,
    ) -> None:
        self.memory = memory
        self.baseline_store = baseline_store
        self.rejection_store = rejection_store

    def query(self, current_context: str | Mapping[str, object] | None) -> tuple[UnderstandingView, ...]:
        query_text = (
            current_context
            if isinstance(current_context, str)
            else json_context(current_context)
        )
        tokens = set(lexical_tokens(query_text))
        views: list[UnderstandingView] = []
        for region_id in self.baseline_store.list_regions():
            baseline = self.baseline_store.get_head(region_id)
            if baseline is None:
                continue
            blocks = []
            valid = True
            source_refs: set[str] = set()
            selected_support = baseline.selected_support
            if selected_support:
                if tuple(item.block_id for item in selected_support) != baseline.supporting_memory_ids:
                    continue
            elif baseline.supporting_state_ids:
                # A legacy baseline with unaligned state IDs cannot be safely served.
                continue
            served_state_ids: list[str] = []
            selected_items = selected_support or tuple(
                AuthorizedSelectedSupport(block_id=block_id, state_id="legacy-current")
                for block_id in baseline.supporting_memory_ids
            )
            for selected in selected_items:
                block_id = selected.block_id
                try:
                    block = (
                        self.memory.get_semantic_block_state(selected.state_id)
                        if baseline.selected_support
                        else self.memory.get_semantic_block(block_id)
                    )
                except KeyError:
                    valid = False
                    break
                if block.block_id != block_id:
                    valid = False
                    break
                try:
                    evidence_valid = all(
                        self.memory.get_evidence(evidence_id).current_valid
                        for evidence_id in block.raw_evidence_ids
                    )
                except KeyError:
                    valid = False
                    break
                if not evidence_valid:
                    valid = False
                    break
                blocks.append(block)
                source_refs.update(block.raw_evidence_ids)
                if block.state_id:
                    served_state_ids.append(block.state_id)
            if not valid or not blocks:
                continue
            searchable = " ".join(
                [baseline.content, *(block.content for block in blocks)]
            )
            if tokens and not (
                tokens & set(lexical_tokens(searchable))
            ):
                continue
            if (
                self.rejection_store is not None
                and self.rejection_store.active_match(
                    region_id=baseline.region_id,
                    content=baseline.content,
                    source_refs=tuple(sorted(source_refs)),
                )
                is not None
            ):
                continue
            views.append(
                UnderstandingView(
                    content=baseline.content,
                    baseline_id=baseline.baseline_id,
                    region_id=baseline.region_id,
                    revision_number=baseline.revision_number,
                    supporting_semantic_block_ids=baseline.supporting_memory_ids,
                    supporting_semantic_block_state_ids=tuple(served_state_ids),
                    supporting_source_refs=tuple(sorted(source_refs)),
                )
            )
        return tuple(sorted(views, key=lambda view: (view.region_id, view.revision_number)))


def json_context(context: Mapping[str, object] | None) -> str:
    if context is None:
        return ""
    return " ".join(str(value) for value in context.values())
