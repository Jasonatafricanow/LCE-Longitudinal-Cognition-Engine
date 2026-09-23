"""AGY Graph vs Oracle Comparison Experiment package (GitHub Issue #17)."""
from research.experiments.agy_graph_vs_oracle.graph_compiler import compile_predicted_graph
from research.experiments.agy_graph_vs_oracle.graph_comparator import (
    compare_graph_pair,
    evaluate_eval_split_graph_parity,
)
from research.experiments.agy_graph_vs_oracle.parser_pipeline import (
    parse_all_fixtures_with_agy_parser,
    parse_fixture_with_agy_parser,
)
from research.experiments.agy_graph_vs_oracle.run_experiment import (
    run_b_hat_condition,
    run_full_issue_17_experiment,
)

__all__ = [
    "compile_predicted_graph",
    "compare_graph_pair",
    "evaluate_eval_split_graph_parity",
    "parse_fixture_with_agy_parser",
    "parse_all_fixtures_with_agy_parser",
    "run_b_hat_condition",
    "run_full_issue_17_experiment",
]
