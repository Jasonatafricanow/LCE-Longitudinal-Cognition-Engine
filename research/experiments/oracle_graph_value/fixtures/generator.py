"""Deterministic Generator for the 8 Longitudinal Fixture Families for Issue #16.

Generates:
- F1: delayed_reconnection_bridge
- F2: distant_longitudinal_recurrence
- F3: state_revision_contradiction
- F4: post_hoc_vs_causality
- F5: holder_attribution_split
- F6: cross_domain_entity_carrier
- F7: transitive_causal_chain
- F8: density_distractor_trap
"""
from __future__ import annotations

import random
from typing import Any

from research.experiments.oracle_graph_value.fixtures.models import (
    A0SemanticBlock,
    CutoffView,
    EvidenceItem,
    LongitudinalFixture,
    TargetOracle,
)
from research.semantic_annotation.schema import (
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
    TemporalAnchoring,
    TemporalAnchorType,
    UnitKind,
    UnitProvenance,
)


def _make_unit(
    unit_id: str,
    text: str,
    kind: UnitKind,
    surface_pred: str,
    norm_pred: str,
    polarity: PolarityType = PolarityType.POSITIVE,
    modality: ModalityType = ModalityType.ASSERTED,
    epistemic_hedge: EpistemicHedge = EpistemicHedge.NONE,
    holder_ref: str = "user",
    attribution_mode: AttributionMode = AttributionMode.DIRECT_SPEAKER,
    norm_time: str = "2026-04-01",
    anchor_type: TemporalAnchorType = TemporalAnchorType.EXACT,
    evidence_id: str = "ev_01",
    block_id: str = "b_01",
    evidence_status: EvidenceStatus = EvidenceStatus.EXPLICIT,
    arguments: dict[str, ArgumentMention] | None = None,
) -> SemanticUnit:
    return SemanticUnit(
        annotation_id=unit_id,
        provenance=UnitProvenance(raw_evidence_id=evidence_id, semantic_block_id=block_id),
        source_span=SourceSpan(char_start=0, char_end=len(text), text=text),
        kind=kind,
        predicate=PredicateSpec(
            surface_predicate=surface_pred,
            normalized_predicate=norm_pred,
            normalization_rule=PredicateNormalizationRule.EXACT_SURFACE if norm_pred == surface_pred.lower() else PredicateNormalizationRule.COMPOUND_LOWER,
        ),
        arguments=arguments or {},
        polarity=polarity,
        modality=modality,
        epistemic_hedge=epistemic_hedge,
        holder_ref=holder_ref,
        attribution_mode=attribution_mode,
        temporal_anchoring=TemporalAnchoring(normalized_value=norm_time, anchor_type=anchor_type),
        evidence_status=evidence_status,
        confidence=1.0,
    )


def generate_f1_delayed_bridge() -> LongitudinalFixture:
    """F1: Delayed Reconnection Bridge. Two clusters reconnected across time by a bridging arrival."""
    ev1 = EvidenceItem(evidence_id="ev_f1_1", content="We planned the database migration to PostgreSQL.", occurred_at="2026-04-01T10:00:00Z")
    ev2 = EvidenceItem(evidence_id="ev_f1_2", content="Our monthly AWS cloud infrastructure costs exceeded budget.", occurred_at="2026-04-03T10:00:00Z")
    ev3 = EvidenceItem(evidence_id="ev_f1_3", content="Completing the database migration directly reduced AWS cloud costs by 40%.", occurred_at="2026-04-10T10:00:00Z")

    b1 = A0SemanticBlock(block_id="b_f1_1", evidence_ids=["ev_f1_1"], text=ev1.content, occurred_start=ev1.occurred_at, occurred_end=ev1.occurred_at)
    b2 = A0SemanticBlock(block_id="b_f1_2", evidence_ids=["ev_f1_2"], text=ev2.content, occurred_start=ev2.occurred_at, occurred_end=ev2.occurred_at)
    b3 = A0SemanticBlock(block_id="b_f1_3", evidence_ids=["ev_f1_3"], text=ev3.content, occurred_start=ev3.occurred_at, occurred_end=ev3.occurred_at)

    u1 = _make_unit("u1", "We planned the database migration", UnitKind.EVENT, "planned", "planned", norm_time="2026-04-01", evidence_id="ev_f1_1", block_id="b_f1_1")
    u2 = _make_unit("u2", "cloud infrastructure costs exceeded budget", UnitKind.STATE, "exceeded", "exceeded", norm_time="2026-04-03", evidence_id="ev_f1_2", block_id="b_f1_2")
    u3 = _make_unit("u3", "database migration directly reduced AWS cloud costs", UnitKind.EVENT, "reduced", "reduced", norm_time="2026-04-10", evidence_id="ev_f1_3", block_id="b_f1_3")

    # u3 is the bridge: caused reduction of u2, sequential after u1
    r1 = SemanticRelation(
        relation_id="rel_f1_1", source_id="u1", target_id="u3", relation_type=RelationType.BEFORE,
        evidence_status=EvidenceStatus.EXPLICIT, confidence=1.0,
        provenance=RelationProvenance(raw_evidence_id="ev_f1_3", semantic_block_id="b_f1_3"),
    )
    r2 = SemanticRelation(
        relation_id="rel_f1_2", source_id="u3", target_id="u2", relation_type=RelationType.CAUSE,
        evidence_status=EvidenceStatus.EXPLICIT, confidence=1.0,
        provenance=RelationProvenance(raw_evidence_id="ev_f1_3", semantic_block_id="b_f1_3"),
    )

    doc = SemanticAnnotationDocument(
        document_id="doc_f1", cutoff_time="2026-04-15T00:00:00Z",
        units=[u1, u2, u3], relations=[r1, r2],
    )

    cutoffs = [
        CutoffView(cutoff_time="2026-04-05T00:00:00Z", visible_evidence_ids=["ev_f1_1", "ev_f1_2"], visible_a0_block_ids=["b_f1_1", "b_f1_2"], visible_unit_ids=["u1", "u2"], is_target_evaluable=False),
        CutoffView(cutoff_time="2026-04-12T00:00:00Z", visible_evidence_ids=["ev_f1_1", "ev_f1_2", "ev_f1_3"], visible_a0_block_ids=["b_f1_1", "b_f1_2", "b_f1_3"], visible_unit_ids=["u1", "u2", "u3"], is_target_evaluable=True),
    ]

    oracle = TargetOracle(
        target_id="oracle_f1", target_type="bridge",
        target_unit_ids=["u1", "u3", "u2"], target_block_ids=["b_f1_1", "b_f1_3", "b_f1_2"],
        description="Arrival u3 bridges the separate database cluster u1 with infrastructure cost cluster u2 via CAUSE.",
    )

    return LongitudinalFixture(
        fixture_id="F1_delayed_bridge", family="delayed_reconnection_bridge",
        description="Reconnection of disjoint clusters via bridging unit arriving at T2.",
        evidence=[ev1, ev2, ev3], cutoffs=cutoffs, a0_blocks=[b1, b2, b3],
        gold_document=doc, oracle=oracle,
    )


def generate_f2_distant_recurrence() -> LongitudinalFixture:
    """F2: Distant Longitudinal Recurrence across long temporal gap."""
    ev1 = EvidenceItem(evidence_id="ev_f2_1", content="The auth service experienced high memory saturation.", occurred_at="2026-01-10T08:00:00Z")
    ev2 = EvidenceItem(evidence_id="ev_f2_2", content="We redesigned the frontend navigation menu.", occurred_at="2026-02-20T10:00:00Z")
    ev3 = EvidenceItem(evidence_id="ev_f2_3", content="The team held a quarterly business review.", occurred_at="2026-03-15T14:00:00Z")
    ev4 = EvidenceItem(evidence_id="ev_f2_4", content="The auth service experienced the same high memory saturation.", occurred_at="2026-05-01T09:00:00Z")

    b1 = A0SemanticBlock(block_id="b_f2_1", evidence_ids=["ev_f2_1"], text=ev1.content, occurred_start=ev1.occurred_at, occurred_end=ev1.occurred_at)
    b2 = A0SemanticBlock(block_id="b_f2_2", evidence_ids=["ev_f2_2"], text=ev2.content, occurred_start=ev2.occurred_at, occurred_end=ev2.occurred_at)
    b3 = A0SemanticBlock(block_id="b_f2_3", evidence_ids=["ev_f2_3"], text=ev3.content, occurred_start=ev3.occurred_at, occurred_end=ev3.occurred_at)
    b4 = A0SemanticBlock(block_id="b_f2_4", evidence_ids=["ev_f2_4"], text=ev4.content, occurred_start=ev4.occurred_at, occurred_end=ev4.occurred_at)

    u1 = _make_unit("u1", "auth service experienced high memory saturation", UnitKind.STATE, "experienced", "experienced", norm_time="2026-01-10", evidence_id="ev_f2_1", block_id="b_f2_1")
    u2 = _make_unit("u2", "redesigned the frontend navigation menu", UnitKind.EVENT, "redesigned", "redesigned", norm_time="2026-02-20", evidence_id="ev_f2_2", block_id="b_f2_2")
    u3 = _make_unit("u3", "team held quarterly business review", UnitKind.EVENT, "held", "held", norm_time="2026-03-15", evidence_id="ev_f2_3", block_id="b_f2_3")
    u4 = _make_unit("u4", "auth service experienced high memory saturation", UnitKind.STATE, "experienced", "experienced", norm_time="2026-05-01", evidence_id="ev_f2_4", block_id="b_f2_4")

    # Gold relation: EQUIVALENT recurring state across 4-month gap
    r1 = SemanticRelation(
        relation_id="rel_f2_1", source_id="u1", target_id="u4", relation_type=RelationType.EQUIVALENT,
        evidence_status=EvidenceStatus.EXPLICIT, confidence=1.0,
        provenance=RelationProvenance(raw_evidence_id="ev_f2_4", semantic_block_id="b_f2_4"),
    )

    doc = SemanticAnnotationDocument(
        document_id="doc_f2", cutoff_time="2026-05-05T00:00:00Z",
        units=[u1, u2, u3, u4], relations=[r1],
    )

    cutoffs = [
        CutoffView(cutoff_time="2026-03-01T00:00:00Z", visible_evidence_ids=["ev_f2_1", "ev_f2_2"], visible_a0_block_ids=["b_f2_1", "b_f2_2"], visible_unit_ids=["u1", "u2"], is_target_evaluable=False),
        CutoffView(cutoff_time="2026-05-02T00:00:00Z", visible_evidence_ids=["ev_f2_1", "ev_f2_2", "ev_f2_3", "ev_f2_4"], visible_a0_block_ids=["b_f2_1", "b_f2_2", "b_f2_3", "b_f2_4"], visible_unit_ids=["u1", "u2", "u3", "u4"], is_target_evaluable=True),
    ]

    oracle = TargetOracle(
        target_id="oracle_f2", target_type="recurrence",
        target_unit_ids=["u1", "u4"], target_block_ids=["b_f2_1", "b_f2_4"],
        description="Recurrent memory saturation state at u4 identical to u1 after 4-month gap.",
    )

    return LongitudinalFixture(
        fixture_id="F2_distant_recurrence", family="distant_longitudinal_recurrence",
        description="Distant recurrence of state across 4 months without intermediate links.",
        evidence=[ev1, ev2, ev3, ev4], cutoffs=cutoffs, a0_blocks=[b1, b2, b3, b4],
        gold_document=doc, oracle=oracle,
    )


def generate_f3_state_revision() -> LongitudinalFixture:
    """F3: State Revision vs Temporal Transition. Genuine contradiction vs temporal progression."""
    ev1 = EvidenceItem(evidence_id="ev_f3_1", content="I prefer monolithic architecture for all micro-projects.", occurred_at="2026-03-01T10:00:00Z")
    ev2 = EvidenceItem(evidence_id="ev_f3_2", content="I strictly reject monolithic architecture for micro-projects.", occurred_at="2026-03-05T10:00:00Z")
    ev3 = EvidenceItem(evidence_id="ev_f3_3", content="In 2020 I worked at Company A; in 2026 I work at Company B.", occurred_at="2026-03-10T10:00:00Z")

    b1 = A0SemanticBlock(block_id="b_f3_1", evidence_ids=["ev_f3_1"], text=ev1.content, occurred_start=ev1.occurred_at, occurred_end=ev1.occurred_at)
    b2 = A0SemanticBlock(block_id="b_f3_2", evidence_ids=["ev_f3_2"], text=ev2.content, occurred_start=ev2.occurred_at, occurred_end=ev2.occurred_at)
    b3 = A0SemanticBlock(block_id="b_f3_3", evidence_ids=["ev_f3_3"], text=ev3.content, occurred_start=ev3.occurred_at, occurred_end=ev3.occurred_at)

    u1 = _make_unit("u1", "I prefer monolithic architecture", UnitKind.ATTITUDE, "prefer", "prefer", polarity=PolarityType.POSITIVE, modality=ModalityType.DESIRED, norm_time="2026-03", anchor_type=TemporalAnchorType.BOUNDED_RANGE, evidence_id="ev_f3_1", block_id="b_f3_1")
    u2 = _make_unit("u2", "I strictly reject monolithic architecture", UnitKind.ATTITUDE, "reject", "reject", polarity=PolarityType.NEGATIVE, modality=ModalityType.ASSERTED, norm_time="2026-03", anchor_type=TemporalAnchorType.BOUNDED_RANGE, evidence_id="ev_f3_2", block_id="b_f3_2")
    u3 = _make_unit("u3", "In 2020 I worked at Company A", UnitKind.STATE, "worked", "worked", norm_time="2020", evidence_id="ev_f3_3", block_id="b_f3_3")
    u4 = _make_unit("u4", "in 2026 I work at Company B", UnitKind.STATE, "work", "work", norm_time="2026", evidence_id="ev_f3_3", block_id="b_f3_3")

    # u1 and u2 are INCOMPATIBLE (overlapping validity revision)
    r1 = SemanticRelation(
        relation_id="rel_f3_1", source_id="u1", target_id="u2", relation_type=RelationType.INCOMPATIBLE,
        evidence_status=EvidenceStatus.EXPLICIT, confidence=1.0,
        provenance=RelationProvenance(raw_evidence_id="ev_f3_2", semantic_block_id="b_f3_2"),
    )
    # u3 and u4 are BEFORE (cross-time transition, NOT INCOMPATIBLE)
    r2 = SemanticRelation(
        relation_id="rel_f3_2", source_id="u3", target_id="u4", relation_type=RelationType.BEFORE,
        evidence_status=EvidenceStatus.EXPLICIT, confidence=1.0,
        provenance=RelationProvenance(raw_evidence_id="ev_f3_3", semantic_block_id="b_f3_3"),
    )

    doc = SemanticAnnotationDocument(
        document_id="doc_f3", cutoff_time="2026-03-15T00:00:00Z",
        units=[u1, u2, u3, u4], relations=[r1, r2],
    )

    cutoffs = [
        CutoffView(cutoff_time="2026-03-03T00:00:00Z", visible_evidence_ids=["ev_f3_1"], visible_a0_block_ids=["b_f3_1"], visible_unit_ids=["u1"], is_target_evaluable=False),
        CutoffView(cutoff_time="2026-03-12T00:00:00Z", visible_evidence_ids=["ev_f3_1", "ev_f3_2", "ev_f3_3"], visible_a0_block_ids=["b_f3_1", "b_f3_2", "b_f3_3"], visible_unit_ids=["u1", "u2", "u3", "u4"], is_target_evaluable=True),
    ]

    oracle = TargetOracle(
        target_id="oracle_f3", target_type="revision",
        target_unit_ids=["u1", "u2"], target_block_ids=["b_f3_1", "b_f3_2"],
        description="Genuine state contradiction between u1 and u2 (INCOMPATIBLE), while u3->u4 is temporal progression.",
    )

    return LongitudinalFixture(
        fixture_id="F3_state_revision", family="state_revision_contradiction",
        description="True state incompatibility vs cross-temporal job transition.",
        evidence=[ev1, ev2, ev3], cutoffs=cutoffs, a0_blocks=[b1, b2, b3],
        gold_document=doc, oracle=oracle,
    )


def generate_f4_post_hoc_causality() -> LongitudinalFixture:
    """F4: Post-hoc temporal succession vs genuine causal connection."""
    ev1 = EvidenceItem(evidence_id="ev_f4_1", content="It rained heavily in Seattle this morning.", occurred_at="2026-04-01T08:00:00Z")
    ev2 = EvidenceItem(evidence_id="ev_f4_2", content="The CI build failed with compilation errors.", occurred_at="2026-04-01T08:05:00Z")
    ev3 = EvidenceItem(evidence_id="ev_f4_3", content="Developer Bob merged a syntax error in main.", occurred_at="2026-04-01T09:00:00Z")
    ev4 = EvidenceItem(evidence_id="ev_f4_4", content="The staging deploy failed because of Bob's syntax error.", occurred_at="2026-04-01T09:15:00Z")

    b1 = A0SemanticBlock(block_id="b_f4_1", evidence_ids=["ev_f4_1"], text=ev1.content, occurred_start=ev1.occurred_at, occurred_end=ev1.occurred_at)
    b2 = A0SemanticBlock(block_id="b_f4_2", evidence_ids=["ev_f4_2"], text=ev2.content, occurred_start=ev2.occurred_at, occurred_end=ev2.occurred_at)
    b3 = A0SemanticBlock(block_id="b_f4_3", evidence_ids=["ev_f4_3"], text=ev3.content, occurred_start=ev3.occurred_at, occurred_end=ev3.occurred_at)
    b4 = A0SemanticBlock(block_id="b_f4_4", evidence_ids=["ev_f4_4"], text=ev4.content, occurred_start=ev4.occurred_at, occurred_end=ev4.occurred_at)

    u1 = _make_unit("u1", "rained heavily in Seattle", UnitKind.EVENT, "rained", "rained", norm_time="2026-04-01T08:00", evidence_id="ev_f4_1", block_id="b_f4_1")
    u2 = _make_unit("u2", "CI build failed", UnitKind.EVENT, "failed", "failed", norm_time="2026-04-01T08:05", evidence_id="ev_f4_2", block_id="b_f4_2")
    u3 = _make_unit("u3", "merged syntax error in main", UnitKind.EVENT, "merged", "merged", norm_time="2026-04-01T09:00", evidence_id="ev_f4_3", block_id="b_f4_3")
    u4 = _make_unit("u4", "staging deploy failed", UnitKind.EVENT, "failed", "failed", norm_time="2026-04-01T09:15", evidence_id="ev_f4_4", block_id="b_f4_4")

    # u1 and u2 are strictly BEFORE (post hoc succession, NOT CAUSE)
    r1 = SemanticRelation(
        relation_id="rel_f4_1", source_id="u1", target_id="u2", relation_type=RelationType.BEFORE,
        evidence_status=EvidenceStatus.EXPLICIT, confidence=1.0,
        provenance=RelationProvenance(raw_evidence_id="ev_f4_2", semantic_block_id="b_f4_2"),
    )
    # u3 and u4 are CAUSE (genuine causal link with connective 'because of')
    r2 = SemanticRelation(
        relation_id="rel_f4_2", source_id="u3", target_id="u4", relation_type=RelationType.CAUSE,
        evidence_status=EvidenceStatus.EXPLICIT, confidence=1.0,
        provenance=RelationProvenance(raw_evidence_id="ev_f4_4", semantic_block_id="b_f4_4"),
        supporting_spans=[SourceSpan(char_start=26, char_end=36, text="because of")],
    )

    doc = SemanticAnnotationDocument(
        document_id="doc_f4", cutoff_time="2026-04-01T12:00:00Z",
        units=[u1, u2, u3, u4], relations=[r1, r2],
    )

    cutoffs = [
        CutoffView(cutoff_time="2026-04-01T08:30:00Z", visible_evidence_ids=["ev_f4_1", "ev_f4_2"], visible_a0_block_ids=["b_f4_1", "b_f4_2"], visible_unit_ids=["u1", "u2"], is_target_evaluable=False),
        CutoffView(cutoff_time="2026-04-01T10:00:00Z", visible_evidence_ids=["ev_f4_1", "ev_f4_2", "ev_f4_3", "ev_f4_4"], visible_a0_block_ids=["b_f4_1", "b_f4_2", "b_f4_3", "b_f4_4"], visible_unit_ids=["u1", "u2", "u3", "u4"], is_target_evaluable=True),
    ]

    oracle = TargetOracle(
        target_id="oracle_f4", target_type="causality",
        target_unit_ids=["u3", "u4"], target_block_ids=["b_f4_3", "b_f4_4"],
        description="Genuine causal relationship between u3 and u4, rejecting spurious post-hoc causality between u1 and u2.",
    )

    return LongitudinalFixture(
        fixture_id="F4_post_hoc_vs_causality", family="post_hoc_vs_causality",
        description="Temporal succession without cause vs genuine connective-backed causality.",
        evidence=[ev1, ev2, ev3, ev4], cutoffs=cutoffs, a0_blocks=[b1, b2, b3, b4],
        gold_document=doc, oracle=oracle,
    )


def generate_f5_holder_attribution() -> LongitudinalFixture:
    """F5: Holder Attribution Divergence. Author conviction vs 3rd-party quote."""
    ev1 = EvidenceItem(evidence_id="ev_f5_1", content="The external consultant stated 'Rust is inappropriate for enterprise systems'.", occurred_at="2026-04-01T10:00:00Z")
    ev2 = EvidenceItem(evidence_id="ev_f5_2", content="We adopted Rust for our core enterprise microservices.", occurred_at="2026-04-05T10:00:00Z")

    b1 = A0SemanticBlock(block_id="b_f5_1", evidence_ids=["ev_f5_1"], text=ev1.content, occurred_start=ev1.occurred_at, occurred_end=ev1.occurred_at)
    b2 = A0SemanticBlock(block_id="b_f5_2", evidence_ids=["ev_f5_2"], text=ev2.content, occurred_start=ev2.occurred_at, occurred_end=ev2.occurred_at)

    u1 = _make_unit("u1", "Rust is inappropriate for enterprise systems", UnitKind.PROPOSITION, "inappropriate", "inappropriate", holder_ref="consultant", attribution_mode=AttributionMode.DIRECT_QUOTE, norm_time="2026-04-01", evidence_id="ev_f5_1", block_id="b_f5_1")
    u2 = _make_unit("u2", "We adopted Rust for our core enterprise microservices", UnitKind.EVENT, "adopted", "adopted", holder_ref="user", attribution_mode=AttributionMode.DIRECT_SPEAKER, norm_time="2026-04-05", evidence_id="ev_f5_2", block_id="b_f5_2")

    r1 = SemanticRelation(
        relation_id="rel_f5_1", source_id="u1", target_id="u2", relation_type=RelationType.BEFORE,
        evidence_status=EvidenceStatus.EXPLICIT, confidence=1.0,
        provenance=RelationProvenance(raw_evidence_id="ev_f5_2", semantic_block_id="b_f5_2"),
    )

    doc = SemanticAnnotationDocument(
        document_id="doc_f5", cutoff_time="2026-04-10T00:00:00Z",
        units=[u1, u2], relations=[r1],
    )

    cutoffs = [
        CutoffView(cutoff_time="2026-04-03T00:00:00Z", visible_evidence_ids=["ev_f5_1"], visible_a0_block_ids=["b_f5_1"], visible_unit_ids=["u1"], is_target_evaluable=False),
        CutoffView(cutoff_time="2026-04-08T00:00:00Z", visible_evidence_ids=["ev_f5_1", "ev_f5_2"], visible_a0_block_ids=["b_f5_1", "b_f5_2"], visible_unit_ids=["u1", "u2"], is_target_evaluable=True),
    ]

    oracle = TargetOracle(
        target_id="oracle_f5", target_type="attribution",
        target_unit_ids=["u1", "u2"], target_block_ids=["b_f5_1", "b_f5_2"],
        description="Holder attribution divergence: u1 is external consultant quote; u2 is user adoption. Not author contradiction.",
    )

    return LongitudinalFixture(
        fixture_id="F5_holder_attribution", family="holder_attribution_split",
        description="Decoupling third-party claim from author decision despite high lexical overlap.",
        evidence=[ev1, ev2], cutoffs=cutoffs, a0_blocks=[b1, b2],
        gold_document=doc, oracle=oracle,
    )


def generate_f6_cross_domain_entity() -> LongitudinalFixture:
    """F6: Cross-Domain Entity Carrier. An entity coreferenced across distant domains."""
    ev1 = EvidenceItem(evidence_id="ev_f6_1", content="Alice overhauled the real-time financial clearing pipeline.", occurred_at="2026-04-01T10:00:00Z")
    ev2 = EvidenceItem(evidence_id="ev_f6_2", content="The team evaluated new payment settlement vendors.", occurred_at="2026-04-03T10:00:00Z")
    ev3 = EvidenceItem(evidence_id="ev_f6_3", content="She published an open-source synthesizer for ambient electronic music.", occurred_at="2026-04-15T10:00:00Z")

    b1 = A0SemanticBlock(block_id="b_f6_1", evidence_ids=["ev_f6_1"], text=ev1.content, occurred_start=ev1.occurred_at, occurred_end=ev1.occurred_at)
    b2 = A0SemanticBlock(block_id="b_f6_2", evidence_ids=["ev_f6_2"], text=ev2.content, occurred_start=ev2.occurred_at, occurred_end=ev2.occurred_at)
    b3 = A0SemanticBlock(block_id="b_f6_3", evidence_ids=["ev_f6_3"], text=ev3.content, occurred_start=ev3.occurred_at, occurred_end=ev3.occurred_at)

    m1 = ArgumentMention(mention_id="m_f6_1", role="actor", text="Alice", entity_ref="Alice")
    m2 = ArgumentMention(mention_id="m_f6_2", role="actor", text="She", entity_ref="Alice")

    u1 = _make_unit("u1", "Alice overhauled real-time financial clearing pipeline", UnitKind.EVENT, "overhauled", "overhauled", norm_time="2026-04-01", evidence_id="ev_f6_1", block_id="b_f6_1", arguments={"actor": m1})
    u2 = _make_unit("u2", "team evaluated payment settlement vendors", UnitKind.EVENT, "evaluated", "evaluated", norm_time="2026-04-03", evidence_id="ev_f6_2", block_id="b_f6_2")
    u3 = _make_unit("u3", "She published open-source synthesizer for ambient music", UnitKind.EVENT, "published", "published", norm_time="2026-04-15", evidence_id="ev_f6_3", block_id="b_f6_3", arguments={"actor": m2})

    # SAME_ENTITY links m_f6_1 and m_f6_2 across distant domains (Finance vs Music)
    r1 = SemanticRelation(
        relation_id="rel_f6_1", source_id="m_f6_1", target_id="m_f6_2", relation_type=RelationType.SAME_ENTITY,
        evidence_status=EvidenceStatus.EXPLICIT, confidence=1.0,
        provenance=RelationProvenance(raw_evidence_id="ev_f6_3", semantic_block_id="b_f6_3"),
    )

    doc = SemanticAnnotationDocument(
        document_id="doc_f6", cutoff_time="2026-04-20T00:00:00Z",
        units=[u1, u2, u3], relations=[r1],
    )

    cutoffs = [
        CutoffView(cutoff_time="2026-04-05T00:00:00Z", visible_evidence_ids=["ev_f6_1", "ev_f6_2"], visible_a0_block_ids=["b_f6_1", "b_f6_2"], visible_unit_ids=["u1", "u2"], is_target_evaluable=False),
        CutoffView(cutoff_time="2026-04-18T00:00:00Z", visible_evidence_ids=["ev_f6_1", "ev_f6_2", "ev_f6_3"], visible_a0_block_ids=["b_f6_1", "b_f6_2", "b_f6_3"], visible_unit_ids=["u1", "u2", "u3"], is_target_evaluable=True),
    ]

    oracle = TargetOracle(
        target_id="oracle_f6", target_type="entity_trajectory",
        target_unit_ids=["u1", "u3"], target_block_ids=["b_f6_1", "b_f6_3"],
        description="Entity trajectory of Alice linking finance pipeline (u1) and music synthesizer (u3) via SAME_ENTITY.",
    )

    return LongitudinalFixture(
        fixture_id="F6_cross_domain_entity", family="cross_domain_entity_carrier",
        description="Tracing entity trajectory across disparate topical domains where vectors are orthogonal.",
        evidence=[ev1, ev2, ev3], cutoffs=cutoffs, a0_blocks=[b1, b2, b3],
        gold_document=doc, oracle=oracle,
    )


def generate_f7_transitive_causal_chain() -> LongitudinalFixture:
    """F7: Transitive Causal Chain. 4-step directed causal propagation."""
    ev1 = EvidenceItem(evidence_id="ev_f7_1", content="The primary rack power distribution unit shorted out.", occurred_at="2026-04-01T10:00:00Z")
    ev2 = EvidenceItem(evidence_id="ev_f7_2", content="Because the power unit shorted, the storage cluster lost quorum.", occurred_at="2026-04-01T10:02:00Z")
    ev3 = EvidenceItem(evidence_id="ev_f7_3", content="Due to the lost quorum, the API gateway began returning 503 errors.", occurred_at="2026-04-01T10:04:00Z")
    ev4 = EvidenceItem(evidence_id="ev_f7_4", content="Consequently, checkout transactions dropped to zero.", occurred_at="2026-04-01T10:06:00Z")

    b1 = A0SemanticBlock(block_id="b_f7_1", evidence_ids=["ev_f7_1"], text=ev1.content, occurred_start=ev1.occurred_at, occurred_end=ev1.occurred_at)
    b2 = A0SemanticBlock(block_id="b_f7_2", evidence_ids=["ev_f7_2"], text=ev2.content, occurred_start=ev2.occurred_at, occurred_end=ev2.occurred_at)
    b3 = A0SemanticBlock(block_id="b_f7_3", evidence_ids=["ev_f7_3"], text=ev3.content, occurred_start=ev3.occurred_at, occurred_end=ev3.occurred_at)
    b4 = A0SemanticBlock(block_id="b_f7_4", evidence_ids=["ev_f7_4"], text=ev4.content, occurred_start=ev4.occurred_at, occurred_end=ev4.occurred_at)

    u1 = _make_unit("u1", "power distribution unit shorted out", UnitKind.EVENT, "shorted", "shorted", norm_time="2026-04-01T10:00", evidence_id="ev_f7_1", block_id="b_f7_1")
    u2 = _make_unit("u2", "storage cluster lost quorum", UnitKind.EVENT, "lost", "lost", norm_time="2026-04-01T10:02", evidence_id="ev_f7_2", block_id="b_f7_2")
    u3 = _make_unit("u3", "API gateway returned 503 errors", UnitKind.EVENT, "returned", "returned", norm_time="2026-04-01T10:04", evidence_id="ev_f7_3", block_id="b_f7_3")
    u4 = _make_unit("u4", "checkout transactions dropped to zero", UnitKind.EVENT, "dropped", "dropped", norm_time="2026-04-01T10:06", evidence_id="ev_f7_4", block_id="b_f7_4")

    r1 = SemanticRelation(
        relation_id="rel_f7_1", source_id="u1", target_id="u2", relation_type=RelationType.CAUSE,
        evidence_status=EvidenceStatus.EXPLICIT, confidence=1.0,
        provenance=RelationProvenance(raw_evidence_id="ev_f7_2", semantic_block_id="b_f7_2"),
        supporting_spans=[SourceSpan(char_start=0, char_end=7, text="Because")],
    )
    r2 = SemanticRelation(
        relation_id="rel_f7_2", source_id="u2", target_id="u3", relation_type=RelationType.CAUSE,
        evidence_status=EvidenceStatus.EXPLICIT, confidence=1.0,
        provenance=RelationProvenance(raw_evidence_id="ev_f7_3", semantic_block_id="b_f7_3"),
        supporting_spans=[SourceSpan(char_start=0, char_end=6, text="Due to")],
    )
    r3 = SemanticRelation(
        relation_id="rel_f7_3", source_id="u3", target_id="u4", relation_type=RelationType.CAUSE,
        evidence_status=EvidenceStatus.EXPLICIT, confidence=1.0,
        provenance=RelationProvenance(raw_evidence_id="ev_f7_4", semantic_block_id="b_f7_4"),
        supporting_spans=[SourceSpan(char_start=0, char_end=12, text="Consequently")],
    )

    doc = SemanticAnnotationDocument(
        document_id="doc_f7", cutoff_time="2026-04-01T11:00:00Z",
        units=[u1, u2, u3, u4], relations=[r1, r2, r3],
    )

    cutoffs = [
        CutoffView(cutoff_time="2026-04-01T10:03:00Z", visible_evidence_ids=["ev_f7_1", "ev_f7_2"], visible_a0_block_ids=["b_f7_1", "b_f7_2"], visible_unit_ids=["u1", "u2"], is_target_evaluable=False),
        CutoffView(cutoff_time="2026-04-01T10:10:00Z", visible_evidence_ids=["ev_f7_1", "ev_f7_2", "ev_f7_3", "ev_f7_4"], visible_a0_block_ids=["b_f7_1", "b_f7_2", "b_f7_3", "b_f7_4"], visible_unit_ids=["u1", "u2", "u3", "u4"], is_target_evaluable=True),
    ]

    oracle = TargetOracle(
        target_id="oracle_f7", target_type="causal_chain",
        target_unit_ids=["u1", "u2", "u3", "u4"], target_block_ids=["b_f7_1", "b_f7_2", "b_f7_3", "b_f7_4"],
        description="4-step causal chain propagation: u1 -> u2 -> u3 -> u4.",
    )

    return LongitudinalFixture(
        fixture_id="F7_transitive_causal_chain", family="transitive_causal_chain",
        description="Multi-hop causal propagation without direct short-circuiting.",
        evidence=[ev1, ev2, ev3, ev4], cutoffs=cutoffs, a0_blocks=[b1, b2, b3, b4],
        gold_document=doc, oracle=oracle,
    )


def generate_f8_density_distractor() -> LongitudinalFixture:
    """F8: Density Distractor Trap. Dense lexical token overlap with independent relations."""
    ev1 = EvidenceItem(evidence_id="ev_f8_1", content="Kubernetes cluster production pod deployment in us-east was drained.", occurred_at="2026-04-01T10:00:00Z")
    ev2 = EvidenceItem(evidence_id="ev_f8_2", content="Kubernetes cluster production service deployment in us-east was renewed.", occurred_at="2026-04-02T10:00:00Z")
    ev3 = EvidenceItem(evidence_id="ev_f8_3", content="Kubernetes cluster production ingress deployment in us-east was adjusted.", occurred_at="2026-04-03T10:00:00Z")
    ev4 = EvidenceItem(evidence_id="ev_f8_4", content="Kubernetes cluster production replica deployment in us-east was upgraded.", occurred_at="2026-04-04T10:00:00Z")

    b1 = A0SemanticBlock(block_id="b_f8_1", evidence_ids=["ev_f8_1"], text=ev1.content, occurred_start=ev1.occurred_at, occurred_end=ev1.occurred_at)
    b2 = A0SemanticBlock(block_id="b_f8_2", evidence_ids=["ev_f8_2"], text=ev2.content, occurred_start=ev2.occurred_at, occurred_end=ev2.occurred_at)
    b3 = A0SemanticBlock(block_id="b_f8_3", evidence_ids=["ev_f8_3"], text=ev3.content, occurred_start=ev3.occurred_at, occurred_end=ev3.occurred_at)
    b4 = A0SemanticBlock(block_id="b_f8_4", evidence_ids=["ev_f8_4"], text=ev4.content, occurred_start=ev4.occurred_at, occurred_end=ev4.occurred_at)

    u1 = _make_unit("u1", "Kubernetes cluster production pod deployment in us-east drained", UnitKind.EVENT, "drained", "drained", norm_time="2026-04-01", evidence_id="ev_f8_1", block_id="b_f8_1")
    u2 = _make_unit("u2", "Kubernetes cluster production service deployment in us-east renewed", UnitKind.EVENT, "renewed", "renewed", norm_time="2026-04-02", evidence_id="ev_f8_2", block_id="b_f8_2")
    u3 = _make_unit("u3", "Kubernetes cluster production ingress deployment in us-east adjusted", UnitKind.EVENT, "adjusted", "adjusted", norm_time="2026-04-03", evidence_id="ev_f8_3", block_id="b_f8_3")
    u4 = _make_unit("u4", "Kubernetes cluster production replica deployment in us-east upgraded", UnitKind.EVENT, "upgraded", "upgraded", norm_time="2026-04-04", evidence_id="ev_f8_4", block_id="b_f8_4")

    # Strictly NO_RELATION between all pairs (control labels)
    r1 = SemanticRelation(relation_id="rel_f8_1", source_id="u1", target_id="u2", relation_type=RelationType.NO_RELATION, evidence_status=EvidenceStatus.EXPLICIT, confidence=1.0, provenance=RelationProvenance(raw_evidence_id="ev_f8_2", semantic_block_id="b_f8_2"))
    r2 = SemanticRelation(relation_id="rel_f8_2", source_id="u2", target_id="u3", relation_type=RelationType.NO_RELATION, evidence_status=EvidenceStatus.EXPLICIT, confidence=1.0, provenance=RelationProvenance(raw_evidence_id="ev_f8_3", semantic_block_id="b_f8_3"))
    r3 = SemanticRelation(relation_id="rel_f8_3", source_id="u3", target_id="u4", relation_type=RelationType.NO_RELATION, evidence_status=EvidenceStatus.EXPLICIT, confidence=1.0, provenance=RelationProvenance(raw_evidence_id="ev_f8_4", semantic_block_id="b_f8_4"))

    doc = SemanticAnnotationDocument(
        document_id="doc_f8", cutoff_time="2026-04-10T00:00:00Z",
        units=[u1, u2, u3, u4], relations=[r1, r2, r3],
    )

    cutoffs = [
        CutoffView(cutoff_time="2026-04-02T12:00:00Z", visible_evidence_ids=["ev_f8_1", "ev_f8_2"], visible_a0_block_ids=["b_f8_1", "b_f8_2"], visible_unit_ids=["u1", "u2"], is_target_evaluable=False),
        CutoffView(cutoff_time="2026-04-06T00:00:00Z", visible_evidence_ids=["ev_f8_1", "ev_f8_2", "ev_f8_3", "ev_f8_4"], visible_a0_block_ids=["b_f8_1", "b_f8_2", "b_f8_3", "b_f8_4"], visible_unit_ids=["u1", "u2", "u3", "u4"], is_target_evaluable=True),
    ]

    oracle = TargetOracle(
        target_id="oracle_f8", target_type="distractor_rejection",
        target_unit_ids=[], target_block_ids=[],
        description="Dense lexical token distractor: 0 genuine longitudinal relations; all false clusterings must be rejected.",
    )

    return LongitudinalFixture(
        fixture_id="F8_density_distractor", family="density_distractor_trap",
        description="High token-overlap distractor where graph edges reveal total independence.",
        evidence=[ev1, ev2, ev3, ev4], cutoffs=cutoffs, a0_blocks=[b1, b2, b3, b4],
        gold_document=doc, oracle=oracle,
    )


def generate_all_fixtures() -> list[LongitudinalFixture]:
    """Generate all 8 canonical longitudinal fixtures for Issue #16."""
    return [
        generate_f1_delayed_bridge(),
        generate_f2_distant_recurrence(),
        generate_f3_state_revision(),
        generate_f4_post_hoc_causality(),
        generate_f5_holder_attribution(),
        generate_f6_cross_domain_entity(),
        generate_f7_transitive_causal_chain(),
        generate_f8_density_distractor(),
    ]
