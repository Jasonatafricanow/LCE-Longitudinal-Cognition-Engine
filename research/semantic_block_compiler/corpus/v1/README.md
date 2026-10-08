# SemanticBlock V1 实验数据使用 README（本地 Codex / LCE）

> **当前状态：语料已准备，尚未运行真实 LCE 向量组织或 LLM 关联判断。** 本文件是可执行的数据使用说明，不是实验结果报告。

## 1. 实验目标与执行分工

研究严格按以下顺序：**(1) 固定 Block 边界，比较语义编译文本 → (2) 用真实 LCE 向量模型组织候选结构 → (3) 交给 LLM 消费候选，判断哪些关联或趋势有意义**。只有编译规则在不同语料上表现大致稳定，才另行研究 Block 如何切分。

- **远端 GitHub**：保存公开合成原始语料、手工编译版本、导出脚本和研究控制面。
- **本地 Codex / LCE**：从远端拉取实验材料，使用**项目现有真实** embedding 模型及组织流程，保存原始候选结构；随后调用本地可用的 LLM 做关联判断。
- **不要求 embedding 理解逻辑**：它只负责发现可能相关的邻接或结构，关系真假由下一步 LLM 判断。
- **语义保真标准**：大致恢复原意即可；不要求原文复述、同样字数或相同句式。不能把推测写成已发生事实，也不能变更关键的来源、条件、否定或状态。

## 2. 数据位置与规模

仓库：`Jasonatafricanow/LCE-Longitudinal-Cognition-Engine`

研究分支：`research/semantic-compiler-control-after-e1-20261008`

语料目录：`research/semantic_block_compiler/corpus/v1/`

| 文件 | 作用 |
| --- | --- |
| `fixed_blocks.json` | **原始数据**：24 个固定实验 Block、26 条合成对话消息、每个 Block 三种编译版本 |
| `export_arms.py` | Python 标准库脚本：校验文件并导出三个独立的 JSONL 集合 |
| `README.md` | 本文档 |
| `../../CONTROL.md` | 研究目标、三步执行顺序和门槛的唯一控制面（相对本目录为 `../../CONTROL.md`） |

四条合成事件线，每条 6 个时点：

- A / `release`：测试包、签名、权限、测试机与正式部署
- B / `jewelry`：手链样品、客户确认、腕围修正、发货条件
- C / `venue`：论坛场地、投影设备、合同、活动调整
- D / `scanners`：扫描器订购、分批配送、验机、换货

这些事件线既有跨时点延续，也有相似的“确认、批准、发货、完成”词汇。**没有提供预设的正确关联边**；让 LCE 自己提出候选，再由 LLM 判断。

### 单个原始 Block 的字段

`fixed_blocks.json` 顶层包括 `arms` 和 `cases`。每个 `cases[]` 包含：

- `block_id`：例如 `A01`，固定实验容器的唯一 ID
- `track`：`release / jewelry / venue / scanners`
- `known_at`：该时点的本地时间字符串
- `source_turns[]`：合成原始对话，包含 `turn_id`、`role`、`text`
- `prior_context_ids[]`：同一事件线的此前 Block ID（**上下文索引，不是经过 LLM 认证的关系边**）
- `compiled.baseline`：自然叙述的手工语义编译
- `compiled.attribution`：显化谁说、谁确认、谁转述
- `compiled.state`：显化已完成、待确认、未授权等状态区别

三种版本是**人工编写的候选**，不是三次强模型生成结果，也不是已审定的语义 gold。版本之间存在措辞和篇幅差异；不能只凭本实验判断某个因子单独导致了效果。

## 3. 本地获取与导出（先执行这一步）

前提：已在本地克隆 LCE 仓库，有 Python 3。可先用 `git status` 检查工作区，避免切换分支时覆盖未提交修改。

```bash
git fetch origin research/semantic-compiler-control-after-e1-20261008
git switch research/semantic-compiler-control-after-e1-20261008
git pull --ff-only origin research/semantic-compiler-control-after-e1-20261008

python research/semantic_block_compiler/corpus/v1/export_arms.py --out ./out/semanticblock-v1
```

如果本地**尚无**该研究分支，先用 `git switch --track origin/research/semantic-compiler-control-after-e1-20261008` 创建跟踪分支，再运行导出脚本。

应产生：

```text
out/semanticblock-v1/
  baseline.jsonl       # 24 行
  attribution.jsonl    # 24 行
  state.jsonl          # 24 行
  EXPORT_RECEIPT.json  # 来源与导出文件 SHA-256
```

导出行示例（仅表示字段结构）：

```json
{"id":"A01","text":"Lumen 2.3 安装包已放到测试机共享文件夹，软件尚未安装。","known_at":"2026-09-01T10:00:00+08:00","track":"release"}
```

本地快速核对：

```bash
python -c "from pathlib import Path; p=Path('out/semanticblock-v1'); print({f.name:len(f.read_text(encoding='utf-8').splitlines()) for f in p.glob('*.jsonl')})"
```

预期三个 JSONL 各 24 行；`EXPORT_RECEIPT.json` 有三种 arm 的摘要值。校验不通过时**不要继续跑 LCE**，先确认分支、数据和编码一致。

## 4. STEP 2 — 用本地真实 LCE 向量模型

**本仓库没有承诺通用的 LCE CLI 命令；本地 Codex 应检查当前 LCE 版本的现有 embedding 入口和配置，复用既有模块，不新造向量模型或替换成随机向量。**

依次运行 `baseline`、`attribution`、`state` 三组实验：

1. 每组都从**独立的空索引或独立命名空间**开始，分别导入其 24 条数据。**同一个 ID 的三种编译版本不能混进同一个检索库**。
2. 仅使用 `text` 生成 embedding；`id`、`known_at`、`track` 只作为溯源元数据。不要提前用 `track` 强制分类或提供预定义关系边，以免把场景答案注入结构生成过程。
3. 三组固定**同一模型标识/版本、维度、参数、向量归一化规则、候选发现配置及随机种子（若适用）**。
4. 导出真实的每个 Block 候选邻居、相似度（若模型返回）、候选结构/局部连接。只观察组织结果，不让向量模型判断说话者归属、否定或事件真假。
5. 保存模型接入状态、模型版本、运行时配置及每条 arm 的原始回执。**如真实 LCE 模型不可调用，停止并报告阻塞，不换模型冒充结果**。

建议保存：

```text
out/semanticblock-v1/
  step2_run_metadata.json
  step2_baseline_candidates.jsonl
  step2_attribution_candidates.jsonl
  step2_state_candidates.jsonl
```

上述 STEP 2 文件名为**建议的交付文件名，不是本仓库已有脚本自动生成的产物**。

## 5. STEP 3 — LLM 消费 STEP 2 候选

给 LLM 的输入为：某 arm 的**实际候选对/候选组**、相关 Block 的编译正文及必要的时点信息；不提供“正确关系清单”，也不先给它原始对话答案。

建议让 LLM 对每个候选回答：

1. 是否可能存在具体的重复模式、同一事件的延续、状态演化或其他有意义关联？也可以回答“没有充分关联”。
2. 关系依据是哪些 Block 的什么信息？哪些只是字面相似，不能推成因果、已确认状态或同一个实体？
3. 若证据不足，标记 `UNKNOWN`，不要编造缺失环节。

保存 `step3_{arm}_judgments.jsonl`（建议名称），其中包含候选 ID、采纳/拒绝/未知、简要理由、引用的 Block ID 及模型标识。LLM 的答案仍需用合成原文审查是否误判，**不是绝对真值**。

跨三组比较：哪些真实消费有意义的结构在不同编译版本中出现/消失，哪一项编译表达因子值得进一步修改与复测。**不要把向量 top-1、文本字数或结构数量直接当成语义质量。**

## 6. 本地 Codex 的最低交付与停止条件

本次应把以下内容留在本地并返回研究讨论：`EXPORT_RECEIPT.json`、LCE 的真实模型与配置、三份 STEP 2 候选结构及其生成方式、STEP 3 的实际 LLM 判断、`RESULTS.md`（分开写观察、推断、限制与失败）。

停止条件：
- 导出校验失败：停止。
- 真实 LCE embedding 无法调用：记录阻塞，**不得用模拟向量代替**。
- 未运行 LLM 消费：只报告 STEP 2，**不得宣称关联成立**。
- 没有稳定的跨环境实验效果：如实标为 **INCONCLUSIVE**，不提前进入 Block 切分或产品化噪音优化。

本目录为**公开合成探索集**。它不是自动编译器、不是大型标注语料，也不包含用户真实私人对话。后续可扩充多轮复杂窗口，但不得为了让第一次结果好看而事后改写冻结输入。需要变更时应另起版本并保留原 V1 供复现。
