"""Execution runners for Condition B (Oracle Typed Graph) and Edge-Family Ablations."""
from __future__ import annotations

from typing import Any

from research.experiments.oracle_graph_value.candidate_generator import (
    CandidateProposal,
    GenericCandidateGenerator,
)
from research.experiments.oracle_graph_value.embeddings import EmbeddingPipeline
from research.experiments.oracle_graph_value.fixtures.models import LongitudinalFixture
from research.oracle_graph.compiler import OracleGraphCompiler


def run_b_condition(
    fixture: LongitudinalFixture,
    embedder: EmbeddingPipeline,
    ablate_edge_types: set[str] | None = None,
    generator: GenericCandidateGenerator | None = None,
) -> list[CandidateProposal]:
    """Execute Condition B: gold atomic units + Oracle Typed Graph relations."""
    # 1. Compile Oracle Typed Graph from gold document
    graph = OracleGraphCompiler.compile_document(fixture.gold_document, graph_id=f"oracle_{fixture.fixture_id}")

    # 2. Get visible units at final cutoff
    final_cutoff = fixture.cutoffs[-1]
    visible_units = [u for u in fixture.gold_document.units if u.annotation_id in final_cutoff.visible_unit_ids]

    items: list[dict[str, Any]] = []
    for u in visible_units:
        vec = embedder.embed_text(u.source_span.text)
        items.append({
            "id": u.annotation_id,
            "vector": vec,
            "occurred_at": u.temporal_anchoring.normalized_value,
            "polarity": u.polarity.value,
            "modality": u.modality.value,
            "holder": u.holder_ref,
        })

    # 3. Execute candidate generator with graph enabled and ablations applied
    abl = ablate_edge_types or set()
    gen = GenericCandidateGenerator(
        enable_graph_edges=True,
        ablate_edge_types=abl,
        sim_threshold=generator.sim_threshold if generator else 0.50,
        max_candidates=generator.max_candidates if generator else 15,
    )
    return gen.generate(items, graph=graph)


def run_isolated_edge_ablation(
    fixture: LongitudinalFixture,
    embedder: EmbeddingPipeline,
    edge_type: str,
    generator: GenericCandidateGenerator | None = None,
) -> list[CandidateProposal]:
    """Execute Condition B with exactly one edge type ablated for causal attribution."""
    return run_b_condition(
        fixture=fixture,
        embedder=embedder,
        ablate_edge_types={edge_type},
        generator=generator,
    )


def run_all_ablations(
    fixture: LongitudinalFixture,
    embedder: EmbeddingPipeline,
) -> dict[str, list[CandidateProposal]]:
    """Run full B condition alongside all edge-family ablations."""
    return {
        "B_full": run_b_condition(fixture, embedder, ablate_edge_types=set()),
        "B_no_temporal": run_b_condition(fixture, embedder, ablate_edge_types={"BEFORE", "AFTER"}),
        "B_no_causal": run_b_condition(fixture, embedder, ablate_edge_types={"CAUSE"}),
        "B_no_incompatible": run_b_condition(fixture, embedder, ablate_edge_types={"INCOMPATIBLE"}),
        "B_no_coref": run_b_condition(fixture, embedder, ablate_edge_types={"SAME_ENTITY"}),
        "B_no_discourse": run_b_condition(fixture, embedder, ablate_edge_types={"CONDITION", "CONCESSION", "PURPOSE", "CONTRAST", "EQUIVALENT"}),
    }
