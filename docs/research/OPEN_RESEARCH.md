# Open Research

This page is the public entry point for research contributions to LCE.

The repository intentionally separates **implemented engineering invariants** from **open research questions**. Contributors do not need to accept a complete theory of longitudinal cognition. Pick one question, build a controlled experiment, and let the result decide what survives.

## Active research tasks

| Issue | Question | Suggested outcome |
| --- | --- | --- |
| [#6](https://github.com/Jasonatafricanow/LCE-Longitudinal-Cognition-Engine/issues/6) | Does MST add useful reconnection signal beyond multi-scale kNN? | keep / defer / reject MST for this role |
| [#7](https://github.com/Jasonatafricanow/LCE-Longitudinal-Cognition-Engine/issues/7) | Where does semantic bridge recovery fail under paraphrase, noise, density and dropout? | operating-region / UNKNOWN boundary |
| [#8](https://github.com/Jasonatafricanow/LCE-Longitudinal-Cognition-Engine/issues/8) | Does PH-H1 add semantic value beyond simpler controls? | keep / defer / reject PH-H1 |
| [#9](https://github.com/Jasonatafricanow/LCE-Longitudinal-Cognition-Engine/issues/9) | Can bounded interpretation reject attractive but unsupported structural patterns? | adversarial evaluation fixture |
| [#10](https://github.com/Jasonatafricanow/LCE-Longitudinal-Cognition-Engine/issues/10) | How much does same-model proposal + judgment inflate conclusions? | circularity baseline |

The original capability-boundary plan remains in [#1](https://github.com/Jasonatafricanow/LCE-Longitudinal-Cognition-Engine/issues/1). The smaller issues above are intended to be independently claimable and reviewable.

## Good contribution shapes

### 1. Reproduce a failure

Example:

```text
controlled evidence
-> current representation
-> structure disappears under paraphrase
-> classify where and why
```

Useful output: deterministic fixture + failure curve.

### 2. Compare a complex supplier against a simple baseline

Example:

```text
kNN / multi-scale baseline
vs
MST / PH / other supplier
```

Useful output: incremental information, not algorithm sophistication.

### 3. Build an adversarial evaluation

Example:

```text
plausible structure
-> bounded source package
-> interpreter should reject or return UNKNOWN
```

Useful output: false-positive cases that become permanent tests.

### 4. Kill an idea cleanly

If a method adds no useful signal, document the negative result and remove it from the roadmap. This repository explicitly treats that as progress.

## Result format

Every bounded research task should end with:

```text
Result: SUPPORTED | NOT SUPPORTED | INCONCLUSIVE

Question:
Baseline:
Fixture:
Metric:
Observed operating region:
Observed failure boundary:
Increment over simpler baseline:
Known misses:
Recommendation: keep | defer | reject
```

## Existing negative results

Before proposing a new subsystem, read [FINDINGS.md](FINDINGS.md).

Several attractive ideas have already failed or been bounded:

- raw similarity collapsed mixed semantic material;
- fixed time buckets were poor semantic boundaries;
- exclusive clustering lost multi-membership;
- prior H1 structure had no useful semantic signal;
- persistence alone produced a large noise floor;
- same-model/free-search interpretation created circularity risk;
- replay/recap could manufacture support without stricter identity rules;
- green happy-path tests missed legal recovery failures.

Do not reintroduce a rejected idea under a new name without a new experiment that directly addresses the recorded failure.

## Areas open beyond the current issues

The current findings still leave important questions open:

- embedding/model quality and cross-model robustness;
- threshold calibration and operating-region estimation;
- cross-corpus generalization;
- higher-order candidate precision;
- standardized external evaluation of trajectory fidelity;
- contradiction and revision behavior under later evidence;
- independent/adversarial judging protocols.

If opening a new research issue, use the research experiment template and keep the first question narrow enough to falsify.
