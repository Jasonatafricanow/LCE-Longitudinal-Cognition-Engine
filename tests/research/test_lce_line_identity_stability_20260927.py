from __future__ import annotations

from research.experiments.lce_line_identity_stability_20260927 import (
    experiment as exp,
)


def test_branch_proliferation_does_not_clone_lines() -> None:
    result = exp.proliferation_scenario()

    assert result["before"]["line_count"] == 1
    assert result["before"]["branch_count"] == 24
    assert result["after"]["line_count"] == 1
    assert result["after"]["branch_count"] == 24


def test_many_callable_projections_do_not_become_persistent_cognition_nodes() -> None:
    result = exp.proliferation_scenario()

    assert result["after"]["projection_materializations"] == 500
    assert result["persistent_projection_node_count"] == 0
    assert result["after"]["line_count"] == 1


def test_callable_projection_keeps_owner_and_branch_provenance() -> None:
    result = exp.proliferation_scenario()
    projection = result["first_projection"]

    assert projection["owner_line_id"] == "line_trading"
    assert projection["source_branch_id"] == "branch_0"
    assert {"trunk_0", "trunk_1", "trunk_2", "trunk_3"} <= set(
        projection["raw_closure"]
    )
    assert {"b0_0", "b0_1", "b0_2"} <= set(projection["raw_closure"])


def test_same_line_can_join_two_surfaces_through_two_real_branches_without_cloning() -> None:
    result = exp.surface_branch_reference_scenario()

    assert result["trading_line_identity_count"] == 1
    assert result["surface_count"] == 2
    memberships = result["trading_surface_memberships"]
    assert memberships == [
        {"surface_id": "surface_timing", "branch_ids": ["trade_timing"]},
        {"surface_id": "surface_execution", "branch_ids": ["trade_execution"]},
    ]
    assert result["persistent_relation_view_nodes"] == 0


def test_surface_closure_only_contains_the_participating_branch_not_sibling() -> None:
    result = exp.surface_branch_reference_scenario()

    timing = set(result["surface_timing_raw"])
    execution = set(result["surface_execution_raw"])

    assert "trade_timing_raw" in timing
    assert "trade_execution_raw" not in timing
    assert "trade_execution_raw" in execution
    assert "trade_timing_raw" not in execution

    assert "trade_trunk" in timing
    assert "trade_trunk" in execution


def test_one_surface_cannot_fake_independent_support_with_three_branches_of_one_line() -> None:
    result = exp.duplicate_owner_surface_rejection_scenario()

    assert result["rejected"] is True
    assert result["surface_count"] == 0
    assert result["line_count"] == 1


def test_early_branch_is_not_immediately_a_split_candidate() -> None:
    result = exp.split_candidate_scenario()

    assert result["early"]["unique_branch_raw"] == 1
    assert result["early"]["split_candidate"] is False
    assert result["line_count_before_candidate"] == 1


def test_mature_independent_branch_can_become_candidate_without_auto_split() -> None:
    result = exp.split_candidate_scenario()

    assert result["mature"]["split_candidate"] is True
    assert result["mature"]["candidate"]["owner_line_id"] == "line_root"
    assert result["mature"]["candidate"]["branch_id"] == "branch_mature"

    assert result["line_count_after_candidate"] == 1
    assert result["new_line_created"] is False
    assert result["candidate_is_non_mutating"] is True


def test_candidate_support_closes_to_existing_raw_not_cloned_evidence() -> None:
    result = exp.split_candidate_scenario()
    closure = set(result["mature"]["candidate"]["raw_closure"])

    assert {"t0", "t1", "t2"} <= closure
    assert {f"mature_{index}" for index in range(5)} <= closure
    assert "mature_child_a_raw" not in closure
    assert "mature_child_b_raw" not in closure
