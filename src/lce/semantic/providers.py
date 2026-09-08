"""Dependency-free semantic decision provider for standalone operation."""

from __future__ import annotations

import re
from collections.abc import Sequence

from lce.reference_memory.contracts import RawEvidence, SemanticBlock
from lce.semantic.contracts import SemanticDecision, SemanticGroup


def _subject(value: object, fallback: str) -> str:
    text = str(value).strip() if value is not None else ""
    return text or fallback


def _same_subject(left: str, right: str) -> bool:
    def normalize(value: str) -> str:
        return re.sub(r"\W+", "", value, flags=re.UNICODE).casefold()
    a, b = normalize(left), normalize(right)
    return bool(a and b and (a == b or a in b or b in a))


class RuleBasedSemanticProvider:
    """Small deterministic fallback; model-backed providers can replace it."""

    def decide(
        self,
        *,
        evidence: RawEvidence,
        open_block: SemanticBlock | None,
        recent_blocks: Sequence[SemanticBlock],
    ) -> SemanticDecision:
        metadata = evidence.provenance
        topic = _subject(metadata.get("topic"), "general")
        semantic_content = str(metadata.get("semantic_content") or evidence.content).strip()
        topics = metadata.get("topics")
        if isinstance(topics, (list, tuple)) and len(topics) >= 2:
            groups = tuple(
                SemanticGroup(_subject(item, f"topic-{index}"), semantic_content)
                for index, item in enumerate(topics, start=1)
            )
            return SemanticDecision("SPLIT", topic, semantic_content, groups=groups, reason="input declares distinct topics")

        matching = next(
            (
                block
                for block in reversed(tuple(recent_blocks))
                if _same_subject(str(block.metadata.get("subject", "")), topic)
            ),
            None,
        )
        if metadata.get("recap") is True and matching is not None:
            new_information = metadata.get("new_information")
            return SemanticDecision(
                "RECAP",
                topic,
                semantic_content,
                recap_block_ids=(matching.block_id,),
                new_information=str(new_information).strip() if new_information else None,
                reason="semantic recap matched an existing block",
            )
        if open_block is not None and _same_subject(str(open_block.metadata.get("subject", "")), topic):
            return SemanticDecision("CONTINUE", topic, semantic_content, reason="semantic subject continues")
        return SemanticDecision("NEW", topic, semantic_content, reason="new semantic subject")
