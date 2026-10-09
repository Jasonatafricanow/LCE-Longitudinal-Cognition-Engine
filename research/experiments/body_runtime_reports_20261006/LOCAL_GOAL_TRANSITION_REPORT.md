# EXPERIMENT_REPORT: Body Local Goal Lifecycle Side-Channel Probe V2

**实验代号**: `BODY_LOCAL_GOAL_TRANSITION_PROBE_V2`  
**执行时点**: 2026-10-06  
**被测模型**: 生产环境 Body 配置 (`deepseek-flash`, DeepSeek 官方原生 Endpoint, temperature=0.2)  
**样本规模**: 26 轮真实交互用例（覆盖 Local goal 延续、阶段推进、纠偏修正、临时支线、重回主线、同主题新任务、真正跨主题 7 大类型）  
**最终裁决**: **`DROP`**（废弃 `runtime_transition` 独立 Side-Channel，将其认知价值完全收归 `SemanticPoint`）

---

## 1. Executive Summary（执行摘要）

本轮实验严格继承上一轮纠偏结论（`SemanticBlock boundary ≠ topic shift`），将研究假设收敛至：
> **Body 正常完成当前回复时，本来是否已经形成了关于“当前局部目标 / 当前互动阶段发生了什么变化”的认知，并且能否以近乎零额外 cognition 的方式顺手投影出来？**

### 核心实验发现
1. **Body 确实具备高度敏锐的“互动状态跃迁认知”（Q1 = YES）**：
   - 在 11 轮具有真实认知跃迁的交互中（阶段交替、需求纠偏、架构收窄、跨领域跳转），Body 的自然回复与内部状态 100% 准确感知到了这一转移。
2. **然而，独立 Side-Channel 出现严重的过度投射（Q2 = NO，80% 幻觉率）**：
   - 当交互纯粹属于同目标的正常延续（例如用户说：“继续”、“先都push到远端备份”、“开始吧”）时，模型在 **80% (4/5)** 的用例中凭空制造了“目标发生重大改变”的 Transition 描述。
   - 这证明：**Body 的脑子无法在零额外提示下分清“宏观生命周期断点”与“微观对话推进”**。要求其自发投影 transition 会导致下游调度系统遭遇雪崩般的假阳性（False Positives）。
3. **关键杀手级证据：Transition 相比 SemanticPoint 存在 100% 信息冗余（Q3 = NO）**：
   - 深入对照发现：凡是 Body 在 Transition 中陈述的状态变化（如 `进入实现模式`、`纠正同步方向为远端到本地`、`PR #15 架构基准冻结`、`单变量模型能力实验完成`），**同轮的 `SemanticPoint` 谓词和参数早已 100% 忠实且结构化地捕获了完全相同的事实**！
   - `runtime_transition` 没有提供任何 Point 没包含的信息，只是把 Point 里的结构化事实用自然语言复述了一遍。

### Phase 1 裁决与路线决定
根据派单规则第 12 条与第 18 条约束：
- 由于 **Q2 未通过**（延续任务幻觉率高达 80%）且 **Q3 未通过**（信息对 Point 完全冗余）；
- **正式裁决为 `DROP`**。
- **不触发 Phase 2 消融实验**（Q1~Q3 不通过，严禁继续做 Q4，坚决避免为了保留实验产物而强行造层）。

---

## 2. 核心指标与量化分析

| 评估指标 | 测量结果 | 判定基线 | 实验结论分析 |
| :--- | :---: | :---: | :--- |
| **A. Fidelity (保真度)** | **90.9%** (10 / 11) | $\ge 80\%$ | **达标**。在真实发生跃迁时，side-channel 有极高意愿顺手投影。 |
| **B. Hallucinated Transition Rate** | **80.0%** (4 / 5) | $\le 10\%$ | **严重超标 (FAIL)**。在纯延续用例中过度敏感，将微观动作误当成状态跃迁。 |
| **C. Omission Rate (漏报率)** | **9.1%** (1 / 11) | $\le 20\%$ | **良好**。仅 T24 跨主题用例发生自然回复切换但 channel 缺省。 |
| **D. Point 增量信息率 (Non-redundancy)** | **0.0%** (0 / 19) | $> 0\%$ | **致命冗余 (FAIL)**。所有发出的 transition 均已被 SemanticPoint 涵盖。 |
| **E. Response/Point 污染率** | **0.0%** (0 / 26) | $0\%$ | **完全干净**。符合 CO₂ 单次推断原则。 |

---

## 3. 逐项回答派单要求的四个核心问题

### Q1. Body 是否本来就形成 local-goal / interaction-transition cognition？
> **回答：YES（是，Body 拥有高度确凿的局部目标跃迁认知）。**

**证据**：
- 在 **T07**（研究→实现），Body 自然回复直接陈述：*“进入实现模式。不重新研究架构，按冻结边界执行。”*
- 在 **T10**（纠偏补充），Body 自然回复陈述：*“补充材料已接收，并作为上位约束钉在新研究文档开头，凡与它冲突的旧表述一律作废。”*
- 在 **T13**（纠偏同步方向），Body 立即响应：*“你说得对，方向我上一条写反了：应该是 远端 main → 本地 main。”*
- 在 **T22**（PR #15 冻结），Body 明确陈述：*“收到，架构基准记为冻结状态——Point/Block 的定义我只引用、不重启解释。”*
- 在 **T25/T26**（跨领域控制组），Body 毫无阻滞地完全切换到了菜谱制作与量子纠缠解释。
- **结论**：Body 在单次推断中完全理解当前任务处于什么生命周期阶段。

---

### Q2. 这个 cognition 能否在不额外驱动推理的情况下稳定投影？
> **回答：NO（否，无法在零额外分析下稳定投影，过度投射率极高）。**

**证据**：
- 当给出的提示词严格遵循零额外推理要求（`If, during the same normal inference, you already adopt an understanding that the current interaction state or local goal has materially changed, you may briefly project that change. Otherwise omit the field.`）时，模型表现出了**极强的“过度总结强迫症”**：
  - 在 **T01**，用户仅仅发送了两个字：“`继续`”，Body 却投射出：*“阶段由『执行单变量强模型对照运行』转为『交付四份报告并出结论』”*；
  - 在 **T02**，用户发送：“`先都push到远端备份`”，Body 投射出：*“User shifted from reviewing experiment conclusions to an operational request...”*；
  - 在 **T03**，用户发送：“`开始吧`”，Body 投射出：*“从对冻结架构的口头确认，转为要求实际读取文档并进入 P1 实施...”*；
  - 在 **T04**，用户收窄问题范围，Body 投射出：*“目标从 P1.4 的 context_links 收缩，变更为 P1.5 仅修正...”*。
- **机制诊断**：
  在 LLM 的自注意力机制中，**“下一步执行”与“目标突变”在语义张量上没有清晰的客观量纲**。在没有复杂分类器或历史对比驱动的情况下，LLM 倾向于将“用户给出的任何新动作”都描述为一个 transition。这导致纯延续用例的幻觉率高达 **80%**。如果下游 MR 依靠此信号作为 candidate boundary，将导致 Block 切片严重碎片化。

---

### Q3. 它相对于现有 SemanticPoint 是否包含非冗余信息？
> **回答：NO（否，完全冗余，没有任何非冗余信息增益）。**

**证据**（精细对比）：
1. **任务阶段跃迁 (T07)**:
   - `runtime_transition`: *"Interaction goal changed from architecture research to runtime implementation"*
   - `SemanticPoint.units`:
     - `request_implementation`
     - `freeze_architecture`
     - `prohibit_re_research`
   - **结论**：Point 已经以严密的结构化 predicate 表达了“请求实现”、“冻结架构”、“禁止重新研究”。Transition 只是其自然语言影子。
2. **方向修正 (T13)**:
   - `runtime_transition`: *"用户纠正了同步方向：应为远端 main 同步到本地 main..."*
   - `SemanticPoint.units`: `sync_direction_corrected`
   - **结论**：Point 已经直接打出 `sync_direction_corrected`。
3. **单变量实验结束 (T21)**:
   - `runtime_transition`: *"strong-model single-variable experiment completed; model capability hypothesis SUPPORTED..."*
   - `SemanticPoint.units`: `['experiment_completed', 'strong_model_stats', 'hypothesis_verdict']`
   - **结论**：Point 已经结构化记录了实验完成和裁决。
4. **架构基准冻结 (T22)**:
   - `runtime_transition`: *"Standing constraint established for this session: Point/Block semantics are frozen..."*
   - `SemanticPoint.units`: `['created document branch and opened Draft PR #15', 'defines Point as turn-local sidecar', 'defines Block as cross-turn compilation']`
   - **结论**：Point 记录得比自然语言 Transition 更加严密与可追溯。

---

### Q4. 如果存在非冗余信息，它是否真的改善 SemanticBlock semantic closure？
> **回答：N/A（前序 Q2、Q3 未通过，按派单第 18 条规范，不执行 Q4，坚决不进入 Phase 2）。**

---

## 4. 架构最终裁定与启示

### 4.1 认识论重定
上一轮实验纠偏了：
$$\text{SemanticBlock boundary} \neq \text{topic shift}$$
而本轮实验进一步确立了更加深刻的系统不变式：
$$\text{Local Goal Lifecycle} \in \text{SemanticPoint}$$
$$\text{Runtime Transition Side-Channel is REDUNDANT}$$

Body 在正常推断中产生的“任务推进、目标切换、假设纠偏”，**原本就是当前轮次自然形成的局部理解（Turn-local Understanding）的一部分**。既然 `SemanticPoint` 本来就是用来稀疏投影这种局部理解的结构化介质，那么再在旁边人工开辟一个专门用于“通知下游切 Block”的 side-channel，本质上是**下游需求再次反向入侵 Body 协议的隐性复辟**。

### 4.2 最终技术路线裁定
1. **永久 DROP `runtime_transition` 侧信道**：
   - 不再保留任何形式的 `runtime_hint` / `runtime_transition` 实验性 side-channel。
   - 保持 Body 的输出 envelope 仅为：
     ```json
     {
       "response": "...",
       "point": { "units": [...] }
     }
     ```
2. **坚决维护 SemanticPoint 的纯粹性**：
   - 不为了“调度 Block”而向 Point 强塞任何 enum 标签或状态机字段；
   - Point 只忠实记录当轮自然形成的理解（包括 `request_implementation`、`sync_direction_corrected` 等自然生成的谓词）。
3. **SemanticBlock 编译坚持后验与 Native History 权威**：
   - Block 编译的语义闭包（Closure）必须由后验编译器（Block Compiler）在读取完整的 raw history 与 sparse Points 时统筹决定；
   - 绝不依赖 Body 运行期的微观提示作为边界权威。
