from __future__ import annotations

from research.experiments.lce_callable_projection_20260927 import experiment as exp


def test_callable_projection_prefers_relevant_branch_over_full_line() -> None:
    result = exp.callable_projection_scenario()

    assert result["selected_projection"] == "p_execution"
    assert result["new_raw_routed_to"] == "p_execution"
    assert result["consumer_context_feature_count"] < result["full_line_feature_count"]
    assert result["context_reduction_fraction"] > 0.5


def test_recursive_projection_closes_to_unique_raw_evidence() -> None:
    graph = exp.build_trading_projection_graph()

    assert graph.raw_closure("p_execution") == frozenset(
        {"r_exec_1", "r_exec_2", "r_exec_3"}
    )
    assert graph.raw_closure("p_reused_higher") == frozenset(
        {
            "r_exec_1",
            "r_exec_2",
            "r_exec_3",
            "r_timing_1",
            "r_timing_2",
        }
    )
    assert "p_execution" not in graph.raw_closure("p_reused_higher")


def test_projection_usage_never_becomes_new_independent_support() -> None:
    result = exp.no_self_evidence_scenario(consumptions=100)

    assert result["q_raw_closure_before_usage"] == ["a", "b", "c"]
    assert result["q_raw_closure_after_usage"] == ["a", "b", "c"]
    assert result["independent_support_count"] == 3
    assert result["p_usage_count"] == 100
    assert result["q_usage_count"] == 100


def test_new_raw_evidence_can_extend_projection_without_raw_rescan() -> None:
    result = exp.callable_projection_scenario()

    assert result["old_execution_raw_closure"] == [
        "r_exec_1",
        "r_exec_2",
        "r_exec_3",
    ]
    assert result["extended_execution_raw_closure"] == [
        "r_exec_1",
        "r_exec_2",
        "r_exec_3",
        "r_exec_4",
    ]


def test_invalidation_can_downgrade_supported_projection_to_unknown() -> None:
    result = exp.rollback_scenario()

    assert result["initial"]["status"] == exp.SUPPORTED
    assert result["after_250_consumptions"]["status"] == exp.SUPPORTED
    assert result["after_source_invalidation"]["status"] == exp.UNKNOWN
    assert result["after_source_invalidation"]["valid_raw_support"] == ["a"]


def test_new_raw_corrections_can_make_previous_compiled_claim_wrong() -> None:
    result = exp.rollback_scenario()

    recompiled = result["recompiled_with_new_raw_corrections"]
    assert recompiled["status"] == exp.WRONG
    assert recompiled["valid_raw_support"] == ["a", "d", "e"]
    assert recompiled["usage_count"] == 0


def test_wrong_is_not_irreversible_and_can_return_to_unknown() -> None:
    result = exp.rollback_scenario()

    assert result["recompiled_with_new_raw_corrections"]["status"] == exp.WRONG
    assert result["after_correction_invalidation"]["status"] == exp.UNKNOWN
    assert result["after_correction_invalidation"]["valid_raw_support"] == ["a"]


def test_nested_dependents_are_traceable_from_invalidated_raw() -> None:
    result = exp.rollback_scenario()

    assert result["affected_by_b"] == ["p_initial", "p_recompiled"]
    assert result["p_initial_raw_closure"] == ["a", "b", "c"]
    assert result["p_recompiled_raw_closure"] == ["a", "b", "c", "d", "e"]


def test_no_manual_abstraction_level_is_required_for_retrieval() -> None:
    graph = exp.build_trading_projection_graph()

    assert not hasattr(graph.projections["p_execution"], "level")
    assert graph.dependency_depth("p_execution") == 1
    assert graph.dependency_depth("p_trading_line") == 2

    ranked = exp.rank_callable_projections(
        graph,
        frozenset({"trading", "execution", "breakout", "entry"}),
        candidate_ids=("p_execution", "p_timing", "p_philosophy", "p_trading_line"),
    )
    assert ranked[0][0] == "p_execution"
