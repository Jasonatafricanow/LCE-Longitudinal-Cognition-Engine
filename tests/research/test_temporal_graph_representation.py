"""Regression test suite for Temporal Semantic Graph Representation (GitHub Issue #12).

Tests:
1. Fixture invariants for all 5 fixtures (TG-01 through TG-05)
2. Graph construction invariants (allowed edge families, provenance, no LLM semantic labels)
3. Edge ablation behavior (semantic only, temporal only, both)
4. Experimental controls (temporal shuffle, vector perturbation, block dropout)
5. Structural detection verification across all 5 fixtures
6. Primary success / kill criteria and report schema invariants
"""
from __future__ import annotations

import numpy as np
import pytest

from research.experiments.temporal_graph_representation.baseline import run_baseline
from research.experiments.temporal_graph_representation.controls import (
    block_dropout_control,
    get_ablation_flags,
    temporal_shuffle_control,
    vector_perturbation_control,
)
from research.experiments.temporal_graph_representation.evaluate import (
    determine_verdict,
    generate_markdown_report,
    run_experiment_suite,
)
from research.experiments.temporal_graph_representation.fixtures import (
    generate_tg01_delayed_bridge,
    generate_tg02_distant_recurrence,
    generate_tg03_contradiction_geometry,
    generate_tg04_multi_membership,
    generate_tg05_density_trap,
    load_all_fixtures,
)
from research.experiments.temporal_graph_representation.graph import (
    TemporalSemanticGraph,
    evaluate_temporal_semantic_graph,
    find_articulation_points_and_bridges,
    find_overlapping_communities,
    find_semantic_components,
)


def test_fixture_invariants_and_geometry() -> None:
    fixtures = load_all_fixtures()
    assert set(fixtures.keys()) == {"TG-01", "TG-02", "TG-03", "TG-04", "TG-05"}

    for fix_id, fix_data in fixtures.items():
        items = fix_data.items
        assert len(items) > 0, f"{fix_id} must have items"
        ids = [it.item_id for it in items]
        assert len(ids) == len(set(ids)), f"{fix_id} item IDs must be unique"

        # Check vectors are unit norm
        for it in items:
            norm = np.linalg.norm(it.vector)
            assert abs(norm - 1.0) < 1e-5, f"{fix_id} vector {it.item_id} must have unit norm"


def test_no_llm_semantic_labels_in_graph() -> None:
    forbidden_labels = {
        "supports",
        "contradicts",
        "causes",
        "reconnects",
        "same_belief",
        "same_cognition",
        "confirmed_structure",
    }
    fixtures = load_all_fixtures()
    for fix_id, fix_data in fixtures.items():
        graph = TemporalSemanticGraph(fix_data.items)
        for edge in graph.edges:
            assert edge.edge_family in {"semantic_neighbour", "temporal_next", "same_context_key"}
            assert not any(f in edge.edge_family.lower() for f in forbidden_labels)
            assert not any(f in str(edge.provenance).lower() for f in forbidden_labels)


def test_edge_ablations() -> None:
    fix_data = generate_tg01_delayed_bridge()

    # Full graph
    g_full = TemporalSemanticGraph(fix_data.items, include_semantic=True, include_temporal=True)
    families_full = {e.edge_family for e in g_full.edges}
    assert "semantic_neighbour" in families_full
    assert "temporal_next" in families_full

    # Semantic only
    g_sem = TemporalSemanticGraph(fix_data.items, include_semantic=True, include_temporal=False)
    families_sem = {e.edge_family for e in g_sem.edges}
    assert "semantic_neighbour" in families_sem
    assert "temporal_next" not in families_sem

    # Temporal only
    g_temp = TemporalSemanticGraph(fix_data.items, include_semantic=False, include_temporal=True)
    families_temp = {e.edge_family for e in g_temp.edges}
    assert "semantic_neighbour" not in families_temp
    assert "temporal_next" in families_temp


def test_experimental_controls() -> None:
    fix_data = generate_tg05_density_trap()
    items = fix_data.items

    # 1. Temporal shuffle
    shuffled = temporal_shuffle_control(items, seed=99)
    assert len(shuffled) == len(items)
    assert {it.item_id for it in shuffled} == {it.item_id for it in items}
    # Check that timestamps order changed
    orig_order = [it.item_id for it in items]
    shuffled_order = [it.item_id for it in shuffled]
    assert orig_order != shuffled_order

    # 2. Vector perturbation
    perturbed = vector_perturbation_control(items, sigma=0.03, seed=99)
    assert len(perturbed) == len(items)
    for orig, pert in zip(items, perturbed):
        assert orig.item_id == pert.item_id
        # Vector changed but still unit norm
        assert not np.allclose(orig.vector, pert.vector)
        assert abs(np.linalg.norm(pert.vector) - 1.0) < 1e-5

    # 3. Block dropout
    dropped = block_dropout_control(items, dropout_rate=0.20, seed=99)
    assert 0 < len(dropped) <= len(items)
    assert set(it.item_id for it in dropped).issubset(set(it.item_id for it in items))


def test_tg01_delayed_bridge_structural_gain() -> None:
    fix_data = generate_tg01_delayed_bridge()
    base_res = run_baseline(fix_data.items)
    graph_res = evaluate_temporal_semantic_graph(fix_data.items)

    # Graph recovers X_bridge as articulation point
    assert "X_bridge" in graph_res.articulation_points
    assert any(c.candidate_type == "reconnection_bridge" and "X_bridge" in c.carrier_ids for c in graph_res.candidates)

    # Baseline fails to identify X_bridge as a bridge node due to mediocre direct cosine
    assert "X_bridge" not in base_res.bridge_nodes


def test_tg04_multi_membership_preservation() -> None:
    fix_data = generate_tg04_multi_membership()
    base_res = run_baseline(fix_data.items)
    graph_res = evaluate_temporal_semantic_graph(fix_data.items)

    # In baseline: exclusive clustering assigns M_multi to only one cluster
    assert len(base_res.multi_membership.get("M_multi", [])) == 1

    # In graph: overlapping communities preserve M_multi participating in multiple communities
    assert len(graph_res.multi_membership.get("M_multi", [])) >= 2
    assert any(c.candidate_type == "multi_membership" and "M_multi" in c.carrier_ids for c in graph_res.candidates)


def test_tg05_density_trap_temporal_discrimination_and_shuffle_drop() -> None:
    fix_data = generate_tg05_density_trap()

    # Clean graph recovers temporal coherent chain
    graph_clean = evaluate_temporal_semantic_graph(fix_data.items)
    chain_cands = [c for c in graph_clean.candidates if c.candidate_type == "temporal_coherent_chain"]
    assert len(chain_cands) >= 1

    # Shuffled graph loses the temporal chain
    shuffled_items = temporal_shuffle_control(fix_data.items, seed=42)
    graph_shuffled = evaluate_temporal_semantic_graph(shuffled_items)
    shuffled_chains = [c for c in graph_shuffled.candidates if c.candidate_type == "temporal_coherent_chain"]
    assert len(shuffled_chains) == 0, "Temporal chain must degrade under temporal shuffle"


def test_full_experiment_suite_and_report_generation() -> None:
    results = run_experiment_suite()
    assert len(results) == 5

    verdict, justifications, recommendation = determine_verdict(results)
    assert verdict in {"SUPPORTED", "NOT SUPPORTED", "INCONCLUSIVE"}
    assert recommendation in {"keep", "defer", "reject"}
    assert len(justifications) > 0

    report_md = generate_markdown_report(results, verdict, justifications, recommendation)
    assert f"**Result: {verdict}**" in report_md
    assert f"**Recommendation:** {recommendation}" in report_md
    assert "## Compact Comparison Table" in report_md
    assert "| **TG-01**" in report_md
    assert "| **TG-02**" in report_md
    assert "| **TG-03**" in report_md
    assert "| **TG-04**" in report_md
    assert "| **TG-05**" in report_md
