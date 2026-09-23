"""Oracle Typed Graph Incremental Value Experiment package (GitHub Issue #16)."""
from research.experiments.oracle_graph_value.ablations import run_all_ablations, run_b_condition
from research.experiments.oracle_graph_value.baselines import run_a0_baseline, run_a1_baseline
from research.experiments.oracle_graph_value.candidate_generator import (
    CandidateProposal,
    GenericCandidateGenerator,
)
from research.experiments.oracle_graph_value.embeddings import EmbeddingPipeline, cosine_similarity
from research.experiments.oracle_graph_value.evaluator import (
    compute_aggregate_metrics,
    evaluate_falsification_verdict,
    evaluate_fixture_proposals,
)
from research.experiments.oracle_graph_value.fixtures import (
    LongitudinalFixture,
    generate_all_fixtures,
)

__all__ = [
    "run_a0_baseline",
    "run_a1_baseline",
    "run_b_condition",
    "run_all_ablations",
    "CandidateProposal",
    "GenericCandidateGenerator",
    "EmbeddingPipeline",
    "cosine_similarity",
    "evaluate_fixture_proposals",
    "compute_aggregate_metrics",
    "evaluate_falsification_verdict",
    "LongitudinalFixture",
    "generate_all_fixtures",
]
