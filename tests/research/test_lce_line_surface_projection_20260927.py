from __future__ import annotations

from research.experiments.lce_line_surface_projection_20260927 import experiment as exp


def test_cross_domain_raw_points_are_far_but_trajectory_shapes_match() -> None:
    result = exp.geometry_scenario()

    for values in result["raw_cross_line_similarity"].values():
        assert values["max"] < 0.05
        assert values["mean"] < 0.02

    for score in result["shape_similarity"].values():
        assert score > 0.99


def test_distractor_line_is_not_promoted_into_surface() -> None:
    result = exp.geometry_scenario()

    assert all(
        score < 0.90
        for score in result["distractor_shape_similarity"].values()
    )
    assert result["surfaces"] == [
        {
            "line_ids": [
                "line_engineering",
                "line_trading",
                "line_writing",
            ],
            "min_pairwise_shape_similarity": 1.0,
        }
    ]


def test_surface_raw_closure_contains_only_underlying_raw_evidence() -> None:
    result = exp.callable_routing_scenario()
    closure = result["surface"]["raw_closure"]

    assert len(closure) == 12
    assert all(
        raw_id.startswith(("eng_", "trade_", "write_"))
        for raw_id in closure
    )
    assert not any(raw_id.startswith("line_") for raw_id in closure)


def test_local_queries_choose_local_lines_not_surface() -> None:
    result = exp.callable_routing_scenario()

    assert result["local_queries"]["trading"]["top"] == "line_trading"
    assert result["local_queries"]["engineering"]["top"] == "line_engineering"
    assert result["local_queries"]["writing"]["top"] == "line_writing"

    for local in result["local_queries"].values():
        assert local["surface_score"] == 0.0
        assert local["surface_rank"] > 1


def test_cross_line_reflective_query_prefers_surface_projection() -> None:
    result = exp.callable_routing_scenario()

    assert result["reflective_query"]["top"] == "surface_shared_trajectory"
    assert result["surface"]["feature_count"] > 0


def test_no_manual_abstraction_level_is_present() -> None:
    lines = exp.fixture_lines()
    graph = exp.build_projection_graph(lines)
    surfaces = exp.discover_surfaces(lines)
    exp.add_surface_projection(
        graph,
        surfaces[0],
        {line.line_id: line for line in lines},
    )

    assert not hasattr(graph.projections["line_trading"], "level")
    assert not hasattr(graph.projections["surface_shared_trajectory"], "level")


def test_corrected_line_can_make_previous_surface_unresolved() -> None:
    result = exp.rollback_scenario()

    assert result["initial_surface_count"] == 1
    assert result["after_corrected_line_surface_count"] == 0
    assert result["current_status"] == exp.UNKNOWN


def test_surface_keeps_historical_provenance_while_current_support_shrinks() -> None:
    result = exp.rollback_scenario()

    assert result["historical_raw_closure_count"] == 12
    assert result["current_valid_raw_closure_count"] == 8
    assert result["invalidated_line_raw_ids"] == [
        "trade_0",
        "trade_1",
        "trade_2",
        "trade_3",
    ]
