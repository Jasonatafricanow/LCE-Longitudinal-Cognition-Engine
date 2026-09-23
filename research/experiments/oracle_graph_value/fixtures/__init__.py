"""Longitudinal fixture corpus for GitHub Issue #16 experiment."""
from research.experiments.oracle_graph_value.fixtures.generator import (
    generate_all_fixtures,
    generate_f1_delayed_bridge,
    generate_f2_distant_recurrence,
    generate_f3_state_revision,
    generate_f4_post_hoc_causality,
    generate_f5_holder_attribution,
    generate_f6_cross_domain_entity,
    generate_f7_transitive_causal_chain,
    generate_f8_density_distractor,
)
from research.experiments.oracle_graph_value.fixtures.models import (
    A0SemanticBlock,
    CutoffView,
    EvidenceItem,
    LongitudinalFixture,
    TargetOracle,
)

__all__ = [
    "EvidenceItem",
    "A0SemanticBlock",
    "TargetOracle",
    "CutoffView",
    "LongitudinalFixture",
    "generate_all_fixtures",
    "generate_f1_delayed_bridge",
    "generate_f2_distant_recurrence",
    "generate_f3_state_revision",
    "generate_f4_post_hoc_causality",
    "generate_f5_holder_attribution",
    "generate_f6_cross_domain_entity",
    "generate_f7_transitive_causal_chain",
    "generate_f8_density_distractor",
]
