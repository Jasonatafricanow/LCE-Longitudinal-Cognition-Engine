"""Metadata-only support seams shared by standalone and canonical projections.

The legacy fallback reads real standalone evidence. Canonical integrations
provide these capabilities explicitly and never construct or read RawEvidence.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, cast

from lce.reference_memory.contracts import RawEvidence, SemanticBlock


@dataclass(frozen=True, slots=True)
class SupportStatus:
    occurred_at: datetime
    known_at: datetime
    current_valid: bool


class LegacySupportReader(Protocol):
    def get_evidence(self, evidence_id: str) -> RawEvidence: ...


def support_status(memory: object, support_id: str) -> SupportStatus:
    reader = getattr(memory, "get_support_status", None)
    if callable(reader):
        status = reader(support_id)
        if not isinstance(status, SupportStatus):
            raise TypeError("SupportStatus required")
        return status
    item = cast(LegacySupportReader, memory).get_evidence(support_id)
    return SupportStatus(item.occurred_at, item.effective_known_at, item.current_valid)


def support_valid_at(memory: object, support_id: str, cutoff: datetime) -> bool:
    reader = getattr(memory, "support_valid_at", None)
    if callable(reader):
        return bool(reader(support_id, cutoff))
    reader = getattr(memory, "evidence_valid_at", None)
    if callable(reader):
        return bool(reader(support_id, cutoff))
    status = support_status(memory, support_id)
    return status.known_at <= cutoff and status.current_valid


def block_current_valid(memory: object, block: SemanticBlock) -> bool:
    reader = getattr(memory, "block_current_valid", None)
    if callable(reader):
        return bool(reader(block.block_id))
    return all(support_status(memory, sid).current_valid for sid in block.raw_evidence_ids)


def block_valid_at(memory: object, block: SemanticBlock, cutoff: datetime) -> bool:
    reader = getattr(memory, "block_valid_at", None)
    if callable(reader):
        return bool(reader(block.block_id, cutoff))
    return all(support_valid_at(memory, sid, cutoff) for sid in block.raw_evidence_ids)
