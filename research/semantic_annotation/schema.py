"""Canonical machine-readable schema and validation for LCE Semantic Annotation v0.1.

Research-only specification (GitHub Issue #13).
This module serves as the single CANONICAL schema for v0.1 semantic annotation contracts.
JSON Schemas under research/schemas/ are validated against or derived from this module.
Does not modify production runtime or contracts.
"""

from __future__ import annotations

from enum import Enum
import re
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


class TemporalAnchorType(str, Enum):
    EXACT = "exact"
    BOUNDED_RANGE = "bounded_range"
    RELATIVE = "relative"
    UNANCHORED = "unanchored"


class RelationType(str, Enum):
    # Identity (applies to argument mentions/referents)
    SAME_ENTITY = "SAME_ENTITY"
    SAME_EVENT = "SAME_EVENT"

    # Temporal (applies to proposition/event units)
    BEFORE = "BEFORE"
    AFTER = "AFTER"
    OVERLAP = "OVERLAP"
    TEMPORAL_UNKNOWN = "TEMPORAL_UNKNOWN"

    # Logical / Discourse (applies to proposition/event units)
    CAUSE = "CAUSE"
    CONDITION = "CONDITION"
    PURPOSE = "PURPOSE"
    CONTRAST = "CONTRAST"
    CONCESSION = "CONCESSION"

    # State Compatibility (applies to proposition/state/attitude units with overlapping time)
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
    """A grounded argument mention linked to a conservative semantic role."""

    model_config = ConfigDict(frozen=True, extra="forbid")

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
            # If relative, reference_anchor must be explicitly provided
            raise ValueError(
                "Relative temporal anchor must specify 'reference_anchor' (e.g. 'evidence:occurred_at')"
            )
        return self


class PredicateSpec(BaseModel):
    """Surface form, normalized predicate lemma/frame, and the reproducible normalization rule."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    surface_predicate: str = Field(min_length=1, description="Verbatim predicate/verb/expression from text")
    normalized_predicate: str = Field(min_length=1, description="Normalized lemma or standard frame label")
    normalization_rule: str = Field(
        min_length=1,
        description="Explicit rule name or method (e.g. 'verb_lemma', 'shallow_nested_hedge', 'exact_match')",
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


class SemanticRelation(BaseModel):
    """Typed relation linking two units or two argument mentions."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    relation_id: str = Field(min_length=1)
    source_id: str = Field(
        min_length=1,
        description="Source endpoint: unit annotation_id (e.g. 'u1') or argument mention (e.g. 'u1:actor')",
    )
    target_id: str = Field(
        min_length=1,
        description="Target endpoint: unit annotation_id (e.g. 'u2') or argument mention (e.g. 'u2:theme')",
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
        """Control labels (NO_RELATION, UNKNOWN, TEMPORAL_UNKNOWN) are not valid graph edges."""
        return self.relation_type not in CONTROL_RELATION_TYPES

    def to_graph_edge(self) -> dict[str, Any]:
        """Serialize as an authoritative graph edge. Fails if relation is a control outcome."""
        if not self.is_graph_edge:
            raise ValueError(
                f"Control label '{self.relation_type.value}' cannot be serialized as a positive graph edge."
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
        # 1. Check unit uniqueness
        unit_map: dict[str, SemanticUnit] = {}
        for u in self.units:
            if u.annotation_id in unit_map:
                raise ValueError(f"Duplicate unit annotation_id: '{u.annotation_id}'")
            unit_map[u.annotation_id] = u

        # 2. Check relation uniqueness and endpoints
        rel_ids: set[str] = set()
        for r in self.relations:
            if r.relation_id in rel_ids:
                raise ValueError(f"Duplicate relation_id: '{r.relation_id}'")
            rel_ids.add(r.relation_id)

            # Validate endpoints according to relation type
            if r.relation_type == RelationType.SAME_ENTITY:
                # SAME_ENTITY must target argument mentions, e.g. "u1:actor"
                self._validate_argument_endpoint(r.source_id, unit_map, r.relation_id, "source_id")
                self._validate_argument_endpoint(r.target_id, unit_map, r.relation_id, "target_id")
            else:
                # Other relations target proposition unit IDs directly
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
                # If both units have exact different temporal anchors, they are cross-time shifts, not INCOMPATIBLE!
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

    @staticmethod
    def _validate_argument_endpoint(
        endpoint: str,
        unit_map: dict[str, SemanticUnit],
        rel_id: str,
        endpoint_name: str,
    ) -> None:
        """Validate an argument mention endpoint formatted as 'unit_id:role'."""
        if ":" not in endpoint:
            raise ValueError(
                f"SAME_ENTITY relation '{rel_id}' {endpoint_name} '{endpoint}' must specify an argument "
                "mention in format '<unit_id>:<role>' (e.g. 'u1:actor'). Proposition IDs cannot be SAME_ENTITY."
            )
        u_id, role = endpoint.split(":", 1)
        if u_id not in unit_map:
            raise ValueError(
                f"Relation '{rel_id}' {endpoint_name} '{endpoint}' references non-existent unit '{u_id}'"
            )
        unit = unit_map[u_id]
        if role not in unit.arguments:
            raise ValueError(
                f"Relation '{rel_id}' {endpoint_name} '{endpoint}' references role '{role}' "
                f"which does not exist on unit '{u_id}' (available roles: {list(unit.arguments.keys())})"
            )
