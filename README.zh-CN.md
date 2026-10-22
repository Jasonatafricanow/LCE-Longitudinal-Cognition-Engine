# LCE — Longitudinal Cognition Engine

[English](README.md) | [简体中文](README.zh-CN.md)

研究如何从历史证据派生、修订和失效长期结构，并保留回到原始证据的链接。

## 先看证据

[发现与负结果](docs/research/FINDINGS.md) · [开放研究问题](docs/research/OPEN_RESEARCH.md) · [验证说明](docs/VERIFICATION.md)

公开实现包含 Path B 轨迹和兼容的 Frontier/Baseline 路径。稳定 Line、分支、修订和读取接口仍是派生结构，事实权威来自源记录。

较新的 Thread / Path A / Path B 工作在 [MR-Mem](https://github.com/Jasonatafricanow/MR-Mem) 中跟进，不把那里的设计宣称为本仓库已经实现的功能。本版本细节见[实现说明](docs/IMPLEMENTATION.md)。

## 复现公开验证

```bash
python -m pip install -e . -r requirements-verification.txt
python scripts/verify.py
```

需要 Python 3.12+。验证覆盖可执行机制、来源、恢复和静态检查。公开合成夹具不能证明在外部数据集上提升召回效果；外部基线对照仍未完成，这里不宣称已有分数。

## 研究贡献与权利

建议提出带有基线、对照、指标和停止条件的可证伪问题。提交较大代码贡献前，请先与维护者明确贡献和复用条款，见 [CONTRIBUTING.md](CONTRIBUTING.md)。

尚未选择项目整体的复用许可证，权利由各自权利人保留；公开可见不等于授予开源许可。见 [NOTICE.md](NOTICE.md)。
