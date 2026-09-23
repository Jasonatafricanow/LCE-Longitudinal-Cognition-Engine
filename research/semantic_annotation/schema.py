"""Machine-readable schema and validation for LCE Semantic Annotation v0.1.

Research-only specification (GitHub Issue #13). Does not modify production runtime.
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


class HolderSource(str, Enum):
    USER = "user"
    QUOTED = "quoted"
    REPORTED = "reported"
    SYSTEM = "system"
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
    # Identity
    SAME_ENTITY = "SAME_ENTITY"
    SAME_EVENT = "SAME_EVENT"

    # Temporal
    BEFORE = "BEFORE"
    AFTER = "AFTER"
    OVERLAP = "OVERLAP"
    TEMPORAL_UNKNOWN = "TEMPORAL_UNKNOWN"

    # Logical / Discourse
    CAUSE = "CAUSE"
    CONDITION = "CONDITION"
    PURPOSE = "PURPOSE"
    CONTRAST = "CONTRAST"
    CONCESSION = "CONCESSION"

    # State Compatibility
    EQUIVALENT = "EQUIVALENT"
    INCOMPATIBLE = "INCOMPATIBLE"

    # Control
    NO_RELATION = "NO_RELATION"
    UNKNOWN = "UNKNOWN"


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


class TemporalAnchoring(BaseModel):
    """Normalized temporal anchoring information."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    value: str = Field(min_length=1, description="ISO date/range or 'unknown'")
    anchor_type: TemporalAnchorType
    source_expression: str | None = Field(default=None, description="Verbatim temporal expression")


class SemanticUnit(BaseModel):
    """Atomic, source-grounded semantic unit (proposition, event, state, or attitude)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    annotation_id: str = Field(min_length=1)
    provenance: UnitProvenance
    source_span: SourceSpan
    kind: UnitKind
    predicate: str = Field(min_length=1)
    arguments: dict[str, str] = Field(default_factory=dict)
    polarity: PolarityType
    modality: ModalityType
    holder: HolderSource
    temporal_anchoring: TemporalAnchoring
    evidence_status: EvidenceStatus
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("arguments")
    @classmethod
    def validate_argument_roles(cls, args: dict[str, str]) -> dict[str, str]:
        for role in args:
            if role not in ROLE_VOCABULARY:
                raise ValueError(
                    f"Invalid argument role '{role}'. Role must be one of: {sorted(ROLE_VOCABULARY)}"
                )
        return args

    @field_validator("predicate")
    @classmethod
    def validate_predicate_not_forbidden(cls, pred: str) -> str:
        upper_pred = pred.strip().upper()
        if upper_pred in FORBIDDEN_LABELS:
            raise ValueError(
                f"Forbidden downstream cognition label '{pred}' cannot be used as a unit predicate."
            )
        return pred


class SemanticRelation(BaseModel):
    """Typed relation linking two SemanticUnit instances."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    relation_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    relation_type: RelationType
    evidence_status: EvidenceStatus
    confidence: float = Field(ge=0.0, le=1.0)
    provenance_spans: list[SourceSpan] = Field(default_factory=list)

    @field_validator("relation_type")
    @classmethod
    def validate_relation_not_forbidden(cls, rel: RelationType) -> RelationType:
        if rel.value in FORBIDDEN_LABELS:
            raise ValueError(
                f"Forbidden downstream cognition label '{rel.value}' cannot be used as a relation type."
            )
        return rel


class SemanticAnnotationDocument(BaseModel):
    """A collection of semantic units and relations within a cutoff-bounded context."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str = Field(min_length=1)
    cutoff_time: str = Field(description="ISO 8601 UTC cutoff timestamp")
    units: list[SemanticUnit]
    relations: list[SemanticRelation]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_referential_integrity(self) -> SemanticAnnotationDocument:
        unit_ids = set()
        for u in self.units:
            if u.annotation_id in unit_ids:
                raise ValueError(f"Duplicate unit annotation_id: '{u.annotation_id}'")
            unit_ids.add(u.annotation_id)

        rel_ids = set()
        for r in self.relations:
            if r.relation_id in rel_ids:
                raise ValueError(f"Duplicate relation_id: '{r.relation_id}'")
            rel_ids.add(r.relation_id)

            if r.source_id not in unit_ids:
                raise ValueError(
                    f"Relation '{r.relation_id}' has dangling source_id '{r.source_id}' not found in units"
                )
            if r.target_id not in unit_ids:
                raise ValueError(
                    f"Relation '{r.relation_id}' has dangling target_id '{r.target_id}' not found in units"
                )

        return self
