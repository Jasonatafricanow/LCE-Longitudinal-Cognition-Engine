"""Evaluation engine and pre-registered falsification criteria auditor for Issue #16."""
from __future__ import annotations

from typing import Any

from research.experiments.oracle_graph_value.candidate_generator import CandidateProposal
from research.experiments.oracle_graph_value.fixtures.models import LongitudinalFixture


def evaluate_fixture_proposals(
    proposals: list[CandidateProposal],
    fixture: LongitudinalFixture,
    is_a0: bool = False,
    k: int = 5,
) -> dict[str, Any]:
    """Evaluate candidate proposals against the fixture's TargetOracle."""
    oracle = fixture.oracle
    target_type = oracle.target_type
    target_ids = set(oracle.target_block_ids if is_a0 else oracle.target_unit_ids)

    top_k = proposals[:k]
    candidate_count = len(proposals)

    # Special handling for distractor rejection (F8)
    if target_type == "distractor_rejection":
        # Target expectation is 0 candidates (clean rejection)
        # If 0 candidates emitted, precision = 1.0, recall = 1.0
        # If candidates emitted, they are false positives!
        if candidate_count == 0:
            return {
                "recovered": True,
                "recall": 1.0,
                "precision": 1.0,
                "f1": 1.0,
                "bloat_ratio": 0.0,
                "candidate_count": 0,
            }
        else:
            return {
                "recovered": False,
                "recall": 0.0,
                "precision": 0.0,
                "f1": 0.0,
                "bloat_ratio": float(candidate_count),
                "candidate_count": candidate_count,
            }

    # For positive targets (F1-F7)
    recovered = False
    valid_matches = 0

    for cand in top_k:
        cand_items = set(cand.item_ids)
        # Check intersection / match with target IDs
        if target_ids.issubset(cand_items) or (cand.candidate_type == target_type and len(target_ids.intersection(cand_items)) >= 2):
            recovered = True
            valid_matches += 1

    recall = 1.0 if recovered else 0.0
    precision = (valid_matches / len(top_k)) if len(top_k) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0.0 else 0.0
    bloat_ratio = candidate_count / 1.0  # 1 ground truth target

    return {
        "recovered": recovered,
        "recall": recall,
        "precision": precision,
        "f1": f1,
        "bloat_ratio": round(bloat_ratio, 2),
        "candidate_count": candidate_count,
    }


def compute_aggregate_metrics(
    eval_results: dict[str, dict[str, Any]]
) -> dict[str, float]:
    """Compute mean metrics across all fixtures."""
    n = len(eval_results)
    if n == 0:
        return {}

    mean_recall = sum(r["recall"] for r in eval_results.values()) / n
    mean_precision = sum(r["precision"] for r in eval_results.values()) / n
    mean_f1 = sum(r["f1"] for r in eval_results.values()) / n
    mean_bloat = sum(r["bloat_ratio"] for r in eval_results.values()) / n

    return {
        "mean_recall": round(mean_recall, 4),
        "mean_precision": round(mean_precision, 4),
        "mean_f1": round(mean_f1, 4),
        "mean_bloat_ratio": round(mean_bloat, 2),
    }


def evaluate_falsification_verdict(
    metrics_a0: dict[str, float],
    metrics_a1: dict[str, float],
    metrics_b: dict[str, float],
    distractor_bloat_a1: float,
    distractor_bloat_b: float,
    temporal_sensitivity_b: float,
    temporal_sensitivity_a1: float,
) -> dict[str, Any]:
    """Evaluate pre-registered decision rules for SUPPORTED / NOT SUPPORTED / INCONCLUSIVE."""
    f1_delta_b_vs_a1 = metrics_b["mean_f1"] - metrics_a1["mean_f1"]
    distractor_reduction = (distractor_bloat_a1 - distractor_bloat_b) / max(distractor_bloat_a1, 0.001)

    verdict = "INCONCLUSIVE"
    reasons: list[str] = []

    # Rule 1: SUPPORTED criteria
    if (
        f1_delta_b_vs_a1 >= 0.15
        and distractor_reduction >= 0.40
        and temporal_sensitivity_b >= 0.20
    ):
        verdict = "SUPPORTED"
        reasons.append(f"Condition B outperforms A1 by {round(f1_delta_b_vs_a1 * 100, 1)}% F1 (threshold: >= 15%).")
        reasons.append(f"Condition B achieves {round(distractor_reduction * 100, 1)}% bloat reduction under distractor noise (threshold: >= 40%).")
        reasons.append(f"Condition B exhibits significant temporal sensitivity: {round(temporal_sensitivity_b * 100, 1)}% drop under shuffle (threshold: >= 20%).")

    # Rule 2: NOT SUPPORTED criteria
    elif (
        f1_delta_b_vs_a1 < 0.05
        or (metrics_b["mean_bloat_ratio"] >= 3.0 and metrics_b["mean_precision"] < 0.30)
    ):
        verdict = "NOT SUPPORTED"
        if f1_delta_b_vs_a1 < 0.05:
            reasons.append(f"Condition A1 achieves within {round(f1_delta_b_vs_a1 * 100, 1)}% F1 of Condition B without graph edges.")
        if metrics_b["mean_bloat_ratio"] >= 3.0 and metrics_b["mean_precision"] < 0.30:
            reasons.append(f"Condition B triggers combinatorial candidate bloat ({metrics_b['mean_bloat_ratio']}x) with low precision ({metrics_b['mean_precision']}).")

    # Rule 3: INCONCLUSIVE
    else:
        verdict = "INCONCLUSIVE"
        reasons.append(f"F1 delta B vs A1 is moderate ({round(f1_delta_b_vs_a1 * 100, 1)}%), but did not meet full pre-registered SUPPORTED thresholds.")

    return {
        "verdict": verdict,
        "f1_delta_b_vs_a1": round(f1_delta_b_vs_a1, 4),
        "distractor_bloat_reduction": round(distractor_reduction, 4),
        "temporal_sensitivity_b": round(temporal_sensitivity_b, 4),
        "temporal_sensitivity_a1": round(temporal_sensitivity_a1, 4),
        "reasons": reasons,
    }
