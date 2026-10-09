"""Build 75 comprehensive test cases and ground truth definitions.

Covers all 25 difficult linguistic and cognitive phenomena (§9).
Synthesizes:
- 12 verified adversarial closure cases (§3.2, V2)
- 48 adjudicated linguistic family cases (semantic_block_v0_3)
- (15 private production conversations removed from the public repository)
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES_DIR = HERE / "cases"
CASES_DIR.mkdir(parents=True, exist_ok=True)

# 1. Load V2 closure cases
v2_file = HERE.parent / "semantic_compilation_v1" / "closure_cases.json"
v2_data = json.loads(v2_file.read_text(encoding="utf-8"))

all_cases = []
all_ground_truth = {}

phenomenon_mapping = {
    "simple_assertion": ["simple_assertion"],
    "mixed_transient_and_constraint": ["transient_plus_durable", "multiple_independent_topics"],
    "plan_completed_ongoing": ["plan_completed_ongoing", "state_evolution"],
    "uncertain_diagnosis": ["uncertainty", "self_belief"],
    "conditional_invariant": ["conditional_statement", "durable_rule"],
    "cross_turn_correction": ["cross_turn_correction", "supersedes"],
    "unresolved_reference": ["unresolved_reference", "must_defer"],
    "resolved_reference_with_context": ["resolved_pronoun", "context_dependency"],
    "state_change_over_time": ["state_change_over_time", "longitudinal_evolution"],
    "nested_stance": ["nested_stance", "evidence_limitation", "negation"],
    "question_not_fact": ["question_not_fact"],
    "coding_result_plus_durable_rule": ["transient_plus_durable", "durable_rule"]
}

v2_ground_truth_specs = {
    "simple_assertion": {
        "required_meanings": ["办公室 Linux 机器承载服务器运行"],
        "forbidden_inferences": [],
        "must_defer": False,
        "expected_speech_act": "assertion",
        "expected_epistemic": "asserted",
    },
    "mixed_transient_and_constraint": {
        "required_meanings": ["测试已全部通过", "报告不用太长，只看结论和异常"],
        "forbidden_inferences": [],
        "must_defer": False,
    },
    "plan_completed_ongoing": {
        "required_meanings": ["原计划本月交首付", "昨天已经交了首付", "正在等待贷款审批"],
        "forbidden_inferences": ["首付款尚未支付", "贷款已经完成审批"],
        "must_defer": False,
    },
    "uncertain_diagnosis": {
        "required_meanings": ["怀疑热启动机制可能有问题，尚未确认"],
        "forbidden_inferences": ["热启动机制已被确认存在故障"],
        "must_defer": False,
        "expected_epistemic": "uncertain",
    },
    "conditional_invariant": {
        "required_meanings": ["如果 BGE 换版本则必须重建向量", "SemanticBlock 身份不应该改变"],
        "forbidden_inferences": ["无条件必须重建向量", "SemanticBlock 身份随版本改变"],
        "must_defer": False,
        "expected_epistemic": "hypothetical",
    },
    "cross_turn_correction": {
        "required_meanings": ["最初要求 top-k=100", "撤销 100 改为测试 20/30/50/70"],
        "forbidden_inferences": ["当前仍要求使用 top-k=100"],
        "must_defer": False,
        "expected_speech_act": "directive",
    },
    "unresolved_reference": {
        "required_meanings": [],
        "forbidden_inferences": ["擅自猜测并确定具体是哪个方案"],
        "must_defer": True,
    },
    "resolved_reference_with_context": {
        "required_meanings": ["用户选择方案 B（原生库做 Raw authority）"],
        "forbidden_inferences": ["用户选择了方案 A（双库同步）"],
        "must_defer": False,
        "expected_speech_act": "directive",
    },
    "state_change_over_time": {
        "required_meanings": ["该问题上周已经修好", "同一问题当前再次出现故障"],
        "forbidden_inferences": ["该问题一直处于完好状态"],
        "must_defer": False,
    },
    "nested_stance": {
        "required_meanings": ["否认当前结果足以证明算法正确", "仅说明测试夹具能跑"],
        "forbidden_inferences": ["用户断定算法存在错误"],
        "must_defer": False,
    },
    "question_not_fact": {
        "required_meanings": ["询问 LCE 为何不能即时执行"],
        "forbidden_inferences": ["断言 LCE 永远无法即时执行"],
        "must_defer": False,
        "expected_speech_act": "question",
    },
    "coding_result_plus_durable_rule": {
        "required_meanings": ["pytest 3918 个测试通过", "今后不要为了 coverage 写低价值重复测试"],
        "forbidden_inferences": ["测试未通过", "要求以后写更多测试以提高覆盖率"],
        "must_defer": False,
        "expected_speech_act": "directive",
    },
}

for case in v2_data["cases"]:
    cid = f"V2-{case['id']}"
    turns = [
        {"evidence_id": r["evidence_id"], "speaker": "user", "text": r["text"]}
        for r in case["raw"]
    ]
    all_cases.append({
        "case_id": cid,
        "source": "v2_adversarial",
        "phenomena": phenomenon_mapping.get(case["id"], []),
        "dialogue": turns,
        "context_turns": len(turns)
    })
    
    spec = v2_ground_truth_specs.get(case["id"], {})
    all_ground_truth[cid] = {
        "case_id": cid,
        "min_point_count": len(case["points"]),
        "max_point_count": len(case["points"]) + 2,
        "required_meanings": spec.get("required_meanings", [p["meaning"] for p in case["points"] if p.get("status") != "defer"]),
        "forbidden_inferences": spec.get("forbidden_inferences", []),
        "expected_closure_groups": case["expected_groups"],
        "expected_separate_pairs": case.get("separate_pairs", []),
        "expected_deferred_ids": case.get("expected_deferred", []),
        "must_defer": spec.get("must_defer", len(case.get("expected_deferred", [])) > 0),
        "expected_speech_act": spec.get("expected_speech_act"),
        "expected_epistemic": spec.get("expected_epistemic"),
        "gold_points": case["points"],
        "gold_dependencies": case["dependencies"]
    }

# 2. Add 48 cases from cases_v0_3
v0_3_file = HERE.parent / "semantic_block_v0_3" / "cases_v0_3.jsonl"
gold_v0_3_file = HERE.parent / "semantic_block_v0_3" / "gold_v0_3.jsonl"

gold_v0_3_map = {}
if gold_v0_3_file.exists():
    for line in gold_v0_3_file.read_text(encoding="utf-8").splitlines():
        if line.strip():
            g_item = json.loads(line)
            gold_v0_3_map[g_item["case_id"]] = g_item

if v0_3_file.exists():
    lines = [json.loads(line) for line in v0_3_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    for item in lines:
        cid = item["case_id"]
        turns = [
            {"evidence_id": f"E{idx+1:02d}", "speaker": d["speaker"], "text": d["text"]}
            for idx, d in enumerate(item["dialogue"])
        ]
        family = item["family"]
        variant = item["variant"]
        phenomena = [family, variant]
        
        g_item = gold_v0_3_map.get(cid, {})
        must_defer = ("genuine_ambiguity" in variant)
        
        # Derive typed expectations
        speech_act = None
        if "question" in variant:
            speech_act = "question"
        elif "directive" in variant or "requirement" in variant or "obligation" in variant:
            speech_act = "directive"

        polarity = None
        if "negative" in variant:
            polarity = "negative"

        epistemic = None
        if "uncertain" in variant or "possible" in variant or "probable" in variant or "self_belief" in variant:
            epistemic = "uncertain"
        elif "report" in variant:
            epistemic = "reported"
        elif "counterfactual" in variant:
            epistemic = "counterfactual"
        elif "conditional" in variant or "hypothetical" in variant or "suggestion" in variant:
            epistemic = "hypothetical"
        elif "intention" in variant:
            epistemic = "planned"
        elif "completed" in variant:
            epistemic = "asserted"

        all_cases.append({
            "case_id": cid,
            "source": "v0_3_adjudicated",
            "phenomena": phenomena,
            "dialogue": turns,
            "context_turns": len(turns)
        })
        
        all_ground_truth[cid] = {
            "case_id": cid,
            "min_point_count": 1,
            "max_point_count": len(turns) + 1,
            "required_meanings": [t["text"] for t in turns if t.get("speaker") == "user"] or [turns[-1]["text"]],
            "forbidden_inferences": g_item.get("must_not_claim", []),
            "must_defer": must_defer,
            "expected_speech_act": speech_act,
            "expected_polarity": polarity,
            "expected_epistemic": epistemic,
        }

# 3. (Removed) 15 real Hermes production conversations were private and are
#    not included in this repository; the experiment runs on the cases above.

# Write cases and ground truth
cases_path = CASES_DIR / "cases.json"
gt_path = CASES_DIR / "ground_truth.json"

cases_path.write_text(json.dumps({"total_cases": len(all_cases), "cases": all_cases}, indent=2, ensure_ascii=False), encoding="utf-8")
gt_path.write_text(json.dumps(all_ground_truth, indent=2, ensure_ascii=False), encoding="utf-8")

print(f"Generated {len(all_cases)} test cases and {len(all_ground_truth)} ground truth definitions.")
