"""Runner for One-Pass Multi-Turn Semantic Compilation Experiment.

Executes:
  1. Condition A: Baseline One-Pass Prompt (35 cases)
  2. Condition B: Patched One-Pass Prompt with Anti-Omission Protocols (35 cases)
  3. Latency & Token Overhead Benchmark (Pure conversational baseline vs One-Pass)
  4. Generates results/one_pass_multiturn_baseline.jsonl,
     results/one_pass_multiturn_patched.jsonl,
     and results/summary_one_pass.json
"""

from __future__ import annotations

import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
_logger = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research.experiments.semantic_compilation_body_v1.one_pass.body_adapter import BodyAdapter
from research.experiments.semantic_compilation_body_v1.one_pass.evaluate_one_pass import OnePassEvaluator

RESULTS_DIR = HERE / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

PROMPT_BASELINE = (HERE / "prompt_one_pass.md").read_text(encoding="utf-8")
PROMPT_PATCHED = (HERE / "prompt_one_pass_patched.md").read_text(encoding="utf-8")


def _run_single_case(case: dict[str, Any], adapter: BodyAdapter, sys_prompt: str, evaluator: OnePassEvaluator) -> dict[str, Any]:
    cid = case["case_id"]
    turn_res = adapter.run_turn(
        dialogue=case["dialogue"],
        system_override=sys_prompt,
        case_id=cid,
    )
    eval_res = evaluator.evaluate_case(case, turn_res)
    return eval_res


def run_experiment():
    cases_file = HERE / "cases_multiturn_v1.json"
    gt_file = HERE / "ground_truth_multiturn_v1.json"

    cases: list[dict[str, Any]] = json.loads(cases_file.read_text(encoding="utf-8"))
    ground_truth: dict[str, Any] = json.loads(gt_file.read_text(encoding="utf-8"))

    evaluator = OnePassEvaluator(ground_truth)

    _logger.info("Loaded %d multi-turn test cases.", len(cases))

    # -------------------------------------------------------------------------
    # 1. Benchmark: Pure Baseline Conversational Overhead (no sidecar)
    # -------------------------------------------------------------------------
    _logger.info("--- Step 1: Measuring Pure Conversational Baseline Overhead ---")
    baseline_adapter = BodyAdapter()
    baseline_stats = []
    for c in cases[:15]:
        res_pure = baseline_adapter.run_baseline_turn(c["dialogue"], case_id=c["case_id"])
        baseline_stats.append({
            "latency_ms": res_pure["latency_ms"],
            "total_tokens": res_pure["usage"]["total_tokens"],
            "completion_tokens": res_pure["usage"]["completion_tokens"],
        })
    avg_pure_latency = sum(s["latency_ms"] for s in baseline_stats) / len(baseline_stats)
    avg_pure_tokens = sum(s["total_tokens"] for s in baseline_stats) / len(baseline_stats)
    avg_pure_comp_tokens = sum(s["completion_tokens"] for s in baseline_stats) / len(baseline_stats)
    _logger.info("Pure Baseline: Latency=%.1fms, TotalTokens=%.1f, CompTokens=%.1f",
                 avg_pure_latency, avg_pure_tokens, avg_pure_comp_tokens)

    # -------------------------------------------------------------------------
    # 2. Condition A: One-Pass Baseline Prompt (Parallel 3 workers)
    # -------------------------------------------------------------------------
    _logger.info("--- Step 2: Running Condition A (One-Pass Baseline Prompt) ---")
    adapter_baseline = BodyAdapter(system_prompt=PROMPT_BASELINE, temperature=0.0)
    baseline_eval_results: list[dict[str, Any]] = []
    baseline_jsonl = RESULTS_DIR / "one_pass_multiturn_baseline.jsonl"

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_map = {
            executor.submit(_run_single_case, c, adapter_baseline, PROMPT_BASELINE, evaluator): c
            for c in cases
        }
        done_cnt = 0
        with open(baseline_jsonl, "w", encoding="utf-8") as f_out:
            for fut in as_completed(future_map):
                done_cnt += 1
                eval_res = fut.result()
                baseline_eval_results.append(eval_res)
                f_out.write(json.dumps(eval_res, ensure_ascii=False) + "\n")
                f_out.flush()
                if done_cnt % 5 == 0 or done_cnt == len(cases):
                    _logger.info("Baseline progress: %d/%d (Last Case %s: pass=%s, cov=%.2f)",
                                 done_cnt, len(cases), eval_res["case_id"], eval_res["passed"], eval_res["obligation_coverage"])

    # Sort deterministically
    baseline_eval_results.sort(key=lambda r: r["case_id"])
    agg_baseline = evaluator.aggregate_results(baseline_eval_results)

    # -------------------------------------------------------------------------
    # 3. Condition B: One-Pass Patched Prompt (Parallel 3 workers)
    # -------------------------------------------------------------------------
    _logger.info("--- Step 3: Running Condition B (One-Pass Patched Prompt) ---")
    adapter_patched = BodyAdapter(system_prompt=PROMPT_PATCHED, temperature=0.0)
    patched_eval_results: list[dict[str, Any]] = []
    patched_jsonl = RESULTS_DIR / "one_pass_multiturn_patched.jsonl"

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_map = {
            executor.submit(_run_single_case, c, adapter_patched, PROMPT_PATCHED, evaluator): c
            for c in cases
        }
        done_cnt = 0
        with open(patched_jsonl, "w", encoding="utf-8") as f_out:
            for fut in as_completed(future_map):
                done_cnt += 1
                eval_res = fut.result()
                patched_eval_results.append(eval_res)
                f_out.write(json.dumps(eval_res, ensure_ascii=False) + "\n")
                f_out.flush()
                if done_cnt % 5 == 0 or done_cnt == len(cases):
                    _logger.info("Patched progress: %d/%d (Last Case %s: pass=%s, cov=%.2f)",
                                 done_cnt, len(cases), eval_res["case_id"], eval_res["passed"], eval_res["obligation_coverage"])

    # Sort deterministically
    patched_eval_results.sort(key=lambda r: r["case_id"])
    agg_patched = evaluator.aggregate_results(patched_eval_results)

    # -------------------------------------------------------------------------
    # 4. Comparative Summary
    # -------------------------------------------------------------------------
    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": "DeepSeek-V4-Flash",
        "primary_provider": "Volces Ark (with AMD Radeon fallback)",
        "total_cases": len(cases),
        "pure_conversational_baseline": {
            "avg_latency_ms": avg_pure_latency,
            "avg_total_tokens": avg_pure_tokens,
            "avg_completion_tokens": avg_pure_comp_tokens,
        },
        "condition_a_baseline": agg_baseline,
        "condition_b_patched": agg_patched,
        "delta": {
            "case_pass_rate": agg_patched["case_pass_rate"] - agg_baseline["case_pass_rate"],
            "obligation_coverage_macro": agg_patched["obligation_coverage_macro"] - agg_baseline["obligation_coverage_macro"],
            "closure_context_integrity_rate": agg_patched["closure_context_integrity_rate"] - agg_baseline["closure_context_integrity_rate"],
            "e19_divergence_delta": agg_patched["e19_divergence_count"] - agg_baseline["e19_divergence_count"],
        },
    }

    summary_file = RESULTS_DIR / "summary_one_pass.json"
    summary_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    _logger.info("Experiment completed. Summary written to %s", summary_file)

    # Print comparative table to console
    print("\n" + "=" * 80)
    print("           ONE-PASS MULTI-TURN EXPERIMENT SUMMARY REPORT")
    print("=" * 80)
    print(f"{'Metric':<35} | {'Baseline One-Pass':<18} | {'Patched One-Pass':<18} | {'Delta':<10}")
    print("-" * 80)
    print(f"{'Case Pass Rate':<35} | {agg_baseline['case_pass_rate']*100:>17.2f}% | {agg_patched['case_pass_rate']*100:>17.2f}% | {(agg_patched['case_pass_rate']-agg_baseline['case_pass_rate'])*100:>+9.2f}%")
    print(f"{'Obligation Coverage (Macro)':<35} | {agg_baseline['obligation_coverage_macro']*100:>17.2f}% | {agg_patched['obligation_coverage_macro']*100:>17.2f}% | {(agg_patched['obligation_coverage_macro']-agg_baseline['obligation_coverage_macro'])*100:>+9.2f}%")
    print(f"{'Obligation Coverage (Micro)':<35} | {agg_baseline['obligation_coverage_micro']*100:>17.2f}% | {agg_patched['obligation_coverage_micro']*100:>17.2f}% | {(agg_patched['obligation_coverage_micro']-agg_baseline['obligation_coverage_micro'])*100:>+9.2f}%")
    print(f"{'Closure Context Integrity':<35} | {agg_baseline['closure_context_integrity_rate']*100:>17.2f}% | {agg_patched['closure_context_integrity_rate']*100:>17.2f}% | {(agg_patched['closure_context_integrity_rate']-agg_baseline['closure_context_integrity_rate'])*100:>+9.2f}%")
    print(f"{'E19 Divergence Rate':<35} | {agg_baseline['e19_divergence_rate']*100:>17.2f}% | {agg_patched['e19_divergence_rate']*100:>17.2f}% | {(agg_patched['e19_divergence_rate']-agg_baseline['e19_divergence_rate'])*100:>+9.2f}%")
    print(f"{'E19 Divergence Count':<35} | {agg_baseline['e19_divergence_count']:>18} | {agg_patched['e19_divergence_count']:>18} | {agg_patched['e19_divergence_count']-agg_baseline['e19_divergence_count']:>+10}")
    print(f"{'Avg Latency (ms)':<35} | {agg_baseline['avg_latency_ms']:>18.1f} | {agg_patched['avg_latency_ms']:>18.1f} | {agg_patched['avg_latency_ms']-agg_baseline['avg_latency_ms']:>+10.1f}")
    print(f"{'Avg Completion Tokens':<35} | {agg_baseline['avg_completion_tokens']:>18.1f} | {agg_patched['avg_completion_tokens']:>18.1f} | {agg_patched['avg_completion_tokens']-agg_baseline['avg_completion_tokens']:>+10.1f}")
    print("-" * 80)
    print("Omission Breakdown (O1-O10):")
    from research.experiments.semantic_compilation_body_v1.one_pass.omission_analysis import OMISSION_DEFINITIONS
    for code, desc in OMISSION_DEFINITIONS.items():
        base_cnt = agg_baseline["omission_distribution"].get(code, 0)
        patch_cnt = agg_patched["omission_distribution"].get(code, 0)
        print(f"  {code:<4} {desc[:28]:<30} | Base: {base_cnt:>3} | Patch: {patch_cnt:>3} | Delta: {patch_cnt-base_cnt:>+3}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_experiment()
