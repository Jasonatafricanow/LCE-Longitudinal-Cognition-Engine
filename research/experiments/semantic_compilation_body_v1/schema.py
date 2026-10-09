"""Typed Schema for Semantic Compilation Body/AGY Experiment V1.

Fulfills §11, §12, §13, §14 of experiment specification.
Enforces structural logic without closed business ontology.
"""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


SpeechAct = Literal["assertion", "question", "directive", "other"]
Polarity = Literal["positive", "negative", "unknown"]
EpistemicStatus = Literal[
    "asserted",
    "uncertain",
    "hypothetical",
    "counterfactual",
    "planned",
    "reported",
    "unknown",
]
TemporalKind = Literal["past", "current", "future", "atemporal", "unknown"]
BoundaryPolicy = Literal["cohabit", "context", "separate"]
PointStatus = Literal["resolved", "defer"]


class RawTurn(BaseModel):
    evidence_id: str
    speaker: str = "user"
    text: str
    timestamp: str | None = None


class SemanticPoint(BaseModel):
    local_id: str = Field(description="Unique local identifier, e.g. P01, P02A")
    source_refs: list[str] = Field(default_factory=list, description="Raw evidence IDs grounding this point, e.g. ['E01']")
    meaning: str = Field(description="Open natural language meaning statement representing this semantic component")
    status: PointStatus = Field(default="resolved", description="'resolved' if self-contained/resolved, 'defer' if ambiguous/unresolved")
    speech_act: SpeechAct = Field(default="assertion")
    polarity: Polarity = Field(default="positive")
    epistemic_status: EpistemicStatus = Field(default="asserted")
    temporal: TemporalKind = Field(default="current")
    unresolved_refs: list[str] = Field(default_factory=list, description="Unresolved anaphoric or contextual references")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class SemanticDependency(BaseModel):
    from_point: str = Field(description="Source semantic point ID")
    to_point: str = Field(description="Target semantic point ID")
    relation: str = Field(description="Open string relation name, e.g. condition_scope, updates_state, supersedes, limitation_scope")
    boundary_policy: BoundaryPolicy = Field(
        description=(
            "'cohabit': splitting changes original meaning; must be in same SemanticBlock. "
            "'context': separate longitudinal identity, but target is required supporting context. "
            "'separate': independent semantic points."
        )
    )
    reason: str = Field(default="", description="Brief explanation for boundary policy assignment")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class SemanticParseResultV1(BaseModel):
    schema_version: str = "semantic_parse_v1"
    source_window_refs: list[str] = Field(default_factory=list)
    semantic_points: list[SemanticPoint] = Field(default_factory=list)
    dependencies: list[SemanticDependency] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list, description="List of deferred points or unresolved references")


class SemanticBlock(BaseModel):
    block_id: str
    member_point_ids: list[str]
    context_point_ids: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    analysis_text: str = Field(
        description="Context-complete canonical meaning for embedding and cognition analysis without verbatim context string concatenation"
    )
    speech_act: SpeechAct = "assertion"
    polarity: Polarity = "positive"
    epistemic_status: EpistemicStatus = "asserted"
    temporal: TemporalKind = "current"
