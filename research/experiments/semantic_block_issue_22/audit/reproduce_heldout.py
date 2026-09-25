"""Phase C Reproducibility Rerun Script.

Executes a single, frozen rerun of the Held-Out evaluation across all arms (B0-B4)
and methods (R0-R3) using the locked configuration (gemini-3.1-flash-lite, seed=42, temp=0.0).
Compares the rerun results to the original held_out_results.json.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.experiments.semantic_block_issue_22.benchmark_runner import (
    Issue22BenchmarkRunner,
    load_all_datasets,
)
from research.experiments.semantic_block_issue_22.projection_compiler import (
    CompiledArmRepresentation,
)

BASE_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = BASE_DIR / "results"
AUDIT_DIR = BASE_DIR / "audit"


def run_reproducibility():
    print("=== STARTING PHASE C: FROZEN HELD-OUT REPRODUCIBILITY RERUN ===")
    
    # 1. Load frozen compiled representations from extraction_outputs.json
    with open(RESULTS_DIR / "extraction_outputs.json", "r", encoding="utf-8") as f:
        raw_extractions = json.load(f)

    compiled_items = {}
    for item_id, arms in raw_extractions.items():
        compiled_items[item_id] = {}
        for arm_id, d in arms.items():
            compiled_items[item_id][arm_id] = CompiledArmRepresentation(**d)

    (
        cases,
        gold,
        forks,
        splits,
        queries,
        stress_cases,
        stress_gold,
        stress_queries,
    ) = load_all_datasets()

    fork_group_map = {rid: f["fork_group_id"] for rid, f in forks.items()}
    heldout_core_ids = set(splits["core"]["held_out"])
    heldout_fork_groups = set(splits["temporal_forks"]["held_out"])
    heldout_fork_ids = set(rid for rid, f in forks.items() if f["fork_group_id"] in heldout_fork_groups)
    heldout_item_ids = sorted(list(heldout_core_ids | heldout_fork_ids))
    heldout_queries = [q for q in queries if q["split"] == "held_out"]

    runner = Issue22BenchmarkRunner()
    rerun_results = runner.evaluate_split(
        split_name="held_out",
        item_ids=heldout_item_ids,
        queries=heldout_queries,
        compiled_items=compiled_items,
        fork_group_map=fork_group_map,
        arms=["B0", "B1", "B2", "B3", "B4"],
        methods=["R0", "R1", "R2", "R3"],
    )

    # 2. Compare against original held_out_results.json
    with open(RESULTS_DIR / "held_out_results.json", "r", encoding="utf-8") as f:
        orig_results = json.load(f)

    comparison_report = {
        "status": "COMPLETED",
        "evaluations_compared": 0,
        "perfect_metric_matches": 0,
        "mismatches": [],
        "decision_level_matches": 0,
        "decision_level_total": 0,
    }

    orig_evals = orig_results["evaluations"]
    rerun_evals = rerun_results["evaluations"]

    for arm in ["B0", "B1", "B2", "B3", "B4"]:
        for m in ["R0", "R1", "R2", "R3"]:
            if m not in orig_evals[arm]:
                continue
            for budget_key in ["k_3", "k_5", "k_8"]:
                comparison_report["evaluations_compared"] += 1
                orig_summary = orig_evals[arm][m][budget_key]
                rerun_summary = rerun_evals[arm][m][budget_key]

                metrics_to_check = [
                    "mean_recall_at_k",
                    "target_miss_rate",
                    "mean_first_target_rank",
                    "hard_negative_presence_rate",
                    "mean_final_accepted_target_recall",
                    "mean_false_accepted_cognition_rate",
                    "mean_adjudication_precision",
                ]

                all_matched = True
                for metric in metrics_to_check:
                    diff = abs(orig_summary[metric] - rerun_summary[metric])
                    if diff > 1e-4:
                        all_matched = False
                        comparison_report["mismatches"].append({
                            "arm": arm,
                            "method": m,
                            "budget": budget_key,
                            "metric": metric,
                            "original": orig_summary[metric],
                            "rerun": rerun_summary[metric],
                            "diff": diff,
                        })

                if all_matched:
                    comparison_report["perfect_metric_matches"] += 1

                # Compare query decisions
                orig_qs = orig_summary["queries"]
                rerun_qs = rerun_summary["queries"]
                for i in range(len(orig_qs)):
                    comparison_report["decision_level_total"] += 1
                    oq_adj = orig_qs[i]["adjudication"]
                    rq_adj = rerun_qs[i]["adjudication"]
                    if abs(oq_adj["final_accepted_target_recall"] - rq_adj["final_accepted_target_recall"]) < 1e-4 and \
                       abs(oq_adj["adjudication_precision"] - rq_adj["adjudication_precision"]) < 1e-4:
                        comparison_report["decision_level_matches"] += 1

    comparison_report["match_rate"] = comparison_report["perfect_metric_matches"] / max(1, comparison_report["evaluations_compared"])
    comparison_report["decision_match_rate"] = comparison_report["decision_level_matches"] / max(1, comparison_report["decision_level_total"])

    print("\n=== PHASE C REPRODUCIBILITY RESULTS ===")
    print(f"Evaluations Checked: {comparison_report['evaluations_compared']}")
    print(f"Perfect Metric Matches: {comparison_report['perfect_metric_matches']} / {comparison_report['evaluations_compared']} ({comparison_report['match_rate']*100:.1f}%)")
    print(f"Decision-Level Matches: {comparison_report['decision_level_matches']} / {comparison_report['decision_level_total']} ({comparison_report['decision_match_rate']*100:.1f}%)")
    print(f"Mismatches Count: {len(comparison_report['mismatches'])}")

    with open(AUDIT_DIR / "REPRODUCIBILITY_COMPARISON.json", "w", encoding="utf-8") as f:
        json.dump(comparison_report, f, indent=2, ensure_ascii=False)
    print("Saved REPRODUCIBILITY_COMPARISON.json")


if __name__ == "__main__":
    run_reproducibility()
