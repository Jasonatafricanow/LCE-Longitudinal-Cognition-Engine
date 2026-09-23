"""Execution runners for Baseline A0 (Semantic Blocks) and Baseline A1 (Atomic Units)."""
from __future__ import annotations

from typing import Any

from research.experiments.oracle_graph_value.candidate_generator import (
    CandidateProposal,
    GenericCandidateGenerator,
)
from research.experiments.oracle_graph_value.embeddings import EmbeddingPipeline
from research.experiments.oracle_graph_value.fixtures.models import LongitudinalFixture


def run_a0_baseline(
    fixture: LongitudinalFixture,
    embedder: EmbeddingPipeline,
    generator: GenericCandidateGenerator | None = None,
) -> list[CandidateProposal]:
    """Execute Baseline A0: coarse semantic-boundary vector baseline."""
    gen = generator or GenericCandidateGenerator(enable_graph_edges=False)

    # Get visible blocks at the latest cutoff
    final_cutoff = fixture.cutoffs[-1]
    visible_blocks = [b for b in fixture.a0_blocks if b.block_id in final_cutoff.visible_a0_block_ids]

    items: list[dict[str, Any]] = []
    for b in visible_blocks:
        vec = embedder.embed_text(b.text)
        items.append({
            "id": b.block_id,
            "vector": vec,
            "occurred_at": b.occurred_start,
            "polarity": "positive",
            "modality": "asserted",
            "holder": "user",
        })

    return gen.generate(items, graph=None)


def run_a1_baseline(
    fixture: LongitudinalFixture,
    embedder: EmbeddingPipeline,
    generator: GenericCandidateGenerator | None = None,
) -> list[CandidateProposal]:
    """Execute Baseline A1: gold atomic semantic units, vector-only (no typed relations)."""
    gen = generator or GenericCandidateGenerator(enable_graph_edges=False)

    # Get visible atomic units at the latest cutoff
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

    return gen.generate(items, graph=None)
