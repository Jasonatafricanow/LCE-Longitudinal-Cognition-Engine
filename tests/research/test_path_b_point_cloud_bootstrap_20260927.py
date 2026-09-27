from __future__ import annotations

from dataclasses import replace

from research.experiments.path_b_point_cloud_bootstrap_20260927 import experiment as exp


def _candidate_shape(points: tuple[exp.Point, ...], algorithm_name: str) -> tuple[tuple[str, ...], ...]:
    algorithm = exp.ALGORITHMS[algorithm_name]
    return tuple(sorted(tuple(sorted(candidate.member_ids)) for candidate in algorithm(points)))


def test_gold_labels_do_not_affect_any_bootstrap_algorithm(monkeypatch) -> None:
    original = exp.corpus()
    baseline = {
        name: _candidate_shape(original, name)
        for name in exp.ALGORITHMS
    }

    scrambled = tuple(
        replace(
            point,
            gold_trends=frozenset({"FAKE_A", "FAKE_B"} if point.gold_trends else ()),
        )
        for point in original
    )
    monkeypatch.setattr(exp, "corpus", lambda: scrambled)

    for name in exp.ALGORITHMS:
        assert _candidate_shape(scrambled, name) == baseline[name]


def test_recurrent_density_rejects_short_coherent_burst() -> None:
    burst = tuple(
        exp.Point(
            f"b{i}",
            100 + i,
            frozenset({"same_topic", "shared_detail", f"x{i}"}),
        )
        for i in range(6)
    )

    assert exp.recurrent_density(burst) == ()
    assert exp.multiscale_recurrent(burst) == ()
    assert exp.persistent_mutual_knn(burst) == ()


def test_recurrent_density_can_seed_long_lived_semantic_recurrence() -> None:
    points = tuple(
        exp.Point(
            f"p{i}",
            i * 35,
            frozenset({"stable_a", "stable_b", f"rotating_{i % 2}"}),
        )
        for i in range(6)
    )

    assert exp.recurrent_density(points)


def test_old_support_is_not_dropped_by_a_hard_temporal_window() -> None:
    points = tuple(
        exp.Point(
            f"p{i}",
            i * 90,
            frozenset({"persistent_theme", "shared_logic", f"detail_{i % 2}"}),
        )
        for i in range(5)
    )

    candidates = exp.recurrent_density(points)
    assert candidates
    assert any({"p0", "p4"}.issubset(candidate.member_ids) for candidate in candidates)


def test_volume_curve_reports_data_quantity_explicitly() -> None:
    curve = exp.volume_curve()

    assert curve["cutoffs"] == sorted(curve["cutoffs"])
    assert curve["cutoffs"][-1] == curve["corpus_points"]
    assert set(curve["algorithms"]) == set(exp.ALGORITHMS)

    for name, rows in curve["algorithms"].items():
        assert len(rows) == len(curve["cutoffs"]), name
        for row in rows:
            if row["trend_recall"] is not None:
                assert 0.0 <= row["trend_recall"] <= 1.0
            assert 0.0 <= row["false_candidate_rate"] <= 1.0


def test_temporal_shuffle_control_keeps_same_semantic_points() -> None:
    report = exp.temporal_shuffle_control()

    assert set(report) == {"A2_RECURRENT_DENSITY", "A3_MULTISCALE_RECURRENT"}
    for values in report.values():
        assert set(values) == {"normal", "shuffled"}


def test_temporal_collapse_control_is_reported_for_recurrent_suppliers() -> None:
    report = exp.temporal_collapse_control()

    assert set(report) == {
        "A2_RECURRENT_DENSITY",
        "A3_MULTISCALE_RECURRENT",
        "A4_PERSISTENT_MUTUAL_KNN",
    }
    for values in report.values():
        assert set(values) == {"normal", "collapsed"}


def test_a4_parameter_sweep_is_bounded_and_reproducible() -> None:
    rows = exp.a4_parameter_sweep()

    assert len(rows) == 12
    for row in rows:
        assert row["k"] in {3, 4, 5, 6}
        assert row["min_span_days"] in {30, 60, 90}
        assert 0.0 <= row["false_candidate_rate"] <= 1.0
        if row["trend_recall"] is not None:
            assert 0.0 <= row["trend_recall"] <= 1.0
