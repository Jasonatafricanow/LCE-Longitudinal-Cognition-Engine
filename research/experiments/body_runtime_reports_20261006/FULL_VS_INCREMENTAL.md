# FULL_VS_INCREMENTAL: Full-History Pro vs Incremental Evidence Access

**Experiment Code**: `SEMANTIC-BLOCK-INCREMENTAL-PRO-V1`  
**Compiler Model**: `deepseek-v4-pro` (Frozen, temperature=0.2, max_tokens=32768, response_format=json_object)  
**Frozen MR-Mem Commit**: `cbef533334e4c4efe0bf2f6d43d668d44a9907f4`  
**Raw Evidence Source**: 34 Public Messages (`rollout-2026-10-05T00-43-05-01a107cc-33f1-7a33-a100-27fc2db83dfb.jsonl`)  
**Experiment Result**: **`INCREMENTAL_RESULT = NO_COST_WIN`**

---

## 1. Executive Summary & Core Comparison

| Metric | Full Pro (Baseline 冻结) | Incremental (机械增量窗口) | 变化比例 (Ratio) | 结论/影响 |
| :--- | :---: | :---: | :---: | :--- |
| **Calls** | 1 | 5 | 5.0x | 5 轮机械窗口调用 |
| **Blocks** | 3 | 15 | 5.0x | 发生严重过度碎片化（Call 1 产出 11 Blocks） |
| **Units** | 16 | 124 | 7.75x | 出现大量逐项派单/步骤/清单枚举 |
| **Relations** | 0 | 0 | 1.0x | 内部结构仍主要为 predicate 句子列表 |
| **Input tokens** | 24,764 | 35,800 | 1.4456x (+44.6%) | 系统 Prompt 重复预填充 + Lookback 重复输入 |
| **Completion tokens** | 4,280 | 44,659 | 10.4343x (+943.4%) | 局部窗口缺乏全历史压缩压力，输出过度详述 |
| **Reasoning tokens** | 2,559 | 32,608 | 12.7425x (+1174.2%) | 模型在每个小窗口内深度反复思考，推理预算暴增 |
| **Total tokens** | 29,044 | 80,459 | 2.7702x (+177.0%) | **总 Token 暴涨至全量的 2.77 倍，无成本优势** |
| **Output chars** | 7,855 | 54,733 | 6.9679x (+596.8%) | 输出字符量扩大近 7 倍 |
| **Duplicate observations** | — | **High (显著重复)** | — | Call 1 (B1-B5) 与 Call 2 (B0) 严重重复架构边界定义 |
| **Correction loss** | — | **High (状态残留)** | — | Call 1 中被废弃的前期研究计划/交付物作为有效块永久入库 |
| **Transcript enumeration** | Low (低) | **High (复发严重)** | — | Call 1 列举 16 节/8 路径，Call 3 列举 Phase A-E / 测试清单 |

---

## 2. Incremental 5-Call 分步调用明细

| Call | Window 消息索引 | Lookback / New | Input Tok | Comp Tok | Reasoning Tok | Total Tok | Chars | Blocks | Units | Finish / Parse |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Call 1** | `[0..7]` (8 msgs) | 0 / 8 | 12,472 | 13,338 | 8,458 | 25,810 | 21,787 | 11 | 58 | stop / PASS |
| **Call 2** | `[6..15]` (10 msgs) | 2 / 8 | 9,897 | 7,776 | 6,645 | 17,673 | 5,689 | 1 | 14 | stop / PASS |
| **Call 3** | `[14..23]` (10 msgs) | 2 / 8 | 6,028 | 12,374 | 8,333 | 18,402 | 19,046 | 1 | 26 | stop / PASS |
| **Call 4** | `[22..31]` (10 msgs) | 2 / 8 | 6,125 | 7,202 | 5,804 | 13,327 | 6,490 | 1 | 16 | stop / PASS |
| **Call 5** | `[30..33]` (4 msgs) | 2 / 2 | 1,278 | 3,969 | 3,368 | 5,247 | 1,721 | 1 | 10 | stop / PASS |
| **合计** | **34 msgs** | **8 / 34** | **35,800** | **44,659** | **32,608** | **80,459** | **54,733** | **15** | **124** | **全部 PASS** |

---

## 3. 语义稳定性深度观察 (A–E 专项审计)

### A. 核心架构职责与边界保留情况
- **Full Pro Baseline**:  
  Block 0 跨全会话高度凝练了 5 处核心边界：`Point = Body 当轮理解投影`、`Point fidelity != objective correctness`、`raw Session History 是 Block 证据权威`、`Block != Point merge`、`Block = LCE point`。
- **Incremental 表现**:  
  核心关系在语义层面**未彻底丢失**，但分散在不同块中。  
  - Call 1 Block 1: 架构模型与语义权威定义；
  - Call 1 Block 2: 忠实性与客观正确性解耦（Fidelity != Correctness）；
  - Call 1 Block 3: Point 仅为副产品，禁止驱动认知；
  - Call 1 Block 5: Block 来源于原始证据，非 Point 合并；
  - Call 2 Block 0: 在单元 `pred: The session established the boundary...` 中再次完整重申上述边界。  
- **结论**: 架构概念本身的语义理解在强模型下具有韧性，但表征形态由“全局凝练”退化为“局部离散拼贴”。

### B. 纠偏与修正（Correction）被打断与孤立残留
- **Full Pro Baseline**:  
  全历史编译具备“全局后验视野”，能够识别前期方案已被推翻，仅将最终纠偏后的权威共识写入 Block 0，自动过滤已废弃的探索性讨论。
- **Incremental 表现**:  
  **严重打断并产生过时状态永久残留**。  
  在 Call 1（窗口仅覆盖消息 0..7）中，由于缺乏后续实现与验收失败的上下文，模型将前期讨论的过渡性计划作为持久认知固化：
  - **Block 8**: 记录了已被用户明确批评并收窄的“三项研究问题与 Gold Study”研究计划；
  - **Block 10**: 记录了“Assistant 承诺只产出研究文档、不写生产代码”。  
  然而在后续的 Call 3、Call 4 中，助手已经开始大范围编写代码并执行生产接入。由于缺乏跨窗口的语义淘汰与 supersession 机制，**过时的规划状态与后续的真实代码实现被同时持久化入库**，造成事实冲突。

### C. 大量重复语义块（Duplicate Blocks）
- **现象**: 机械 Lookback（每次向前带 2 条 raw 消息）和任务重述引发跨窗口重复生成。
- **典型并排复述**:
  - **Call 1 Block 1~5**: 分解生成 5 个 Block 详细定义了 Body LLM、Session History、Point、Block、LCE 的职责。
  - **Call 2 Block 0**: 重新将消息 6、7（纠偏总结）及后续消息编织成一个包含 14 个 Units 的大块，其 Unit 0~5 逐条再次重申了：
    - `Unit 0`: Body LLM=mind, Session History=record, SemanticPoint=turn projection, SemanticBlock=minimal complete unit, LCE=cognitive structure.
    - `Unit 1`: SemanticPoint exists because Body already understands; schema must not drive cognition.
    - `Unit 2`: CO2 invariant (consumer filters, never generates).
    - `Unit 4`: Point fidelity separate from objective truth.
    - `Unit 5`: Block post-hoc compiled from raw, not merged from Points.
- **结论**: 两次窗口对重叠证据独立处理，导致同一架构共识在 Canonical 库中出现两份完整独立的投影。

### D. 重新退化为结构化转录枚举（Transcript Enumeration）
- **Full Pro Baseline**:  
  在全历史下，Pro 成功摆脱了 Flash 的“逐项派单枚举”缺陷，Units 仅 16 条，概括最终结果而非步骤。
- **Incremental 表现**:  
  **严重复发**。局部窗口缩短后，模型对当前窗口内每一条消息的细节进行穷尽式枚举：
  - **Call 1 Block 0**: 枚举用户汇报的全部清单——“16 sections, 8 research routes, 3 candidates, 7 Point/Block structure examples, Q1-Q8 answers, recommended Candidate B”；
  - **Call 1 Block 8**: 将三项研究问题 A、B、C 及评估标准逐一拆成独立的 Predicate；
  - **Call 3 Block 0**: 包含 **26 个 Units**，全盘复述了助手工作步骤与派单条目：
    - `pred: requires Phase A production Host audit`
    - `pred: requires Phase B production Host cutover to SemanticRuntimeV1`
    - `pred: requires Phase C live SemanticPoint validation`
    - `pred: requires Phase D binding real Block generator`
    - `pred: requires Closure assessor V1 implementation`
    - `pred: requires Phase E real current Session auto-compile experiment`
    - `pred: sets test requirements for live integration`
    - `pred: specifies acceptance criteria for system-level completion`
    - `pred: lists non-goals for this order`
    - `pred: specifies deliverables and reporting`
- **结论**: 窗口局部化直接解除了模型的“宏观概括义务”，迫使强模型退化回“听写式记录员”。

### E. 过度碎片化（Over-Fragmentation）
- **Full Pro Baseline**: 仅 3 个清晰的 Block。
- **Incremental 表现**: 膨胀为 15 个 Block。仅 Call 1 一个窗口就裂解出 11 个 Block（Block 0 至 Block 10）。许多 Block 仅承载单一短命主张（如 Block 6 仅 3 个 units 记录 Point/Block 联合设计原则），失去了“minimal context-complete”的宏观闭包价值。

---

## 4. 机械管道与工程不变式验证

所有 15 个 Incremental Blocks 均原样进入隔离库并验证：
1. **Canonical Admission**: 15 个 Blocks 全部入库，最大属性为 3,846 bytes，未违反 16 KB 上限。
2. **Canonical Reopen / Replay**: 重启后读取并重新 Admit 检验，状态与 Hash 完全一致，零分歧。
3. **LCE Mapping & Projection Replay**: 全部 15 个 Block 顺利映射并投影至 LCE，Replay 标记均返回 `replayed=True`。
4. **Point Invariant**: LCE 依旧严格拦截 `SemanticPoint` 并抛出 `TypeError`，认知边界未被击穿。

---

## 5. 最终裁决与核心启示

```text
INCREMENTAL_RESULT = NO_COST_WIN
```

- **核心结论**:  
  在固定 `deepseek-v4-pro` 的前提下，从 full-history 改为机械 incremental evidence access，**不仅未能降低 Token 成本（总消耗从 2.9 万暴增至 8.0 万，增幅 +177%），反而严重破坏了语义形态**：诱发了过度碎片化（15 块）、跨窗口重复编译、过时规划状态残留，并使模型彻底复发为阶段清单与测试步骤的逐项听写枚举。
- **根因洞察**:  
  全历史输入并不是成本的累赘，而是模型进行“全局显著性压缩”的必要信息约束。一旦剥离全局上下文，大模型在小窗口内会建立局部的“完整性幻觉”，将局部瞬态细节放大为长期事实，从而在推理与生成阶段消耗天量 Token。
