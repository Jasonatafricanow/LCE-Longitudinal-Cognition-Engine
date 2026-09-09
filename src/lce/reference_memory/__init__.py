"""Standalone, replaceable Reference Memory substrate for LCE."""

from lce.reference_memory.contracts import (
    AuditEvent,
    CompilerCheckpoint,
    CompilerProgressPort,
    EvidencePort,
    RawEvidence,
    ReferenceMemoryPort,
    ReferenceMemorySubstratePort,
    SemanticBlock,
    SemanticBlockPort,
    VectorProjection,
    VectorProjectionPort,
)
from lce.reference_memory.sqlite import ReferenceMemoryStore

__all__ = [
    "AuditEvent",
    "CompilerCheckpoint",
    "CompilerProgressPort",
    "EvidencePort",
    "RawEvidence",
    "ReferenceMemoryPort",
    "ReferenceMemoryStore",
    "ReferenceMemorySubstratePort",
    "SemanticBlock",
    "SemanticBlockPort",
    "VectorProjection",
    "VectorProjectionPort",
]
