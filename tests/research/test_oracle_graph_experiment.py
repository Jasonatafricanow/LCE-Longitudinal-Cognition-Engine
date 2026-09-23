"""Automated regression test suite for Issue #16: Oracle Typed Graph Incremental Value.

Tests:
1. Ingestion security guard: asserts passing prediction files raises SecurityAdmissionError.
2. Fixture generation integrity: all 8 families compile with valid schemas.
3. Shared embedding consistency between A0 and A1.
4. Generic candidate generator determinism across all fixtures.
5. Full experiment execution and SUPPORTED verdict assertions.
6. Zero production mutation (src/lce/ untouched).
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import pytest

from research.oracle_graph.compiler import SecurityAdmissionError, compile_oracle_graph
from research.oracle_graph.models import OracleTypedGraph
from research.oracle_graph.serializer import canonical_graph_json, compute_graph_digest
from research.experiments.oracle_graph_value.embeddings import EmbeddingPipeline, cosine_similarity
from research.experiments.oracle_graph_value.fixtures.generator import generate_all_fixtures
from research.experiments.oracle_graph_value.fixtures.models import LongitudinalFixture
from research.experiments.oracle_graph_value.candidate_generator import GenericCandidateGenerator
from research.experiments.oracle_graph_value.run_experiment import run_full_experiment


def test_security_admission_guard_rejects_predictions(tmp_path: Path) -> None:
    """Security admission guard must reject any predictions or uncertified files."""
    fixtures = generate_all_fixtures()
    doc = fixtures[0].gold_document

    # Test rejection of canonical prediction benchmark file
    with pytest.raises(SecurityAdmissionError, match="CRITICAL SECURITY VIOLATION"):
        compile_oracle_graph(
            doc,
            input_provenance_path="research/benchmarks/semantic_annotation_v0_1/predictions_eval.jsonl",
        )

    # Test rejection of any file containing 'prediction' in name
    fake_pred_file = tmp_path / "model_predictions.jsonl"
    fake_pred_file.write_text('{"dummy": true}', encoding="utf-8")
    with pytest.raises(SecurityAdmissionError, match="CRITICAL SECURITY VIOLATION"):
        compile_oracle_graph(doc, input_provenance_path=fake_pred_file)


def test_all_8_fixtures_schema_and_compile() -> None:
    """All 8 fixture families must be generated with valid schemas and compile into OracleTypedGraph."""
    fixtures = generate_all_fixtures()
    assert len(fixtures) == 8

    expected_ids = {
        "F1_delayed_bridge",
        "F2_distant_recurrence",
        "F3_state_revision",
        "F4_post_hoc_vs_causality",
        "F5_holder_attribution",
        "F6_cross_domain_entity",
        "F7_transitive_causal_chain",
        "F8_density_distractor",
    }
    actual_ids = {f.fixture_id for f in fixtures}
    assert actual_ids == expected_ids

    for fix in fixtures:
        assert len(fix.evidence) >= 2
        assert len(fix.cutoffs) >= 2
        assert len(fix.a0_blocks) >= 2
        assert len(fix.gold_document.units) >= 2
        assert fix.oracle.target_type in {
            "bridge",
            "recurrence",
            "revision",
            "causality",
            "attribution",
            "entity_trajectory",
            "causal_chain",
            "distractor_rejection",
        }

        # Compile to Oracle Typed Graph
        graph = compile_oracle_graph(
            fix.gold_document,
            input_provenance_path="gold/annotation/certified_fixture.jsonl",
        )
        assert isinstance(graph, OracleTypedGraph)
        assert graph.graph_id == fix.gold_document.document_id

        # Deterministic serialization and hashing
        serialized = canonical_graph_json(graph)
        assert isinstance(serialized, str)
        h = compute_graph_digest(graph)
        assert len(h) == 64


def test_shared_embedding_consistency_a0_and_a1(tmp_path: Path) -> None:
    """A0 and A1 embeddings must originate from the exact same pipeline and normalize properly."""
    embedder = EmbeddingPipeline(cache_dir=tmp_path / "cache", dim=64)

    text = "Kubernetes deployment drained in us-east"
    v_a0 = embedder.embed_text(text)
    v_a1 = embedder.embed_text(text)

    # Identical vector values
    assert v_a0 == v_a1
    assert len(v_a0) == 64

    # Norm should be approximately 1.0
    norm = sum(x * x for x in v_a0)
    assert abs(norm - 1.0) < 1e-4

    # Orthogonal / distant texts have lower similarity
    diff_text = "Completely unrelated culinary recipe for chocolate cake"
    v_diff = embedder.embed_text(diff_text)
    sim = cosine_similarity(v_a0, v_diff)
    assert sim < 0.30


def test_generic_candidate_generator_determinism() -> None:
    """Candidate generator must produce strictly deterministic rankings."""
    generator = GenericCandidateGenerator()
    items = [
        {"id": "u1", "vector": [1.0, 0.0, 0.0], "occurred_at": "2026-04-01T10:00:00Z"},
        {"id": "u2", "vector": [0.9, 0.1, 0.0], "occurred_at": "2026-04-02T10:00:00Z"},
        {"id": "u3", "vector": [0.0, 1.0, 0.0], "occurred_at": "2026-04-03T10:00:00Z"},
    ]

    p1 = generator.generate(items, graph=None)
    p2 = generator.generate(items, graph=None)

    assert len(p1) == len(p2)
    for a, b in zip(p1, p2):
        assert a.candidate_id == b.candidate_id
        assert a.score == b.score
        assert a.item_ids == b.item_ids


def test_experiment_falsification_supported_verdict() -> None:
    """Run full experiment and verify pre-registered SUPPORTED verdict criteria."""
    summary, report_md = run_full_experiment(output_report=False)

    assert summary["verdict"] == "SUPPORTED"
    assert summary["f1_delta_b_vs_a1"] >= 0.15, f"F1 delta {summary['f1_delta_b_vs_a1']} < 0.15"
    assert summary["distractor_bloat_reduction"] >= 0.40, f"Bloat reduction {summary['distractor_bloat_reduction']} < 0.40"
    assert summary["temporal_sensitivity_b"] >= 0.20, f"Temporal sensitivity {summary['temporal_sensitivity_b']} < 0.20"

    # Superiority of Condition B over A1
    assert summary["metrics_b"]["mean_f1"] > summary["metrics_a1"]["mean_f1"]
    assert "OFFICIAL EXPERIMENT VERDICT: SUPPORTED" in report_md


def test_zero_production_mutation() -> None:
    """Verify that src/lce remains completely untouched by research additions."""
    result = subprocess.run(
        ["git", "status", "--porcelain", "src/lce/"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "", f"Production code modified: {result.stdout}"
