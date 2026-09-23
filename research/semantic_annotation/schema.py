"""Canonical machine-readable schema and validation for LCE Semantic Annotation v0.1.

Research-only specification (GitHub Issue #13 Final Patch).
This module serves as the single CANONICAL schema for v0.1 semantic annotation contracts.
JSON Schemas under research/schemas/ are validated against or derived from this module.
Does not modify production runtime or contracts.
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Constants and Vocabularies
# ---------------------------------------------------------------------------

ROLE_VOCABULARY: frozenset[str] = frozenset({
    "actor",
    "experiencer",
    "theme",
    "target",
    "stimulus",
    "topic",
    "place",
    "reason",
    "purpose",
    "result",
    "time",
})

FORBIDDEN_LABELS: frozenset[str] = frozenset({
    "REVISION",
    "RECURRENCE",
    "TRAJECTORY",
    "STABLE_PREFERENCE",
    "COGNITIVE_SHIFT",
    "LONG_TERM_BELIEF",
    "LONG_TERM_IDENTITY",
    "SUPPORTS_LONGITUDINAL_COGNITION",
    "SUPERCEDES_LONG_TERM_BELIEF",
})

# Frozen deterministic predicate normalization lookup table for v0.1
FROZEN_PREDICATE_MAP: dict[str, str] = {
    "prefer writing": "prefer",
    "loved working": "love",
    "burned out": "burn_out",
    "are riskier": "risky",
    "running out of disk space": "low_disk_space",
}


class UnitKind(str, Enum):
    EVENT = "event"
    STATE = "state"
    PROPOSITION = "proposition"
    ATTITUDE = "attitude"


class PolarityType(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    UNKNOWN = "unknown"


class ModalityType(str, Enum):
    ASSERTED = "asserted"
    POSSIBLE = "possible"
    HYPOTHETICAL = "hypothetical"
    INTENDED = "intended"
    DESIRED = "desired"
    UNCERTAIN = "uncertain"
    UNKNOWN = "unknown"


class EpistemicHedge(str, Enum):
    """Explicit outer epistemic hedging decoupled from the inner proposition/desire modality."""

    NONE = "none"
    THINK = "think"            # e.g. "I think", "I believe"
    PROBABLE = "probable"      # e.g. "probably", "likely"
    UNCERTAIN = "uncertain"    # e.g. "wonder if", "not sure if"
    DOUBT = "doubt"            # e.g. "I doubt that"


class PredicateNormalizationRule(str, Enum):
    """Deterministic mechanical normalization rules permitted in v0.1."""

    EXACT_SURFACE = "exact_surface"      # exact lowercase surface form
    LEMMA = "lemma"                      # mechanical lowercased English base lemma
    COMPOUND_LOWER = "compound_lower"    # lowercase with whitespace -> underscore
    FROZEN_MAP = "frozen_map"            # lookup in explicit frozen FROZEN_PREDICATE_MAP


class AttributionMode(str, Enum):
    DIRECT_SPEAKER = "direct_speaker"
    DIRECT_QUOTE = "direct_quote"
    INDIRECT_REPORT = "indirect_report"
    EXTERNAL_SOURCE = "external_source"
    UNKNOWN = "unknown"


class EvidenceStatus(str, Enum):
    EXPLICIT = "explicit"
    ENTAILED = "entailed"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


# Graph admission: only explicit and entailed units/relations are eligible as positive graph nodes/edges
GRAPH_ADMISSIBLE_EVIDENCE_STATUSES: frozenset[EvidenceStatus] = frozenset({
    EvidenceStatus.EXPLICIT,
    EvidenceStatus.ENTAILED,
})


class TemporalAnchorType(str, Enum):
    EXACT = "exact"
    BOUNDED_RANGE = "bounded_range"
    RELATIVE = "relative"
    UNANCHORED = "unanchored"


class RelationType(str, Enum):
    # Identity (strictly links stable mention IDs)
    SAME_ENTITY = "SAME_ENTITY"
    SAME_EVENT = "SAME_EVENT"

    # Temporal (links proposition/event unit IDs)
    BEFORE = "BEFORE"
    AFTER = "AFTER"
    OVERLAP = "OVERLAP"
    TEMPORAL_UNKNOWN = "TEMPORAL_UNKNOWN"

    # Logical / Discourse (links proposition/event unit IDs)
    CAUSE = "CAUSE"
    CONDITION = "CONDITION"
    PURPOSE = "PURPOSE"
    CONTRAST = "CONTRAST"
    CONCESSION = "CONCESSION"

    # State Compatibility (links proposition/state/attitude unit IDs with overlapping time)
    EQUIVALENT = "EQUIVALENT"
    INCOMPATIBLE = "INCOMPATIBLE"

    # Control outcomes (evaluation/annotation only, NEVER persisted as graph edges)
    NO_RELATION = "NO_RELATION"
    UNKNOWN = "UNKNOWN"


CONTROL_RELATION_TYPES: frozenset[RelationType] = frozenset({
    RelationType.NO_RELATION,
    RelationType.UNKNOWN,
    RelationType.TEMPORAL_UNKNOWN,
})


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class SourceSpan(BaseModel):
    """Character offsets and verbatim text within a raw evidence source."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    char_start: int = Field(ge=0, description="0-indexed start offset")
    char_end: int = Field(ge=1, description="0-indexed end offset (exclusive)")
    text: str = Field(min_length=1, description="Verbatim text span")

    @model_validator(mode="after")
    def validate_bounds(self) -> SourceSpan:
        if self.char_end <= self.char_start:
            raise ValueError(
                f"char_end ({self.char_end}) must be strictly greater than char_start ({self.char_start})"
            )
        return self


class UnitProvenance(BaseModel):
    """Mandatory upstream provenance linking back to raw evidence and boundary block."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    raw_evidence_id: str = Field(min_length=1)
    semantic_block_id: str = Field(min_length=1)


class RelationProvenance(BaseModel):
    """Independent grounding and provenance for a semantic relation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    raw_evidence_id: str = Field(min_length=1)
    semantic_block_id: str = Field(min_length=1)


class ArgumentMention(BaseModel):
    """A grounded argument mention with its own stable mention_id."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mention_id: str = Field(min_length=1, description="Stable unique mention identifier, e.g. 'm_001'")
    role: str = Field(description="Role from ROLE_VOCABULARY")
    text: str = Field(min_length=1, description="Verbatim text or normalized argument string")
    source_span: SourceSpan | None = Field(default=None, description="Optional exact span within raw evidence")
    entity_ref: str | None = Field(default=None, description="Optional entity identifier or coreference key")

    @field_validator("role")
    @classmethod
    def validate_role(cls, r: str) -> str:
        if r not in ROLE_VOCABULARY:
            raise ValueError(
                f"Invalid argument role '{r}'. Role must be one of: {sorted(ROLE_VOCABULARY)}"
            )
        return r


class TemporalAnchoring(BaseModel):
    """Normalized temporal anchoring information with explicit reference anchor."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    normalized_value: str = Field(min_length=1, description="ISO date/range or 'unknown'")
    anchor_type: TemporalAnchorType
    source_expression: str | None = Field(default=None, description="Verbatim temporal expression from span")
    reference_anchor: str | None = Field(
        default=None,
        description="Reference time anchor for relative expressions (e.g. 'evidence:occurred_at', 'doc_time')",
    )

    @model_validator(mode="after")
    def validate_relative_anchor(self) -> TemporalAnchoring:
        if self.anchor_type == TemporalAnchorType.RELATIVE and not self.reference_anchor:
            raise ValueError(
                "Relative temporal anchor must specify 'reference_anchor' (e.g. 'evidence:occurred_at')"
            )
        return self


class PredicateSpec(BaseModel):
    """Deterministic mechanical predicate normalization."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    surface_predicate: str = Field(min_length=1, description="Verbatim predicate/verb/expression from text")
    normalized_predicate: str = Field(min_length=1, description="Mechanically normalized predicate")
    normalization_rule: PredicateNormalizationRule = Field(
        description="Deterministic normalization rule (exact_surface, lemma, compound_lower, frozen_map)"
    )

    @field_validator("normalized_predicate")
    @classmethod
    def validate_predicate_not_forbidden(cls, pred: str) -> str:
        upper_pred = pred.strip().upper()
        if upper_pred in FORBIDDEN_LABELS:
            raise ValueError(
                f"Forbidden downstream cognition label '{pred}' cannot be used as a unit predicate."
            )
        return pred

    @model_validator(mode="after")
    def validate_normalization_mechanics(self) -> PredicateSpec:
        surf_clean = self.surface_predicate.strip().lower()
        if self.normalization_rule == PredicateNormalizationRule.EXACT_SURFACE:
            if self.normalized_predicate != surf_clean:
                raise ValueError(
                    f"Rule 'exact_surface' requires normalized_predicate ('{self.normalized_predicate}') "
                    f"to equal lowercase surface_predicate ('{surf_clean}')"
                )
        elif self.normalization_rule == PredicateNormalizationRule.COMPOUND_LOWER:
            expected = surf_clean.replace(" ", "_")
            if self.normalized_predicate != expected:
                raise ValueError(
                    f"Rule 'compound_lower' requires normalized_predicate ('{self.normalized_predicate}') "
                    f"to equal '{expected}'"
                )
        elif self.normalization_rule == PredicateNormalizationRule.FROZEN_MAP:
            if surf_clean in FROZEN_PREDICATE_MAP:
                expected = FROZEN_PREDICATE_MAP[surf_clean]
                if self.normalized_predicate != expected:
                    raise ValueError(
                        f"Rule 'frozen_map' requires normalized_predicate to equal '{expected}' "
                        f"for surface '{surf_clean}', got '{self.normalized_predicate}'"
                    )
            else:
                raise ValueError(
                    f"Surface predicate '{surf_clean}' is not in FROZEN_PREDICATE_MAP: {list(FROZEN_PREDICATE_MAP.keys())}"
                )
        return self


class SemanticUnit(BaseModel):
    """Atomic, source-grounded semantic unit (proposition, event, state, or attitude)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    annotation_id: str = Field(min_length=1)
    provenance: UnitProvenance
    source_span: SourceSpan
    kind: UnitKind
    predicate: PredicateSpec
    arguments: dict[str, ArgumentMention] = Field(default_factory=dict)
    polarity: PolarityType
    modality: ModalityType
    epistemic_hedge: EpistemicHedge = Field(
        default=EpistemicHedge.NONE,
        description="Outer epistemic hedging (e.g. 'think', 'probable') decoupled from inner matrix modality",
    )
    holder_ref: str = Field(
        min_length=1,
        description="Entity reference of holder (e.g. 'user', 'Alice', 'VP', 'system', 'unknown')",
    )
    attribution_mode: AttributionMode = Field(
        description="Mode of attribution (direct_speaker, direct_quote, indirect_report, external_source, unknown)"
    )
    temporal_anchoring: TemporalAnchoring
    evidence_status: EvidenceStatus
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("kind")
    @classmethod
    def validate_kind_not_forbidden(cls, k: UnitKind) -> UnitKind:
        if k.value.upper() in FORBIDDEN_LABELS:
            raise ValueError(f"Forbidden label '{k.value}' cannot be used as unit kind.")
        return k

    @property
    def is_graph_eligible(self) -> bool:
        """Only explicit and entailed units are eligible as positive graph nodes in v0.1/#16/#17."""
        return self.evidence_status in GRAPH_ADMISSIBLE_EVIDENCE_STATUSES

    def to_graph_node(self) -> dict[str, Any]:
        """Serialize as an authoritative graph node. Fails if evidence_status is audit-only (inferred/unknown)."""
        if not self.is_graph_eligible:
            raise ValueError(
                f"Unit '{self.annotation_id}' with evidence_status='{self.evidence_status.value}' "
                "is audit-only and MUST NOT become a positive graph node in v0.1/#16/#17."
            )
        return {
            "annotation_id": self.annotation_id,
            "kind": self.kind.value,
            "predicate": self.predicate.normalized_predicate,
            "polarity": self.polarity.value,
            "modality": self.modality.value,
            "epistemic_hedge": self.epistemic_hedge.value,
            "holder_ref": self.holder_ref,
            "attribution_mode": self.attribution_mode.value,
            "temporal_anchoring": {
                "normalized_value": self.temporal_anchoring.normalized_value,
                "anchor_type": self.temporal_anchoring.anchor_type.value,
            },
            "evidence_status": self.evidence_status.value,
            "confidence": self.confidence,
        }


class SemanticRelation(BaseModel):
    """Typed relation linking two units or two stable mention IDs."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    relation_id: str = Field(min_length=1)
    source_id: str = Field(
        min_length=1,
        description="Source endpoint: unit annotation_id (e.g. 'u1') or stable mention_id (e.g. 'm_001')",
    )
    target_id: str = Field(
        min_length=1,
        description="Target endpoint: unit annotation_id (e.g. 'u2') or stable mention_id (e.g. 'm_002')",
    )
    relation_type: RelationType
    evidence_status: EvidenceStatus
    confidence: float = Field(ge=0.0, le=1.0)
    provenance: RelationProvenance
    supporting_spans: list[SourceSpan] = Field(default_factory=list)

    @field_validator("relation_type")
    @classmethod
    def validate_relation_not_forbidden(cls, rel: RelationType) -> RelationType:
        if rel.value in FORBIDDEN_LABELS:
            raise ValueError(
                f"Forbidden downstream cognition label '{rel.value}' cannot be used as a relation type."
            )
        return rel

    @property
    def is_graph_edge(self) -> bool:
        """Graph admission freeze: only explicit and entailed non-control relations are positive graph edges."""
        return (
            self.relation_type not in CONTROL_RELATION_TYPES
            and self.evidence_status in GRAPH_ADMISSIBLE_EVIDENCE_STATUSES
        )

    def to_graph_edge(self) -> dict[str, Any]:
        """Serialize as an authoritative graph edge. Fails if control label or audit-only (inferred/unknown)."""
        if self.relation_type in CONTROL_RELATION_TYPES:
            raise ValueError(
                f"Control label '{self.relation_type.value}' cannot be serialized as a positive graph edge."
            )
        if self.evidence_status not in GRAPH_ADMISSIBLE_EVIDENCE_STATUSES:
            raise ValueError(
                f"Relation '{self.relation_id}' with evidence_status='{self.evidence_status.value}' "
                "is audit-only and MUST NOT become a positive graph edge in v0.1/#16/#17."
            )
        return {
            "relation_id": self.relation_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "evidence_status": self.evidence_status.value,
            "confidence": self.confidence,
            "provenance": {
                "raw_evidence_id": self.provenance.raw_evidence_id,
                "semantic_block_id": self.provenance.semantic_block_id,
            },
            "supporting_spans": [s.model_dump() for s in self.supporting_spans],
        }


class SemanticAnnotationDocument(BaseModel):
    """A collection of semantic units and relations within a cutoff-bounded context."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str = Field(min_length=1)
    cutoff_time: str = Field(description="ISO 8601 UTC cutoff timestamp")
    units: list[SemanticUnit]
    relations: list[SemanticRelation]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_document_semantics(self) -> SemanticAnnotationDocument:
        # 1. Check unit uniqueness and collect stable mention IDs
        unit_map: dict[str, SemanticUnit] = {}
        mention_map: dict[str, ArgumentMention] = {}

        for u in self.units:
            if u.annotation_id in unit_map:
                raise ValueError(f"Duplicate unit annotation_id: '{u.annotation_id}'")
            unit_map[u.annotation_id] = u

            for role_name, arg_mention in u.arguments.items():
                m_id = arg_mention.mention_id
                if m_id in mention_map:
                    raise ValueError(
                        f"Duplicate mention_id '{m_id}' found in unit '{u.annotation_id}' argument '{role_name}'"
                    )
                mention_map[m_id] = arg_mention

        # 2. Check relation uniqueness and endpoints
        rel_ids: set[str] = set()
        for r in self.relations:
            if r.relation_id in rel_ids:
                raise ValueError(f"Duplicate relation_id: '{r.relation_id}'")
            rel_ids.add(r.relation_id)

            if r.relation_type == RelationType.SAME_ENTITY:
                # SAME_ENTITY must strictly connect stable mention IDs
                if ":" in r.source_id or ":" in r.target_id:
                    raise ValueError(
                        f"SAME_ENTITY relation '{r.relation_id}' must connect stable mention IDs, "
                        f"not '<unit_id>:<role>' pseudo-identifiers. Got source='{r.source_id}', target='{r.target_id}'"
                    )
                if r.source_id not in mention_map:
                    raise ValueError(
                        f"SAME_ENTITY relation '{r.relation_id}' source_id '{r.source_id}' "
                        f"not found in document mention IDs: {sorted(mention_map.keys())}"
                    )
                if r.target_id not in mention_map:
                    raise ValueError(
                        f"SAME_ENTITY relation '{r.relation_id}' target_id '{r.target_id}' "
                        f"not found in document mention IDs: {sorted(mention_map.keys())}"
                    )
            else:
                # Other relations connect unit annotation IDs
                if r.source_id not in unit_map:
                    raise ValueError(
                        f"Relation '{r.relation_id}' source_id '{r.source_id}' not found in units"
                    )
                if r.target_id not in unit_map:
                    raise ValueError(
                        f"Relation '{r.relation_id}' target_id '{r.target_id}' not found in units"
                    )

            # 3. Check INCOMPATIBLE temporal overlap requirement
            if r.relation_type == RelationType.INCOMPATIBLE:
                u_src = unit_map[r.source_id]
                u_tgt = unit_map[r.target_id]
                t_src = u_src.temporal_anchoring
                t_tgt = u_tgt.temporal_anchoring
                if (
                    t_src.anchor_type == TemporalAnchorType.EXACT
                    and t_tgt.anchor_type == TemporalAnchorType.EXACT
                    and t_src.normalized_value != t_tgt.normalized_value
                ):
                    raise ValueError(
                        f"Relation '{r.relation_id}' asserts INCOMPATIBLE between '{r.source_id}' "
                        f"({t_src.normalized_value}) and '{r.target_id}' ({t_tgt.normalized_value}) "
                        "at non-overlapping exact times. INCOMPATIBLE requires overlapping temporal validity; "
                        "cross-time shifts must be modeled via temporal ordering (BEFORE) and opposite polarities/values."
                    )

        return self
