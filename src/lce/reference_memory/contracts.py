"""Contracts for the minimal standalone Memory substrate.

Reference Memory owns canonical Raw Evidence and Semantic Blocks. Vectors and
all structure observations are explicitly derived records and can be deleted
without deleting their canonical inputs.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable


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


@dataclass(frozen=True, slots=True)
class RawEvidence:
    """Immutable source material with explicit canonical provenance."""

    evidence_id: str
    content: str
    occurred_at: datetime
    provenance: Mapping[str, object]
    ordering_key: str | None = None
    state: str = "VALID"
    superseded_by: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.evidence_id, "evidence_id")
        _require_text(self.content, "content")
        _require_utc(self.occurred_at, "occurred_at")
        if not isinstance(self.provenance, Mapping):
            raise TypeError("provenance must be a Mapping")
        if self.ordering_key is not None:
            _require_text(self.ordering_key, "ordering_key")
        if self.state not in {"VALID", "INVALID", "SUPERSEDED"}:
            raise ValueError("state must be VALID, INVALID, or SUPERSEDED")
        if self.superseded_by is not None:
            _require_text(self.superseded_by, "superseded_by")

    @property
    def current_valid(self) -> bool:
        return self.state == "VALID" and self.superseded_by is None

    @property
    def effective_ordering_key(self) -> str:
        return self.ordering_key or self.occurred_at.isoformat()


@dataclass(frozen=True, slots=True)
class SemanticBlock:
    """Canonical semantic unit used as the cognition point before embedding."""

    block_id: str
    content: str
    raw_evidence_ids: tuple[str, ...]
    occurred_start: datetime
    occurred_end: datetime
    compiler_version: str
    lineage_id: str
    metadata: Mapping[str, object] = field(default_factory=dict)
    state_id: str | None = None
    state_version: int = 1

    def __post_init__(self) -> None:
        _require_text(self.block_id, "block_id")
        _require_text(self.content, "content")
        if not isinstance(self.raw_evidence_ids, tuple) or not self.raw_evidence_ids:
            raise ValueError("raw_evidence_ids must be a non-empty tuple")
        if len(set(self.raw_evidence_ids)) != len(self.raw_evidence_ids):
            raise ValueError("raw_evidence_ids must not contain duplicates")
        for evidence_id in self.raw_evidence_ids:
            _require_text(evidence_id, "raw_evidence_id")
        _require_utc(self.occurred_start, "occurred_start")
        _require_utc(self.occurred_end, "occurred_end")
        if self.occurred_end < self.occurred_start:
            raise ValueError("occurred_end must not precede occurred_start")
        _require_text(self.compiler_version, "compiler_version")
        _require_text(self.lineage_id, "lineage_id")
        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a Mapping")
        if self.state_id is not None:
            _require_text(self.state_id, "state_id")
        if not isinstance(self.state_version, int) or self.state_version < 1:
            raise ValueError("state_version must be an integer >= 1")


@dataclass(frozen=True, slots=True)
class AuthorizedSelectedSupport:
    """One explicitly authorized immutable state selected for cognition."""

    block_id: str
    state_id: str

    def __post_init__(self) -> None:
        _require_text(self.block_id, "block_id")
        _require_text(self.state_id, "state_id")


@dataclass(frozen=True, slots=True)
class VectorProjection:
    """Rebuildable vector projection of exactly one Semantic Block."""

    block_id: str
    values: tuple[float, ...]
    index_version: str

    def __post_init__(self) -> None:
        _require_text(self.block_id, "block_id")
        if not isinstance(self.values, tuple) or not self.values:
            raise ValueError("values must be a non-empty tuple")
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in self.values):
            raise TypeError("vector values must be numeric")
        _require_text(self.index_version, "index_version")


@dataclass(frozen=True, slots=True)
class AuditEvent:
    evidence_id: str
    event_type: str
    reason: str | None
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class CompilerCheckpoint:
    lineage_id: str
    last_ordering_key: str | None
    open_block_id: str | None
    compiler_version: str
    state: Mapping[str, object] = field(default_factory=dict)


@runtime_checkable
class ReferenceMemoryPort(Protocol):
    """Compatibility evidence port for callers that only need raw evidence."""

    def add_evidence(self, item: RawEvidence) -> RawEvidence:
        ...

    def list_current_valid_evidence(self) -> tuple[RawEvidence, ...]:
        ...


@runtime_checkable
class EvidencePort(ReferenceMemoryPort, Protocol):
    """Canonical Raw Evidence operations consumed by the V1 pipeline."""

    def get_evidence(self, evidence_id: str) -> RawEvidence:
        ...

    def invalidate(self, evidence_id: str, *, reason: str) -> None:
        ...

    def supersede(self, evidence_id: str, replacement_evidence_id: str) -> None:
        ...


@runtime_checkable
class SemanticBlockPort(EvidencePort, Protocol):
    """Semantic Block and immutable historical-state operations."""

    def put_semantic_block(self, block: SemanticBlock) -> SemanticBlock:
        ...

    def get_semantic_block(self, block_id: str) -> SemanticBlock:
        ...

    def get_semantic_block_state(self, state_id: str) -> SemanticBlock:
        ...

    def list_semantic_blocks(self, *, current_valid_only: bool = True) -> tuple[SemanticBlock, ...]:
        ...

    def list_semantic_block_states(self, *, current_valid_only: bool = True) -> tuple[SemanticBlock, ...]:
        ...

    def list_semantic_blocks_at_cutoff(
        self, cutoff: datetime, *, current_valid_only: bool = True
    ) -> tuple[SemanticBlock, ...]:
        ...

    def extend_semantic_block(
        self,
        block_id: str,
        *,
        content: str | None,
        evidence_id: str,
        occurred_at: datetime,
    ) -> SemanticBlock:
        ...


@runtime_checkable
class VectorProjectionPort(Protocol):
    """Rebuildable vector projection operations."""

    def rebuild_vector_index(
        self,
        embedder: Callable[[SemanticBlock], tuple[float, ...]],
        *,
        index_version: str,
    ) -> None:
        ...

    def delete_vector_index(self) -> None:
        ...

    def get_vector(self, block_id: str, *, state_id: str | None = None) -> VectorProjection:
        ...

    def vector_projection_ids(self) -> tuple[str, ...]:
        ...


@runtime_checkable
class CompilerProgressPort(Protocol):
    """Durable compiler and downstream pipeline progress operations."""

    def get_checkpoint(self, lineage_id: str) -> CompilerCheckpoint | None:
        ...

    def save_checkpoint(self, checkpoint: CompilerCheckpoint) -> None:
        ...

    def commit_compilation(
        self,
        *,
        evidence_id: str,
        lineage_id: str,
        block_states: tuple[SemanticBlock, ...],
        block_ids: tuple[str, ...],
        decision: Mapping[str, object],
        checkpoint: CompilerCheckpoint,
    ) -> None:
        ...

    def compiled_block_ids(self, evidence_id: str) -> tuple[str, ...] | None:
        ...

    def mark_pending_failure(self, lineage_id: str, *, evidence_id: str, ordering_key: str) -> None:
        ...

    def get_pipeline_stage(self, evidence_id: str) -> str | None:
        ...

    def mark_pipeline_stage(self, evidence_id: str, stage: str, *, fingerprint: str | None = None) -> None:
        ...


@runtime_checkable
class ReferenceMemorySubstratePort(
    SemanticBlockPort, VectorProjectionPort, CompilerProgressPort, Protocol
):
    """Complete focused-port composition required by standalone LCE V1."""

    def close(self) -> None:
        ...
