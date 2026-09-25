"""Corpus and Gold Relation Builder for Issue #24.

Builds:
- data/corpus_blocks.jsonl (60 SemanticBlocks with deterministic timestamps and projections)
- data/gold_relations.jsonl (70 gold pairs covering all 6 relations, 10 families, and F1-F5 falsification probes)
- data/splits.json (Dev: 6 domains, Held-Out: 4 domains)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

CORPUS_FILE = DATA_DIR / "corpus_blocks.jsonl"
GOLD_FILE = DATA_DIR / "gold_relations.jsonl"
SPLITS_FILE = DATA_DIR / "splits.json"


def dt(iso_str: str) -> datetime:
    return datetime.fromisoformat(iso_str).astimezone(UTC)


def make_block(
    block_id: str,
    content: str,
    start: str,
    end: str,
    domain: str,
    thread_id: str,
    source_attribution: dict,
    epistemic_commitment: str,
    action_or_state: dict,
    localized_unknowns: list[str],
    communicative_act: str,
    polarity: str,
    condition: dict,
    revision_retraction: dict,
    entity_anchors: dict,
) -> dict:
    return {
        "block_id": block_id,
        "content": content,
        "occurred_start": dt(start).isoformat(),
        "occurred_end": dt(end).isoformat(),
        "domain": domain,
        "thread_id": thread_id,
        "raw_evidence_ids": [f"ev_{block_id.lower()}"],
        "compiler_version": "v0.3-issue22",
        "lineage_id": "main",
        "projections": {
            "source_attribution": source_attribution,
            "epistemic_commitment": epistemic_commitment,
            "action_or_state": action_or_state,
            "localized_unknowns": localized_unknowns,
            "communicative_act": communicative_act,
            "polarity": polarity,
            "condition_or_hypothesis": condition,
            "revision_retraction": revision_retraction,
            "entity_role_anchors": entity_anchors,
        },
    }


def make_gold_pair(
    pair_id: str,
    t1: str,
    t2: str,
    relation: str,
    dimension: str,
    unknown_resolved: bool,
    resolved_dim: str | None,
    outcome: str,
    spans: list[str],
    split: str,
    family: str,
    falsification_tags: list[str],
    rejections: dict[str, str],
) -> dict:
    return {
        "pair_id": pair_id,
        "predecessor_block_id": t1,
        "successor_block_id": t2,
        "relation_type": relation,
        "affected_dimension": dimension,
        "prior_unknown_resolved": unknown_resolved,
        "resolved_dimension": resolved_dim,
        "outcome_or_current_state": outcome,
        "gold_evidence_spans": spans,
        "split": split,
        "contrastive_family": family,
        "falsification_tags": falsification_tags,
        "reason_competing_rejections": rejections,
    }


def generate_all():
    blocks = []
    gold = []

    # =========================================================================
    # DOMAIN 1: D1_FLIGHT (Travel & Flight) - DEV
    # =========================================================================
    # t1: requirement
    blocks.append(make_block(
        "B_FLIGHT_01",
        "我今天必须赶杭州到北京的飞机。",
        "2026-10-01T08:00:00Z", "2026-10-01T08:05:00Z",
        "FLIGHT", "th_flight_01",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "current_requirement_obligation", "summary": "用户必须赶今天杭州到北京的航班"},
        ["最终是否按时登机", "是否顺利起飞到达"],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["用户"], "target_recipient": [], "affected_object": ["飞机航班"], "destination_or_location": ["杭州", "北京"], "key_entities": ["航班", "杭州", "北京"]},
    ))
    # t2_success: uncertainty resolution (success)
    blocks.append(make_block(
        "B_FLIGHT_02_SUCC",
        "赶上了，已经坐到座位上了。",
        "2026-10-01T11:30:00Z", "2026-10-01T11:32:00Z",
        "FLIGHT", "th_flight_01",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "completed_past", "summary": "用户顺利赶上飞机并就座"},
        [],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["用户"], "target_recipient": [], "affected_object": ["飞机座位"], "destination_or_location": ["机舱"], "key_entities": ["座位", "飞机"]},
    ))
    # t2_fail: uncertainty resolution (failure)
    blocks.append(make_block(
        "B_FLIGHT_02_FAIL",
        "路上堵死了，最后没赶上飞机。",
        "2026-10-01T11:30:00Z", "2026-10-01T11:32:00Z",
        "FLIGHT", "th_flight_01",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "completed_past", "summary": "因严重堵车导致未能赶上飞机"},
        [],
        "assertion", "negative",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["用户"], "target_recipient": [], "affected_object": ["航班"], "destination_or_location": ["路上", "机场"], "key_entities": ["堵车", "飞机"]},
    ))
    # t2_cancel: uncertainty resolution (cancellation)
    blocks.append(make_block(
        "B_FLIGHT_02_CANCEL",
        "机场发来紧急短信，因为暴雨该航班已被官方取消。",
        "2026-10-01T09:30:00Z", "2026-10-01T09:35:00Z",
        "FLIGHT", "th_flight_01",
        {"speaker": "user", "reported_source": "机场短信", "user_endorsement": "endorsed"},
        "certain",
        {"status": "cancelled_retracted", "summary": "暴雨导致航班被官方取消"},
        [],
        "assertion", "negative",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["机场官方"], "target_recipient": ["用户"], "affected_object": ["航班"], "destination_or_location": ["杭州机场"], "key_entities": ["暴雨", "取消", "航班"]},
    ))
    # t2_state_change: world state change
    blocks.append(make_block(
        "B_FLIGHT_02_CHANGE",
        "刚收到航司通知，航班延期改到今晚九点起飞了。",
        "2026-10-01T09:40:00Z", "2026-10-01T09:42:00Z",
        "FLIGHT", "th_flight_01",
        {"speaker": "user", "reported_source": "航司通知", "user_endorsement": "endorsed"},
        "certain",
        {"status": "intention_plan", "summary": "航班时间调整至今晚九点"},
        ["最终是否按新时间起飞"],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": True, "retracted_target": "原定起飞时间", "correction_nature": "external_state_change"},
        {"actor_agent": ["航空公司"], "target_recipient": ["用户"], "affected_object": ["航班时刻"], "destination_or_location": ["杭州", "北京"], "key_entities": ["延期", "今晚九点", "航班"]},
    ))
    # t2_correction: correction retraction
    blocks.append(make_block(
        "B_FLIGHT_02_CORR",
        "我刚才口误说错了，不是飞北京，其实是飞深圳。",
        "2026-10-01T08:10:00Z", "2026-10-01T08:12:00Z",
        "FLIGHT", "th_flight_01",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "cancelled_retracted", "summary": "用户纠正此前口误，实际目的地是深圳而非北京"},
        [],
        "correction_retraction", "mixed_contrastive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": True, "retracted_target": "目的地北京", "correction_nature": "speaker_slip_repair"},
        {"actor_agent": ["用户"], "target_recipient": [], "affected_object": ["航班目的地"], "destination_or_location": ["深圳"], "key_entities": ["口误", "深圳", "北京"]},
    ))
    # t2_persist: persistence
    blocks.append(make_block(
        "B_FLIGHT_02_PERSIST",
        "现在还在高架上死堵着，依然不知道能不能赶上。",
        "2026-10-01T10:00:00Z", "2026-10-01T10:02:00Z",
        "FLIGHT", "th_flight_01",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "probable",
        {"status": "current_requirement_obligation", "summary": "仍然处于堵车途中，赶飞机结果仍未明朗"},
        ["最终是否按时登机"],
        "assertion", "mixed_contrastive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["用户"], "target_recipient": [], "affected_object": ["行程进展"], "destination_or_location": ["高架路"], "key_entities": ["死堵", "赶上", "高架"]},
    ))
    # t2_unrelated: distractor
    blocks.append(make_block(
        "B_FLIGHT_02_UNRELATED",
        "下周去上海的高铁票我已经买好了。",
        "2026-10-01T12:00:00Z", "2026-10-01T12:05:00Z",
        "FLIGHT", "th_flight_02",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "completed_past", "summary": "购买了下周赴上海的高铁票"},
        [],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["用户"], "target_recipient": [], "affected_object": ["高铁票"], "destination_or_location": ["上海"], "key_entities": ["上海", "高铁票"]},
    ))
    # t2_elapsed_no_ev: elapsed time without evidence (F3 probe)
    blocks.append(make_block(
        "B_FLIGHT_02_ELAPSED_NO_EV",
        "今天北京的天气据说是晴天。",
        "2026-10-05T08:00:00Z", "2026-10-05T08:02:00Z",
        "FLIGHT", "th_flight_01",
        {"speaker": "user", "reported_source": "天气预报", "user_endorsement": "endorsed"},
        "probable",
        {"status": "state_observation", "summary": "北京天气晴天"},
        [],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["用户"], "target_recipient": [], "affected_object": ["天气"], "destination_or_location": ["北京"], "key_entities": ["天气", "晴天", "北京"]},
    ))

    # Gold pairs for Flight:
    gold.append(make_gold_pair(
        "GP_FLIGHT_01", "B_FLIGHT_01", "B_FLIGHT_02_SUCC",
        "UNCERTAINTY_RESOLUTION", "eventual_boarding", True, "最终是否按时登机",
        "成功赶上飞机并就座", ["赶上了，已经坐到座位上了"], "dev", "requirement_to_success", ["F2_NO_MUTATION"],
        {"STATE_CHANGE": "计划并未变更，而是最初的不确定性得到事实终结", "CORRECTION_RETRACTION": "原初需求完全真实，无表述错误", "PERSISTENCE_CONFIRMATION": "状态已由未知变为明确结果"}
    ))
    gold.append(make_gold_pair(
        "GP_FLIGHT_02", "B_FLIGHT_01", "B_FLIGHT_02_FAIL",
        "UNCERTAINTY_RESOLUTION", "eventual_boarding", True, "最终是否按时登机",
        "未能赶上飞机", ["路上堵死了，最后没赶上飞机"], "dev", "requirement_to_failure", ["F2_NO_MUTATION"],
        {"STATE_CHANGE": "非主观计划调整，而是执行结果确证失败", "CORRECTION_RETRACTION": "前序需求真实存在，无口误", "PERSISTENCE_CONFIRMATION": "已明确产生终局失败结果"}
    ))
    gold.append(make_gold_pair(
        "GP_FLIGHT_03", "B_FLIGHT_01", "B_FLIGHT_02_CANCEL",
        "UNCERTAINTY_RESOLUTION", "flight_operation_status", True, "是否顺利起飞到达",
        "航班被官方取消", ["因为暴雨该航班已被官方取消"], "dev", "requirement_to_cancellation", ["F2_NO_MUTATION"],
        {"STATE_CHANGE": "属于外部事实对不确定维度的闭合", "CORRECTION_RETRACTION": "前序认知真实有效"}
    ))
    gold.append(make_gold_pair(
        "GP_FLIGHT_04", "B_FLIGHT_01", "B_FLIGHT_02_CHANGE",
        "STATE_CHANGE", "schedule_time", False, None,
        "起飞时间由原定改至今晚九点", ["航班延期改到今晚九点起飞了"], "dev", "plan_changed", ["F4_STATE_VS_CORRECTION"],
        {"CORRECTION_RETRACTION": "此前时刻真实有效，系航司后续事实变更而非用户口误", "UNCERTAINTY_RESOLUTION": "事件仍处于计划态未终结"}
    ))
    gold.append(make_gold_pair(
        "GP_FLIGHT_05", "B_FLIGHT_01", "B_FLIGHT_02_CORR",
        "CORRECTION_RETRACTION", "destination_city", False, None,
        "目的地纠正为深圳，前序北京系口误", ["我刚才口误说错了，不是飞北京，其实是飞深圳"], "dev", "statement_corrected", ["F4_STATE_VS_CORRECTION"],
        {"STATE_CHANGE": "现实目的地从未发生变迁，系前序认知陈述出现错误", "UNCERTAINTY_RESOLUTION": "非结果敲定，而是认知撤回修复"}
    ))
    gold.append(make_gold_pair(
        "GP_FLIGHT_06", "B_FLIGHT_01", "B_FLIGHT_02_PERSIST",
        "PERSISTENCE_CONFIRMATION", "boarding_uncertainty", False, None,
        "堵车中，能否赶上依然悬而未决", ["依然不知道能不能赶上"], "dev", "persisted_unresolved", [],
        {"UNCERTAINTY_RESOLUTION": "未知维度依然敞开，未获得结果关闭", "STATE_CHANGE": "初始状态持续延续，未发生质变"}
    ))
    gold.append(make_gold_pair(
        "GP_FLIGHT_07", "B_FLIGHT_01", "B_FLIGHT_02_UNRELATED",
        "UNRELATED", "none", False, None,
        "完全无关的上海高铁票购买", [], "dev", "temporal_distractor_unrelated", ["F1_TIME_INSUFFICIENT"],
        {"UNCERTAINTY_RESOLUTION": "分属完全独立的旅行客体", "STATE_CHANGE": "无共享实体演化关系"}
    ))
    gold.append(make_gold_pair(
        "GP_FLIGHT_08", "B_FLIGHT_01", "B_FLIGHT_02_ELAPSED_NO_EV",
        "UNKNOWN_RELATION", "eventual_boarding", False, None,
        "经历多日后提及北京天气，但无任何证据表明该航班最终是否赶上", [], "dev", "elapsed_time_no_evidence", ["F3_UNKNOWN_CLOSES_ONLY_WITH_EVIDENCE"],
        {"UNCERTAINTY_RESOLUTION": "绝无新证据闭合航班赶上与否，时间流逝不可制造知识", "STATE_CHANGE": "无状态转移证据"}
    ))

    # =========================================================================
    # DOMAIN 2: D2_REPORT (Executive Report Submission) - DEV
    # =========================================================================
    blocks.append(make_block(
        "B_REPORT_01",
        "这个季度总结报告我今天下班前必须提交给王总。",
        "2026-10-02T09:00:00Z", "2026-10-02T09:05:00Z",
        "REPORT", "th_report_01",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "current_requirement_obligation", "summary": "下班前须提交季度报告给王总"},
        ["是否在下班前提交完成", "王总是否验收接收"],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["用户"], "target_recipient": ["王总"], "affected_object": ["季度总结报告"], "destination_or_location": ["公司"], "key_entities": ["季度总结报告", "王总", "下班前"]},
    ))
    blocks.append(make_block(
        "B_REPORT_02_SUCC",
        "报告刚才已经通过邮件发给王总了，他也回邮件确认收到了。",
        "2026-10-02T16:30:00Z", "2026-10-02T16:35:00Z",
        "REPORT", "th_report_01",
        {"speaker": "user", "reported_source": "王总回信", "user_endorsement": "direct"},
        "certain",
        {"status": "completed_past", "summary": "已邮件提交报告并获王总确认接收"},
        [],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["用户"], "target_recipient": ["王总"], "affected_object": ["季度总结报告"], "destination_or_location": ["邮件"], "key_entities": ["王总", "确认收到", "报告"]},
    ))
    blocks.append(make_block(
        "B_REPORT_02_FAIL",
        "办公电脑主板突然烧了，文件没备份，今天肯定交不上去了。",
        "2026-10-02T16:00:00Z", "2026-10-02T16:05:00Z",
        "REPORT", "th_report_01",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "completed_past", "summary": "电脑硬件损坏且无备份，今日提交失败确证"},
        [],
        "assertion", "negative",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["用户"], "target_recipient": ["王总"], "affected_object": ["电脑主板", "报告文件"], "destination_or_location": ["工位"], "key_entities": ["电脑烧了", "交不上", "报告"]},
    ))
    blocks.append(make_block(
        "B_REPORT_02_CHANGE",
        "王总刚在群里通知，季度总结提交时间统一顺延到下周一上午。",
        "2026-10-02T14:00:00Z", "2026-10-02T14:05:00Z",
        "REPORT", "th_report_01",
        {"speaker": "user", "reported_source": "王总群通知", "user_endorsement": "endorsed"},
        "certain",
        {"status": "intention_plan", "summary": "报告提交截止时间调整至下周一上午"},
        ["下周一能否顺利提交"],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": True, "retracted_target": "今天下班前的截止时间", "correction_nature": "external_state_change"},
        {"actor_agent": ["王总"], "target_recipient": ["团队"], "affected_object": ["报告提交截止时间"], "destination_or_location": ["群通知"], "key_entities": ["顺延", "下周一", "季度总结"]},
    ))
    blocks.append(make_block(
        "B_REPORT_02_CORR",
        "我刚才脑子懵了说错了，下班前要交的不是季度报告，是差旅报销单。",
        "2026-10-02T09:15:00Z", "2026-10-02T09:18:00Z",
        "REPORT", "th_report_01",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "cancelled_retracted", "summary": "更正前序口误，今日截止事项实为差旅报销而非季度报告"},
        [],
        "correction_retraction", "mixed_contrastive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": True, "retracted_target": "提交事项为季度总结报告", "correction_nature": "speaker_slip_repair"},
        {"actor_agent": ["用户"], "target_recipient": ["王总"], "affected_object": ["差旅报销单"], "destination_or_location": ["工位"], "key_entities": ["说错了", "差旅报销单", "季度报告"]},
    ))
    blocks.append(make_block(
        "B_REPORT_02_PERSIST",
        "还在等财务部门同步最后两组核心数据，报告现在还没法最终提交。",
        "2026-10-02T15:00:00Z", "2026-10-02T15:03:00Z",
        "REPORT", "th_report_01",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "probable",
        {"status": "current_requirement_obligation", "summary": "仍在等待数据补充，报告依然处于待提交阻塞状态"},
        ["财务数据何时提供", "能否在下班前提交完成"],
        "assertion", "mixed_contrastive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["用户"], "target_recipient": ["财务部门"], "affected_object": ["财务数据", "报告"], "destination_or_location": ["工位"], "key_entities": ["还在等", "没法提交", "财务数据"]},
    ))
    blocks.append(make_block(
        "B_REPORT_02_UNRELATED",
        "张助理刚才送来了这周的办公室绿植养护表。",
        "2026-10-02T11:00:00Z", "2026-10-02T11:02:00Z",
        "REPORT", "th_report_02",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "completed_past", "summary": "接收绿植养护表"},
        [],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["张助理"], "target_recipient": ["用户"], "affected_object": ["绿植养护表"], "destination_or_location": ["办公室"], "key_entities": ["张助理", "绿植养护表"]},
    ))

    gold.append(make_gold_pair(
        "GP_REPORT_01", "B_REPORT_01", "B_REPORT_02_SUCC",
        "UNCERTAINTY_RESOLUTION", "submission_outcome", True, "是否在下班前提交完成",
        "成功完成报告提交并获确认", ["报告刚才已经通过邮件发给王总了"], "dev", "requirement_to_success", ["F2_NO_MUTATION"],
        {"STATE_CHANGE": "目标如期达成关闭未知，非条件流转", "CORRECTION_RETRACTION": "原先交付需求真实正确"}
    ))
    gold.append(make_gold_pair(
        "GP_REPORT_02", "B_REPORT_01", "B_REPORT_02_FAIL",
        "UNCERTAINTY_RESOLUTION", "submission_outcome", True, "是否在下班前提交完成",
        "硬件损坏导致提交确定失败", ["办公电脑主板突然烧了", "今天肯定交不上去了"], "dev", "requirement_to_failure", ["F2_NO_MUTATION"],
        {"STATE_CHANGE": "客观阻碍闭合为失败事实，非主动调整", "CORRECTION_RETRACTION": "早前目标非虚假"}
    ))
    gold.append(make_gold_pair(
        "GP_REPORT_03", "B_REPORT_01", "B_REPORT_02_CHANGE",
        "STATE_CHANGE", "submission_deadline", False, None,
        "交付截止点被通知延期至下周一", ["王总刚在群里通知", "统一顺延到下周一上午"], "dev", "plan_changed", ["F4_STATE_VS_CORRECTION"],
        {"CORRECTION_RETRACTION": "原今天下班前确为当时政策，系外部通知改期而非口误", "UNCERTAINTY_RESOLUTION": "下周一前是否交付仍未知"}
    ))
    gold.append(make_gold_pair(
        "GP_REPORT_04", "B_REPORT_01", "B_REPORT_02_CORR",
        "CORRECTION_RETRACTION", "delivery_subject", False, None,
        "用户自我纠错：实为差旅报销单而非季度总结", ["我刚才脑子懵了说错了，下班前要交的不是季度报告，是差旅报销单"], "dev", "statement_corrected", ["F4_STATE_VS_CORRECTION"],
        {"STATE_CHANGE": "现实中应交之物始终未变，系陈述者产生误言", "UNCERTAINTY_RESOLUTION": "此操作撤销先前表征"}
    ))
    gold.append(make_gold_pair(
        "GP_REPORT_05", "B_REPORT_01", "B_REPORT_02_PERSIST",
        "PERSISTENCE_CONFIRMATION", "submission_state", False, None,
        "仍等待财务数据，阻滞状态继续维持", ["报告现在还没法最终提交"], "dev", "persisted_unresolved", [],
        {"UNCERTAINTY_RESOLUTION": "尚未产生成败确据", "STATE_CHANGE": "状态同态延展"}
    ))
    gold.append(make_gold_pair(
        "GP_REPORT_06", "B_REPORT_01", "B_REPORT_02_UNRELATED",
        "UNRELATED", "none", False, None,
        "无关行政绿植表事项", [], "dev", "temporal_distractor_unrelated", ["F1_TIME_INSUFFICIENT"],
        {"UNCERTAINTY_RESOLUTION": "客体毫不相干"}
    ))

    # =========================================================================
    # DOMAIN 3: D3_MEETING (Product Launch Meeting) - DEV
    # =========================================================================
    blocks.append(make_block(
        "B_MEETING_01",
        "我们组的产品复盘会定在周二上午十点开。",
        "2026-10-03T10:00:00Z", "2026-10-03T10:05:00Z",
        "MEETING", "th_meeting_01",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "intention_plan", "summary": "复盘会安排在周二上午十点"},
        ["届时是否如期召开", "核心参会人是否出席"],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["产品组"], "target_recipient": ["参会人"], "affected_object": ["产品复盘会"], "destination_or_location": ["会议室"], "key_entities": ["复盘会", "周二上午十点"]},
    ))
    blocks.append(make_block(
        "B_MEETING_02_CHANGE",
        "会议组织人发邮件通知，周二会议室冲突，复盘会改到周三上午十点了。",
        "2026-10-03T15:00:00Z", "2026-10-03T15:05:00Z",
        "MEETING", "th_meeting_01",
        {"speaker": "user", "reported_source": "组织人邮件", "user_endorsement": "endorsed"},
        "certain",
        {"status": "intention_plan", "summary": "复盘会因会议室冲突改期至周三上午十点"},
        ["周三是否如期召开"],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": True, "retracted_target": "周二上午十点的时间安排", "correction_nature": "external_state_change"},
        {"actor_agent": ["会议组织人"], "target_recipient": ["参会人"], "affected_object": ["复盘会时间"], "destination_or_location": ["会议室"], "key_entities": ["改到周三", "复盘会", "会议室冲突"]},
    ))
    blocks.append(make_block(
        "B_MEETING_02_CORR",
        "我刚才记混看错日程了，周二那是运营会的点，复盘会实际一直都是周四。",
        "2026-10-03T10:20:00Z", "2026-10-03T10:25:00Z",
        "MEETING", "th_meeting_01",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "cancelled_retracted", "summary": "用户自我纠正看错日程的失误，复盘会实际为周四"},
        [],
        "correction_retraction", "mixed_contrastive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": True, "retracted_target": "复盘会定在周二的陈述", "correction_nature": "speaker_slip_repair"},
        {"actor_agent": ["用户"], "target_recipient": ["参会人"], "affected_object": ["日程记录"], "destination_or_location": ["日历"], "key_entities": ["看错日程", "实际一直都是周四", "复盘会"]},
    ))
    blocks.append(make_block(
        "B_MEETING_02_SUCC",
        "周二复盘会刚顺利开完了，大家对各模块表现做了充分拆解。",
        "2026-10-06T12:00:00Z", "2026-10-06T12:05:00Z",
        "MEETING", "th_meeting_01",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "completed_past", "summary": "周二复盘会如期举行并圆满结束"},
        [],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["产品组"], "target_recipient": ["参会人"], "affected_object": ["复盘会"], "destination_or_location": ["会议室"], "key_entities": ["顺利开完了", "复盘会"]},
    ))
    blocks.append(make_block(
        "B_MEETING_02_PERSIST",
        "产品复盘会还是维持在周二，目前没有任何调整变动。",
        "2026-10-04T09:00:00Z", "2026-10-04T09:02:00Z",
        "MEETING", "th_meeting_01",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "intention_plan", "summary": "确认会议仍维持周二不变"},
        ["届时是否如期召开"],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["产品组"], "target_recipient": [], "affected_object": ["复盘会日程"], "destination_or_location": ["会议室"], "key_entities": ["维持在周二", "没有变动"]},
    ))
    blocks.append(make_block(
        "B_MEETING_02_UNRELATED",
        "隔壁市场部今天下午正在三楼召开新品发布动员大会。",
        "2026-10-03T14:00:00Z", "2026-10-03T14:05:00Z",
        "MEETING", "th_meeting_02",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "completed_past", "summary": "市场部在三楼举行发布动员会"},
        [],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["市场部"], "target_recipient": ["市场团队"], "affected_object": ["发布动员大会"], "destination_or_location": ["三楼会议室"], "key_entities": ["市场部", "动员大会"]},
    ))

    gold.append(make_gold_pair(
        "GP_MEETING_01", "B_MEETING_01", "B_MEETING_02_CHANGE",
        "STATE_CHANGE", "meeting_time", False, None,
        "因会议室冲突，会议改期至周三", ["复盘会改到周三上午十点了"], "dev", "plan_changed", ["F4_STATE_VS_CORRECTION"],
        {"CORRECTION_RETRACTION": "周二在当时是真实的预订安排，后因冲突改变，非看错日程", "UNCERTAINTY_RESOLUTION": "周三会否照常开依然悬置"}
    ))
    gold.append(make_gold_pair(
        "GP_MEETING_02", "B_MEETING_01", "B_MEETING_02_CORR",
        "CORRECTION_RETRACTION", "meeting_time", False, None,
        "用户澄清看错日程：一直都是周四，周二是运营会", ["我刚才记混看错日程了", "实际一直都是周四"], "dev", "statement_corrected", ["F4_STATE_VS_CORRECTION"],
        {"STATE_CHANGE": "事实日程并未迁移，系主体认知错误纠偏", "UNCERTAINTY_RESOLUTION": "修正先验事实表征"}
    ))
    gold.append(make_gold_pair(
        "GP_MEETING_03", "B_MEETING_01", "B_MEETING_02_SUCC",
        "UNCERTAINTY_RESOLUTION", "meeting_execution", True, "届时是否如期召开",
        "复盘会如期完成召开", ["周二复盘会刚顺利开完了"], "dev", "requirement_to_success", ["F2_NO_MUTATION"],
        {"STATE_CHANGE": "计划原样落实，未发生漂移"}
    ))
    gold.append(make_gold_pair(
        "GP_MEETING_04", "B_MEETING_01", "B_MEETING_02_PERSIST",
        "PERSISTENCE_CONFIRMATION", "schedule_status", False, None,
        "确认维持原定周二安排不变", ["还是维持在周二", "目前没有任何调整变动"], "dev", "persisted_unresolved", [],
        {"STATE_CHANGE": "显式无变动", "UNCERTAINTY_RESOLUTION": "尚未至会议举行节点"}
    ))
    gold.append(make_gold_pair(
        "GP_MEETING_05", "B_MEETING_01", "B_MEETING_02_UNRELATED",
        "UNRELATED", "none", False, None,
        "市场部在开另外的动员会", [], "dev", "temporal_distractor_unrelated", ["F1_TIME_INSUFFICIENT"],
        {"UNCERTAINTY_RESOLUTION": "完全不同的团队与会议客体"}
    ))

    # =========================================================================
    # DOMAIN 4: D4_HIRING (Senior Architect Hiring) - DEV
    # =========================================================================
    blocks.append(make_block(
        "B_HIRING_01",
        "首席架构师候选人老张的录用审批单我已经提交给集团HRD了。",
        "2026-10-04T10:00:00Z", "2026-10-04T10:05:00Z",
        "HIRING", "th_hiring_01",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "current_requirement_obligation", "summary": "老张录用审批提交集团HRD审批中"},
        ["集团HRD是否批准通过", "老张是否接受offer"],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["用户"], "target_recipient": ["集团HRD"], "affected_object": ["录用审批单"], "destination_or_location": ["集团HR系统"], "key_entities": ["老张", "首席架构师", "录用审批单"]},
    ))
    blocks.append(make_block(
        "B_HIRING_02_SUCC",
        "HRD刚在系统里签字通过了，正式offer已经发送给老张。",
        "2026-10-06T15:00:00Z", "2026-10-06T15:05:00Z",
        "HIRING", "th_hiring_01",
        {"speaker": "user", "reported_source": "HR系统", "user_endorsement": "direct"},
        "certain",
        {"status": "completed_past", "summary": "老张录用审批获HRD批准，offer已发出"},
        ["老张是否接受offer"],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["HRD"], "target_recipient": ["老张"], "affected_object": ["正式offer"], "destination_or_location": ["邮件系统"], "key_entities": ["通过", "正式offer", "老张"]},
    ))
    blocks.append(make_block(
        "B_HIRING_02_FAIL",
        "HRD把审批退回了，说薪酬方案超出当前级别上限，不同意录用。",
        "2026-10-06T14:30:00Z", "2026-10-06T14:35:00Z",
        "HIRING", "th_hiring_01",
        {"speaker": "user", "reported_source": "HR系统退回意见", "user_endorsement": "direct"},
        "certain",
        {"status": "completed_past", "summary": "老张录用审批因薪资超限被HRD驳回"},
        [],
        "assertion", "negative",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["HRD"], "target_recipient": ["用户"], "affected_object": ["录用审批单"], "destination_or_location": ["审批流"], "key_entities": ["退回", "超出上限", "不同意录用"]},
    ))
    blocks.append(make_block(
        "B_HIRING_02_CANCEL",
        "集团今天紧急下发通知全线冻结下半年技术HC，该岗位招聘已整体撤销。",
        "2026-10-05T16:00:00Z", "2026-10-05T16:05:00Z",
        "HIRING", "th_hiring_01",
        {"speaker": "user", "reported_source": "集团通知", "user_endorsement": "endorsed"},
        "certain",
        {"status": "cancelled_retracted", "summary": "因集团冻结HC导致招聘流程撤销"},
        [],
        "assertion", "negative",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["集团"], "target_recipient": ["业务线"], "affected_object": ["招聘岗位"], "destination_or_location": ["集团公告"], "key_entities": ["冻结HC", "撤销", "招聘"]},
    ))
    blocks.append(make_block(
        "B_HIRING_02_PERSIST",
        "老张的审批在HRD那里压了三天了，到现在系统状态还是待审批中。",
        "2026-10-07T11:00:00Z", "2026-10-07T11:05:00Z",
        "HIRING", "th_hiring_01",
        {"speaker": "user", "reported_source": "HR系统", "user_endorsement": "direct"},
        "probable",
        {"status": "current_requirement_obligation", "summary": "老张录用审批已积压三天，仍维持待批状态"},
        ["集团HRD是否批准通过"],
        "assertion", "mixed_contrastive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["HRD"], "target_recipient": ["老张"], "affected_object": ["审批单"], "destination_or_location": ["审批系统"], "key_entities": ["压了三天", "待审批中", "老张"]},
    ))
    blocks.append(make_block(
        "B_HIRING_02_UNRELATED",
        "今天上午面试了一个前端实习生小李，基本功还可以。",
        "2026-10-04T12:00:00Z", "2026-10-04T12:05:00Z",
        "HIRING", "th_hiring_02",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "completed_past", "summary": "完成实习生小李的面试"},
        [],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["用户"], "target_recipient": ["小李"], "affected_object": ["实习生面试"], "destination_or_location": ["会议室"], "key_entities": ["小李", "前端实习生"]},
    ))

    gold.append(make_gold_pair(
        "GP_HIRING_01", "B_HIRING_01", "B_HIRING_02_SUCC",
        "UNCERTAINTY_RESOLUTION", "approval_outcome", True, "集团HRD是否批准通过",
        "HRD签字通过，审批闭环", ["HRD刚在系统里签字通过了"], "dev", "requirement_to_success", ["F2_NO_MUTATION"],
        {"STATE_CHANGE": "审批流程预期获得正常关闭", "PERSISTENCE_CONFIRMATION": "已由未知流转至通过确知"}
    ))
    gold.append(make_gold_pair(
        "GP_HIRING_02", "B_HIRING_01", "B_HIRING_02_FAIL",
        "UNCERTAINTY_RESOLUTION", "approval_outcome", True, "集团HRD是否批准通过",
        "HRD驳回审批，确定录用失败", ["HRD把审批退回了", "不同意录用"], "dev", "requirement_to_failure", ["F2_NO_MUTATION"],
        {"STATE_CHANGE": "否定性事实直接解决先前不确定悬念"}
    ))
    gold.append(make_gold_pair(
        "GP_HIRING_03", "B_HIRING_01", "B_HIRING_02_CANCEL",
        "UNCERTAINTY_RESOLUTION", "hiring_process_continuation", True, "集团HRD是否批准通过",
        "外部政策冻结导致招聘闭环取消", ["全线冻结下半年技术HC，该岗位招聘已整体撤销"], "dev", "requirement_to_cancellation", ["F2_NO_MUTATION"],
        {"STATE_CHANGE": "外部行政令迫使流程中断终结"}
    ))
    gold.append(make_gold_pair(
        "GP_HIRING_04", "B_HIRING_01", "B_HIRING_02_PERSIST",
        "PERSISTENCE_CONFIRMATION", "approval_state", False, None,
        "处于三天停滞审批积压态", ["到现在系统状态还是待审批中"], "dev", "persisted_unresolved", [],
        {"UNCERTAINTY_RESOLUTION": "HRD未作裁决"}
    ))
    gold.append(make_gold_pair(
        "GP_HIRING_05", "B_HIRING_01", "B_HIRING_02_UNRELATED",
        "UNRELATED", "none", False, None,
        "前端实习生小李面试，无关老张", [], "dev", "temporal_distractor_unrelated", ["F1_TIME_INSUFFICIENT"],
        {"UNCERTAINTY_RESOLUTION": "不同职能级别与候选人个体"}
    ))

    # =========================================================================
    # DOMAIN 5: D5_MEDICAL (Clinical Health Examination) - DEV
    # =========================================================================
    blocks.append(make_block(
        "B_MED_01",
        "我明天早晨去华山医院空腹抽血做肝功能和血脂全套检查。",
        "2026-10-05T20:00:00Z", "2026-10-05T20:05:00Z",
        "MEDICAL", "th_med_01",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "intention_plan", "summary": "明日早上去华山医院做空腹抽血化验"},
        ["明日是否按时完成抽血", "检验指标是否正常"],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["用户"], "target_recipient": ["华山医院"], "affected_object": ["肝功能血脂化验"], "destination_or_location": ["华山医院检验科"], "key_entities": ["华山医院", "抽血", "肝功能"]},
    ))
    blocks.append(make_block(
        "B_MED_02_SUCC",
        "血抽完了，护士说下午四点可以在手机App上查电子化验单。",
        "2026-10-06T09:00:00Z", "2026-10-06T09:03:00Z",
        "MEDICAL", "th_med_01",
        {"speaker": "user", "reported_source": "护士说明", "user_endorsement": "direct"},
        "certain",
        {"status": "completed_past", "summary": "顺利完成抽血，等待下午出报告"},
        ["化验单具体指标结果"],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["用户"], "target_recipient": ["华山医院"], "affected_object": ["静脉抽血"], "destination_or_location": ["检验科"], "key_entities": ["血抽完了", "电子化验单"]},
    ))
    blocks.append(make_block(
        "B_MED_02_CHANGE",
        "早上起晚不小心喝了含糖豆浆，抽血只能延期改到后天早上了。",
        "2026-10-06T08:00:00Z", "2026-10-06T08:03:00Z",
        "MEDICAL", "th_med_01",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "intention_plan", "summary": "因进食破坏空腹条件，抽血延期至后天早上"},
        ["后天早上是否顺利完成空腹抽血"],
        "assertion", "mixed_contrastive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": True, "retracted_target": "明天早上抽血的时间安排", "correction_nature": "external_state_change"},
        {"actor_agent": ["用户"], "target_recipient": ["华山医院"], "affected_object": ["抽血日程"], "destination_or_location": ["家中"], "key_entities": ["喝了豆浆", "延期改到后天", "抽血"]},
    ))
    blocks.append(make_block(
        "B_MED_02_CORR",
        "我刚看挂号短信发现我说错了，预约的是中山医院，不是华山医院。",
        "2026-10-05T20:20:00Z", "2026-10-05T20:23:00Z",
        "MEDICAL", "th_med_01",
        {"speaker": "user", "reported_source": "挂号短信", "user_endorsement": "direct"},
        "certain",
        {"status": "cancelled_retracted", "summary": "纠正医院口误：实际预约为中山医院而非华山医院"},
        [],
        "correction_retraction", "mixed_contrastive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": True, "retracted_target": "就诊医院为华山医院", "correction_nature": "speaker_slip_repair"},
        {"actor_agent": ["用户"], "target_recipient": ["中山医院"], "affected_object": ["挂号预约"], "destination_or_location": ["中山医院"], "key_entities": ["看错短信", "中山医院", "华山医院"]},
    ))
    blocks.append(make_block(
        "B_MED_02_UNRELATED",
        "晚上回家顺路在药房买了一盒复合维生素B咀嚼片。",
        "2026-10-06T18:00:00Z", "2026-10-06T18:05:00Z",
        "MEDICAL", "th_med_02",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "completed_past", "summary": "购买复合维生素B"},
        [],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["用户"], "target_recipient": ["药房"], "affected_object": ["维生素B片"], "destination_or_location": ["药房"], "key_entities": ["药房", "维生素B"]},
    ))

    gold.append(make_gold_pair(
        "GP_MED_01", "B_MED_01", "B_MED_02_SUCC",
        "UNCERTAINTY_RESOLUTION", "blood_drawing_action", True, "明日是否按时完成抽血",
        "如期完成空腹抽血化验", ["血抽完了"], "dev", "requirement_to_success", ["F2_NO_MUTATION"],
        {"STATE_CHANGE": "计划按部就班履行完毕"}
    ))
    gold.append(make_gold_pair(
        "GP_MED_02", "B_MED_01", "B_MED_02_CHANGE",
        "STATE_CHANGE", "appointment_date", False, None,
        "误饮豆浆打破空腹，检查推迟到后天", ["抽血只能延期改到后天早上了"], "dev", "plan_changed", ["F4_STATE_VS_CORRECTION"],
        {"CORRECTION_RETRACTION": "原先安排明天抽血真实无误，系后续生活事件破坏条件引发调整"}
    ))
    gold.append(make_gold_pair(
        "GP_MED_03", "B_MED_01", "B_MED_02_CORR",
        "CORRECTION_RETRACTION", "hospital_location", False, None,
        "用户口误纠正：预约的是中山医院", ["我说错了，预约的是中山医院，不是华山医院"], "dev", "statement_corrected", ["F4_STATE_VS_CORRECTION"],
        {"STATE_CHANGE": "医院预约并未发生转院改期，系口头误报"}
    ))
    gold.append(make_gold_pair(
        "GP_MED_04", "B_MED_01", "B_MED_02_UNRELATED",
        "UNRELATED", "none", False, None,
        "买维生素日常琐事", [], "dev", "temporal_distractor_unrelated", ["F1_TIME_INSUFFICIENT"],
        {"UNCERTAINTY_RESOLUTION": "与医院空腹抽血无关联"}
    ))

    # =========================================================================
    # DOMAIN 6: D6_SERVER (Production Database Migration) - DEV
    # =========================================================================
    blocks.append(make_block(
        "B_SRV_01",
        "核心生产库从MySQL迁移到PostgreSQL的操作定在今天凌晨两点实施。",
        "2026-10-06T14:00:00Z", "2026-10-06T14:05:00Z",
        "SERVER", "th_srv_01",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "intention_plan", "summary": "核心数据库迁移安排在今日凌晨两点"},
        ["凌晨两点割接是否成功", "业务是否发生异常回滚"],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["运维团队"], "target_recipient": ["生产环境"], "affected_object": ["生产数据库"], "destination_or_location": ["机房集群"], "key_entities": ["核心生产库", "PostgreSQL", "凌晨两点"]},
    ))
    blocks.append(make_block(
        "B_SRV_02_SUCC",
        "凌晨三点半数据流量全部切到新PG集群，业务回归测试全绿，割接成功。",
        "2026-10-07T03:35:00Z", "2026-10-07T03:40:00Z",
        "SERVER", "th_srv_01",
        {"speaker": "user", "reported_source": "运维发布报告", "user_endorsement": "direct"},
        "certain",
        {"status": "completed_past", "summary": "PG集群流量切换完成，回归测试通过，割接成功"},
        [],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["运维团队"], "target_recipient": ["生产环境"], "affected_object": ["PG集群"], "destination_or_location": ["生产网络"], "key_entities": ["割接成功", "全绿", "新PG集群"]},
    ))
    blocks.append(make_block(
        "B_SRV_02_FAIL",
        "割接后主键冲突严重导致订单服务雪崩，运维已于凌晨两点四十全量回滚老库。",
        "2026-10-07T03:00:00Z", "2026-10-07T03:05:00Z",
        "SERVER", "th_srv_01",
        {"speaker": "user", "reported_source": "监控警报与回滚记录", "user_endorsement": "direct"},
        "certain",
        {"status": "completed_past", "summary": "主键冲突引发异常，迁移失败并已紧急回滚老库"},
        [],
        "assertion", "negative",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["运维团队"], "target_recipient": ["生产环境"], "affected_object": ["订单服务", "老MySQL库"], "destination_or_location": ["集群"], "key_entities": ["全量回滚", "服务雪崩", "主键冲突"]},
    ))
    blocks.append(make_block(
        "B_SRV_02_CHANGE",
        "因大促压测延后，生产库迁移时间调整改到了下周五凌晨两点。",
        "2026-10-06T18:00:00Z", "2026-10-06T18:05:00Z",
        "SERVER", "th_srv_01",
        {"speaker": "user", "reported_source": "技术委员会邮件", "user_endorsement": "endorsed"},
        "certain",
        {"status": "intention_plan", "summary": "迁移时间顺延调整至下周五凌晨"},
        ["下周五迁移是否顺利"],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": True, "retracted_target": "今天凌晨两点的实施窗口", "correction_nature": "external_state_change"},
        {"actor_agent": ["技术委员会"], "target_recipient": ["运维团队"], "affected_object": ["迁移排期"], "destination_or_location": ["排期系统"], "key_entities": ["调整改到下周五", "压测延后", "迁移时间"]},
    ))
    blocks.append(make_block(
        "B_SRV_02_CORR",
        "我刚才口误敲错了，今晚要迁的是测试环境库，不是生产库。",
        "2026-10-06T14:15:00Z", "2026-10-06T14:20:00Z",
        "SERVER", "th_srv_01",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "cancelled_retracted", "summary": "纠正手误：今晚迁移目标实为测试环境库而非生产库"},
        [],
        "correction_retraction", "mixed_contrastive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": True, "retracted_target": "迁移目标为核心生产库", "correction_nature": "speaker_slip_repair"},
        {"actor_agent": ["用户"], "target_recipient": ["运维团队"], "affected_object": ["测试环境库"], "destination_or_location": ["测试集群"], "key_entities": ["敲错了", "测试环境库", "不是生产库"]},
    ))
    blocks.append(make_block(
        "B_SRV_02_UNRELATED",
        "刚才把公司内部Wiki服务器的Redis缓存实例顺手重启了一下。",
        "2026-10-06T16:00:00Z", "2026-10-06T16:05:00Z",
        "SERVER", "th_srv_02",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "completed_past", "summary": "重启内部Wiki的Redis缓存"},
        [],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["用户"], "target_recipient": ["内部Wiki"], "affected_object": ["Redis缓存"], "destination_or_location": ["Wiki机房"], "key_entities": ["Wiki", "Redis缓存"]},
    ))

    gold.append(make_gold_pair(
        "GP_SRV_01", "B_SRV_01", "B_SRV_02_SUCC",
        "UNCERTAINTY_RESOLUTION", "migration_outcome", True, "凌晨两点割接是否成功",
        "数据库割接圆满完成测试全绿", ["流量全部切到新PG集群，业务回归测试全绿，割接成功"], "dev", "requirement_to_success", ["F2_NO_MUTATION"],
        {"STATE_CHANGE": "计划执行闭合确证"}
    ))
    gold.append(make_gold_pair(
        "GP_SRV_02", "B_SRV_01", "B_SRV_02_FAIL",
        "UNCERTAINTY_RESOLUTION", "migration_outcome", True, "业务是否发生异常回滚",
        "割接故障紧急全量回滚", ["割接后主键冲突严重导致订单服务雪崩，运维已于凌晨两点四十全量回滚老库"], "dev", "requirement_to_failure", ["F2_NO_MUTATION"],
        {"STATE_CHANGE": "故障结局确定闭合"}
    ))
    gold.append(make_gold_pair(
        "GP_SRV_03", "B_SRV_01", "B_SRV_02_CHANGE",
        "STATE_CHANGE", "migration_window", False, None,
        "受压测影响，实施窗口推迟到下周五", ["生产库迁移时间调整改到了下周五凌晨两点"], "dev", "plan_changed", ["F4_STATE_VS_CORRECTION"],
        {"CORRECTION_RETRACTION": "原今晚两点计划真实有效，系正式决议改期"}
    ))
    gold.append(make_gold_pair(
        "GP_SRV_04", "B_SRV_01", "B_SRV_02_CORR",
        "CORRECTION_RETRACTION", "target_database_tier", False, None,
        "用户口误纠正：是测试库而非生产库", ["我刚才口误敲错了，今晚要迁的是测试环境库，不是生产库"], "dev", "statement_corrected", ["F4_STATE_VS_CORRECTION"],
        {"STATE_CHANGE": "并未发生生产库到测试库的降级演化，系表述有误"}
    ))
    gold.append(make_gold_pair(
        "GP_SRV_05", "B_SRV_01", "B_SRV_02_UNRELATED",
        "UNRELATED", "none", False, None,
        "Wiki Redis缓存维护与核心库迁移无关", [], "dev", "temporal_distractor_unrelated", ["F1_TIME_INSUFFICIENT"],
        {"UNCERTAINTY_RESOLUTION": "服务集群客体完全隔离"}
    ))

    # =========================================================================
    # DOMAIN 7: D7_LEASE (Apartment Lease Renewal) - HELD-OUT
    # =========================================================================
    blocks.append(make_block(
        "B_LEASE_01",
        "这套朝南两居室的租房合同下周三到期，我正在和房东谈续租一年。",
        "2026-10-07T10:00:00Z", "2026-10-07T10:05:00Z",
        "LEASE", "th_lease_01",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "intention_plan", "summary": "租约下周三到期，正在协商续租一年"},
        ["房东是否同意续租", "租金是否涨价"],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["用户"], "target_recipient": ["房东"], "affected_object": ["两居室租房合同"], "destination_or_location": ["公寓"], "key_entities": ["续租一年", "房东", "租房合同"]},
    ))
    blocks.append(make_block(
        "B_LEASE_02_SUCC",
        "房东答应维持原价续租，我们刚刚在电子租赁平台上把新合同签好了。",
        "2026-10-09T18:00:00Z", "2026-10-09T18:05:00Z",
        "LEASE", "th_lease_01",
        {"speaker": "user", "reported_source": "电子签合同", "user_endorsement": "direct"},
        "certain",
        {"status": "completed_past", "summary": "房东同意原价续租，已电子签署新合同"},
        [],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["用户", "房东"], "target_recipient": [], "affected_object": ["新租约合同"], "destination_or_location": ["电子平台"], "key_entities": ["原价续租", "签好了", "新合同"]},
    ))
    blocks.append(make_block(
        "B_LEASE_02_FAIL",
        "房东坚持每月要涨八百块还不肯让步，我们谈崩了，我决定下周搬走。",
        "2026-10-09T17:30:00Z", "2026-10-09T17:35:00Z",
        "LEASE", "th_lease_01",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "completed_past", "summary": "续租谈判破裂，用户决定下周搬走"},
        [],
        "assertion", "negative",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["房东"], "target_recipient": ["用户"], "affected_object": ["租金条件"], "destination_or_location": ["公寓"], "key_entities": ["谈崩了", "涨八百", "决定搬走"]},
    ))
    blocks.append(make_block(
        "B_LEASE_02_CHANGE",
        "房东刚打电话说他儿子下个月回国结婚要收回自住，完全不能再租了。",
        "2026-10-08T11:00:00Z", "2026-10-08T11:05:00Z",
        "LEASE", "th_lease_01",
        {"speaker": "user", "reported_source": "房东电话", "user_endorsement": "endorsed"},
        "certain",
        {"status": "cancelled_retracted", "summary": "房东家庭原因收回房屋自住，续租可能关闭"},
        [],
        "assertion", "negative",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": True, "retracted_target": "协商续租意向", "correction_nature": "external_state_change"},
        {"actor_agent": ["房东"], "target_recipient": ["用户"], "affected_object": ["房屋出租状态"], "destination_or_location": ["公寓"], "key_entities": ["收回自住", "结婚", "不能再租"]},
    ))
    blocks.append(make_block(
        "B_LEASE_02_CORR",
        "我刚才笔误把租期写错了，不是下周三到期，实际是下个月三号才到期。",
        "2026-10-07T10:15:00Z", "2026-10-07T10:20:00Z",
        "LEASE", "th_lease_01",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "cancelled_retracted", "summary": "更正到期时间笔误：是下月三号而非下周三"},
        [],
        "correction_retraction", "mixed_contrastive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": True, "retracted_target": "合同下周三到期", "correction_nature": "speaker_slip_repair"},
        {"actor_agent": ["用户"], "target_recipient": ["房东"], "affected_object": ["合同到期日"], "destination_or_location": ["租房记录"], "key_entities": ["笔误", "下个月三号", "不是下周三"]},
    ))
    blocks.append(make_block(
        "B_LEASE_02_PERSIST",
        "房东还在外地出差，续租的事情到现在一直还没有回信。",
        "2026-10-10T09:00:00Z", "2026-10-10T09:03:00Z",
        "LEASE", "th_lease_01",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "probable",
        {"status": "current_requirement_obligation", "summary": "房东出差中，续租意向仍无进展"},
        ["房东何时回复"],
        "assertion", "mixed_contrastive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["房东"], "target_recipient": ["用户"], "affected_object": ["续租答复"], "destination_or_location": ["外地"], "key_entities": ["还在出差", "没有回信"]},
    ))
    blocks.append(make_block(
        "B_LEASE_02_UNRELATED",
        "今天把地下车库的月租车位管理费交清了。",
        "2026-10-07T14:00:00Z", "2026-10-07T14:05:00Z",
        "LEASE", "th_lease_02",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "completed_past", "summary": "缴纳车位管理费"},
        [],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["用户"], "target_recipient": ["物业"], "affected_object": ["车位管理费"], "destination_or_location": ["地库"], "key_entities": ["车位管理费", "地库"]},
    ))

    gold.append(make_gold_pair(
        "GP_LEASE_01", "B_LEASE_01", "B_LEASE_02_SUCC",
        "UNCERTAINTY_RESOLUTION", "lease_negotiation_outcome", True, "房东是否同意续租",
        "原价续约成功并签署电子合同", ["房东答应维持原价续租，我们刚刚在电子租赁平台上把新合同签好了"], "held_out", "requirement_to_success", ["F2_NO_MUTATION"],
        {"STATE_CHANGE": "意向顺利转化为落定事实"}
    ))
    gold.append(make_gold_pair(
        "GP_LEASE_02", "B_LEASE_01", "B_LEASE_02_FAIL",
        "UNCERTAINTY_RESOLUTION", "lease_negotiation_outcome", True, "房东是否同意续租",
        "因加价谈崩决定搬离", ["我们谈崩了，我决定下周搬走"], "held_out", "requirement_to_failure", ["F2_NO_MUTATION"],
        {"STATE_CHANGE": "终结性否定结果"}
    ))
    gold.append(make_gold_pair(
        "GP_LEASE_03", "B_LEASE_01", "B_LEASE_02_CHANGE",
        "STATE_CHANGE", "rental_feasibility", False, None,
        "房东家庭自住改变客观出租可能", ["房东刚打电话说他儿子下个月回国结婚要收回自住"], "held_out", "plan_changed", ["F4_STATE_VS_CORRECTION"],
        {"CORRECTION_RETRACTION": "早先谈判协商确为真实事实，系外部家庭突发变迁"}
    ))
    gold.append(make_gold_pair(
        "GP_LEASE_04", "B_LEASE_01", "B_LEASE_02_CORR",
        "CORRECTION_RETRACTION", "lease_expiration_date", False, None,
        "修正到期日笔误：是下个月三号", ["我刚才笔误把租期写错了，不是下周三到期，实际是下个月三号才到期"], "held_out", "statement_corrected", ["F4_STATE_VS_CORRECTION"],
        {"STATE_CHANGE": "合同客观到期时间并未变更，系书写笔误纠偏"}
    ))
    gold.append(make_gold_pair(
        "GP_LEASE_05", "B_LEASE_01", "B_LEASE_02_PERSIST",
        "PERSISTENCE_CONFIRMATION", "negotiation_status", False, None,
        "房东出差，续租事项仍悬而未决", ["续租的事情到现在一直还没有回信"], "held_out", "persisted_unresolved", [],
        {"UNCERTAINTY_RESOLUTION": "未产生成败结果"}
    ))
    gold.append(make_gold_pair(
        "GP_LEASE_06", "B_LEASE_01", "B_LEASE_02_UNRELATED",
        "UNRELATED", "none", False, None,
        "交地库车位费与公寓续租无关", [], "held_out", "temporal_distractor_unrelated", ["F1_TIME_INSUFFICIENT"],
        {"UNCERTAINTY_RESOLUTION": "合同客体不同"}
    ))

    # =========================================================================
    # DOMAIN 8: D8_AUDIT (Q3 Financial Compliance Audit) - HELD-OUT
    # =========================================================================
    blocks.append(make_block(
        "B_AUDIT_01",
        "普华审计师事务所正在对我们第三季度的研发费用加计扣除做专项合规审核。",
        "2026-10-08T09:00:00Z", "2026-10-08T09:05:00Z",
        "AUDIT", "th_audit_01",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "intention_plan", "summary": "普华对Q3研发费用加计扣除做合规审核"},
        ["审核是否出具合规签字", "是否存在纳税调增风险"],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["普华审计师"], "target_recipient": ["财务部"], "affected_object": ["Q3研发加计扣除"], "destination_or_location": ["审计现场"], "key_entities": ["普华", "研发费用加计扣除", "合规审核"]},
    ))
    blocks.append(make_block(
        "B_AUDIT_02_SUCC",
        "审计合规签字确认函刚才正式送达，加计扣除项目全额无保留意见通过。",
        "2026-10-12T16:00:00Z", "2026-10-12T16:05:00Z",
        "AUDIT", "th_audit_01",
        {"speaker": "user", "reported_source": "合规确认函", "user_endorsement": "direct"},
        "certain",
        {"status": "completed_past", "summary": "普华出具无保留合规签字函，审核顺利完成"},
        [],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["普华审计师"], "target_recipient": ["公司"], "affected_object": ["合规确认函"], "destination_or_location": ["财务处"], "key_entities": ["无保留意见", "正式送达", "签字确认函"]},
    ))
    blocks.append(make_block(
        "B_AUDIT_02_CHANGE",
        "国家税务局刚下发新监管文件，研发审核范围扩大至包含外协外包合同全部凭证。",
        "2026-10-09T14:00:00Z", "2026-10-09T14:05:00Z",
        "AUDIT", "th_audit_01",
        {"speaker": "user", "reported_source": "税局通知", "user_endorsement": "endorsed"},
        "certain",
        {"status": "intention_plan", "summary": "新规导致审核范围扩展至外包外协合同凭证"},
        ["外协凭证是否完整过审"],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": True, "retracted_target": "原先的纯内部研发审核范围", "correction_nature": "external_state_change"},
        {"actor_agent": ["税务局"], "target_recipient": ["纳税企业", "审计师"], "affected_object": ["审核监管口径"], "destination_or_location": ["监管文件"], "key_entities": ["新监管文件", "外协外包", "扩大范围"]},
    ))
    blocks.append(make_block(
        "B_AUDIT_02_CORR",
        "我刚才看错抬头说错了，来现场做专项审核的是德勤，不是普华。",
        "2026-10-08T09:20:00Z", "2026-10-08T09:25:00Z",
        "AUDIT", "th_audit_01",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "cancelled_retracted", "summary": "纠正审计机构名称口误：实为德勤而非普华"},
        [],
        "correction_retraction", "mixed_contrastive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": True, "retracted_target": "审计机构为普华", "correction_nature": "speaker_slip_repair"},
        {"actor_agent": ["用户"], "target_recipient": ["德勤审计师"], "affected_object": ["机构名称"], "destination_or_location": ["现场"], "key_entities": ["看错抬头", "德勤", "不是普华"]},
    ))
    blocks.append(make_block(
        "B_AUDIT_02_PERSIST",
        "审计团队还在会议室对账，前两周抽检的单据现在依旧还在核实中。",
        "2026-10-11T11:00:00Z", "2026-10-11T11:05:00Z",
        "AUDIT", "th_audit_01",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "probable",
        {"status": "current_requirement_obligation", "summary": "单据审核仍在进行中，尚未出具定论"},
        ["抽检单据核实结果"],
        "assertion", "mixed_contrastive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["审计团队"], "target_recipient": ["财务部"], "affected_object": ["抽检单据"], "destination_or_location": ["会议室"], "key_entities": ["还在对账", "依旧在核实中"]},
    ))
    blocks.append(make_block(
        "B_AUDIT_02_UNRELATED",
        "行政部今天正在向全员推行差旅发票电子归档系统的新规范。",
        "2026-10-08T15:00:00Z", "2026-10-08T15:05:00Z",
        "AUDIT", "th_audit_02",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "completed_past", "summary": "行政部推行发票归档新规"},
        [],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["行政部"], "target_recipient": ["全体员工"], "affected_object": ["电子发票规范"], "destination_or_location": ["OA公告"], "key_entities": ["行政部", "发票电子归档"]},
    ))

    gold.append(make_gold_pair(
        "GP_AUDIT_01", "B_AUDIT_01", "B_AUDIT_02_SUCC",
        "UNCERTAINTY_RESOLUTION", "audit_signoff_result", True, "审核是否出具合规签字",
        "无保留意见通过审计获确认函", ["审计合规签字确认函刚才正式送达，加计扣除项目全额无保留意见通过"], "held_out", "requirement_to_success", ["F2_NO_MUTATION"],
        {"STATE_CHANGE": "审核流程得到最终确凿结果"}
    ))
    gold.append(make_gold_pair(
        "GP_AUDIT_02", "B_AUDIT_01", "B_AUDIT_02_CHANGE",
        "STATE_CHANGE", "audit_scope", False, None,
        "税局新规扩大合规审核范围至外协凭证", ["研发审核范围扩大至包含外协外包合同全部凭证"], "held_out", "plan_changed", ["F4_STATE_VS_CORRECTION"],
        {"CORRECTION_RETRACTION": "原范围为真实合规范围，因税局政策变迁引发变更"}
    ))
    gold.append(make_gold_pair(
        "GP_AUDIT_03", "B_AUDIT_01", "B_AUDIT_02_CORR",
        "CORRECTION_RETRACTION", "auditor_institution", False, None,
        "更正审计机构口误：实为德勤", ["我刚才看错抬头说错了，来现场做专项审核的是德勤，不是普华"], "held_out", "statement_corrected", ["F4_STATE_VS_CORRECTION"],
        {"STATE_CHANGE": "事实主体自始至终为德勤，纯系说辞错误"}
    ))
    gold.append(make_gold_pair(
        "GP_AUDIT_04", "B_AUDIT_01", "B_AUDIT_02_PERSIST",
        "PERSISTENCE_CONFIRMATION", "audit_progress", False, None,
        "抽检单据继续处于核实阶段", ["单据现在依旧还在核实中"], "held_out", "persisted_unresolved", [],
        {"UNCERTAINTY_RESOLUTION": "审核未完毕"}
    ))
    gold.append(make_gold_pair(
        "GP_AUDIT_05", "B_AUDIT_01", "B_AUDIT_02_UNRELATED",
        "UNRELATED", "none", False, None,
        "行政部差旅归档新规无关Q3专项审计", [], "held_out", "temporal_distractor_unrelated", ["F1_TIME_INSUFFICIENT"],
        {"UNCERTAINTY_RESOLUTION": "事件与主体不同"}
    ))

    # =========================================================================
    # DOMAIN 9: D9_LEGAL (Strategic Partnership NDA) - HELD-OUT
    # =========================================================================
    blocks.append(make_block(
        "B_LEGAL_01",
        "与阿尔法科技的战略合作双向保密协议正在法务处进行最终条款合规审查。",
        "2026-10-09T10:00:00Z", "2026-10-09T10:05:00Z",
        "LEGAL", "th_legal_01",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "intention_plan", "summary": "与阿尔法科技的保密协议正处于法务合规审查"},
        ["法务是否审批通过协议", "双方何时签署执行"],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["法务处"], "target_recipient": ["阿尔法科技"], "affected_object": ["双向保密协议"], "destination_or_location": ["法务系统"], "key_entities": ["阿尔法科技", "保密协议", "合规审查"]},
    ))
    blocks.append(make_block(
        "B_LEGAL_02_SUCC",
        "双方总法务已经签署用印，该战略合作保密协议今日起正式生效。",
        "2026-10-11T15:00:00Z", "2026-10-11T15:05:00Z",
        "LEGAL", "th_legal_01",
        {"speaker": "user", "reported_source": "法务通知", "user_endorsement": "direct"},
        "certain",
        {"status": "completed_past", "summary": "双方完成签署盖章，保密协议正式生效"},
        [],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["双方总法务"], "target_recipient": ["双方企业"], "affected_object": ["保密协议"], "destination_or_location": ["法务档案库"], "key_entities": ["正式生效", "签署用印", "保密协议"]},
    ))
    blocks.append(make_block(
        "B_LEGAL_02_CHANGE",
        "阿尔法科技法务提出异议，第四条排他期限条款已被正式修改为非排他合作。",
        "2026-10-10T14:00:00Z", "2026-10-10T14:05:00Z",
        "LEGAL", "th_legal_01",
        {"speaker": "user", "reported_source": "异议公函", "user_endorsement": "endorsed"},
        "certain",
        {"status": "intention_plan", "summary": "因对方异议，第四条排他条款修改为非排他"},
        ["修改后双方是否达成一致签约"],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": True, "retracted_target": "第四条排他条款", "correction_nature": "external_state_change"},
        {"actor_agent": ["阿尔法科技法务"], "target_recipient": ["我方法务"], "affected_object": ["第四条排他条款"], "destination_or_location": ["合同草案"], "key_entities": ["非排他合作", "异议", "第四条条款"]},
    ))
    blocks.append(make_block(
        "B_LEGAL_02_CORR",
        "我刚才口误说错了合作方名字，正在审查的是贝塔科技的协议，不是阿尔法科技。",
        "2026-10-09T10:15:00Z", "2026-10-09T10:18:00Z",
        "LEGAL", "th_legal_01",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "cancelled_retracted", "summary": "纠正合作方名称口误：实为贝塔科技而非阿尔法科技"},
        [],
        "correction_retraction", "mixed_contrastive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": True, "retracted_target": "合作方为阿尔法科技", "correction_nature": "speaker_slip_repair"},
        {"actor_agent": ["用户"], "target_recipient": ["贝塔科技"], "affected_object": ["保密协议草案"], "destination_or_location": ["法务处"], "key_entities": ["贝塔科技", "不是阿尔法科技", "口误"]},
    ))
    blocks.append(make_block(
        "B_LEGAL_02_UNRELATED",
        "今天向国家知识产权局提交了一项关于分布式缓存一致性的发明专利申请。",
        "2026-10-09T16:00:00Z", "2026-10-09T16:05:00Z",
        "LEGAL", "th_legal_02",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "completed_past", "summary": "提交发明专利申请"},
        [],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["用户", "知识产权代理人"], "target_recipient": ["国知局"], "affected_object": ["专利申请书"], "destination_or_location": ["国知局系统"], "key_entities": ["专利申请", "分布式缓存"]},
    ))

    gold.append(make_gold_pair(
        "GP_LEGAL_01", "B_LEGAL_01", "B_LEGAL_02_SUCC",
        "UNCERTAINTY_RESOLUTION", "nda_signing_outcome", True, "双方何时签署执行",
        "签署用印完成，协议正式生效", ["双方总法务已经签署用印，该战略合作保密协议今日起正式生效"], "held_out", "requirement_to_success", ["F2_NO_MUTATION"],
        {"STATE_CHANGE": "签约目标落实"}
    ))
    gold.append(make_gold_pair(
        "GP_LEGAL_02", "B_LEGAL_01", "B_LEGAL_02_CHANGE",
        "STATE_CHANGE", "nda_exclusivity_clause", False, None,
        "协议第四条根据谈判异议由排他变为非排他", ["第四条排他期限条款已被正式修改为非排他合作"], "held_out", "plan_changed", ["F4_STATE_VS_CORRECTION"],
        {"CORRECTION_RETRACTION": "原排他草案确为真实初稿，经商务博弈后调整"}
    ))
    gold.append(make_gold_pair(
        "GP_LEGAL_03", "B_LEGAL_01", "B_LEGAL_02_CORR",
        "CORRECTION_RETRACTION", "contract_counterparty", False, None,
        "纠正合作方名称口误：是贝塔科技", ["正在审查的是贝塔科技的协议，不是阿尔法科技"], "held_out", "statement_corrected", ["F4_STATE_VS_CORRECTION"],
        {"STATE_CHANGE": "阿尔法科技并非真实审查对象，系口误所致"}
    ))
    gold.append(make_gold_pair(
        "GP_LEGAL_04", "B_LEGAL_01", "B_LEGAL_02_UNRELATED",
        "UNRELATED", "none", False, None,
        "申请专利与保密协议审查无关联", [], "held_out", "temporal_distractor_unrelated", ["F1_TIME_INSUFFICIENT"],
        {"UNCERTAINTY_RESOLUTION": "法律客体不同"}
    ))

    # =========================================================================
    # DOMAIN 10: D10_OUTDOOR (Charity Marathon Event) - HELD-OUT
    # =========================================================================
    blocks.append(make_block(
        "B_EVENT_01",
        "本周六上午在奥森公园举办的年度慈善半程马拉松赛事安排已全部就绪。",
        "2026-10-10T10:00:00Z", "2026-10-10T10:05:00Z",
        "OUTDOOR", "th_event_01",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "intention_plan", "summary": "周六上午在奥森举行慈善半马安排就绪"},
        ["周六比赛是否如期举行", "天气是否支持户外起跑"],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["组委会"], "target_recipient": ["参赛跑者"], "affected_object": ["半程马拉松赛"], "destination_or_location": ["奥森公园"], "key_entities": ["慈善马拉松", "周六上午", "奥森公园"]},
    ))
    blocks.append(make_block(
        "B_EVENT_02_SUCC",
        "周六慈善马拉松顺利鸣枪完赛，共有三千名选手成功冲线完赛。",
        "2026-10-11T14:00:00Z", "2026-10-11T14:05:00Z",
        "OUTDOOR", "th_event_01",
        {"speaker": "user", "reported_source": "赛事简讯", "user_endorsement": "direct"},
        "certain",
        {"status": "completed_past", "summary": "周六赛事顺利进行，三千跑者冲线完赛"},
        [],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["跑者", "组委会"], "target_recipient": [], "affected_object": ["马拉松赛事"], "destination_or_location": ["奥森公园"], "key_entities": ["顺利鸣枪完赛", "三千名选手", "冲线完赛"]},
    ))
    blocks.append(make_block(
        "B_EVENT_02_CHANGE",
        "气象台发布雷暴黄色预警，组委会宣布马拉松比赛整体顺延改到周日上午举行。",
        "2026-10-10T16:00:00Z", "2026-10-10T16:05:00Z",
        "OUTDOOR", "th_event_01",
        {"speaker": "user", "reported_source": "组委会公告", "user_endorsement": "endorsed"},
        "certain",
        {"status": "intention_plan", "summary": "因雷暴预警，比赛改期顺延至周日上午"},
        ["周日上午天气是否适合完赛"],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": True, "retracted_target": "周六上午的比赛时间", "correction_nature": "external_state_change"},
        {"actor_agent": ["组委会"], "target_recipient": ["跑者"], "affected_object": ["比赛时间"], "destination_or_location": ["奥森公园"], "key_entities": ["雷暴预警", "顺延改到周日", "马拉松"]},
    ))
    blocks.append(make_block(
        "B_EVENT_02_CORR",
        "我刚才看错通知口误了，这周六是全马选拔赛，慈善半马实际是下个月六号。",
        "2026-10-10T10:20:00Z", "2026-10-10T10:25:00Z",
        "OUTDOOR", "th_event_01",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "cancelled_retracted", "summary": "纠正赛事时间口误：慈善半马实为下月六号"},
        [],
        "correction_retraction", "mixed_contrastive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": True, "retracted_target": "周六举办慈善半马", "correction_nature": "speaker_slip_repair"},
        {"actor_agent": ["用户"], "target_recipient": ["跑友"], "affected_object": ["赛事时间"], "destination_or_location": ["奥森公园"], "key_entities": ["看错通知", "下个月六号", "慈善半马"]},
    ))
    blocks.append(make_block(
        "B_EVENT_02_UNRELATED",
        "今天下午在体育用品店为登山露营选购了一顶防风帐篷。",
        "2026-10-10T15:00:00Z", "2026-10-10T15:05:00Z",
        "OUTDOOR", "th_event_02",
        {"speaker": "user", "reported_source": None, "user_endorsement": "direct"},
        "certain",
        {"status": "completed_past", "summary": "购买防风帐篷"},
        [],
        "assertion", "positive",
        {"type": "actual_unconditional", "condition_text": None, "consequent_text": None},
        {"is_revision": False, "retracted_target": None, "correction_nature": None},
        {"actor_agent": ["用户"], "target_recipient": ["体育用品店"], "affected_object": ["防风帐篷"], "destination_or_location": ["商店"], "key_entities": ["防风帐篷", "露营"]},
    ))

    gold.append(make_gold_pair(
        "GP_EVENT_01", "B_EVENT_01", "B_EVENT_02_SUCC",
        "UNCERTAINTY_RESOLUTION", "event_execution_outcome", True, "周六比赛是否如期举行",
        "比赛如期鸣枪并圆满落幕", ["周六慈善马拉松顺利鸣枪完赛"], "held_out", "requirement_to_success", ["F2_NO_MUTATION"],
        {"STATE_CHANGE": "比赛如约达成"}
    ))
    gold.append(make_gold_pair(
        "GP_EVENT_02", "B_EVENT_01", "B_EVENT_02_CHANGE",
        "STATE_CHANGE", "event_date", False, None,
        "天气雷暴预警，赛事整体推迟到周日", ["宣布马拉松比赛整体顺延改到周日上午举行"], "held_out", "plan_changed", ["F4_STATE_VS_CORRECTION"],
        {"CORRECTION_RETRACTION": "原周六安排系官方正式发布，后因天气不可抗力变更"}
    ))
    gold.append(make_gold_pair(
        "GP_EVENT_03", "B_EVENT_01", "B_EVENT_02_CORR",
        "CORRECTION_RETRACTION", "event_date", False, None,
        "更正赛事时间口误：慈善半马为下月六号", ["我刚才看错通知口误了", "慈善半马实际是下个月六号"], "held_out", "statement_corrected", ["F4_STATE_VS_CORRECTION"],
        {"STATE_CHANGE": "事实赛事排期自始至终未变，纯系看错口误"}
    ))
    gold.append(make_gold_pair(
        "GP_EVENT_04", "B_EVENT_01", "B_EVENT_02_UNRELATED",
        "UNRELATED", "none", False, None,
        "买露营帐篷与马拉松赛事无关", [], "held_out", "temporal_distractor_unrelated", ["F1_TIME_INSUFFICIENT"],
        {"UNCERTAINTY_RESOLUTION": "事件相隔独立"}
    ))

    # Save to files
    with open(CORPUS_FILE, "w", encoding="utf-8") as f:
        for b in blocks:
            f.write(json.dumps(b, ensure_ascii=False) + "\n")

    with open(GOLD_FILE, "w", encoding="utf-8") as f:
        for g in gold:
            f.write(json.dumps(g, ensure_ascii=False) + "\n")

    splits_data = {
        "dev_domains": ["FLIGHT", "REPORT", "MEETING", "HIRING", "MEDICAL", "SERVER"],
        "held_out_domains": ["LEASE", "AUDIT", "LEGAL", "OUTDOOR"],
        "dev_block_ids": [b["block_id"] for b in blocks if b["domain"] in ["FLIGHT", "REPORT", "MEETING", "HIRING", "MEDICAL", "SERVER"]],
        "held_out_block_ids": [b["block_id"] for b in blocks if b["domain"] in ["LEASE", "AUDIT", "LEGAL", "OUTDOOR"]],
        "dev_pair_ids": [g["pair_id"] for g in gold if g["split"] == "dev"],
        "held_out_pair_ids": [g["pair_id"] for g in gold if g["split"] == "held_out"],
        "total_blocks": len(blocks),
        "total_pairs": len(gold),
        "dev_pairs_count": len([g for g in gold if g["split"] == "dev"]),
        "held_out_pairs_count": len([g for g in gold if g["split"] == "held_out"]),
    }

    with open(SPLITS_FILE, "w", encoding="utf-8") as f:
        json.dump(splits_data, f, ensure_ascii=False, indent=2)

    print(f"Generated {len(blocks)} blocks and {len(gold)} gold relation pairs.")
    print(f"Dev pairs: {splits_data['dev_pairs_count']}, Held-out pairs: {splits_data['held_out_pairs_count']}")


if __name__ == "__main__":
    generate_all()
