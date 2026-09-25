"""Experiment Contracts and Data Definitions for Issue #24."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from lce.cognition.longitudinal_relation import (
    LongitudinalCandidate,
    LongitudinalObservation,
    LongitudinalRelationType,
    compute_block_content_hash,
)
from lce.reference_memory.contracts import SemanticBlock


@dataclass(frozen=True, slots=True)
class CorpusBlockRecord:
    """Canonical SemanticBlock representation stored in benchmark dataset."""

    block_id: str
    content: str
    occurred_start: datetime
    occurred_end: datetime
    domain: str
    thread_id: str
    projections: dict[str, Any]
    raw_evidence_ids: tuple[str, ...] = ("ev_001",)
    compiler_version: str = "v0.3-issue22"
    lineage_id: str = "main"

    def to_semantic_block(self) -> SemanticBlock:
        return SemanticBlock(
            block_id=self.block_id,
            content=self.content,
            raw_evidence_ids=self.raw_evidence_ids,
            occurred_start=self.occurred_start,
            occurred_end=self.occurred_end,
            compiler_version=self.compiler_version,
            lineage_id=self.lineage_id,
            metadata={"domain": self.domain, "thread_id": self.thread_id, "projections": self.projections},
        )


@dataclass(frozen=True, slots=True)
class GoldRelationRecord:
    """Ground truth longitudinal relation annotation between two blocks."""

    pair_id: str
    predecessor_block_id: str
    successor_block_id: str
    relation_type: LongitudinalRelationType
    affected_dimension: str
    prior_unknown_resolved: bool
    resolved_dimension: str | None
    outcome_or_current_state: str
    gold_evidence_spans: tuple[str, ...]
    split: str  # "dev" | "held_out"
    contrastive_family: str
    falsification_tags: tuple[str, ...]
    reason_competing_rejections: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AdjudicationOutput:
    """Structured response from L3 Selective Adjudication."""

    pair_id: str
    predecessor_block_id: str
    successor_block_id: str
    predicted_relation: LongitudinalRelationType
    affected_dimension: str
    prior_unknown_resolved: bool
    resolved_dimension: str | None
    outcome_or_current_state: str
    evidence_spans: tuple[str, ...]
    reason_competing_rejections: dict[str, str]
    confidence: float
    adjudication_trace: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    cached: bool


@dataclass(frozen=True, slots=True)
class CandidateFormationMetrics:
    level: str  # "L0", "L1", "L2"
    total_possible_pairs: int
    candidates_produced: int
    true_relation_pairs_count: int
    true_candidates_recalled: int
    recall: float
    candidates_per_block: float
    reduction_pct: float
    false_candidate_rate: float


@dataclass(frozen=True, slots=True)
class RelationAdjudicationMetrics:
    level: str  # "L0", "L1", "L2", "L3"
    total_evaluated: int
    overall_accuracy: float
    state_change_accuracy: float
    correction_retraction_accuracy: float
    state_vs_correction_confusion_rate: float
    uncertainty_resolution_accuracy: float
    persistence_accuracy: float
    unrelated_rejection_accuracy: float
    unknown_relation_rate: float
    confusion_matrix: dict[str, dict[str, int]]


@dataclass(frozen=True, slots=True)
class TemporalIntegrityMetrics:
    future_leakage_count: int
    reverse_time_errors: int
    immutability_violation_count: int
    unsupported_unknown_closure_count: int
    passed_all: bool


@dataclass(frozen=True, slots=True)
class CostMetrics:
    total_adjudication_calls: int
    calls_per_block: float
    tokens_per_accepted_relation: float
    avg_latency_ms: float


__all__ = [
    "LongitudinalRelationType",
    "LongitudinalCandidate",
    "LongitudinalObservation",
    "compute_block_content_hash",
    "CorpusBlockRecord",
    "GoldRelationRecord",
    "AdjudicationOutput",
    "CandidateFormationMetrics",
    "RelationAdjudicationMetrics",
    "TemporalIntegrityMetrics",
    "CostMetrics",
]
