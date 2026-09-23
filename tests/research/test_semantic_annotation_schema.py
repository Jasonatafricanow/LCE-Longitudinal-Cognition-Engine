"""Regression test suite for research semantic annotation schema and invariants (GitHub Issue #13 Final Patch).

Covers all 4 final patch requirements:
1. Stable mention_id for every argument/entity mention; SAME_ENTITY connects mention IDs (rejects <unit_id>:<role>).
2. Nested-attitude semantics: preserves desire (modality=desired) separately from epistemic hedging (epistemic_hedge=think) with confidence=1.0.
3. Deterministic mechanical predicate normalization: exact_surface, lemma, compound_lower, and explicit frozen map (no ungrounded synonym rewriting).
4. Frozen graph admission: inferred units/relations are audit-only and CANNOT become positive graph nodes/edges; only explicit and entailed are eligible.
"""

from __future__ import annotations

import json
from pathlib import Path
import jsonschema
import pytest
from pydantic import ValidationError

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


def _make_unit(
    annotation_id: str,
    *,
    kind: UnitKind = UnitKind.PROPOSITION,
    surface_pred: str = "test",
    norm_pred: str = "test",
    norm_rule: PredicateNormalizationRule = PredicateNormalizationRule.EXACT_SURFACE,
    arguments: dict[str, ArgumentMention] | None = None,
    polarity: PolarityType = PolarityType.POSITIVE,
    modality: ModalityType = ModalityType.ASSERTED,
    epistemic_hedge: EpistemicHedge = EpistemicHedge.NONE,
    holder_ref: str = "user",
    attribution_mode: AttributionMode = AttributionMode.DIRECT_SPEAKER,
    norm_time: str = "2026-09-23",
    anchor_type: TemporalAnchorType = TemporalAnchorType.EXACT,
    ref_anchor: str | None = None,
    evidence_status: EvidenceStatus = EvidenceStatus.EXPLICIT,
    confidence: float = 1.0,
) -> SemanticUnit:
    return SemanticUnit(
        annotation_id=annotation_id,
        provenance=UnitProvenance(raw_evidence_id="ev_01", semantic_block_id="b_01"),
        source_span=SourceSpan(char_start=0, char_end=10, text="sample text"),
        kind=kind,
        predicate=PredicateSpec(
            surface_predicate=surface_pred,
            normalized_predicate=norm_pred,
            normalization_rule=norm_rule,
        ),
        arguments=arguments or {},
        polarity=polarity,
        modality=modality,
        epistemic_hedge=epistemic_hedge,
        holder_ref=holder_ref,
        attribution_mode=attribution_mode,
        temporal_anchoring=TemporalAnchoring(
            normalized_value=norm_time,
            anchor_type=anchor_type,
            reference_anchor=ref_anchor,
        ),
        evidence_status=evidence_status,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# Requirement 1: Stable mention_id and mention-based SAME_ENTITY
# ---------------------------------------------------------------------------

def test_argument_mention_requires_stable_mention_id() -> None:
    """Every argument mention must have its own stable mention_id."""
    arg = ArgumentMention(
        mention_id="m_001",
        role="actor",
        text="Alice",
        entity_ref="ent_alice",
    )
    assert arg.mention_id == "m_001"
    assert arg.role == "actor"


def test_same_entity_connects_stable_mention_ids() -> None:
    """SAME_ENTITY must connect stable mention IDs, rejecting <unit_id>:<role>."""
    u1 = _make_unit(
        "u1",
        arguments={"actor": ArgumentMention(mention_id="m_alice_1", role="actor", text="Alice", entity_ref="ent_alice")},
    )
    u2 = _make_unit(
        "u2",
        arguments={"target": ArgumentMention(mention_id="m_alice_2", role="target", text="her", entity_ref="ent_alice")},
    )

    # Valid: connects mention IDs directly
    rel_valid = SemanticRelation(
        relation_id="rel_same_ent",
        source_id="m_alice_1",
        target_id="m_alice_2",
        relation_type=RelationType.SAME_ENTITY,
        evidence_status=EvidenceStatus.EXPLICIT,
        confidence=1.0,
        provenance=RelationProvenance(raw_evidence_id="ev_01", semantic_block_id="b_01"),
    )

    doc = SemanticAnnotationDocument(
        document_id="doc_test",
        cutoff_time="2026-09-23T00:00:00Z",
        units=[u1, u2],
        relations=[rel_valid],
    )
    assert doc.relations[0].source_id == "m_alice_1"
    assert doc.relations[0].target_id == "m_alice_2"

    # Rejection of pseudo-identifier <unit_id>:<role>
    rel_pseudo = SemanticRelation(
        relation_id="rel_pseudo_err",
        source_id="u1:actor",
        target_id="u2:target",
        relation_type=RelationType.SAME_ENTITY,
        evidence_status=EvidenceStatus.EXPLICIT,
        confidence=1.0,
        provenance=RelationProvenance(raw_evidence_id="ev_01", semantic_block_id="b_01"),
    )

    with pytest.raises(ValidationError, match="SAME_ENTITY relation .* must connect stable mention IDs"):
        SemanticAnnotationDocument(
            document_id="doc_test",
            cutoff_time="2026-09-23T00:00:00Z",
            units=[u1, u2],
            relations=[rel_pseudo],
        )

    # Rejection of non-existent mention ID
    rel_missing_mention = SemanticRelation(
        relation_id="rel_missing",
        source_id="m_alice_1",
        target_id="m_nonexistent",
        relation_type=RelationType.SAME_ENTITY,
        evidence_status=EvidenceStatus.EXPLICIT,
        confidence=1.0,
        provenance=RelationProvenance(raw_evidence_id="ev_01", semantic_block_id="b_01"),
    )

    with pytest.raises(ValidationError, match="not found in document mention IDs"):
        SemanticAnnotationDocument(
            document_id="doc_test",
            cutoff_time="2026-09-23T00:00:00Z",
            units=[u1, u2],
            relations=[rel_missing_mention],
        )


# ---------------------------------------------------------------------------
# Requirement 2: Nested Attitude Semantics (Desire preserved, Epistemic Hedge decoupled)
# ---------------------------------------------------------------------------

def test_nested_attitude_semantics_preserved() -> None:
    """'I think I want to leave': preserve desire (modality=desired) separately from epistemic hedging (think) with confidence=1.0."""
    u_nested = _make_unit(
        "u_nested",
        kind=UnitKind.ATTITUDE,
        surface_pred="leave",
        norm_pred="leave",
        norm_rule=PredicateNormalizationRule.EXACT_SURFACE,
        modality=ModalityType.DESIRED,
        epistemic_hedge=EpistemicHedge.THINK,
        confidence=1.0,  # No arbitrary confidence reduction!
    )
    # Verify desire modality is preserved
    assert u_nested.modality == ModalityType.DESIRED
    # Verify epistemic hedge is captured cleanly and explicitly
    assert u_nested.epistemic_hedge == EpistemicHedge.THINK
    # Verify confidence remains 1.0 (evaluating annotation accuracy, not semantic compromise)
    assert u_nested.confidence == 1.0


# ---------------------------------------------------------------------------
# Requirement 3: Deterministic Mechanical Predicate Normalization
# ---------------------------------------------------------------------------

def test_deterministic_predicate_normalization_rules() -> None:
    """Mechanical normalization only: exact_surface, compound_lower, lemma, and explicit frozen map."""
    # 1. exact_surface
    p_exact = PredicateSpec(
        surface_predicate="resign",
        normalized_predicate="resign",
        normalization_rule=PredicateNormalizationRule.EXACT_SURFACE,
    )
    assert p_exact.normalized_predicate == "resign"

    # exact_surface failure if normalized != lower surface
    with pytest.raises(ValidationError, match="requires normalized_predicate .* to equal lowercase surface_predicate"):
        PredicateSpec(
            surface_predicate="want",
            normalized_predicate="desire",  # Open-ended synonym rewriting rejected!
            normalization_rule=PredicateNormalizationRule.EXACT_SURFACE,
        )

    # 2. compound_lower
    p_compound = PredicateSpec(
        surface_predicate="drop database",
        normalized_predicate="drop_database",
        normalization_rule=PredicateNormalizationRule.COMPOUND_LOWER,
    )
    assert p_compound.normalized_predicate == "drop_database"

    # 3. frozen_map
    p_frozen = PredicateSpec(
        surface_predicate="prefer writing",
        normalized_predicate="prefer",
        normalization_rule=PredicateNormalizationRule.FROZEN_MAP,
    )
    assert p_frozen.normalized_predicate == "prefer"

    # frozen_map failure if surface not in explicit frozen table
    with pytest.raises(ValidationError, match="is not in FROZEN_PREDICATE_MAP"):
        PredicateSpec(
            surface_predicate="arbitrary unknown synonym",
            normalized_predicate="desire",
            normalization_rule=PredicateNormalizationRule.FROZEN_MAP,
        )


# ---------------------------------------------------------------------------
# Requirement 4: Frozen Graph Admission (inferred is audit-only)
# ---------------------------------------------------------------------------

def test_frozen_graph_admission_inferred_rejected_from_graph() -> None:
    """inferred units and relations are audit-only and MUST NOT become positive graph nodes/edges."""
    # 1. Inferred unit cannot serialize to graph node
    u_inferred = _make_unit("u_inf", evidence_status=EvidenceStatus.INFERRED)
    assert not u_inferred.is_graph_eligible
    with pytest.raises(ValueError, match="is audit-only and MUST NOT become a positive graph node"):
        u_inferred.to_graph_node()

    # Explicit unit can serialize
    u_explicit = _make_unit("u_exp", evidence_status=EvidenceStatus.EXPLICIT)
    assert u_explicit.is_graph_eligible
    node_dict = u_explicit.to_graph_node()
    assert node_dict["annotation_id"] == "u_exp"

    # Entailed unit can serialize
    u_entailed = _make_unit("u_ent", evidence_status=EvidenceStatus.ENTAILED)
    assert u_entailed.is_graph_eligible

    # 2. Inferred relation cannot serialize to graph edge
    rel_inferred = SemanticRelation(
        relation_id="rel_inf",
        source_id="u_exp",
        target_id="u_ent",
        relation_type=RelationType.CAUSE,
        evidence_status=EvidenceStatus.INFERRED,
        confidence=0.8,
        provenance=RelationProvenance(raw_evidence_id="ev_01", semantic_block_id="b_01"),
    )
    assert not rel_inferred.is_graph_edge
    with pytest.raises(ValueError, match="is audit-only and MUST NOT become a positive graph edge"):
        rel_inferred.to_graph_edge()

    # Explicit relation can serialize
    rel_explicit = SemanticRelation(
        relation_id="rel_exp",
        source_id="u_exp",
        target_id="u_ent",
        relation_type=RelationType.CAUSE,
        evidence_status=EvidenceStatus.EXPLICIT,
        confidence=0.95,
        provenance=RelationProvenance(raw_evidence_id="ev_01", semantic_block_id="b_01"),
    )
    assert rel_explicit.is_graph_edge
    edge = rel_explicit.to_graph_edge()
    assert edge["relation_id"] == "rel_exp"


# ---------------------------------------------------------------------------
# Additional Existing Invariant Tests
# ---------------------------------------------------------------------------

def test_incompatible_rejected_across_non_overlapping_times() -> None:
    """Opposite preferences at non-overlapping times do NOT produce INCOMPATIBLE."""
    u_2022 = _make_unit("u_2022", norm_time="2022", polarity=PolarityType.POSITIVE, modality=ModalityType.DESIRED)
    u_2026 = _make_unit("u_2026", norm_time="2026", polarity=PolarityType.NEGATIVE, modality=ModalityType.INTENDED)

    rel_bad = SemanticRelation(
        relation_id="rel_bad_incompat",
        source_id="u_2022",
        target_id="u_2026",
        relation_type=RelationType.INCOMPATIBLE,
        evidence_status=EvidenceStatus.EXPLICIT,
        confidence=1.0,
        provenance=RelationProvenance(raw_evidence_id="ev_01", semantic_block_id="b_01"),
    )

    with pytest.raises(ValidationError, match="INCOMPATIBLE requires overlapping temporal validity"):
        SemanticAnnotationDocument(
            document_id="doc_test",
            cutoff_time="2026-09-23T00:00:00Z",
            units=[u_2022, u_2026],
            relations=[rel_bad],
        )


def test_control_labels_cannot_serialize_as_graph_edges() -> None:
    """NO_RELATION / UNKNOWN / TEMPORAL_UNKNOWN cannot serialize as graph-positive edges."""
    for ctrl_rel in CONTROL_RELATION_TYPES:
        rel = SemanticRelation(
            relation_id=f"rel_{ctrl_rel.value.lower()}",
            source_id="u1",
            target_id="u2",
            relation_type=ctrl_rel,
            evidence_status=EvidenceStatus.EXPLICIT,
            confidence=1.0,
            provenance=RelationProvenance(raw_evidence_id="ev_01", semantic_block_id="b_01"),
        )
        assert not rel.is_graph_edge
        with pytest.raises(ValueError, match="cannot be serialized as a positive graph edge"):
            rel.to_graph_edge()


def test_forbidden_downstream_cognition_labels_rejected() -> None:
    """Downstream cognition labels cannot appear in kind, predicate, or relation_type."""
    for label in FORBIDDEN_LABELS:
        with pytest.raises(ValidationError):
            _make_unit("u_bad", norm_pred=label)

        with pytest.raises(ValidationError):
            _make_unit("u_bad_kind", kind=label)  # type: ignore[arg-type]


def test_schema_parity() -> None:
    """Schema parity test between canonical Pydantic model and exported JSON schema."""
    schema_path = Path("research/schemas/semantic_annotation_v0_1.json")
    assert schema_path.exists(), "Exported JSON schema must exist"

    with open(schema_path, encoding="utf-8") as f:
        json_schema = json.load(f)

    # 1. Parity of exported enum values
    defs = json_schema.get("$defs", {})
    assert "UnitKind" in defs
    json_unit_kinds = set(defs["UnitKind"]["enum"])
    pydantic_unit_kinds = {e.value for e in UnitKind}
    assert json_unit_kinds == pydantic_unit_kinds

    assert "RelationType" in defs
    json_rel_types = set(defs["RelationType"]["enum"])
    pydantic_rel_types = {e.value for e in RelationType}
    assert json_rel_types == pydantic_rel_types

    assert "EpistemicHedge" in defs
    json_hedges = set(defs["EpistemicHedge"]["enum"])
    pydantic_hedges = {e.value for e in EpistemicHedge}
    assert json_hedges == pydantic_hedges

    assert "PredicateNormalizationRule" in defs
    json_rules = set(defs["PredicateNormalizationRule"]["enum"])
    pydantic_rules = {e.value for e in PredicateNormalizationRule}
    assert json_rules == pydantic_rules

    # 2. Verify forbidden labels are excluded from both schemas
    for forbidden in FORBIDDEN_LABELS:
        assert forbidden not in json_unit_kinds
        assert forbidden not in json_rel_types

    # 3. Validate walkthrough document against JSON Schema
    walkthrough_doc_dict = {
        "document_id": "doc_walkthrough_01",
        "cutoff_time": "2026-09-23T00:00:00Z",
        "units": [
            {
                "annotation_id": "u1",
                "provenance": {"raw_evidence_id": "ev_01", "semantic_block_id": "b_01"},
                "source_span": {"char_start": 0, "char_end": 35, "text": "In 2022, I loved working at BigCorp"},
                "kind": "attitude",
                "predicate": {
                    "surface_predicate": "loved working",
                    "normalized_predicate": "love",
                    "normalization_rule": "frozen_map",
                },
                "arguments": {
                    "experiencer": {"mention_id": "m1", "role": "experiencer", "text": "I", "entity_ref": "user"},
                    "theme": {"mention_id": "m2", "role": "theme", "text": "working at BigCorp"},
                    "time": {"mention_id": "m3", "role": "time", "text": "In 2022"},
                },
                "polarity": "positive",
                "modality": "asserted",
                "epistemic_hedge": "none",
                "holder_ref": "user",
                "attribution_mode": "direct_speaker",
                "temporal_anchoring": {
                    "normalized_value": "2022",
                    "anchor_type": "exact",
                    "source_expression": "In 2022",
                    "reference_anchor": None,
                },
                "evidence_status": "explicit",
                "confidence": 1.0,
            },
            {
                "annotation_id": "u3",
                "provenance": {"raw_evidence_id": "ev_01", "semantic_block_id": "b_01"},
                "source_span": {"char_start": 81, "char_end": 113, "text": "by 2025 I completely burned out"},
                "kind": "event",
                "predicate": {
                    "surface_predicate": "burned out",
                    "normalized_predicate": "burn_out",
                    "normalization_rule": "frozen_map",
                },
                "arguments": {
                    "actor": {"mention_id": "m4", "role": "actor", "text": "I", "entity_ref": "user"},
                    "time": {"mention_id": "m5", "role": "time", "text": "by 2025"},
                },
                "polarity": "positive",
                "modality": "asserted",
                "epistemic_hedge": "none",
                "holder_ref": "user",
                "attribution_mode": "direct_speaker",
                "temporal_anchoring": {
                    "normalized_value": "2025",
                    "anchor_type": "exact",
                    "source_expression": "by 2025",
                    "reference_anchor": None,
                },
                "evidence_status": "explicit",
                "confidence": 1.0,
            },
        ],
        "relations": [
            {
                "relation_id": "rel_01",
                "source_id": "u1",
                "target_id": "u3",
                "relation_type": "BEFORE",
                "evidence_status": "explicit",
                "confidence": 1.0,
                "provenance": {"raw_evidence_id": "ev_01", "semantic_block_id": "b_01"},
                "supporting_spans": [],
            },
            {
                "relation_id": "rel_02",
                "source_id": "m1",
                "target_id": "m4",
                "relation_type": "SAME_ENTITY",
                "evidence_status": "explicit",
                "confidence": 1.0,
                "provenance": {"raw_evidence_id": "ev_01", "semantic_block_id": "b_01"},
                "supporting_spans": [],
            },
        ],
    }

    # Validate against JSON schema
    jsonschema.validate(instance=walkthrough_doc_dict, schema=json_schema)

    # Validate against Pydantic model
    doc = SemanticAnnotationDocument.model_validate(walkthrough_doc_dict)
    assert len(doc.units) == 2
    assert len(doc.relations) == 2
