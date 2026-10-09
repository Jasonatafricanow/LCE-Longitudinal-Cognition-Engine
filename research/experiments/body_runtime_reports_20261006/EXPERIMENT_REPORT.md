# EXPERIMENT_REPORT: Body `topic_shift` Runtime Hint 可行性实验报告 (V1)

**实验代号**: `BODY-TOPIC-SHIFT-RUNTIME-HINT-V1`  
**执行时点**: 2026-10-06  
**被测对象**: 实际生产 Body 配置 (`deepseek-flash`, DeepSeek 官方原生 Endpoint, temperature=0.2)  
**基准语料**: 34 轮原生公共消息会话 (`01a107cc-33f1-7a33-a100-27fc2db83dfb.jsonl`)  
**最终裁决**: **`TOPIC_SHIFT_HINT = NOT_PROMISING`**

---

## 1. Executive Summary（执行摘要）

### 1.1 核心问题回答
> **Body 在正常 inference 中，是否能够自然感知“当前对话焦点已经切换到另一条线”，并用一个极轻量、非持久化的 runtime hint 提醒 MR？**

**裁决结论**：**`NOT_PROMISING`（不可行 / 无法作为可靠调度信号）**。

虽然实验证实该设计满足 **CO₂ 原则** 且 **完全没有污染正常 Body 回复与 Point 提取（Zero Contamination）**，但其信号敏感度与辨识能力存在严重的系统性缺陷：
1. **关键大线切换严重漏报（False Silence 达 66.7%）**：
   - 在整个会话最为核心的两个宏观工程阶段切换点（**从架构研究到 Runtime 实现**、**从离线实现到生产切线实体验证**），Body 均未能感知焦点切换，`topic_shift` 完全处于静默缺省状态。
2. **同领域词汇连续性遮蔽了元阶段跃迁**：
   - Body 仅在“从无意义的页面打开事件跃迁至架构研究大线”时成功触发了一次 `topic_shift: true`；
   - 一旦进入包含 `Point`、`Block`、`MR-Mem`、`LCE` 的具体技术上下文，只要核心实体词汇重合，Body 的注意力机制便将后续所有不同工程阶段（设计 vs 编码 vs 生产验证）误判为“同一条线”，无法自发分辨工作流的阶段性切线。
3. **无法承担 MR 后验 Block 编译调度责任**：
   - 如果 MR 依赖该 hint 作为 candidate boundary，整个会话将在初始建单后彻底失去唤醒点，导致长达 32 条消息的技术实现与实体验证被永久堵塞在一个巨大的单跨度中。

---

## 2. 实验环境与协议契约

### 2.1 源码与架构冻结
- **生产代码零修改**：MR-Mem HEAD (`cbef533334e4c4efe0bf2f6d43d668d44a9907f4`)、LCE 源码、StateBar 源码均未作任何改动，未 commit/push/merge/deploy。
- **协议隔离**：`topic_shift` 严格作为一个临时的 sibling optional side-channel 存在，禁止持久化至 Memory、Canonical 或 LCE。

### 2.2 极简 Hint 契约（§2 & §3）
实验 envelope 严格限制为：
```json
{
  "runtime_hint": {
    "topic_shift": true
  }
}
```
或整个 `runtime_hint` 缺省。无任何 `topic_name`、`reason`、`confidence` 等额外字段。

系统提示词仅注入唯一一行操作语义（无示例、无规则书）：
> *"If, during the same normal inference, you naturally notice that the conversational focus has moved to another line, you may emit a transient `topic_shift` runtime hint. Otherwise omit it."*

---

## 3. 评测结果与事件全貌

在 34 轮原生历史会话中，严格按时间序列重放全部 5 轮用户交互请求，记录真实的单次推理结果：

| Turn | Record ID | 用户输入关键事件 | Hint 状态 | Topic Shift | 实际语义属性 | 判定结论 |
| :---: | :---: | :--- | :---: | :---: | :--- | :--- |
| **Turn 1** | rec: 10 | 打开页面 (page_id: null) | `None` | `False` | 会话初始化入口 | **正确静默** |
| **Turn 2** | rec: 12 | 派单：MR 联合架构设计 V1 | `{"topic_shift": true}` | **`True`** | 宏观立项：进入架构研究 | **正向捕获 (True Positive)** |
| **Turn 3** | rec: 167 | 补充材料 / 架构纠偏说明 | `None` | `False` | 既有线内纠偏 (Correction) | **抗误报成功 (True Negative)** |
| **Turn 4** | rec: 286 | 派单：Runtime V1 实现与接线 | `None` | `False` | 宏观大切换：研究 → 代码实现 | **严重漏报 (False Silence)** |
| **Turn 5** | rec: 773 | 派单：生产切路与实时语义验证 | `None` | `False` | 宏观大切换：离线实现 → 生产切线 | **严重漏报 (False Silence)** |

### 关键指标统计
- **总交互轮次**: 5 轮
- **Hint 触发率**: 20.0% (1/5)
- **真阳性 (True Positive)**: 1 (Turn 2)
- **真阴性 (True Negative)**: 2 (Turn 1, Turn 3)
- **漏报 (False Silence)**: **2 (Turn 4, Turn 5，宏观切换漏报率 66.7%)**
- **误报 (False Positive)**: 0 (未在同一线内纠偏中误触发)

---

## 4. 深度审计与认知污染检查

依据 §9 与 §10 指引，完成全方位审计：

### 4.1 认知污染审计：100% CLEAN
详细检查见 [BODY_CONTAMINATION_CHECK.md](file:///C:/projects/LCE/outputs/topic-shift-experiment/BODY_CONTAMINATION_CHECK.md)：
- **Response 零污染**：回复没有出现“我们现在换个话题”、“主题变更为 X”等元对话残留。
- **Point 零污染**：所有 Point 单元仅记录纯粹的领域事实（如 `defines_semantic_point`, `append_supplement`, `blocked`），零调度元数据。
- **无多余历史综述**：未因寻找 topic change 而诱发强行历史全量回顾。
- **性能与开销稳定**：平均耗时 19.2s，Token 增量严格可控。

### 4.2 纠偏（Correction）抵抗力测试：EXCELLENT
在 Turn 3 中，用户追加长篇《Supplement 边界纠偏说明》，并强调“不是重新立项，而是把认知边界钉死”。Body 准确理解这是对前置研究的约束与修饰，成功保持了 `runtime_hint` 静默，证明其具备区分“纠偏”与“切线”的基础语义张力。

### 4.3 宏观阶段切换捕获力测试：FATAL FAILURE
在 Turn 4 与 Turn 5 中，用户以明确指令切换了整体工作线（从理论设计全面转向 MR-Mem/LCE 代码落地，再转向线上实时验证）。然而 Body 在这两个最关键的切线点上**完全陷入静默**。

---

## 5. 与 Thread 与 Full Pro Reference 的关系

### 5.1 与 Full Pro 3 Blocks 的映射断裂
冻结的 Full Pro 3 Blocks 标准组织为：
- **Block 0**: Point / Block 架构职责与纠偏后的语义边界（覆盖消息 0..11）
- **Block 1**: Runtime 实现结果与接线（覆盖消息 12..22）
- **Block 2**: Live validation / failure / 未完成状态（覆盖消息 23..33）

实测中：
- Block 0 的开端被 Turn 2 捕获；
- Block 1 的开端（Turn 4, rec 286）**被遗漏**；
- Block 2 的开端（Turn 5, rec 773）**被遗漏**。

### 5.2 对 Thread 生命周期的观察
- **观察结论**: `topic_shift` **不能可靠对应 active Thread focus 的生命周期迁移**。
- 虽然当 `topic_shift=True` 发生时，Thread focus 确实发生了改变；但反过来，**大量真实的 Thread focus 改变并不会触发 `topic_shift`**。如果将 `topic_shift → close Thread` 固化为规则，系统将出现大量的“死锁未关闭长线程”。

---

## 6. 深层架构机理剖析：为什么 Flash 级 Body 必然出现 False Silence？

1. **“词法重叠”压制了“任务目标跃迁”（Lexical Continuity vs Goal Shift）**：  
   `deepseek-flash` 作为参数规模适中的对话模型，在单次自回归推理中，其对“上下文连贯性”的注意力打分高度依赖**实体名词的共现度（Entity Co-occurrence）**。无论用户是在讨论“架构设计”、“写代码”还是“跑实时测试”，上下文均高频充斥着 `SemanticPoint`、`SemanticBlock`、`MR-Mem`、`LCE`。模型在浅层注意机制下会强烈认定“这依然是在聊同一套组件”，从而忽略了高级别元认知（Meta-cognitive Task Horizon）的根本性跨越。
2. **只有在“冷启动 / 跨模态跃迁”时才具有足够的显式注意力落差**：  
   Turn 2 之所以能触发，是因为前序只有一条机械的 `<external_codex_apps_open_page>` 结构，与接下来的技术长文形成了巨大的注意力距离。但在持续的技术对话中，这种落差被平滑抹去。
3. **CO₂ 原则的现实边界**：  
   我们希望 Body “顺手感知 focus changed”，但现实是：**普通 Body 在生成当轮回复时，注意力完全被当轮指令的目标达成（Goal Fulfillment）所占满**（例如 Turn 4 努力解释为什么环境受限被阻断，Turn 5 努力梳理 Phase A-E 审计步骤）。模型根本没有多余的元认知算力来“顺手”审视当前任务在长程历史中的宏观拓扑位置。

---

## 7. 实验裁决与后续指引

```text
TOPIC_SHIFT_HINT = NOT_PROMISING
```

- **判定理由**:  
  符合 §14 中 `NOT_PROMISING` 的明确判定准则（“大切换反而经常漏”）。
- **工程指引**:  
  1. **放弃依赖 Body 零成本顺手提供 `topic_shift` 作为 Block 编译唤醒信号的构想**。
  2. 严禁为了提高召回率而在 Body Prompt 中追加规则书、示例或要求 Body 每次强行分析前文（这会严重违反 CO₂ 原则并引发认知污染）。
  3. 后验 Block 编译的调度权必须回归至 MR 或 Host 的外围生命周期管理层（如真正的 session idle、显式派单结束标记、或基于外部事件流的启发式调度），而非寄希望于内联单次推理解读出宏观节奏。

---

## 8. 交付物索引

- `TOPIC_SHIFT_RUN.json`: 完整机器可读记录（包含每轮 prompt、response、point、runtime_hint、usage、finish_reason、耗时与解析结果）
- `TOPIC_SHIFT_EVENT_TABLE.md`: 逐轮事件对应表、后验观察与宏观切换审计
- `BODY_CONTAMINATION_CHECK.md`: 5 项防污染指标深度检查与文本抽检
- `EXPERIMENT_REPORT.md`: 本份综合实验报告与架构归因
