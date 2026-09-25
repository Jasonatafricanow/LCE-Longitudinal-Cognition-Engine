"""First longitudinal layer contracts above SemanticBlock.

Authoritative constraints (Issue #24):
- SemanticBlock remains an immutable local truth at time t.
- Time ordering (t1 < t2) is deterministic authority.
- Later facts NEVER mutate predecessor SemanticBlocks.
- UNKNOWN only closes with new evidence, not elapsed time.
- World state change != earlier cognition was wrong.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
import hashlib

from lce.reference_memory.contracts import SemanticBlock


class LongitudinalRelationType(str, Enum):
    """The six canonical longitudinal relation types tested in Issue #24."""

    UNCERTAINTY_RESOLUTION = "UNCERTAINTY_RESOLUTION"
    STATE_CHANGE = "STATE_CHANGE"
    CORRECTION_RETRACTION = "CORRECTION_RETRACTION"
    PERSISTENCE_CONFIRMATION = "PERSISTENCE_CONFIRMATION"
    UNRELATED = "UNRELATED"
    UNKNOWN_RELATION = "UNKNOWN_RELATION"


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


def compute_block_content_hash(block: SemanticBlock) -> str:
    """Deterministic hash of SemanticBlock identity and content to guarantee immutability."""
    payload = f"{block.block_id}:{block.content}:{block.occurred_start.isoformat()}:{block.occurred_end.isoformat()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class LongitudinalCandidate:
    """Bounded longitudinal candidate pair formed before selective adjudication."""

    candidate_id: str
    predecessor_block_id: str
    successor_block_id: str
    predecessor_time: datetime
    successor_time: datetime
    signals: tuple[str, ...]
    filter_level: str
    score: float = 0.0

    def __post_init__(self) -> None:
        _require_text(self.candidate_id, "candidate_id")
        _require_text(self.predecessor_block_id, "predecessor_block_id")
        _require_text(self.successor_block_id, "successor_block_id")
        _require_utc(self.predecessor_time, "predecessor_time")
        _require_utc(self.successor_time, "successor_time")
        if self.successor_time < self.predecessor_time:
            raise ValueError(
                f"Temporal violation: successor ({self.successor_time}) cannot precede predecessor ({self.predecessor_time})"
            )
        _require_text(self.filter_level, "filter_level")


@dataclass(frozen=True, slots=True)
class LongitudinalObservation:
    """Accepted typed longitudinal relation record above SemanticBlock."""

    observation_id: str
    predecessor_block_id: str
    successor_block_id: str
    time_order_valid: bool
    relation_type: LongitudinalRelationType
    affected_dimension: str
    prior_unknown_resolved: bool
    outcome_or_current_state: str
    evidence_spans: tuple[str, ...] = ()
    resolved_dimension: str | None = None
    adjudication_trace: str = ""
    competing_rejections: Mapping[str, str] = field(default_factory=dict)
    confidence: float = 1.0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        _require_text(self.observation_id, "observation_id")
        _require_text(self.predecessor_block_id, "predecessor_block_id")
        _require_text(self.successor_block_id, "successor_block_id")
        if not self.time_order_valid:
            raise ValueError("Longitudinal observations strictly require valid chronological time ordering")
        if not isinstance(self.relation_type, LongitudinalRelationType):
            raise TypeError(f"relation_type must be a LongitudinalRelationType, got {self.relation_type}")
        _require_text(self.affected_dimension, "affected_dimension")
        _require_text(self.outcome_or_current_state, "outcome_or_current_state")
        _require_utc(self.created_at, "created_at")

    def as_dict(self) -> dict[str, object]:
        return {
            "observation_id": self.observation_id,
            "predecessor_block_id": self.predecessor_block_id,
            "successor_block_id": self.successor_block_id,
            "time_order_valid": self.time_order_valid,
            "relation_type": self.relation_type.value,
            "affected_dimension": self.affected_dimension,
            "prior_unknown_resolved": self.prior_unknown_resolved,
            "resolved_dimension": self.resolved_dimension,
            "outcome_or_current_state": self.outcome_or_current_state,
            "evidence_spans": list(self.evidence_spans),
            "adjudication_trace": self.adjudication_trace,
            "competing_rejections": dict(self.competing_rejections),
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
        }
