# SemanticBlock 固定 Block 实验语料 V2 — 本地使用 README

**状态：远端合成语料已写入，等待本地真实 LCE 向量模型与 LLM 消费。** V2 是 V1 的增量扩充，**没有更改 V1**。没有声称编译规则已稳定。

## 研究位置

按冻结的三步顺序执行：

1. 固定实验 Block 边界，人工提供不同语义编译方式：`baseline`、`attribution`、`state`。
2. 用**相同的真实 LCE embedding 模型和组织设置**，分别处理三个 arm，取得真实候选邻接/局部结构。**向量不负责判断真假、因果、否定或事件关系。**
3. 让 LLM 阅读每个 arm **实际产生**的候选及其编译正文，判断是否可能有真实关联、延续或趋势，并保留拒绝/未知。原文只用于事后核对。Block 自动切分、产品级噪音治理仍不在本轮范围。

## 文件与规模

- `../v1/fixed_blocks.json`：**保持不变**的 24 个 V1 固定 Block。
- `challenge_blocks.json`：本次新增 **24 个**合成固定 Block（A07—A12、B07—B12、C07—C12、D07—D12），四条业务领域各新增 6 项。
- `export_arms.py`：读取 V1+V2，结构校验后导出 **48 个固定 Block × 3 种编译版本＝144 条编译载荷**。仅使用 Python 3 标准库，不调用向量或 LLM。
- `AUDIT_ONLY_design_hypotheses.md`：**实验完成后**用于核对设计意图和原文的参考，**禁止在 STEP 2/3 前复制给 LLM 作为提示或关系清单**。

V2 新增的语境不是“某条线必然连到另一条线”的人工标签，而是让原始记录中自然出现：软件试点使用仓库扫描设备的跨线依赖、论坛礼袋采购手链的跨线交叉，以及相同品牌不同软件版本、相同银色照片不同订单、相似场地流程不同活动、不同仓库相同设备数量等近似干扰。部分跨线关联可以从上下文明确恢复，部分近似事项仅有泛主题相似性而非同一事件。设计意图在审计文件里，但**不进入消费者输入**。

这批数据是人工虚构与手工编译的实验候选；不能把这些结果称为模型已经学会编译。和 V1 一样，文本长短不作为质量要求，以能否大致恢复原意为原则。

## 本地拉取与导出

分支：`research/semantic-compiler-control-after-e1-20261008`

在本地已有 LCE 仓库中，先执行 `git status` 确认不覆盖本地修改：

```bash
git fetch origin research/semantic-compiler-control-after-e1-20261008
git switch research/semantic-compiler-control-after-e1-20261008
git pull --ff-only origin research/semantic-compiler-control-after-e1-20261008

python research/semantic_block_compiler/corpus/v2/export_arms.py --out ./out/semanticblock-v2
```

如果尚未创建本地研究分支：在 `git fetch` 后先执行 `git switch --track origin/research/semantic-compiler-control-after-e1-20261008`。需要保留其他工作区时，使用独立 worktree 或临时检出，不要在有未提交改动的分支强切换。

预期产生：

```text
out/semanticblock-v2/
    baseline.jsonl               # 48 行
    attribution.jsonl            # 48 行
    state.jsonl                  # 48 行
    id_map_ANALYST_ONLY.json     # 真实来源 ID/领域/上下文映射，仅研究者看
    EXPORT_RECEIPT.json         # 语料 SHA-256、导出 SHA-256、行数
```

正常输出包含 `PASS: 48 unique fixed blocks, 144 manual variants`。三个 JSONL 的 `id` 为**不含 A/B/C/D 事件线前缀的固定不透明 ID**；它们在不同 arm 之间保持一致，以支持结构差异比较。每行只提供：

```json
{"id":"W_...","text":"该固定 Block 的编译文本","known_at":"2026-09-07T10:00:00+08:00"}
```

`id_map_ANALYST_ONLY.json` 提供不透明 ID 与原始块编号、来源、领域、跨时点上下文的映射，**不要把它交给 LLM 消费者，也不要使用 track 标签强制构造候选**。本地 LCE 若需要其他字段，应由适配器提供技术元数据，但不可把设计者关系线索作为召回监督。

## 在本地运行真实实验

**STEP 2：** 三种 JSONL 各自进入独立空索引。三组使用相同的 LCE `gemini-embedding-001`（如果还是此前的真实模型配置）、同一维度/归一化方式、mutual-kNN/结构组织配置和候选选取协议；不允许换模型或用假向量。导入时 embedding 只使用 `text`，`known_at` 用于时间与后续组织。记录模型实际版本、`task_type`、请求配置与三组的每个 ID 的候选边、路径、孤立节点等数据。**若无法使用相同模型，记录阻塞或明确标识模型迁移，不要混入旧的横向比较。**

**STEP 3：** 给实际 STEP 2 候选及其必要编译正文，让 LLM 解释关系/拒绝/未知。需要在相同抽样协议下观察真实跨线桥接、同一领域的独立事项以及已有事件线上的状态变化。不要把 `AUDIT_ONLY_design_hypotheses.md` 和 `id_map_ANALYST_ONLY.json` 放入判断提示；分析者等消费结果冻结后才使用它们核对原文和设计意图。候选未被 LCE 召回时，不手工补进 LLM 输入冒充命中。

**报告**应区分：结构发现结果、LLM 关系解释、来源核对、未产生候选、未知与失败。模型全 ACCEPT、候选数量、向量分数本身都不足以证明哪种编译方式更好；但不要求现在就达到产品级噪音控制。

## 停止条件与注意事项

- 脚本校验失败：停止，核实 V1/V2 和提交版本。
- 未拿到真实向量：不声称 STEP 2 成功；未拿到实际 LLM 消费：不声称 STEP 3 成功。
- 原文与三个手工编译版本应可恢复大致相同的关键含义；归属显化和状态显化只是探索性写法，不是定型规则。
- **审计文件不具备真正的盲化保护**：它只是文本隔离纪律。让执行者不要预览该文件并把内容传给同一个 judge 会话。
- 48 Block 仍属小型人工合成集；若形成一些可用结构，只能作为继续验证的研究信号，不能宣称跨真实环境已稳定。
