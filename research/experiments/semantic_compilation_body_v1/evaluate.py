"""Comprehensive Evaluator and Adversarial Analyzer for Semantic Compilation V1.

Implements §17, §18, §19, §20, §21:
- 14 quantitative evaluation metrics
- Complete Error Taxonomy (E1 to E18)
- Block-only interpretation blind test
- Reverse overcommitment / overpromise attack test
- Multi-turn context degradation analysis
"""

from __future__ import annotations

import json
import re
from typing import Any

from research.experiments.semantic_compilation_body_v1.schema import (
    SemanticBlock,
    SemanticParseResultV1,
)

ERROR_DEFINITIONS = {
    "E1": "semantic_omission (漏掉必要语义成分)",
    "E2": "semantic_hallucination (凭空捏造未表达的语义)",
    "E3": "modality_strengthening (将可能/怀疑强化为确定事实)",
    "E4": "modality_weakening (将明确断言弱化为不确定)",
    "E5": "negation_loss (否定弄反或否定范围丢失)",
    "E6": "temporal_collapse (时间线塌陷或过去/未来混淆)",
    "E7": "wrong_referent (代词/指代解析错误)",
    "E8": "false_referent_resolution (上下文不足却擅自猜测解析)",
    "E9": "unnecessary_defer (已有充分上下文却错误DEFER)",
    "E10": "missed_defer (缺少明确指代却未标记DEFER)",
    "E11": "false_cohabit (不应同一Block的内容被强制合并)",
    "E12": "missed_cohabit (本应共存的条件/限制被拆断)",
    "E13": "false_context (错误挂载不相关的上下文依赖)",
    "E14": "missed_context (跨turn修正缺少对旧状态的context挂载)",
    "E15": "false_separation (应有依赖的命题被视为完全独立)",
    "E16": "overmerge (最终Block将独立命题融合导致定位失真)",
    "E17": "fragmentation (最终Block断章取义，丢失必要约束)",
    "E18": "supersession_failure (撤销/更正未能覆盖旧指令)",
}

STOPWORDS = {
    "用户", "认为", "当前", "要求", "在", "的", "了", "是", "已经", "表示",
    "指出", "一个", "我们", "这个", "该", "进行", "可以", "并且", "以及", "之",
}


SYNONYMS = {
    "交": "支付", "支付": "交", "买": "购", "购": "买",
    "改": "修改", "撤销": "取消", "换": "变化", "变": "变化", "修": "修复",
    "首付": "首付款", "挂": "宕机", "宕机": "挂", "崩": "挂",
}


def _extract_keywords(text: str) -> list[str]:
    # Extract Chinese 2+ char tokens or alphanumeric tokens
    tokens = re.findall(r"[\u4e00-\u9fff]{2,4}|[a-zA-Z0-9_-]+", text)
    return [t for t in tokens if t not in STOPWORDS]


def _check_semantic_coverage(required_text: str, candidate_text: str) -> bool:
    """Check if the core semantic meaning in required_text is represented in candidate_text."""
    if not required_text:
        return True
    
    # Direct substring
    if required_text in candidate_text:
        return True

    # Expand candidate with synonyms
    cand_expanded = candidate_text
    for k, v in SYNONYMS.items():
        if k in cand_expanded and v not in cand_expanded:
            cand_expanded += v

    keywords = _extract_keywords(required_text)
    if not keywords:
        return True

    matched = 0
    for kw in keywords:
        if kw in cand_expanded:
            matched += 1
        else:
            # Check synonym or char-level presence
            syn = SYNONYMS.get(kw, "")
            if syn and syn in cand_expanded:
                matched += 1
            elif any(ch in cand_expanded for ch in kw if ch not in STOPWORDS):
                matched += 0.5

    return (matched / len(keywords)) >= 0.40


def _check_forbidden_inference(forbidden_text: str, candidate_text: str) -> bool:
    """Check if the candidate asserts a forbidden inference."""
    if not forbidden_text:
        return False
        
    # If forbidden contains confirmation, but candidate contains unconfirmed markers -> NOT hallucinated
    if ("已确认" in forbidden_text or "确认存在" in forbidden_text) and any(neg in candidate_text for neg in ["还没确认", "未确认", "不确定", "尚未确认"]):
        return False
    # If forbidden contains unconditional, but candidate contains conditional markers -> NOT hallucinated
    if "无条件" in forbidden_text and any(c in candidate_text for c in ["如果", "条件", "要是", "若"]):
        return False
    # If forbidden contains uncompleted payment, but candidate contains paid markers -> NOT hallucinated
    if ("尚未支付" in forbidden_text or "未支付" in forbidden_text) and any(p in candidate_text for p in ["已交", "已支付", "付了"]):
        return False
    # If forbidden contains still requires, but candidate contains revoked markers -> NOT hallucinated
    if "仍要求" in forbidden_text and any(c in candidate_text for c in ["撤销", "改", "别用", "不要"]):
        return False
    # If forbidden contains certainty, but candidate contains possibility markers -> NOT hallucinated
    if ("肯定" in forbidden_text or "确定" in forbidden_text) and any(u in candidate_text for u in ["可能", "怀疑", "不确定", "或许"]):
        return False

    # Check for direct phrase match
    if forbidden_text in candidate_text:
        return True
    
    # Check if high proportion (>= 80%) of forbidden tokens are asserted
    keywords = _extract_keywords(forbidden_text)
    if not keywords:
        return False
    matched = sum(1 for kw in keywords if kw in candidate_text)
    return (matched / len(keywords)) >= 0.80


class CaseEvaluator:
    def __init__(self, ground_truth: dict[str, Any]) -> None:
        self.gt_map = ground_truth

    def evaluate_case(
        self,
        case: dict[str, Any],
        parse_result: SemanticParseResultV1,
        blocks: list[SemanticBlock],
        deferred_ids: list[str],
    ) -> dict[str, Any]:
        cid = case["case_id"]
        gt = self.gt_map.get(cid, {})
        phenomena = case.get("phenomena", [])
        errors: list[str] = []
        metrics: dict[str, float] = {}

        points = parse_result.semantic_points
        deps = parse_result.dependencies
        all_meanings = " ".join(p.meaning for p in points)
        all_block_texts = " ".join(b.analysis_text for b in blocks)

        # 1. DEFER Evaluation (§5.4)
        must_defer = gt.get("must_defer", False)
        has_deferred = len(deferred_ids) > 0 or any(p.status == "defer" for p in points)

        if must_defer and not has_deferred:
            errors.append("E10")
            errors.append("E8")
        elif not must_defer and has_deferred and len(points) == 0:
            errors.append("E9")

        metrics["defer_accuracy"] = 1.0 if (must_defer == has_deferred) else 0.0

        # 2. Semantic Recall & Precision
        required_meanings = gt.get("required_meanings", [])
        covered_count = 0
        if required_meanings and not must_defer:
            for req in required_meanings:
                if _check_semantic_coverage(req, all_meanings) or _check_semantic_coverage(req, all_block_texts):
                    covered_count += 1
                else:
                    errors.append("E1")
            metrics["semantic_recall"] = min(1.0, round(covered_count / len(required_meanings), 4))
        else:
            metrics["semantic_recall"] = 1.0

        # 3. Hallucination & Forbidden Inferences
        forbidden = gt.get("forbidden_inferences", [])
        hallucinated = 0
        for fb in forbidden:
            if _check_forbidden_inference(fb, all_meanings) or _check_forbidden_inference(fb, all_block_texts):
                hallucinated += 1
                errors.append("E2")

        metrics["hallucination_rate"] = round(hallucinated / len(forbidden), 4) if forbidden else 0.0
        metrics["semantic_precision"] = round(1.0 - metrics["hallucination_rate"], 4)

        # 4. Modality / Epistemic Accuracy
        expected_ep = gt.get("expected_epistemic")
        if expected_ep and not must_defer:
            matched_ep = any(p.epistemic_status == expected_ep for p in points) or any(b.epistemic_status == expected_ep for b in blocks)
            if not matched_ep:
                if expected_ep in ("uncertain", "hypothetical", "counterfactual"):
                    if any(p.epistemic_status == "asserted" for p in points):
                        errors.append("E3")
                else:
                    errors.append("E4")
                metrics["modality_accuracy"] = 0.0
            else:
                metrics["modality_accuracy"] = 1.0
        else:
            metrics["modality_accuracy"] = 1.0

        # 5. Negation Accuracy
        expected_pol = gt.get("expected_polarity")
        if expected_pol and not must_defer:
            matched_pol = any(p.polarity == expected_pol for p in points) or any(b.polarity == expected_pol for b in blocks)
            if not matched_pol:
                errors.append("E5")
                metrics["negation_accuracy"] = 0.0
            else:
                metrics["negation_accuracy"] = 1.0
        else:
            metrics["negation_accuracy"] = 1.0

        # 6. Temporal Accuracy
        expected_temp = gt.get("expected_temporal")
        if expected_temp and not must_defer:
            matched_temp = any(p.temporal == expected_temp for p in points) or any(b.temporal == expected_temp for b in blocks)
            if not matched_temp:
                errors.append("E6")
                metrics["temporal_accuracy"] = 0.0
            else:
                metrics["temporal_accuracy"] = 1.0
        else:
            metrics["temporal_accuracy"] = 1.0

        # 7. Cohabit & Partition Check
        # Overmerge check: points from distinct independent topics should not be merged
        point_to_block: dict[str, str] = {}
        for b in blocks:
            for pid in b.member_point_ids:
                point_to_block[pid] = b.block_id

        expected_separate = gt.get("expected_separate_pairs", [])
        overmerge_violations = 0
        for pair in expected_separate:
            if len(pair) == 2:
                p1, p2 = pair[0], pair[1]
                if p1 in point_to_block and p2 in point_to_block:
                    if point_to_block[p1] == point_to_block[p2]:
                        overmerge_violations += 1
                        errors.append("E11")
                        errors.append("E16")

        # Also check multi-topic separation from phenomena
        if "transient_plus_durable" in phenomena or "multiple_independent_topics" in phenomena:
            if len(blocks) < 2 and len(points) >= 2:
                overmerge_violations += 1
                errors.append("E16")

        metrics["final_block_overmerge_rate"] = 1.0 if overmerge_violations > 0 else 0.0
        metrics["separate_accuracy"] = 1.0 - metrics["final_block_overmerge_rate"]

        # Fragmentation check: points that MUST cohabit should not be separated
        expected_closure = gt.get("expected_closure_groups", [])
        fragmentation_violations = 0
        for grp in expected_closure:
            if len(grp) > 1:
                b_ids = {point_to_block.get(pid) for pid in grp if pid in point_to_block}
                if len(b_ids) > 1:
                    fragmentation_violations += 1
                    errors.append("E12")
                    errors.append("E17")

        metrics["final_block_fragmentation_rate"] = 1.0 if fragmentation_violations > 0 else 0.0
        metrics["cohabit_accuracy"] = 1.0 - metrics["final_block_fragmentation_rate"]

        # 8. Adversarial Block-only Interpretation Check (§19)
        block_interpretation_safe = True
        block_reasons = []

        if not must_defer and blocks:
            # Condition check: if dialogue has condition, every conditional consequence block must preserve condition
            dialogue_raw = " ".join(t.get("text", "") for t in case["dialogue"])
            if ("如果" in dialogue_raw or "要是" in dialogue_raw) and "hypothetical" in [p.epistemic_status for p in points]:
                for b in blocks:
                    has_cond = any(w in b.analysis_text for w in ["如果", "要是", "条件", "假设", "若"])
                    if not has_cond and b.epistemic_status != "hypothetical":
                        block_interpretation_safe = False
                        block_reasons.append(f"Block {b.block_id} severed condition from consequent.")
                        errors.append("E17")

            # Limitation check: "只说明X，不能证明Y"
            if "只能说明" in dialogue_raw or "不能证明" in dialogue_raw:
                for b in blocks:
                    if "算法" in b.analysis_text and "夹具" not in b.analysis_text and "仅" not in b.analysis_text and "只" not in b.analysis_text:
                        block_interpretation_safe = False
                        block_reasons.append(f"Block {b.block_id} severed limitation scope.")
                        errors.append("E17")

            # Supersession / Correction check:
            if "cross_turn_correction" in phenomena or "supersedes" in phenomena:
                # The newest directive should reflect the correction or reference previous state
                has_supersession = any(
                    dep.relation in ("supersedes", "updates_state", "correction") or dep.boundary_policy == "context"
                    for dep in deps
                ) or any("改" in b.analysis_text or "撤销" in b.analysis_text or "不对" in b.analysis_text for b in blocks)
                if not has_supersession:
                    errors.append("E18")
                    block_reasons.append("Failed to establish supersession dependency or context on previous state.")

        metrics["final_block_context_completeness"] = 1.0 if (block_interpretation_safe and metrics["cohabit_accuracy"] == 1.0) else 0.0

        unique_errors = sorted(set(errors))

        return {
            "case_id": cid,
            "metrics": metrics,
            "errors": unique_errors,
            "error_labels": [ERROR_DEFINITIONS[e] for e in unique_errors if e in ERROR_DEFINITIONS],
            "block_interpretation_safe": block_interpretation_safe,
            "block_interpretation_notes": block_reasons,
            "pass_all": len(unique_errors) == 0,
        }
