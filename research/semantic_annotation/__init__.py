"""Research-only semantic annotation contract v0.1 (GitHub Issue #13 Final Patch).

Defines the frozen semantic annotation ontology, guideline types,
and canonical machine-readable validation schemas for LCE semantic parsing experiments.
Does not modify production runtime or contracts.
"""

from research.semantic_annotation.schema import (
    CONTROL_RELATION_TYPES,
    FORBIDDEN_LABELS,
    FROZEN_PREDICATE_MAP,
    GRAPH_ADMISSIBLE_EVIDENCE_STATUSES,
    ROLE_VOCABULARY,
    ArgumentMention,
    AttributionMode,
    EpistemicHedge,
    EvidenceStatus,
    ModalityType,
    PolarityType,
    PredicateNormalizationRule,
    PredicateSpec,
    RelationProvenance,
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
    "CONTROL_RELATION_TYPES",
    "FORBIDDEN_LABELS",
    "FROZEN_PREDICATE_MAP",
    "GRAPH_ADMISSIBLE_EVIDENCE_STATUSES",
    "ROLE_VOCABULARY",
    "ArgumentMention",
    "AttributionMode",
    "EpistemicHedge",
    "EvidenceStatus",
    "ModalityType",
    "PolarityType",
    "PredicateNormalizationRule",
    "PredicateSpec",
    "RelationProvenance",
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
