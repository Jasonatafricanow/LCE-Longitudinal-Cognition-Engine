"""Baseline data contracts for LCE.

A Baseline is a durable, highly compressed long-term logical understanding
derived from an externally discovered point cloud of related memories.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime

_ALLOWED_MODEL_TRACE_KEYS = frozenset(
    {
        "provider",
        "model",
        "model_version",
        "run_id",
        "confidence",
        "timestamp",
        "duration_ms",
    }
)
_MAX_AUDIT_STRING_LENGTH = 128


def validate_model_trace(model_trace: Mapping[str, object]) -> None:
    """Validate that model_trace contains only bounded allowlisted scalar metadata.

    Rejects unknown keys, nested structures (mappings, lists, tuples), and oversized values.
    Prevents model_trace from acting as a disguised raw prompt or memory store.
    """
    if not isinstance(model_trace, Mapping):
        raise TypeError("model_trace must be a Mapping")

    for key, val in model_trace.items():
        if not isinstance(key, str):
            raise TypeError("model_trace keys must be strings")
        if key not in _ALLOWED_MODEL_TRACE_KEYS:
            raise ValueError(
                f"model_trace key '{key}' is not permitted in audit metadata (allowed: {sorted(_ALLOWED_MODEL_TRACE_KEYS)})"
            )
        if val is None:
            continue

        if key in ("provider", "model", "model_version", "run_id", "timestamp"):
            if not isinstance(val, str):
                raise TypeError(
                    f"model_trace['{key}'] must be a string or None, got {type(val).__name__}"
                )
            if len(val) > _MAX_AUDIT_STRING_LENGTH:
                raise ValueError(
                    f"model_trace['{key}'] exceeds maximum length of {_MAX_AUDIT_STRING_LENGTH} chars (got {len(val)})"
                )
        elif key in ("confidence", "duration_ms"):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise TypeError(
                    f"model_trace['{key}'] must be numeric, got {type(val).__name__}"
                )
            if key == "confidence" and not (0.0 <= float(val) <= 1.0):
                raise ValueError(
                    f"model_trace['confidence'] must be in range [0.0, 1.0], got {val}"
                )
            if key == "duration_ms" and float(val) < 0.0:
                raise ValueError(
                    f"model_trace['duration_ms'] must be non-negative, got {val}"
                )


def normalize_content(content: str) -> str:
    """Normalize baseline text for deterministic comparison and hashing."""
    # Collapse consecutive whitespace and strip
    return re.sub(r"\s+", " ", content).strip()


def compute_content_hash(content: str) -> str:
    """Compute SHA-256 digest of normalized baseline content."""
    normalized = normalize_content(content)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class Baseline:
    """Immutable record of learned long-term understanding for a region.

    Hard invariants:
      - baseline_id: Independent unique revision identity (UUID-based).
      - region_id: Opaque LCE lineage identifier (not vector coordinates).
      - revision_number: 1-indexed sequential integer.
      - content: Compressed learned understanding text.
      - content_hash: SHA-256 digest of normalize_content(content).
      - supporting_memory_ids: Non-empty, deduplicated tuple of stable external Memory IDs.
      - previous_baseline_id: ID of predecessor revision (None for rev 1).
      - created_at: Aware UTC datetime timestamp.
      - model_trace: Bounded audit metadata (provider, model, confidence, etc.).
        Strictly restricted to allowlisted scalar fields with length caps.
    """

    baseline_id: str
    region_id: str
    revision_number: int
    content: str
    content_hash: str
    supporting_memory_ids: tuple[str, ...]
    created_at: datetime
    previous_baseline_id: str | None = None
    model_trace: Mapping[str, object] = field(default_factory=dict)
    supporting_state_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.baseline_id, str) or not self.baseline_id.strip():
            raise ValueError("baseline_id must be a non-empty string")
        if not isinstance(self.region_id, str) or not self.region_id.strip():
            raise ValueError("region_id must be a non-empty string")
        if not isinstance(self.revision_number, int) or self.revision_number < 1:
            raise ValueError("revision_number must be an integer >= 1")
        if not isinstance(self.content, str) or not self.content.strip():
            raise ValueError("content must be a non-empty string")
        if not isinstance(self.content_hash, str) or not self.content_hash.strip():
            raise ValueError("content_hash must be a non-empty string")
        if not isinstance(self.supporting_memory_ids, tuple):
            raise TypeError("supporting_memory_ids must be a tuple of strings")
        if not self.supporting_memory_ids:
            raise ValueError("supporting_memory_ids must not be empty")
        for mem_id in self.supporting_memory_ids:
            if not isinstance(mem_id, str) or not mem_id.strip():
                raise ValueError("each supporting_memory_id must be a non-empty string")
        if len(self.supporting_memory_ids) != len(set(self.supporting_memory_ids)):
            raise ValueError("supporting_memory_ids contains duplicate memory IDs")
        if not isinstance(self.created_at, datetime):
            raise TypeError("created_at must be a datetime")
        if self.created_at.tzinfo is None or self.created_at.tzinfo != UTC:
            raise ValueError("created_at must be an aware UTC datetime")

        if self.revision_number == 1 and self.previous_baseline_id is not None:
            raise ValueError("revision 1 must have previous_baseline_id=None")
        if self.revision_number > 1:
            if not isinstance(self.previous_baseline_id, str) or not self.previous_baseline_id.strip():
                raise ValueError("revision > 1 must have a non-empty previous_baseline_id")
            if self.previous_baseline_id == self.baseline_id:
                raise ValueError("self-referencing previous_baseline_id is forbidden")

        validate_model_trace(self.model_trace)


@dataclass(frozen=True, slots=True)
class BaselineHistory:
    """Audit collection of historical baseline revisions for a region."""

    region_id: str
    revisions: tuple[Baseline, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.region_id, str) or not self.region_id.strip():
            raise ValueError("region_id must be a non-empty string")
        if not isinstance(self.revisions, tuple):
            raise TypeError("revisions must be a tuple of Baseline records")
        for rev in self.revisions:
            if not isinstance(rev, Baseline):
                raise TypeError("revisions elements must be Baseline instances")
            if rev.region_id != self.region_id:
                raise ValueError(
                    f"revision {rev.baseline_id} region_id '{rev.region_id}' "
                    f"does not match history region_id '{self.region_id}'"
                )
