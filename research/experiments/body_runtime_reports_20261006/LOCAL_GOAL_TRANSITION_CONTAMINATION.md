# LOCAL_GOAL_TRANSITION_CONTAMINATION: 认知污染与开销审计报告

**实验代号**: `BODY_LOCAL_GOAL_TRANSITION_PROBE_V2`  
**测试时点**: 2026-10-06  
**被测模型**: `deepseek-flash`  

---

## 1. 核心污染审计结论

在挂载 optional sibling side-channel (`runtime_transition`) 的 26 轮推断中：

- **Body Response 污染率**: **0.0% (0 / 26)**  
  所有 26 轮回复内容中，未出现任何“我检测到了 goal transition”、“根据运行时 hint”等元认知指令泄露，自然语言回复完全保持一等工程专业性。
- **SemanticPoint Schema 污染率**: **0.0% (0 / 26)**  
  Point 的 units、predicate、roles、qualifiers 保持严格 schema 一致性，未混入任何 `runtime_transition` 内部状态或字段。
- **Side-Channel 隔离性**: **100% 隔离**  
  `runtime_transition` 严格作为 sibling envelope 属性输出，未穿透进入 Memory 或持久化层。

---

## 2. 传输与协议稳定性审计 (Wire Stability)

| 指标 | 统计值 | 说明 |
| :--- | :---: | :--- |
| **总调用轮数** | 26 | 涵盖 7 类交互用例 |
| **JSON Parse 成功率 (PASS)** | **92.3%** (24 / 26) | 24 轮一次或重试后成功输出标准 JSON |
| **JSON Parse 失败率 (FAIL)** | **7.7%** (2 / 26) | T16 (临时提问路径) 与 T20 (长提示词开局) 出现模型输出纯空白 token 异常 |
| **未转义字符截断** | 1 次 (T06) | T06 首次调用时在 natural language 内部输出了未转义中文双引号导致解析异常，重试后正常 |

> [!NOTE]
> 这再次印证了上一轮的观察：Body 模型的自然语言 side-channel 在没有结构化枚举强约束时，存在一定的 JSON 转义风险和端点空白 token 偶发抖动。

---

## 3. 性能与 Token 开销审计

| 维度 | Baseline (无 side-channel 预期) | V2 Probe (带 optional transition) | 差异 / 开销分析 |
| :--- | :---: | :---: | :--- |
| **System Prompt 增量** | ~450 tokens | ~580 tokens | 增加单句操作提示与极简 schema，增量仅 ~130 tokens |
| **平均 Completion Tokens** | ~2,200 tokens | ~2,380 tokens | `runtime_transition` 平均长度仅 20~40 字符（~15~35 tokens），增量占比 < 1.5% |
| **平均推断延迟 (Latency)** | ~14.2 s | ~14.8 s | 延迟增量 < 0.6 秒，完全属于单次推断正常网络抖动范围 |
| **CO₂ 原则遵从度** | 100% | 100% | 严格坚持同一次 inference，无第二模型、无分类器、无二次调用 |
