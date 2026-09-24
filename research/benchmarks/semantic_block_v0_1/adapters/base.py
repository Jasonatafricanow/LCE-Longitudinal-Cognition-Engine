"""Base adapter and input preparation for Issue #19 benchmark arms."""

from __future__ import annotations

import abc
from datetime import datetime
from typing import Any

from research.benchmarks.semantic_block_v0_1.contracts import (
    PredictionRecord,
    PublicRelation,
    PublicSemanticBlock,
    SourceSpan,
    VisibleCaseInput,
)


def _parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def prepare_visible_input(case: dict[str, Any], cutoff: str) -> VisibleCaseInput:
    """Prepare strictly cutoff-visible evidence and bounded context for a case."""
    cutoff_dt = _parse_iso(cutoff)
    raw_evidence = case["raw_evidence"]
    context_ids = set(case.get("context_evidence_ids", []))

    visible_all: list[dict[str, Any]] = []
    for ev in raw_evidence:
        if _parse_iso(ev["available_at"]) <= cutoff_dt:
            visible_all.append(ev)

    # Sort strictly by (available_at, occurred_at, evidence_id)
    visible_all.sort(
        key=lambda e: (_parse_iso(e["available_at"]), _parse_iso(e["occurred_at"]), e["evidence_id"])
    )

    # Separate primary visible evidence vs prior context evidence
    visible_evidence: list[dict[str, Any]] = []
    context_evidence: list[dict[str, Any]] = []
    for ev in visible_all:
        if ev["evidence_id"] in context_ids:
            context_evidence.append(ev)
        else:
            visible_evidence.append(ev)

    # Bounded context: at most 4 prior evidence records
    bounded_context = context_evidence[-4:]

    return VisibleCaseInput(
        case_id=case["case_id"],
        family=case["family"],
        variant=case["variant"],
        split=case["split"],
        cutoff=cutoff,
        visible_evidence=visible_evidence,
        context_evidence=bounded_context,
        entity_registry=dict(case.get("entity_registry", {})),
    )


def verify_span(
    evidence_id: str,
    char_start: int,
    char_end: int,
    text: str,
    evidence_map: dict[str, dict[str, Any]],
) -> SourceSpan | None:
    """Verify exact character span slicing against raw evidence content."""
    if evidence_id not in evidence_map:
        return None
    raw_content = evidence_map[evidence_id]["content"]
    if not (0 <= char_start < char_end <= len(raw_content)):
        # Attempt fallback to exact substring index if char coords were 0 or slightly offset
        idx = raw_content.find(text)
        if idx >= 0:
            return SourceSpan(
                evidence_id=evidence_id,
                char_start=idx,
                char_end=idx + len(text),
                text=text,
            )
        return None
    sliced = raw_content[char_start:char_end]
    if sliced != text:
        # Check if text exists elsewhere uniquely
        idx = raw_content.find(text)
        if idx >= 0:
            return SourceSpan(
                evidence_id=evidence_id,
                char_start=idx,
                char_end=idx + len(text),
                text=text,
            )
        return None
    return SourceSpan(
        evidence_id=evidence_id,
        char_start=char_start,
        char_end=char_end,
        text=text,
    )


class BaseCompilerAdapter(abc.ABC):
    """Abstract base class for all compiler arms (A, B, C, D)."""

    def __init__(self, arm_id: str) -> None:
        self.arm_id = arm_id

    @abc.abstractmethod
    def compile(self, case_input: VisibleCaseInput) -> PredictionRecord:
        """Compile cutoff-visible inputs into a sealed PredictionRecord."""
        raise NotImplementedError
