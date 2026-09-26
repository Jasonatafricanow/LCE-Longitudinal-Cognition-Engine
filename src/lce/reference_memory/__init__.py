"""Standalone and external-source Memory substrates for LCE."""

from lce.reference_memory.composite import (
    ExternalSourceMutationError,
    ProjectionSubstrate,
)
from lce.reference_memory.contracts import (
    AuditEvent,
    AuthorizedSelectedSupport,
    CanonicalEvidenceSourcePort,
    CompilerCheckpoint,
    CompilerProgressPort,
    DerivedProjectionStatePort,
    EvidencePort,
    RawEvidence,
    ReferenceMemoryPort,
    ReferenceMemorySubstratePort,
    SemanticBlock,
    SemanticBlockPort,
    VectorProjection,
    VectorProjectionPort,
)
from lce.reference_memory.projection_state import SqliteProjectionStateStore
from lce.reference_memory.sqlite import ReferenceMemoryStore

__all__ = [
    "AuditEvent",
    "AuthorizedSelectedSupport",
    "CanonicalEvidenceSourcePort",
    "CompilerCheckpoint",
    "CompilerProgressPort",
    "DerivedProjectionStatePort",
    "EvidencePort",
    "ExternalSourceMutationError",
    "ProjectionSubstrate",
    "RawEvidence",
    "ReferenceMemoryPort",
    "ReferenceMemoryStore",
    "ReferenceMemorySubstratePort",
    "SemanticBlock",
    "SemanticBlockPort",
    "SqliteProjectionStateStore",
    "VectorProjection",
    "VectorProjectionPort",
]
