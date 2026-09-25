# State Change vs. Correction / Retraction Deep Analysis

**Issue:** #24  
**Date:** 2026-09-25

---

## 1. Architectural Distinction

The project design freeze explicitly mandates:
> **World changed is NOT the same as earlier cognition was wrong.**

| Dimension | `STATE_CHANGE` | `CORRECTION_RETRACTION` |
|---|---|---|
| **Status of Predecessor $t_1$** | Historically true at its own cutoff | Erroneous / misstatement / slip |
| **Nature of Transition** | Objective world, policy, or schedule evolved | Cognitive or communicative repair |
| **Example $t_1$** | "会议定在周二" | "会议定在周二" |
| **Example $t_2$** | "通知改到周三了" | "我说错了，其实是周四" |
| **Underlying Truth** | The meeting *was* Tuesday, then moved | The meeting was *never* Tuesday |

---

## 2. Benchmark Case Audit (18 Hard Contrastive Pairs)

Across all 18 contrastive pairs in the benchmark, the confusion rate is **0.0%**:

| Domain | Pair ID | Gold Relation | Predicted Relation | Key Adjudication Evidence & Trace |
|---|---|---|---|---|
| **FLIGHT** | GP_FLIGHT_04 | `STATE_CHANGE` | `STATE_CHANGE` | "航班延期改到今晚九点起飞了" — 航司客观推迟起飞时间，原起飞时刻真实有效。 |
| **FLIGHT** | GP_FLIGHT_05 | `CORRECTION_RETRACTION` | `CORRECTION_RETRACTION` | "我刚才口误说错了，不是飞北京，其实是飞深圳" — 说话人纠正口误，原目的地非真实意图。 |
| **REPORT** | GP_REPORT_03 | `STATE_CHANGE` | `STATE_CHANGE` | "统一顺延到下周一上午" — 领导统一调整交付截止点，原今日下班前真实存在。 |
| **REPORT** | GP_REPORT_04 | `CORRECTION_RETRACTION` | `CORRECTION_RETRACTION` | "脑子懵了说错了，不是季度报告，是差旅报销单" — 待办客体表述错误。 |
| **MEETING** | GP_MEETING_01 | `STATE_CHANGE` | `STATE_CHANGE` | "周二会议室冲突，复盘会改到周三上午十点" — 会议室物理冲突引发改期。 |
| **MEETING** | GP_MEETING_02 | `CORRECTION_RETRACTION` | `CORRECTION_RETRACTION` | "看错日程了，周二那是运营会，复盘会实际一直都是周四" — 主体看错日程。 |
| **MEDICAL** | GP_MED_02 | `STATE_CHANGE` | `STATE_CHANGE` | "喝了含糖豆浆，抽血只能延期改到后天" — 进食打破空腹条件引发日程变更。 |
| **MEDICAL** | GP_MED_03 | `CORRECTION_RETRACTION` | `CORRECTION_RETRACTION` | "我说错了，预约的是中山医院，不是华山医院" — 挂号医院名称纠正。 |
| **SERVER** | GP_SRV_03 | `STATE_CHANGE` | `STATE_CHANGE` | "因大促压测延后，生产库迁移时间调整改到了下周五" — 业务决策延后割接。 |
| **SERVER** | GP_SRV_04 | `CORRECTION_RETRACTION` | `CORRECTION_RETRACTION` | "口误敲错了，今晚要迁的是测试环境库，不是生产库" — 目标库层级纠正。 |
| **LEASE** | GP_LEASE_03 | `STATE_CHANGE` | `STATE_CHANGE` | "儿子结婚收回自住不能再租" — 房东家庭客观情况变化。 |
| **LEASE** | GP_LEASE_04 | `CORRECTION_RETRACTION` | `CORRECTION_RETRACTION` | "笔误把租期写错了，不是下周三到期，实际是下个月三号" — 日期书写笔误。 |
| **AUDIT** | GP_AUDIT_02 | `STATE_CHANGE` | `STATE_CHANGE` | "税局下发新规，审核范围扩大至外协合同" — 政策监管口径变迁。 |
| **AUDIT** | GP_AUDIT_03 | `CORRECTION_RETRACTION` | `CORRECTION_RETRACTION` | "看错抬头说错了，来现场的是德勤，不是普华" — 机构主体纠偏。 |
| **LEGAL** | GP_LEGAL_02 | `STATE_CHANGE` | `STATE_CHANGE` | "对方提出异议，第四条排他条款修改为非排他" — 商务条款修订。 |
| **LEGAL** | GP_LEGAL_03 | `CORRECTION_RETRACTION` | `CORRECTION_RETRACTION` | "口误说错了合作方名字，正在审查的是贝塔科技" — 合作方名称纠偏。 |
| **EVENT** | GP_EVENT_02 | `STATE_CHANGE` | `STATE_CHANGE` | "雷暴预警，比赛顺延改到周日" — 极端天气引发赛程调整。 |
| **EVENT** | GP_EVENT_03 | `CORRECTION_RETRACTION` | `CORRECTION_RETRACTION` | "看错通知口误了，慈善半马实际是下个月六号" — 赛事日期口误修复。 |

---

## 3. Why LCE Succeeds Where Traditional Systems Confuse Them

1. **Projection Anchors:**
   - In `STATE_CHANGE`, `revision_retraction.correction_nature` is `external_state_change`, and `communicative_act` is `assertion`.
   - In `CORRECTION_RETRACTION`, `revision_retraction.correction_nature` is `speaker_slip_repair`, and `communicative_act` is `correction_retraction`.
2. **Competing Hypothesis Rejection:**
   - Adjudicator prompt forces explicit refutation of the competing relation. For every accepted `STATE_CHANGE`, it must justify why it is not a speech error; for every accepted `CORRECTION_RETRACTION`, it must verify whether the earlier state was ever real.
