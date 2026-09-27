from __future__ import annotations

from dataclasses import replace

from research.experiments.path_b_trajectory_bootstrap_20260927 import experiment as exp


def _shape(points: tuple[exp.Point, ...]) -> tuple[tuple[str, ...], ...]:
    return tuple(
        sorted(
            candidate.ordered_ids
            for candidate in exp.trajectory_candidates(
                points,
                k=3,
                min_similarity=0.08,
            )
        )
    )


def test_gold_labels_do_not_affect_a4r_structure() -> None:
    points = exp.branching_fixture()
    baseline = _shape(points)
    scrambled = tuple(
        replace(point, gold_lines=frozenset({"FAKE"}))
        for point in points
    )
    assert _shape(scrambled) == baseline


def test_sparse_longitudinal_line_survives_large_irrelevant_history() -> None:
    points = exp.sparse_longitudinal_fixture(noise_points=2000)
    candidates = exp.trajectory_candidates(points)
    best = exp._best_for_line(points, candidates, "SPARSE_LINE")

    assert best is not None
    assert best["coverage"] == 1.0
    assert best["purity"] == 1.0
    assert best["candidate"]["support"] == 4
    assert best["candidate"]["logical_span"] == 2900


def test_local_continuity_recovers_dynamic_drift_that_global_cohesion_rejects() -> None:
    points = exp.drift_fixture()
    assert exp._pairwise_mean(points) < 0.15

    legacy = exp.legacy_a4_like(
        points,
        axis="logical",
        k=3,
        min_similarity=0.08,
    )
    assert legacy == ()

    candidates = exp.trajectory_candidates(
        points,
        k=3,
        min_similarity=0.08,
    )
    best = exp._best_for_line(points, candidates, "DRIFT_LINE")

    assert best is not None
    assert best["coverage"] == 1.0
    assert best["candidate"]["support"] == 6
    assert best["candidate"]["mean_local_similarity"] > 0.25


def test_dual_time_blocks_future_leakage_but_allows_retroactive_placement() -> None:
    points = exp.retroactive_fixture()

    pre = exp.visible_at(points, 2025)
    assert "retro_2021" not in {point.point_id for point in pre}

    post = exp.visible_at(points, 2026)
    assert [point.point_id for point in post] == [
        "retro_2020",
        "retro_2021",
        "retro_2022",
        "retro_2023",
    ]

    candidates = exp.trajectory_candidates(
        post,
        k=3,
        min_similarity=0.08,
        min_support=2,
    )
    assert any(
        candidate.ordered_ids == (
            "retro_2020",
            "retro_2021",
            "retro_2022",
            "retro_2023",
        )
        for candidate in candidates
    )


def test_branching_preserves_two_overlapping_paths_instead_of_one_component() -> None:
    points = exp.branching_fixture()
    candidates = exp.trajectory_candidates(
        points,
        k=3,
        min_similarity=0.08,
    )

    best_a = exp._best_for_line(points, candidates, "BRANCH_A")
    best_b = exp._best_for_line(points, candidates, "BRANCH_B")

    assert best_a is not None and best_b is not None
    path_a = best_a["candidate"]["ordered_ids"]
    path_b = best_b["candidate"]["ordered_ids"]

    assert path_a[:2] == ["trunk_0", "trunk_1"]
    assert path_b[:2] == ["trunk_0", "trunk_1"]
    assert path_a != path_b
    assert "a_4" in path_a and "b_4" not in path_a
    assert "b_4" in path_b and "a_4" not in path_b


def test_time_is_diagnostic_evidence_not_structure_admission_gate() -> None:
    points = exp.burst_and_sparse_fixture()
    candidates = exp.trajectory_candidates(
        points,
        k=3,
        min_similarity=0.08,
    )

    burst = exp._best_for_line(points, candidates, "BURST")
    spread = exp._best_for_line(points, candidates, "SPREAD")

    assert burst is not None and spread is not None
    assert burst["coverage"] == spread["coverage"] == 1.0
    assert burst["candidate"]["logical_span"] == 3
    assert spread["candidate"]["logical_span"] == 2900
    assert burst["candidate"]["independent_knowledge_events"] == 1
    assert spread["candidate"]["independent_knowledge_events"] == 4


def test_mature_multi_anchor_surface_expands_recall_without_unrelated_absorption() -> None:
    scores = exp.retrieval_surface_scores()

    assert scores["mature_multi_anchor_to_late"] > scores["single_earliest_to_late"]
    assert scores["mature_multi_anchor_to_late"] > 0.9
    assert scores["mature_multi_anchor_to_unrelated"] == 0.0
