"""Issue #25 contracts: production-shaped Path B with two orthogonal axes.

Key design changes from Issue #24:
  - No thread_id, domain, correction_nature, or gold-relation oracle fields.
  - Input uses production-shaped MR Memory + provenance + dual time axes.
  - Adjudication output separates longitudinal relation from knowledge effect
    so that STATE_CHANGE + prior_unknown_resolved = true is representable.
  - Only Stage 1 discovered candidates enter the adjudicator.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from lce.reference_memory.contracts import SemanticBlock


# ---------------------------------------------------------------------------
# Axis A: Longitudinal Relation
# ---------------------------------------------------------------------------

class LongitudinalRelation(str, Enum):
    """Bounded longitudinal relation type (Axis A of adjudication)."""
    STATE_CHANGE = "STATE_CHANGE"
    CORRECTION_RETRACTION = "CORRECTION_RETRACTION"
    PERSISTENCE_CONFIRMATION = "PERSISTENCE_CONFIRMATION"
    UNRELATED = "UNRELATED"
    UNKNOWN_RELATION = "UNKNOWN_RELATION"


# ---------------------------------------------------------------------------
# Axis B: Knowledge Effect (independent from relation type)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class KnowledgeEffect:
    """Independent knowledge-effect axis.

    Captures whether prior unknowns are resolved, and which dimensions.
    This is NOT mutually exclusive with the longitudinal relation.
    A STATE_CHANGE can simultaneously have prior_unknown_resolved=True.
    """
    prior_unknown_resolved: bool | None = None  # True/False/None(=unknown)
    resolved_dimensions: tuple[str, ...] = ()
    newly_introduced_unknowns: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.prior_unknown_resolved is False and self.resolved_dimensions:
            raise ValueError(
                "resolved_dimensions must be empty when prior_unknown_resolved is False"
            )


# ---------------------------------------------------------------------------
# Production-shaped MR Memory input (Axis A + Axis B temporal coordinates)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class TemporalCoordinates:
    """Dual time-axis coordinates as defined in the MR → LCE substrate.

    Axis A (knowledge/source chronology):
      - source_occurred_at: when the source event happened
      - received_at: when the system received the evidence
      - observed_at: when the system observed/processed the evidence
      - committed_at: when the evidence was committed to canonical state

    Axis B (proposition/world validity):
      - semantic_time: when the proposition is semantically about
      - valid_start / valid_end: proposition validity window
    """
    # Axis A
    source_occurred_at: datetime
    received_at: datetime
    observed_at: datetime | None = None
    committed_at: datetime | None = None

    # Axis B
    semantic_time: datetime | None = None
    valid_start: datetime | None = None
    valid_end: datetime | None = None

    def __post_init__(self) -> None:
        _require_utc(self.source_occurred_at, "source_occurred_at")
        _require_utc(self.received_at, "received_at")
        if self.observed_at is not None:
            _require_utc(self.observed_at, "observed_at")
        if self.committed_at is not None:
            _require_utc(self.committed_at, "committed_at")
        if self.semantic_time is not None:
            _require_utc(self.semantic_time, "semantic_time")
        if self.valid_start is not None:
            _require_utc(self.valid_start, "valid_start")
        if self.valid_end is not None:
            _require_utc(self.valid_end, "valid_end")
        if (
            self.valid_start is not None
            and self.valid_end is not None
            and self.valid_end < self.valid_start
        ):
            raise ValueError("valid_end must not precede valid_start")


@dataclass(frozen=True, slots=True)
class ProductionMemoryView:
    """Production-shaped MR Memory view consumed by Path B.

    Deliberate exclusions (no oracle fields):
      - No thread_id
      - No oracle domain
      - No correction_nature
      - No gold relation type
      - No precomputed trajectory label
      - No grouping key that reveals the answer
    """
    memory_id: str
    content: str
    source_refs: tuple[str, ...]
    temporal: TemporalCoordinates
    provenance: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_text(self.memory_id, "memory_id")
        _require_text(self.content, "content")
        if not isinstance(self.source_refs, tuple) or not self.source_refs:
            raise ValueError("source_refs must be a non-empty tuple")
        for ref in self.source_refs:
            _require_text(ref, "source_ref")
        if not isinstance(self.provenance, Mapping):
            raise TypeError("provenance must be a Mapping")
        # Forbidden oracle field check
        forbidden = {"thread_id", "oracle_domain", "correction_nature",
                      "gold_relation", "trajectory_label", "grouping_key"}
        if forbidden.intersection(self.provenance.keys()):
            raise ValueError(
                f"provenance must not contain oracle fields: "
                f"{forbidden.intersection(self.provenance.keys())}"
            )

    def to_semantic_block(self, *, compiler_version: str = "v0.4-issue25",
                          lineage_id: str = "path-b") -> SemanticBlock:
        """Convert to SemanticBlock for embedding/structure operations."""
        return SemanticBlock(
            block_id=self.memory_id,
            content=self.content,
            raw_evidence_ids=self.source_refs,
            occurred_start=self.temporal.source_occurred_at,
            occurred_end=self.temporal.received_at,
            compiler_version=compiler_version,
            lineage_id=lineage_id,
            metadata=dict(self.provenance),
        )


# ---------------------------------------------------------------------------
# Candidate pair (Stage 1 output → Stage 2 input)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class DiscoveredCandidate:
    """Candidate pair discovered by Stage 1 latent candidate discovery.

    Only DiscoveredCandidates may enter Stage 2 adjudication.
    Gold-pair shortcut is explicitly forbidden.
    """
    candidate_id: str
    predecessor_id: str
    successor_id: str
    predecessor_time: datetime
    successor_time: datetime
    signals: tuple[str, ...]
    baseline_level: str  # "B0", "B1", "B2"
    score: float = 0.0

    def __post_init__(self) -> None:
        _require_text(self.candidate_id, "candidate_id")
        _require_text(self.predecessor_id, "predecessor_id")
        _require_text(self.successor_id, "successor_id")
        _require_utc(self.predecessor_time, "predecessor_time")
        _require_utc(self.successor_time, "successor_time")
        if self.successor_time < self.predecessor_time:
            raise ValueError(
                f"Temporal violation: successor ({self.successor_time}) "
                f"cannot precede predecessor ({self.predecessor_time})"
            )
        _require_text(self.baseline_level, "baseline_level")
        if not self.signals:
            raise ValueError("signals must not be empty")


# ---------------------------------------------------------------------------
# Adjudication output (Stage 2)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AdjudicationResult:
    """Stage 2 adjudication result with orthogonal relation + knowledge effect.

    Key design: longitudinal_relation and knowledge_effect are independent.
    A single event can simultaneously be:
      - longitudinal_relation = STATE_CHANGE
      - knowledge_effect.prior_unknown_resolved = True
    """
    candidate_id: str
    predecessor_id: str
    successor_id: str
    longitudinal_relation: LongitudinalRelation
    knowledge_effect: KnowledgeEffect
    evidence_spans: tuple[str, ...] = ()
    adjudication_trace: str = ""
    confidence: float = 1.0

    def __post_init__(self) -> None:
        _require_text(self.candidate_id, "candidate_id")
        if not isinstance(self.longitudinal_relation, LongitudinalRelation):
            raise TypeError("longitudinal_relation must be a LongitudinalRelation")
        if not isinstance(self.knowledge_effect, KnowledgeEffect):
            raise TypeError("knowledge_effect must be a KnowledgeEffect")
        if self.longitudinal_relation == LongitudinalRelation.UNRELATED:
            if self.knowledge_effect.prior_unknown_resolved is True:
                raise ValueError(
                    "UNRELATED cannot resolve prior unknowns"
                )


# ---------------------------------------------------------------------------
# Gold annotation for evaluation (never consumed by the pipeline)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class GoldAnnotation:
    """Ground truth annotation for one pair. Used only for metrics."""
    pair_id: str
    predecessor_id: str
    successor_id: str
    longitudinal_relation: LongitudinalRelation
    knowledge_effect: KnowledgeEffect
    semantic_family: str
    falsification_tags: tuple[str, ...] = ()
    notes: str = ""


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class CandidateDiscoveryMetrics:
    baseline_level: str
    total_possible_pairs: int
    candidates_produced: int
    true_relation_pairs: int
    true_recalled: int
    recall: float
    candidates_per_block: float
    reduction_pct: float
    false_candidate_rate: float
    target_miss_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AdjudicationMetrics:
    total_evaluated: int
    relation_accuracy: float
    correction_vs_state_confusion: float
    unrelated_rejection_accuracy: float
    persistence_accuracy: float
    unknown_relation_rate: float
    confusion_matrix: Mapping[str, Mapping[str, int]] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class KnowledgeEffectMetrics:
    total_evaluated: int
    prior_unknown_resolution_precision: float
    prior_unknown_resolution_recall: float
    wrong_unknown_closure_rate: float
    wrong_dimension_resolution_rate: float
    evidence_free_closure_count: int


@dataclass(frozen=True, slots=True)
class TemporalIntegrityMetrics:
    reverse_time_errors: int
    future_leakage_count: int
    invalid_rewrite_count: int
    axis_confusion_count: int  # knowledge time confused with proposition valid time
    passed_all: bool


@dataclass(frozen=True, slots=True)
class CostMetrics:
    adjudication_calls: int
    calls_per_block: float
    tokens_per_accepted: float
    candidate_volume_before: int
    candidate_volume_after: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _require_utc(value: object, name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo != UTC:
        raise ValueError(f"{name} must be an aware UTC datetime")
    return value
