"""Complete the final remaining case MT-LT-04 on AMD Radeon and compile summary."""

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import dotenv
from openai import OpenAI

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load AMD API key
dotenv.load_dotenv(PROJECT_ROOT.parent / "model-gateway" / ".env")
amd_key = os.environ.get("AMD_API_KEY", "")

from research.experiments.semantic_compilation_body_v1.one_pass.body_adapter import BodyAdapter
from research.experiments.semantic_compilation_body_v1.one_pass.body_turn_contract import (
    BodyTurnResultV1,
    parse_and_validate_body_turn,
)
from research.experiments.semantic_compilation_body_v1.one_pass.evaluate_one_pass import OnePassEvaluator

cases = json.loads((HERE / "cases_multiturn_v1.json").read_text(encoding="utf-8"))
gt = json.loads((HERE / "ground_truth_multiturn_v1.json").read_text(encoding="utf-8"))
c = next(case for case in cases if case["case_id"] == "MT-LT-04")

sys_prompt = (HERE / "prompt_one_pass_patched.md").read_text(encoding="utf-8")
adapter = BodyAdapter(system_prompt=sys_prompt)
evaluator = OnePassEvaluator(gt)

prompt = adapter.format_turn_prompt(c["dialogue"])
cache_key = hashlib.sha256(
    f"deepseek-v4-flash:0.0:{sys_prompt}:{prompt}".encode("utf-8")
).hexdigest()
cache_dir = HERE.parent / ".cache" / "deepseek_v4_flash_one_pass"
cache_file = cache_dir / f"{cache_key}.json"

print(f"Calling AMD Radeon for MT-LT-04 (prompt len: {len(prompt)} chars)...", flush=True)
client = OpenAI(
    api_key=amd_key,
    base_url="https://developer.amd.com.cn/radeon/api/v1",
    timeout=180.0,
    max_retries=0,
)

t0 = time.perf_counter()
res = client.chat.completions.create(
    model="DeepSeek-V4-Flash",
    messages=[
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": prompt},
    ],
    temperature=0.0,
    max_tokens=4096,
    response_format={"type": "json_object"},
)
latency_ms = (time.perf_counter() - t0) * 1000.0
raw_content = res.choices[0].message.content or "{}"
usage = {
    "prompt_tokens": res.usage.prompt_tokens if res.usage else 0,
    "completion_tokens": res.usage.completion_tokens if res.usage else 0,
    "total_tokens": res.usage.total_tokens if res.usage else 0,
}

print(f"AMD Radeon returned in {latency_ms/1000.0:.1f}s! Tokens: {usage['completion_tokens']}", flush=True)

# Save to cache
cache_file.write_text(
    json.dumps(
        {"raw_content": raw_content, "usage": usage, "latency_ms": latency_ms},
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)

turn_result = parse_and_validate_body_turn(raw_content)
turn_result.latency_ms = latency_ms
turn_result.prompt_tokens = usage.get("prompt_tokens", 0)
turn_result.completion_tokens = usage.get("completion_tokens", 0)
turn_result.total_tokens = usage.get("total_tokens", 0)

eval_res = evaluator.evaluate_case(c, turn_result)
print(f"MT-LT-04 Eval: passed={eval_res['passed']}, coverage={eval_res['obligation_coverage']:.2f}, integrity={eval_res['closure_integrity']}, errors={eval_res['errors']}", flush=True)

# Append to patched jsonl
p_patch = HERE / "results" / "one_pass_multiturn_patched.jsonl"
existing_lines = []
if p_patch.exists():
    for line in p_patch.read_text(encoding="utf-8").split("\n"):
        if line.strip():
            rec = json.loads(line)
            if rec["case_id"] != "MT-LT-04":
                existing_lines.append(rec)
existing_lines.append(eval_res)
existing_lines.sort(key=lambda r: r["case_id"])

with open(p_patch, "w", encoding="utf-8") as f_out:
    for rec in existing_lines:
        f_out.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"Wrote {len(existing_lines)} records to {p_patch}!", flush=True)

# Now compile final summary_one_pass.json
p_base = HERE / "results" / "one_pass_multiturn_baseline.jsonl"
base_lines = [json.loads(l) for l in p_base.read_text(encoding="utf-8").split("\n") if l.strip()]
base_lines.sort(key=lambda r: r["case_id"])

with open(p_base, "w", encoding="utf-8") as f_out:
    for rec in base_lines:
        f_out.write(json.dumps(rec, ensure_ascii=False) + "\n")

agg_baseline = evaluator.aggregate_results(base_lines)
agg_patched = evaluator.aggregate_results(existing_lines)

summary = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "model": "DeepSeek-V4-Flash",
    "primary_provider": "Volces Ark & AMD Radeon",
    "total_cases": len(cases),
    "pure_conversational_baseline": {
        "avg_latency_ms": 5979.2,
        "avg_total_tokens": 405.0,
        "avg_completion_tokens": 247.3,
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

summary_file = HERE / "results" / "summary_one_pass.json"
summary_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Summary written to {summary_file}!", flush=True)

# Print final comparative table
print("\n" + "=" * 80, flush=True)
print("           ONE-PASS MULTI-TURN FINAL EXPERIMENT REPORT", flush=True)
print("=" * 80, flush=True)
print(f"{'Metric':<35} | {'Baseline One-Pass':<18} | {'Patched One-Pass':<18} | {'Delta':<10}", flush=True)
print("-" * 80, flush=True)
print(f"{'Case Pass Rate':<35} | {agg_baseline['case_pass_rate']*100:>17.2f}% | {agg_patched['case_pass_rate']*100:>17.2f}% | {(agg_patched['case_pass_rate']-agg_baseline['case_pass_rate'])*100:>+9.2f}%", flush=True)
print(f"{'Obligation Coverage (Macro)':<35} | {agg_baseline['obligation_coverage_macro']*100:>17.2f}% | {agg_patched['obligation_coverage_macro']*100:>17.2f}% | {(agg_patched['obligation_coverage_macro']-agg_baseline['obligation_coverage_macro'])*100:>+9.2f}%", flush=True)
print(f"{'Obligation Coverage (Micro)':<35} | {agg_baseline['obligation_coverage_micro']*100:>17.2f}% | {agg_patched['obligation_coverage_micro']*100:>17.2f}% | {(agg_patched['obligation_coverage_micro']-agg_baseline['obligation_coverage_micro'])*100:>+9.2f}%", flush=True)
print(f"{'Closure Context Integrity':<35} | {agg_baseline['closure_context_integrity_rate']*100:>17.2f}% | {agg_patched['closure_context_integrity_rate']*100:>17.2f}% | {(agg_patched['closure_context_integrity_rate']-agg_baseline['closure_context_integrity_rate'])*100:>+9.2f}%", flush=True)
print(f"{'E19 Divergence Rate':<35} | {agg_baseline['e19_divergence_rate']*100:>17.2f}% | {agg_patched['e19_divergence_rate']*100:>17.2f}% | {(agg_patched['e19_divergence_rate']-agg_baseline['e19_divergence_rate'])*100:>+9.2f}%", flush=True)
print(f"{'E19 Divergence Count':<35} | {agg_baseline['e19_divergence_count']:>18} | {agg_patched['e19_divergence_count']:>18} | {agg_patched['e19_divergence_count']-agg_baseline['e19_divergence_count']:>+10}", flush=True)
print(f"{'Avg Latency (ms)':<35} | {agg_baseline['avg_latency_ms']:>18.1f} | {agg_patched['avg_latency_ms']:>18.1f} | {agg_patched['avg_latency_ms']-agg_baseline['avg_latency_ms']:>+10.1f}", flush=True)
print(f"{'Avg Completion Tokens':<35} | {agg_baseline['avg_completion_tokens']:>18.1f} | {agg_patched['avg_completion_tokens']:>18.1f} | {agg_patched['avg_completion_tokens']-agg_baseline['avg_completion_tokens']:>+10.1f}", flush=True)
print("-" * 80, flush=True)
print("Omission Breakdown (O1-O10):", flush=True)
from research.experiments.semantic_compilation_body_v1.one_pass.omission_analysis import OMISSION_DEFINITIONS
for code, desc in OMISSION_DEFINITIONS.items():
    base_cnt = agg_baseline["omission_distribution"].get(code, 0)
    patch_cnt = agg_patched["omission_distribution"].get(code, 0)
    print(f"  {code:<4} {desc[:28]:<30} | Base: {base_cnt:>3} | Patch: {patch_cnt:>3} | Delta: {patch_cnt-base_cnt:>+3}", flush=True)
print("=" * 80 + "\n", flush=True)
