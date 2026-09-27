from __future__ import annotations

from research.experiments.lce_branch_rejoin_20260927 import experiment as exp


def test_pre_rejoin_frontier_contains_both_branches() -> None:
    result = exp.standard_rejoin_scenario()

    assert result["frontier_2023"] == {
        "nodes": ["branch_a_3", "branch_b_3"],
        "state": exp.OPEN,
    }


def test_rejoin_replaces_current_frontier_without_erasing_history() -> None:
    result = exp.standard_rejoin_scenario()

    assert result["frontier_2024"] == {
        "nodes": ["rejoin_4"],
        "state": exp.REJOINED,
    }
    assert result["frontier_2025"] == {
        "nodes": ["post_5"],
        "state": exp.OPEN,
    }

    historical = set(result["historical_nodes_2025"])
    assert {"branch_a_2", "branch_a_3", "branch_b_2", "branch_b_3"} <= historical


def test_rejoin_is_multi_parent_inside_same_line_not_new_line() -> None:
    result = exp.standard_rejoin_scenario()

    assert result["rejoin_parents"] == ["branch_a_3", "branch_b_3"]
    assert result["line_identity_count"] == 1


def test_rejoin_provenance_contains_both_branch_histories_and_trunk() -> None:
    result = exp.standard_rejoin_scenario()
    closure = set(result["rejoin_raw_closure"])

    assert {"t0", "t1"} <= closure
    assert {"a2", "a3"} <= closure
    assert {"b2", "b3"} <= closure
    assert "r4" in closure


def test_post_rejoin_continuation_extends_same_provenance() -> None:
    result = exp.standard_rejoin_scenario()

    rejoin = set(result["rejoin_raw_closure"])
    post = set(result["post_rejoin_raw_closure"])
    assert rejoin < post
    assert "r5" in post


def test_invalidating_rejoin_evidence_reopens_prior_branches() -> None:
    result = exp.invalidation_reopens_branches_scenario()

    assert result["before"] == {
        "nodes": ["post_5"],
        "state": exp.OPEN,
    }
    assert result["after"] == {
        "nodes": ["branch_a_3", "branch_b_3"],
        "state": exp.OPEN,
    }
    assert result["branch_history_preserved"] is True
    assert result["rejoin_visible_after"] is False
    assert result["post_visible_after"] is False
    assert result["line_identity_count"] == 1


def test_late_known_historical_rejoin_does_not_leak_before_knowledge_cutoff() -> None:
    result = exp.late_known_rejoin_scenario()

    assert result["retro_raw"] == {
        "known_at": 2026,
        "logical_at": 2024,
    }
    assert result["cutoff_2025"]["frontier"] == [
        "branch_a_3",
        "branch_b_3",
    ]
    assert result["cutoff_2025"]["state"] == exp.OPEN
    assert "retro_rejoin_4" not in result["cutoff_2025"]["visible_nodes"]


def test_late_known_rejoin_can_reconstruct_past_after_it_becomes_known() -> None:
    result = exp.late_known_rejoin_scenario()

    assert result["cutoff_2026"]["frontier"] == ["retro_rejoin_4"]
    assert result["cutoff_2026"]["state"] == exp.REJOINED
    assert "retro_rejoin_4" in result["cutoff_2026"]["visible_nodes"]

    closure = set(result["retro_rejoin_raw_closure"])
    assert {"a2", "a3", "b2", "b3", "retro_r4"} <= closure


def test_current_convergence_and_historical_divergence_coexist() -> None:
    result = exp.no_history_rewrite_scenario()

    assert result["historical_divergence_preserved"] is True
    assert result["fork_history_erased"] is False
    assert result["current_convergence_present"] is True
    assert result["current_frontier"] == ["post_5"]
