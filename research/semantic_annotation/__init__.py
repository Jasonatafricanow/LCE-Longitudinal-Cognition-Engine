"""Research-only semantic annotation contract v0.1 (GitHub Issue #13).

Defines the frozen semantic annotation ontology, guideline types,
and machine-readable validation schemas for LCE semantic parsing experiments.
Does not modify production runtime or contracts.
"""

from research.semantic_annotation.schema import (
    FORBIDDEN_LABELS,
    ROLE_VOCABULARY,
    EvidenceStatus,
    HolderSource,
    ModalityType,
    PolarityType,
    RelationType,
    SemanticAnnotationDocument,
    SemanticRelation,
    SemanticUnit,
    SourceSpan,
    TemporalAnchorType,
    TemporalAnchoring,
    UnitKind,
    UnitProvenance,
)

__all__ = [
    "FORBIDDEN_LABELS",
    "ROLE_VOCABULARY",
    "EvidenceStatus",
    "HolderSource",
    "ModalityType",
    "PolarityType",
    "RelationType",
    "SemanticAnnotationDocument",
    "SemanticRelation",
    "SemanticUnit",
    "SourceSpan",
    "TemporalAnchorType",
    "TemporalAnchoring",
    "UnitKind",
    "UnitProvenance",
]
