"""Taxonomy and Diagnostic Analysis for Multi-Turn Semantic Omissions (O1-O10) and E19 Divergence.

Fulfills Phase 4 requirements:
  - O1-O10 Structural Omission Classification
  - E19 Response vs. Sidecar Divergence Detection
  - Obligation Coverage Metric Computation
"""

from __future__ import annotations

import re
from typing import Any
from research.experiments.semantic_compilation_body_v1.schema import (
    SemanticBlock,
    SemanticParseResultV1,
)

OMISSION_DEFINITIONS = {
    "O1": "tail_omission (尾部遗漏：漏掉句末或尾轮补充约束/二级命题)",
    "O2": "qualifier_modality_omission (限定词/情态遗漏：丢失'可能'、'暂时'、'如果'等情态修饰)",
    "O3": "cross_turn_context_omission (跨轮上下文遗漏：'后者'/'按刚才说的'未能关联前轮实体)",
    "O4": "old_state_residual (旧状态残留：更新/推翻前轮后，旧状态仍被视为当前有效事实)",
    "O5": "embedded_directive_omission (嵌入式指令遗漏：长对话中夹带的持久约束被当成闲聊忽略)",
    "O6": "negation_scope_shrinkage (否定范围收缩：丢失多重否定或全局否定态度)",
    "O7": "condition_consequence_split (条件/后果断裂：条件依赖漏记或与后果分离)",
    "O8": "source_relative_stance_omission (来源立场遗漏：把第三方转述直接误认为用户自身事实)",
    "O9": "partial_correction_distortion (局部修复失真：只修改参数A时丢失了保持不变的参数B)",
    "O10": "ambiguous_ref_not_deferred (歧义未决未DEFER：指代不明时擅自猜测，未标记DEFER)",
}


def classify_omission(
    missed_obligation: str,
    dialogue: list[dict[str, Any]],
    case_category: str,
    points_text: str,
) -> str:
    """Classify why a specific must_preserve obligation was omitted into O1-O10."""
    ob_lower = missed_obligation.lower()

    # 1. Check if it's an ambiguous reference that wasn't deferred
    if "defer" in ob_lower or "指代不明" in ob_lower or "模糊" in ob_lower:
        return "O10"

    # 2. Check category hints
    if case_category == "durable_instruction_intro" or case_category == "buried_durable_instruction" or "规矩" in missed_obligation or "以后" in missed_obligation or "永久" in missed_obligation:
        return "O5"

    if case_category == "partial_correction" or "保持不变" in missed_obligation or "不变" in missed_obligation:
        return "O9"

    if case_category == "source_relative_stance" or "第三方" in missed_obligation or "立场" in missed_obligation or "转述" in missed_obligation or "声称" in missed_obligation:
        return "O8"

    if case_category == "reference_resolution_latter" or "后者" in missed_obligation or "关联" in missed_obligation:
        return "O3"

    if "旧" in missed_obligation or "原定" in missed_obligation or "原计划" in missed_obligation:
        return "O4"

    if "如果" in missed_obligation or "若" in missed_obligation or "条件" in missed_obligation:
        return "O7"

    if "不认为" in missed_obligation or "否认" in missed_obligation or "严禁" in missed_obligation or "反对" in missed_obligation:
        return "O6"

    if any(q in missed_obligation for q in ["可能", "考虑", "暂时", "目前", "打算"]):
        return "O2"

    # Default to O1 if it appeared near the end of the turn/dialogue
    return "O1"


def detect_response_sidecar_divergence(
    assistant_response: str,
    semantic_points_text: str,
    must_preserve: list[str],
) -> tuple[bool, list[str]]:
    """Detect E19: Divergence between conversational assistant response and semantic sidecar.

    Cases of divergence:
      - Type A (Assistant understood, sidecar dropped):
        Assistant response explicitly acknowledges or addresses an obligation,
        but the semantic sidecar has zero mention of it.
      - Type B (Sidecar captured, assistant hallucinated contradiction):
        Sidecar parsed the constraint, but assistant response directly violated it.
    """
    divergences: list[str] = []

    for ob in must_preserve:
        in_resp = _fuzzy_presence(ob, assistant_response)
        in_sidecar = _fuzzy_presence(ob, semantic_points_text)

        if in_resp and not in_sidecar:
            divergences.append(
                f"Type A (Understood in reply, lost in sidecar): Assistant mentioned '{ob}', but sidecar omitted it."
            )
        elif in_sidecar and not in_resp and any(d in ob for d in ["严禁", "必须", "以后"]):
            # Check for critical instruction divergence
            divergences.append(
                f"Type B (Sidecar has constraint, reply ignored): Constraint '{ob}' in sidecar but not acknowledged in reply."
            )

    has_e19 = len(divergences) > 0
    return has_e19, divergences


def _fuzzy_presence(target: str, text: str) -> bool:
    """Helper for presence detection."""
    # Clean target
    clean = re.sub(r"[用户|原定|原计划|决定|要求|曾|指令]", "", target)
    keywords = re.findall(r"[\u4e00-\u9fff]{2,4}|[a-zA-Z0-9_-]+", clean)
    if not keywords:
        return target in text
    
    matches = sum(1 for kw in keywords if kw in text)
    return (matches / len(keywords)) >= 0.45
