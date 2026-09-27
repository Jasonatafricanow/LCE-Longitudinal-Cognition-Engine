from __future__ import annotations

from research.experiments.lce_surface_overlap_branching_20260927 import (
    experiment as exp,
)


def test_same_polyline_survives_different_state_counts() -> None:
    result = exp.different_length_scenario()

    assert result["point_counts"] == {
        "u_short": 4,
        "u_medium": 7,
        "u_long": 13,
    }
    assert all(
        score > 0.999999
        for score in result["pairwise_shape_similarity"].values()
    )
    assert len(result["surfaces"]) == 1
    assert result["surfaces"][0]["owner_line_ids"] == [
        "line_long",
        "line_medium",
        "line_short",
    ]


def test_worktree_surface_uses_matching_branch_not_whole_tree() -> None:
    result = exp.branching_scenario()
    surface = result["surface"]

    assert "strategy_branch_a" in surface["view_ids"]
    assert "strategy_branch_b" not in surface["view_ids"]
    assert surface["owner_line_ids"] == [
        "line_engineering",
        "line_writing",
        "worktree_strategy",
    ]


def test_nonparticipating_sibling_branch_does_not_leak_into_surface_raw_closure() -> None:
    result = exp.branching_scenario()

    assert result["sibling_branch_raw_in_surface"] == []
    assert result["shared_trunk_raw_in_surface"] == [
        "strategy_t0",
        "strategy_t1",
    ]


def test_branch_choice_is_structural_not_owner_identity() -> None:
    result = exp.branching_scenario()

    assert all(
        score > 0.999999
        for score in result["branch_a_similarity"].values()
    )
    assert all(
        score < 0.90
        for score in result["branch_b_similarity"].values()
    )


def test_one_line_can_participate_in_two_surfaces_without_exclusive_assignment() -> None:
    result = exp.overlap_scenario()

    assert len(result["surfaces"]) == 2
    assert result["trading_surface_membership_count"] == 2
    assert all(
        "line_trading" in membership["owner_line_ids"]
        for membership in result["trading_memberships"]
    )
    assert result["cross_pattern_similarity"] < 0.95


def test_overlapping_surfaces_share_only_the_underlying_raw_support_they_really_share() -> None:
    result = exp.overlap_scenario()

    assert set(result["shared_raw_closure"]) == set(result["expected_trading_raw"])
    assert len(result["shared_raw_closure"]) == 13


def test_surface_discovery_does_not_count_two_views_of_same_line_as_independent_directions() -> None:
    result = exp.overlap_scenario()

    for surface in result["surfaces"]:
        owners = surface["owner_line_ids"]
        assert len(owners) == len(set(owners))
        assert surface["min_shape_similarity"] > 0.999999


def test_relation_views_are_graph_structure_not_manual_abstraction_levels() -> None:
    views = exp.overlap_fixture()
    graph = exp.build_overlap_projection_graph(views)

    assert not hasattr(graph.projections["trade_view_u"], "level")
    assert not hasattr(graph.projections["trade_view_f"], "level")
    assert graph.raw_closure("trade_view_u") == graph.raw_closure("trade_view_f")
