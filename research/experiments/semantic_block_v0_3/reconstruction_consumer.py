"""Blind reconstruction consumer and evaluator for SemanticBlock v0.3.

Implements Stage A Blind Reconstruction:
1. Consumer receives ONLY the compiled SemanticBlock representation.
   Original dialogue, family labels, gold records, and retrieval targets are strictly hidden.
2. Independent consumer reconstructs time-local meaning.
3. Blind evaluator scores the reconstruction against adjudicated gold constraints:
   - Must-Preserve Recall
   - Forbidden-Claim Rate (Must-Not-Claim)
   - UNKNOWN Localization Accuracy
   - Attribution Fidelity
   - Temporal Locality
   - Full-case Semantic Equivalence
   - Severe contamination tracking
   - Failure taxonomy attribution
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.experiments.semantic_block_v0_3.llm_client import BenchmarkLLMClient

CONSUMER_SYSTEM_PROMPT = """你是一个独立的下游语义消费者（Semantic Consumer）。
你收到的输入是一个语义表示（SemanticBlock Representation）。你无法看到原始对话。
请基于该表示，客观、准确地重构出截断点当时的真实含义：

重构应准确体现：
1. 此时此刻确切知道的信息是什么；
2. 观点的归属来源是谁（用户本人主张、转述他人观点、用户认同转述、还是用户拒绝转述）；
3. 语力与情态（是陈述、问题、建议、假设条件、反事实愿望、还是口误纠正）；
4. 确定性级别（确定事实、大概率、可能、未知、否定）；
5. 动作或状态（当前约束要求、计划安排、愿望、已完成状态、还是纯假设）；
6. 哪些事项在当前是未知或未决的。

输出严格 JSON 格式：
{
  "reconstructed_account": "简洁、客观的自然语言重构陈述",
  "attribution_summary": "观点所有者及归属关系",
  "commitment_modality": "确定性与语态说明",
  "action_or_state_status": "动作状态或约束类型",
  "unresolved_unknowns": ["未知具体事项列表"]
}"""

SCORER_SYSTEM_PROMPT = """你是一个严格的语义评测裁判（Semantic Adjudicator & Scorer）。
你的任务是对照权威黄金标准（Adjudicated Gold），对下游消费者从语义表示中重构出的内容进行多维度客观评分。

权威黄金标准包含：
- gold_semantic_account: 规范基准语义陈述
- must_preserve: 必须完整保留的核心语义点列表
- must_not_claim: 绝对禁止做出的过度断言或扭曲陈述列表
- legitimate_unknowns: 当前截断点必须保持未知的合理未知项列表

评分维度要求：
1. must_preserve_results: 对 must_preserve 中每个要点，判断重构内容是否忠实表达了该要点（recalled: true/false）。
2. must_not_claim_results: 对 must_not_claim 中每个禁止项，判断重构内容是否错误地主张了该禁止项（claimed: true/false）。claimed 为 true 即为违规过度断言。
3. unknown_localization_accuracy: 未知定位准确度（0.0到1.0）。若将已知当未知、或将未知脑补为已知、或泛化抹去已知，则扣分；准确保留未知维度给 1.0。
4. attribution_fidelity: 归属保真度（0.0到1.0）。若将他人观点变成用户观点、或弄错发言主体给 0.0。
5. temporal_locality: 时间局部性保真度（0.0到1.0）。若将未来未发生结果提前断言给 0.0。
6. full_case_equivalent: 整体功能等价性（true/false）。重构语义是否在功能上等价于权威基准。
7. severe_contaminations: 跟踪7类严重污染错误（true/false）：
   - reported_to_belief: 转述他人观点 -> 用户自身信念
   - question_to_assertion: 询问/确认 -> 断言事实
   - counterfactual_to_fact: 假设/反事实 -> 真实发生事实
   - possibility_to_certainty: 可能性 -> 确定性事实
   - obligation_to_completed: 约束/愿望/计划 -> 已完成事件
   - future_to_past: 未来未发生结果 -> 提前注入当前切点
   - invented_certainty: 无证据脑补确定性消除UNKNOWN
8. failure_labels: 若存在缺陷，从以下标准分类法中选择最贴切标签（可多选，无则空列表 []）：
   [CONTEXT_INSUFFICIENT, SEMANTIC_MISREAD, ATTRIBUTION_DRIFT, OVERCLAIM, UNDERCLAIM, UNKNOWN_MISPLACED, TEMPORAL_OVERREACH, NON_RECONSTRUCTABLE, TRIVIAL_NON_STRUCTURE, GRANULARITY_COLLAPSE, SURFACE_SENSITIVITY, OVER_ATOMIZATION]

输出严格 JSON 格式：
{
  "must_preserve_results": [{"item": "...", "recalled": true}],
  "must_not_claim_results": [{"item": "...", "claimed": false}],
  "unknown_localization_accuracy": 1.0,
  "attribution_fidelity": 1.0,
  "temporal_locality": 1.0,
  "full_case_equivalent": true,
  "severe_contaminations": {
    "reported_to_belief": false,
    "question_to_assertion": false,
    "counterfactual_to_fact": false,
    "possibility_to_certainty": false,
    "obligation_to_completed": false,
    "future_to_past": false,
    "invented_certainty": false
  },
  "failure_labels": [],
  "explanation": "简短判定理由"
}"""


@dataclass
class ReconstructionResult:
    case_id: str
    arm_id: str
    reconstruction_content: dict[str, Any]
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    cached: bool


@dataclass
class EvaluationResult:
    case_id: str
    arm_id: str
    must_preserve_recall: float
    forbidden_claim_rate: float
    unknown_localization_accuracy: float
    attribution_fidelity: float
    temporal_locality: float
    full_case_equivalent: bool
    severe_contaminations: dict[str, bool]
    has_severe_contamination: bool
    failure_labels: list[str]
    details: dict[str, Any]
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    cached: bool


class BlindReconstructor:
    def __init__(self, llm_client: BenchmarkLLMClient) -> None:
        self.client = llm_client

    def reconstruct(self, case_id: str, arm_id: str, representation_text: str) -> ReconstructionResult:
        prompt = (
            f"语义表示输入（SemanticBlock Representation）：\n"
            f"```text\n{representation_text}\n```\n\n"
            f"请根据上述表示重构其截断点含义（严格输出JSON格式）。"
        )
        res = self.client.generate_json(prompt, system_instruction=CONSUMER_SYSTEM_PROMPT)
        content = res.content
        if isinstance(content, list) and content and isinstance(content[0], dict):
            content = content[0]
        elif not isinstance(content, dict):
            content = {"reconstructed_account": str(content)}

        return ReconstructionResult(
            case_id=case_id,
            arm_id=arm_id,
            reconstruction_content=content,
            prompt_tokens=res.prompt_tokens,
            completion_tokens=res.completion_tokens,
            latency_ms=res.latency_ms,
            cached=res.cached,
        )

    def evaluate(
        self,
        case_id: str,
        arm_id: str,
        reconstruction: dict[str, Any],
        gold_record: dict[str, Any],
    ) -> EvaluationResult:
        prompt = (
            f"下游重构输出：\n{json.dumps(reconstruction, ensure_ascii=False, indent=2)}\n\n"
            f"权威黄金标准（Adjudicated Gold）：\n"
            f"gold_semantic_account: {gold_record.get('gold_semantic_account') or gold_record.get('gold_prefix_semantic_account')}\n"
            f"must_preserve: {json.dumps(gold_record.get('must_preserve', []), ensure_ascii=False)}\n"
            f"must_not_claim: {json.dumps(gold_record.get('must_not_claim', []), ensure_ascii=False)}\n"
            f"legitimate_unknowns: {json.dumps(gold_record.get('legitimate_unknowns', []), ensure_ascii=False)}\n\n"
            f"请严格进行对照评测并输出评测 JSON。"
        )
        res = self.client.generate_json(prompt, system_instruction=SCORER_SYSTEM_PROMPT)
        eval_data = res.content
        if isinstance(eval_data, list) and eval_data and isinstance(eval_data[0], dict):
            eval_data = eval_data[0]
        elif not isinstance(eval_data, dict):
            eval_data = {}

        mp_list = eval_data.get("must_preserve_results", [])
        recalled_cnt = sum(1 for m in mp_list if m.get("recalled", False))
        mp_recall = recalled_cnt / len(mp_list) if mp_list else 1.0

        mnc_list = eval_data.get("must_not_claim_results", [])
        claimed_cnt = sum(1 for m in mnc_list if m.get("claimed", False))
        forbidden_rate = claimed_cnt / len(mnc_list) if mnc_list else 0.0

        severe = eval_data.get("severe_contaminations", {})
        has_severe = any(bool(v) for v in severe.values())

        return EvaluationResult(
            case_id=case_id,
            arm_id=arm_id,
            must_preserve_recall=mp_recall,
            forbidden_claim_rate=forbidden_rate,
            unknown_localization_accuracy=float(eval_data.get("unknown_localization_accuracy", 1.0)),
            attribution_fidelity=float(eval_data.get("attribution_fidelity", 1.0)),
            temporal_locality=float(eval_data.get("temporal_locality", 1.0)),
            full_case_equivalent=bool(eval_data.get("full_case_equivalent", False)),
            severe_contaminations=severe,
            has_severe_contamination=has_severe,
            failure_labels=list(eval_data.get("failure_labels", [])),
            details=eval_data,
            prompt_tokens=res.prompt_tokens,
            completion_tokens=res.completion_tokens,
            latency_ms=res.latency_ms,
            cached=res.cached,
        )
