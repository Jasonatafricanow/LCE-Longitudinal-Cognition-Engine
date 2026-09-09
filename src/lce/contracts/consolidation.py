"""Semantic consolidation contracts and ports for LCE.

A semantic consolidator takes an authorized set of related memory views
and an optional previous baseline, and emits a CandidateBaseline.
The candidate is NOT authoritative until validated and committed by LCE Core.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from lce.contracts.baseline import Baseline, validate_model_trace
from lce.contracts.external_memory import MemoryItemView


class LceError(Exception):
    """Base exception for all LCE Core errors."""


class UnauthorizedSourceError(LceError):
    """Raised when a candidate baseline references an unauthorized source memory ID."""


class EmptyNeighborhoodError(LceError):
    """Raised when consolidation is attempted with an empty memory set."""


@dataclass(frozen=True, slots=True)
class CandidateBaseline:
    """A proposed candidate understanding produced by a semantic model.

    Candidate understanding has zero canonical authority on its own.
    It must be verified against authorized input memory IDs by LCE Core.
    """

    content: str
    supporting_memory_ids: tuple[str, ...]
    model_trace: Mapping[str, object] = field(default_factory=dict)
    supporting_state_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.content, str) or not self.content.strip():
            raise ValueError("CandidateBaseline.content must be a non-empty string")
        if not isinstance(self.supporting_memory_ids, tuple):
            raise TypeError("CandidateBaseline.supporting_memory_ids must be a tuple of strings")
        if not self.supporting_memory_ids:
            raise ValueError("CandidateBaseline.supporting_memory_ids must not be empty")
        for mem_id in self.supporting_memory_ids:
            if not isinstance(mem_id, str) or not mem_id.strip():
                raise ValueError("each supporting_memory_id must be a non-empty string")
        if len(self.supporting_memory_ids) != len(set(self.supporting_memory_ids)):
            raise ValueError("CandidateBaseline.supporting_memory_ids contains duplicate memory IDs")
        if len(self.supporting_state_ids) != len(set(self.supporting_state_ids)):
            raise ValueError("CandidateBaseline.supporting_state_ids contains duplicate state IDs")
        validate_model_trace(self.model_trace)


@dataclass(frozen=True, slots=True)
class ConsolidationResult:
    """Outcome of an LCE consolidation operation."""

    baseline: Baseline
    revised: bool
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.baseline, Baseline):
            raise TypeError("baseline must be an instance of Baseline")
        if not isinstance(self.revised, bool):
            raise TypeError("revised must be a bool")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("reason must be a non-empty string")


@runtime_checkable
class SemanticConsolidatorPort(Protocol):
    """Injectable semantic consolidation port."""

    def consolidate(
        self,
        *,
        memories: tuple[MemoryItemView, ...],
        previous_baseline: Baseline | None,
        context: Mapping[str, object] | None = None,
    ) -> CandidateBaseline:
        """Produce a candidate compressed understanding from related memories."""
        ...
