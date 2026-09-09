"""Derived structure and snapshot contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime

from lce.reference_memory.contracts import SemanticBlock


def _utc(value: datetime, name: str) -> None:
    if value.tzinfo != UTC:
        raise ValueError(f"{name} must be UTC")


@dataclass(frozen=True, slots=True)
class StructureConfig:
    k_values: tuple[int, ...] = (2, 4, 8)
    min_similarity: float = 0.75
    higher_order_similarity: float = 0.85
    algorithm_version: str = "structure-06r-lite-v1"

    def __post_init__(self) -> None:
        if not self.k_values or any(k < 1 for k in self.k_values):
            raise ValueError("k_values must contain positive integers")
        if not 0.0 <= self.min_similarity <= 1.0:
            raise ValueError("min_similarity must be within [0, 1]")
        if not 0.0 <= self.higher_order_similarity <= 1.0:
            raise ValueError("higher_order_similarity must be within [0, 1]")


@dataclass(frozen=True, slots=True)
class StructureObservation:
    structure_id: str
    center_block_id: str
    member_block_ids: tuple[str, ...]
    k: int
    support_score: float
    neighbourhood_stability: float
    local_overlap: float
    multi_point_participation: int
    temporal_dates: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StructureSnapshot:
    snapshot_id: str
    timestamp: datetime
    cutoff: datetime
    visible_block_ids: tuple[str, ...]
    structures: tuple[StructureObservation, ...]
    algorithm_version: str
    config: StructureConfig
    block_states: tuple[SemanticBlock, ...] = ()
    vectors: Mapping[str, tuple[float, ...]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _utc(self.timestamp, "timestamp")
        _utc(self.cutoff, "cutoff")

    @property
    def visible_block_state_ids(self) -> tuple[str, ...]:
        return tuple(
            block.state_id or block.block_id
            for block in self.block_states
            if block.block_id in self.visible_block_ids
        )


@dataclass(frozen=True, slots=True)
class StructureChange:
    structure_id: str
    added_block_ids: tuple[str, ...] = ()
    removed_block_ids: tuple[str, ...] = ()
    relation_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StructureDiff:
    previous_snapshot_id: str
    current_snapshot_id: str
    new_members: tuple[StructureChange, ...] = ()
    lost_or_weakened: tuple[StructureChange, ...] = ()
    stronger_support: tuple[StructureChange, ...] = ()
    reconnections: tuple[StructureChange, ...] = ()
    reorganizations: tuple[StructureChange, ...] = ()
    linked_structures: tuple[StructureChange, ...] = ()


@dataclass(frozen=True, slots=True)
class HigherOrderCandidate:
    candidate_id: str
    snapshot_id: str
    supporting_structure_ids: tuple[str, ...]
    supporting_block_ids: tuple[str, ...]
    relation_type: str
    strength: float
    status: str = "UNKNOWN"
    metadata: Mapping[str, object] = field(default_factory=dict)
