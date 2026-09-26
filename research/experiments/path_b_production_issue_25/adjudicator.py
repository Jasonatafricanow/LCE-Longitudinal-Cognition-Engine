"""Stage 2: Selective semantic adjudication for Issue #25.

Only Stage 1 discovered candidates may reach this adjudicator.
Gold-pair shortcut is forbidden.

Output separates two orthogonal axes:
  A. Longitudinal relation (STATE_CHANGE, CORRECTION_RETRACTION, etc.)
  B. Knowledge effect (prior_unknown_resolved, resolved_dimensions, etc.)
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from research.experiments.path_b_production_issue_25.contracts import (
    AdjudicationResult,
    DiscoveredCandidate,
    KnowledgeEffect,
    LongitudinalRelation,
    ProductionMemoryView,
)


# ---------------------------------------------------------------------------
# Deterministic rule-based adjudicator (no LLM in this small experiment)
# ---------------------------------------------------------------------------

# Lexical signal patterns
_CORRECTION_PATTERN = re.compile(
    r'说错|更正|纠正|其实不是|搞错|弄错|之前.*错|原来.*不是'
)
_EXPLICIT_CORRECTION = re.compile(
    r'(之前|上次|以前).*?说错|更正通知|纠正'
)
_CANCELLATION_PATTERN = re.compile(
    r'取消|撤回|不.*了|退出|放弃|作废'
)
_COMPLETION_PATTERN = re.compile(
    r'已经|完成|到了|办好|搞定|拿到|做完|结束|出来了|成功'
)
_FAILURE_PATTERN = re.compile(
    r'没过|失败|没成功|不行|被拒|落选|没能|未通过'
)
_PERSISTENCE_PATTERN = re.compile(
    r'还在|仍然|继续|还没|依然|一直|没变|照旧|还是.*等'
)
_PLAN_PATTERN = re.compile(
    r'计划|打算|准备|约了|预定|预约|要去'
)
_UNCERTAINTY_PATTERN = re.compile(
    r'不知道|可能|也许|大概|待定|不确定|等.*结果|审批中|暗示|还没.*通知'
)
_RESOLUTION_PATTERN = re.compile(
    r'确定|正式|结果.*出来|通知|批准|明确|确认|决定|不.*了'
)
_LATE_FACT_PATTERN = re.compile(
    r'原来|其实|后来才知道|一直不知道'
)


def _entity_overlap_ratio(text_a: str, text_b: str) -> float:
    """Compute Chinese bigram overlap ratio as entity proxy."""
    chars_a = re.findall(r'[\u4e00-\u9fff]', text_a)
    chars_b = re.findall(r'[\u4e00-\u9fff]', text_b)
    bg_a = {chars_a[i] + chars_a[i+1] for i in range(len(chars_a) - 1)} if len(chars_a) > 1 else set()
    bg_b = {chars_b[i] + chars_b[i+1] for i in range(len(chars_b) - 1)} if len(chars_b) > 1 else set()
    if not bg_a or not bg_b:
        return 0.0
    return len(bg_a & bg_b) / max(len(bg_a), len(bg_b))


class SelectiveAdjudicator:
    """Rule-based adjudicator producing orthogonal relation + knowledge effect.

    Strictly operates only on Stage 1 discovered candidates.
    No gold-pair shortcut.
    """

    def __init__(self, views: Sequence[ProductionMemoryView]) -> None:
        self._view_map = {v.memory_id: v for v in views}

    def adjudicate(
        self,
        candidates: Sequence[DiscoveredCandidate],
    ) -> list[AdjudicationResult]:
        """Adjudicate a batch of Stage 1 candidates."""
        results = []
        for cand in candidates:
            result = self._adjudicate_one(cand)
            results.append(result)
        return results

    def _adjudicate_one(self, cand: DiscoveredCandidate) -> AdjudicationResult:
        pred = self._view_map[cand.predecessor_id]
        succ = self._view_map[cand.successor_id]

        p_content = pred.content
        s_content = succ.content

        # ---- Step 1: Entity/subject continuity check ----
        overlap = _entity_overlap_ratio(p_content, s_content)
        trace_parts = [f"overlap={overlap:.2f}"]

        # Low overlap → likely UNRELATED
        if overlap < 0.05 and not any(
            sig.startswith(("plan_outcome", "correction", "persistence", "uncertainty"))
            for sig in cand.signals
        ):
            return AdjudicationResult(
                candidate_id=cand.candidate_id,
                predecessor_id=cand.predecessor_id,
                successor_id=cand.successor_id,
                longitudinal_relation=LongitudinalRelation.UNRELATED,
                knowledge_effect=KnowledgeEffect(),
                adjudication_trace=f"low_overlap_rejection; {'; '.join(trace_parts)}",
                confidence=0.8,
            )

        # ---- Step 2: Determine longitudinal relation ----
        relation = LongitudinalRelation.UNKNOWN_RELATION
        evidence_spans: list[str] = []
        confidence = 0.5

        # Check for correction
        if _EXPLICIT_CORRECTION.search(s_content) or _CORRECTION_PATTERN.search(s_content):
            # Correction: source was wrong, not world change
            relation = LongitudinalRelation.CORRECTION_RETRACTION
            evidence_spans.append("correction_lexical_cue")
            trace_parts.append("correction_detected")
            confidence = 0.85

        # Check for persistence
        elif _PERSISTENCE_PATTERN.search(s_content) and overlap >= 0.1:
            relation = LongitudinalRelation.PERSISTENCE_CONFIRMATION
            evidence_spans.append("persistence_lexical_cue")
            trace_parts.append("persistence_detected")
            confidence = 0.8

        # Check for state change (world actually changed)
        elif (
            (_PLAN_PATTERN.search(p_content) and (
                _COMPLETION_PATTERN.search(s_content)
                or _FAILURE_PATTERN.search(s_content)
                or _CANCELLATION_PATTERN.search(s_content)
            ))
            or (_UNCERTAINTY_PATTERN.search(p_content) and _RESOLUTION_PATTERN.search(s_content))
            or overlap >= 0.08
            and any(
                sig.startswith(("plan_outcome", "uncertainty_resolution"))
                for sig in cand.signals
            )
        ):
            relation = LongitudinalRelation.STATE_CHANGE
            evidence_spans.append("state_change_arc")
            trace_parts.append("state_change_detected")
            confidence = 0.85

        # Check for late-arriving fact (special case of correction)
        elif _LATE_FACT_PATTERN.search(s_content) and overlap >= 0.05:
            relation = LongitudinalRelation.CORRECTION_RETRACTION
            evidence_spans.append("late_fact_correction")
            trace_parts.append("late_fact_detected")
            confidence = 0.75

        # Fallback: if good signals but no clear pattern
        elif overlap >= 0.15:
            # High overlap with temporal succession → possible state change
            # Check if content indicates change vs same
            if any(kw in s_content for kw in ("变了", "换了", "改了", "跳槽", "搬", "转", "提前", "推迟")):
                relation = LongitudinalRelation.STATE_CHANGE
                evidence_spans.append("implicit_state_change")
                trace_parts.append("implicit_change_detected")
                confidence = 0.7
            else:
                relation = LongitudinalRelation.UNKNOWN_RELATION
                trace_parts.append("high_overlap_but_ambiguous")
                confidence = 0.4

        else:
            # Insufficient evidence for a relation
            if overlap < 0.05:
                relation = LongitudinalRelation.UNRELATED
                trace_parts.append("insufficient_evidence_unrelated")
                confidence = 0.6
            else:
                relation = LongitudinalRelation.UNKNOWN_RELATION
                trace_parts.append("insufficient_evidence_unknown")
                confidence = 0.3

        # ---- Step 3: Determine knowledge effect (independent axis) ----
        prior_unknown_resolved: bool | None = None
        resolved_dims: list[str] = []
        new_unknowns: list[str] = []

        # If predecessor had uncertainty and successor provides resolution
        if _UNCERTAINTY_PATTERN.search(p_content):
            if _RESOLUTION_PATTERN.search(s_content) or _COMPLETION_PATTERN.search(s_content):
                prior_unknown_resolved = True
                # Try to identify the dimension
                if "结果" in p_content or "检查" in p_content:
                    resolved_dims.append("test_result")
                if "通过" in p_content or "审批" in p_content or "签证" in p_content:
                    resolved_dims.append("approval_status")
                if "可能" in p_content:
                    resolved_dims.append("possibility_resolution")
                if not resolved_dims:
                    resolved_dims.append("general_resolution")
                trace_parts.append("prior_unknown_resolved")
            elif _PERSISTENCE_PATTERN.search(s_content):
                prior_unknown_resolved = False
                trace_parts.append("prior_unknown_persists")
            elif _FAILURE_PATTERN.search(s_content) or _CANCELLATION_PATTERN.search(s_content):
                prior_unknown_resolved = True
                resolved_dims.append("outcome_determined")
                trace_parts.append("outcome_resolved_negatively")

        # Plan completion also resolves the implicit "will it happen" unknown
        if _PLAN_PATTERN.search(p_content) and (
            _COMPLETION_PATTERN.search(s_content)
            or _FAILURE_PATTERN.search(s_content)
            or _CANCELLATION_PATTERN.search(s_content)
        ):
            if prior_unknown_resolved is None:
                prior_unknown_resolved = True
                resolved_dims.append("plan_outcome")
                trace_parts.append("plan_outcome_resolved")

        # Correction doesn't resolve uncertainty — it fixes wrong information
        if relation == LongitudinalRelation.CORRECTION_RETRACTION:
            if not _UNCERTAINTY_PATTERN.search(p_content):
                # Correction of a definite statement is not unknown resolution
                if prior_unknown_resolved is None:
                    prior_unknown_resolved = False

        # PERSISTENCE cannot resolve unknowns (F6: no new evidence = no new cognition)
        if relation == LongitudinalRelation.PERSISTENCE_CONFIRMATION:
            prior_unknown_resolved = False
            resolved_dims = []

        # UNRELATED cannot resolve unknowns
        if relation == LongitudinalRelation.UNRELATED:
            prior_unknown_resolved = None
            resolved_dims = []

        knowledge_effect = KnowledgeEffect(
            prior_unknown_resolved=prior_unknown_resolved if prior_unknown_resolved is not None else None,
            resolved_dimensions=tuple(resolved_dims),
            newly_introduced_unknowns=tuple(new_unknowns),
        )

        return AdjudicationResult(
            candidate_id=cand.candidate_id,
            predecessor_id=cand.predecessor_id,
            successor_id=cand.successor_id,
            longitudinal_relation=relation,
            knowledge_effect=knowledge_effect,
            evidence_spans=tuple(evidence_spans),
            adjudication_trace="; ".join(trace_parts),
            confidence=confidence,
        )
