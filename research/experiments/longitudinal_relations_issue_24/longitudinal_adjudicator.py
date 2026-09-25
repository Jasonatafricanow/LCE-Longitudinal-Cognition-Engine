"""Selective Longitudinal Adjudicator (L3) for Issue #24.

Evaluates bounded candidate pairs using Gemini 3.1 Flash-Lite with temperature 0.0 and caching.
Enforces the 6-way relation taxonomy, evidence contract, and critical falsification invariants:
- Time is strong authority (t1 < t2).
- Earlier SemanticBlock is immutable.
- World change != earlier cognition was wrong.
- UNKNOWN only closes with new evidence, not elapsed time.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from lce.cognition.longitudinal_relation import LongitudinalRelationType
from research.experiments.longitudinal_relations_issue_24.contracts import (
    AdjudicationOutput,
    CorpusBlockRecord,
)
from research.experiments.longitudinal_relations_issue_24.llm_client import get_llm_client

SYSTEM_PROMPT = """你是一个纵向认知结构裁决器（Longitudinal Relation Adjudicator）。
你的唯一职责是判定两个按时间先后顺序排列的语义块（SemanticBlock t1 和 t2，满足 t1 < t2）之间的一级纵向认知关系。

核心原则与禁忌（不可违背）：
1. 【时间强权威】：时间顺序 t1 < t2 已由底层系统严格保证，你绝不需要推断时间先后，也不得颠倒时序。
2. 【早期语义不可篡改】：t1 是 t1 时刻的局部真实（local truth）。后来的事实不能回写或否定早期客观事实。
3. 【客观状态变迁 != 认知纠错撤回】：
   - STATE_CHANGE（状态变迁）：t1 在当时完全真实（如会议原定周二），因后续世界发展/通知变更改到周三。t1 仍然是有效的历史事实。
   - CORRECTION_RETRACTION（纠错撤回）：t1 的陈述本身就是错误的（如“我说错了”、“看错日程了”，其实一直都是周四）。这属于说话人或前序认知的撤回纠错。
4. 【时间流逝绝不制造知识】：
   - 就算 t1 留有未决维度（UNKNOWN），仅仅经历时间流逝而没有新证据到来，系统认知必须保持 UNKNOWN（UNKNOWN_RELATION 或 PERSISTENCE_CONFIRMATION）。
   - 绝不允许“因为时间过了，所以默认已经完成或失败”。没有新证据，就没有新认知（No new evidence, no new cognition）。
5. 【纯时间邻近不等于有关系】：
   - 如果两个块仅仅是时间上接近，但描述的是无关事件、不同对象，必须判定为 UNRELATED。绝不得强行脑补关联。

你只能在以下六种关系中选择其一：
1. UNCERTAINTY_RESOLUTION: t1 中存在未决悬念、义务要求或潜在可能性，t2 提供了确凿事实结果彻底闭合了该悬念（无论是成功、失败还是外部取消）。此时 prior_unknown_resolved 必须为 true。
2. STATE_CHANGE: t1 描述的状态/计划在当时是真实的，但随后客观世界、决策或通知发生了现实变迁，进入新状态。
3. CORRECTION_RETRACTION: t2 指出 t1 的信息陈述有口误、笔误或认知错误，撤回并纠正前序陈述。
4. PERSISTENCE_CONFIRMATION: t1 处于未决或阻滞状态，t2 确认该未决状态在持续延续，仍未获得结果。
5. UNRELATED: 两者属于彼此独立的事务或对象，无直接纵向演化关系。
6. UNKNOWN_RELATION: 证据不足以支持确认上述任何关系，或时间流逝但无任何相关证据闭合前序未知。

输出必须严格为 JSON 格式：
{
  "relation_type": "UNCERTAINTY_RESOLUTION" | "STATE_CHANGE" | "CORRECTION_RETRACTION" | "PERSISTENCE_CONFIRMATION" | "UNRELATED" | "UNKNOWN_RELATION",
  "affected_dimension": "影响的具体语义维度，如 schedule_time, eventual_boarding, approval_outcome 等",
  "prior_unknown_resolved": true | false,
  "resolved_dimension": "若 prior_unknown_resolved 为 true 则填写具体闭合的维度名称，否则为 null",
  "outcome_or_current_state": "简要总结 t2 带来的新结果或当前状态",
  "evidence_spans": ["来自 t1 或 t2 的关键原文支撑片段"],
  "reason_competing_rejections": {
    "STATE_CHANGE": "若未选 STATE_CHANGE，说明为何排除它",
    "CORRECTION_RETRACTION": "若未选 CORRECTION_RETRACTION，说明为何排除它",
    "UNCERTAINTY_RESOLUTION": "若未选 UNCERTAINTY_RESOLUTION，说明为何排除它"
  },
  "confidence": 0.0 到 1.0 之间的置信度,
  "adjudication_trace": "简洁清晰的判定论证链条"
}
"""


class LongitudinalAdjudicator:
    def __init__(self) -> None:
        self.llm_client = get_llm_client()

    def adjudicate(
        self,
        pair_id: str,
        t1: CorpusBlockRecord,
        t2: CorpusBlockRecord,
    ) -> AdjudicationOutput:
        """Adjudicate candidate pair using LLM with deterministic caching."""
        prompt = f"""请对以下按时间先后发生的一组 SemanticBlock 判定一级纵向关系：

【前序语义块 t1 (Occurred: {t1.occurred_start.isoformat()})】:
- Block ID: {t1.block_id}
- Domain: {t1.domain}
- 核心内容: {t1.content}
- 动作/状态投影: {json.dumps(t1.projections.get('action_or_state', {}), ensure_ascii=False)}
- 本地已知/未知投影: {json.dumps(t1.projections.get('localized_unknowns', []), ensure_ascii=False)}
- 实体角色锚点: {json.dumps(t1.projections.get('entity_role_anchors', {}), ensure_ascii=False)}

【后续语义块 t2 (Occurred: {t2.occurred_start.isoformat()})】:
- Block ID: {t2.block_id}
- Domain: {t2.domain}
- 核心内容: {t2.content}
- 动作/状态投影: {json.dumps(t2.projections.get('action_or_state', {}), ensure_ascii=False)}
- 话语行为投影: {t2.projections.get('communicative_act', 'assertion')}
- 修订/撤回投影: {json.dumps(t2.projections.get('revision_retraction', {}), ensure_ascii=False)}
- 实体角色锚点: {json.dumps(t2.projections.get('entity_role_anchors', {}), ensure_ascii=False)}

请严格按 JSON 规范输出纵向认知关系裁决结果："""

        call_res = self.llm_client.generate_json(
            prompt=prompt,
            system_instruction=SYSTEM_PROMPT,
        )

        data = call_res.content

        # Parse relation type safely
        rel_str = str(data.get("relation_type", "UNKNOWN_RELATION")).strip().upper()
        try:
            rel_type = LongitudinalRelationType(rel_str)
        except ValueError:
            rel_type = LongitudinalRelationType.UNKNOWN_RELATION

        # Normalize prior_unknown_resolved
        prior_resolved = bool(data.get("prior_unknown_resolved", False))
        if rel_type != LongitudinalRelationType.UNCERTAINTY_RESOLUTION:
            prior_resolved = False

        res_dim = data.get("resolved_dimension")
        if not prior_resolved:
            res_dim = None

        return AdjudicationOutput(
            pair_id=pair_id,
            predecessor_block_id=t1.block_id,
            successor_block_id=t2.block_id,
            predicted_relation=rel_type,
            affected_dimension=str(data.get("affected_dimension", "unknown")),
            prior_unknown_resolved=prior_resolved,
            resolved_dimension=res_dim,
            outcome_or_current_state=str(data.get("outcome_or_current_state", "")),
            evidence_spans=tuple(data.get("evidence_spans", [])),
            reason_competing_rejections=data.get("reason_competing_rejections", {}),
            confidence=float(data.get("confidence", 1.0)),
            adjudication_trace=str(data.get("adjudication_trace", "")),
            prompt_tokens=call_res.prompt_tokens,
            completion_tokens=call_res.completion_tokens,
            latency_ms=call_res.latency_ms,
            cached=call_res.cached,
        )
