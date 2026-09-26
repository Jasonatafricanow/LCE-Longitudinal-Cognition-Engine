"""Fresh confirmatory heldout corpus for Issue #26.

Completely new adversarial cases, never seen during Issue #25 development.
14 semantic families including the 2 additional families required by Issue #26:
  13. weak lexical overlap but strong longitudinal continuity
  14. strong lexical overlap but no longitudinal relation

No paraphrases of Issue #25 cases. Different life domains, different entities.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from research.experiments.path_b_production_issue_25.contracts import (
    GoldAnnotation,
    KnowledgeEffect,
    LongitudinalRelation,
    ProductionMemoryView,
    TemporalCoordinates,
)

_BASE = datetime(2026, 9, 1, 8, 0, tzinfo=UTC)


def _t(days: int, hours: int = 0) -> datetime:
    return _BASE + timedelta(days=days, hours=hours)


def build_heldout_corpus() -> tuple[ProductionMemoryView, ...]:
    """Build the fresh heldout corpus. Sorted by received_at."""
    return tuple(sorted(_ALL, key=lambda v: v.temporal.received_at))


# ===================================================================
# Family 1: future plan → completed
# ===================================================================

_H01_PLAN = ProductionMemoryView(
    memory_id="h01_marathon_plan",
    content="我报名了十一月的杭州马拉松，目标是跑进四小时",
    source_refs=("ev_h01",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(0), received_at=_t(0, 1),
        semantic_time=_t(60),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)
_H01_DONE = ProductionMemoryView(
    memory_id="h02_marathon_done",
    content="马拉松跑完了，3小时52分，达标了！",
    source_refs=("ev_h02",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(60, 8), received_at=_t(60, 9),
        semantic_time=_t(60),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

# ===================================================================
# Family 2: future plan → failed
# ===================================================================

_H03_PLAN = ProductionMemoryView(
    memory_id="h03_cert_plan",
    content="我打算年底考PMP认证，已经报了培训班",
    source_refs=("ev_h03",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(2), received_at=_t(2, 1),
        semantic_time=_t(90),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)
_H03_FAIL = ProductionMemoryView(
    memory_id="h04_cert_fail",
    content="PMP没过，差了十几分，培训班的模拟题和真题差距太大",
    source_refs=("ev_h04",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(92), received_at=_t(92, 1),
        semantic_time=_t(92),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

# ===================================================================
# Family 3: future plan → cancelled externally
# ===================================================================

_H05_PLAN = ProductionMemoryView(
    memory_id="h05_concert_plan",
    content="买了下月的演唱会门票，终于能现场看偶像了",
    source_refs=("ev_h05",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(3), received_at=_t(3, 1),
        semantic_time=_t(30),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)
_H05_CANCEL = ProductionMemoryView(
    memory_id="h06_concert_cancel",
    content="演唱会主办方宣布延期了，退票流程好麻烦",
    source_refs=("ev_h06",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(20), received_at=_t(20, 1),
        semantic_time=_t(30),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

# ===================================================================
# Family 4: possibility → confirmed
# ===================================================================

_H07_POSS = ProductionMemoryView(
    memory_id="h07_promotion_rumor",
    content="组里传言年底可能有一批晋升名额，但还不确定",
    source_refs=("ev_h07",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(5), received_at=_t(5, 1),
        semantic_time=_t(5),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)
_H07_CONF = ProductionMemoryView(
    memory_id="h08_promotion_confirmed",
    content="晋升名单公布了，我在列！从P6升到P7",
    source_refs=("ev_h08",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(85), received_at=_t(85, 1),
        semantic_time=_t(85),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

# ===================================================================
# Family 5: possibility → disproven
# ===================================================================

_H09_POSS = ProductionMemoryView(
    memory_id="h09_office_move_rumor",
    content="听说公司可能搬到新CBD大楼，离我家远了好多",
    source_refs=("ev_h09",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(7), received_at=_t(7, 1),
        semantic_time=_t(7),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)
_H09_DISPROVE = ProductionMemoryView(
    memory_id="h10_office_stay",
    content="行政部确认不搬了，新大楼租金谈崩了",
    source_refs=("ev_h10",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(40), received_at=_t(40, 1),
        semantic_time=_t(40),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

# ===================================================================
# Family 6: unresolved → resolved by later evidence
# ===================================================================

_H11_UNRESOLVED = ProductionMemoryView(
    memory_id="h11_loan_pending",
    content="房贷申请交上去了，银行说要审核，不知道利率能批多少",
    source_refs=("ev_h11",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(10), received_at=_t(10, 1),
        semantic_time=_t(10),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)
_H11_RESOLVED = ProductionMemoryView(
    memory_id="h12_loan_approved",
    content="房贷批了，利率3.65%，比预期低一点",
    source_refs=("ev_h12",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(25), received_at=_t(25, 1),
        semantic_time=_t(25),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

# ===================================================================
# Family 7: world state change
# ===================================================================

_H13_STATE = ProductionMemoryView(
    memory_id="h13_single",
    content="我目前单身，最近也没什么认识新朋友的机会",
    source_refs=("ev_h13",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(1), received_at=_t(1, 1),
        semantic_time=_t(1),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)
_H13_CHANGE = ProductionMemoryView(
    memory_id="h14_relationship",
    content="交了个女朋友，上周末在朋友聚会上认识的",
    source_refs=("ev_h14",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(45), received_at=_t(45, 1),
        semantic_time=_t(45),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

# ===================================================================
# Family 8: correction/retraction
# ===================================================================

_H15_ORIGINAL = ProductionMemoryView(
    memory_id="h15_flight_info",
    content="航班是明天早上八点半的CA1234",
    source_refs=("ev_h15",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(12), received_at=_t(12, 1),
        semantic_time=_t(13),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)
_H15_CORRECT = ProductionMemoryView(
    memory_id="h16_flight_correction",
    content="刚才说错了，不是CA1234是CA1235，起飞时间也改成九点了",
    source_refs=("ev_h16",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(12, 4), received_at=_t(12, 5),
        semantic_time=_t(13),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

# ===================================================================
# Family 9: persistence without resolution
# ===================================================================

_H17_PENDING = ProductionMemoryView(
    memory_id="h17_patent_pending",
    content="专利申请递交了，审查周期可能要一年多",
    source_refs=("ev_h17",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(4), received_at=_t(4, 1),
        semantic_time=_t(4),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)
_H17_STILL = ProductionMemoryView(
    memory_id="h18_patent_still_pending",
    content="专利还在审查中，问了代理人说还要再等几个月",
    source_refs=("ev_h18",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(50), received_at=_t(50, 1),
        semantic_time=_t(50),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

# ===================================================================
# Family 10: semantically similar but unrelated
# ===================================================================

_H19_SIM = ProductionMemoryView(
    memory_id="h19_friend_marathon",
    content="同事李明也报了杭州马拉松，他跑过三次了",
    source_refs=("ev_h19",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(0, 3), received_at=_t(0, 4),
        semantic_time=_t(0),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)
_H20_SIM = ProductionMemoryView(
    memory_id="h20_past_marathon",
    content="去年参加了北京马拉松，跑了4小时15分",
    source_refs=("ev_h20",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(1, 5), received_at=_t(1, 6),
        semantic_time=_t(-365),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

# ===================================================================
# Family 11: late-arriving past fact
# ===================================================================

_H21_EARLIER = ProductionMemoryView(
    memory_id="h21_never_cooked",
    content="我不太会做饭，基本上都是外卖或者食堂",
    source_refs=("ev_h21",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(6), received_at=_t(6, 1),
        semantic_time=_t(6),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)
_H21_LATE = ProductionMemoryView(
    memory_id="h22_actually_chef",
    content="其实我大学时候在餐厅后厨打过两年工，只是毕业后就没再做过",
    source_refs=("ev_h22",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(15), received_at=_t(15, 1),
        semantic_time=_t(-1460),  # ~4 years ago
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

# ===================================================================
# Family 12: future proposition known now
# ===================================================================

_H23_FUTURE = ProductionMemoryView(
    memory_id="h23_lease_end",
    content="租约到明年三月底到期，已经确定了",
    source_refs=("ev_h23",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(8), received_at=_t(8, 1),
        semantic_time=_t(8),
        valid_start=_t(8), valid_end=_t(210),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)
_H23_CHANGE = ProductionMemoryView(
    memory_id="h24_lease_early_termination",
    content="房东同意提前解约，下个月底就能搬走了",
    source_refs=("ev_h24",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(30), received_at=_t(30, 1),
        semantic_time=_t(30),
        valid_start=_t(30), valid_end=_t(60),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

# ===================================================================
# Family 13 (NEW): weak lexical overlap but strong longitudinal continuity
# ===================================================================

_H25_WEAK_LEX = ProductionMemoryView(
    memory_id="h25_symptoms",
    content="这几天一直咳嗽，嗓子不舒服，吃了点含片",
    source_refs=("ev_h25",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(9), received_at=_t(9, 1),
        semantic_time=_t(9),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)
_H25_DIAGNOSIS = ProductionMemoryView(
    memory_id="h26_diagnosis",
    content="去医院看了，大夫说是支原体感染，开了阿奇霉素",
    source_refs=("ev_h26",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(12, 8), received_at=_t(12, 9),
        semantic_time=_t(12),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

# ===================================================================
# Family 14 (NEW): strong lexical overlap but no longitudinal relation
# ===================================================================

_H27_STRONG_LEX = ProductionMemoryView(
    memory_id="h27_recipe_chicken",
    content="今天试了个新菜谱，做了香辣鸡翅，味道不错",
    source_refs=("ev_h27",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(11), received_at=_t(11, 1),
        semantic_time=_t(11),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)
_H28_STRONG_LEX = ProductionMemoryView(
    memory_id="h28_recipe_shrimp",
    content="又试了一个新菜谱，蒜蓉大虾，比上次那个鸡翅更好吃",
    source_refs=("ev_h28",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(18), received_at=_t(18, 1),
        semantic_time=_t(18),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

# ===================================================================
# Additional noise blocks
# ===================================================================

_NOISE_H1 = ProductionMemoryView(
    memory_id="h29_noise_run",
    content="今天跑了五公里，天气不错适合运动",
    source_refs=("ev_h29",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(3, 6), received_at=_t(3, 7),
        semantic_time=_t(3),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

_NOISE_H2 = ProductionMemoryView(
    memory_id="h30_noise_flight",
    content="帮同事查了个去深圳的航班信息",
    source_refs=("ev_h30",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(12, 6), received_at=_t(12, 7),
        semantic_time=_t(12),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

_NOISE_H3 = ProductionMemoryView(
    memory_id="h31_noise_patent",
    content="看了一篇关于专利法改革的文章，和我的申请没什么关系",
    source_refs=("ev_h31",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(14), received_at=_t(14, 1),
        semantic_time=_t(14),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

_NOISE_H4 = ProductionMemoryView(
    memory_id="h32_noise_cook",
    content="路过一个烹饪学校的广告，看了一眼就走了",
    source_refs=("ev_h32",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(16), received_at=_t(16, 1),
        semantic_time=_t(16),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)

_NOISE_H5 = ProductionMemoryView(
    memory_id="h33_noise_promotion",
    content="读了一篇关于职场晋升策略的公众号文章",
    source_refs=("ev_h33",),
    temporal=TemporalCoordinates(
        source_occurred_at=_t(6, 6), received_at=_t(6, 7),
        semantic_time=_t(6),
    ),
    provenance={"source_type": "user_message", "channel": "chat"},
)


# ---------------------------------------------------------------------------
_ALL = [
    _H01_PLAN, _H01_DONE,
    _H03_PLAN, _H03_FAIL,
    _H05_PLAN, _H05_CANCEL,
    _H07_POSS, _H07_CONF,
    _H09_POSS, _H09_DISPROVE,
    _H11_UNRESOLVED, _H11_RESOLVED,
    _H13_STATE, _H13_CHANGE,
    _H15_ORIGINAL, _H15_CORRECT,
    _H17_PENDING, _H17_STILL,
    _H19_SIM, _H20_SIM,
    _H21_EARLIER, _H21_LATE,
    _H23_FUTURE, _H23_CHANGE,
    _H25_WEAK_LEX, _H25_DIAGNOSIS,
    _H27_STRONG_LEX, _H28_STRONG_LEX,
    _NOISE_H1, _NOISE_H2, _NOISE_H3, _NOISE_H4, _NOISE_H5,
]


# ===================================================================
# Gold annotations (never consumed by the pipeline)
# ===================================================================

def build_heldout_gold() -> tuple[GoldAnnotation, ...]:
    return (
        # F1: plan → completed
        GoldAnnotation(
            pair_id="HG01", predecessor_id="h01_marathon_plan",
            successor_id="h02_marathon_done",
            longitudinal_relation=LongitudinalRelation.STATE_CHANGE,
            knowledge_effect=KnowledgeEffect(prior_unknown_resolved=True,
                                              resolved_dimensions=("marathon_completion",)),
            semantic_family="F1_plan_completed",
        ),
        # F2: plan → failed
        GoldAnnotation(
            pair_id="HG02", predecessor_id="h03_cert_plan",
            successor_id="h04_cert_fail",
            longitudinal_relation=LongitudinalRelation.STATE_CHANGE,
            knowledge_effect=KnowledgeEffect(prior_unknown_resolved=True,
                                              resolved_dimensions=("cert_outcome",)),
            semantic_family="F2_plan_failed",
        ),
        # F3: plan → cancelled
        GoldAnnotation(
            pair_id="HG03", predecessor_id="h05_concert_plan",
            successor_id="h06_concert_cancel",
            longitudinal_relation=LongitudinalRelation.STATE_CHANGE,
            knowledge_effect=KnowledgeEffect(prior_unknown_resolved=True,
                                              resolved_dimensions=("concert_happening",)),
            semantic_family="F3_plan_cancelled",
        ),
        # F4: possibility → confirmed
        GoldAnnotation(
            pair_id="HG04", predecessor_id="h07_promotion_rumor",
            successor_id="h08_promotion_confirmed",
            longitudinal_relation=LongitudinalRelation.STATE_CHANGE,
            knowledge_effect=KnowledgeEffect(prior_unknown_resolved=True,
                                              resolved_dimensions=("promotion_outcome",)),
            semantic_family="F4_confirmed",
        ),
        # F5: possibility → disproven
        GoldAnnotation(
            pair_id="HG05", predecessor_id="h09_office_move_rumor",
            successor_id="h10_office_stay",
            longitudinal_relation=LongitudinalRelation.STATE_CHANGE,
            knowledge_effect=KnowledgeEffect(prior_unknown_resolved=True,
                                              resolved_dimensions=("office_location",)),
            semantic_family="F5_disproven",
        ),
        # F6: unresolved → resolved
        GoldAnnotation(
            pair_id="HG06", predecessor_id="h11_loan_pending",
            successor_id="h12_loan_approved",
            longitudinal_relation=LongitudinalRelation.STATE_CHANGE,
            knowledge_effect=KnowledgeEffect(prior_unknown_resolved=True,
                                              resolved_dimensions=("loan_approval",)),
            semantic_family="F6_resolved",
        ),
        # F7: world state change
        GoldAnnotation(
            pair_id="HG07", predecessor_id="h13_single",
            successor_id="h14_relationship",
            longitudinal_relation=LongitudinalRelation.STATE_CHANGE,
            knowledge_effect=KnowledgeEffect(prior_unknown_resolved=False),
            semantic_family="F7_state_change",
        ),
        # F8: correction
        GoldAnnotation(
            pair_id="HG08", predecessor_id="h15_flight_info",
            successor_id="h16_flight_correction",
            longitudinal_relation=LongitudinalRelation.CORRECTION_RETRACTION,
            knowledge_effect=KnowledgeEffect(prior_unknown_resolved=False),
            semantic_family="F8_correction",
        ),
        # F9: persistence
        GoldAnnotation(
            pair_id="HG09", predecessor_id="h17_patent_pending",
            successor_id="h18_patent_still_pending",
            longitudinal_relation=LongitudinalRelation.PERSISTENCE_CONFIRMATION,
            knowledge_effect=KnowledgeEffect(prior_unknown_resolved=False),
            semantic_family="F9_persistence",
        ),
        # F10: similar but unrelated
        GoldAnnotation(
            pair_id="HG10", predecessor_id="h19_friend_marathon",
            successor_id="h20_past_marathon",
            longitudinal_relation=LongitudinalRelation.UNRELATED,
            knowledge_effect=KnowledgeEffect(),
            semantic_family="F10_unrelated_similar",
        ),
        # F11: late fact corrects earlier claim
        GoldAnnotation(
            pair_id="HG11", predecessor_id="h21_never_cooked",
            successor_id="h22_actually_chef",
            longitudinal_relation=LongitudinalRelation.CORRECTION_RETRACTION,
            knowledge_effect=KnowledgeEffect(prior_unknown_resolved=True,
                                              resolved_dimensions=("cooking_history",)),
            semantic_family="F11_late_fact",
        ),
        # F12: future proposition changed
        GoldAnnotation(
            pair_id="HG12", predecessor_id="h23_lease_end",
            successor_id="h24_lease_early_termination",
            longitudinal_relation=LongitudinalRelation.STATE_CHANGE,
            knowledge_effect=KnowledgeEffect(prior_unknown_resolved=False),
            semantic_family="F12_future_changed",
        ),
        # F13: weak lexical, strong longitudinal (symptoms → diagnosis)
        GoldAnnotation(
            pair_id="HG13", predecessor_id="h25_symptoms",
            successor_id="h26_diagnosis",
            longitudinal_relation=LongitudinalRelation.STATE_CHANGE,
            knowledge_effect=KnowledgeEffect(prior_unknown_resolved=True,
                                              resolved_dimensions=("health_diagnosis",)),
            semantic_family="F13_weak_lexical_strong_relation",
        ),
        # F14: strong lexical, no longitudinal relation
        GoldAnnotation(
            pair_id="HG14", predecessor_id="h27_recipe_chicken",
            successor_id="h28_recipe_shrimp",
            longitudinal_relation=LongitudinalRelation.UNRELATED,
            knowledge_effect=KnowledgeEffect(),
            semantic_family="F14_strong_lexical_no_relation",
        ),
        # Noise contrast: marathon plan vs friend's marathon
        GoldAnnotation(
            pair_id="HG15_noise", predecessor_id="h01_marathon_plan",
            successor_id="h19_friend_marathon",
            longitudinal_relation=LongitudinalRelation.UNRELATED,
            knowledge_effect=KnowledgeEffect(),
            semantic_family="noise_contrast",
        ),
        # Noise contrast: flight info vs colleague's flight
        GoldAnnotation(
            pair_id="HG16_noise", predecessor_id="h15_flight_info",
            successor_id="h30_noise_flight",
            longitudinal_relation=LongitudinalRelation.UNRELATED,
            knowledge_effect=KnowledgeEffect(),
            semantic_family="noise_contrast",
        ),
        # Noise contrast: patent pending vs patent article
        GoldAnnotation(
            pair_id="HG17_noise", predecessor_id="h17_patent_pending",
            successor_id="h31_noise_patent",
            longitudinal_relation=LongitudinalRelation.UNRELATED,
            knowledge_effect=KnowledgeEffect(),
            semantic_family="noise_contrast",
        ),
        # Noise contrast: cooking history vs cooking school ad
        GoldAnnotation(
            pair_id="HG18_noise", predecessor_id="h21_never_cooked",
            successor_id="h32_noise_cook",
            longitudinal_relation=LongitudinalRelation.UNRELATED,
            knowledge_effect=KnowledgeEffect(),
            semantic_family="noise_contrast",
        ),
    )
