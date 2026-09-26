"""Adversarial corpus for Issue #25 Path B production-shaped experiment.

12 mandatory semantic families, each with hard contrasts.
All input uses ProductionMemoryView — NO oracle fields.

Families:
  1. future plan → completed
  2. future plan → failed
  3. future plan → cancelled externally
  4. possible event → confirmed
  5. possible event → disproven
  6. unresolved state → resolved by later evidence
  7. state actually changes
  8. earlier statement is corrected
  9. unresolved state persists
 10. semantically similar but unrelated neighbors
 11. late-arriving past fact
 12. future proposition known now
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from research.experiments.path_b_production_issue_25.contracts import (
    AdjudicationResult,
    DiscoveredCandidate,
    GoldAnnotation,
    KnowledgeEffect,
    LongitudinalRelation,
    ProductionMemoryView,
    TemporalCoordinates,
)

# ---------------------------------------------------------------------------
# Time scaffolding — all deterministic and replayable
# ---------------------------------------------------------------------------

_BASE = datetime(2026, 7, 1, 8, 0, tzinfo=UTC)


def _t(days: int, hours: int = 0) -> datetime:
    return _BASE + timedelta(days=days, hours=hours)


# ---------------------------------------------------------------------------
# Corpus blocks (ProductionMemoryView, no oracle fields)
# ---------------------------------------------------------------------------

def build_corpus() -> tuple[ProductionMemoryView, ...]:
    """Build the adversarial corpus of production-shaped memory views."""
    return tuple(_ALL_BLOCKS)


# Family 1: future plan → completed
_F1_PLAN = ProductionMemoryView(
    memory_id="m01_plan_trip",
    content="我计划下周三去上海出差，需要订周二晚上的高铁票",
    source_refs=("ev_m01",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(0),
        received_at=_t(0, 1),
        semantic_time=_t(7),  # about next Wednesday
        valid_start=_t(0),
        valid_end=_t(7),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

_F1_DONE = ProductionMemoryView(
    memory_id="m02_trip_completed",
    content="已经到上海了，高铁准时到达，酒店也顺利入住",
    source_refs=("ev_m02",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(7, 2),
        received_at=_t(7, 3),
        semantic_time=_t(7),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

# Family 2: future plan → failed
_F2_PLAN = ProductionMemoryView(
    memory_id="m03_exam_plan",
    content="我打算周六参加驾照科目二考试",
    source_refs=("ev_m03",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(1),
        received_at=_t(1, 1),
        semantic_time=_t(5),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

_F2_FAILED = ProductionMemoryView(
    memory_id="m04_exam_failed",
    content="科目二没过，倒库的时候压线了，下次还要重新约考",
    source_refs=("ev_m04",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(5, 6),
        received_at=_t(5, 7),
        semantic_time=_t(5),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

# Family 3: future plan → cancelled externally
_F3_PLAN = ProductionMemoryView(
    memory_id="m05_dinner_plan",
    content="周五和客户约了晚餐，讨论合同细节",
    source_refs=("ev_m05",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(2),
        received_at=_t(2, 1),
        semantic_time=_t(4),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

_F3_CANCELLED = ProductionMemoryView(
    memory_id="m06_dinner_cancelled",
    content="客户临时通知取消周五的晚餐，说要出差",
    source_refs=("ev_m06",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(3, 4),
        received_at=_t(3, 5),
        semantic_time=_t(4),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

# Family 4: possible event → confirmed
_F4_POSSIBLE = ProductionMemoryView(
    memory_id="m07_possible_raise",
    content="听说公司可能会在季度末调薪，但还没有正式通知",
    source_refs=("ev_m07",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(3),
        received_at=_t(3, 1),
        semantic_time=_t(3),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

_F4_CONFIRMED = ProductionMemoryView(
    memory_id="m08_raise_confirmed",
    content="HR正式发了调薪通知，从下个月开始涨15%",
    source_refs=("ev_m08",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(10, 2),
        received_at=_t(10, 3),
        semantic_time=_t(10),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

# Family 5: possible event → disproven
_F5_POSSIBLE = ProductionMemoryView(
    memory_id="m09_possible_move",
    content="房东暗示可能要收回房子自住，但还没明确",
    source_refs=("ev_m09",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(4),
        received_at=_t(4, 1),
        semantic_time=_t(4),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

_F5_DISPROVEN = ProductionMemoryView(
    memory_id="m10_move_disproven",
    content="房东说不收回了，续签两年合同，租金不变",
    source_refs=("ev_m10",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(12),
        received_at=_t(12, 1),
        semantic_time=_t(12),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

# Family 6: unresolved state → resolved by later evidence
_F6_UNRESOLVED = ProductionMemoryView(
    memory_id="m11_blood_test_waiting",
    content="做了血常规检查，医生说要等结果出来才知道有没有问题",
    source_refs=("ev_m11",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(5),
        received_at=_t(5, 1),
        semantic_time=_t(5),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

_F6_RESOLVED = ProductionMemoryView(
    memory_id="m12_blood_test_result",
    content="血检结果出来了，各项指标正常，没什么问题",
    source_refs=("ev_m12",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(8),
        received_at=_t(8, 1),
        semantic_time=_t(8),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

# Family 7: state actually changes (world changes, not a correction)
_F7_STATE_A = ProductionMemoryView(
    memory_id="m13_job_current",
    content="我现在在一家互联网公司做后端开发",
    source_refs=("ev_m13",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(0, 3),
        received_at=_t(0, 4),
        semantic_time=_t(0),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

_F7_STATE_B = ProductionMemoryView(
    memory_id="m14_job_changed",
    content="我上个月跳槽了，现在在一家AI公司做大模型训练",
    source_refs=("ev_m14",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(30),
        received_at=_t(30, 1),
        semantic_time=_t(30),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

# Family 8: earlier statement is corrected (source was wrong)
_F8_ORIGINAL = ProductionMemoryView(
    memory_id="m15_meeting_time",
    content="明天的项目评审会在下午两点开始",
    source_refs=("ev_m15",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(6),
        received_at=_t(6, 1),
        semantic_time=_t(7),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

_F8_CORRECTED = ProductionMemoryView(
    memory_id="m16_meeting_correction",
    content="之前说错了，评审会是下午三点不是两点，刚收到更正通知",
    source_refs=("ev_m16",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(6, 6),
        received_at=_t(6, 7),
        semantic_time=_t(7),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

# Family 9: unresolved state persists (no new evidence)
_F9_UNRESOLVED = ProductionMemoryView(
    memory_id="m17_visa_pending",
    content="签证申请提交了，还在审批中，不知道能不能通过",
    source_refs=("ev_m17",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(2, 3),
        received_at=_t(2, 4),
        semantic_time=_t(2),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

_F9_STILL_PENDING = ProductionMemoryView(
    memory_id="m18_visa_still_pending",
    content="签证还没消息，已经两周了，继续等着吧",
    source_refs=("ev_m18",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(16),
        received_at=_t(16, 1),
        semantic_time=_t(16),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

# Family 10: semantically similar but UNRELATED neighbors
# (hard contrast: similar wording about "上海出差" but different life context)
_F10_SIMILAR_A = ProductionMemoryView(
    memory_id="m19_colleague_trip",
    content="同事王明下周也要去上海出差，我帮他订了酒店",
    source_refs=("ev_m19",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(0, 5),
        received_at=_t(0, 6),
        semantic_time=_t(0),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

_F10_SIMILAR_B = ProductionMemoryView(
    memory_id="m20_own_shanghai_memory",
    content="去年在上海出差的时候吃到了很好吃的小笼包",
    source_refs=("ev_m20",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(1, 2),
        received_at=_t(1, 3),
        semantic_time=_t(-365),  # about last year
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

# Family 11: late-arriving past fact
_F11_LATE_CONTEXT = ProductionMemoryView(
    memory_id="m21_late_fact",
    content="原来我小时候在这个城市住过三年，之前一直不知道",
    source_refs=("ev_m21",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(9),
        received_at=_t(9, 1),
        semantic_time=_t(-7300),  # about childhood, ~20 years ago
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

_F11_EARLIER_MENTION = ProductionMemoryView(
    memory_id="m22_city_mention",
    content="这个城市我完全不熟悉，从来没去过",
    source_refs=("ev_m22",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(3, 6),
        received_at=_t(3, 7),
        semantic_time=_t(3),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

# Family 12: future proposition known now
_F12_FUTURE_KNOWN = ProductionMemoryView(
    memory_id="m23_future_deadline",
    content="下个季度的KPI截止日是12月31号，已经确定了",
    source_refs=("ev_m23",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(8, 4),
        received_at=_t(8, 5),
        semantic_time=_t(8),
        valid_start=_t(8),
        valid_end=_t(183),  # end of quarter
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

_F12_DEADLINE_CHANGED = ProductionMemoryView(
    memory_id="m24_deadline_moved",
    content="KPI截止日提前到12月15号，领导说要提前汇总",
    source_refs=("ev_m24",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(20),
        received_at=_t(20, 1),
        semantic_time=_t(20),
        valid_start=_t(20),
        valid_end=_t(168),  # new deadline
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)


# Extra hard-contrast items: wording-similar noise blocks
# These must NOT be linked to their semantic-family peers

_NOISE_1 = ProductionMemoryView(
    memory_id="m25_noise_exam",
    content="孩子的期末考试成绩出来了，数学考了98分",
    source_refs=("ev_m25",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(5, 8),
        received_at=_t(5, 9),
        semantic_time=_t(5),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

_NOISE_2 = ProductionMemoryView(
    memory_id="m26_noise_blood",
    content="今天买了血橙，特别甜",
    source_refs=("ev_m26",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(5, 4),
        received_at=_t(5, 5),
        semantic_time=_t(5),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

_NOISE_3 = ProductionMemoryView(
    memory_id="m27_noise_hotel",
    content="帮同事推荐了一个上海的酒店，评价很好",
    source_refs=("ev_m27",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(1, 6),
        received_at=_t(1, 7),
        semantic_time=_t(1),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

_NOISE_4 = ProductionMemoryView(
    memory_id="m28_noise_contract",
    content="看了一个有趣的合同法案例，和我的工作无关但学到东西了",
    source_refs=("ev_m28",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(3, 8),
        received_at=_t(3, 9),
        semantic_time=_t(3),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)


# ---------------------------------------------------------------------------
# All blocks in chronological order (by received_at)
# ---------------------------------------------------------------------------

_ALL_BLOCKS = sorted(
    [
        _F1_PLAN, _F1_DONE,
        _F2_PLAN, _F2_FAILED,
        _F3_PLAN, _F3_CANCELLED,
        _F4_POSSIBLE, _F4_CONFIRMED,
        _F5_POSSIBLE, _F5_DISPROVEN,
        _F6_UNRESOLVED, _F6_RESOLVED,
        _F7_STATE_A, _F7_STATE_B,
        _F8_ORIGINAL, _F8_CORRECTED,
        _F9_UNRESOLVED, _F9_STILL_PENDING,
        _F10_SIMILAR_A, _F10_SIMILAR_B,
        _F11_LATE_CONTEXT, _F11_EARLIER_MENTION,
        _F12_FUTURE_KNOWN, _F12_DEADLINE_CHANGED,
        _NOISE_1, _NOISE_2, _NOISE_3, _NOISE_4,
    ],
    key=lambda m: m.temporal.received_at,
)


# ---------------------------------------------------------------------------
# Gold annotations (never consumed by the pipeline)
# ---------------------------------------------------------------------------

def build_gold_annotations() -> tuple[GoldAnnotation, ...]:
    """Gold truth for all meaningful pairs.

    Key: these annotations are ONLY for evaluation.
    The pipeline must discover candidates from Stage 1 alone.
    """
    return (
        # Family 1: plan → completed (STATE_CHANGE + resolves "will it happen")
        GoldAnnotation(
            pair_id="G01",
            predecessor_id="m01_plan_trip",
            successor_id="m02_trip_completed",
            longitudinal_relation=LongitudinalRelation.STATE_CHANGE,
            knowledge_effect=KnowledgeEffect(
                prior_unknown_resolved=True,
                resolved_dimensions=("trip_completion",),
            ),
            semantic_family="F1_plan_completed",
            falsification_tags=("F1", "F5"),
        ),
        # Family 2: plan → failed (STATE_CHANGE + resolves "exam outcome")
        GoldAnnotation(
            pair_id="G02",
            predecessor_id="m03_exam_plan",
            successor_id="m04_exam_failed",
            longitudinal_relation=LongitudinalRelation.STATE_CHANGE,
            knowledge_effect=KnowledgeEffect(
                prior_unknown_resolved=True,
                resolved_dimensions=("exam_outcome",),
            ),
            semantic_family="F2_plan_failed",
            falsification_tags=("F1", "F4", "F5"),
        ),
        # Family 3: plan → cancelled externally (STATE_CHANGE, plan is voided)
        GoldAnnotation(
            pair_id="G03",
            predecessor_id="m05_dinner_plan",
            successor_id="m06_dinner_cancelled",
            longitudinal_relation=LongitudinalRelation.STATE_CHANGE,
            knowledge_effect=KnowledgeEffect(
                prior_unknown_resolved=True,
                resolved_dimensions=("dinner_happening",),
            ),
            semantic_family="F3_plan_cancelled",
            falsification_tags=("F1", "F4", "F5"),
        ),
        # Family 4: possible → confirmed (STATE_CHANGE + resolves rumor)
        GoldAnnotation(
            pair_id="G04",
            predecessor_id="m07_possible_raise",
            successor_id="m08_raise_confirmed",
            longitudinal_relation=LongitudinalRelation.STATE_CHANGE,
            knowledge_effect=KnowledgeEffect(
                prior_unknown_resolved=True,
                resolved_dimensions=("salary_adjustment",),
            ),
            semantic_family="F4_confirmed",
            falsification_tags=("F1", "F5"),
        ),
        # Family 5: possible → disproven (STATE_CHANGE + resolves uncertainty)
        GoldAnnotation(
            pair_id="G05",
            predecessor_id="m09_possible_move",
            successor_id="m10_move_disproven",
            longitudinal_relation=LongitudinalRelation.STATE_CHANGE,
            knowledge_effect=KnowledgeEffect(
                prior_unknown_resolved=True,
                resolved_dimensions=("housing_status",),
            ),
            semantic_family="F5_disproven",
            falsification_tags=("F1", "F5"),
        ),
        # Family 6: unresolved → resolved (STATE_CHANGE + explicit resolution)
        GoldAnnotation(
            pair_id="G06",
            predecessor_id="m11_blood_test_waiting",
            successor_id="m12_blood_test_result",
            longitudinal_relation=LongitudinalRelation.STATE_CHANGE,
            knowledge_effect=KnowledgeEffect(
                prior_unknown_resolved=True,
                resolved_dimensions=("health_status",),
            ),
            semantic_family="F6_resolved",
            falsification_tags=("F1", "F5", "F6"),
        ),
        # Family 7: world state change (not a correction)
        GoldAnnotation(
            pair_id="G07",
            predecessor_id="m13_job_current",
            successor_id="m14_job_changed",
            longitudinal_relation=LongitudinalRelation.STATE_CHANGE,
            knowledge_effect=KnowledgeEffect(
                prior_unknown_resolved=False,
            ),
            semantic_family="F7_state_change",
            falsification_tags=("F4",),
        ),
        # Family 8: correction (source was wrong, not world change)
        GoldAnnotation(
            pair_id="G08",
            predecessor_id="m15_meeting_time",
            successor_id="m16_meeting_correction",
            longitudinal_relation=LongitudinalRelation.CORRECTION_RETRACTION,
            knowledge_effect=KnowledgeEffect(
                prior_unknown_resolved=False,
            ),
            semantic_family="F8_correction",
            falsification_tags=("F4",),
        ),
        # Family 9: persistence (unresolved persists)
        GoldAnnotation(
            pair_id="G09",
            predecessor_id="m17_visa_pending",
            successor_id="m18_visa_still_pending",
            longitudinal_relation=LongitudinalRelation.PERSISTENCE_CONFIRMATION,
            knowledge_effect=KnowledgeEffect(
                prior_unknown_resolved=False,
                newly_introduced_unknowns=(),
            ),
            semantic_family="F9_persistence",
            falsification_tags=("F6",),
        ),
        # Family 10: semantically similar but UNRELATED
        GoldAnnotation(
            pair_id="G10",
            predecessor_id="m19_colleague_trip",
            successor_id="m20_own_shanghai_memory",
            longitudinal_relation=LongitudinalRelation.UNRELATED,
            knowledge_effect=KnowledgeEffect(),
            semantic_family="F10_unrelated_similar",
            falsification_tags=("F1",),
        ),
        # Family 11: late-arriving fact corrects an earlier claim
        GoldAnnotation(
            pair_id="G11",
            predecessor_id="m22_city_mention",
            successor_id="m21_late_fact",
            longitudinal_relation=LongitudinalRelation.CORRECTION_RETRACTION,
            knowledge_effect=KnowledgeEffect(
                prior_unknown_resolved=True,
                resolved_dimensions=("city_history",),
            ),
            semantic_family="F11_late_fact",
            falsification_tags=("F4", "F5"),
        ),
        # Family 12: future proposition changed
        GoldAnnotation(
            pair_id="G12",
            predecessor_id="m23_future_deadline",
            successor_id="m24_deadline_moved",
            longitudinal_relation=LongitudinalRelation.STATE_CHANGE,
            knowledge_effect=KnowledgeEffect(
                prior_unknown_resolved=False,
            ),
            semantic_family="F12_future_changed",
            falsification_tags=("F4",),
        ),
        # Cross-family noise rejection: exam plan vs child's exam (similar word "考试")
        GoldAnnotation(
            pair_id="G13_noise",
            predecessor_id="m03_exam_plan",
            successor_id="m25_noise_exam",
            longitudinal_relation=LongitudinalRelation.UNRELATED,
            knowledge_effect=KnowledgeEffect(),
            semantic_family="noise_contrast",
            falsification_tags=("F1",),
        ),
        # Cross-family noise: blood test vs blood orange (similar word "血")
        GoldAnnotation(
            pair_id="G14_noise",
            predecessor_id="m11_blood_test_waiting",
            successor_id="m26_noise_blood",
            longitudinal_relation=LongitudinalRelation.UNRELATED,
            knowledge_effect=KnowledgeEffect(),
            semantic_family="noise_contrast",
            falsification_tags=("F1",),
        ),
        # Cross-family noise: plan trip vs colleague trip (similar "上海出差")
        GoldAnnotation(
            pair_id="G15_noise",
            predecessor_id="m01_plan_trip",
            successor_id="m19_colleague_trip",
            longitudinal_relation=LongitudinalRelation.UNRELATED,
            knowledge_effect=KnowledgeEffect(),
            semantic_family="noise_contrast",
            falsification_tags=("F1",),
        ),
    )
