"""Contracts and schemas for the Issue #19 SemanticBlock Benchmark.

Defines public block structures, relations, case input representations,
prediction containers, and query operation types.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Mapping


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class SourceSpan:
    evidence_id: str
    char_start: int
    char_end: int
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "text": self.text,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SourceSpan:
        return cls(
            evidence_id=d["evidence_id"],
            char_start=d["char_start"],
            char_end=d["char_end"],
            text=d["text"],
        )


@dataclass(frozen=True, slots=True)
class PublicSemanticBlock:
    """Public SemanticBlock shape as defined in Issue #18 and #19 protocol."""
    block_id: str
    state_id: str
    state_available_at: str
    canonical_content: str
    predicate: str
    kind: str
    participants: dict[str, str]
    holder: str
    utterer: str
    attribution_mode: str
    polarity: str
    modality: str
    epistemic_hedge: str
    valid_time: str
    time_precision: str
    entity_status: str
    uncertainty: str
    independent_support_count: int
    source_spans: list[SourceSpan]
    lineage_id: str
    compiler_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "block_id": self.block_id,
            "state_id": self.state_id,
            "state_available_at": self.state_available_at,
            "canonical_content": self.canonical_content,
            "predicate": self.predicate,
            "kind": self.kind,
            "participants": dict(self.participants),
            "holder": self.holder,
            "utterer": self.utterer,
            "attribution_mode": self.attribution_mode,
            "polarity": self.polarity,
            "modality": self.modality,
            "epistemic_hedge": self.epistemic_hedge,
            "valid_time": self.valid_time,
            "time_precision": self.time_precision,
            "entity_status": self.entity_status,
            "uncertainty": self.uncertainty,
            "independent_support_count": self.independent_support_count,
            "source_spans": [s.to_dict() for s in self.source_spans],
            "lineage_id": self.lineage_id,
            "compiler_version": self.compiler_version,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PublicSemanticBlock:
        return cls(
            block_id=d["block_id"],
            state_id=d["state_id"],
            state_available_at=d["state_available_at"],
            canonical_content=d["canonical_content"],
            predicate=d["predicate"],
            kind=d["kind"],
            participants=dict(d.get("participants", {})),
            holder=d["holder"],
            utterer=d["utterer"],
            attribution_mode=d["attribution_mode"],
            polarity=d["polarity"],
            modality=d["modality"],
            epistemic_hedge=d["epistemic_hedge"],
            valid_time=d["valid_time"],
            time_precision=d["time_precision"],
            entity_status=d["entity_status"],
            uncertainty=d["uncertainty"],
            independent_support_count=d.get("independent_support_count", 1),
            source_spans=[SourceSpan.from_dict(s) for s in d.get("source_spans", [])],
            lineage_id=d["lineage_id"],
            compiler_version=d["compiler_version"],
        )


@dataclass(frozen=True, slots=True)
class PublicRelation:
    """Public typed relation linking two visible block states."""
    type: str  # CAUSE | SAME_ENTITY | BEFORE
    direction: str  # "directed"
    source_state_id: str
    target_state_id: str
    basis: str  # e.g. "explicit_connective", "authorized_registry", "explicit_temporal"
    cue_span: SourceSpan | None
    traversal_allowed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "direction": self.direction,
            "source_state_id": self.source_state_id,
            "target_state_id": self.target_state_id,
            "basis": self.basis,
            "cue_span": self.cue_span.to_dict() if self.cue_span else None,
            "traversal_allowed": self.traversal_allowed,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PublicRelation:
        cue = SourceSpan.from_dict(d["cue_span"]) if d.get("cue_span") else None
        return cls(
            type=d["type"],
            direction=d["direction"],
            source_state_id=d["source_state_id"],
            target_state_id=d["target_state_id"],
            basis=d["basis"],
            cue_span=cue,
            traversal_allowed=d["traversal_allowed"],
        )


@dataclass(frozen=True, slots=True)
class PredictionRecord:
    """Prediction record produced for a (case_id, cutoff) pair."""
    case_id: str
    cutoff: str
    arm_id: str
    manifest_id: str
    blocks: list[PublicSemanticBlock]
    relations: list[PublicRelation]
    call_count: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "cutoff": self.cutoff,
            "arm_id": self.arm_id,
            "manifest_id": self.manifest_id,
            "blocks": [b.to_dict() for b in self.blocks],
            "relations": [r.to_dict() for r in self.relations],
            "call_count": self.call_count,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "latency_ms": self.latency_ms,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PredictionRecord:
        return cls(
            case_id=d["case_id"],
            cutoff=d["cutoff"],
            arm_id=d["arm_id"],
            manifest_id=d["manifest_id"],
            blocks=[PublicSemanticBlock.from_dict(b) for b in d.get("blocks", [])],
            relations=[PublicRelation.from_dict(r) for r in d.get("relations", [])],
            call_count=d.get("call_count", 0),
            prompt_tokens=d.get("prompt_tokens", 0),
            completion_tokens=d.get("completion_tokens", 0),
            total_tokens=d.get("total_tokens", 0),
            latency_ms=d.get("latency_ms", 0.0),
        )


@dataclass(frozen=True, slots=True)
class VisibleCaseInput:
    """Input supplied to an arm compiler for a specific cutoff."""
    case_id: str
    family: str
    variant: str
    split: str
    cutoff: str
    visible_evidence: list[dict[str, Any]]
    context_evidence: list[dict[str, Any]]
    entity_registry: dict[str, str]
