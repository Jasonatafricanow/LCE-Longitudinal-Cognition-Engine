"""Typed data models for the Issue #16 Longitudinal Fixture Corpus."""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from research.semantic_annotation.schema import SemanticAnnotationDocument


class EvidenceItem(BaseModel):
    """Raw evidence entry with timestamp."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence_id: str
    content: str
    occurred_at: str


class A0SemanticBlock(BaseModel):
    """A0 coarse semantic boundary unit (Semantic Block) grouping evidence."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    block_id: str
    evidence_ids: list[str]
    text: str
    occurred_start: str
    occurred_end: str


class TargetOracle(BaseModel):
    """Ground-truth structural expectation defined outside the graph."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    target_id: str
    target_type: str  # "bridge", "recurrence", "revision", "causality", "attribution", "entity_trajectory", "causal_chain", "distractor_rejection"
    target_unit_ids: list[str]  # Responsible atomic units
    target_block_ids: list[str]  # Corresponding A0 boundary blocks
    description: str


class CutoffView(BaseModel):
    """Visible window at a specific cutoff timestamp."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    cutoff_time: str
    visible_evidence_ids: list[str]
    visible_a0_block_ids: list[str]
    visible_unit_ids: list[str]
    is_target_evaluable: bool  # Can the target be evaluated at this cutoff?


class LongitudinalFixture(BaseModel):
    """A multi-cutoff longitudinal fixture for evaluating A0 vs A1 vs B."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    fixture_id: str
    family: str
    description: str
    evidence: list[EvidenceItem]
    cutoffs: list[CutoffView]
    a0_blocks: list[A0SemanticBlock]
    gold_document: SemanticAnnotationDocument
    oracle: TargetOracle
    noise_variant: dict[str, Any] | None = None
    shuffle_control: dict[str, Any] | None = None
