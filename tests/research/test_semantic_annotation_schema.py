"""Test suite for research semantic annotation schema and invariants (GitHub Issue #13)."""

from __future__ import annotations

import json
from pathlib import Path
import jsonschema
import pytest
from pydantic import ValidationError

from research.semantic_annotation.schema import (
    FORBIDDEN_LABELS,
    ROLE_VOCABULARY,
    EvidenceStatus,
    HolderSource,
    ModalityType,
    PolarityType,
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


def test_valid_unit_instantiation() -> None:
    unit = SemanticUnit(
        annotation_id="u_001",
        provenance=UnitProvenance(
            raw_evidence_id="ev_001",
            semantic_block_id="block_001",
        ),
        source_span=SourceSpan(
            char_start=0,
            char_end=35,
            text="I submitted my resignation yesterday",
        ),
        kind=UnitKind.EVENT,
        predicate="submit_resignation",
        arguments={
            "actor": "I",
            "time": "yesterday",
        },
        polarity=PolarityType.POSITIVE,
        modality=ModalityType.ASSERTED,
        holder=HolderSource.USER,
        temporal_anchoring=TemporalAnchoring(
            value="2026-09-22",
            anchor_type=TemporalAnchorType.RELATIVE,
            source_expression="yesterday",
        ),
        evidence_status=EvidenceStatus.EXPLICIT,
        confidence=1.0,
    )
    assert unit.annotation_id == "u_001"
    assert unit.arguments["actor"] == "I"
    assert unit.kind == UnitKind.EVENT


def test_valid_relation_instantiation() -> None:
    relation = SemanticRelation(
        relation_id="rel_001",
        source_id="u_001",
        target_id="u_002",
        relation_type=RelationType.CAUSE,
        evidence_status=EvidenceStatus.EXPLICIT,
        confidence=0.95,
        provenance_spans=[
            SourceSpan(char_start=36, char_end=43, text="because"),
        ],
    )
    assert relation.relation_type == RelationType.CAUSE
    assert relation.confidence == 0.95


def test_first_class_unknown_and_no_relation() -> None:
    """Verify that UNKNOWN and NO_RELATION are valid first-class outcomes."""
    unit = SemanticUnit(
        annotation_id="u_unk",
        provenance=UnitProvenance(raw_evidence_id="ev_1", semantic_block_id="b_1"),
        source_span=SourceSpan(char_start=0, char_end=10, text="Maybe later"),
        kind=UnitKind.PROPOSITION,
        predicate="unknown_pred",
        arguments={},
        polarity=PolarityType.UNKNOWN,
        modality=ModalityType.UNKNOWN,
        holder=HolderSource.UNKNOWN,
        temporal_anchoring=TemporalAnchoring(
            value="unknown",
            anchor_type=TemporalAnchorType.UNANCHORED,
            source_expression=None,
        ),
        evidence_status=EvidenceStatus.UNKNOWN,
        confidence=0.5,
    )
    assert unit.polarity == PolarityType.UNKNOWN
    assert unit.modality == ModalityType.UNKNOWN

    rel_no = SemanticRelation(
        relation_id="r_no",
        source_id="u_unk",
        target_id="u_unk",
        relation_type=RelationType.NO_RELATION,
        evidence_status=EvidenceStatus.EXPLICIT,
        confidence=1.0,
    )
    assert rel_no.relation_type == RelationType.NO_RELATION

    rel_unk = SemanticRelation(
        relation_id="r_unk",
        source_id="u_unk",
        target_id="u_unk",
        relation_type=RelationType.UNKNOWN,
        evidence_status=EvidenceStatus.UNKNOWN,
        confidence=0.0,
    )
    assert rel_unk.relation_type == RelationType.UNKNOWN


def test_forbidden_labels_rejected_in_unit_predicate() -> None:
    """Verify that forbidden downstream cognition labels cannot be smuggled into unit predicates."""
    for label in FORBIDDEN_LABELS:
        with pytest.raises(ValidationError, match="Forbidden downstream cognition label"):
            SemanticUnit(
                annotation_id="u_bad",
                provenance=UnitProvenance(raw_evidence_id="ev_1", semantic_block_id="b_1"),
                source_span=SourceSpan(char_start=0, char_end=5, text="shift"),
                kind=UnitKind.EVENT,
                predicate=label,
                arguments={},
                polarity=PolarityType.POSITIVE,
                modality=ModalityType.ASSERTED,
                holder=HolderSource.USER,
                temporal_anchoring=TemporalAnchoring(
                    value="2026",
                    anchor_type=TemporalAnchorType.EXACT,
                ),
                evidence_status=EvidenceStatus.EXPLICIT,
                confidence=1.0,
            )


def test_invalid_argument_roles_rejected() -> None:
    """Verify that non-standard roles outside ROLE_VOCABULARY are rejected."""
    with pytest.raises(ValidationError, match="Invalid argument role 'agent'"):
        SemanticUnit(
            annotation_id="u_bad_role",
            provenance=UnitProvenance(raw_evidence_id="ev_1", semantic_block_id="b_1"),
            source_span=SourceSpan(char_start=0, char_end=10, text="Alice left"),
            kind=UnitKind.EVENT,
            predicate="leave",
            arguments={"agent": "Alice"},  # Should be 'actor'
            polarity=PolarityType.POSITIVE,
            modality=ModalityType.ASSERTED,
            holder=HolderSource.USER,
            temporal_anchoring=TemporalAnchoring(
                value="2026",
                anchor_type=TemporalAnchorType.EXACT,
            ),
            evidence_status=EvidenceStatus.EXPLICIT,
            confidence=1.0,
        )


def test_invalid_span_bounds_rejected() -> None:
    """Verify that char_end must be strictly greater than char_start."""
    with pytest.raises(ValidationError, match="char_end .* must be strictly greater than char_start"):
        SourceSpan(char_start=10, char_end=5, text="invalid")

    with pytest.raises(ValidationError, match="char_end .* must be strictly greater than char_start"):
        SourceSpan(char_start=5, char_end=5, text="empty")


def test_document_referential_integrity() -> None:
    """Verify that relations referencing non-existent units fail validation."""
    u1 = SemanticUnit(
        annotation_id="u_1",
        provenance=UnitProvenance(raw_evidence_id="ev_1", semantic_block_id="b_1"),
        source_span=SourceSpan(char_start=0, char_end=4, text="text"),
        kind=UnitKind.PROPOSITION,
        predicate="test",
        arguments={},
        polarity=PolarityType.POSITIVE,
        modality=ModalityType.ASSERTED,
        holder=HolderSource.USER,
        temporal_anchoring=TemporalAnchoring(
            value="unknown",
            anchor_type=TemporalAnchorType.UNANCHORED,
        ),
        evidence_status=EvidenceStatus.EXPLICIT,
        confidence=1.0,
    )

    # Missing target u_2
    rel_dangling = SemanticRelation(
        relation_id="rel_dangle",
        source_id="u_1",
        target_id="u_2",
        relation_type=RelationType.CAUSE,
        evidence_status=EvidenceStatus.EXPLICIT,
        confidence=0.9,
    )

    with pytest.raises(ValidationError, match="dangling target_id 'u_2'"):
        SemanticAnnotationDocument(
            document_id="doc_test",
            cutoff_time="2026-09-23T00:00:00Z",
            units=[u1],
            relations=[rel_dangling],
        )


def test_json_schema_validates_walkthrough_document() -> None:
    """Verify that the JSON Schema file correctly validates the canonical walkthrough document."""
    schema_path = Path("research/schemas/semantic_annotation_v0_1.json")
    assert schema_path.exists(), "Schema file must exist"

    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)

    # Document matching walkthrough in EXAMPLES_V0_1.md
    walkthrough_doc = {
        "document_id": "doc_walkthrough_01",
        "cutoff_time": "2026-09-23T00:00:00Z",
        "units": [
            {
                "annotation_id": "u1",
                "provenance": {
                    "raw_evidence_id": "ev_2026_09_15_01",
                    "semantic_block_id": "block_042",
                },
                "source_span": {
                    "char_start": 0,
                    "char_end": 37,
                    "text": "In 2022, I loved working at BigCorp",
                },
                "kind": "attitude",
                "predicate": "love",
                "arguments": {
                    "experiencer": "I",
                    "theme": "working at BigCorp",
                    "time": "2022",
                },
                "polarity": "positive",
                "modality": "asserted",
                "holder": "user",
                "temporal_anchoring": {
                    "value": "2022",
                    "anchor_type": "exact",
                    "source_expression": "In 2022",
                },
                "evidence_status": "explicit",
                "confidence": 1.0,
            },
            {
                "annotation_id": "u2",
                "provenance": {
                    "raw_evidence_id": "ev_2026_09_15_01",
                    "semantic_block_id": "block_042",
                },
                "source_span": {
                    "char_start": 46,
                    "char_end": 74,
                    "text": "the scale was exhilarating",
                },
                "kind": "attitude",
                "predicate": "exhilarating",
                "arguments": {
                    "stimulus": "the scale",
                    "experiencer": "I",
                },
                "polarity": "positive",
                "modality": "asserted",
                "holder": "user",
                "temporal_anchoring": {
                    "value": "2022",
                    "anchor_type": "relative",
                    "source_expression": "In 2022",
                },
                "evidence_status": "explicit",
                "confidence": 0.95,
            },
            {
                "annotation_id": "u3",
                "provenance": {
                    "raw_evidence_id": "ev_2026_09_15_01",
                    "semantic_block_id": "block_042",
                },
                "source_span": {
                    "char_start": 89,
                    "char_end": 125,
                    "text": "by 2025 I completely burned out",
                },
                "kind": "event",
                "predicate": "burn_out",
                "arguments": {
                    "actor": "I",
                    "time": "by 2025",
                },
                "polarity": "positive",
                "modality": "asserted",
                "holder": "user",
                "temporal_anchoring": {
                    "value": "2025",
                    "anchor_type": "exact",
                    "source_expression": "by 2025",
                },
                "evidence_status": "explicit",
                "confidence": 1.0,
            },
            {
                "annotation_id": "u4",
                "provenance": {
                    "raw_evidence_id": "ev_2026_09_15_01",
                    "semantic_block_id": "block_042",
                },
                "source_span": {
                    "char_start": 140,
                    "char_end": 194,
                    "text": "I will never work for a giant corporation again",
                },
                "kind": "attitude",
                "predicate": "work_at",
                "arguments": {
                    "actor": "I",
                    "target": "giant corporation",
                },
                "polarity": "negative",
                "modality": "intended",
                "holder": "user",
                "temporal_anchoring": {
                    "value": "2025/..",
                    "anchor_type": "bounded_range",
                    "source_expression": "again",
                },
                "evidence_status": "explicit",
                "confidence": 1.0,
            },
            {
                "annotation_id": "u5",
                "provenance": {
                    "raw_evidence_id": "ev_2026_09_15_01",
                    "semantic_block_id": "block_042",
                },
                "source_span": {
                    "char_start": 218,
                    "char_end": 244,
                    "text": "Small startups are riskier",
                },
                "kind": "proposition",
                "predicate": "risky",
                "arguments": {
                    "theme": "Small startups",
                },
                "polarity": "positive",
                "modality": "asserted",
                "holder": "quoted",
                "temporal_anchoring": {
                    "value": "unknown",
                    "anchor_type": "unanchored",
                    "source_expression": None,
                },
                "evidence_status": "explicit",
                "confidence": 1.0,
            },
            {
                "annotation_id": "u6",
                "provenance": {
                    "raw_evidence_id": "ev_2026_09_15_01",
                    "semantic_block_id": "block_042",
                },
                "source_span": {
                    "char_start": 254,
                    "char_end": 302,
                    "text": "I joined a five-person AI lab last week",
                },
                "kind": "event",
                "predicate": "join",
                "arguments": {
                    "actor": "I",
                    "target": "five-person AI lab",
                    "time": "last week",
                },
                "polarity": "positive",
                "modality": "asserted",
                "holder": "user",
                "temporal_anchoring": {
                    "value": "2026-09",
                    "anchor_type": "relative",
                    "source_expression": "last week",
                },
                "evidence_status": "explicit",
                "confidence": 1.0,
            },
        ],
        "relations": [
            {
                "relation_id": "rel_01",
                "source_id": "u2",
                "target_id": "u1",
                "relation_type": "CAUSE",
                "evidence_status": "explicit",
                "confidence": 0.95,
            },
            {
                "relation_id": "rel_02",
                "source_id": "u1",
                "target_id": "u3",
                "relation_type": "BEFORE",
                "evidence_status": "explicit",
                "confidence": 1.0,
            },
            {
                "relation_id": "rel_03",
                "source_id": "u1",
                "target_id": "u4",
                "relation_type": "INCOMPATIBLE",
                "evidence_status": "entailed",
                "confidence": 0.95,
            },
            {
                "relation_id": "rel_04",
                "source_id": "u3",
                "target_id": "u4",
                "relation_type": "CAUSE",
                "evidence_status": "explicit",
                "confidence": 0.9,
            },
            {
                "relation_id": "rel_05",
                "source_id": "u5",
                "target_id": "u6",
                "relation_type": "CONCESSION",
                "evidence_status": "explicit",
                "confidence": 0.9,
            },
        ],
    }

    # Validate against JSON Schema
    jsonschema.validate(instance=walkthrough_doc, schema=schema)

    # Also validate with Pydantic model
    doc = SemanticAnnotationDocument.model_validate(walkthrough_doc)
    assert len(doc.units) == 6
    assert len(doc.relations) == 5
