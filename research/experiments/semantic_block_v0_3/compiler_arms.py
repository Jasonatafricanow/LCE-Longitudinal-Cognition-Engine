"""Compiler arms implementation for SemanticBlock v0.3 Benchmark.

Implements:
- P0: Raw-text passthrough control
- P1: Canonical semantic account
- P2: Minimal structured SemanticBlock
- P3: Atomized / high-structure control
- P4: Legacy V1 compiler reference
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


@dataclass
class CompiledRepresentation:
    arm_id: str
    case_id: str
    cutoff_turn: int
    raw_data: dict[str, Any]
    representation_text: str
    structure_only_text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    cached: bool = False


# Prompt templates for P1, P2, P3

P1_SYSTEM_PROMPT = """你是一个高精度的语义编译器（SemanticBlock Compiler）。
你的任务是将给定的截断对话语料编译为唯一的“规范语义陈述（Canonical Semantic Account）”。

严格遵守以下语义保真度原则：
1. 时间局部性：仅依据当前切点之前可见的对话陈述事实。绝对不要猜测未来结果，不要将尚未发生的事情当成已完成。
2. 归属忠实性：如果用户是在转述他人（如朋友、同事、HR）的话，必须明确保留转述来源，绝不能将他人的话直接变成用户的个人判断。
3. 语力区分：严格区分陈述、询问（反问/确认）、提议建议、反事实愿望、假设条件、口误纠错。
4. 模态区分：严格区分确定（必然）、大概率、可能性、未知、否定。
5. 诚实保留UNKNOWN：对话中没有明确的信息保持未知，不要为了完整性胡乱推断或脑补。
6. 避免字面照抄：用规范、概括的自然语言忠实陈述语义核心，不要直接复制原始对话整句。

输出严格 JSON 格式：
{
  "canonical_semantic_account": "对当前截断点语义的完整忠实自然语言概括"
}"""

P2_SYSTEM_PROMPT = """你是一个最小结构化语义编译器（Minimal Structured SemanticBlock Compiler）。
你的任务是将截断对话编译为一个时间局部语义点，包含：规范语义陈述 + 区分检索所需的最小有界结构。

严格遵守以下原则：
1. 语义忠实优先于结构完整。
2. 时间局部性：记录此时此刻的事实或状态，严禁预言未来结果。
3. 归属忠实：区分用户直接断言、转述他人观点、用户明确认同转述、用户明确拒绝转述。
4. 语力与状态：区分当前强要求/约束、计划/意图、愿望/偏好、已完成、纯假设、纠正/撤回。
5. 诚实UNKNOWN：将真正未知的维度精确定位在 localized_unknowns 中，不泛化也不脑补。

输出严格 JSON 格式：
{
  "canonical_semantic_account": "对当前截断点语义的完整忠实自然语言概括",
  "source_attribution": {
    "speaker": "user",
    "reported_source": null 或 "朋友 / 老王 / HR 等",
    "user_endorsement": "direct | endorsed | skeptical_rejected | uncommitted_unknown"
  },
  "communicative_mode": "assertion | question | tentative_suggestion | correction_retraction | hypothetical_counterfactual | command_obligation",
  "epistemic_commitment": "certain | probable | possible | explicitly_unknown | negated",
  "action_or_state": {
    "status": "current_requirement_obligation | intention_plan | desire_preference | completed_past | hypothetical | cancelled_retracted | state_observation",
    "summary": "简短动作或状态描述"
  },
  "localized_unknowns": ["真正未知的具体事项1", "真正未知的具体事项2"]
}"""

P3_SYSTEM_PROMPT = """你是一个细粒度原子命题语义编译器（Atomized / High-Structure SemanticBlock Compiler）。
你的任务是将截断对话分解为离散的命题框架（propositions）、角色元组和语力行为。
注意：不要输出连贯的长文本叙述，完全依赖结构化命题与类型槽位表示。

输出严格 JSON 格式：
{
  "propositions": [
    {
      "prop_id": "p1",
      "predicate": "谓词核心词",
      "agent": "主语/施事",
      "theme_or_target": "受事/目标/内容",
      "temporal_anchor": "时间锚点（如明天、下个月、昨天、当前）",
      "modality": "certain | probable | possible | unknown",
      "polarity": "positive | negative",
      "truth_status": "asserted | reported | hypothetical | questioned | unknown",
      "attribution_source": "user | friend | lao_wang | hr | other"
    }
  ],
  "speech_act": {
    "type": "assert | ask | suggest | correct | counterfactual_wish | complain",
    "speaker": "user",
    "target": "dialogue_partner | self | world"
  },
  "localized_unknowns": ["未确定事项1"]
}"""


def format_dialogue(turns: list[dict[str, str]]) -> str:
    return " | ".join(f"{t['speaker']}: {t['text']}" for t in turns)


class CompilerArms:
    def __init__(self, llm_client: BenchmarkLLMClient) -> None:
        self.client = llm_client

    def compile_p0(self, case_id: str, dialogue: list[dict[str, str]], cutoff_turn: int) -> CompiledRepresentation:
        visible = dialogue[:cutoff_turn]
        raw_text = format_dialogue(visible)
        data = {
            "arm": "P0",
            "case_id": case_id,
            "cutoff_turn": cutoff_turn,
            "raw_text": raw_text,
        }
        return CompiledRepresentation(
            arm_id="P0",
            case_id=case_id,
            cutoff_turn=cutoff_turn,
            raw_data=data,
            representation_text=raw_text,
            structure_only_text=raw_text,
        )

    def compile_p1(self, case_id: str, dialogue: list[dict[str, str]], cutoff_turn: int) -> CompiledRepresentation:
        visible = dialogue[:cutoff_turn]
        dialogue_text = format_dialogue(visible)
        prompt = f"对话输入（截止第{cutoff_turn}轮）：\n{dialogue_text}\n\n请编译生成规范语义陈述（JSON格式）。"

        res = self.client.generate_json(prompt, system_instruction=P1_SYSTEM_PROMPT)
        content = res.content
        if isinstance(content, dict):
            account = content.get("canonical_semantic_account", "")
        elif isinstance(content, list) and content and isinstance(content[0], dict):
            account = content[0].get("canonical_semantic_account", "")
        else:
            account = str(content)

        return CompiledRepresentation(
            arm_id="P1",
            case_id=case_id,
            cutoff_turn=cutoff_turn,
            raw_data=content if isinstance(content, dict) else {"canonical_semantic_account": account},
            representation_text=account,
            structure_only_text=account,
            prompt_tokens=res.prompt_tokens,
            completion_tokens=res.completion_tokens,
            latency_ms=res.latency_ms,
            cached=res.cached,
        )

    def compile_p2(self, case_id: str, dialogue: list[dict[str, str]], cutoff_turn: int) -> CompiledRepresentation:
        visible = dialogue[:cutoff_turn]
        dialogue_text = format_dialogue(visible)
        prompt = f"对话输入（截止第{cutoff_turn}轮）：\n{dialogue_text}\n\n请编译生成最小结构化SemanticBlock（JSON格式）。"

        res = self.client.generate_json(prompt, system_instruction=P2_SYSTEM_PROMPT)
        content = res.content
        if isinstance(content, list) and content and isinstance(content[0], dict):
            content = content[0]
        elif not isinstance(content, dict):
            content = {"canonical_semantic_account": str(content)}

        account = content.get("canonical_semantic_account", "")
        src = content.get("source_attribution", {})
        comm = content.get("communicative_mode", "")
        epist = content.get("epistemic_commitment", "")
        action = content.get("action_or_state", {})
        unknowns = content.get("localized_unknowns", [])

        # Full P2 representation combines canonical account + bounded structured projection
        rep_text = (
            f"{account}\n"
            f"[来源归属: {json.dumps(src, ensure_ascii=False)}] "
            f"[语力模式: {comm}] "
            f"[认知强度: {epist}] "
            f"[动作状态: {json.dumps(action, ensure_ascii=False)}] "
            f"[未知维度: {json.dumps(unknowns, ensure_ascii=False)}]"
        )

        # Structure-only ablation representation (removes the natural-language canonical account)
        struct_only = (
            f"[来源归属: {json.dumps(src, ensure_ascii=False)}] "
            f"[语力模式: {comm}] "
            f"[认知强度: {epist}] "
            f"[动作状态: {json.dumps(action, ensure_ascii=False)}] "
            f"[未知维度: {json.dumps(unknowns, ensure_ascii=False)}]"
        )

        return CompiledRepresentation(
            arm_id="P2",
            case_id=case_id,
            cutoff_turn=cutoff_turn,
            raw_data=content,
            representation_text=rep_text,
            structure_only_text=struct_only,
            prompt_tokens=res.prompt_tokens,
            completion_tokens=res.completion_tokens,
            latency_ms=res.latency_ms,
            cached=res.cached,
        )

    def compile_p3(self, case_id: str, dialogue: list[dict[str, str]], cutoff_turn: int) -> CompiledRepresentation:
        visible = dialogue[:cutoff_turn]
        dialogue_text = format_dialogue(visible)
        prompt = f"对话输入（截止第{cutoff_turn}轮）：\n{dialogue_text}\n\n请编译生成细粒度原子命题框架（JSON格式）。"

        res = self.client.generate_json(prompt, system_instruction=P3_SYSTEM_PROMPT)
        content = res.content
        if isinstance(content, list):
            props = content
            act = {}
            unknowns = []
            content = {"propositions": props, "speech_act": act, "localized_unknowns": unknowns}
        elif isinstance(content, dict):
            props = content.get("propositions", [])
            act = content.get("speech_act", {})
            unknowns = content.get("localized_unknowns", [])
        else:
            props = []
            act = {}
            unknowns = []
            content = {"propositions": [], "speech_act": {}, "localized_unknowns": []}

        prop_strs = []
        for p in props:
            if isinstance(p, dict):
                p_str = (
                    f"命题({p.get('prop_id', '')}): [{p.get('attribution_source', '')}] "
                    f"主语={p.get('agent', '')}, 谓词={p.get('predicate', '')}, 受事={p.get('theme_or_target', '')}, "
                    f"时间={p.get('temporal_anchor', '')}, 模态={p.get('modality', '')}, 极性={p.get('polarity', '')}, 状态={p.get('truth_status', '')}"
                )
                prop_strs.append(p_str)
            else:
                prop_strs.append(str(p))

        rep_text = (
            f"命题集合:\n" + "\n".join(prop_strs) + "\n"
            f"言语行为: {json.dumps(act, ensure_ascii=False)}\n"
            f"未知事项: {json.dumps(unknowns, ensure_ascii=False)}"
        )

        return CompiledRepresentation(
            arm_id="P3",
            case_id=case_id,
            cutoff_turn=cutoff_turn,
            raw_data=content,
            representation_text=rep_text,
            structure_only_text=rep_text,
            prompt_tokens=res.prompt_tokens,
            completion_tokens=res.completion_tokens,
            latency_ms=res.latency_ms,
            cached=res.cached,
        )

    def compile_p4(self, case_id: str, dialogue: list[dict[str, str]], cutoff_turn: int) -> CompiledRepresentation:
        """Legacy V1 compiler reference. Passes through raw dialogue without semantic slots (all UNKNOWN)."""
        visible = dialogue[:cutoff_turn]
        raw_text = format_dialogue(visible)
        legacy_data = {
            "arm": "P4_V1",
            "case_id": case_id,
            "cutoff_turn": cutoff_turn,
            "canonical_content": raw_text,
            "predicate": "UNKNOWN",
            "kind": "UNKNOWN",
            "participants": {"subject": "UNKNOWN"},
            "holder": "UNKNOWN",
            "utterer": "UNKNOWN",
            "attribution_mode": "UNKNOWN",
            "polarity": "UNKNOWN",
            "modality": "UNKNOWN",
            "epistemic_hedge": "UNKNOWN",
            "valid_time": "UNKNOWN",
            "entity_status": "UNKNOWN",
            "uncertainty": "UNKNOWN",
        }
        rep_text = (
            f"V1_Block:\n"
            f"content: {raw_text}\n"
            f"attribution_mode: UNKNOWN\n"
            f"modality: UNKNOWN\n"
            f"uncertainty: UNKNOWN"
        )
        return CompiledRepresentation(
            arm_id="P4",
            case_id=case_id,
            cutoff_turn=cutoff_turn,
            raw_data=legacy_data,
            representation_text=rep_text,
            structure_only_text=rep_text,
        )
