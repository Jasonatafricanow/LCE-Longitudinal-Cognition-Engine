"""Immutable Pydantic data models for the Oracle Typed Graph Representation.

Formalizes the two-level typed property graph:
- V_U: Proposition Unit Nodes (events, states, attitudes, propositions)
- V_M: Entity Mention Nodes (grounded arguments)
- V_E: Canonical Entity Clusters (resolved via SAME_ENTITY equivalence classes)
- E_prop: Inter-unit proposition relation edges (temporal, causal, discourse, incompatibility)
- E_arg: Unit-to-mention argument participation edges
- E_coref: Mention-to-mention coreference edges
"""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class UnitGraphNode(BaseModel):
    """Authoritative proposition unit node admitted into the typed graph."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    node_id: str = Field(min_length=1, description="Unique node identifier, e.g. 'u1' or 'case_01:u1'")
    kind: str = Field(description="Unit kind: event, state, attitude, proposition")
    predicate: str = Field(description="Mechanically normalized predicate")
    polarity: str = Field(description="positive or negative")
    modality: str = Field(description="asserted, intended, desired, hypothetical, etc.")
    epistemic_hedge: str = Field(description="Epistemic hedge: none, think, probable, etc.")
    holder_ref: str = Field(description="Holder reference identifier")
    attribution_mode: str = Field(description="Attribution mode: direct_speaker, direct_quote, etc.")
    temporal_anchoring: dict[str, str] = Field(description="Normalized temporal anchor and anchor type")
    evidence_status: str = Field(description="Grounding: explicit or entailed")
    confidence: float = Field(ge=0.0, le=1.0)
    provenance: dict[str, str] = Field(default_factory=dict)


class MentionGraphNode(BaseModel):
    """Grounded entity argument mention node."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mention_id: str = Field(min_length=1, description="Globally unique mention identifier, e.g. 'm1'")
    unit_id: str = Field(min_length=1, description="Parent unit annotation ID")
    role: str = Field(description="Approved role from ROLE_VOCABULARY")
    text: str = Field(min_length=1, description="Verbatim mention surface text")
    entity_ref: str | None = Field(default=None, description="Explicit entity label if present")
    canonical_entity_id: str | None = Field(default=None, description="Assigned canonical entity cluster ID")


class CanonicalEntityNode(BaseModel):
    """Unified entity cluster resolved via transitive closure over SAME_ENTITY."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    entity_id: str = Field(min_length=1, description="Canonical entity cluster ID, e.g. 'ent_alice'")
    mention_ids: list[str] = Field(min_length=1, description="Member mention IDs in cluster")
    canonical_label: str = Field(min_length=1, description="Representative surface label")


class RelationGraphEdge(BaseModel):
    """Admitted directed typed relation edge linking units or mentions."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    relation_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1, description="Source unit or mention ID")
    target_id: str = Field(min_length=1, description="Target unit or mention ID")
    relation_type: str = Field(description="Admitted relation type (BEFORE, CAUSE, INCOMPATIBLE, SAME_ENTITY, etc.)")
    evidence_status: str = Field(description="explicit or entailed")
    confidence: float = Field(ge=0.0, le=1.0)
    provenance: dict[str, str] = Field(default_factory=dict)
    supporting_spans: list[dict[str, Any]] = Field(default_factory=list)


class ArgumentGraphEdge(BaseModel):
    """Directed edge linking a proposition unit node to an argument mention node."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_unit_id: str = Field(min_length=1)
    target_mention_id: str = Field(min_length=1)
    role: str = Field(description="Role from ROLE_VOCABULARY")


class OracleTypedGraph(BaseModel):
    """Container for a canonical Oracle Typed Graph."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    graph_id: str = Field(min_length=1)
    cutoff_time: str = Field(description="ISO 8601 cutoff timestamp")
    unit_nodes: dict[str, UnitGraphNode] = Field(default_factory=dict)
    mention_nodes: dict[str, MentionGraphNode] = Field(default_factory=dict)
    canonical_entities: dict[str, CanonicalEntityNode] = Field(default_factory=dict)
    relation_edges: list[RelationGraphEdge] = Field(default_factory=list)
    argument_edges: list[ArgumentGraphEdge] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def node_count(self) -> int:
        return len(self.unit_nodes)

    @property
    def edge_count(self) -> int:
        return len(self.relation_edges)

    @property
    def mention_count(self) -> int:
        return len(self.mention_nodes)
