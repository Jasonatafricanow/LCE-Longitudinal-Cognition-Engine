# LCE — Longitudinal Cognition Engine

[English](README.md) | [简体中文](README.zh-CN.md)

A research system for deriving, revising and invalidating longitudinal structures while retaining links to their original evidence.

## Start with the evidence

[Findings and negative results](docs/research/FINDINGS.md) · [open research questions](docs/research/OPEN_RESEARCH.md) · [verification](docs/VERIFICATION.md)

The public implementation contains Path B trajectories and a compatibility Frontier/Baseline path. Stable Lines, branches, revisions and read APIs remain derived structures; source records retain factual authority.

Newer Thread / Path A / Path B work is tracked in [MR-Mem](https://github.com/Jasonatafricanow/MR-Mem). Those designs are not presented as already implemented in this repository. See [this checkout's implementation guide](docs/IMPLEMENTATION.md).

## Reproduce the public gate

```bash
python -m pip install -e . -r requirements-verification.txt
python scripts/verify.py
```

Python 3.12+. The gate covers executable mechanics, provenance, recovery and static checks. Public synthetic fixtures do not establish improved recall on an external dataset. An external baseline comparison remains open; no benchmark score is claimed here.

## Research contributions and rights

Propose a falsifiable question with a baseline, controls, metric and stopping criterion. Before submitting substantial code, clarify contribution and reuse terms with the maintainer; see [CONTRIBUTING.md](CONTRIBUTING.md).

No project-wide reuse license has been selected. All rights remain with their respective holders; public source visibility does not grant an open-source license. See [NOTICE.md](NOTICE.md).
