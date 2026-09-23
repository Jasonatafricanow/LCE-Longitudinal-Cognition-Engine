"""Automated regression test suite for Issue #17: AGY Graph vs. Oracle Comparison.

Validates:
1. Predicted graph compiler admission rules, mention indexing, and coreference resolution.
2. Structural graph comparator fidelity metrics (node IoU, edge family macro F1).
3. 40 held-out Eval split graph parity benchmarks (eval.jsonl vs predictions_eval.jsonl).
4. Zero production code mutation (src/lce/ untouched).
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import pytest

from research.experiments.agy_graph_vs_oracle.graph_compiler import compile_predicted_graph
from research.experiments.agy_graph_vs_oracle.graph_comparator import (
    compare_graph_pair,
    compute_span_iou,
    evaluate_eval_split_graph_parity,
)
from research.oracle_graph.compiler import OracleGraphCompiler
from research.oracle_graph.models import OracleTypedGraph
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
    TemporalAnchorType,
    TemporalAnchoring,
    UnitKind,
    UnitProvenance,
)


def _make_dummy_doc(doc_id: str = "doc_test") -> SemanticAnnotationDocument:
    """Create a minimal valid document for testing."""
    u1 = SemanticUnit(
        annotation_id="u1",
        provenance=UnitProvenance(raw_evidence_id="ev1", semantic_block_id="b1"),
        source_span=SourceSpan(char_start=0, char_end=20, text="Alice deployed system"),
        kind=UnitKind.EVENT,
        predicate=PredicateSpec(
            surface_predicate="deployed",
            normalized_predicate="deployed",
            normalization_rule=PredicateNormalizationRule.EXACT_SURFACE,
        ),
        arguments={
            "actor": ArgumentMention(mention_id="m1", role="actor", text="Alice", entity_ref="Alice")
        },
        polarity=PolarityType.POSITIVE,
        modality=ModalityType.ASSERTED,
        epistemic_hedge=EpistemicHedge.NONE,
        holder_ref="user",
        attribution_mode=AttributionMode.DIRECT_SPEAKER,
        temporal_anchoring=TemporalAnchoring(normalized_value="2026-04-01", anchor_type=TemporalAnchorType.EXACT),
        evidence_status=EvidenceStatus.EXPLICIT,
        confidence=1.0,
    )
    u2 = SemanticUnit(
        annotation_id="u2",
        provenance=UnitProvenance(raw_evidence_id="ev2", semantic_block_id="b2"),
        source_span=SourceSpan(char_start=0, char_end=20, text="Service failed now"),
        kind=UnitKind.EVENT,
        predicate=PredicateSpec(
            surface_predicate="failed",
            normalized_predicate="failed",
            normalization_rule=PredicateNormalizationRule.EXACT_SURFACE,
        ),
        arguments={},
        polarity=PolarityType.POSITIVE,
        modality=ModalityType.ASSERTED,
        epistemic_hedge=EpistemicHedge.NONE,
        holder_ref="user",
        attribution_mode=AttributionMode.DIRECT_SPEAKER,
        temporal_anchoring=TemporalAnchoring(normalized_value="2026-04-02", anchor_type=TemporalAnchorType.EXACT),
        evidence_status=EvidenceStatus.EXPLICIT,
        confidence=1.0,
    )
    r1 = SemanticRelation(
        relation_id="r1",
        source_id="u1",
        target_id="u2",
        relation_type=RelationType.CAUSE,
        evidence_status=EvidenceStatus.EXPLICIT,
        confidence=1.0,
        provenance=RelationProvenance(raw_evidence_id="ev2", semantic_block_id="b2"),
    )
    r_ctrl = SemanticRelation(
        relation_id="r_ctrl",
        source_id="u1",
        target_id="u2",
        relation_type=RelationType.NO_RELATION,
        evidence_status=EvidenceStatus.EXPLICIT,
        confidence=1.0,
        provenance=RelationProvenance(raw_evidence_id="ev2", semantic_block_id="b2"),
    )
    return SemanticAnnotationDocument(
        document_id=doc_id,
        cutoff_time="2026-04-10T00:00:00Z",
        units=[u1, u2],
        relations=[r1, r_ctrl],
    )


def test_predicted_graph_compiler_admission_and_schema() -> None:
    """Test predicted graph compiler correctly gates control relations and outputs valid graph."""
    doc = _make_dummy_doc()
    graph = compile_predicted_graph(doc)

    assert isinstance(graph, OracleTypedGraph)
    assert graph.graph_id == "doc_test"
    assert len(graph.unit_nodes) == 2
    assert "u1" in graph.unit_nodes
    assert "u2" in graph.unit_nodes

    # Control relation NO_RELATION must be excluded
    assert len(graph.relation_edges) == 1
    assert graph.relation_edges[0].relation_type == "CAUSE"

    # Mentions & Arguments mapped
    assert len(graph.mention_nodes) == 1
    assert "m1" in graph.mention_nodes
    assert len(graph.canonical_entities) == 1


def test_span_iou_computation() -> None:
    """Test character span IoU computation."""
    assert compute_span_iou(0, 10, 0, 10) == 1.0
    assert compute_span_iou(0, 10, 5, 15) == 5.0 / 15.0
    assert compute_span_iou(0, 10, 10, 20) == 0.0
    assert compute_span_iou(0, 5, 10, 15) == 0.0


def test_graph_pair_comparator() -> None:
    """Test graph comparator on a document compared with itself."""
    doc = _make_dummy_doc()
    comp = compare_graph_pair(doc, doc, case_id="self_test")

    assert comp["node_f1"] == 1.0
    assert comp["edge_f1"] == 1.0
    assert comp["family_metrics"]["CAUSE"]["f1"] == 1.0


def test_eval_split_graph_parity_benchmark() -> None:
    """Run structural parity evaluation on all 40 held-out cases from Issue #15."""
    res = evaluate_eval_split_graph_parity()

    assert res["total_eval_cases"] == 40
    # Proposition node alignment threshold >= 85%
    assert res["mean_node_f1"] >= 0.85, f"Mean node F1 {res['mean_node_f1']} < 0.85"
    # Relation edge fidelity threshold >= 70%
    assert res["mean_edge_f1"] >= 0.70, f"Mean edge F1 {res['mean_edge_f1']} < 0.70"

    # CAUSE family must achieve high precision
    cause_data = res["family_breakdown"]["CAUSE"]
    assert cause_data["precision"] >= 0.80


def test_zero_production_mutation() -> None:
    """Verify that src/lce remains completely untouched by research additions."""
    result = subprocess.run(
        ["git", "status", "--porcelain", "src/lce/"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "", f"Production code modified: {result.stdout}"
