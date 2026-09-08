"""Ports and decisions for the bounded Semantic Block compiler."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from lce.reference_memory.contracts import RawEvidence, SemanticBlock


@dataclass(frozen=True, slots=True)
class SemanticGroup:
    subject: str
    cognition: str

    def __post_init__(self) -> None:
        if not self.subject.strip() or not self.cognition.strip():
            raise ValueError("semantic groups require subject and cognition")


@dataclass(frozen=True, slots=True)
class SemanticDecision:
    """Provider proposal; the compiler alone mutates canonical block state."""

    action: str
    subject: str
    cognition: str
    groups: tuple[SemanticGroup, ...] = ()
    recap_block_ids: tuple[str, ...] = ()
    new_information: str | None = None
    reason: str = ""

    def __post_init__(self) -> None:
        if self.action not in {"NEW", "CONTINUE", "MERGE", "SPLIT", "AUXILIARY", "RECAP"}:
            raise ValueError(f"unsupported semantic action: {self.action}")
        if not self.subject.strip() or not self.cognition.strip():
            raise ValueError("semantic decisions require subject and cognition")
        if self.action == "SPLIT" and len(self.groups) < 2:
            raise ValueError("SPLIT requires at least two semantic groups")

    def as_mapping(self) -> dict[str, object]:
        return {
            "action": self.action,
            "subject": self.subject,
            "cognition": self.cognition,
            "groups": [{"subject": group.subject, "cognition": group.cognition} for group in self.groups],
            "recap_block_ids": list(self.recap_block_ids),
            "new_information": self.new_information,
            "reason": self.reason,
        }


@runtime_checkable
class SemanticDecisionProvider(Protocol):
    def decide(
        self,
        *,
        evidence: RawEvidence,
        open_block: SemanticBlock | None,
        recent_blocks: Sequence[SemanticBlock],
    ) -> SemanticDecision:
        """Propose bounded semantic handling for one Raw Evidence unit."""
        ...
