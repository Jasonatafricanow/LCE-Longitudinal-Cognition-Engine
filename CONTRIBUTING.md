# Contributing to LCE

LCE is built around research questions that can fail.

A useful contribution does not need to prove a new algorithm is better. A reproducible negative result, a clearer failure boundary, or a stronger adversarial fixture can be equally valuable.

## Start here

Set up the public verification environment:

```bash
python -m pip install -e . -r requirements-verification.txt
python scripts/verify.py
```

Then choose one bounded task from [Open Research](docs/research/OPEN_RESEARCH.md).

If you are new to the repository, prefer an issue already marked `good first issue` or one that asks only for fixtures/evaluation rather than runtime contract changes.

## The experiment contract

Before implementation, a research task should state:

```text
Question
Baseline
Controlled fixture
Metric
Failure boundary or kill criterion
Expected artifact
```

The result should end in one of three states:

- **SUPPORTED** — the tested method adds the claimed useful signal inside a stated operating region;
- **NOT SUPPORTED** — the tested method does not add useful signal, or fails its kill criterion;
- **INCONCLUSIVE** — the experiment cannot distinguish the hypotheses with the current representation/data/evaluation.

Do not turn `INCONCLUSIVE` into a positive result by adding interpretation after the fact.

## Research order

Prefer this order:

```text
controlled synthetic fixture
-> real LCE representation path
-> baseline comparison
-> stress / failure-boundary sweep
-> blind or independent evaluation where needed
-> real/private corpus only after controlled capability is established
```

A private-corpus miss does not automatically mean an algorithm failed. It may mean the corpus does not contain enough of the target signal.

## Negative results

Negative results should remain visible.

If an experiment shows that:

- MST adds nothing beyond a simpler multi-scale baseline;
- PH-H1 produces structure without useful semantic discrimination;
- a segmentation strategy collapses under paraphrase;
- an evaluator accepts its own proposals more often than an independent judge;

then document the result, add the regression/fixture where useful, and recommend `keep / defer / reject`.

Deleting an unnecessary supplier from the roadmap is a successful research outcome.

## Pull request shape

Keep one PR focused on one research question.

A research PR should include:

- the question and baseline;
- the fixture/data generation path;
- the metric and acceptance/kill criterion;
- exact commands used;
- the result classification: `SUPPORTED / NOT SUPPORTED / INCONCLUSIVE`;
- failure cases and misses, not only successes;
- any follow-up question created by the result.

Use the repository PR template rather than replacing this with a narrative architecture document.

## Architecture boundary

Do not add a new architecture layer because an experiment is hard to make pass.

In particular:

- derived structure is not factual authority;
- similarity is not semantic truth;
- future evidence must not leak into earlier cutoffs;
- repeated replay/recap must not manufacture support;
- bounded interpretation may legitimately stop at `UNKNOWN`;
- experiments do not change accepted runtime contracts by implication.

If a result genuinely requires a contract change, separate the research result from the architecture decision and open a dedicated design/contract change.

## Reproducibility

For experiments intended to become public evidence:

- preserve random seeds or deterministic fixture generation where practical;
- record tool/model/provider versions when they affect the result;
- keep source closure inspectable;
- preserve negative controls;
- do not silently drop failed cases;
- do not use a private corpus as the only evidence.

The public verification contract is documented in [docs/VERIFICATION.md](docs/VERIFICATION.md).
