"""Master Experiment Driver for Semantic Compilation Body/AGY Experiment V1.

Executes across model arms, computes closures, evaluates against ground truth,
records JSONL logs, and aggregates multi-dimensional metrics.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from research.experiments.semantic_compilation_body_v1.closure import compile_semantic_closure
from research.experiments.semantic_compilation_body_v1.evaluate import CaseEvaluator
from research.experiments.semantic_compilation_body_v1.runner import ModelRunner
from research.experiments.semantic_compilation_body_v1.schema import SemanticParseResultV1
from research.experiments.semantic_compilation_body_v1.validator import validate_parse_result

HERE = Path(__file__).resolve().parent
CASES_FILE = HERE / "cases" / "cases.json"
GT_FILE = HERE / "cases" / "ground_truth.json"
RESULTS_DIR = HERE / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def run_experiment(model_arm: str = "deepseek_v4_flash", limit: int | None = None) -> dict[str, Any]:
    print(f"\n=======================================================")
    print(f"Starting Semantic Compilation Experiment Arm: {model_arm}")
    print(f"=======================================================")

    cases_data = json.loads(CASES_FILE.read_text(encoding="utf-8"))["cases"]
    gt_data = json.loads(GT_FILE.read_text(encoding="utf-8"))

    if limit is not None:
        cases_data = cases_data[:limit]

    runner = ModelRunner(model_arm=model_arm, temperature=0.0)
    evaluator = CaseEvaluator(gt_data)

    records: list[dict[str, Any]] = []
    error_counter: Counter[str] = Counter()
    metric_sums: dict[str, float] = defaultdict(float)
    metric_counts: dict[str, int] = defaultdict(int)

    depth_metrics: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    depth_counts: dict[str, int] = defaultdict(int)

    out_jsonl = RESULTS_DIR / f"semantic_compilation_body_v1_{model_arm}.jsonl"
    with open(out_jsonl, "w", encoding="utf-8") as jf:
        for idx, case in enumerate(cases_data):
            cid = case["case_id"]
            turn_count = len(case["dialogue"])
            if turn_count == 1:
                depth_bucket = "1-turn"
            elif turn_count == 2:
                depth_bucket = "2-turn"
            elif turn_count <= 5:
                depth_bucket = "3-5 turns"
            else:
                depth_bucket = "5+ turns"

            print(f"[{idx+1:02d}/{len(cases_data)}] Running {cid} ({turn_count} turns)...", end=" ", flush=True)

            try:
                raw_rec = runner.run_case(case, use_cache=True)
                val_parse, diags = validate_parse_result(
                    raw_rec["raw_output"],
                    source_refs=[t["evidence_id"] for t in case["dialogue"]],
                )
                blocks, defs = compile_semantic_closure(val_parse, case_id=cid)
                eval_res = evaluator.evaluate_case(case, val_parse, blocks, defs)

                for err in eval_res["errors"]:
                    error_counter[err] += 1

                for k, v in eval_res["metrics"].items():
                    metric_sums[k] += v
                    metric_counts[k] += 1
                    depth_metrics[depth_bucket][k] += v
                depth_counts[depth_bucket] += 1

                full_item = {
                    "case_id": cid,
                    "model_arm": model_arm,
                    "model_identity": raw_rec.get("model_identity", model_arm),
                    "context_turns": turn_count,
                    "depth_bucket": depth_bucket,
                    "phenomena": case.get("phenomena", []),
                    "raw_text": [t["text"] for t in case["dialogue"]],
                    "raw_refs": [t["evidence_id"] for t in case["dialogue"]],
                    "model_raw_output": raw_rec.get("raw_output", ""),
                    "diagnostics": diags,
                    "latency_ms": raw_rec.get("latency_ms", 0),
                    "usage": raw_rec.get("usage", {}),
                    "validated_parse": val_parse.model_dump(),
                    "semantic_points": [p.model_dump() for p in val_parse.semantic_points],
                    "dependencies": [d.model_dump() for d in val_parse.dependencies],
                    "compiled_blocks": [b.model_dump() for b in blocks],
                    "deferred_point_ids": defs,
                    "ground_truth": gt_data.get(cid, {}),
                    "evaluation": eval_res,
                    "error_codes": eval_res["errors"],
                }
                records.append(full_item)
                jf.write(json.dumps(full_item, ensure_ascii=False) + "\n")
                jf.flush()

                status_str = "PASS" if eval_res["pass_all"] else f"FAIL ({', '.join(eval_res['errors'])})"
                print(f"{status_str} [Blocks: {len(blocks)}, Pts: {len(val_parse.semantic_points)}]")

            except Exception as e:
                print(f"ERROR: {e}")
                err_item = {
                    "case_id": cid,
                    "model_arm": model_arm,
                    "error": str(e),
                }
                records.append(err_item)
                jf.write(json.dumps(err_item, ensure_ascii=False) + "\n")

    # Aggregate metrics
    summary_metrics = {}
    for k in metric_sums:
        summary_metrics[k] = round(metric_sums[k] / max(1, metric_counts[k]), 4)

    # Aggregate depth metrics
    depth_summary = {}
    for db in depth_counts:
        depth_summary[db] = {
            "count": depth_counts[db],
            "context_completeness": round(depth_metrics[db]["final_block_context_completeness"] / max(1, depth_counts[db]), 4),
            "semantic_recall": round(depth_metrics[db]["semantic_recall"] / max(1, depth_counts[db]), 4),
            "overmerge_rate": round(depth_metrics[db]["final_block_overmerge_rate"] / max(1, depth_counts[db]), 4),
            "fragmentation_rate": round(depth_metrics[db]["final_block_fragmentation_rate"] / max(1, depth_counts[db]), 4),
        }

    summary = {
        "model_arm": model_arm,
        "total_cases": len(cases_data),
        "evaluated_cases": len(records),
        "pass_all_rate": round(sum(1 for r in records if r.get("evaluation", {}).get("pass_all", False)) / max(1, len(records)), 4),
        "metrics": summary_metrics,
        "error_distribution": dict(error_counter.most_common()),
        "depth_breakdown": depth_summary,
    }

    summary_file = RESULTS_DIR / f"summary_{model_arm}.json"
    summary_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n----------------- SUMMARY METRICS -----------------")
    for k, v in summary_metrics.items():
        print(f"  {k:35s}: {v:0.4f}")
    print("\n----------------- ERROR DISTRIBUTION --------------")
    for err, cnt in error_counter.most_common():
        print(f"  {err:5s}: {cnt:3d}")
    print(f"\nOverall Pass Rate: {summary['pass_all_rate']*100:.1f}%\n")

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="deepseek_v4_flash", choices=["deepseek_v4_flash", "gemini_2_5_flash", "glm_4_flash"])
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    run_experiment(model_arm=args.model, limit=args.limit)
