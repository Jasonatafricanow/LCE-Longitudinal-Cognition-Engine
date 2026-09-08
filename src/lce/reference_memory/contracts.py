"""Contracts for the minimal standalone Memory substrate.

Reference Memory owns canonical Raw Evidence and Semantic Blocks. Vectors and
all structure observations are explicitly derived records and can be deleted
without deleting their canonical inputs.
"""

from __future__ import annotations

from collections.abc import Mapping
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
    """Minimal port that permits replacing local Reference Memory."""

    def add_evidence(self, item: RawEvidence) -> RawEvidence:
        ...

    def list_current_valid_evidence(self) -> tuple[RawEvidence, ...]:
        ...
