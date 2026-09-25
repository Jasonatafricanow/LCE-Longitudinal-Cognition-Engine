# Per-Projection Incremental Value & Admission Table (Issue #22)

**Date:** 2026-09-25  
**Rule:** *Every proposed projection must answer: What concrete semantic distinction or retrieval/adjudication failure does this projection preserve? If a projection has no measurable downstream use, defer it.*

---

## 1. Incremental Value Summary Table

| Projection Dimension | Arm Introduced | Motivating Failure / Example | Source Evidence Needed | UNKNOWN Behavior | Deterministic vs LLM | Downstream Value (Rerank/Recall) | Adjudication Impact | Final Recommendation |
|---|---|---|---|---|---|---|---|---|
| **source_attribution** | B1 | “朋友说公司可能裁员” vs 用户直接观点 | 说话人及转述引述标记（'他说'、'朋友称'） | 未说明来源默认为用户自身直接断言 | LLM 语义提取 | 消除 100% 的转述归属混淆；防止他人观点被作为用户信念召回 | 裁决器无需重新分析嵌套引述层级，归属保真度达 100% | **KEEP** |
| **epistemic_commitment** | B1 | “公司下个月可能裁员” vs “一定会裁员” | 情态动词、概率副词（'可能'、'大概'、'八九不离十'） | 明确表达'不知道'时标记 explicitly_unknown | LLM 语义提取 | 将可能性与确定事实区分开，消除 Gate 1 中的模态通胀 | 消除 possibility -> certainty 虚假接受错误 | **KEEP** |
| **action_or_state** | B1 | “必须去北京” (约束) vs “想去” (愿望) vs “到了” (完成) | 时态助词与语气（'必须'、'打算'、'已经'、'早就会'） | 未提及具体行动时记录 state_observation | LLM 语义提取 | 区分当前强约束、计划与历史已完成，保护时间局部性 | 消除 obligation -> completed 误判 | **KEEP** |
| **localized_unknowns** | B1 | “我不知道明天是否延期” (延期未知，但用户发言已知) | 显式未知、疑问或未决前提 | 诚实罗列真正未知的具体事项列表 | LLM 语义提取 | 防止将局部未知泛化为整个 block 失效，防止脑补确定性 | 裁决器直接感知未决边界，避免 invented_certainty | **KEEP** |
| **communicative_act** | B2 | “我明天是去北京吗？” (反问确认) vs “我明天去北京” (断言) | 疑问句式、反问语气、建议标志词（'要不'） | 常规陈述归为 assertion | LLM 语义提取 | 提高语力识别，在同词重合下准确分离疑问与断言 (+16.7% R@1) | 消除 question -> assertion 认知错误 | **KEEP** |
| **polarity** | B2 | “我同意签署协议” vs “我不同意签署协议” | 显式否定词（'不'、'没'、'未'、'拒绝'） | 无否定词默认为 positive | 准确定性规则+LLM验证 | 解决向量检索对否定词不敏感的致命弱点，极性区分率 100% | 完全避免相反立场的语义污染 | **KEEP** |
| **condition_or_hypothesis** | B2 | “如果明天下雨就不去” (假设) vs “明天没去” (事实) | 条件从句连接词（'如果...就'、'要是...才'、'假设'） | 无条件时标为 actual_unconditional | LLM 语义提取 | 防止条件性预案被当成已确立的无条件既成事实 (+12.5% R@3) | 防止 counterfactual_to_fact 污染 | **KEEP** |
| **temporal_status** | B3 | “过去已发生” vs “当前约束” vs “未来计划” | 时间状语与动作体标记 | 无明显时间标记归为 present 或 timeless | 部分元数据确定性 + LLM | 对齐时间局部性与检索时态过滤 | 与 action_or_state 略有功能重合，但提供宏观时态锚点 | **KEEP** |
| **change_type & revision_retraction** | B3 | “刚才说错了不是明天是后天” (口误) vs “通知延期” (客观变化) | 纠错标志（'说错了'、'口误'）vs 变更依据（'通知改了'、'延期'） | 常规陈述标为 first_report，无纠错 | LLM 语义提取 | 区分纵向轨迹的'认知修正'与'世界演进'，防止错误历史沿袭 | 使后续轨迹合成模块能正确建立修正边 | **KEEP** |
| **scoped_unresolved_dimensions** | B3 | 未决事项带有 scope 与 blocking_condition | 依赖外部阻碍或后续事件确认的具体维度 | 无阻碍时为空 | LLM 语义提取 | 对 B1 localized_unknowns 提供了结构化 scope 扩展 | 在当前单点检索中收益较小，主要为纵向轨迹服务 | **DEFER** (当前阶段保留简版 localized_unknowns 即可，待纵向合成时启用) |
| **entity_role_anchors** | B4 | “李主管通知张经理” vs “张经理通知李主管” | 动作主语（施事）、介词宾语（受事）、涉及实体 | 无实体时为空列表 | 有界槽位提取（不破坏核心完整性） | 在近乎 100% 词汇重合的实体角色对调负样本下提供关键判别力 (+100% 角色对调准确率) | 彻底阻断主体反转负样本进入最终认知 | **KEEP** (作为有界索引，严禁蜕变为三元组) |

---

## 2. Summary Recommendation

- **KEEP (推荐保留为标准投影组件):**
  1. `source_attribution` (B1)
  2. `epistemic_commitment` (B1)
  3. `action_or_state` (B1)
  4. `localized_unknowns` (B1)
  5. `communicative_act` (B2)
  6. `polarity` (B2)
  7. `condition_or_hypothesis` (B2)
  8. `temporal_status` (B3)
  9. `change_type & revision_retraction` (B3)
  10. `entity_role_anchors` (B4) — 作为定位索引保留，绝不取代核心。

- **DEFER (推迟至纵向轨迹合成阶段再引入):**
  1. `scoped_unresolved_dimensions` (复杂作用域未决对象在当前点状检索与判定中边际增益有限，维持 B1 的扁平列表已知即可)。

- **REJECT (明确拒绝的伪扩展):**
  1. 命题切分（P3 风格的命题原子化与独立三元组）— 彻底摧毁语义完整性，坚决拒绝。
  2. 全局关系推断 — 严禁在 block 内部提前做跨 block 关系推测。