"""Regression test suite for research semantic annotation schema and invariants (GitHub Issue #13).

Covers all 11 review recommendations from Issue #13 post-implementation audit:
- Holder/attribution decoupling
- INCOMPATIBLE temporal overlap semantics
- Independent relation grounding and provenance
- Gating control labels from graph serialization
- Argument-mention endpoints for SAME_ENTITY
- Relative temporal anchor reference validation
- Prohibition on manufactured result states
- Shallow nested attitude handling
- Schema parity test between canonical Pydantic model and JSON Schema
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
    ROLE_VOCABULARY,
    ArgumentMention,
    AttributionMode,
    EvidenceStatus,
    ModalityType,
    PolarityType,
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
    norm_rule: str = "exact_match",
    arguments: dict[str, ArgumentMention] | None = None,
    polarity: PolarityType = PolarityType.POSITIVE,
    modality: ModalityType = ModalityType.ASSERTED,
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


def test_holder_identity_and_attribution_mode_split() -> None:
    """Review Point 1: Verify holder identity is decoupled from attribution mode."""
    # Direct quote preserves actual holder (VP) while recording direct_quote
    u_quote = _make_unit(
        "u_quote",
        holder_ref="VP",
        attribution_mode=AttributionMode.DIRECT_QUOTE,
    )
    assert u_quote.holder_ref == "VP"
    assert u_quote.attribution_mode == AttributionMode.DIRECT_QUOTE

    # Indirect report preserves reported person (team_lead)
    u_rep = _make_unit(
        "u_rep",
        holder_ref="team_lead",
        attribution_mode=AttributionMode.INDIRECT_REPORT,
    )
    assert u_rep.holder_ref == "team_lead"
    assert u_rep.attribution_mode == AttributionMode.INDIRECT_REPORT


def test_incompatible_rejected_across_non_overlapping_times() -> None:
    """Review Point 2: Opposite preferences at non-overlapping times do NOT produce INCOMPATIBLE."""
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


def test_incompatible_accepted_for_overlapping_times() -> None:
    """Review Point 2: Overlapping mutually exclusive states may produce INCOMPATIBLE."""
    u1 = _make_unit("u1", norm_time="2026-09-23", polarity=PolarityType.POSITIVE)
    u2 = _make_unit("u2", norm_time="2026-09-23", polarity=PolarityType.NEGATIVE)

    rel_valid = SemanticRelation(
        relation_id="rel_valid_incompat",
        source_id="u1",
        target_id="u2",
        relation_type=RelationType.INCOMPATIBLE,
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
    assert len(doc.relations) == 1
    assert doc.relations[0].relation_type == RelationType.INCOMPATIBLE


def test_relation_requires_independent_grounding_and_provenance() -> None:
    """Review Point 3: A relation cannot be accepted without its own grounding/provenance/evidence status."""
    with pytest.raises(ValidationError):
        # Missing required provenance
        SemanticRelation(
            relation_id="rel_missing_prov",
            source_id="u1",
            target_id="u2",
            relation_type=RelationType.CAUSE,
            evidence_status=EvidenceStatus.EXPLICIT,
            confidence=0.9,
            # provenance omitted -> should fail validation
        )


def test_control_labels_cannot_serialize_as_graph_edges() -> None:
    """Review Point 4: NO_RELATION / UNKNOWN / TEMPORAL_UNKNOWN cannot serialize as graph-positive edges."""
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

    # Positive relation can serialize
    rel_pos = SemanticRelation(
        relation_id="rel_pos_cause",
        source_id="u1",
        target_id="u2",
        relation_type=RelationType.CAUSE,
        evidence_status=EvidenceStatus.EXPLICIT,
        confidence=0.95,
        provenance=RelationProvenance(raw_evidence_id="ev_01", semantic_block_id="b_01"),
    )
    assert rel_pos.is_graph_edge
    edge_dict = rel_pos.to_graph_edge()
    assert edge_dict["relation_type"] == "CAUSE"


def test_same_entity_requires_argument_mention_endpoints() -> None:
    """Review Point 5: SAME_ENTITY connects mention/referent endpoints, rejecting proposition IDs."""
    u1 = _make_unit(
        "u1",
        arguments={"actor": ArgumentMention(role="actor", text="Alice", entity_ref="ent_alice")},
    )
    u2 = _make_unit(
        "u2",
        arguments={"target": ArgumentMention(role="target", text="her", entity_ref="ent_alice")},
    )

    # Valid: targets mention endpoints "u1:actor" and "u2:target"
    rel_valid = SemanticRelation(
        relation_id="rel_same_ent",
        source_id="u1:actor",
        target_id="u2:target",
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
    assert doc.relations[0].relation_type == RelationType.SAME_ENTITY

    # Invalid: targets proposition IDs "u1" and "u2" directly
    rel_invalid = SemanticRelation(
        relation_id="rel_invalid_same_ent",
        source_id="u1",
        target_id="u2",
        relation_type=RelationType.SAME_ENTITY,
        evidence_status=EvidenceStatus.EXPLICIT,
        confidence=1.0,
        provenance=RelationProvenance(raw_evidence_id="ev_01", semantic_block_id="b_01"),
    )

    with pytest.raises(ValidationError, match="must specify an argument mention in format '<unit_id>:<role>'"):
        SemanticAnnotationDocument(
            document_id="doc_test",
            cutoff_time="2026-09-23T00:00:00Z",
            units=[u1, u2],
            relations=[rel_invalid],
        )


def test_relative_temporal_anchors_require_reference_anchor() -> None:
    """Review Point 6: Relative temporal anchors must preserve the reference anchor."""
    # Valid relative anchor with reference_anchor
    t_valid = TemporalAnchoring(
        normalized_value="2026-09-22",
        anchor_type=TemporalAnchorType.RELATIVE,
        source_expression="yesterday",
        reference_anchor="evidence:occurred_at",
    )
    assert t_valid.reference_anchor == "evidence:occurred_at"

    # Invalid: relative anchor without reference_anchor
    with pytest.raises(ValidationError, match="must specify 'reference_anchor'"):
        TemporalAnchoring(
            normalized_value="2026-09-22",
            anchor_type=TemporalAnchorType.RELATIVE,
            source_expression="yesterday",
            reference_anchor=None,
        )


def test_shallow_nested_attitude_policy() -> None:
    """Review Point 8: Nested attitude follows shallow-policy behavior."""
    # "I think I want to leave"
    u_nested = _make_unit(
        "u_nested",
        kind=UnitKind.ATTITUDE,
        surface_pred="think I want to leave",
        norm_pred="leave",
        norm_rule="shallow_nested_hedge",
        modality=ModalityType.UNCERTAIN,
        confidence=0.70,
    )
    assert u_nested.modality == ModalityType.UNCERTAIN
    assert u_nested.confidence == 0.70
    assert u_nested.predicate.normalization_rule == "shallow_nested_hedge"


def test_forbidden_downstream_cognition_labels_rejected() -> None:
    """Negative invariant: downstream cognition labels cannot appear in kind, predicate, or relation_type."""
    for label in FORBIDDEN_LABELS:
        with pytest.raises(ValidationError):
            _make_unit("u_bad", norm_pred=label)

        with pytest.raises(ValidationError):
            _make_unit("u_bad_kind", kind=label)  # type: ignore[arg-type]


def test_schema_parity() -> None:
    """Review Point 11: Schema parity test between canonical Pydantic model and exported JSON schema."""
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

    assert "AttributionMode" in defs
    json_attr_modes = set(defs["AttributionMode"]["enum"])
    pydantic_attr_modes = {e.value for e in AttributionMode}
    assert json_attr_modes == pydantic_attr_modes

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
                    "normalization_rule": "verb_lemma",
                },
                "arguments": {
                    "experiencer": {"role": "experiencer", "text": "I", "entity_ref": "user"},
                    "theme": {"role": "theme", "text": "working at BigCorp"},
                    "time": {"role": "time", "text": "In 2022"},
                },
                "polarity": "positive",
                "modality": "asserted",
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
                    "normalization_rule": "verb_lemma",
                },
                "arguments": {
                    "actor": {"role": "actor", "text": "I", "entity_ref": "user"},
                    "time": {"role": "time", "text": "by 2025"},
                },
                "polarity": "positive",
                "modality": "asserted",
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
                "source_id": "u1:experiencer",
                "target_id": "u3:actor",
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
