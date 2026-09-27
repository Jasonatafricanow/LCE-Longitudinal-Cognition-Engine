"""Fresh untouched corpus for the frozen A4 bootstrap supplier.

A4 parameters were frozen in experiment.py before this corpus was added.
Do not tune A4 from these results inside this run.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from research.experiments.path_b_point_cloud_bootstrap_20260927.experiment import (
    Point,
    _evaluate,
    pair_components,
    mutual_knn,
    persistent_mutual_knn,
)


@dataclass(frozen=True, slots=True)
class HoldoutSpec:
    name: str
    contexts: tuple[str, ...]
    features: tuple[str, ...]


SPECS: tuple[HoldoutSpec, ...] = (
    HoldoutSpec(
        "META_UNCERTAINTY_DISCIPLINE",
        ("ctx_trading", "ctx_engineering", "ctx_writing"),
        (
            "unknown_boundary",
            "optionality",
            "evidence_threshold",
            "avoid_premature_closure",
            "scenario_space",
            "asymmetry",
            "confidence_calibration",
            "new_evidence_required",
        ),
    ),
    HoldoutSpec(
        "ENGINEERING_MINIMAL_CORE",
        ("ctx_engineering", "ctx_runtime"),
        (
            "small_core",
            "boundary_first",
            "interface_reuse",
            "incremental_update",
            "authority_separation",
            "decoupling",
            "avoid_ontology_growth",
            "explicit_lifecycle",
        ),
    ),
    HoldoutSpec(
        "VISUAL_REALISM",
        ("ctx_business", "ctx_visual"),
        (
            "exact_scale",
            "material_accuracy",
            "gravity_contact",
            "minor_imperfection",
            "natural_light",
            "candid_framing",
            "continuity",
            "restrained_retouch",
        ),
    ),
    HoldoutSpec(
        "TRADING_WAIT_FOR_EDGE",
        ("ctx_trading", "ctx_market"),
        (
            "wait_signal",
            "position_size",
            "breakout_quality",
            "sector_strength",
            "valuation_room",
            "trigger_condition",
            "stop_structure",
            "risk_reward",
        ),
    ),
    HoldoutSpec(
        "WRITING_CAUSAL_DENSITY",
        ("ctx_writing", "ctx_analysis"),
        (
            "causal_chain",
            "argument_density",
            "mechanism",
            "strong_judgment",
            "evidence",
            "continuity",
            "avoid_report",
            "counterexample",
        ),
    ),
    HoldoutSpec(
        "LONGITUDINAL_MEMORY_ARCH",
        ("ctx_memory", "ctx_engineering"),
        (
            "semantic_point",
            "point_cloud",
            "thread_handoff",
            "worktree_branch",
            "baseline_freeze",
            "time_authority",
            "unknown_boundary",
            "delta_reasoning",
        ),
    ),
)

GENERIC = ("observe", "compare", "revise", "prefer", "reject")


def _trend_points(spec: HoldoutSpec, index: int) -> list[Point]:
    out: list[Point] = []
    width = len(spec.features)
    for i in range(14):
        day = 8 + i * 27 + index * 3
        # Rotate three features with a non-adjacent stride; no single feature
        # appears in every point.
        start = (i * 3 + index) % width
        features = {
            spec.features[start],
            spec.features[(start + 2) % width],
            spec.features[(start + 5) % width],
            spec.contexts[(i + index) % len(spec.contexts)],
            GENERIC[(i * 2 + index) % len(GENERIC)],
        }
        out.append(
            Point(
                f"h{index}_{i:02d}",
                day,
                frozenset(features),
                frozenset({spec.name}),
            )
        )
    return out


def _decoys() -> list[Point]:
    groups = (
        ("camera_purchase", 66, ("camera", "lens", "price", "shop")),
        ("airport_delay", 152, ("airport", "delay", "gate", "flight")),
        ("restaurant_week", 238, ("restaurant", "menu", "delivery", "meal")),
        ("device_setup", 321, ("device", "setup", "account", "sync")),
    )
    out: list[Point] = []
    for g, (name, day, pool) in enumerate(groups):
        for i in range(4):
            out.append(
                Point(
                    f"hd{g}_{i}",
                    day + i,
                    frozenset(
                        {
                            pool[i % 4],
                            pool[(i + 1) % 4],
                            "observe",
                            f"burst_holdout_{g}",
                        }
                    ),
                    decoy_group=name,
                )
            )
    return out


def _noise() -> list[Point]:
    contexts = (
        "ctx_trading",
        "ctx_engineering",
        "ctx_writing",
        "ctx_business",
        "ctx_memory",
        "daily_life",
    )
    out: list[Point] = []
    for i in range(30):
        out.append(
            Point(
                f"hn{i:02d}",
                5 + i * 12,
                frozenset(
                    {
                        contexts[(i * 5) % len(contexts)],
                        GENERIC[(i * 3) % len(GENERIC)],
                        f"holdout_oneoff_{i}",
                        f"holdout_detail_{(i * 11) % 37}",
                    }
                ),
            )
        )
    return out


def corpus() -> tuple[Point, ...]:
    points: list[Point] = []
    for index, spec in enumerate(SPECS):
        points.extend(_trend_points(spec, index))
    points.extend(_decoys())
    points.extend(_noise())
    return tuple(sorted(points, key=lambda point: (point.day, point.point_id)))


def volume_curve() -> dict[str, object]:
    points = corpus()
    cutoffs = (40, 70, 100, len(points))
    algorithms = {
        "A0_PAIR_COMPONENTS": pair_components,
        "A1_MUTUAL_KNN": mutual_knn,
        "A4_FROZEN_PERSISTENT_MUTUAL_KNN": persistent_mutual_knn,
    }
    results: dict[str, list[dict[str, object]]] = {}
    for name, algorithm in algorithms.items():
        rows: list[dict[str, object]] = []
        for cutoff in cutoffs:
            visible = points[:cutoff]
            evaluation = _evaluate(visible, algorithm(visible))
            rows.append(
                {
                    "cutoff": cutoff,
                    "eligible_trends": evaluation["eligible_trends"],
                    "discovered_trends": evaluation["discovered_trends"],
                    "trend_recall": evaluation["trend_recall"],
                    "candidate_count": evaluation["candidate_count"],
                    "false_candidate_rate": evaluation["false_candidate_rate"],
                    "mean_qualifying_purity": evaluation["mean_qualifying_purity"],
                    "fragmentation_per_discovered_trend": evaluation["fragmentation_per_discovered_trend"],
                }
            )
        results[name] = rows
    return {
        "points": len(points),
        "cutoffs": list(cutoffs),
        "algorithms": results,
    }


def discovery_latency() -> dict[str, object]:
    """First point-cloud size at which each gold trend becomes a valid seed."""

    points = corpus()
    first: dict[str, dict[str, int]] = {}
    all_trends = {spec.name for spec in SPECS}

    for prefix in range(20, len(points) + 1):
        visible = points[:prefix]
        evaluation = _evaluate(visible, persistent_mutual_knn(visible))
        discovered = set(evaluation["discovered_trend_names"])
        for trend in sorted(discovered - set(first)):
            support_count = sum(trend in point.gold_trends for point in visible)
            first[trend] = {
                "visible_points": prefix,
                "trend_support_points": support_count,
            }
        if set(first) == all_trends:
            break

    return {
        "per_trend": first,
        "all_discovered": set(first) == all_trends,
        "max_visible_points_to_discover_all": max(
            (value["visible_points"] for value in first.values()),
            default=None,
        ),
        "max_support_points_to_seed": max(
            (value["trend_support_points"] for value in first.values()),
            default=None,
        ),
        "min_support_points_to_seed": min(
            (value["trend_support_points"] for value in first.values()),
            default=None,
        ),
    }


def temporal_collapse_control() -> dict[str, object]:
    points = corpus()
    bases = {spec.name: 20 + idx * 50 for idx, spec in enumerate(SPECS)}
    offsets = {spec.name: 0 for spec in SPECS}
    collapsed: list[Point] = []
    for point in points:
        if point.gold_trends:
            trend = sorted(point.gold_trends)[0]
            offset = offsets[trend]
            offsets[trend] += 1
            new_day = bases[trend] + (offset % 10)
            collapsed.append(
                Point(
                    point.point_id,
                    new_day,
                    point.features,
                    point.gold_trends,
                    point.decoy_group,
                )
            )
        else:
            collapsed.append(point)
    collapsed_points = tuple(sorted(collapsed, key=lambda p: (p.day, p.point_id)))
    normal = _evaluate(points, persistent_mutual_knn(points))
    collapsed_eval = _evaluate(collapsed_points, persistent_mutual_knn(collapsed_points))
    return {
        "normal": {
            "trend_recall": normal["trend_recall"],
            "candidate_count": normal["candidate_count"],
            "false_candidate_rate": normal["false_candidate_rate"],
        },
        "collapsed": {
            "trend_recall": collapsed_eval["trend_recall"],
            "candidate_count": collapsed_eval["candidate_count"],
            "false_candidate_rate": collapsed_eval["false_candidate_rate"],
        },
    }


def report() -> dict[str, object]:
    return {
        "experiment": "path-b-point-cloud-bootstrap-holdout",
        "frozen_algorithm": {
            "name": "A4_PERSISTENT_MUTUAL_KNN",
            "k": 4,
            "min_similarity": 0.10,
            "min_support": 4,
            "min_span_days": 42,
            "min_time_buckets": 3,
            "bucket_days": 45,
            "min_cohesion": 0.15,
        },
        "corpus": {
            "points": len(corpus()),
            "true_trends": len(SPECS),
            "trend_points": sum(bool(point.gold_trends) for point in corpus()),
            "decoy_points": sum(point.decoy_group is not None for point in corpus()),
            "noise_points": sum(not point.gold_trends and point.decoy_group is None for point in corpus()),
        },
        "volume_curve": volume_curve(),
        "discovery_latency": discovery_latency(),
        "temporal_collapse_control": temporal_collapse_control(),
    }


def main() -> None:
    print(json.dumps(report(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
